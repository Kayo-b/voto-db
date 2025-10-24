# VotoDB - Sistema de Análise de Votações

Sistema completo para análise de votações da Câmara dos Deputados, com foco em proposições de alta relevância social e política.

## Funcionalidades

### Implementadas

#### Backend (FastAPI + Redis)
- **API de Deputados**: Busca e detalhes de deputados
- **Análise de Proposições**: Sistema completo de análise de proposições relevantes
- **Cache Inteligente**: Redis para otimização de performance
- **Análise de Perfil**: Análise do histórico de votação de deputados
- **Dados Pré-selecionados**: Base de proposições de alta relevância

#### Frontend (React + TypeScript)
- **Busca de Deputados**: Interface para buscar e visualizar deputados
- **Proposições Relevantes**: Lista de proposições importantes com filtros
- **Análise Avançada**: Análise do perfil de votação de deputados específicos
- **Interface Responsiva**: Design moderno e responsivo

### Tecnologias

- **Backend**: FastAPI, Redis, Python
- **Frontend**: React, TypeScript, CSS personalizado
- **API Externa**: API da Câmara dos Deputados
- **Deploy**: Railway (configurado)

## Como Usar

### Pré-requisitos
- Python 3.13+
- Node.js 18+
- Redis (opcional, sistema funciona sem)

### Instalação

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install fastapi uvicorn redis requests python-dotenv
```

#### Frontend
```bash
cd frontend
npm install axios --legacy-peer-deps
```

### Executar o Sistema

#### Backend
```bash
cd backend
PYTHONPATH=/path/to/venv/lib/python3.13/site-packages python -m uvicorn main_v2:app --host 127.0.0.1 --port 8001
```

#### Frontend
```bash
cd frontend
npm start
```

### Acessar
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001
- **Documentação API**: http://localhost:8001/docs

## Endpoints da API

### Endpoints Básicos
- `GET /deputados` - Lista deputados
- `GET /deputados/{id}` - Detalhes do deputado
- `GET /deputados/{id}/votacoes` - Votações do deputado

### Endpoints de Análise (Novos)
- `GET /proposicoes/relevantes` - Lista proposições pré-selecionadas
- `GET /proposicoes/buscar` - Busca proposição específica
- `POST /proposicoes/analisar` - Análise completa de proposição
- `GET /deputados/{id}/analise` - Análise do perfil do deputado
- `GET /estatisticas/geral` - Estatísticas do sistema
- `GET /health` - Status do sistema

## Casos de Uso

### 1. Analisar Deputado Específico
1. Acesse "Buscar Deputados"
2. Digite o nome do deputado
3. Clique no deputado desejado
4. Veja o histórico de votações
5. Use "Análise Avançada" para análise detalhada

### 2. Explorar Proposições Relevantes
1. Acesse "Proposições Relevantes"
2. Filtre por relevância (alta, média, baixa)
3. Veja o impacto de cada proposição
4. Analise estatísticas gerais

### 3. Análise Comparativa
1. Acesse "Análise Avançada"
2. Digite o ID do deputado
3. Escolha "Análise Rápida" ou "Análise Completa"
4. Compare perfis de votação

## Proposições Pré-selecionadas

O sistema inclui análise de 23 proposições de alta relevância:

### Alta Relevância
- **PEC 241/2016**: Teto de Gastos Públicos
- **PL 6787/2016**: Reforma Trabalhista  
- **PEC 6/2019**: Reforma da Previdência
- **PL 490/2007**: Marco Temporal Terras Indígenas
- **PEC 45/2019**: Reforma Tributária

### Média Relevância
- **PL 2630/2020**: Marco Legal do Saneamento
- **PL 1179/2020**: Marco Legal das Startups
- **PL 5829/2019**: Lei de Cotas - Renovação

## Sistema de Análise

### Identificação de Votações Principais
O sistema identifica automaticamente as votações mais importantes usando:
- Votações do Plenário (`siglaOrgao == "PLEN"`)
- Termos-chave: "texto-base", "substitutivo global", "redação final"
- Ordenação por data (mais recentes primeiro)

### Métricas Calculadas
- **Presença**: Percentual de participação em votações
- **Alinhamento**: Padrão de votação (favorável/contrário)
- **Estatísticas por Partido**: Distribuição de votos por partido
- **Relevância**: Classificação do impacto da proposição

## Desenvolvimento

### Scripts Úteis

#### Executar Demo
```bash
cd backend
python demo_sistema.py
```

#### Testar Sistema (com API real)
```bash
cd backend
python test_sistema.py
```

#### Verificar Status da API
```bash
curl http://localhost:8001/health
```

## Deploy

### Railway
O projeto está configurado para deploy no Railway:

1. **railway.toml** configurado
2. **Variáveis necessárias**:
   - `REDIS_URL` (automático)
   - `PORT` (automático)

### Deploy Manual
```bash
npm install -g @railway/cli
railway login
railway init
railway add
railway up
```

## Links úteis

- https://dadosabertos.camara.leg.br/swagger/api.html  
- https://www2.camara.leg.br/transparencia/dados-abertos/dados-abertos-legislativo/webservices  
- https://www.camara.leg.br/proposicoesWeb

---

**VotoDB v2.0** - Sistema Completo de Análise de Votações
Desenvolvido para transparência e análise política no Brasil
