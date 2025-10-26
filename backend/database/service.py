"""
Database service layer for VotoDB - handles all database operations
with intelligent caching and incremental updates
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import logging

from .connection import get_db_session, DatabaseService
from .models import Deputado, Proposicao, Votacao, Voto, CacheStatus, AnaliseDeputado
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

logger = logging.getLogger(__name__)

class VotoDBService:
    """Main service class for database operations with intelligent caching"""
    
    def __init__(self, api_client=None):
        """Initialize service with optional API client for data fetching"""
        self.api_client = api_client
        
    # DEPUTADO OPERATIONS
    def get_or_fetch_deputado(self, deputado_id: int, force_update: bool = False) -> Optional[Deputado]:
        """Get deputado from DB or fetch from API if not exists/outdated"""
        with get_db_session() as session:
            deputado = session.query(Deputado).filter(Deputado.id == deputado_id).first()
            
            # Check if we need to fetch/update from API
            needs_update = (
                deputado is None or 
                force_update or 
                self._is_deputado_outdated(session, deputado_id)
            )
            
            if needs_update and self.api_client:
                logger.info(f"Fetching deputado {deputado_id} from API")
                api_data = self.api_client._fazer_requisicao(f"/deputados/{deputado_id}")
                
                if api_data and api_data.get('dados'):
                    deputado_data = api_data['dados']
                    deputado = self._upsert_deputado(session, deputado_data)
                    self._update_cache_status(session, f"deputado_{deputado_id}", "deputado")
            
            return deputado
    
    def search_deputados(self, nome: str = None, partido: str = None, uf: str = None, 
                        limit: int = 50) -> List[Dict]:
        """Search deputados in database with filters"""
        with get_db_session() as session:
            query = session.query(Deputado)
            
            if nome:
                query = query.filter(
                    or_(
                        Deputado.nome_parlamentar.ilike(f"%{nome}%"),
                        Deputado.nome_civil.ilike(f"%{nome}%")
                    )
                )
            
            if partido:
                query = query.filter(Deputado.sigla_partido == partido.upper())
                
            if uf:
                query = query.filter(Deputado.sigla_uf == uf.upper())
            
            deputados = query.limit(limit).all()
            
            # Convert to dictionary format to avoid session issues
            return [
                {
                    "id": dep.id,
                    "nome_parlamentar": dep.nome_parlamentar,
                    "nome_civil": dep.nome_civil,
                    "sigla_partido": dep.sigla_partido,
                    "sigla_uf": dep.sigla_uf,
                    "situacao": dep.situacao,
                    "email": dep.email,
                    "telefone": dep.telefone,
                    "atualizado_em": dep.atualizado_em.isoformat() if dep.atualizado_em else None
                }
                for dep in deputados
            ]
    
    def _upsert_deputado(self, session: Session, deputado_data: Dict) -> Deputado:
        """Insert or update deputado data"""
        deputado_id = deputado_data.get('id')
        existing = session.query(Deputado).filter(Deputado.id == deputado_id).first()
        
        # Extract relevant fields - handle both search and detail API formats
        ultimo_status = deputado_data.get('ultimoStatus', {})
        
        # Handle different API response formats
        nome_parlamentar = (
            deputado_data.get('nome') or  # From search API
            ultimo_status.get('nome', '')  # From detail API
        )
        
        sigla_partido = (
            deputado_data.get('siglaPartido') or  # From search API
            ultimo_status.get('siglaPartido', '')  # From detail API
        )
        
        sigla_uf = (
            deputado_data.get('siglaUf') or  # From search API
            ultimo_status.get('siglaUf', '')  # From detail API
        )
        
        email = (
            deputado_data.get('email') or  # From search API
            ultimo_status.get('email', '')  # From detail API
        )
        
        data = {
            'id': deputado_id,
            'nome_civil': deputado_data.get('nomeCivil', ''),
            'nome_parlamentar': nome_parlamentar,
            'sigla_partido': sigla_partido,
            'sigla_uf': sigla_uf,
            'situacao': ultimo_status.get('situacao', ''),
            'data_nascimento': deputado_data.get('dataNascimento', ''),
            'escolaridade': deputado_data.get('escolaridade', ''),
            'email': email,
            'telefone': ultimo_status.get('telefone', ''),
            'dados_completos': deputado_data,
            'atualizado_em': datetime.utcnow()
        }
        
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            deputado = existing
        else:
            deputado = Deputado(**data)
            session.add(deputado)
        
        session.commit()
        return deputado
    
    # PROPOSIÇÃO OPERATIONS
    def get_or_fetch_proposicao(self, tipo: str, numero: int, ano: int, 
                               force_update: bool = False) -> Optional[Proposicao]:
        """Get proposição from DB or fetch from API"""
        with get_db_session() as session:
            proposicao = session.query(Proposicao).filter(
                and_(
                    Proposicao.tipo == tipo,
                    Proposicao.numero == numero,
                    Proposicao.ano == ano
                )
            ).first()
            
            # Check if we need to fetch from API
            cache_key = f"proposicao_{tipo}_{numero}_{ano}"
            needs_update = (
                proposicao is None or 
                force_update or 
                self._is_cache_expired(session, cache_key)
            )
            
            if needs_update and self.api_client:
                logger.info(f"Fetching proposição {tipo} {numero}/{ano} from API")
                api_data = self.api_client.buscar_proposicao(tipo, numero, ano)
                
                if api_data:
                    proposicao = self._upsert_proposicao(session, api_data)
                    self._update_cache_status(session, cache_key, "proposicao")
            
            return proposicao
    
    def _upsert_proposicao(self, session: Session, proposicao_data: Dict) -> Proposicao:
        """Insert or update proposição data"""
        proposicao_id = proposicao_data.get('id')
        existing = session.query(Proposicao).filter(Proposicao.id == proposicao_id).first()
        
        data = {
            'id': proposicao_id,
            'tipo': proposicao_data.get('siglaTipo', ''),
            'numero': proposicao_data.get('numero', 0),
            'ano': proposicao_data.get('ano', 0),
            'ementa': proposicao_data.get('ementa', ''),
            'titulo': proposicao_data.get('ementa', ''),  # Use ementa as titulo if no specific titulo
            'uri': proposicao_data.get('uri', ''),
            'dados_completos': proposicao_data,
            'atualizado_em': datetime.utcnow()
        }
        
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            proposicao = existing
        else:
            proposicao = Proposicao(**data)
            session.add(proposicao)
        
        session.commit()
        return proposicao
    
    # VOTAÇÃO OPERATIONS
    def get_or_fetch_votacoes(self, proposicao_id: int, force_update: bool = False) -> List[Votacao]:
        """Get votações from DB or fetch from API"""
        with get_db_session() as session:
            votacoes = session.query(Votacao).filter(
                Votacao.proposicao_id == proposicao_id
            ).all()
            
            # Check if we need to fetch from API
            cache_key = f"votacoes_{proposicao_id}"
            needs_update = (
                not votacoes or 
                force_update or 
                self._is_cache_expired(session, cache_key)
            )
            
            if needs_update and self.api_client:
                logger.info(f"Fetching votações for proposição {proposicao_id} from API")
                api_data = self.api_client.buscar_votacoes_proposicao(proposicao_id)
                
                if api_data:
                    votacoes = self._upsert_votacoes(session, proposicao_id, api_data)
                    self._update_cache_status(session, cache_key, "votacoes")
            
            return votacoes
    
    def _upsert_votacoes(self, session: Session, proposicao_id: int, votacoes_data: List[Dict]) -> List[Votacao]:
        """Insert or update votações data"""
        votacoes = []
        
        for votacao_data in votacoes_data:
            votacao_id = votacao_data.get('id')
            existing = session.query(Votacao).filter(Votacao.id == votacao_id).first()
            
            # Parse datetime fields
            data_hora_registro = None
            if votacao_data.get('dataHoraRegistro'):
                try:
                    data_hora_registro = datetime.fromisoformat(
                        votacao_data['dataHoraRegistro'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            data = {
                'id': votacao_id,
                'proposicao_id': proposicao_id,
                'data_hora_registro': data_hora_registro,
                'descricao': votacao_data.get('descricao', ''),
                'sigla_orgao': votacao_data.get('siglaOrgao', ''),
                'uri_orgao': votacao_data.get('uriOrgao', ''),
                'aprovacao': votacao_data.get('aprovacao', False),
                'dados_completos': votacao_data,
                'atualizado_em': datetime.utcnow()
            }
            
            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
                votacao = existing
            else:
                votacao = Votacao(**data)
                session.add(votacao)
            
            votacoes.append(votacao)
        
        session.commit()
        return votacoes
    
    # VOTO OPERATIONS
    def get_or_fetch_votos(self, votacao_id: str, force_update: bool = False) -> List[Voto]:
        """Get votos from DB or fetch from API"""
        with get_db_session() as session:
            votos = session.query(Voto).filter(Voto.votacao_id == votacao_id).all()
            
            # Check if we need to fetch from API
            cache_key = f"votos_{votacao_id}"
            needs_update = (
                not votos or 
                force_update or 
                self._is_cache_expired(session, cache_key)
            )
            
            if needs_update and self.api_client:
                logger.info(f"Fetching votos for votação {votacao_id} from API")
                api_data = self.api_client.buscar_votos_votacao(votacao_id)
                
                if api_data:
                    votos = self._upsert_votos(session, votacao_id, api_data)
                    self._update_cache_status(session, cache_key, "votos")
            
            return votos
    
    def _upsert_votos(self, session: Session, votacao_id: str, votos_data: List[Dict]) -> List[Voto]:
        """Insert or update votos data"""
        votos = []
        
        for voto_data in votos_data:
            deputado_data = voto_data.get('deputado_', {})
            deputado_id = deputado_data.get('id')
            tipo_voto = voto_data.get('tipoVoto', '')
            
            if not deputado_id:
                continue
            
            # Ensure deputado exists
            self._upsert_deputado(session, deputado_data)
            
            # Check if voto already exists
            existing = session.query(Voto).filter(
                and_(
                    Voto.deputado_id == deputado_id,
                    Voto.votacao_id == votacao_id
                )
            ).first()
            
            data = {
                'deputado_id': deputado_id,
                'votacao_id': votacao_id,
                'tipo_voto': tipo_voto,
                'dados_completos': voto_data
            }
            
            if existing:
                existing.tipo_voto = tipo_voto
                existing.dados_completos = voto_data
                voto = existing
            else:
                voto = Voto(**data)
                session.add(voto)
            
            votos.append(voto)
        
        session.commit()
        return votos
    
    # CACHE MANAGEMENT
    def _is_deputado_outdated(self, session: Session, deputado_id: int, max_age_days: int = 7) -> bool:
        """Check if deputado data is outdated"""
        deputado = session.query(Deputado).filter(Deputado.id == deputado_id).first()
        if not deputado:
            return True
            
        age_limit = datetime.utcnow() - timedelta(days=max_age_days)
        return deputado.atualizado_em < age_limit
    
    def _is_cache_expired(self, session: Session, cache_key: str, default_ttl_hours: int = 24) -> bool:
        """Check if cache entry is expired"""
        cache_entry = session.query(CacheStatus).filter(CacheStatus.chave == cache_key).first()
        
        if not cache_entry:
            return True
            
        if cache_entry.expira_em and cache_entry.expira_em < datetime.utcnow():
            return True
            
        # Fallback to default TTL
        age_limit = datetime.utcnow() - timedelta(hours=default_ttl_hours)
        return cache_entry.ultima_atualizacao < age_limit
    
    def _update_cache_status(self, session: Session, cache_key: str, tipo: str, ttl_hours: int = 24):
        """Update cache status entry"""
        cache_entry = session.query(CacheStatus).filter(CacheStatus.chave == cache_key).first()
        
        now = datetime.utcnow()
        expira_em = now + timedelta(hours=ttl_hours)
        
        if cache_entry:
            cache_entry.ultima_atualizacao = now
            cache_entry.expira_em = expira_em
            cache_entry.status = 'ativo'
        else:
            cache_entry = CacheStatus(
                chave=cache_key,
                tipo=tipo,
                ultima_atualizacao=now,
                expira_em=expira_em,
                status='ativo'
            )
            session.add(cache_entry)
        
        session.commit()
    
    # ANALYSIS OPERATIONS
    def save_deputado_analysis(self, deputado_id: int, analise_data: Dict) -> AnaliseDeputado:
        """Save processed deputado analysis"""
        with get_db_session() as session:
            # Remove old analysis for this deputado
            session.query(AnaliseDeputado).filter(
                AnaliseDeputado.deputado_id == deputado_id
            ).delete()
            
            # Extract statistics
            stats = analise_data.get('estatisticas', {})
            
            analise = AnaliseDeputado(
                deputado_id=deputado_id,
                total_votacoes=stats.get('participacao', 0),
                presenca_percentual=stats.get('presenca_percentual', 0),
                votos_favoraveis=stats.get('votos_favoraveis', 0),
                votos_contrarios=stats.get('votos_contrarios', 0),
                proposicoes_analisadas=stats.get('total_votacoes_analisadas', 0),
                analise_completa=analise_data
            )
            
            session.add(analise)
            session.commit()
            return analise
    
    def get_deputado_analysis(self, deputado_id: int, max_age_days: int = 1) -> Optional[AnaliseDeputado]:
        """Get cached deputado analysis if not too old"""
        with get_db_session() as session:
            age_limit = datetime.utcnow() - timedelta(days=max_age_days)
            
            return session.query(AnaliseDeputado).filter(
                and_(
                    AnaliseDeputado.deputado_id == deputado_id,
                    AnaliseDeputado.data_analise > age_limit
                )
            ).order_by(desc(AnaliseDeputado.data_analise)).first()
    
    # UTILITY METHODS
    def get_database_stats(self) -> Dict:
        """Get database statistics"""
        with get_db_session() as session:
            return {
                'deputados': session.query(Deputado).count(),
                'proposicoes': session.query(Proposicao).count(),
                'votacoes': session.query(Votacao).count(),
                'votos': session.query(Voto).count(),
                'analises': session.query(AnaliseDeputado).count(),
                'cache_entries': session.query(CacheStatus).count()
            }
    
    def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        with get_db_session() as session:
            now = datetime.utcnow()
            
            # Mark expired entries
            expired_count = session.query(CacheStatus).filter(
                CacheStatus.expira_em < now
            ).update({'status': 'expirado'})
            
            # Clean up very old entries (30+ days)
            old_date = now - timedelta(days=30)
            deleted_count = session.query(CacheStatus).filter(
                CacheStatus.ultima_atualizacao < old_date
            ).delete()
            
            session.commit()
            
            logger.info(f"Cache cleanup: {expired_count} expired, {deleted_count} deleted")
            return expired_count, deleted_count
    
    def get_deputado_voting_history(self, deputado_id: int, limit: int = 50) -> List[Dict]:
        """Get deputado voting history from database"""
        with get_db_session() as session:
            # Get all votes for this deputy with related votacao and proposicao data
            votos_query = (
                session.query(Voto, Votacao, Proposicao)
                .join(Votacao, Voto.votacao_id == Votacao.id)
                .join(Proposicao, Votacao.proposicao_id == Proposicao.id)
                .filter(Voto.deputado_id == deputado_id)
                .order_by(desc(Votacao.data_hora_registro))
                .limit(limit)
            )
            
            voting_history = []
            for voto, votacao, proposicao in votos_query.all():
                # Format the data similar to the API response
                vote_data = {
                    "id": voto.votacao_id,
                    "data": votacao.data_hora_registro.isoformat() if votacao.data_hora_registro else "",
                    "dataHoraRegistro": votacao.data_hora_registro.isoformat() if votacao.data_hora_registro else "",
                    "siglaOrgao": votacao.sigla_orgao or "",
                    "uriOrgao": votacao.uri_orgao or "",
                    "voto": voto.tipo_voto,
                    "proposicao": {
                        "id": proposicao.id,
                        "uri": proposicao.uri or f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{proposicao.id}",
                        "siglaTipo": proposicao.tipo,
                        "numero": str(proposicao.numero),
                        "ano": str(proposicao.ano),
                        "ementa": proposicao.ementa or ""
                    }
                }
                voting_history.append(vote_data)
            
            return voting_history
    
    def save_deputado_analysis(self, deputado_id: int, analise_data: Dict) -> AnaliseDeputado:
        """Save or update deputado analysis in database"""
        with get_db_session() as session:
            # Check if analysis already exists
            existing = session.query(AnaliseDeputado).filter(
                AnaliseDeputado.deputado_id == deputado_id
            ).first()
            
            # Extract statistics from analysis
            stats = analise_data.get('estatisticas', {})
            
            analysis_data = {
                'deputado_id': deputado_id,
                'data_analise': datetime.utcnow(),
                'total_votacoes': stats.get('participacao', 0),
                'presenca_percentual': int(stats.get('presenca_percentual', 0)),
                'votos_favoraveis': stats.get('votos_favoraveis', 0),
                'votos_contrarios': stats.get('votos_contrarios', 0),
                'abstencoes': stats.get('abstencoes', 0),
                'obstrucoes': stats.get('obstrucoes', 0),
                'analise_completa': analise_data,
                'proposicoes_analisadas': len(analise_data.get('historico_votacoes', []))
            }
            
            if existing:
                # Update existing analysis
                for key, value in analysis_data.items():
                    setattr(existing, key, value)
                analise = existing
            else:
                # Create new analysis
                analise = AnaliseDeputado(**analysis_data)
                session.add(analise)
            
            session.commit()
            return analise