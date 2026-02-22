"""Services for fiscal investigation ingestion and anomaly analysis."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
import csv
import hashlib
import io
import os
import re
import time
import unicodedata
import zipfile
from typing import Any, Dict, List, Optional

import requests
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from .model import FiscalPerson, FiscalFinancialRecord, FiscalAnalysisResult


# Sources distilled from open-gov-data.md that are directly useful for personal fiscal trails.
OPEN_DATA_SOURCES: List[Dict[str, Any]] = [
    {
        "codigo": "portal_transparencia",
        "nome": "Portal da Transparência",
        "url": "https://portaldatransparencia.gov.br/api-de-dados",
        "foco": "remuneracao_servidores, transferencias, beneficiarios",
        "requer_chave": True,
    },
    {
        "codigo": "camara_dados_abertos",
        "nome": "Câmara dos Deputados - Dados Abertos",
        "url": "https://dadosabertos.camara.leg.br/api/v2",
        "foco": "deputados, atividade parlamentar, despesas",
        "requer_chave": False,
    },
    {
        "codigo": "senado_dados_abertos",
        "nome": "Senado Federal - Dados Abertos",
        "url": "https://www12.senado.leg.br/dados-abertos",
        "foco": "senadores, verbas, dados legislativos",
        "requer_chave": False,
    },
    {
        "codigo": "tesouro_siconfi",
        "nome": "Tesouro Transparente / SICONFI",
        "url": "https://apidatalake.tesouro.gov.br",
        "foco": "execucao_orcamentaria e transferencias",
        "requer_chave": False,
    },
    {
        "codigo": "cnj_datajud",
        "nome": "CNJ DataJud",
        "url": "https://datajud-wiki.cnj.jus.br",
        "foco": "movimentacoes judiciais e metadados",
        "requer_chave": True,
    },
    {
        "codigo": "inlabs_dou",
        "nome": "DOU / INLabs",
        "url": "https://inlabs.gov.br/api",
        "foco": "nomeacoes, exonerações, atos oficiais",
        "requer_chave": True,
    },
    {
        "codigo": "pncp",
        "nome": "PNCP",
        "url": "https://pncp.gov.br/api/pncp/v1",
        "foco": "contratacoes publicas e fornecedores",
        "requer_chave": False,
    },
    {
        "codigo": "tse_dados_abertos",
        "nome": "TSE - Dados Abertos (Prestação de Contas)",
        "url": "https://dadosabertos.tse.jus.br/",
        "foco": "doacoes e receitas eleitorais por candidato",
        "requer_chave": False,
    },
]

PORTAL_TRANSPARENCIA_BASE_URL = "https://api.portaldatransparencia.gov.br/api-de-dados"
TSE_CKAN_BASE_URL = "https://dadosabertos.tse.jus.br/api/3/action"

SOURCE_DOMAINS: Dict[str, List[str]] = {
    "Corporate/Financial": [
        "Portal Dados Abertos", "Receita Federal CNPJ/QSA", "Juntas Comerciais", "CVM Aberta",
        "Formulário Referência CVM", "Fatos Relevantes CVM", "Insider Trading CVM", "Fundos de Investimento CVM",
        "B3 Negociações", "BCB Câmbio/PTAX", "BCB Selic/Juros", "BCB PIX", "BCB Crédito",
        "BCB IFData", "BCB Base Monetária", "BCB Reservas Internacionais", "BCB Capitais Estrangeiros",
    ],
    "Transparency/Spending": [
        "Portal da Transparência", "Tesouro Transparente", "Base dos Dados", "SIAFI", "SICONFI", "SIOP",
        "ComprasNet/PNCP", "FNDE Repasses", "TCU Auditorias", "TCEs/TCMs",
    ],
    "Sanctions/Compliance": ["CEIS", "CNEP", "CEPIM", "CEAF", "PGFN Dívida Ativa", "SICAF"],
    "Electoral": ["TSE Candidaturas", "TSE Bens Declarados", "TSE Doações", "TSE Resultados Eleitorais"],
    "Health": ["DATASUS SIH", "DATASUS SIM", "DATASUS CNES", "DATASUS SINAN", "INSS/DATAPREV", "PREVIC", "ANS", "ANVISA"],
    "Legal/Judicial": ["DataJud CNJ", "DOU", "DOEs Estaduais", "Querido Diário"],
    "Demographics/Economy": [
        "IBGE Censo", "IBGE PNAD", "IBGE IPCA/INPC", "IBGE PIB", "IBGE PMC", "IBGE PIM-PF",
        "IBGE POF", "IBGE Geociências", "IPEAData",
    ],
    "Education": ["INEP Censo Escolar", "INEP ENEM"],
    "Employment": ["RAIS", "CAGED"],
    "Environment/Land": ["IBAMA Embargos", "IBAMA Licenciamento", "IBAMA SINAFLOR", "INPE DETER", "INPE PRODES", "CAR/SICAR", "INCRA", "CPRM", "INDE"],
    "Transport/Infrastructure": ["DENATRAN/RENAVAM", "ANAC RAB", "ANTT", "ANTAQ", "DNIT", "PRF Acidentes"],
    "Regulation": ["ANEEL", "ANP", "ANATEL", "ANCINE"],
}

PATTERN_IDS: List[Dict[str, str]] = [
    {"id": "P01", "name": "Auto-direcionamento de emendas"},
    {"id": "P02", "name": "Funcionários fantasma"},
    {"id": "P03", "name": "Escola/entidade fantasma"},
    {"id": "P04", "name": "Circuito fechado doação ↔ contrato"},
    {"id": "P05", "name": "Empresa laranja offshore"},
    {"id": "P06", "name": "Licitação direcionada"},
    {"id": "P07", "name": "Desmatamento × mandato"},
    {"id": "P08", "name": "Dívida ativa × contratos ativos"},
    {"id": "P09", "name": "Insider trading"},
    {"id": "P10", "name": "Enriquecimento ilícito"},
]


def _normalize_cpf(cpf: str) -> str:
    digits = "".join(ch for ch in cpf if ch.isdigit())
    if len(digits) != 11:
        raise ValueError("CPF inválido. Informe 11 dígitos.")
    return digits


def _cpf_hash(cpf: str) -> str:
    normalized = _normalize_cpf(cpf)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _safe_cpf_hash(cpf: Optional[str]) -> Optional[str]:
    if not cpf:
        return None
    digits = "".join(ch for ch in str(cpf) if ch.isdigit())
    if len(digits) != 11:
        return None
    return hashlib.sha256(digits.encode("utf-8")).hexdigest()


def _possible_cpf_hashes(cpf: str) -> List[str]:
    raw = _cpf_hash(cpf)
    return [
        raw,
        f"tse:{raw}",
        f"cpf:{raw}",
    ]


def list_open_data_sources() -> List[Dict[str, Any]]:
    return OPEN_DATA_SOURCES


def list_source_domains() -> Dict[str, Any]:
    total = sum(len(items) for items in SOURCE_DOMAINS.values())
    return {"total_sources": total, "domains": SOURCE_DOMAINS}


def get_integration_status() -> Dict[str, Any]:
    implemented = [
        {"id": "portal_remuneracao", "source": "Portal da Transparência", "status": "implemented"},
        {"id": "portal_emendas", "source": "Portal da Transparência", "status": "implemented"},
        {"id": "camara_cota_parlamentar", "source": "Câmara dos Deputados", "status": "implemented"},
        {"id": "pncp_contratos", "source": "PNCP/ComprasNet", "status": "implemented"},
        {"id": "tse_doacoes_csv", "source": "TSE Doações", "status": "implemented"},
        {"id": "tse_bens_csv", "source": "TSE Bens Declarados", "status": "implemented"},
        {"id": "tse_candidaturas_csv", "source": "TSE Candidaturas", "status": "implemented"},
    ]
    high_impact_pending = [
        {"id": "ceis_cnep_ceaf", "source": "CGU sanções", "reason": "compliance e risco contratual"},
        {"id": "pgfn_divida_ativa", "source": "PGFN", "reason": "necessário para padrão P08"},
        {"id": "sicaf_habilitacao", "source": "SICAF", "reason": "necessário para padrão P08"},
        {"id": "senado_despesas", "source": "Senado", "reason": "completar renda/despesa parlamentar"},
    ]
    return {
        "implemented_count": len(implemented),
        "implemented": implemented,
        "high_impact_pending": high_impact_pending,
        "total_catalog_sources": sum(len(items) for items in SOURCE_DOMAINS.values()),
    }


def _normalize_name_key(name: str) -> str:
    base = unicodedata.normalize("NFKD", (name or "").strip().lower())
    ascii_only = "".join(ch for ch in base if not unicodedata.combining(ch))
    cleaned = re.sub(r"[^a-z0-9 ]+", " ", ascii_only)
    return re.sub(r"\s+", " ", cleaned).strip()


def _merge_metadata(base: Optional[Dict[str, Any]], extra: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not base and not extra:
        return None
    merged: Dict[str, Any] = dict(base or {})
    for key, value in (extra or {}).items():
        if value is not None and value != "":
            merged[key] = value
    return merged


def _resolve_person_by_name(db: Session, nome: str, cargo: Optional[str] = None, orgao: Optional[str] = None) -> Optional[FiscalPerson]:
    name_key = _normalize_name_key(nome)
    if not name_key:
        return None

    # Pull a bounded set first and resolve in Python for accent-insensitive comparison.
    candidates = (
        db.query(FiscalPerson)
        .filter(FiscalPerson.ativo.is_(True))
        .order_by(FiscalPerson.updated_at.desc())
        .limit(20000)
        .all()
    )

    exact_matches: List[FiscalPerson] = []
    for item in candidates:
        if _normalize_name_key(item.nome) == name_key:
            exact_matches.append(item)

    if not exact_matches:
        return None

    if cargo:
        for item in exact_matches:
            if (item.cargo or "").lower() == cargo.lower() and (not orgao or (item.orgao or "").lower() == orgao.lower()):
                return item

    if orgao:
        for item in exact_matches:
            if (item.orgao or "").lower() == orgao.lower():
                return item

    return exact_matches[0]


def upsert_person(db: Session, payload: Dict[str, Any]) -> FiscalPerson:
    person_id = payload.get("id")
    person = db.query(FiscalPerson).filter(FiscalPerson.id == person_id).first() if person_id else None

    if not person and payload.get("cpf_hash"):
        person = db.query(FiscalPerson).filter(FiscalPerson.cpf_hash == payload["cpf_hash"]).first()

    if not person and payload.get("nome"):
        person = _resolve_person_by_name(
            db=db,
            nome=payload["nome"],
            cargo=payload.get("cargo"),
            orgao=payload.get("orgao"),
        )

    if person:
        person.nome = payload.get("nome", person.nome)
        person.cargo = payload.get("cargo", person.cargo)
        person.orgao = payload.get("orgao", person.orgao)
        if payload.get("cpf_hash"):
            existing_same_hash = db.query(FiscalPerson).filter(FiscalPerson.cpf_hash == payload["cpf_hash"]).first()
            if existing_same_hash and existing_same_hash.id != person.id:
                person = existing_same_hash
            elif not person.cpf_hash:
                person.cpf_hash = payload["cpf_hash"]
            elif person.cpf_hash.startswith(("autor_emenda:", "nome:", "tse:")) and not payload["cpf_hash"].startswith(("autor_emenda:", "nome:", "tse:")):
                person.cpf_hash = payload["cpf_hash"]
        person.ativo = payload.get("ativo", person.ativo)
        person.metadata_json = _merge_metadata(person.metadata_json, payload.get("metadata_json"))
    else:
        person = FiscalPerson(
            nome=payload["nome"],
            cpf_hash=payload.get("cpf_hash"),
            cargo=payload["cargo"],
            orgao=payload.get("orgao"),
            ativo=payload.get("ativo", True),
            metadata_json=payload.get("metadata_json"),
        )
        db.add(person)

    db.commit()
    db.refresh(person)
    return person


def add_financial_records(db: Session, person_id: int, records: List[Dict[str, Any]]) -> int:
    inserted = 0
    for record in records:
        reference_date = None
        if record.get("data_referencia"):
            reference_date = datetime.fromisoformat(record["data_referencia"])

        new_record = FiscalFinancialRecord(
            person_id=person_id,
            ano=record["ano"],
            tipo=record["tipo"],
            valor=Decimal(str(record["valor"])),
            moeda=record.get("moeda", "BRL"),
            fonte=record["fonte"],
            fonte_url=record.get("fonte_url"),
            confianca=float(record.get("confianca", 1.0)),
            extra_json=record.get("extra_json"),
            data_referencia=reference_date,
        )
        db.add(new_record)
        inserted += 1

    db.commit()
    return inserted


def _parse_brl_value(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    text = str(value).strip()
    if not text:
        return Decimal("0")

    cleaned = text.replace("R$", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        return Decimal(cleaned)
    except Exception:
        return Decimal("0")


def _month_date_from_mes_ano(mes_ano: int) -> datetime:
    text = str(mes_ano)
    if len(text) != 6:
        raise ValueError("mes_ano deve seguir formato YYYYMM")
    year = int(text[:4])
    month = int(text[4:])
    return datetime(year, month, 1)


def _upsert_financial_record(
    db: Session,
    person_id: int,
    ano: int,
    tipo: str,
    valor: Decimal,
    fonte: str,
    fonte_url: Optional[str] = None,
    confianca: float = 1.0,
    extra_json: Optional[Dict[str, Any]] = None,
    data_referencia: Optional[datetime] = None,
) -> FiscalFinancialRecord:
    existing = db.query(FiscalFinancialRecord).filter(
        FiscalFinancialRecord.person_id == person_id,
        FiscalFinancialRecord.ano == ano,
        FiscalFinancialRecord.tipo == tipo,
        FiscalFinancialRecord.fonte == fonte,
        FiscalFinancialRecord.data_referencia == data_referencia,
    ).first()

    if existing:
        existing.valor = valor
        existing.fonte_url = fonte_url or existing.fonte_url
        existing.confianca = confianca
        existing.extra_json = extra_json
        return existing

    record = FiscalFinancialRecord(
        person_id=person_id,
        ano=ano,
        tipo=tipo,
        valor=valor,
        moeda="BRL",
        fonte=fonte,
        fonte_url=fonte_url,
        confianca=confianca,
        extra_json=extra_json,
        data_referencia=data_referencia,
    )
    db.add(record)
    return record


def _http_get_with_retry(
    url: str,
    *,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    retries: int = 3,
    retry_sleep_seconds: float = 1.0,
) -> requests.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=timeout)
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
            time.sleep(retry_sleep_seconds * attempt)

    raise requests.ConnectionError(f"Falha em GET {url} após {retries} tentativas: {last_exc}")


def _risk_level(score: float) -> str:
    if score >= 80:
        return "CRITICO"
    if score >= 60:
        return "ALTO"
    if score >= 40:
        return "MEDIO"
    if score >= 20:
        return "BAIXO"
    return "MINIMO"


def sync_portal_transparencia_servidores_remuneracao(
    db: Session,
    mes_ano: int,
    max_servidores: int = 50,
    pagina_inicial: int = 1,
) -> Dict[str, Any]:
    """
    Connector #1: ingest federal executive server remuneration from Portal da Transparência.
    Requires env var PORTAL_TRANSPARENCIA_API_KEY.
    """
    api_key = os.getenv("PORTAL_TRANSPARENCIA_API_KEY")
    if not api_key:
        raise ValueError("PORTAL_TRANSPARENCIA_API_KEY não configurada")

    headers = {"chave-api-dados": api_key}
    ref_date = _month_date_from_mes_ano(mes_ano)
    year = ref_date.year

    ingested_people = 0
    inserted_or_updated_records = 0
    remuneration_failures = 0
    page = pagina_inicial
    orgaos_page = pagina_inicial
    server_page_by_orgao: Dict[str, int] = {}
    processed_server_ids = set()

    while ingested_people < max_servidores:
        # /servidores requires filter. We fetch available SIAPE organs first.
        orgao_resp = requests.get(
            f"{PORTAL_TRANSPARENCIA_BASE_URL}/servidores/por-orgao",
            headers=headers,
            params={"pagina": orgaos_page},
            timeout=30,
        )
        if orgao_resp.status_code == 429:
            raise ValueError("Limite de requisições excedido no Portal da Transparência (HTTP 429)")
        orgao_resp.raise_for_status()
        orgaos = orgao_resp.json() or []
        if not orgaos:
            break

        for orgao_item in orgaos:
            if ingested_people >= max_servidores:
                break

            orgao_codigo = orgao_item.get("codOrgaoExercicioSiape") or orgao_item.get("codOrgaoLotacaoSiape")
            if not orgao_codigo:
                continue

            server_page = server_page_by_orgao.get(orgao_codigo, 1)
            servidores_resp = requests.get(
                f"{PORTAL_TRANSPARENCIA_BASE_URL}/servidores",
                headers=headers,
                params={"pagina": server_page, "orgaoServidorExercicio": orgao_codigo},
                timeout=30,
            )
            if servidores_resp.status_code == 429:
                raise ValueError("Limite de requisições excedido no Portal da Transparência (HTTP 429)")
            if servidores_resp.status_code >= 400:
                continue

            servidores = servidores_resp.json() or []
            if not servidores:
                continue

            for servidor_item in servidores:
                if ingested_people >= max_servidores:
                    break

                servidor = servidor_item.get("servidor", {}) or {}
                servidor_id = servidor.get("id")
                if not servidor_id or servidor_id in processed_server_ids:
                    continue
                processed_server_ids.add(servidor_id)

                pessoa = servidor.get("pessoa", {}) or {}
                cpf = pessoa.get("cpfFormatado") or pessoa.get("cpf")
                cpf_hash = hashlib.sha256(cpf.encode("utf-8")).hexdigest() if cpf else None

                nome = pessoa.get("nome") or f"Servidor {servidor_id}"
                cargo = (servidor.get("funcao") or {}).get("descricaoFuncaoCargo") or "servidor_publico"
                orgao = (servidor.get("orgaoServidorExercicio") or {}).get("nome") or (servidor.get("orgaoServidorLotacao") or {}).get("nome")

                metadata = {
                    "portal_transparencia_id": servidor_id,
                    "tipo_servidor": servidor.get("tipoServidor"),
                    "situacao": servidor.get("situacao"),
                    "orgao_codigo_siape": orgao_codigo,
                }

                person = upsert_person(
                    db,
                    {
                        "nome": nome,
                        "cpf_hash": cpf_hash,
                        "cargo": cargo,
                        "orgao": orgao,
                        "ativo": True,
                        "metadata_json": metadata,
                    },
                )

                remun_resp = requests.get(
                    f"{PORTAL_TRANSPARENCIA_BASE_URL}/servidores/remuneracao",
                    headers=headers,
                    params={"id": servidor_id, "mesAno": mes_ano, "pagina": 1},
                    timeout=30,
                )
                if remun_resp.status_code == 404:
                    remuneration_failures += 1
                    ingested_people += 1
                    continue
                if remun_resp.status_code == 429:
                    raise ValueError("Limite de requisições excedido no Portal da Transparência (HTTP 429)")
                if remun_resp.status_code >= 400:
                    remuneration_failures += 1
                    ingested_people += 1
                    continue

                remuneracoes = remun_resp.json() or []
                total_remuneracao = Decimal("0")
                for rem in remuneracoes:
                    itens = rem.get("remuneracoesDTO", []) or []
                    for item in itens:
                        total_remuneracao += _parse_brl_value(item.get("valorTotalRemuneracaoAposDeducoes"))

                if total_remuneracao > 0:
                    _upsert_financial_record(
                        db=db,
                        person_id=person.id,
                        ano=year,
                        tipo="salario",
                        valor=total_remuneracao,
                        fonte="portal_transparencia",
                        fonte_url=f"{PORTAL_TRANSPARENCIA_BASE_URL}/servidores/remuneracao?id={servidor_id}&mesAno={mes_ano}&pagina=1",
                        confianca=0.95,
                        extra_json={
                            "mes_ano": mes_ano,
                            "portal_transparencia_id": servidor_id,
                            "registros_remuneracao": len(remuneracoes),
                        },
                        data_referencia=ref_date,
                    )
                    inserted_or_updated_records += 1

                ingested_people += 1

            server_page_by_orgao[orgao_codigo] = server_page + 1

        orgaos_page += 1
        page += 1

    db.commit()
    return {
        "mes_ano": mes_ano,
        "processados": ingested_people,
        "registros_salario_upsert": inserted_or_updated_records,
        "falhas_remuneracao": remuneration_failures,
        "pagina_final": page - 1,
    }


def sync_portal_transparencia_emendas(
    db: Session,
    ano: int,
    max_paginas: int = 10,
    pagina_inicial: int = 1,
) -> Dict[str, Any]:
    """
    Connector #2: ingest public financing signals from parliamentary amendments.
    Stores yearly value paid as `financiamento_publico` for each author.
    """
    api_key = os.getenv("PORTAL_TRANSPARENCIA_API_KEY")
    if not api_key:
        raise ValueError("PORTAL_TRANSPARENCIA_API_KEY não configurada")

    headers = {"chave-api-dados": api_key}
    page = pagina_inicial
    pages_processed = 0
    people_touched = 0
    records_upserted = 0

    while pages_processed < max_paginas:
        resp = requests.get(
            f"{PORTAL_TRANSPARENCIA_BASE_URL}/emendas",
            headers=headers,
            params={"ano": ano, "pagina": page},
            timeout=30,
        )
        if resp.status_code == 429:
            raise ValueError("Limite de requisições excedido no Portal da Transparência (HTTP 429)")
        resp.raise_for_status()
        rows = resp.json() or []
        if not rows:
            break

        for item in rows:
            nome_autor = item.get("nomeAutor")
            if not nome_autor:
                continue

            person = upsert_person(
                db,
                {
                    "nome": nome_autor,
                    # Emendas endpoint usually does not expose CPF; rely on entity resolution by name/cargo/orgao.
                    "cpf_hash": None,
                    "cargo": "parlamentar",
                    "orgao": "congresso_nacional",
                    "ativo": True,
                    "metadata_json": {
                        "origem": "emendas_portal_transparencia",
                        "name_key": _normalize_name_key(nome_autor),
                    },
                },
            )

            valor_pago = _parse_brl_value(item.get("valorPago"))
            valor_liquidado = _parse_brl_value(item.get("valorLiquidado"))
            total_valor = valor_pago if valor_pago > 0 else valor_liquidado

            if total_valor > 0:
                _upsert_financial_record(
                    db=db,
                    person_id=person.id,
                    ano=ano,
                    tipo="financiamento_publico",
                    valor=total_valor,
                    fonte="portal_transparencia_emendas",
                    fonte_url=f"{PORTAL_TRANSPARENCIA_BASE_URL}/emendas?ano={ano}&pagina={page}",
                    confianca=0.9,
                    extra_json={
                        "codigoEmenda": item.get("codigoEmenda"),
                        "numeroEmenda": item.get("numeroEmenda"),
                        "tipoEmenda": item.get("tipoEmenda"),
                    },
                    data_referencia=datetime(ano, 1, 1),
                )
                records_upserted += 1

            people_touched += 1

        page += 1
        pages_processed += 1

    db.commit()
    return {
        "ano": ano,
        "paginas_processadas": pages_processed,
        "pessoas_processadas": people_touched,
        "registros_financiamento_upsert": records_upserted,
        "pagina_final": page - 1,
    }


def sync_camara_deputados_expenses(
    db: Session,
    ano: int,
    max_deputados: int = 100,
    max_paginas_despesas_por_deputado: int = 10,
) -> Dict[str, Any]:
    """
    Connector: Câmara dos Deputados open API (/deputados/{id}/despesas).
    Aggregates yearly reimbursed parliamentary expenses as public financing signals.
    """
    if max_deputados <= 0:
        raise ValueError("'max_deputados' deve ser maior que zero")
    if max_paginas_despesas_por_deputado <= 0:
        raise ValueError("'max_paginas_despesas_por_deputado' deve ser maior que zero")

    base_url = "https://dadosabertos.camara.leg.br/api/v2"
    headers = {"accept": "application/json"}

    deputados_processados = 0
    registros_upsert = 0
    pagina_deputados = 1
    paginas_deputados_processadas = 0

    while deputados_processados < max_deputados:
        dep_resp = _http_get_with_retry(
            f"{base_url}/deputados",
            headers=headers,
            params={"itens": 100, "pagina": pagina_deputados},
            timeout=30,
            retries=3,
        )
        dep_resp.raise_for_status()
        dep_payload = dep_resp.json() or {}
        deputados = dep_payload.get("dados") or []
        if not deputados:
            break

        for dep in deputados:
            if deputados_processados >= max_deputados:
                break

            dep_id = dep.get("id")
            dep_nome = dep.get("nome")
            if not dep_id or not dep_nome:
                continue

            despesas_total = Decimal("0")
            pagina_despesas = 1
            paginas_despesas_processadas = 0

            while paginas_despesas_processadas < max_paginas_despesas_por_deputado:
                try:
                    desp_resp = _http_get_with_retry(
                        f"{base_url}/deputados/{dep_id}/despesas",
                        headers=headers,
                        params={"ano": ano, "itens": 100, "pagina": pagina_despesas},
                        timeout=30,
                        retries=3,
                    )
                except requests.RequestException:
                    # Skip unstable deputy page instead of aborting whole connector run.
                    break
                if desp_resp.status_code == 404:
                    break
                desp_resp.raise_for_status()
                desp_payload = desp_resp.json() or {}
                rows = desp_payload.get("dados") or []
                if not rows:
                    break

                for row in rows:
                    val = _parse_brl_value(row.get("valorLiquido"))
                    if val <= 0:
                        val = _parse_brl_value(row.get("valorDocumento"))
                    if val > 0:
                        despesas_total += val

                paginas_despesas_processadas += 1
                pagina_despesas += 1

            person = upsert_person(
                db,
                {
                    "nome": dep_nome,
                    "cpf_hash": None,
                    "cargo": "deputado",
                    "orgao": "camara",
                    "ativo": True,
                    "metadata_json": {
                        "origem": "camara_despesas",
                        "camara_id": dep_id,
                        "sigla_uf": dep.get("siglaUf"),
                        "sigla_partido": dep.get("siglaPartido"),
                        "name_key": _normalize_name_key(dep_nome),
                    },
                },
            )

            if despesas_total > 0:
                _upsert_financial_record(
                    db=db,
                    person_id=person.id,
                    ano=ano,
                    tipo="financiamento_publico",
                    valor=despesas_total,
                    fonte="camara_cota_parlamentar",
                    fonte_url=f"{base_url}/deputados/{dep_id}/despesas?ano={ano}",
                    confianca=0.93,
                    extra_json={
                        "camara_id": dep_id,
                        "ano": ano,
                    },
                    data_referencia=datetime(ano, 1, 1),
                )
                registros_upsert += 1

            deputados_processados += 1

        paginas_deputados_processadas += 1
        pagina_deputados += 1

    db.commit()
    return {
        "ano": ano,
        "deputados_processados": deputados_processados,
        "paginas_deputados_processadas": paginas_deputados_processadas,
        "registros_financiamento_upsert": registros_upsert,
    }


def sync_pncp_contracts(
    db: Session,
    data_inicial: str,
    data_final: str,
    max_paginas: int = 5,
    tamanho_pagina: int = 50,
) -> Dict[str, Any]:
    """
    Connector: PNCP Consulta API (/consulta/v1/contratos).
    Links suppliers to known persons by CPF hash or normalized name and records contract inflow.
    """
    if max_paginas <= 0:
        raise ValueError("'max_paginas' deve ser maior que zero")
    if tamanho_pagina < 10:
        raise ValueError("'tamanho_pagina' deve ser >= 10 (restrição da API PNCP)")

    base_url = "https://pncp.gov.br/api/consulta/v1/contratos"
    params_base = {
        "dataInicial": data_inicial,
        "dataFinal": data_final,
        "tamanhoPagina": tamanho_pagina,
    }

    # Candidate index for fast matching.
    people = db.query(FiscalPerson).filter(FiscalPerson.ativo.is_(True)).all()
    by_hash = {p.cpf_hash: p for p in people if p.cpf_hash}
    by_name = {_normalize_name_key(p.nome): p for p in people}

    paginas_processadas = 0
    contratos_lidos = 0
    contratos_com_match = 0
    registros_upsert = 0

    for pagina in range(1, max_paginas + 1):
        resp = _http_get_with_retry(
            base_url,
            params={**params_base, "pagina": pagina},
            timeout=45,
            retries=3,
        )
        if resp.status_code == 429:
            raise ValueError("Limite de requisições excedido no PNCP (HTTP 429)")
        resp.raise_for_status()
        payload = resp.json() or {}
        rows = payload.get("data") or []
        if not rows:
            break

        paginas_processadas += 1

        for row in rows:
            contratos_lidos += 1

            supplier_doc = str(row.get("niFornecedor") or "").strip()
            supplier_name = str(row.get("nomeRazaoSocialFornecedor") or "").strip()
            if not supplier_doc and not supplier_name:
                continue

            person: Optional[FiscalPerson] = None
            supplier_hash = _safe_cpf_hash(supplier_doc)
            if supplier_hash:
                person = by_hash.get(supplier_hash)

            if not person and supplier_name:
                person = by_name.get(_normalize_name_key(supplier_name))

            if not person:
                continue

            contratos_com_match += 1
            valor_global = _parse_brl_value(row.get("valorGlobal"))
            if valor_global <= 0:
                valor_global = _parse_brl_value(row.get("valorInicial"))
            if valor_global <= 0:
                continue

            ano = int(row.get("anoContrato") or datetime.now().year)
            _upsert_financial_record(
                db=db,
                person_id=person.id,
                ano=ano,
                tipo="renda_extra",
                valor=valor_global,
                fonte="pncp_contratos",
                fonte_url=base_url,
                confianca=0.86,
                extra_json={
                    "numero_controle_pncp": row.get("numeroControlePNCP"),
                    "numero_controle_compra": row.get("numeroControlePncpCompra"),
                    "orgao_cnpj": ((row.get("orgaoEntidade") or {}).get("cnpj") if isinstance(row.get("orgaoEntidade"), dict) else None),
                    "orgao_razao_social": ((row.get("orgaoEntidade") or {}).get("razaoSocial") if isinstance(row.get("orgaoEntidade"), dict) else None),
                    "fornecedor_doc": supplier_doc,
                    "fornecedor_nome": supplier_name,
                },
                data_referencia=datetime(ano, 1, 1),
            )
            registros_upsert += 1

    db.commit()
    return {
        "data_inicial": data_inicial,
        "data_final": data_final,
        "paginas_processadas": paginas_processadas,
        "contratos_lidos": contratos_lidos,
        "contratos_com_match": contratos_com_match,
        "registros_renda_extra_upsert": registros_upsert,
    }


def _extract_csv_from_content(content: bytes, url: str) -> str:
    lower = url.lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            csv_names = [name for name in zf.namelist() if name.lower().endswith(".csv")]
            if not csv_names:
                raise ValueError("Arquivo ZIP sem CSV")
            raw = zf.read(csv_names[0])
            try:
                return raw.decode("latin-1")
            except UnicodeDecodeError:
                return raw.decode("utf-8")
    try:
        return content.decode("latin-1")
    except UnicodeDecodeError:
        return content.decode("utf-8")


def _tse_package_show(package_id: str) -> Dict[str, Any]:
    resp = _http_get_with_retry(
        f"{TSE_CKAN_BASE_URL}/package_show",
        params={"id": package_id},
        timeout=45,
        retries=3,
    )
    resp.raise_for_status()
    payload = resp.json() or {}
    if not payload.get("success") or not payload.get("result"):
        raise ValueError(f"Pacote TSE não encontrado: {package_id}")
    return payload["result"]


def _tse_find_resource_url(package: Dict[str, Any], name_contains: List[str]) -> Optional[str]:
    resources = package.get("resources") or []
    for resource in resources:
        name = str(resource.get("name") or "").lower()
        fmt = str(resource.get("format") or "").lower()
        url = resource.get("url")
        if not url:
            continue
        if fmt not in ("csv", "txt", "zip"):
            continue
        if all(token.lower() in name for token in name_contains):
            return str(url)
    return None


def discover_tse_urls_for_year(ano: int) -> Dict[str, Optional[str]]:
    """
    Discover canonical TSE open-data resources for a given election year via CKAN.
    """
    cand_package = _tse_package_show(f"candidatos-{ano}")
    presta_package = _tse_package_show(f"prestacao-de-contas-eleitorais-{ano}")

    candidates_url = _tse_find_resource_url(cand_package, ["candidatos"])
    assets_url = _tse_find_resource_url(cand_package, ["bens", "candidatos"])
    donations_url = _tse_find_resource_url(presta_package, ["contas", "candidatos"])

    return {
        "candidates_url": candidates_url,
        "assets_url": assets_url,
        "donations_url": donations_url,
    }


def _pick_value(row: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def sync_tse_donations_from_csv_url(
    db: Session,
    csv_url: str,
    ano: int,
    max_linhas: int = 50000,
) -> Dict[str, Any]:
    """
    Connector #3: ingest donations from TSE open-data CSV/ZIP URL.
    Expected to map campaign receipts to `doacao_recebida`.
    """
    resp = requests.get(csv_url, timeout=60)
    resp.raise_for_status()
    text = _extract_csv_from_content(resp.content, csv_url)

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    processed = 0
    matched = 0
    upserted = 0

    for row in reader:
        if processed >= max_linhas:
            break
        processed += 1

        nome = _pick_value(row, ["NM_CANDIDATO", "NOME_CANDIDATO", "NM_PRESTADOR_CONTAS", "nome_candidato"])
        if not nome:
            continue

        valor = _parse_brl_value(_pick_value(row, ["VR_RECEITA", "VALOR_RECEITA", "valor_receita", "valor"]))
        if valor <= 0:
            continue

        cpf = _pick_value(row, ["NR_CPF_CANDIDATO", "CPF_CANDIDATO", "NR_CPF_CNPJ_CANDIDATO", "cpf_candidato"])
        cpf_hash = _safe_cpf_hash(cpf)
        cargo = _pick_value(row, ["DS_CARGO", "CARGO", "cargo"]) or "agente_politico"
        uf = _pick_value(row, ["SG_UF", "UF", "sigla_uf"])
        partido = _pick_value(row, ["SG_PARTIDO", "SIGLA_PARTIDO", "partido"])

        person = upsert_person(
            db,
            {
                "nome": str(nome).strip(),
                "cpf_hash": cpf_hash,
                "cargo": str(cargo).strip().lower().replace(" ", "_"),
                "orgao": uf,
                "ativo": True,
                "metadata_json": {
                    "origem": "tse_donations",
                    "partido": partido,
                    "name_key": _normalize_name_key(str(nome)),
                },
            },
        )

        _upsert_financial_record(
            db=db,
            person_id=person.id,
            ano=ano,
            tipo="doacao_recebida",
            valor=valor,
            fonte="tse_receitas_eleitorais",
            fonte_url=csv_url,
            confianca=0.88,
            extra_json={
                "fonte_linha": processed,
                "descricao_receita": _pick_value(row, ["DS_FONTE_RECEITA", "DS_RECEITA"]),
            },
            data_referencia=datetime(ano, 1, 1),
        )
        matched += 1
        upserted += 1

    db.commit()
    return {
        "ano": ano,
        "linhas_processadas": processed,
        "linhas_com_match": matched,
        "registros_doacao_upsert": upserted,
    }


def sync_tse_assets_from_csv_url(
    db: Session,
    csv_url: str,
    ano: int,
    max_linhas: int = 50000,
) -> Dict[str, Any]:
    """
    Ingest TSE declared assets to support illicit enrichment analysis.
    """
    resp = requests.get(csv_url, timeout=60)
    resp.raise_for_status()
    text = _extract_csv_from_content(resp.content, csv_url)

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    processed = 0
    matched = 0
    upserted = 0

    assets_by_person: Dict[str, Decimal] = {}
    meta_by_person: Dict[str, Dict[str, Any]] = {}

    for row in reader:
        if processed >= max_linhas:
            break
        processed += 1

        nome = _pick_value(row, ["NM_CANDIDATO", "NOME_CANDIDATO", "nome_candidato"])
        if not nome:
            continue

        cpf = _pick_value(row, ["NR_CPF_CANDIDATO", "CPF_CANDIDATO", "cpf_candidato"])
        cpf_hash = _safe_cpf_hash(cpf)
        key = cpf_hash or f"nome:{_normalize_name_key(str(nome))}"

        value = _parse_brl_value(
            _pick_value(
                row,
                ["VR_BEM_CANDIDATO", "VR_BEM", "VALOR_BEM", "valor_bem"],
            )
        )
        if value <= 0:
            continue

        assets_by_person[key] = assets_by_person.get(key, Decimal("0")) + value
        meta_by_person[key] = {
            "nome": str(nome).strip(),
            "cargo": (_pick_value(row, ["DS_CARGO", "CARGO", "cargo"]) or "agente_politico").strip().lower().replace(" ", "_"),
            "uf": _pick_value(row, ["SG_UF", "UF", "sigla_uf"]),
            "partido": _pick_value(row, ["SG_PARTIDO", "SIGLA_PARTIDO", "partido"]),
            "name_key": _normalize_name_key(str(nome)),
        }
        matched += 1

    for key, total_assets in assets_by_person.items():
        info = meta_by_person[key]
        person = upsert_person(
            db,
            {
                "nome": info["nome"],
                "cpf_hash": key if not key.startswith("nome:") else None,
                "cargo": info["cargo"],
                "orgao": info["uf"],
                "ativo": True,
                "metadata_json": {
                    "origem": "tse_assets",
                    "partido": info.get("partido"),
                    "name_key": info.get("name_key"),
                },
            },
        )
        _upsert_financial_record(
            db=db,
            person_id=person.id,
            ano=ano,
            tipo="patrimonio_declarado",
            valor=total_assets,
            fonte="tse_bens_declarados",
            fonte_url=csv_url,
            confianca=0.92,
            extra_json={"ano": ano},
            data_referencia=datetime(ano, 1, 1),
        )
        upserted += 1

    db.commit()
    return {
        "ano": ano,
        "linhas_processadas": processed,
        "linhas_com_match": matched,
        "registros_patrimonio_upsert": upserted,
    }


def sync_tse_candidates_from_csv_url(
    db: Session,
    csv_url: str,
    ano: int,
    max_linhas: int = 100000,
) -> Dict[str, Any]:
    """
    Connector #5: ingest TSE candidatures metadata to strengthen identity resolution.
    """
    resp = requests.get(csv_url, timeout=60)
    resp.raise_for_status()
    text = _extract_csv_from_content(resp.content, csv_url)

    reader = csv.DictReader(io.StringIO(text), delimiter=";")
    processed = 0
    upserted_people = 0

    for row in reader:
        if processed >= max_linhas:
            break
        processed += 1

        nome = _pick_value(row, ["NM_CANDIDATO", "NOME_CANDIDATO", "nome_candidato"])
        if not nome:
            continue

        cpf = _pick_value(row, ["NR_CPF_CANDIDATO", "CPF_CANDIDATO", "cpf_candidato"])
        cpf_hash = _safe_cpf_hash(cpf)
        cargo = (_pick_value(row, ["DS_CARGO", "CARGO", "cargo"]) or "agente_politico").strip().lower().replace(" ", "_")
        uf = _pick_value(row, ["SG_UF", "UF", "sigla_uf"])
        partido = _pick_value(row, ["SG_PARTIDO", "SIGLA_PARTIDO", "partido"])

        upsert_person(
            db,
            {
                "nome": str(nome).strip(),
                "cpf_hash": cpf_hash,
                "cargo": cargo,
                "orgao": uf or "justica_eleitoral",
                "ativo": True,
                "metadata_json": {
                    "origem": "tse_candidates",
                    "ano_eleicao": ano,
                    "partido": partido,
                    "situacao_candidatura": _pick_value(row, ["DS_SITUACAO_CANDIDATURA", "SITUACAO_CANDIDATURA"]),
                    "name_key": _normalize_name_key(str(nome)),
                },
            },
        )
        upserted_people += 1

    db.commit()
    return {
        "ano": ano,
        "linhas_processadas": processed,
        "pessoas_upsert": upserted_people,
    }


def sync_tse_auto_from_ckan(
    db: Session,
    ano: int,
    max_linhas_doacoes: int = 50000,
    max_linhas_bens: int = 50000,
    max_linhas_candidatos: int = 100000,
) -> Dict[str, Any]:
    """
    Auto-discover TSE resource URLs (CKAN) and ingest candidates, assets and donations.
    """
    urls = discover_tse_urls_for_year(ano)
    result: Dict[str, Any] = {"ano": ano, "urls": urls, "executed": {}}

    if urls.get("candidates_url"):
        try:
            result["executed"]["candidates"] = sync_tse_candidates_from_csv_url(
                db=db,
                csv_url=str(urls["candidates_url"]),
                ano=ano,
                max_linhas=max_linhas_candidatos,
            )
        except Exception as exc:
            result["executed"]["candidates"] = {"error": str(exc)}
    else:
        result["executed"]["candidates"] = {"skipped": True, "reason": "resource_not_found"}

    if urls.get("assets_url"):
        try:
            result["executed"]["assets"] = sync_tse_assets_from_csv_url(
                db=db,
                csv_url=str(urls["assets_url"]),
                ano=ano,
                max_linhas=max_linhas_bens,
            )
        except Exception as exc:
            result["executed"]["assets"] = {"error": str(exc)}
    else:
        result["executed"]["assets"] = {"skipped": True, "reason": "resource_not_found"}

    if urls.get("donations_url"):
        try:
            result["executed"]["donations"] = sync_tse_donations_from_csv_url(
                db=db,
                csv_url=str(urls["donations_url"]),
                ano=ano,
                max_linhas=max_linhas_doacoes,
            )
        except Exception as exc:
            result["executed"]["donations"] = {"error": str(exc)}
    else:
        result["executed"]["donations"] = {"skipped": True, "reason": "resource_not_found"}

    return result


def _score_risk(excesso: Decimal, crescimento: Decimal, compatibilidade: float) -> float:
    if crescimento <= 0:
        return 0.0

    percentual_nao_explicado = float(excesso / crescimento) if crescimento else 0.0
    score = (percentual_nao_explicado * 70.0) + ((1.0 - compatibilidade) * 30.0)
    return max(0.0, min(100.0, score))


def run_analysis(
    db: Session,
    anos: Optional[List[int]] = None,
    min_excesso_brl: float = 100000.0,
    min_ratio_compatibilidade: float = 0.7,
) -> Dict[str, Any]:
    people = db.query(FiscalPerson).filter(FiscalPerson.ativo.is_(True)).all()
    processed = 0
    flagged = 0

    for person in people:
        rows = (
            db.query(
                FiscalFinancialRecord.ano.label("ano"),
                FiscalFinancialRecord.tipo.label("tipo"),
                func.sum(FiscalFinancialRecord.valor).label("valor_total"),
            )
            .filter(FiscalFinancialRecord.person_id == person.id)
            .group_by(FiscalFinancialRecord.ano, FiscalFinancialRecord.tipo)
            .all()
        )

        by_year: Dict[int, Dict[str, Decimal]] = {}
        for row in rows:
            by_year.setdefault(row.ano, {})[row.tipo] = Decimal(row.valor_total or 0)

        years = sorted(by_year.keys())
        if anos:
            allowed = set(anos)
            years = [y for y in years if y in allowed]

        for year in years:
            previous_assets = by_year.get(year - 1, {}).get("patrimonio_declarado")
            current_assets = by_year.get(year, {}).get("patrimonio_declarado")
            if previous_assets is None or current_assets is None:
                continue

            salary = by_year.get(year, {}).get("salario", Decimal("0"))
            donations = by_year.get(year, {}).get("doacao_recebida", Decimal("0"))
            public_funding = by_year.get(year, {}).get("financiamento_publico", Decimal("0"))
            other_income = by_year.get(year, {}).get("renda_extra", Decimal("0"))

            inflows = salary + donations + public_funding + other_income
            growth = current_assets - previous_assets
            excesso = growth - inflows

            if growth <= 0:
                compat = 1.0
            else:
                compat = float(min(Decimal("1"), max(Decimal("0"), inflows / growth)))

            score = _score_risk(excesso=excesso, crescimento=growth, compatibilidade=compat)
            is_flagged = bool(growth > 0 and excesso >= Decimal(str(min_excesso_brl)) and compat < min_ratio_compatibilidade)
            rule = None
            if is_flagged:
                rule = (
                    f"crescimento_patrimonial({growth}) acima de inflows({inflows}) "
                    f"com excesso({excesso}) >= {min_excesso_brl}"
                )

            result = db.query(FiscalAnalysisResult).filter(
                FiscalAnalysisResult.person_id == person.id,
                FiscalAnalysisResult.ano == year,
            ).first()

            if not result:
                result = FiscalAnalysisResult(person_id=person.id, ano=year)
                db.add(result)

            result.patrimonio_anterior = previous_assets
            result.patrimonio_atual = current_assets
            result.crescimento_patrimonial = growth
            result.inflows_conhecidos = inflows
            result.excesso_nao_explicado = excesso
            result.indice_compatibilidade = compat
            result.risco_score = score
            result.sinalizado = is_flagged
            result.regra_disparo = rule
            result.detalhes_json = {
                "salario": float(salary),
                "doacao_recebida": float(donations),
                "financiamento_publico": float(public_funding),
                "renda_extra": float(other_income),
            }
            result.analisado_em = datetime.utcnow()

            processed += 1
            if is_flagged:
                flagged += 1

    db.commit()
    return {
        "processed": processed,
        "flagged": flagged,
        "min_excesso_brl": min_excesso_brl,
        "min_ratio_compatibilidade": min_ratio_compatibilidade,
    }


def get_suspects(db: Session, min_risk_score: float = 50.0, limit: int = 100) -> List[Dict[str, Any]]:
    rows = (
        db.query(FiscalAnalysisResult, FiscalPerson)
        .join(FiscalPerson, FiscalPerson.id == FiscalAnalysisResult.person_id)
        .filter(
            FiscalAnalysisResult.sinalizado.is_(True),
            FiscalAnalysisResult.risco_score >= min_risk_score,
        )
        .order_by(desc(FiscalAnalysisResult.risco_score), desc(FiscalAnalysisResult.excesso_nao_explicado))
        .limit(limit)
        .all()
    )

    suspects: List[Dict[str, Any]] = []
    for result, person in rows:
        suspects.append(
            {
                "person_id": person.id,
                "nome": person.nome,
                "cargo": person.cargo,
                "orgao": person.orgao,
                "ano": result.ano,
                "risco_score": float(result.risco_score),
                "indice_compatibilidade": result.indice_compatibilidade,
                "excesso_nao_explicado": float(result.excesso_nao_explicado or 0),
                "crescimento_patrimonial": float(result.crescimento_patrimonial or 0),
                "inflows_conhecidos": float(result.inflows_conhecidos or 0),
                "regra_disparo": result.regra_disparo,
                "analisado_em": result.analisado_em.isoformat() if result.analisado_em else None,
            }
        )

    return suspects


def get_people_ranking(db: Session, limit: int = 5000, include_sem_dados: bool = False) -> List[Dict[str, Any]]:
    """
    Return all active people with latest analysis and risk categorization.
    """
    latest_subquery = (
        db.query(
            FiscalAnalysisResult.person_id.label("person_id"),
            func.max(FiscalAnalysisResult.ano).label("max_ano"),
        )
        .group_by(FiscalAnalysisResult.person_id)
        .subquery()
    )

    rows = (
        db.query(FiscalPerson, FiscalAnalysisResult)
        .outerjoin(
            latest_subquery,
            latest_subquery.c.person_id == FiscalPerson.id,
        )
        .outerjoin(
            FiscalAnalysisResult,
            (FiscalAnalysisResult.person_id == FiscalPerson.id) &
            (FiscalAnalysisResult.ano == latest_subquery.c.max_ano),
        )
        .filter(FiscalPerson.ativo.is_(True))
        .order_by(desc(func.coalesce(FiscalAnalysisResult.risco_score, 0)), FiscalPerson.nome.asc())
        .limit(limit)
        .all()
    )

    result: List[Dict[str, Any]] = []
    for person, analysis in rows:
        coverage_rows = (
            db.query(FiscalFinancialRecord.tipo, func.count(FiscalFinancialRecord.id))
            .filter(FiscalFinancialRecord.person_id == person.id)
            .group_by(FiscalFinancialRecord.tipo)
            .all()
        )
        coverage_by_type = {tipo: int(count) for tipo, count in coverage_rows}
        coverage_types = sorted(list(coverage_by_type.keys()))
        has_records = bool(coverage_types)
        sufficient_for_analysis = (
            "patrimonio_declarado" in coverage_by_type and
            (
                "salario" in coverage_by_type or
                "doacao_recebida" in coverage_by_type or
                "financiamento_publico" in coverage_by_type or
                "renda_extra" in coverage_by_type
            )
        )

        if analysis:
            score = float(analysis.risco_score or 0)
            level = _risk_level(score)
            unexplained = float(analysis.excesso_nao_explicado or 0)
            compat = analysis.indice_compatibilidade
            ano = analysis.ano
        else:
            score = 5.0 if has_records else 0.0
            level = "MINIMO" if has_records else "SEM_DADOS"
            unexplained = 0.0
            compat = None
            ano = (
                db.query(func.max(FiscalFinancialRecord.ano))
                .filter(FiscalFinancialRecord.person_id == person.id)
                .scalar()
            )

        if (not include_sem_dados) and level == "SEM_DADOS":
            continue

        result.append(
            {
                "person_id": person.id,
                "nome": person.nome,
                "cargo": person.cargo,
                "orgao": person.orgao,
                "ano_referencia": ano,
                "risco_score": score,
                "nivel_suspeita": level,
                "indice_compatibilidade": compat,
                "excesso_nao_explicado": unexplained,
                "sinalizado": bool(analysis.sinalizado) if analysis else False,
                "cobertura": {
                    "tipos": coverage_types,
                    "registros_por_tipo": coverage_by_type,
                    "suficiente_para_analise": sufficient_for_analysis,
                },
            }
        )

    return result


def get_overview(db: Session) -> Dict[str, Any]:
    total_people = db.query(func.count(FiscalPerson.id)).scalar() or 0
    active_people = db.query(func.count(FiscalPerson.id)).filter(FiscalPerson.ativo.is_(True)).scalar() or 0
    total_records = db.query(func.count(FiscalFinancialRecord.id)).scalar() or 0
    total_results = db.query(func.count(FiscalAnalysisResult.id)).scalar() or 0
    total_flagged = db.query(func.count(FiscalAnalysisResult.id)).filter(FiscalAnalysisResult.sinalizado.is_(True)).scalar() or 0

    return {
        "pessoas_total": int(total_people),
        "pessoas_ativas": int(active_people),
        "registros_financeiros": int(total_records),
        "analises_total": int(total_results),
        "analises_sinalizadas": int(total_flagged),
    }


def _merge_person_into(db: Session, source_person_id: int, target_person_id: int) -> None:
    if source_person_id == target_person_id:
        return

    # Move financial records with de-duplication on the natural key used by _upsert_financial_record.
    source_records = db.query(FiscalFinancialRecord).filter(FiscalFinancialRecord.person_id == source_person_id).all()
    for rec in source_records:
        existing = db.query(FiscalFinancialRecord).filter(
            FiscalFinancialRecord.person_id == target_person_id,
            FiscalFinancialRecord.ano == rec.ano,
            FiscalFinancialRecord.tipo == rec.tipo,
            FiscalFinancialRecord.fonte == rec.fonte,
            FiscalFinancialRecord.data_referencia == rec.data_referencia,
        ).first()
        if existing:
            existing.valor = (existing.valor or Decimal("0")) + (rec.valor or Decimal("0"))
            existing.confianca = max(float(existing.confianca or 0), float(rec.confianca or 0))
            existing.extra_json = _merge_metadata(existing.extra_json, rec.extra_json)
            db.delete(rec)
        else:
            rec.person_id = target_person_id

    # Move analysis rows while respecting unique (person_id, ano).
    source_analyses = db.query(FiscalAnalysisResult).filter(FiscalAnalysisResult.person_id == source_person_id).all()
    for src in source_analyses:
        tgt = db.query(FiscalAnalysisResult).filter(
            FiscalAnalysisResult.person_id == target_person_id,
            FiscalAnalysisResult.ano == src.ano,
        ).first()
        if not tgt:
            src.person_id = target_person_id
            continue

        # Merge by keeping strongest risk and most informative fields.
        tgt.risco_score = max(float(tgt.risco_score or 0), float(src.risco_score or 0))
        tgt.sinalizado = bool(tgt.sinalizado or src.sinalizado)
        if (tgt.excesso_nao_explicado or Decimal("0")) < (src.excesso_nao_explicado or Decimal("0")):
            tgt.excesso_nao_explicado = src.excesso_nao_explicado
            tgt.crescimento_patrimonial = src.crescimento_patrimonial
            tgt.inflows_conhecidos = src.inflows_conhecidos
            tgt.indice_compatibilidade = src.indice_compatibilidade
            tgt.regra_disparo = src.regra_disparo
            tgt.detalhes_json = src.detalhes_json
            tgt.patrimonio_anterior = src.patrimonio_anterior
            tgt.patrimonio_atual = src.patrimonio_atual
            tgt.analisado_em = src.analisado_em
        db.delete(src)

    db.query(FiscalPerson).filter(FiscalPerson.id == source_person_id).delete(synchronize_session=False)


def reconcile_people_identities(db: Session) -> Dict[str, Any]:
    """
    Normalize legacy identity keys and merge obvious duplicates.
    """
    people = db.query(FiscalPerson).order_by(FiscalPerson.id.asc()).all()
    normalized_hash_map: Dict[str, int] = {}
    normalized_name_map: Dict[str, int] = {}
    merged_count = 0
    hash_normalized = 0

    for person in people:
        new_hash = person.cpf_hash
        if person.cpf_hash and person.cpf_hash.startswith(("tse:", "cpf:")):
            maybe_hash = person.cpf_hash.split(":", 1)[1]
            if len(maybe_hash) == 64:
                new_hash = maybe_hash
                hash_normalized += 1
        elif person.cpf_hash and person.cpf_hash.startswith("autor_emenda:"):
            new_hash = None
            hash_normalized += 1

        if new_hash and new_hash in normalized_hash_map and normalized_hash_map[new_hash] != person.id:
            _merge_person_into(db, person.id, normalized_hash_map[new_hash])
            merged_count += 1
            continue

        if new_hash:
            person.cpf_hash = new_hash
            normalized_hash_map[new_hash] = person.id

        name_key = _normalize_name_key(person.nome)
        dedupe_key = f"{name_key}|{(person.cargo or '').lower()}|{(person.orgao or '').lower()}"
        if name_key and dedupe_key in normalized_name_map and normalized_name_map[dedupe_key] != person.id:
            _merge_person_into(db, person.id, normalized_name_map[dedupe_key])
            merged_count += 1
            continue

        if name_key:
            normalized_name_map[dedupe_key] = person.id

    db.commit()
    return {
        "hashes_normalizados": hash_normalized,
        "duplicatas_mescladas": merged_count,
    }


def _latest_analysis_for_person(db: Session, person_id: int) -> Optional[FiscalAnalysisResult]:
    return (
        db.query(FiscalAnalysisResult)
        .filter(FiscalAnalysisResult.person_id == person_id)
        .order_by(desc(FiscalAnalysisResult.ano))
        .first()
    )


def _detect_patterns_for_person(db: Session, person: FiscalPerson) -> List[Dict[str, Any]]:
    insights: List[Dict[str, Any]] = []
    latest = _latest_analysis_for_person(db, person.id)

    year_agg_rows = (
        db.query(
            FiscalFinancialRecord.ano.label("ano"),
            FiscalFinancialRecord.tipo.label("tipo"),
            func.sum(FiscalFinancialRecord.valor).label("valor_total"),
        )
        .filter(FiscalFinancialRecord.person_id == person.id)
        .group_by(FiscalFinancialRecord.ano, FiscalFinancialRecord.tipo)
        .all()
    )
    by_year: Dict[int, Dict[str, Decimal]] = {}
    for row in year_agg_rows:
        by_year.setdefault(row.ano, {})[row.tipo] = Decimal(row.valor_total or 0)

    # P10 Enriquecimento ilícito
    if latest and latest.sinalizado:
        confidence = min(99, max(70, int(latest.risco_score + 50)))
        severity = "Crítico" if confidence > 90 else "Alto" if confidence >= 70 else "Médio"
        insights.append(
            {
                "pattern_id": "P10",
                "titulo": "Enriquecimento ilícito",
                "descricao": latest.regra_disparo or "Crescimento patrimonial acima da renda conhecida.",
                "impacto": float(latest.excesso_nao_explicado or 0),
                "confidence": confidence,
                "severity": severity,
                "fontes": ["TSE Bens", "Portal Transparência", "SICONFI"],
                "ano": latest.ano,
            }
        )

    # P04 Doação ↔ contrato (proxy via financiamento público + doação)
    for year, values in by_year.items():
        donation = values.get("doacao_recebida", Decimal("0"))
        public_funding = values.get("financiamento_publico", Decimal("0"))
        if donation > 0 and public_funding > 0:
            impact = float(min(donation, public_funding))
            confidence = 78
            insights.append(
                {
                    "pattern_id": "P04",
                    "titulo": "Circuito fechado doação ↔ contrato",
                    "descricao": f"Há doações ({donation}) e financiamento público ({public_funding}) no mesmo período.",
                    "impacto": impact,
                    "confidence": confidence,
                    "severity": "Alto",
                    "fontes": ["TSE Doações", "Portal Transparência", "ComprasNet/PNCP"],
                    "ano": year,
                }
            )

    # P01 Auto-direcionamento de emendas (proxy)
    for year, values in by_year.items():
        emendas = values.get("financiamento_publico", Decimal("0"))
        if emendas >= Decimal("1000000"):
            insights.append(
                {
                    "pattern_id": "P01",
                    "titulo": "Auto-direcionamento de emendas",
                    "descricao": "Volume elevado de emendas/financiamento público associado ao mesmo ator.",
                    "impacto": float(emendas),
                    "confidence": 74,
                    "severity": "Alto",
                    "fontes": ["Portal Transparência", "TransfereGov"],
                    "ano": year,
                }
            )

    insights.sort(key=lambda i: (i["confidence"], i["impacto"]), reverse=True)
    return insights


def analyze_cpf_report(db: Session, cpf: str) -> Dict[str, Any]:
    cpf_hashes = _possible_cpf_hashes(cpf)
    person = db.query(FiscalPerson).filter(FiscalPerson.cpf_hash.in_(cpf_hashes)).first()
    if not person:
        return {
            "cpf": _normalize_cpf(cpf),
            "found": False,
            "message": "CPF não encontrado nas bases ingeridas. Rode os conectores de doações/bens/salários.",
            "insights": [],
            "timeline": [],
            "entity_graph": {"nodes": [], "edges": []},
            "summary": {
                "exposicao_total": 0.0,
                "irregularidades": 0,
                "fontes": 0,
                "entidades": 0,
                "conexoes": 0,
                "alertas": 0,
            },
        }

    insights = _detect_patterns_for_person(db, person)

    records = (
        db.query(FiscalFinancialRecord)
        .filter(FiscalFinancialRecord.person_id == person.id)
        .order_by(FiscalFinancialRecord.ano.asc(), FiscalFinancialRecord.data_referencia.asc().nullslast())
        .all()
    )

    timeline_raw: List[Dict[str, Any]] = []
    sources_set = set()
    nodes = [{"id": f"person:{person.id}", "label": person.nome, "type": "pessoa"}]
    edges = []
    for rec in records:
        date_key = f"{rec.ano}-{(rec.data_referencia.month if rec.data_referencia else 1):02d}"
        category = "FINANCEIRO"
        if rec.tipo == "patrimonio_declarado":
            category = "PESSOA"
        elif rec.tipo == "financiamento_publico":
            category = "CONTRATO"
        timeline_raw.append(
            {
                "date": date_key,
                "category": category,
                "source": rec.fonte,
                "text": f"{rec.tipo}: {float(rec.valor)}",
            }
        )
        sources_set.add(rec.fonte)
        source_node_id = f"source:{rec.fonte}"
        if all(n["id"] != source_node_id for n in nodes):
            nodes.append({"id": source_node_id, "label": rec.fonte, "type": "fonte"})
        edges.append({"from": f"person:{person.id}", "to": source_node_id, "label": rec.tipo})

    for insight in insights:
        timeline_raw.append(
            {
                "date": f"{insight.get('ano', datetime.now().year)}-12",
                "category": "REGULATÓRIO",
                "source": ",".join(insight["fontes"]),
                "text": insight["titulo"],
            }
        )
        for src in insight["fontes"]:
            sources_set.add(src)

    dedup = {(t["date"], t["category"], t["source"], t["text"]): t for t in timeline_raw}
    timeline = sorted(dedup.values(), key=lambda t: t["date"])

    exposicao_total = float(sum(max(0.0, i["impacto"]) for i in insights))
    critical_alerts = sum(1 for i in insights if i["severity"] == "Crítico")

    return {
        "cpf": _normalize_cpf(cpf),
        "found": True,
        "person": {
            "id": person.id,
            "nome": person.nome,
            "cargo": person.cargo,
            "orgao": person.orgao,
        },
        "summary": {
            "exposicao_total": exposicao_total,
            "irregularidades": len(insights),
            "fontes": len(sources_set),
            "entidades": len(nodes),
            "conexoes": len(edges),
            "alertas": critical_alerts,
        },
        "insights": insights,
        "timeline": timeline,
        "entity_graph": {"nodes": nodes, "edges": edges},
        "supported_patterns": PATTERN_IDS,
    }


def seed_demo_data(db: Session) -> Dict[str, Any]:
    """Create deterministic sample data so the UI can be used immediately."""
    demo_cpf = "11111111111"
    demo_person = upsert_person(
        db,
        {
            "nome": "Exemplo Deputado",
            "cargo": "deputado",
            "orgao": "camara",
            "cpf_hash": _cpf_hash(demo_cpf),
            "metadata_json": {"demo": True},
        },
    )

    # Keep demo deterministic across multiple executions.
    db.query(FiscalFinancialRecord).filter(FiscalFinancialRecord.person_id == demo_person.id).delete()
    db.commit()

    add_financial_records(
        db,
        demo_person.id,
        [
            {"ano": 2022, "tipo": "patrimonio_declarado", "valor": 800000, "fonte": "declaracao_tse"},
            {"ano": 2023, "tipo": "patrimonio_declarado", "valor": 900000, "fonte": "declaracao_tse"},
            {"ano": 2023, "tipo": "salario", "valor": 39600 * 12, "fonte": "portal_transparencia"},
            {"ano": 2023, "tipo": "doacao_recebida", "valor": 120000, "fonte": "portal_transparencia"},
            {"ano": 2024, "tipo": "patrimonio_declarado", "valor": 2200000, "fonte": "declaracao_tse"},
            {"ano": 2024, "tipo": "salario", "valor": 42000 * 12, "fonte": "portal_transparencia"},
            {"ano": 2024, "tipo": "doacao_recebida", "valor": 180000, "fonte": "portal_transparencia"},
            {"ano": 2024, "tipo": "financiamento_publico", "valor": 220000, "fonte": "tesouro_siconfi"},
        ],
    )

    return {"person_id": demo_person.id, "cpf": demo_cpf}
