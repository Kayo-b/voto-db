-- Drop existing database schema and create fresh one
-- WARNING: This will delete all existing data!

-- Drop all existing tables (order matters due to foreign keys)
DROP TABLE IF EXISTS analises_deputado CASCADE;
DROP TABLE IF EXISTS analises_deputados CASCADE;
DROP TABLE IF EXISTS cache_metadata CASCADE;
DROP TABLE IF EXISTS estatisticas_deputados CASCADE;
DROP TABLE IF EXISTS votos CASCADE;
DROP TABLE IF EXISTS votacoes CASCADE;
DROP TABLE IF EXISTS proposicoes CASCADE;
DROP TABLE IF EXISTS deputados CASCADE;
DROP TABLE IF EXISTS partidos CASCADE;
DROP TABLE IF EXISTS legislaturas CASCADE;

-- Drop existing views
DROP VIEW IF EXISTS view_deputados_completo CASCADE;

-- Drop existing functions
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- Drop existing sequences (they'll be recreated)
DROP SEQUENCE IF EXISTS deputados_id_seq CASCADE;
DROP SEQUENCE IF EXISTS proposicoes_id_seq CASCADE;
DROP SEQUENCE IF EXISTS votos_id_seq CASCADE;

-- Now create the fresh schema
-- This is our clean slate based on the API structure

-- Function to update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Table: legislaturas (Legislative periods)
CREATE TABLE legislaturas (
    id SERIAL PRIMARY KEY,
    numero INTEGER UNIQUE NOT NULL,
    inicio TIMESTAMP,
    fim TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: partidos (Political parties)
CREATE TABLE partidos (
    id SERIAL PRIMARY KEY,
    sigla VARCHAR(10) UNIQUE NOT NULL,
    nome VARCHAR(255),
    uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: proposicoes (Legislative proposals)
CREATE TABLE proposicoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,  -- e.g., "PEC 3/2021"
    titulo TEXT NOT NULL,
    ementa TEXT,
    tipo VARCHAR(50),  -- PEC, PL, etc.
    numero VARCHAR(20),
    ano INTEGER,
    uri VARCHAR(500),
    relevancia VARCHAR(20) DEFAULT 'baixa',  -- alta, média, baixa
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: deputados (Deputies/Congresspeople) - using API ID as primary key
CREATE TABLE deputados (
    id INTEGER PRIMARY KEY,  -- ID from the Chamber API (not auto-generated)
    nome VARCHAR(255) NOT NULL,
    nome_parlamentar VARCHAR(255),
    uri VARCHAR(500),
    sigla_uf VARCHAR(2) NOT NULL,
    url_foto VARCHAR(500),
    email VARCHAR(255),
    situacao VARCHAR(50),
    partido_id INTEGER NOT NULL REFERENCES partidos(id),
    legislatura_id INTEGER NOT NULL REFERENCES legislaturas(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: votacoes (Voting sessions)
CREATE TABLE votacoes (
    id SERIAL PRIMARY KEY,
    proposicao_id INTEGER NOT NULL REFERENCES proposicoes(id),
    data_votacao TIMESTAMP NOT NULL,
    descricao TEXT,
    resultado VARCHAR(50),  -- Aprovado, Rejeitado, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: votos (Individual votes)
CREATE TABLE votos (
    id SERIAL PRIMARY KEY,
    deputado_id INTEGER NOT NULL REFERENCES deputados(id),
    votacao_id INTEGER NOT NULL REFERENCES votacoes(id),
    voto VARCHAR(20) NOT NULL,  -- Sim, Não, Abstenção, Obstrução, Ausente
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(deputado_id, votacao_id)
);

-- Table: estatisticas_deputados (Deputy statistics)
CREATE TABLE estatisticas_deputados (
    id SERIAL PRIMARY KEY,
    deputado_id INTEGER UNIQUE NOT NULL REFERENCES deputados(id),
    total_votacoes_analisadas INTEGER DEFAULT 0,
    participacao INTEGER DEFAULT 0,
    presenca_percentual REAL DEFAULT 0.0,
    votos_favoraveis INTEGER DEFAULT 0,
    votos_contrarios INTEGER DEFAULT 0,
    abstencoes INTEGER DEFAULT 0,
    obstrucoes INTEGER DEFAULT 0,
    ausencias INTEGER DEFAULT 0,
    analisado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    proposicoes_analisadas INTEGER DEFAULT 0,
    proposicoes_tentadas INTEGER DEFAULT 0,
    taxa_sucesso REAL DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: cache_metadata (API cache metadata)
CREATE TABLE cache_metadata (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_type VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create all indexes
CREATE INDEX idx_partidos_sigla ON partidos(sigla);

CREATE INDEX idx_proposicoes_codigo ON proposicoes(codigo);
CREATE INDEX idx_proposicoes_tipo_ano ON proposicoes(tipo, ano);
CREATE INDEX idx_proposicoes_relevancia ON proposicoes(relevancia);

CREATE INDEX idx_deputados_nome ON deputados(nome);
CREATE INDEX idx_deputados_nome_parlamentar ON deputados(nome_parlamentar);
CREATE INDEX idx_deputados_uf ON deputados(sigla_uf);
CREATE INDEX idx_deputados_partido_uf ON deputados(partido_id, sigla_uf);

CREATE INDEX idx_votacoes_data ON votacoes(data_votacao);
CREATE INDEX idx_votacoes_proposicao ON votacoes(proposicao_id);

CREATE INDEX idx_votos_deputado_votacao ON votos(deputado_id, votacao_id);
CREATE INDEX idx_votos_deputado ON votos(deputado_id);
CREATE INDEX idx_votos_votacao ON votos(votacao_id);

CREATE INDEX idx_cache_key ON cache_metadata(cache_key);
CREATE INDEX idx_cache_type_expires ON cache_metadata(cache_type, expires_at);

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_legislaturas_updated_at BEFORE UPDATE ON legislaturas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_partidos_updated_at BEFORE UPDATE ON partidos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_proposicoes_updated_at BEFORE UPDATE ON proposicoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_deputados_updated_at BEFORE UPDATE ON deputados FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_votacoes_updated_at BEFORE UPDATE ON votacoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_votos_updated_at BEFORE UPDATE ON votos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_estatisticas_deputados_updated_at BEFORE UPDATE ON estatisticas_deputados FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create a comprehensive view for deputy information
CREATE VIEW view_deputados_completo AS
SELECT 
    d.id as deputado_id,
    d.nome,
    d.nome_parlamentar,
    p.sigla as partido_sigla,
    p.nome as partido_nome,
    d.sigla_uf as uf,
    d.situacao,
    d.url_foto,
    d.email,
    COALESCE(e.total_votacoes_analisadas, 0) as total_votacoes,
    COALESCE(e.presenca_percentual, 0.0) as presenca_percentual,
    COALESCE(e.votos_favoraveis, 0) as votos_favoraveis,
    COALESCE(e.votos_contrarios, 0) as votos_contrarios,
    COALESCE(e.abstencoes, 0) as abstencoes,
    COALESCE(e.ausencias, 0) as ausencias,
    e.analisado_em
FROM deputados d
JOIN partidos p ON d.partido_id = p.id
LEFT JOIN estatisticas_deputados e ON d.id = e.deputado_id;

-- Insert default data
-- Insert current legislatura
INSERT INTO legislaturas (numero, inicio, fim) 
VALUES (57, '2023-02-01', '2027-01-31');

-- Insert common political parties (based on the JSON examples)
INSERT INTO partidos (sigla, nome) VALUES
('MDB', 'Movimento Democrático Brasileiro'),
('PT', 'Partido dos Trabalhadores'),
('PP', 'Progressistas'),
('PL', 'Partido Liberal'),
('PDT', 'Partido Democrático Trabalhista'),
('AVANTE', 'Avante'),
('PSDB', 'Partido da Social Democracia Brasileira');

-- Add table comments for documentation
COMMENT ON TABLE legislaturas IS 'Legislative periods/sessions of the Brazilian Chamber of Deputies';
COMMENT ON TABLE partidos IS 'Political parties in Brazil';
COMMENT ON TABLE deputados IS 'Deputies/Congresspeople of the Brazilian Chamber of Deputies';
COMMENT ON TABLE proposicoes IS 'Legislative proposals (bills, constitutional amendments, etc.)';
COMMENT ON TABLE votacoes IS 'Voting sessions for legislative proposals';
COMMENT ON TABLE votos IS 'Individual votes cast by deputies in voting sessions';
COMMENT ON TABLE estatisticas_deputados IS 'Voting statistics and analysis for each deputy';
COMMENT ON TABLE cache_metadata IS 'Metadata for API response caching system';

COMMENT ON COLUMN deputados.id IS 'Deputy ID from the Chamber API (matches the API response id field)';
COMMENT ON COLUMN votos.voto IS 'Vote type: Sim, Não, Abstenção, Obstrução, Ausente';
COMMENT ON COLUMN proposicoes.relevancia IS 'Proposal relevance: alta, média, baixa';
COMMENT ON COLUMN proposicoes.codigo IS 'Proposal code (e.g., PEC 3/2021, PL 1234/2023)';

-- Display success message
SELECT 'Database schema reset successfully! Fresh schema created based on API structure.' AS status;