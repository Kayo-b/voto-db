"""
Service for managing relevant proposições (legislative proposals).
Validates proposals against government API and stores them in database.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime
import requests
import logging

from .model import Proposicao
from .connection import SessionLocal

logger = logging.getLogger(__name__)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"


class ProposicaoService:
    """Service for managing relevant proposições"""
    
    def __init__(self, db_session: Session = None):
        self.db = db_session or SessionLocal()
        self._should_close_session = db_session is None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session:
            self.db.close()
    
    def validate_proposicao(self, codigo: str) -> Dict[str, Any]:
        """
        Validate proposição exists and has nominal voting sessions.
        
        Args:
            codigo: Proposição code (e.g., "PL 6787/2016", "PEC 3/2021")
            
        Returns:
            Dict with validation result and proposição data
        """
        try:
            # Parse código
            parts = codigo.split(' ')
            if len(parts) < 2:
                return {
                    'valid': False,
                    'error': 'Formato inválido. Use: TIPO NUMERO/ANO (ex: PL 6787/2016)'
                }
            
            tipo = parts[0]
            numero_ano = parts[1]
            
            if '/' not in numero_ano:
                return {
                    'valid': False,
                    'error': 'Formato inválido. Use: TIPO NUMERO/ANO (ex: PL 6787/2016)'
                }
            
            numero, ano = numero_ano.split('/')
            
            # Step 1: Search for proposição
            search_url = f"{CAMARA_BASE_URL}/proposicoes"
            params = {
                'siglaTipo': tipo,
                'numero': numero,
                'ano': ano,
                'itens': 1
            }
            
            logger.info(f"Searching for proposição: {codigo}")
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code != 200:
                return {
                    'valid': False,
                    'error': f'Erro ao buscar proposição: {response.status_code}'
                }
            
            data = response.json()
            proposicoes = data.get('dados', [])
            
            if not proposicoes:
                return {
                    'valid': False,
                    'error': f'Proposição {codigo} não encontrada na API da Câmara'
                }
            
            proposicao = proposicoes[0]
            proposicao_id = proposicao['id']
            
            # Step 2: Get votações (voting sessions)
            votacoes_url = f"{CAMARA_BASE_URL}/proposicoes/{proposicao_id}/votacoes"
            logger.info(f"Fetching votações for proposição ID: {proposicao_id}")
            
            votacoes_response = requests.get(votacoes_url, timeout=10)
            
            if votacoes_response.status_code != 200:
                return {
                    'valid': False,
                    'error': f'Erro ao buscar votações: {votacoes_response.status_code}'
                }
            
            votacoes_data = votacoes_response.json()
            votacoes = votacoes_data.get('dados', [])
            
            if not votacoes:
                return {
                    'valid': False,
                    'error': f'Proposição {codigo} não possui votações registradas'
                }
            
            # Step 3: Check for nominal votações
            nominal_votacoes = []
            
            for votacao in votacoes:
                votacao_id = votacao['id']
                
                # Get votos to check if it's nominal
                votos_url = f"{CAMARA_BASE_URL}/votacoes/{votacao_id}/votos"
                
                try:
                    votos_response = requests.get(votos_url, timeout=10)
                    
                    if votos_response.status_code == 200:
                        votos_data = votos_response.json()
                        votos = votos_data.get('dados', [])
                        
                        # If has individual votes, it's nominal
                        if votos and len(votos) > 0:
                            nominal_votacoes.append({
                                'id': votacao_id,
                                'data': votacao.get('dataHoraRegistro', ''),
                                'descricao': votacao.get('descricao', ''),
                                'total_votos': len(votos)
                            })
                            logger.info(f"Found nominal voting: {votacao_id} with {len(votos)} votes")
                
                except Exception as e:
                    logger.warning(f"Error checking votação {votacao_id}: {e}")
                    continue
            
            if not nominal_votacoes:
                return {
                    'valid': False,
                    'error': f'Proposição {codigo} não possui votações nominais (apenas simbólicas/secretas)'
                }
            
            # Success - proposição is valid and has nominal voting
            return {
                'valid': True,
                'proposicao_id': proposicao_id,
                'codigo': codigo,
                'tipo': tipo,
                'numero': numero,
                'ano': int(ano),
                'ementa': proposicao.get('ementa', ''),
                'autor': proposicao.get('uriAutores', ''),
                'nominal_votacoes': nominal_votacoes,
                'total_votacoes_nominais': len(nominal_votacoes)
            }
            
        except requests.RequestException as e:
            logger.error(f"Network error validating proposição: {e}")
            return {
                'valid': False,
                'error': f'Erro de conexão com API da Câmara: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error validating proposição: {e}")
            return {
                'valid': False,
                'error': f'Erro ao validar proposição: {str(e)}'
            }
    
    def add_proposicao_relevante(
        self, 
        codigo: str, 
        titulo: Optional[str] = None, 
        relevancia: str = 'média',
        votacao_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Add a relevant proposição to the database after validation.
        
        Args:
            codigo: Proposição code (e.g., "PL 6787/2016")
            titulo: Optional title/description (will use API title if not provided)
            relevancia: Relevance level (alta, média, baixa)
            votacao_id: Optional specific voting session ID
            
        Returns:
            Dict with success status and data or error message
        """
        try:
            # Validate proposição first
            validation = self.validate_proposicao(codigo)
            
            if not validation['valid']:
                return {
                    'success': False,
                    'error': validation['error']
                }
            
            # Check if already exists
            existing = self.db.query(Proposicao).filter(
                Proposicao.codigo == codigo
            ).first()
            
            if existing:
                return {
                    'success': False,
                    'error': f'Proposição {codigo} já cadastrada no sistema'
                }
            
            # Use validation titulo if not provided
            final_titulo = titulo if titulo else validation.get('titulo', codigo)
            
            # Create new proposição
            proposicao = Proposicao(
                id=validation['proposicao_id'],
                codigo=codigo,
                titulo=final_titulo,
                ementa=validation['ementa'],
                tipo=validation['tipo'],
                numero=str(validation['numero']),
                ano=validation['ano'],
                uri=f"{CAMARA_BASE_URL}/proposicoes/{validation['proposicao_id']}",
                relevancia=relevancia
            )
            
            self.db.add(proposicao)
            self.db.commit()
            self.db.refresh(proposicao)
            
            logger.info(f"Added proposição: {codigo} with {validation['total_votacoes_nominais']} nominal votações")
            
            return {
                'success': True,
                'data': {
                    'id': proposicao.id,
                    'codigo': proposicao.codigo,
                    'titulo': proposicao.titulo,
                    'tipo': proposicao.tipo,
                    'relevancia': proposicao.relevancia,
                    'total_votacoes_nominais': validation['total_votacoes_nominais'],
                    'nominal_votacoes': validation['nominal_votacoes']
                }
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding proposição: {e}")
            return {
                'success': False,
                'error': f'Erro ao adicionar proposição: {str(e)}'
            }
    
    def get_proposicoes_relevantes(self, relevancia: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all relevant proposições from database.
        
        Args:
            relevancia: Optional filter by relevance level
            
        Returns:
            List of proposições
        """
        try:
            query = self.db.query(Proposicao)
            
            if relevancia:
                query = query.filter(Proposicao.relevancia == relevancia)
            
            proposicoes = query.order_by(Proposicao.ano.desc(), Proposicao.numero.desc()).all()
            
            return [{
                'id': p.id,
                'codigo': p.codigo,
                'titulo': p.titulo,
                'ementa': p.ementa,
                'tipo': p.tipo,
                'numero': p.numero,
                'ano': p.ano,
                'relevancia': p.relevancia,
                'uri': p.uri,
                'created_at': p.created_at.isoformat() if p.created_at else None
            } for p in proposicoes]
            
        except Exception as e:
            logger.error(f"Error fetching proposições: {e}")
            return []
    
    def delete_proposicao_relevante(self, proposicao_id: int) -> Dict[str, Any]:
        """
        Delete a proposição from relevant list.
        
        Args:
            proposicao_id: ID of the proposição to delete
            
        Returns:
            Dict with success status
        """
        try:
            proposicao = self.db.query(Proposicao).filter(Proposicao.id == proposicao_id).first()
            
            if not proposicao:
                return {
                    'success': False,
                    'error': 'Proposição não encontrada'
                }
            
            codigo = proposicao.codigo
            self.db.delete(proposicao)
            self.db.commit()
            
            logger.info(f"Deleted proposição: {codigo}")
            
            return {
                'success': True,
                'message': f'Proposição {codigo} removida com sucesso'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting proposição: {e}")
            return {
                'success': False,
                'error': f'Erro ao remover proposição: {str(e)}'
            }
    
    def update_proposicao_relevancia(self, proposicao_id: int, relevancia: str) -> Dict[str, Any]:
        """
        Update the relevance level of a proposição.
        
        Args:
            proposicao_id: ID of the proposição
            relevancia: New relevance level (alta, média, baixa)
            
        Returns:
            Dict with success status
        """
        try:
            proposicao = self.db.query(Proposicao).filter(Proposicao.id == proposicao_id).first()
            
            if not proposicao:
                return {
                    'success': False,
                    'error': 'Proposição não encontrada'
                }
            
            proposicao.relevancia = relevancia
            self.db.commit()
            
            logger.info(f"Updated proposição {proposicao.codigo} relevancia to {relevancia}")
            
            return {
                'success': True,
                'message': f'Relevância atualizada para {relevancia}'
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating proposição relevancia: {e}")
            return {
                'success': False,
                'error': f'Erro ao atualizar relevância: {str(e)}'
            }


# Convenience functions for use in FastAPI endpoints
def validate_proposicao_exists(codigo: str) -> Dict[str, Any]:
    """Check if proposição exists and has nominal voting"""
    with ProposicaoService() as service:
        return service.validate_proposicao(codigo)


def add_proposicao(codigo: str, titulo: Optional[str] = None, relevancia: str = 'média') -> Dict[str, Any]:
    """Add a new relevant proposição"""
    with ProposicaoService() as service:
        return service.add_proposicao_relevante(codigo, titulo, relevancia)


def get_all_proposicoes_relevantes(relevancia: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all relevant proposições"""
    with ProposicaoService() as service:
        return service.get_proposicoes_relevantes(relevancia)


def remove_proposicao(proposicao_id: int) -> Dict[str, Any]:
    """Remove a proposição from relevant list"""
    with ProposicaoService() as service:
        return service.delete_proposicao_relevante(proposicao_id)
