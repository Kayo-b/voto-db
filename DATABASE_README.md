# 🗳️ Voto-DB Database Schema Documentation

## Overview
A comprehensive PostgreSQL database schema designed to store and analyze data from the Brazilian Chamber of Deputies API, including deputies, political parties, legislative proposals, voting sessions, and individual votes.

## Database Structure

### 📊 Core Tables

#### 1. **legislaturas** - Legislative Periods
```sql
- id (SERIAL PRIMARY KEY)
- numero (INTEGER UNIQUE) - Legislative period number (e.g., 57)
- inicio (TIMESTAMP) - Start date
- fim (TIMESTAMP) - End date
- created_at/updated_at (TIMESTAMP)
```

#### 2. **partidos** - Political Parties
```sql
- id (SERIAL PRIMARY KEY)
- sigla (VARCHAR(10) UNIQUE) - Party abbreviation (e.g., 'MDB', 'PT')
- nome (VARCHAR(255)) - Full party name
- uri (VARCHAR(500)) - API URI reference
- created_at/updated_at (TIMESTAMP)
```

#### 3. **deputados** - Deputies/Congresspeople
```sql
- id (INTEGER PRIMARY KEY) - Uses API ID (e.g., 220542)
- nome (VARCHAR(255)) - Full legal name
- nome_parlamentar (VARCHAR(255)) - Parliamentary name
- uri (VARCHAR(500)) - API URI reference
- sigla_uf (VARCHAR(2)) - State abbreviation (e.g., 'SP', 'RJ')
- url_foto (VARCHAR(500)) - Photo URL
- email (VARCHAR(255)) - Contact email
- situacao (VARCHAR(50)) - Current status (e.g., 'Exercício')
- partido_id (INTEGER FK → partidos.id)
- legislatura_id (INTEGER FK → legislaturas.id)
- created_at/updated_at (TIMESTAMP)
```

#### 4. **proposicoes** - Legislative Proposals
```sql
- id (SERIAL PRIMARY KEY)
- codigo (VARCHAR(50) UNIQUE) - Proposal code (e.g., 'PEC 3/2021')
- titulo (TEXT) - Proposal title
- ementa (TEXT) - Proposal summary/description
- tipo (VARCHAR(50)) - Type (PEC, PL, etc.)
- numero (VARCHAR(20)) - Proposal number
- ano (INTEGER) - Year
- uri (VARCHAR(500)) - API URI reference
- relevancia (VARCHAR(20)) - Relevance level (alta/média/baixa)
- created_at/updated_at (TIMESTAMP)
```

#### 5. **votacoes** - Voting Sessions
```sql
- id (SERIAL PRIMARY KEY)
- proposicao_id (INTEGER FK → proposicoes.id)
- data_votacao (TIMESTAMP) - Voting date and time
- descricao (TEXT) - Voting session description
- resultado (VARCHAR(50)) - Result (Aprovado, Rejeitado, etc.)
- created_at/updated_at (TIMESTAMP)
```

#### 6. **votos** - Individual Votes
```sql
- id (SERIAL PRIMARY KEY)
- deputado_id (INTEGER FK → deputados.id)
- votacao_id (INTEGER FK → votacoes.id)
- voto (VARCHAR(20)) - Vote type (Sim, Não, Abstenção, Obstrução, Ausente)
- created_at/updated_at (TIMESTAMP)
- UNIQUE(deputado_id, votacao_id) - Prevents duplicate votes
```

#### 7. **estatisticas_deputados** - Deputy Statistics
```sql
- id (SERIAL PRIMARY KEY)
- deputado_id (INTEGER UNIQUE FK → deputados.id)
- total_votacoes_analisadas (INTEGER)
- participacao (INTEGER)
- presenca_percentual (REAL)
- votos_favoraveis (INTEGER)
- votos_contrarios (INTEGER)
- abstencoes (INTEGER)
- obstrucoes (INTEGER)
- ausencias (INTEGER)
- analisado_em (TIMESTAMP)
- proposicoes_analisadas (INTEGER)
- proposicoes_tentadas (INTEGER)
- taxa_sucesso (REAL)
- created_at/updated_at (TIMESTAMP)
```

