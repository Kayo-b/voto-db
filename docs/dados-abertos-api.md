i# API Dados Abertos - Câmara dos Deputados

## Informações Gerais

**Base URL**: `https://dadosabertos.camara.leg.br/api/v2`  
**Formato**: JSON e XML  
**Autenticação**: Não requer  
**Rate Limit**: Não documentado oficialmente

## Estrutura de Resposta Padrão

```json
{
  "dados": [...],
  "links": [
    {
      "rel": "self",
      "href": "URL_atual"
    },
    {
      "rel": "first",
      "href": "URL_primeira_pagina"
    },
    {
      "rel": "last",
      "href": "URL_ultima_pagina"
    }
  ]
}
```

## Paginação

Todos os endpoints que retornam listas aceitam:
- `pagina`: número da página (padrão: 1)
- `itens`: itens por página (padrão: 15, máx: 100)

---

## 1. Deputados

### Listar Deputados

```
GET /deputados
```

**Parâmetros**:
- `id`: ID do deputado
- `nome`: Nome do deputado (busca parcial)
- `idLegislatura`: ID da legislatura
- `siglaUf`: UF (ex: SP, RJ)
- `siglaPartido`: Sigla do partido
- `siglaSexo`: M ou F
- `ordem`: ASC ou DESC
- `ordenarPor`: nome, idLegislatura, siglaUf, siglaPartido

**Exemplo**:
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/deputados?siglaUf=SP&pagina=1&itens=10"
```

### Detalhes do Deputado

```
GET /deputados/{id}
```

Retorna dados completos: nome civil, data de nascimento, CPF, escolaridade, URLs de redes sociais.

### Despesas do Deputado

```
GET /deputados/{id}/despesas
```

**Parâmetros**:
- `idLegislatura`: ID da legislatura
- `ano`: Ano das despesas
- `mes`: Mês (1-12)
- `cnpjCpfFornecedor`: CPF/CNPJ do fornecedor
- `ordem`: ASC ou DESC
- `ordenarPor`: ano, mes, valor

### Discursos do Deputado

```
GET /deputados/{id}/discursos
```

**Parâmetros**:
- `dataInicio`: Data início (AAAA-MM-DD)
- `dataFim`: Data fim (AAAA-MM-DD)
- `ordenarPor`: dataHoraInicio, dataHoraFim

### Eventos do Deputado

```
GET /deputados/{id}/eventos
```

### Órgãos do Deputado

```
GET /deputados/{id}/orgaos
```

Comissões e órgãos dos quais o deputado é/foi membro.

### Frentes Parlamentares do Deputado

```
GET /deputados/{id}/frentes
```

---

## 2. Proposições

### Listar Proposições

```
GET /proposicoes
```

**Parâmetros**:
- `siglaTipo`: Tipo (PL, PEC, PLP, etc)
- `numero`: Número da proposição
- `ano`: Ano
- `dataInicio`: Data apresentação inicial
- `dataFim`: Data apresentação final
- `idDeputadoAutor`: ID do deputado autor
- `autor`: Nome do autor
- `siglaPartidoAutor`: Partido do autor
- `siglaUfAutor`: UF do autor
- `keywords`: Palavras-chave
- `tramitacaoSenado`: true/false
- `ordem`: ASC ou DESC
- `ordenarPor`: id, siglaTipo, numero, ano, dataApresentacao

**Exemplo**:
```bash
curl "https://dadosabertos.camara.leg.br/api/v2/proposicoes?siglaTipo=PL&ano=2024&itens=50"
```

### Detalhes da Proposição

```
GET /proposicoes/{id}
```

### Autores da Proposição

```
GET /proposicoes/{id}/autores
```

### Votações da Proposição

```
GET /proposicoes/{id}/votacoes
```

### Tramitações da Proposição

```
GET /proposicoes/{id}/tramitacoes
```

### Temas da Proposição

```
GET /proposicoes/{id}/temas
```

### Relacionadas

```
GET /proposicoes/{id}/relacionadas
```

---

## 3. Legislaturas

### Listar Legislaturas

```
GET /legislaturas
```

### Detalhes da Legislatura

```
GET /legislaturas/{id}
```

### Mesa Diretora

```
GET /legislaturas/{id}/mesa
```

---

## 4. Partidos

### Listar Partidos

```
GET /partidos
```

**Parâmetros**:
- `idLegislatura`: ID da legislatura
- `sigla`: Sigla do partido
- `dataInicio`: Data início
- `dataFim`: Data fim

### Detalhes do Partido

```
GET /partidos/{id}
```

### Membros do Partido

```
GET /partidos/{id}/membros
```

---

## 5. Blocos

### Listar Blocos Partidários

```
GET /blocos
```

**Parâmetros**:
- `idLegislatura`: ID da legislatura

### Detalhes do Bloco

```
GET /blocos/{id}
```

---

## 6. Órgãos

### Listar Órgãos

```
GET /orgaos
```

Comissões, Mesa Diretora, Plenário, etc.

**Parâmetros**:
- `idTipoOrgao`: Tipo do órgão
- `idLegislatura`: ID da legislatura
- `sigla`: Sigla
- `dataInicio`: Data início
- `dataFim`: Data fim

### Detalhes do Órgão

```
GET /orgaos/{id}
```

### Membros do Órgão

```
GET /orgaos/{id}/membros
```

### Votações do Órgão

```
GET /orgaos/{id}/votacoes
```

### Eventos do Órgão

```
GET /orgaos/{id}/eventos
```

---

## 7. Eventos

### Listar Eventos

```
GET /eventos
```

Reuniões, audiências públicas, seminários.

**Parâmetros**:
- `idTipoEvento`: Tipo do evento
- `idOrgao`: ID do órgão
- `dataInicio`: Data início
- `dataFim`: Data fim
- `ordem`: ASC ou DESC
- `ordenarPor`: dataHoraInicio, dataHoraFim

### Detalhes do Evento

```
GET /eventos/{id}
```

### Deputados no Evento

```
GET /eventos/{id}/deputados
```

### Órgãos do Evento

```
GET /eventos/{id}/orgaos
```

---

## 8. Votações

### Listar Votações

```
GET /votacoes
```

**Parâmetros**:
- `id`: ID da votação
- `idProposicao`: ID da proposição votada
- `idOrgao`: ID do órgão
- `dataInicio`: Data início
- `dataFim`: Data fim
- `ordem`: ASC ou DESC
- `ordenarPor`: dataHoraRegistro, siglaOrgao

### Detalhes da Votação

```
GET /votacoes/{id}
```

### Orientações de Bancada

```
GET /votacoes/{id}/orientacoes
```

### Votos

```
GET /votacoes/{id}/votos
```

---

## 9. Frentes Parlamentares

### Listar Frentes

```
GET /frentes
```

**Parâmetros**:
- `idLegislatura`: ID da legislatura
- `keywords`: Palavras-chave

### Detalhes da Frente

```
GET /frentes/{id}
```

### Membros da Frente

```
GET /frentes/{id}/membros
```

---

## 10. Referências

### Tipos de Proposição

```
GET /referencias/tiposProposicao
```

### Situações de Proposição

```
GET /referencias/situacoesProposicao
```

### Tipos de Autor

```
GET /referencias/tiposAutor
```

### Tipos de Órgão

```
GET /referencias/tiposOrgao
```

### Tipos de Evento

```
GET /referencias/tiposEvento
```

### UFs

```
GET /referencias/uf
```

### Ocupações

```
GET /referencias/ocupacoes
```

---

## Download de Arquivos em Massa

Base: `http://dadosabertos.camara.leg.br/arquivos/`

