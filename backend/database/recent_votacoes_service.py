"""
Service for caching and retrieving recent votacoes from the Chamber of Deputies API.
Stores votacoes and individual votos in the database for quick retrieval.
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from .connection import SessionLocal
from .model import Proposicao, Votacao, Voto, Deputado, Partido, Legislatura

logger = logging.getLogger(__name__)


class RecentVotacoesService:
    """Service for caching and retrieving recent votacoes"""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self._should_close = db_session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close:
            self.db.close()

    def get_votacao_by_api_id(self, api_votacao_id: str) -> Optional[Votacao]:
        """
        Get a votacao by its Chamber API ID.
        Returns None if not found.
        """
        return self.db.query(Votacao).filter(
            Votacao.api_votacao_id == str(api_votacao_id)
        ).first()

    def store_votacao_from_api(self, votacao_data: Dict[str, Any]) -> Votacao:
        """
        Store a votacao from API response.
        Creates or updates the votacao in the database.
        Returns the votacao object.
        """
        api_id = str(votacao_data.get('id', ''))
        if not api_id:
            raise ValueError("Votacao must have an ID")

        # Check if already exists
        existing = self.get_votacao_by_api_id(api_id)
        if existing:
            # Update existing votacao with any new data
            existing.descricao = votacao_data.get('descricao', existing.descricao)
            existing.tipo_votacao = votacao_data.get('tipo_votacao', existing.tipo_votacao)
            existing.sigla_orgao = votacao_data.get('siglaOrgao', existing.sigla_orgao)
            existing.aprovacao = votacao_data.get('aprovacao', existing.aprovacao)
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Parse date
        data_str = votacao_data.get('dataHoraRegistro', votacao_data.get('data', ''))
        try:
            if 'T' in str(data_str):
                data_votacao = datetime.fromisoformat(str(data_str).replace('Z', '+00:00'))
            else:
                data_votacao = datetime.strptime(str(data_str)[:19], '%Y-%m-%d %H:%M:%S')
        except:
            data_votacao = datetime.now()

        # Handle proposicao if present
        proposicao_id = None
        proposicao_data = votacao_data.get('proposicao')
        if proposicao_data:
            prop_id = proposicao_data.get('id') or proposicao_data.get('codProposicao')
            if prop_id:
                proposicao_id = self._ensure_proposicao_exists(proposicao_data)

        # Determine tipo_votacao
        tipo_votacao = votacao_data.get('tipo_votacao')
        if not tipo_votacao:
            # Try to infer from regimeUrgencia flag
            if votacao_data.get('regimeUrgencia'):
                tipo_votacao = 'urgencia'
            elif proposicao_data:
                tipo_votacao = 'nominal'

        # Create new votacao
        votacao = Votacao(
            api_votacao_id=api_id,
            proposicao_id=proposicao_id,
            data_votacao=data_votacao,
            descricao=votacao_data.get('descricao', ''),
            resultado=votacao_data.get('resultado', ''),
            tipo_votacao=tipo_votacao,
            sigla_orgao=votacao_data.get('siglaOrgao', ''),
            aprovacao=votacao_data.get('aprovacao')
        )

        self.db.add(votacao)
        self.db.commit()
        self.db.refresh(votacao)

        logger.info(f"Created votacao with api_id {api_id}")
        return votacao

    def _ensure_proposicao_exists(self, proposicao_data: Dict[str, Any]) -> Optional[int]:
        """
        Ensure a proposicao exists in the database.
        Creates a minimal record if it doesn't exist.
        Returns the proposicao ID.
        """
        prop_id = proposicao_data.get('id') or proposicao_data.get('codProposicao')
        if not prop_id:
            return None

        # Check if exists
        existing = self.db.query(Proposicao).filter(Proposicao.id == prop_id).first()
        if existing:
            return existing.id

        # Create minimal proposicao record
        tipo = proposicao_data.get('siglaTipo', proposicao_data.get('codTipo', ''))
        numero = str(proposicao_data.get('numero', ''))
        ano = proposicao_data.get('ano', datetime.now().year)

        proposicao = Proposicao(
            id=prop_id,
            codigo=f"{tipo} {numero}/{ano}".strip(),
            titulo=proposicao_data.get('ementa', '')[:500] if proposicao_data.get('ementa') else f"{tipo} {numero}/{ano}",
            ementa=proposicao_data.get('ementa', ''),
            tipo=tipo,
            numero=numero,
            ano=ano,
            uri=proposicao_data.get('uri', f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{prop_id}"),
            relevancia='media'
        )

        self.db.add(proposicao)
        self.db.commit()
        self.db.refresh(proposicao)

        logger.info(f"Created proposicao {proposicao.codigo}")
        return proposicao.id

    def ensure_deputado_exists(self, deputado_data: Dict[str, Any]) -> Optional[int]:
        """
        Ensure a deputado exists in the database.
        Creates a minimal record if it doesn't exist.
        Returns the deputado ID.
        """
        deputado_id = deputado_data.get('id')
        if not deputado_id:
            return None

        # Check if exists
        existing = self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
        if existing:
            return existing.id

        # Ensure partido exists
        partido_sigla = deputado_data.get('siglaPartido', 'S/P')
        partido = self.db.query(Partido).filter(Partido.sigla == partido_sigla).first()
        if not partido:
            partido = Partido(sigla=partido_sigla, nome=partido_sigla)
            self.db.add(partido)
            self.db.commit()
            self.db.refresh(partido)
            logger.info(f"Created partido {partido_sigla}")

        # Ensure legislatura exists (use default 57 for current)
        legislatura_num = 57
        legislatura = self.db.query(Legislatura).filter(Legislatura.numero == legislatura_num).first()
        if not legislatura:
            legislatura = Legislatura(numero=legislatura_num)
            self.db.add(legislatura)
            self.db.commit()
            self.db.refresh(legislatura)
            logger.info(f"Created legislatura {legislatura_num}")

        # Create minimal deputado record
        deputado = Deputado(
            id=deputado_id,
            nome=deputado_data.get('nome', f'Deputado {deputado_id}'),
            nome_parlamentar=deputado_data.get('nome', f'Deputado {deputado_id}'),
            sigla_uf=deputado_data.get('siglaUf', 'XX'),
            partido_id=partido.id,
            legislatura_id=legislatura.id,
            uri=deputado_data.get('uri', f"https://dadosabertos.camara.leg.br/api/v2/deputados/{deputado_id}")
        )

        self.db.add(deputado)
        self.db.commit()
        self.db.refresh(deputado)

        logger.info(f"Created deputado {deputado.nome}")
        return deputado.id

    def store_votos_for_votacao(self, api_votacao_id: str, votos: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Store individual votes for a votacao.
        Creates deputados if they don't exist.
        Returns statistics about the import.
        """
        result = {
            'votacao_api_id': api_votacao_id,
            'votos_stored': 0,
            'votos_skipped': 0,
            'deputados_created': 0,
            'errors': []
        }

        # Get the votacao
        votacao = self.get_votacao_by_api_id(api_votacao_id)
        if not votacao:
            result['errors'].append(f"Votacao {api_votacao_id} not found in database")
            return result

        for voto_data in votos:
            try:
                deputado_info = voto_data.get('deputado_', voto_data.get('deputado', {}))
                deputado_id = deputado_info.get('id')
                tipo_voto = voto_data.get('tipoVoto', voto_data.get('voto', ''))

                if not deputado_id or not tipo_voto:
                    result['votos_skipped'] += 1
                    continue

                # Ensure deputado exists
                existing_deputado = self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
                if not existing_deputado:
                    self.ensure_deputado_exists(deputado_info)
                    result['deputados_created'] += 1

                # Check if vote already exists
                existing_voto = self.db.query(Voto).filter(
                    Voto.deputado_id == deputado_id,
                    Voto.votacao_id == votacao.id
                ).first()

                if existing_voto:
                    result['votos_skipped'] += 1
                    continue

                # Create vote
                voto = Voto(
                    deputado_id=deputado_id,
                    votacao_id=votacao.id,
                    voto=tipo_voto
                )
                self.db.add(voto)
                result['votos_stored'] += 1

            except Exception as e:
                result['votos_skipped'] += 1
                result['errors'].append(f"Error storing vote: {str(e)}")

        self.db.commit()
        logger.info(f"Stored {result['votos_stored']} votes for votacao {api_votacao_id}")
        return result

    def get_stored_votos(self, api_votacao_id: str) -> List[Dict[str, Any]]:
        """
        Get stored votes for a votacao.
        Returns votes in the same format as the API response.
        """
        votacao = self.get_votacao_by_api_id(api_votacao_id)
        if not votacao:
            return []

        votos = self.db.query(Voto).filter(Voto.votacao_id == votacao.id).all()

        votos_data = []
        for voto in votos:
            deputado = voto.deputado
            votos_data.append({
                "deputado": {
                    "id": deputado.id,
                    "nome": deputado.nome,
                    "siglaPartido": deputado.partido.sigla if deputado.partido else '',
                    "siglaUf": deputado.sigla_uf
                },
                "voto": voto.voto
            })

        return votos_data

    def has_stored_votos(self, api_votacao_id: str) -> bool:
        """Check if we have stored votes for a votacao."""
        votacao = self.get_votacao_by_api_id(api_votacao_id)
        if not votacao:
            return False

        count = self.db.query(Voto).filter(Voto.votacao_id == votacao.id).count()
        return count > 0

    def get_deputado_stored_votes(self, deputado_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get a deputy's votes from stored recent votacoes.
        Returns votes with votacao and proposicao details.
        """
        votos = self.db.query(Voto).join(Votacao).filter(
            Voto.deputado_id == deputado_id,
            Votacao.api_votacao_id.isnot(None)  # Only recent votacoes with API ID
        ).order_by(desc(Votacao.data_votacao)).limit(limit).all()

        result = []
        for voto in votos:
            votacao = voto.votacao
            proposicao = votacao.proposicao

            votacao_info = {
                "votacao_id": votacao.api_votacao_id,
                "data": votacao.data_votacao.isoformat() if votacao.data_votacao else '',
                "sigla_orgao": votacao.sigla_orgao or '',
                "tipo_votacao": votacao.tipo_votacao or '',
                "descricao": votacao.descricao or '',
                "aprovacao": votacao.aprovacao,
                "voto": voto.voto,
                "proposicao": None
            }

            if proposicao:
                votacao_info["proposicao"] = {
                    "id": proposicao.id,
                    "codigo": proposicao.codigo,
                    "tipo": proposicao.tipo,
                    "numero": proposicao.numero,
                    "ano": proposicao.ano,
                    "ementa": proposicao.ementa[:200] + "..." if len(proposicao.ementa or "") > 200 else proposicao.ementa
                }

            result.append(votacao_info)

        return result

    def get_recent_votacoes_from_db(self, tipo: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent votacoes from database.
        Filters by tipo if specified.
        Includes vote count for each votacao.
        """
        query = self.db.query(Votacao).filter(
            Votacao.api_votacao_id.isnot(None)
        )

        if tipo and tipo != 'todas':
            if tipo == 'nominais':
                query = query.filter(Votacao.tipo_votacao == 'nominal')
            elif tipo == 'urgencia':
                query = query.filter(Votacao.tipo_votacao == 'urgencia')

        votacoes = query.order_by(desc(Votacao.data_votacao)).limit(limit).all()

        result = []
        for votacao in votacoes:
            proposicao = votacao.proposicao

            # Count stored votes for this votacao
            votos_count = self.db.query(Voto).filter(Voto.votacao_id == votacao.id).count()

            votacao_data = {
                "id": votacao.api_votacao_id,
                "data": votacao.data_votacao.isoformat() if votacao.data_votacao else '',
                "dataHoraRegistro": votacao.data_votacao.isoformat() if votacao.data_votacao else '',
                "descricao": votacao.descricao or '',
                "siglaOrgao": votacao.sigla_orgao or '',
                "tipo_votacao": votacao.tipo_votacao or '',
                "aprovacao": votacao.aprovacao,
                "proposicao": None,
                "votos_count": votos_count  # Include count of stored votes
            }

            if proposicao:
                votacao_data["proposicao"] = {
                    "id": proposicao.id,
                    "siglaTipo": proposicao.tipo,
                    "numero": proposicao.numero,
                    "ano": proposicao.ano,
                    "ementa": proposicao.ementa
                }

            result.append(votacao_data)

        return result


# Convenience functions for use outside the class

def get_votacao_by_api_id(api_votacao_id: str) -> Optional[Votacao]:
    """Get a votacao by its API ID."""
    with RecentVotacoesService() as service:
        return service.get_votacao_by_api_id(api_votacao_id)


def store_votacao_from_api(votacao_data: Dict[str, Any]) -> Votacao:
    """Store a votacao from API response."""
    with RecentVotacoesService() as service:
        return service.store_votacao_from_api(votacao_data)


def store_votos_for_votacao(api_votacao_id: str, votos: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Store votes for a votacao."""
    with RecentVotacoesService() as service:
        return service.store_votos_for_votacao(api_votacao_id, votos)


def get_stored_votos(api_votacao_id: str) -> List[Dict[str, Any]]:
    """Get stored votes for a votacao."""
    with RecentVotacoesService() as service:
        return service.get_stored_votos(api_votacao_id)


def has_stored_votos(api_votacao_id: str) -> bool:
    """Check if votes are stored for a votacao."""
    with RecentVotacoesService() as service:
        return service.has_stored_votos(api_votacao_id)


def get_deputado_stored_votes(deputado_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    """Get a deputy's votes from stored votacoes."""
    with RecentVotacoesService() as service:
        return service.get_deputado_stored_votes(deputado_id, limit)


def ensure_deputado_exists(deputado_data: Dict[str, Any]) -> Optional[int]:
    """Ensure a deputado exists in the database."""
    with RecentVotacoesService() as service:
        return service.ensure_deputado_exists(deputado_data)


def get_recent_votacoes_from_db(tipo: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """Get recent votacoes from database."""
    with RecentVotacoesService() as service:
        return service.get_recent_votacoes_from_db(tipo, limit)
