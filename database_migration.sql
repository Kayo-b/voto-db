-- Database migration script for Voto-DB
-- PostgreSQL 15 compatible
-- Creates all tables for storing Brazilian Chamber of Deputies data

-- Create database schema
-- (This assumes you're connected to the correct database)

-- Table: legislaturas (Legislative periods)
CREATE TABLE IF NOT EXISTS legislaturas (
    id SERIAL PRIMARY KEY,
    numero INTEGER UNIQUE NOT NULL,
    inicio TIMESTAMP,
    fim TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: partidos (Political parties)
CREATE TABLE IF NOT EXISTS partidos (
    id SERIAL PRIMARY KEY,
    sigla VARCHAR(10) UNIQUE NOT NULL,
    nome VARCHAR(255),
    uri VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for partidos
CREATE INDEX IF NOT EXISTS idx_partidos_sigla ON partidos(sigla);

-- Table: proposicoes (Legislative proposals)
CREATE TABLE IF NOT EXISTS proposicoes (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    titulo TEXT NOT NULL,
    ementa TEXT,
    tipo VARCHAR(50),
    numero VARCHAR(20),
    ano INTEGER,
    uri VARCHAR(500),
    relevancia VARCHAR(20) DEFAULT 'baixa',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for proposicoes
CREATE INDEX IF NOT EXISTS idx_proposicoes_codigo ON proposicoes(codigo);
CREATE INDEX IF NOT EXISTS idx_proposicoes_tipo_ano ON proposicoes(tipo, ano);
CREATE INDEX IF NOT EXISTS idx_proposicoes_relevancia ON proposicoes(relevancia);

-- Table: deputados (Deputies/Congresspeople)
CREATE TABLE IF NOT EXISTS deputados (
    id INTEGER PRIMARY KEY,
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

-- Create indexes for deputados
CREATE INDEX IF NOT EXISTS idx_deputados_nome ON deputados(nome);
CREATE INDEX IF NOT EXISTS idx_deputados_nome_parlamentar ON deputados(nome_parlamentar);
CREATE INDEX IF NOT EXISTS idx_deputados_uf ON deputados(sigla_uf);
CREATE INDEX IF NOT EXISTS idx_deputados_partido_uf ON deputados(partido_id, sigla_uf);

-- Table: votacoes (Voting sessions)
CREATE TABLE IF NOT EXISTS votacoes (
    id SERIAL PRIMARY KEY,
    proposicao_id INTEGER NOT NULL REFERENCES proposicoes(id),
    data_votacao TIMESTAMP NOT NULL,
    descricao TEXT,
    resultado VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for votacoes
CREATE INDEX IF NOT EXISTS idx_votacoes_data ON votacoes(data_votacao);
CREATE INDEX IF NOT EXISTS idx_votacoes_proposicao ON votacoes(proposicao_id);

-- Table: votos (Individual votes)
CREATE TABLE IF NOT EXISTS votos (
    id SERIAL PRIMARY KEY,
    deputado_id INTEGER NOT NULL REFERENCES deputados(id),
    votacao_id INTEGER NOT NULL REFERENCES votacoes(id),
    voto VARCHAR(20) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(deputado_id, votacao_id)
);

-- Create indexes for votos
CREATE INDEX IF NOT EXISTS idx_votos_deputado_votacao ON votos(deputado_id, votacao_id);
CREATE INDEX IF NOT EXISTS idx_votos_deputado ON votos(deputado_id);
CREATE INDEX IF NOT EXISTS idx_votos_votacao ON votos(votacao_id);

-- Table: estatisticas_deputados (Deputy statistics)
CREATE TABLE IF NOT EXISTS estatisticas_deputados (
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
CREATE TABLE IF NOT EXISTS cache_metadata (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) UNIQUE NOT NULL,
    cache_type VARCHAR(50) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for cache_metadata
CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_metadata(cache_key);
CREATE INDEX IF NOT EXISTS idx_cache_type_expires ON cache_metadata(cache_type, expires_at);

-- Create a view for complete deputy information
CREATE OR REPLACE VIEW view_deputados_completo AS
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

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at columns
CREATE OR REPLACE TRIGGER update_legislaturas_updated_at BEFORE UPDATE ON legislaturas FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_partidos_updated_at BEFORE UPDATE ON partidos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_proposicoes_updated_at BEFORE UPDATE ON proposicoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_deputados_updated_at BEFORE UPDATE ON deputados FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_votacoes_updated_at BEFORE UPDATE ON votacoes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_votos_updated_at BEFORE UPDATE ON votos FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE OR REPLACE TRIGGER update_estatisticas_deputados_updated_at BEFORE UPDATE ON estatisticas_deputados FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default legislatura (current period)
INSERT INTO legislaturas (numero, inicio, fim) 
VALUES (57, '2023-02-01', '2027-01-31')
ON CONFLICT (numero) DO NOTHING;

-- Insert some common political parties (based on the JSON examples)
INSERT INTO partidos (sigla, nome) VALUES
('MDB', 'Movimento Democrático Brasileiro'),
('PT', 'Partido dos Trabalhadores'),
('PP', 'Progressistas'),
('PL', 'Partido Liberal'),
('PDT', 'Partido Democrático Trabalhista'),
('AVANTE', 'Avante'),
('PSDB', 'Partido da Social Democracia Brasileira')
ON CONFLICT (sigla) DO NOTHING;

-- Add comments to tables for documentation
COMMENT ON TABLE legislaturas IS 'Legislative periods/sessions of the Brazilian Chamber of Deputies';
COMMENT ON TABLE partidos IS 'Political parties in Brazil';
COMMENT ON TABLE deputados IS 'Deputies/Congresspeople of the Brazilian Chamber of Deputies';
COMMENT ON TABLE proposicoes IS 'Legislative proposals (bills, constitutional amendments, etc.)';
COMMENT ON TABLE votacoes IS 'Voting sessions for legislative proposals';
COMMENT ON TABLE votos IS 'Individual votes cast by deputies in voting sessions';
COMMENT ON TABLE estatisticas_deputados IS 'Voting statistics and analysis for each deputy';
COMMENT ON TABLE cache_metadata IS 'Metadata for API response caching system';

COMMENT ON COLUMN deputados.id IS 'Deputy ID from the Chamber API (not auto-generated)';
COMMENT ON COLUMN votos.voto IS 'Vote type: Sim, Não, Abstenção, Obstrução, Ausente';
COMMENT ON COLUMN proposicoes.relevancia IS 'Proposal relevance: alta, média, baixa';
COMMENT ON COLUMN proposicoes.codigo IS 'Proposal code (e.g., PEC 3/2021, PL 1234/2023)';