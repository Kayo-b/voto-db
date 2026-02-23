"""
Twitter/X posting service for new voting events.

This service is intentionally optional and disabled by default.
When enabled, it posts one summary per votacao using a Playwright script.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from .model import CacheMetadata, Votacao, Voto

logger = logging.getLogger(__name__)

TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_MARKER_TTL_DAYS = 3650


class TwitterBotService:
    """Builds and publishes X posts for newly stored votacoes."""

    def __init__(self, db: Session):
        self.db = db
        # backend/database/twitter_bot_service.py -> backend -> repo root
        self.repo_root = Path(__file__).resolve().parents[2]
        self.script_path = self.repo_root / "backend" / "scripts" / "post_to_x_playwright.js"

    def post_votacao_if_needed(self, api_votacao_id: str) -> Dict[str, str]:
        """
        Post a summary for one votacao if all conditions are met.
        Returns a small status payload to aid logging/debugging.
        """
        if not self._enabled():
            return {"status": "disabled"}

        api_votacao_id = str(api_votacao_id or "").strip()
        if not api_votacao_id:
            return {"status": "invalid_votacao_id"}

        votacao = (
            self.db.query(Votacao)
            .filter(Votacao.api_votacao_id == api_votacao_id)
            .first()
        )
        if not votacao:
            return {"status": "not_found"}

        if self._already_posted(api_votacao_id):
            return {"status": "already_posted"}

        if self._is_older_than_limit(votacao):
            return {"status": "skipped_old_vote"}

        post_text = self._build_post_text(votacao)
        if not post_text:
            return {"status": "no_post_text"}

        publish_result = self._publish_with_playwright(post_text)
        if publish_result.get("status") == "posted":
            self._mark_as_posted(api_votacao_id)
        return publish_result

    def _enabled(self) -> bool:
        return os.getenv("TWITTER_BOT_ENABLED", "false").strip().lower() in TRUE_VALUES

    def _marker_key(self, api_votacao_id: str) -> str:
        return f"twitter_post:votacao:{api_votacao_id}"

    def _already_posted(self, api_votacao_id: str) -> bool:
        key = self._marker_key(api_votacao_id)
        marker = (
            self.db.query(CacheMetadata.id)
            .filter(CacheMetadata.cache_key == key)
            .first()
        )
        return marker is not None

    def _mark_as_posted(self, api_votacao_id: str) -> None:
        key = self._marker_key(api_votacao_id)
        if self._already_posted(api_votacao_id):
            return

        marker = CacheMetadata(
            cache_key=key,
            cache_type="twitter_post",
            expires_at=datetime.utcnow() + timedelta(days=DEFAULT_MARKER_TTL_DAYS),
        )
        self.db.add(marker)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            logger.exception("Failed to store twitter post marker for votacao %s", api_votacao_id)

    def _is_older_than_limit(self, votacao: Votacao) -> bool:
        max_age_days_raw = os.getenv("TWITTER_BOT_MAX_VOTACAO_AGE_DAYS", "0").strip()
        if not max_age_days_raw:
            return False

        try:
            max_age_days = int(max_age_days_raw)
        except ValueError:
            return False

        if max_age_days <= 0 or not votacao.data_votacao:
            return False

        vote_dt = votacao.data_votacao.replace(tzinfo=None) if votacao.data_votacao.tzinfo else votacao.data_votacao
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        return vote_dt < cutoff

    def _build_post_text(self, votacao: Votacao) -> Optional[str]:
        votos = (
            self.db.query(Voto)
            .filter(Voto.votacao_id == votacao.id)
            .all()
        )

        if not votos:
            return None

        counts = Counter()
        voter_rows: List[Tuple[str, str]] = []

        for voto in votos:
            label = self._normalize_vote(voto.voto)
            counts[label] += 1
            deputado = voto.deputado
            if deputado:
                voter_rows.append((deputado.nome or f"Dep. {deputado.id}", label))

        voter_rows.sort(key=lambda item: item[0].lower())

        total_votos = sum(counts.values())
        if total_votos == 0:
            return None

        proposicao = votacao.proposicao
        codigo = (
            (proposicao.codigo or "").strip()
            if proposicao and proposicao.codigo
            else f"Votacao {votacao.api_votacao_id}"
        )
        title_source = ""
        if proposicao:
            title_source = proposicao.titulo or proposicao.ementa or ""
        if not title_source:
            title_source = votacao.descricao or "Sem descricao detalhada"
        title_source = self._compact_space(title_source)

        resultado = self._resolve_result(votacao)
        link = f"https://dadosabertos.camara.leg.br/api/v2/votacoes/{votacao.api_votacao_id}"

        max_people = max(1, self._safe_int_env("TWITTER_BOT_MAX_VOTER_PREVIEW", 5))
        include_link = True
        title_limit = 72

        while True:
            title = self._truncate(title_source, title_limit)
            preview = self._build_voter_preview(voter_rows, max_people=max_people)

            parts = [
                f"{codigo}: {title}",
                f"Resultado: {resultado} | Total: {total_votos}",
                (
                    f"Placar: Sim {counts.get('Sim', 0)} | "
                    f"Nao {counts.get('Nao', 0)} | "
                    f"Abs {counts.get('Abstencao', 0)} | "
                    f"Obs {counts.get('Obstrucao', 0)}"
                ),
                f"Quem votou: {preview}",
            ]

            outros = counts.get("Outros", 0)
            if outros > 0:
                parts[2] = f"{parts[2]} | Outros {outros}"

            if include_link:
                parts.append(link)

            text = "\n".join(parts)
            if len(text) <= 280:
                return text

            if max_people > 1:
                max_people -= 1
                continue
            if title_limit > 36:
                title_limit -= 8
                continue
            if include_link:
                include_link = False
                continue

            return self._truncate(text, 280)

    def _publish_with_playwright(self, post_text: str) -> Dict[str, str]:
        if not self.script_path.exists():
            logger.error("Twitter bot script not found: %s", self.script_path)
            return {"status": "error", "message": "bot_script_not_found"}

        runner = os.getenv("TWITTER_BOT_RUNNER", "npx --yes --package=playwright node")
        command = shlex.split(runner) + [str(self.script_path)]

        timeout_seconds = self._safe_int_env("TWITTER_BOT_TIMEOUT_SECONDS", 120)
        env = os.environ.copy()
        env["TWITTER_POST_TEXT"] = post_text
        env.setdefault(
            "TWITTER_STORAGE_STATE_PATH",
            str(self.repo_root / "playwright" / ".auth" / "twitter-bot.json"),
        )
        env.setdefault(
            "TWITTER_BOT_ARTIFACT_DIR",
            str(self.repo_root / "output" / "playwright"),
        )

        try:
            completed = subprocess.run(
                command,
                cwd=str(self.repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError:
            logger.exception("Twitter bot runner not found: %s", runner)
            return {"status": "error", "message": "runner_not_found"}
        except subprocess.TimeoutExpired:
            logger.error("Twitter bot timed out after %ss", timeout_seconds)
            return {"status": "error", "message": "timeout"}
        except Exception:
            logger.exception("Unexpected error running Twitter bot")
            return {"status": "error", "message": "unexpected_runner_error"}

        if completed.returncode != 0:
            stderr_tail = (completed.stderr or "").strip()[-1000:]
            stdout_tail = (completed.stdout or "").strip()[-500:]
            logger.error("Twitter bot failed. stderr=%s stdout=%s", stderr_tail, stdout_tail)
            return {"status": "error", "message": "playwright_post_failed"}

        logger.info("Twitter bot posted votacao summary successfully")
        return {"status": "posted"}

    @staticmethod
    def _normalize_vote(raw_vote: Optional[str]) -> str:
        value = (raw_vote or "").strip().lower()
        if value in {"sim"}:
            return "Sim"
        if value in {"nao", "n\u00e3o"}:
            return "Nao"
        if "abstenc" in value:
            return "Abstencao"
        if "obstr" in value:
            return "Obstrucao"
        if "sim" in value:
            return "Sim"
        if "nao" in value or "n\u00e3o" in value:
            return "Nao"
        return "Outros"

    @staticmethod
    def _resolve_result(votacao: Votacao) -> str:
        if votacao.resultado:
            return TwitterBotService._compact_space(votacao.resultado)
        if votacao.aprovacao is None:
            return "Sem resultado final"
        return "Aprovado" if int(votacao.aprovacao) == 1 else "Rejeitado"

    @staticmethod
    def _short_name(nome: str) -> str:
        cleaned = TwitterBotService._compact_space(nome)
        parts = cleaned.split(" ")
        if len(parts) >= 2:
            candidate = f"{parts[0]} {parts[1]}"
        else:
            candidate = parts[0] if parts else "Deputado"
        return TwitterBotService._truncate(candidate, 18)

    def _build_voter_preview(self, voter_rows: List[Tuple[str, str]], max_people: int = 5) -> str:
        if not voter_rows:
            return "Sem votos individuais"

        entries: List[str] = []
        for nome, voto_label in voter_rows[:max_people]:
            vote_short = {
                "Sim": "S",
                "Nao": "N",
                "Abstencao": "A",
                "Obstrucao": "O",
            }.get(voto_label, "X")
            entries.append(f"{self._short_name(nome)}({vote_short})")

        remaining = len(voter_rows) - len(entries)
        if remaining > 0:
            entries.append(f"+{remaining}")
        return ", ".join(entries)

    @staticmethod
    def _compact_space(value: str) -> str:
        return " ".join((value or "").split()).strip()

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if limit <= 0:
            return ""
        if len(value) <= limit:
            return value
        if limit <= 3:
            return value[:limit]
        return f"{value[: limit - 3].rstrip()}..."

    @staticmethod
    def _safe_int_env(var_name: str, default: int) -> int:
        raw = os.getenv(var_name, "").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            return default


def post_votacao_to_twitter_if_needed(db: Session, api_votacao_id: str) -> Dict[str, str]:
    """
    Convenience wrapper used by vote ingestion code.
    """
    service = TwitterBotService(db)
    return service.post_votacao_if_needed(api_votacao_id)
