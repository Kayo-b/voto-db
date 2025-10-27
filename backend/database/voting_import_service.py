"""
Service for importing voting history data from API responses.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from .model import Deputado, Proposicao, Votacao, Voto, EstatisticaDeputado
from .connection import SessionLocal

logger = logging.getLogger(__name__)


class VotingImportService:
    """Service for importing voting history from API responses"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or SessionLocal()
        self._should_close_session = db_session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.db.close()
    
    def import_voting_history(self, voting_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import voting history from API response JSON
        
        Expected format:
        {
            "success": true,
            "data": {
                "deputado": {...},
                "historico_votacoes": [...],
                "estatisticas": {...}
            }
        }
        """
        try:
            if not voting_response.get('success'):
                return {
                    'success': False,
                    'message': 'API response indicates failure',
                    'imported_votes': 0
                }
            
            data = voting_response.get('data', {})
            deputado_data = data.get('deputado', {})
            historico_votacoes = data.get('historico_votacoes', [])
            estatisticas = data.get('estatisticas', {})
            
            # Get deputado (should already exist from previous import)
            deputado_id = deputado_data['id']
            deputado = self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
            
            if not deputado:
                return {
                    'success': False,
                    'message': f'Deputado with ID {deputado_id} not found in database',
                    'imported_votes': 0
                }
            
            # Update deputado with any additional info from voting API
            self._update_deputado_info(deputado, deputado_data)
            
            # Import votes
            votes_imported = 0
            for voto_data in historico_votacoes:
                if self._import_single_vote(deputado.id, voto_data):
                    votes_imported += 1
            
            # Update statistics
            self._update_deputado_statistics(deputado.id, estatisticas, data)
            
            # Commit changes
            self.db.commit()
            
            return {
                'success': True,
                'deputado_id': deputado.id,
                'deputado_nome': deputado.nome,
                'imported_votes': votes_imported,
                'total_votes_in_response': len(historico_votacoes)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error importing voting history: {str(e)}")
            return {
                'success': False,
                'message': f"Import failed: {str(e)}",
                'imported_votes': 0
            }
    
    def _update_deputado_info(self, deputado: Deputado, deputado_data: Dict[str, Any]):
        """Update deputado with additional info from voting API"""
        if 'nome_parlamentar' in deputado_data and deputado_data['nome_parlamentar']:
            deputado.nome_parlamentar = deputado_data['nome_parlamentar']
        
        if 'situacao' in deputado_data and deputado_data['situacao']:
            deputado.situacao = deputado_data['situacao']
        
        deputado.updated_at = datetime.utcnow()
    
    def _import_single_vote(self, deputado_id: int, voto_data: Dict[str, Any]) -> bool:
        """Import a single vote record"""
        try:
            proposicao_codigo = voto_data['proposicao']
            titulo = voto_data['titulo']
            voto = voto_data['voto']
            data_voto = datetime.fromisoformat(voto_data['data'].replace('Z', '+00:00'))
            relevancia = voto_data.get('relevancia', 'baixa')
            
            # Get or create proposição
            proposicao = self._get_or_create_proposicao(
                codigo=proposicao_codigo,
                titulo=titulo,
                relevancia=relevancia
            )
            
            # Get or create votação
            votacao = self._get_or_create_votacao(
                proposicao_id=proposicao.id,
                data_votacao=data_voto,
                descricao=f"Votação de {proposicao_codigo}"
            )
            
            # Check if vote already exists
            existing_vote = self.db.query(Voto).filter(
                Voto.deputado_id == deputado_id,
                Voto.votacao_id == votacao.id
            ).first()
            
            if not existing_vote:
                # Create new vote
                new_vote = Voto(
                    deputado_id=deputado_id,
                    votacao_id=votacao.id,
                    voto=voto
                )
                self.db.add(new_vote)
                return True
            else:
                # Update existing vote if different
                if existing_vote.voto != voto:
                    existing_vote.voto = voto
                    existing_vote.updated_at = datetime.utcnow()
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error importing vote: {str(e)}")
            return False
    
    def _get_or_create_proposicao(self, codigo: str, titulo: str, relevancia: str = 'baixa') -> Proposicao:
        """Get existing proposição or create new one"""
        proposicao = self.db.query(Proposicao).filter(
            Proposicao.codigo == codigo
        ).first()
        
        if not proposicao:
            # Parse tipo and numero from codigo (e.g., "PEC 3/2021")
            parts = codigo.split(' ')
            tipo = parts[0] if parts else 'PL'
            numero_ano = parts[1] if len(parts) > 1 else '0/2023'
            
            if '/' in numero_ano:
                numero, ano_str = numero_ano.split('/')
                ano = int(ano_str)
            else:
                numero = numero_ano
                ano = 2023
            
            proposicao = Proposicao(
                codigo=codigo,
                titulo=titulo,
                tipo=tipo,
                numero=numero,
                ano=ano,
                relevancia=relevancia
            )
            self.db.add(proposicao)
            self.db.flush()
        
        return proposicao
    
    def _get_or_create_votacao(self, proposicao_id: int, data_votacao: datetime, descricao: str = None) -> Votacao:
        """Get existing votação or create new one"""
        # Look for votacao on the same day for the same proposal
        day_start = data_votacao.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = data_votacao.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        votacao = self.db.query(Votacao).filter(
            Votacao.proposicao_id == proposicao_id,
            Votacao.data_votacao >= day_start,
            Votacao.data_votacao <= day_end
        ).first()
        
        if not votacao:
            votacao = Votacao(
                proposicao_id=proposicao_id,
                data_votacao=data_votacao,
                descricao=descricao or f"Votação realizada em {data_votacao.strftime('%d/%m/%Y')}"
            )
            self.db.add(votacao)
            self.db.flush()
        
        return votacao
    
    def _update_deputado_statistics(self, deputado_id: int, estatisticas: Dict[str, Any], full_data: Dict[str, Any]):
        """Update or create deputado statistics"""
        stats = self.db.query(EstatisticaDeputado).filter(
            EstatisticaDeputado.deputado_id == deputado_id
        ).first()
        
        if not stats:
            stats = EstatisticaDeputado(deputado_id=deputado_id)
            self.db.add(stats)
        
        # Update statistics from API response
        stats.total_votacoes_analisadas = estatisticas.get('total_votacoes_analisadas', 0)
        stats.participacao = estatisticas.get('participacao', 0)
        stats.presenca_percentual = float(estatisticas.get('presenca_percentual', 0.0))
        stats.votos_favoraveis = estatisticas.get('votos_favoraveis', 0)
        stats.votos_contrarios = estatisticas.get('votos_contrarios', 0)
        
        # Update analysis metadata
        stats.proposicoes_analisadas = full_data.get('proposicoes_analisadas', 0)
        stats.analisado_em = datetime.utcnow()
        
        if 'processamento' in full_data:
            proc = full_data['processamento']
            stats.proposicoes_tentadas = proc.get('total_proposicoes_tentadas', 0)
            taxa_str = proc.get('taxa_sucesso', '0%').replace('%', '')
            try:
                stats.taxa_sucesso = float(taxa_str) if taxa_str.replace('.', '').isdigit() else 0.0
            except (ValueError, AttributeError):
                stats.taxa_sucesso = 0.0


def import_voting_history_from_json(voting_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to import voting history from API JSON response
    """
    with VotingImportService() as service:
        return service.import_voting_history(voting_response)