#### 8. **cache_metadata** - API Cache Management
```sql
- id (SERIAL PRIMARY KEY)
- cache_key (VARCHAR(255) UNIQUE)
- cache_type (VARCHAR(50))
- expires_at (TIMESTAMP)
- created_at (TIMESTAMP)
```

### 📈 Views

#### **view_deputados_completo** - Complete Deputy Information
Combines deputy data with party information and statistics:
```sql
SELECT d.id, d.nome, d.nome_parlamentar, p.sigla as partido_sigla,
       p.nome as partido_nome, d.sigla_uf, d.situacao,
       e.total_votacoes, e.presenca_percentual, e.votos_favoraveis
FROM deputados d
JOIN partidos p ON d.partido_id = p.id
LEFT JOIN estatisticas_deputados e ON d.id = e.deputado_id
```

## 🚀 Setup Instructions

### 1. Database Reset (if needed)
```bash
# Reset database with fresh schema
docker exec -i votodb-postgres psql -U postgres -d votodb < reset_database_schema.sql
```

### 2. Python Environment
```bash
# Install dependencies
pip install sqlalchemy==2.0.34 psycopg2-binary==2.9.9 alembic==1.13.3
```

### 3. Connection Configuration
```python
# Default connection string
DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/votodb'
```

## 💻 Usage Examples

### Basic Repository Usage
```python
from database.connection import SessionLocal
from database.repository import DeputadoRepository, PartidoRepository

with SessionLocal() as db:
    # Search deputies
    deputado_repo = DeputadoRepository(db)
    deputies = deputado_repo.search_by_name("André")
    
    # Get party information
    partido_repo = PartidoRepository(db)
    partido = partido_repo.get_by_sigla("PT")
```

### Creating Data from API Response
```python
# Deputy data from API
deputado_data = {
    'id': 220542,  # API ID
    'nome': 'Alexandre Guimarães',
    'nome_parlamentar': 'Alexandre Guimarães',
    'sigla_uf': 'TO',
    'partido_id': partido.id,
    'legislatura_id': legislatura.id
}
deputado = deputado_repo.create_or_update(deputado_data)
```

### Recording Vote Data
```python
# Create voting session
votacao_data = {
    'proposicao_id': proposicao.id,
    'data_votacao': datetime(2025, 9, 17, 14, 11, 37),
    'descricao': 'Votação da PEC da Blindagem'
}
votacao = votacao_repo.create_or_update(votacao_data)

# Record individual vote
voto_data = {
    'deputado_id': deputado.id,
    'votacao_id': votacao.id,
    'voto': 'Sim'
}
voto = voto_repo.create_or_update(voto_data)
```

## 🔍 API Mapping

### Deputado Search API Response → Database
```json
{
  "id": 220542,                    → deputados.id
  "nome": "Alexandre Guimarães",   → deputados.nome
  "siglaPartido": "MDB",           → partidos.sigla (via FK)
  "siglaUf": "TO",                 → deputados.sigla_uf
  "urlFoto": "https://...",        → deputados.url_foto
  "email": "dep.alexandre@..."     → deputados.email
}
```

### Voting History API Response → Database
```json
{
  "proposicao": "PEC 3/2021",      → proposicoes.codigo
  "titulo": "PEC da Blindagem",    → proposicoes.titulo
  "voto": "Sim",                   → votos.voto
  "data": "2025-09-17T14:11:37",   → votacoes.data_votacao
  "relevancia": "alta"             → proposicoes.relevancia
}
```

## 📋 File Structure
```
backend/database/
├── __init__.py          # Package initialization
├── model.py             # SQLAlchemy models
├── connection.py        # Database connection management
└── repository.py        # Data access layer

database_migration.sql   # Initial schema creation
reset_database_schema.sql # Fresh schema reset
db_manager.py           # Management utility
```

## ✅ Features
- **API-aligned schema**: Matches Brazilian Chamber API response structure
- **Repository pattern**: Clean data access layer
- **Automatic timestamps**: Created/updated tracking
- **Foreign key integrity**: Proper relationships between entities
- **Comprehensive indexing**: Optimized for common queries
- **Statistics tracking**: Deputy voting behavior analysis
- **Cache management**: API response caching support
- **Complete views**: Pre-joined data for complex queries

## 🔧 Management Commands
```bash
# Show database information
python db_manager.py info

# Add sample data
python db_manager.py sample

# Reset entire database
python db_manager.py reset
```