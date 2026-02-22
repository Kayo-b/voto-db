# Portais Brasileiros com API Disponível e Funcional

| # | Portal | URL / Endpoint Base | Documentação / Observações |
|---|--------|--------------------|-----------------------------|
| 1 | Portal Dados Abertos | dados.gov.br | CKAN API + Swagger; token para escrita |
| 2 | Portal da Transparência | portaldatransparencia.gov.br/api-de-dados | REST; chave gratuita; limite 90 req/min |
| 3 | Tesouro Transparente / SICONFI | apidatalake.tesouro.gov.br | REST documentada |
| 4 | Base dos Dados | basedosdados.org | Python/R via BigQuery; cota gratuita |
| 5 | CEIS (CGU) | portaldatransparencia.gov.br/api-de-dados | Mesma API do Portal da Transparência |
| 6 | CNEP (CGU) | portaldatransparencia.gov.br/api-de-dados | Mesma API do Portal da Transparência |
| 7 | CEPIM (CGU) | portaldatransparencia.gov.br/api-de-dados | Mesma API do Portal da Transparência |
| 8 | CEAF (CGU) | portaldatransparencia.gov.br/api-de-dados | Mesma API do Portal da Transparência |
| 9 | ComprasNet / PNCP | pncp.gov.br/api/pncp/v1 | REST documentada; sem autenticação |
| 10 | BCB Câmbio / PTAX | olinda.bcb.gov.br | OData; sem autenticação |
| 11 | BCB Selic / Juros | api.bcb.gov.br / olinda.bcb.gov.br | SGS + OData; sem autenticação |
| 12 | BCB PIX | dadosabertos.bcb.gov.br | REST documentada |
| 13 | BCB Crédito | dadosabertos.bcb.gov.br | OData parcial + CSV |
| 14 | BCB IFData | olinda.bcb.gov.br | OData Swagger documentado |
| 15 | BCB Base Monetária | api.bcb.gov.br/dados/serie/bcdata.sgs.{id} | SGS série temporal |
| 16 | BCB Reservas Internacionais | api.bcb.gov.br/dados/serie/bcdata.sgs.{id} | SGS série temporal |
| 17 | BCB Capitais Estrangeiros | dadosabertos.bcb.gov.br | REST documentada |
| 18 | DOU / INLabs | inlabs.gov.br/api | REST; chave gratuita mediante cadastro |
| 19 | Querido Diário | queridodiario.ok.org.br/api | REST (OKBR); ~750+ municípios |
| 20 | DataJud CNJ | datajud-wiki.cnj.jus.br | Elasticsearch API; chave gratuita |
| 21 | IBGE Censo | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 22 | IBGE PNAD | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 23 | IBGE IPCA / INPC | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 24 | IBGE PIB | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 25 | IBGE PMC | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 26 | IBGE PIM-PF | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 27 | IBGE POF | servicodados.ibge.gov.br/api | REST SIDRA documentada |
| 28 | IBGE Geociências | geoservicos.ibge.gov.br | WMS / WFS / FTP |
| 29 | FNDE Repasses | portaldatransparencia.gov.br/api-de-dados | Via API Portal da Transparência |
| 30 | DATASUS CNES | cnes.datasus.gov.br/pages/sobre/api.jsp | REST documentada |
| 31 | INPE DETER | terrabrasilis.dpi.inpe.br/geonetwork | REST + WMS / WFS |
| 32 | INPE PRODES | terrabrasilis.dpi.inpe.br | REST + download shapefile |
| 33 | INCRA | acervofundiario.incra.gov.br | WFS / WMS geoespacial |
| 34 | CPRM | geosgb.cprm.gov.br | WMS / WFS documentado |
| 35 | INDE | inde.gov.br | OGC (WMS / WFS / WCS / CSW) |
| 36 | IPEAData | ipeadata.gov.br/api | REST documentada; sem autenticação |

---

**Notas**
- Todos os endpoints do BCB estão sob `olinda.bcb.gov.br` (OData) ou `api.bcb.gov.br` (SGS).
- Todos os agregados do IBGE estão sob `servicodados.ibge.gov.br/api/v3/agregados`.
- INCRA, CPRM e INDE expõem padrões OGC (geoespacial), não REST convencional.
- DataJud requer cadastro gratuito para obter chave em `datajud-wiki.cnj.jus.br`.
- Base dos Dados requer projeto Google Cloud para acessar o BigQuery.

