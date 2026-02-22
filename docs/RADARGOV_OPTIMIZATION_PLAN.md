# RadarGov - Plano de Otimizacao de Resultados

Data de referencia da analise: 22/02/2026.
Escopo: somente motor de cruzamento fiscal (sem modulo de votacoes nominais).

## 1) Objetivo tecnico
Aumentar taxa de casos investigaveis (reduzir `SEM_DADOS`) e elevar qualidade dos achados (`ALTO/CRITICO`) com base em dados publicos oficiais.

## 2) APIs disponiveis e funcionando (validadas)

### 2.1 APIs ja integradas no app
1. `Portal da Transparencia` (`https://api.portaldatransparencia.gov.br/api-de-dados`)
- Endpoints em uso: `/servidores/por-orgao`, `/servidores`, `/servidores/remuneracao`, `/emendas`.
- Campos uteis observados: orgao SIAPE, id servidor, nome, CPF (quando exposto), valor remuneracao, valor pago/liquidado de emenda, autor.
- Status: funcionando com chave `chave-api-dados`.

2. `Camara dos Deputados` (`https://dadosabertos.camara.leg.br/api/v2`)
- Endpoints em uso: `/deputados`, `/deputados/{id}/despesas`.
- Campos uteis observados: `id`, `nome`, `siglaPartido`, `siglaUf`, `valorLiquido`, `valorDocumento`, `cnpjCpfFornecedor`, `nomeFornecedor`.
- Status: funcionando, com instabilidade eventual de conexao (necessario retry).

3. `TSE Dados Abertos` (via CSV/ZIP URL)
- Endpoints em uso no app: ingestao de `doacoes`, `bens`, `candidaturas` por arquivo publico.
- Campos uteis: nome candidato, CPF candidato (quando presente), cargo, UF, partido, valor receita, valor bem.
- Status: funcionando.

4. `PNCP/ComprasNet` (`https://pncp.gov.br/api/consulta/v1`)
- Endpoint em uso: `/contratos`.
- Campos uteis observados: `niFornecedor`, `nomeRazaoSocialFornecedor`, `valorGlobal`, `valorInicial`, `orgaoEntidade`, `numeroControlePNCP`, `anoContrato`, `objetoContrato`.
- Status: funcionando (parametros obrigatorios: `dataInicial`, `dataFinal`, `pagina`, `tamanhoPagina >= 10`).

### 2.2 APIs externas funcionais e ainda nao conectadas ao scoring atual
1. `BCB SGS/Olinda` (`api.bcb.gov.br`, `olinda.bcb.gov.br`)
- Retornos: series economicas (`data`, `valor`).
- Uso potencial: deflatores/normalizacao temporal.

2. `IBGE SIDRA` (`servicodados.ibge.gov.br`)
- Retornos: metadados de agregado + `resultados`.
- Uso potencial: baseline regional/setorial.

## 3) Cruzamentos possiveis com dados atuais

## Ja possivel hoje
1. Patrimonio declarado (TSE bens) x entradas conhecidas (salario + doacao + emenda + renda_extra PNCP) por ano.
2. Ranking de risco por pessoa com cobertura por tipo de dado.
3. Timeline e insights por CPF com fontes citadas.

## Limitacoes atuais
1. Muitos casos so com `financiamento_publico` (sem patrimonio e/ou sem salario) => nivel `MINIMO`.
2. `PNCP` tende a trazer fornecedor PJ; match com pessoa fisica (politico/servidor) e baixo sem camada de beneficiario final/QSA.
3. Salarios federais podem retornar `processados` sem `upsert` em alguns recortes de mes/ano.
4. Reconsolidacao de identidades precisa ser robusta para evitar duplicata por nome/hash legado.

## 4) Dados faltantes criticos e como obter por API
1. Beneficiario final de fornecedor (QSA/CNPJ)
- Falta: vinculo fornecedor PJ -> pessoa fisica relacionada.
- Fonte/API: Receita Federal CNPJ/QSA (quando disponivel via dados abertos/espelhos oficiais), juntas comerciais.

2. Contratos com detalhamento de adjudicatario/participacao
- Falta: granularidade para P04/P06/P08.
- Fonte/API: PNCP compras/itens/resultado (expandir endpoints), Compras.gov.

3. Sancoes/compliance
- Falta: CEIS/CNEP/CEAF/CEPIM vinculados a fornecedor/pessoa.
- Fonte/API: Portal da Transparencia (bases CGU).

4. Divida ativa e habilitacao
- Falta: PGFN + SICAF para regra `divida ativa x contrato ativo`.
- Fonte/API: PGFN e SICAF (conectores dedicados).

5. Senado (despesas/verbas)
- Falta: cobertura de senadores no mesmo nivel da Camara.
- Fonte/API: Dados abertos do Senado.

## 5) Metodos de deteccao usados por fiscalizacao (equivalentes tecnicos)
1. Analise de compatibilidade patrimonial
- Crescimento de patrimonio vs renda declarada/justificavel no periodo.

2. Consistencia declaratoria multi-fonte
- Diferencas entre declaracoes (eleitoral/fiscal/contratual) e movimentacao observada.

3. Sinais de interposicao de terceiros
- Fornecedor ligado a familiares/socios e contratacao recorrente com ente favorecido.

4. Padroes temporais suspeitos
- Entrada relevante antes/depois de contratos, emendas, eleicoes, nomeacoes.

5. Analise de rede
- Pessoa -> empresa -> contrato -> orgao -> decisor (grafo de relacoes).

6. Priorizacao por risco composto
- Magnitude financeira, repeticao, recencia, numero de fontes independentes, forca do vinculo.

## 6) Plano de implementacao (priorizado)
1. Confiabilidade de ingestao
- Retries, timeout por conector, falha parcial sem abortar pipeline.

2. Resolucao de identidade
- Chaves canônicas de CPF, normalizacao de nomes, merge seguro de duplicatas com deduplicacao de analises por ano.

3. Cobertura de entradas financeiras
- Camara despesas (ja integrado), PNCP contratos (ja integrado), expandir para Senado e sancoes CGU.

4. Motor de regras
- Evoluir de proxy para regras P04/P06/P08 com evidencias estruturadas.

5. Observabilidade investigativa
- Cobertura por pessoa, fontes usadas no score, motivo de classificacao, lacunas por entidade.

## 7) Criterios de sucesso
1. Queda de `SEM_DADOS` e `MINIMO` para entidades com cobertura multipla.
2. Aumento de casos com score util (`ALTO/CRITICO`) sustentados por >=2 fontes independentes.
3. Reprodutibilidade: mesmas entradas => mesmos resultados.
4. Pipeline resiliente: erro de uma API nao derruba ciclo completo.

