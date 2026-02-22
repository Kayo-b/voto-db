# Investigação Patrimonial: arquitetura proposta

## Objetivo
Detectar crescimento patrimonial potencialmente incompatível com renda e fontes declaradas de agentes públicos (deputados, senadores, juízes, presidentes e ex-presidentes), usando dados públicos abertos com resposta rápida via banco local.

## Fontes priorizadas (extraídas de `open-gov-data.md`)
1. `portaldatransparencia.gov.br/api-de-dados` (remuneração, transferências, beneficiários)
2. `dadosabertos.camara.leg.br/api/v2` (deputados, despesas e atividade)
3. `www12.senado.leg.br/dados-abertos` (senadores e despesas)
4. `apidatalake.tesouro.gov.br` (SICONFI/Tesouro)
5. `datajud-wiki.cnj.jus.br` (DataJud para trilhas no Judiciário)
6. `inlabs.gov.br/api` (DOU: nomeações/exonerações/atos)
7. `pncp.gov.br/api/pncp/v1` (contratações públicas e fornecedores)

## Modelo de dados implementado
- `fiscal_pessoas`: cadastro consolidado do agente público
- `fiscal_registros_financeiros`: registros normalizados (`tipo`, `ano`, `valor`, `fonte`)
- `fiscal_resultados_analise`: resultado anual pré-calculado (risco, excesso não explicado, regra de disparo)

## Fluxo
1. Ingestão por fonte (conectores por órgão) e normalização para `fiscal_registros_financeiros`.
2. Engine de análise anual calcula:
   - `crescimento_patrimonial = patrimonio_atual - patrimonio_anterior`
   - `inflows_conhecidos = salario + doacao_recebida + financiamento_publico + renda_extra`
   - `excesso_nao_explicado = crescimento_patrimonial - inflows_conhecidos`
3. Resultado persistido em `fiscal_resultados_analise` para consultas instantâneas no frontend.

## Regras iniciais de sinalização
- Crescimento patrimonial positivo
- Excesso não explicado >= R$100.000
- Índice de compatibilidade < 0.70

Esses parâmetros são configuráveis pela API.

## Endpoints implementados
- `GET /fiscal-investigation/sources`
- `GET /fiscal-investigation/overview`
- `POST /fiscal-investigation/person`
- `POST /fiscal-investigation/records`
- `POST /fiscal-investigation/sync/portal-transparencia`
- `POST /fiscal-investigation/sync/public-financing`
- `POST /fiscal-investigation/sync/donations`
- `POST /fiscal-investigation/analyze`
- `GET /fiscal-investigation/suspects`
- `GET /fiscal-investigation/people-ranking`
- `GET /fiscal-investigation/sync/status`
- `POST /fiscal-investigation/demo-seed`

### Requisito de autenticação (Portal da Transparência)
- Definir `PORTAL_TRANSPARENCIA_API_KEY` no backend.
- Header usado no conector: `chave-api-dados`.
- Para agendamento automático:
  - `ENABLE_FISCAL_AUTO_SYNC=true`
  - `FISCAL_AUTO_SYNC_INTERVAL_SECONDS=86400` (exemplo diário)
  - `TSE_DONATIONS_CSV_URL=https://...csv|zip` (opcional para incluir doações no job automático)

## Fases sugeridas para produção
1. Conectores robustos para Câmara, Senado e Portal da Transparência.
2. Resolvedor de identidade (deduplicação por CPF hash, nome, cargo e período).
3. Enriquecimento com TSE/declarações patrimoniais eleitorais (quando aplicável).
4. Auditoria de qualidade: trilha de fonte e nível de confiança por registro.
5. Painel de revisão manual para falsos positivos.
