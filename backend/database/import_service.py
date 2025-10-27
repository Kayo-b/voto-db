"""
Service for importing data from Brazilian Chamber of Deputies API into the database.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logging
from datetime import datetime

from .model import Deputado, Partido, Legislatura
from .connection import SessionLocal

logger = logging.getLogger(__name__)


class DeputadoImportService:
    """Service for importing deputados from API responses"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or SessionLocal()
        self._should_close_session = db_session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.db.close()
    
    def import_deputados_from_api_response(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import deputados from API response JSON
        
        Args:
            api_response: The JSON response from the deputados API
            
        Returns:
            Dict with import statistics
        """
        try:
            deputados_data = api_response.get('dados', [])
            
            if not deputados_data:
                return {
                    'success': False,
                    'message': 'No deputados data found in response',
                    'imported': 0,
                    'errors': []
                }
            
            stats = {
                'success': True,
                'total_received': len(deputados_data),
                'imported': 0,
                'updated': 0,
                'skipped': 0,
                'errors': []
            }
            
            for deputado_data in deputados_data:
                try:
                    result = self._import_single_deputado(deputado_data)
                    if result['action'] == 'imported':
                        stats['imported'] += 1
                    elif result['action'] == 'updated':
                        stats['updated'] += 1
                    else:
                        stats['skipped'] += 1
                        
                except Exception as e:
                    error_msg = f"Error importing deputado {deputado_data.get('id', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
            
            # Commit all changes
            self.db.commit()
            
            return stats
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error importing deputados: {str(e)}")
            return {
                'success': False,
                'message': f"Import failed: {str(e)}",
                'imported': 0,
                'errors': [str(e)]
            }
    
    def _import_single_deputado(self, deputado_data: Dict[str, Any]) -> Dict[str, str]:
        """Import a single deputado from API data"""
        
        # Extract basic info
        deputado_id = deputado_data['id']
        nome = deputado_data['nome']
        sigla_partido = deputado_data['siglaPartido']
        sigla_uf = deputado_data['siglaUf']
        id_legislatura = deputado_data['idLegislatura']
        
        # Ensure party exists
        partido = self._get_or_create_partido(
            sigla=sigla_partido,
            uri=deputado_data.get('uriPartido')
        )
        
        # Ensure legislatura exists
        legislatura = self._get_or_create_legislatura(id_legislatura)
        
        # Check if deputado already exists
        existing_deputado = self.db.query(Deputado).filter(
            Deputado.id == deputado_id
        ).first()
        
        if existing_deputado:
            # Update existing deputado
            existing_deputado.nome = nome
            existing_deputado.nome_parlamentar = nome  # Use nome if nome_parlamentar not provided
            existing_deputado.uri = deputado_data.get('uri')
            existing_deputado.sigla_uf = sigla_uf
            existing_deputado.url_foto = deputado_data.get('urlFoto')
            existing_deputado.email = deputado_data.get('email')
            existing_deputado.partido_id = partido.id
            existing_deputado.legislatura_id = legislatura.id
            existing_deputado.updated_at = datetime.utcnow()
            
            return {'action': 'updated', 'deputado_id': deputado_id}
        else:
            # Create new deputado
            new_deputado = Deputado(
                id=deputado_id,
                nome=nome,
                nome_parlamentar=nome,  # Use nome if nome_parlamentar not provided
                uri=deputado_data.get('uri'),
                sigla_uf=sigla_uf,
                url_foto=deputado_data.get('urlFoto'),
                email=deputado_data.get('email'),
                partido_id=partido.id,
                legislatura_id=legislatura.id,
                situacao='Exercício'  # Default value
            )
            
            self.db.add(new_deputado)
            return {'action': 'imported', 'deputado_id': deputado_id}
    
    def _get_or_create_partido(self, sigla: str, uri: Optional[str] = None) -> Partido:
        """Get existing party or create new one"""
        
        partido = self.db.query(Partido).filter(
            Partido.sigla == sigla
        ).first()
        
        if not partido:
            partido = Partido(
                sigla=sigla,
                nome=self._get_partido_nome_from_sigla(sigla),
                uri=uri
            )
            self.db.add(partido)
            self.db.flush()  # Get the ID without committing
        
        return partido
    
    def _get_or_create_legislatura(self, numero: int) -> Legislatura:
        """Get existing legislatura or create new one"""
        
        legislatura = self.db.query(Legislatura).filter(
            Legislatura.numero == numero
        ).first()
        
        if not legislatura:
            # Set appropriate dates for legislatura 57 (current)
            inicio = datetime(2023, 2, 1) if numero == 57 else None
            fim = datetime(2027, 1, 31) if numero == 57 else None
            
            legislatura = Legislatura(
                numero=numero,
                inicio=inicio,
                fim=fim
            )
            self.db.add(legislatura)
            self.db.flush()  # Get the ID without committing
        
        return legislatura
    
    def _get_partido_nome_from_sigla(self, sigla: str) -> str:
        """Map party abbreviation to full name"""
        party_names = {
            'MDB': 'Movimento Democrático Brasileiro',
            'PT': 'Partido dos Trabalhadores',
            'PP': 'Progressistas',
            'PL': 'Partido Liberal',
            'PDT': 'Partido Democrático Trabalhista',
            'AVANTE': 'Avante',
            'PSDB': 'Partido da Social Democracia Brasileira',
            'PSB': 'Partido Socialista Brasileiro',
            'UNIÃO': 'União Brasil',
            'PSD': 'Partido Social Democrático',
            'REPUBLICANOS': 'Republicanos',
            'PSL': 'Partido Social Liberal',
            'PODEMOS': 'Podemos',
            'PSOL': 'Partido Socialismo e Liberdade',
            'PCdoB': 'Partido Comunista do Brasil',
            'CIDADANIA': 'Cidadania',
            'PMB': 'Partido da Mulher Brasileira',
            'PATRIOTA': 'Patriota',
            'SOLIDARIEDADE': 'Solidariedade',
            'NOVO': 'Partido Novo',
        }
        return party_names.get(sigla, f'Partido {sigla}')


# Utility functions for direct usage
def import_deputados_from_json(api_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to import deputados from API JSON response
    
    Usage:
        result = import_deputados_from_json(api_response)
        print(f"Imported {result['imported']} deputados")
    """
    with DeputadoImportService() as service:
        return service.import_deputados_from_api_response(api_response)