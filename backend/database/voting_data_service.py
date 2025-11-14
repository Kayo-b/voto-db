"""
Service for importing and managing voting data in the database.
Handles proposições, votações, and votos from government API responses.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .connection import SessionLocal
from .model import Proposicao, Votacao, Voto, Deputado

logger = logging.getLogger(__name__)


class VotingDataService:
    """Service for managing voting data in the database"""
    
    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self._should_close = db_session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close:
            self.db.close()
    
    def import_proposicao(self, proposicao_data: Dict[str, Any]) -> Proposicao:
        """
        Import a single proposição to the database.
        Returns the proposição object (existing or newly created).
        """
        prop_id = proposicao_data.get('id')
        if not prop_id:
            raise ValueError("Proposição must have an ID")
        
        # Check if already exists
        existing = self.db.query(Proposicao).filter(Proposicao.id == prop_id).first()
        if existing:
            return existing
        
        # Extract data from API response
        tipo_numero = proposicao_data.get('numero', '')
        ano = proposicao_data.get('ano', datetime.now().year)
        
        # Create new proposição
        proposicao = Proposicao(
            id=prop_id,
            codigo=f"{proposicao_data.get('siglaTipo', '')}{tipo_numero}/{ano}".strip(),
            titulo=proposicao_data.get('ementa', '')[:500],  # Limit length
            ementa=proposicao_data.get('ementa', ''),
            tipo=proposicao_data.get('siglaTipo', ''),
            numero=str(tipo_numero),
            ano=ano,
            uri=proposicao_data.get('uri', ''),
            relevancia='alta'  # Since these are from "relevant propositions"
        )
        
        self.db.add(proposicao)
        self.db.commit()
        self.db.refresh(proposicao)
        
        logger.info(f"Created proposição {proposicao.codigo}")
        return proposicao
    
    def import_votacao(self, votacao_data: Dict[str, Any], proposicao_id: int) -> Votacao:
        """
        Import a single votação to the database.
        Returns the votação object (existing or newly created).
        """
        votacao_id = votacao_data.get('id')
        if not votacao_id:
            raise ValueError("Votação must have an ID")
        
        # Check if already exists
        existing = self.db.query(Votacao).filter(Votacao.id == votacao_id).first()
        if existing:
            return existing
        
        # Parse date
        data_str = votacao_data.get('dataHoraRegistro', votacao_data.get('data', ''))
        try:
            if 'T' in data_str:
                data_votacao = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
            else:
                data_votacao = datetime.strptime(data_str[:19], '%Y-%m-%d %H:%M:%S')
        except:
            data_votacao = datetime.now()
        
        # Create new votação
        votacao = Votacao(
            id=votacao_id,
            proposicao_id=proposicao_id,
            data_votacao=data_votacao,
            descricao=votacao_data.get('descricao', ''),
            resultado=votacao_data.get('resultado', '')
        )
        
        self.db.add(votacao)
        self.db.commit()
        self.db.refresh(votacao)
        
        logger.info(f"Created votação {votacao_id} for proposição {proposicao_id}")
        return votacao
    
    def import_voto(self, voto_data: Dict[str, Any], votacao_id: int) -> Optional[Voto]:
        """
        Import a single voto to the database.
        Returns the voto object (existing or newly created).
        """
        deputado_data = voto_data.get('deputado_', {})
        deputado_id = deputado_data.get('id')
        tipo_voto = voto_data.get('tipoVoto', '')
        
        if not deputado_id or not tipo_voto:
            return None
        
        # Check if already exists
        existing = self.db.query(Voto).filter(
            Voto.deputado_id == deputado_id,
            Voto.votacao_id == votacao_id
        ).first()
        if existing:
            return existing
        
        # Check if deputado exists in database
        deputado_exists = self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
        if not deputado_exists:
            logger.warning(f"Deputado {deputado_id} not found in database, skipping vote")
            return None
        
        # Create new voto
        voto = Voto(
            deputado_id=deputado_id,
            votacao_id=votacao_id,
            voto=tipo_voto
        )
        
        self.db.add(voto)
        self.db.commit()
        self.db.refresh(voto)
        
        return voto
    
    def import_voting_session_complete(self, 
                                     proposicao_data: Dict[str, Any], 
                                     votacao_data: Dict[str, Any], 
                                     votos_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Import a complete voting session: proposição + votação + all votos.
        Returns statistics about the import.
        """
        result = {
            'proposicao_id': None,
            'votacao_id': None,
            'votos_imported': 0,
            'votos_skipped': 0,
            'errors': []
        }
        
        try:
            # 1. Import proposição
            proposicao = self.import_proposicao(proposicao_data)
            result['proposicao_id'] = proposicao.id
            
            # 2. Import votação
            votacao = self.import_votacao(votacao_data, proposicao.id)
            result['votacao_id'] = votacao.id
            
            # 3. Import all votos
            for voto_data in votos_data:
                try:
                    voto = self.import_voto(voto_data, votacao.id)
                    if voto:
                        result['votos_imported'] += 1
                    else:
                        result['votos_skipped'] += 1
                except Exception as e:
                    result['votos_skipped'] += 1
                    result['errors'].append(f"Voto import error: {str(e)}")
            
        except Exception as e:
            result['errors'].append(f"General import error: {str(e)}")
        
        return result
    
    def get_deputado_votacoes_from_db(self, deputado_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get voting history for a deputado from database.
        Returns data in the same format as the API endpoint.
        """
        votos = self.db.query(Voto).join(Votacao).join(Proposicao).filter(
            Voto.deputado_id == deputado_id
        ).order_by(Votacao.data_votacao.desc()).limit(limit).all()
        
        votacoes_data = []
        for voto in votos:
            votacao = voto.votacao
            proposicao = votacao.proposicao
            
            votacao_info = {
                "id": votacao.id,
                "data": votacao.data_votacao.isoformat() if votacao.data_votacao else '',
                "dataHoraRegistro": votacao.data_votacao.isoformat() if votacao.data_votacao else '',
                "siglaOrgao": "",  # Not stored in our model
                "uriOrgao": "",    # Not stored in our model
                "voto": voto.voto,
                "proposicao": {
                    "id": proposicao.id,
                    "uri": proposicao.uri or f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao.id}",
                    "siglaTipo": proposicao.tipo or "",
                    "numero": proposicao.numero or "",
                    "ano": str(proposicao.ano) if proposicao.ano else "",
                    "ementa": proposicao.titulo[:100] + "..." if len(proposicao.titulo or "") > 100 else proposicao.titulo or ""
                }
            }
            votacoes_data.append(votacao_info)
        
        return votacoes_data
    
    def has_votacoes_for_deputado(self, deputado_id: int) -> bool:
        """Check if we have voting data for a specific deputado in the database."""
        count = self.db.query(Voto).filter(Voto.deputado_id == deputado_id).count()
        return count > 0


def import_voting_data_from_json(proposicao_data: Dict, votacao_data: Dict, votos_data: List[Dict]) -> Dict[str, Any]:
    """
    Convenience function to import voting data from JSON responses.
    Can be used standalone or from FastAPI endpoints.
    """
    with VotingDataService() as service:
        return service.import_voting_session_complete(proposicao_data, votacao_data, votos_data)


def get_deputado_votacoes_from_database(deputado_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Convenience function to get deputado voting history from database.
    Returns empty list if no data found.
    """
    with VotingDataService() as service:
        return service.get_deputado_votacoes_from_db(deputado_id, limit)


def check_deputado_has_voting_data(deputado_id: int) -> bool:
    """
    Convenience function to check if deputado has voting data in database.
    """
    with VotingDataService() as service:
        return service.has_votacoes_for_deputado(deputado_id)