### Proposições por Ano

```
http://dadosabertos.camara.leg.br/arquivos/proposicoes/{formato}/proposicoes-{ano}.{formato}
```

Formatos: `csv`, `xlsx`, `ods`, `json`, `xml`

### Despesas (CEAP) por Ano

```
http://www.camara.leg.br/cotas/Ano-{ano}.{formato}.zip
```

Formatos: `csv`, `xlsx`, `ods`, `json.zip`, `xml.zip`

### Outros Conjuntos Disponíveis

- `deputados.{formato}` - Lista de todos os deputados
- `orgaos.{formato}` - Todos os órgãos
- `legislaturas.{formato}` - Todas as legislaturas
- `frentes.{formato}` - Frentes parlamentares
- `eventos-{ano}.{formato}` - Eventos por ano
- `votacoes-{ano}.{formato}` - Votações por ano

---

## Códigos de Status HTTP

- `200`: Sucesso
- `400`: Parâmetros inválidos
- `404`: Recurso não encontrado
- `500`: Erro interno do servidor

---

## Exemplos de Uso em Python

### Buscar Deputados de SP

```python
import requests

url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
params = {"siglaUf": "SP", "itens": 100}
response = requests.get(url, params=params)
deputados = response.json()["dados"]

for dep in deputados:
    print(f"{dep['nome']} - {dep['siglaPartido']}")
```

### Buscar Despesas de um Deputado

```python
import requests

dep_id = 204554
url = f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep_id}/despesas"
params = {"ano": 2024, "itens": 100}

response = requests.get(url, params=params)
despesas = response.json()["dados"]

total = sum(d["valorDocumento"] for d in despesas)
print(f"Total gasto: R$ {total:,.2f}")
```

### Buscar Proposições de 2024

```python
import requests

url = "https://dadosabertos.camara.leg.br/api/v2/proposicoes"
params = {
    "siglaTipo": "PL",
    "ano": 2024,
    "itens": 50
}

response = requests.get(url, params=params)
proposicoes = response.json()["dados"]

for prop in proposicoes:
    print(f"PL {prop['numero']}/{prop['ano']} - {prop['ementa'][:100]}...")
```

### Buscar com Paginação

```python
import requests

url = "https://dadosabertos.camara.leg.br/api/v2/deputados"
all_data = []
pagina = 1

while True:
    response = requests.get(url, params={"pagina": pagina, "itens": 100})
    data = response.json()
    
    all_data.extend(data["dados"])
    
    links = {link["rel"]: link["href"] for link in data["links"]}
    if "next" not in links:
        break
    
    pagina += 1

print(f"Total de deputados: {len(all_data)}")
```

---

## Notas Importantes

1. **Rate Limiting**: Não há documentação oficial, mas recomenda-se não ultrapassar 1 req/segundo
2. **Dados Históricos**: Dados completos desde 2001, parciais de 1946-2000, alguns de 1934-1945
3. **Atualização**: Base de dados atualizada diariamente
4. **Formatos**: Preferir JSON para APIs, CSV/XLSX para análises manuais
5. **Legislatura Atual**: 57ª (2023-2027)

---

## Links Úteis

- Documentação Oficial: https://dadosabertos.camara.leg.br/swagger/api.html
- GitHub: https://github.com/CamaraDosDeputados/dados-abertos
- Portal: https://www2.camara.leg.br/transparencia/dados-abertos

---

## Suporte

Issues no GitHub: https://github.com/CamaraDosDeputados/dados-abertos/issues