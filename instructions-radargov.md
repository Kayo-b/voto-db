You are building a Brazilian political corruption detection platform called something like "RadarGov" or "VigilanteBR". Here is the full product specification:

---

## PRODUCT OVERVIEW

A dark-themed intelligence dashboard that ingests 79+ Brazilian open government databases, cross-references them using a politician's CPF as the primary key, and automatically surfaces corruption patterns with risk scores, financial exposure totals, and chronological event timelines.

---

## CORE ARCHITECTURE

**Input:** CPF of a politician (or public figure)
**Output:** A structured intelligence report with:
- Total financial exposure (e.g. R$89.2M)
- Count of irregularities, entities, connections, sources, and alerts
- Ranked list of "insights" by criticality (Crítico / Alto / Médio / Baixo)
- Full chronological timeline of events across all data sources
- Entity graph showing connections between people, companies, contracts, and assets

---

## UI LAYOUT (from screenshots)

### Top Bar
- LIVE indicator (real-time or last-sync badge)
- 4 KPI counters: ENTIDADES | CONEXÕES | FONTES | ALERTAS
- All in high-contrast colored numbers on dark background

### Main Tabs
- **INSIGHTS** (default) — ranked irregularities list
- **DETALHE** — entity detail / graph view

### Insights Panel
- Header card: "EXPOSIÇÃO TOTAL" with large monetary value (e.g. R$89.2M), irregularity count, and source count
- Filter tabs: Todos | Crítico | Alto | Médio (with counts)
- Each insight card contains:
  - Severity badge (CRÍTICO / ALTO / MÉDIO) with % confidence score (e.g. 97%)
  - Title (e.g. "Auto-direcionamento de emendas")
  - Financial impact with money bag icon (e.g. R$47M)
  - Descriptive paragraph explaining the irregularity
  - PATTERN block: shows the detected corruption pattern as a flow (e.g. EMENDA → PREFEITURA ALIADA → CONTRATOS FAMÍLIA)
  - Source tags (e.g. Transparência, Compras.gov, TransfereGov, Receita Federal, TSE)

### Timeline Panel (left/secondary view)
- Title: "LINHA DO TEMPO — EVENTOS CRONOLÓGICOS"
- Vertical timeline with colored dot indicators per event type
- Each event card shows:
  - Date (YYYY-MM format)
  - Category badge with color coding:
    - JURÍDICO (orange)
    - EMPRESA (orange)
    - PESSOA (orange)
    - AMBIENTAL (teal/green)
    - FINANCEIRO (blue)
    - REGULATÓRIO (teal)
    - SAÚDE (pink)
    - CONTRATO (green)
  - Source label (right-aligned, subdued)
  - Event description (1-2 lines)
- Sensitive entity names are redacted with gray blur/block overlays

---

## DATA SOURCES TO INTEGRATE (79 databases)

Group them by domain for the ingestion pipeline:

**Corporate/Financial:** Portal Dados Abertos, Receita Federal CNPJ/QSA, Juntas Comerciais, CVM Aberta, Formulário Referência CVM, Fatos Relevantes CVM, Insider Trading CVM, Fundos de Investimento CVM, B3 Negociações, BCB Câmbio/PTAX, BCB Selic/Juros, BCB PIX, BCB Crédito, BCB IFData, BCB Base Monetária, BCB Reservas Internacionais, BCB Capitais Estrangeiros

**Transparency/Spending:** Portal da Transparência, Tesouro Transparente, Base dos Dados, SIAFI, SICONFI, SIOP, ComprasNet/PNCP, FNDE Repasses, TCU Auditorias, TCEs/TCMs

**Sanctions/Compliance:** CEIS (CGU), CNEP (CGU), CEPIM (CGU), CEAF (CGU), PGFN Dívida Ativa, SICAF

**Electoral:** TSE Candidaturas, TSE Bens Declarados, TSE Doações, TSE Resultados Eleitorais

**Health:** DATASUS SIH, DATASUS SIM, DATASUS CNES, DATASUS SINAN, INSS/DATAPREV, PREVIC, ANS, ANVISA

**Legal/Judicial:** DataJud CNJ, DOU, DOEs Estaduais, Querido Diário

**Demographics/Economy:** IBGE Censo, IBGE PNAD, IBGE IPCA/INPC, IBGE PIB, IBGE PMC, IBGE PIM-PF, IBGE POF, IBGE Geociências, IPEAData

**Education:** INEP Censo Escolar, INEP ENEM

**Employment:** RAIS, CAGED

**Environment/Land:** IBAMA Embargos, IBAMA Licenciamento, IBAMA SINAFLOR, INPE DETER, INPE PRODES, CAR/SICAR, INCRA, CPRM, INDE

**Transport/Infrastructure:** DENATRAN/RENAVAM, ANAC RAB, ANTT, ANTAQ, DNIT, PRF Acidentes

**Regulation:** ANEEL, ANP, ANATEL, ANCINE

---

## CORRUPTION PATTERN DETECTION ENGINE

The system must detect and score these pattern types:

1. **Auto-direcionamento de emendas** — politician directs public amendments to municipalities that then contract family-owned companies
2. **Funcionários fantasma** — payroll entries for individuals with no work evidence, cross-referenced with RAIS/CAGED
3. **Escola/entidade fantasma** — entities receiving FNDE/SIAFI transfers with no physical presence or activity in INEP/DATASUS
4. **Circuito fechado doação ↔ contrato** — campaign donor receives public contract shortly after election (TSE Doações × ComprasNet)
5. **Empresa laranja offshore** — company registered in tax haven (Panama, BVI) with beneficial owner linked to politician via QSA/CVM
6. **Licitação direcionada** — sole bidder contracts, waived bidding (dispensa), repeated vendor in same municipality
7. **Desmatamento × mandato** — land deforestation (INPE/IBAMA) correlated with politician's land assets (TSE Bens) and CAR/INCRA records
8. **Dívida ativa × contratos ativos** — entity with PGFN active debt simultaneously holding active government contracts (SICAF violation)
9. **Insider trading** — asset declaration changes (TSE Bens) correlated with CVM insider trading registry and B3 trading data
10. **Enriquecimento ilícito** — asset growth between mandates disproportionate to declared income

---

## SCORING LOGIC

Each detected pattern gets:
- **Confidence score (0–100%)** based on: number of corroborating sources, recency, financial magnitude, directness of link
- **Severity tier:** Crítico (>90%), Alto (70–90%), Médio (50–70%), Baixo (<50%)
- **Financial exposure:** sum of all monetary values directly or indirectly attributable to the irregularity

---

## TECH STACK GUIDANCE

- **Data ingestion:** Python async pipeline per source, normalized into a graph database (Neo4j or similar) with CPF/CNPJ as primary node keys
- **Entity resolution:** fuzzy name matching + CPF/CNPJ exact match to link individuals across sources
- **Pattern detection:** rule-based graph traversal + optional ML anomaly scoring
- **API layer:** FastAPI serving `/analyze/{cpf}` returning structured JSON
- **Frontend:** React + dark theme, monospace font (matching screenshots), real-time websocket updates for LIVE indicator
- **Redaction layer:** configurable — blur sensitive third-party entity names in public-facing mode

---

## KEY CONSTRAINTS

- All data sources are public Brazilian open data — no private data access required
- CPF is the root entity; all connections expand outward from it
- Timeline must be deduplicated and sorted chronologically across all sources
- Insight cards must always cite which source(s) support the finding
- System must handle politicians with no irregularities gracefully (empty state)
- Redaction of related third-party names must be toggleable for investigative vs. public modes
