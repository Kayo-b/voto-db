"""
Automatic proposition monitoring and synchronization service.

Syncs with Câmara API to:
- discover newly presented propositions
- discover propositions currently in voting flow (via recent votacoes)
- persist proposition + voting data for incremental growth
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging
import requests

from sqlalchemy import case, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .connection import SessionLocal
from .model import Proposicao, Votacao
from .recent_votacoes_service import RecentVotacoesService

logger = logging.getLogger(__name__)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"


class ProposicaoMonitorService:
    """Sync and stats service for proposition monitoring."""

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session or SessionLocal()
        self._should_close = db_session is None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._should_close:
            self.db.close()

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None, timeout: int = 20) -> Optional[Dict[str, Any]]:
        try:
            response = requests.get(f"{CAMARA_BASE_URL}{path}", params=params, timeout=timeout)
            if response.status_code != 200:
                return None
            return response.json()
        except Exception as exc:
            logger.warning("Request failed for %s: %s", path, exc)
            return None

    def _build_codigo(self, tipo: Optional[str], numero: Optional[Any], ano: Optional[Any], proposicao_id: Any) -> str:
        if tipo and numero and ano:
            return f"{tipo} {numero}/{ano}"
        return f"PROP {proposicao_id}"

    def _upsert_proposicao(self, raw_prop: Dict[str, Any], source: str = "sync") -> Optional[Proposicao]:
        prop_id = raw_prop.get("id")
        if not prop_id:
            return None

        tipo = raw_prop.get("siglaTipo") or raw_prop.get("tipo") or ""
        numero = str(raw_prop.get("numero") or "")
        ano_raw = raw_prop.get("ano")
        try:
            ano = int(ano_raw) if ano_raw is not None else None
        except Exception:
            ano = None

        ementa = raw_prop.get("ementa") or raw_prop.get("descricao") or ""
        titulo = (raw_prop.get("ementa") or raw_prop.get("titulo") or raw_prop.get("descricao") or "").strip()
        if not titulo:
            titulo = self._build_codigo(tipo, numero, ano, prop_id)

        codigo = self._build_codigo(tipo, numero, ano, prop_id)
        uri = raw_prop.get("uri") or f"{CAMARA_BASE_URL}/proposicoes/{prop_id}"

        existing = self.db.query(Proposicao).filter(Proposicao.id == int(prop_id)).first()
        if existing:
            existing.codigo = codigo
            existing.titulo = titulo
            existing.ementa = ementa
            existing.tipo = tipo
            existing.numero = numero
            existing.ano = ano
            existing.uri = uri
            if not existing.relevancia:
                existing.relevancia = "baixa"
            logger.debug("Updated proposicao %s from %s", prop_id, source)
            return existing

        proposicao = Proposicao(
            id=int(prop_id),
            codigo=codigo,
            titulo=titulo,
            ementa=ementa,
            tipo=tipo,
            numero=numero,
            ano=ano,
            uri=uri,
            relevancia="baixa"
        )
        self.db.add(proposicao)
        # Flush so repeated upserts in the same transaction can see this row.
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            existing_after_conflict = self.db.query(Proposicao).filter(Proposicao.id == int(prop_id)).first()
            if existing_after_conflict:
                existing_after_conflict.codigo = codigo
                existing_after_conflict.titulo = titulo
                existing_after_conflict.ementa = ementa
                existing_after_conflict.tipo = tipo
                existing_after_conflict.numero = numero
                existing_after_conflict.ano = ano
                existing_after_conflict.uri = uri
                return existing_after_conflict
            raise
        logger.info("Created proposicao %s from %s", prop_id, source)
        return proposicao

    def sync_monitoring_data(self, dias_novas: int = 15, dias_votacoes: int = 15) -> Dict[str, Any]:
        """
        Sync propositions from API and persist into local DB.
        """
        now = datetime.now()
        data_inicio_novas = (now - timedelta(days=dias_novas)).strftime("%Y-%m-%d")
        data_inicio_votacoes = (now - timedelta(days=dias_votacoes)).strftime("%Y-%m-%d")
        data_fim = now.strftime("%Y-%m-%d")

        result = {
            "novas_encontradas": 0,
            "proposicoes_upsert": 0,
            "votacoes_processadas": 0,
            "votos_processados": 0,
            "erros": 0,
            "executado_em": now.isoformat()
        }

        recent_service = RecentVotacoesService(self.db)

        # 1) Newly presented propositions
        novas = self._request(
            "/proposicoes",
            params={
                "dataInicio": data_inicio_novas,
                "dataFim": data_fim,
                "ordem": "DESC",
                "ordenarPor": "dataApresentacao",
                "itens": 100,
                "pagina": 1,
            },
        ) or {}

        for raw_prop in novas.get("dados", []):
            try:
                result["novas_encontradas"] += 1
                existing_before = self.db.query(Proposicao).filter(Proposicao.id == int(raw_prop.get("id", 0))).first()
                self._upsert_proposicao(raw_prop, source="novas")
                if existing_before is None:
                    result["proposicoes_upsert"] += 1
            except Exception:
                result["erros"] += 1

        # 2) Propositions in current voting flow (derived from recent votacoes)
        votacoes = self._request(
            "/votacoes",
            params={
                "dataInicio": data_inicio_votacoes,
                "dataFim": data_fim,
                "ordem": "DESC",
                "ordenarPor": "dataHoraRegistro",
                "itens": 100,
                "pagina": 1,
            },
            timeout=30,
        ) or {}

        for votacao in votacoes.get("dados", []):
            votacao_id = str(votacao.get("id") or "")
            if not votacao_id:
                continue

            try:
                detalhes = self._request(f"/votacoes/{votacao_id}", timeout=15)
                if not detalhes:
                    continue

                detalhes_dados = detalhes.get("dados", {})
                proposicoes_afetadas = detalhes_dados.get("proposicoesAfetadas") or []
                if not proposicoes_afetadas:
                    continue

                result["votacoes_processadas"] += 1

                # Use first linked proposition as the principal one for votacao storage.
                principal = proposicoes_afetadas[0]
                prop_id = principal.get("id")
                prop_details = self._request(f"/proposicoes/{prop_id}") if prop_id else None
                prop_raw = prop_details.get("dados", principal) if prop_details else principal
                self._upsert_proposicao(prop_raw, source="votacao")

                descricao = ((votacao.get("descricao") or "") + " " + (detalhes_dados.get("descricao") or "")).lower()
                ultima_desc = (detalhes_dados.get("descUltimaAberturaVotacao") or "").lower()
                is_urgencia = (
                    "urgência" in descricao
                    or "urgencia" in descricao
                    or "urgência" in ultima_desc
                    or "urgencia" in ultima_desc
                )
                tipo_votacao = "urgencia" if is_urgencia else "nominal"

                recent_service.store_votacao_from_api(
                    {
                        "id": votacao_id,
                        "dataHoraRegistro": votacao.get("dataHoraRegistro", votacao.get("data")),
                        "descricao": detalhes_dados.get("descricao", votacao.get("descricao", "")),
                        "siglaOrgao": votacao.get("siglaOrgao", detalhes_dados.get("siglaOrgao", "")),
                        "resultado": detalhes_dados.get("descResultado", ""),
                        "aprovacao": detalhes_dados.get("aprovacao"),
                        "tipo_votacao": tipo_votacao,
                        "proposicao": {
                            "id": principal.get("id"),
                            "siglaTipo": principal.get("siglaTipo"),
                            "numero": principal.get("numero"),
                            "ano": principal.get("ano"),
                            "ementa": principal.get("ementa", ""),
                        },
                    }
                )

                # Try to persist individual votes too, for richer stats.
                votos_resp = self._request(f"/votacoes/{votacao_id}/votos", timeout=20)
                votos = (votos_resp or {}).get("dados", [])
                if votos:
                    votos_result = recent_service.store_votos_for_votacao(votacao_id, votos)
                    result["votos_processados"] += votos_result.get("votos_stored", 0)

            except Exception:
                result["erros"] += 1

        self.db.commit()
        return result

    def get_monitored_proposicoes(self, relevancia: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """
        Returns propositions with aggregated voting stats from local DB.
        """
        seven_days_ago = datetime.now() - timedelta(days=7)

        nominal_case = case((Votacao.tipo_votacao == "nominal", 1), else_=0)
        recent_case = case((Votacao.data_votacao >= seven_days_ago, 1), else_=0)

        stats_subquery = (
            self.db.query(
                Votacao.proposicao_id.label("proposicao_id"),
                func.count(Votacao.id).label("total_votacoes"),
                func.coalesce(func.sum(nominal_case), 0).label("votacoes_nominais"),
                func.max(Votacao.data_votacao).label("ultima_votacao"),
                func.coalesce(func.sum(recent_case), 0).label("votacoes_7d"),
            )
            .filter(Votacao.proposicao_id.isnot(None))
            .group_by(Votacao.proposicao_id)
            .subquery()
        )

        query = (
            self.db.query(
                Proposicao,
                stats_subquery.c.total_votacoes,
                stats_subquery.c.votacoes_nominais,
                stats_subquery.c.ultima_votacao,
                stats_subquery.c.votacoes_7d,
            )
            .outerjoin(stats_subquery, Proposicao.id == stats_subquery.c.proposicao_id)
        )

        if relevancia:
            query = query.filter(Proposicao.relevancia == relevancia)

        rows = query.order_by(Proposicao.updated_at.desc()).limit(limit).all()

        result: List[Dict[str, Any]] = []
        for row in rows:
            proposicao, total_votacoes_raw, votacoes_nominais_raw, ultima_votacao, votacoes_7d_raw = row

            total_votacoes = int(total_votacoes_raw or 0)
            votacoes_nominais = int(votacoes_nominais_raw or 0)
            votacoes_7d = int(votacoes_7d_raw or 0)
            em_votacao = votacoes_7d > 0

            result.append(
                {
                    "id": proposicao.id,
                    "codigo": proposicao.codigo,
                    "tipo": proposicao.tipo,
                    "numero": proposicao.numero,
                    "ano": proposicao.ano,
                    "titulo": proposicao.titulo,
                    "ementa": proposicao.ementa,
                    "relevancia": proposicao.relevancia,
                    "uri": proposicao.uri,
                    "status": "Em votação" if em_votacao else "Sem votação recente",
                    "em_votacao": em_votacao,
                    "stats": {
                        "total_votacoes": total_votacoes,
                        "votacoes_nominais": votacoes_nominais,
                        "ultima_votacao": ultima_votacao.isoformat() if ultima_votacao else None,
                    },
                    "updated_at": proposicao.updated_at.isoformat() if proposicao.updated_at else None,
                }
            )

        return result


def run_monitor_sync_once() -> Dict[str, Any]:
    """Convenience function to run one sync cycle."""
    with ProposicaoMonitorService() as service:
        return service.sync_monitoring_data()


def get_monitored_proposicoes(relevancia: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    """Convenience function to list monitored propositions with stats."""
    with ProposicaoMonitorService() as service:
        return service.get_monitored_proposicoes(relevancia=relevancia, limit=limit)
