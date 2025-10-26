"""
Database models for VotoDB using SQLAlchemy ORM
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

Base = declarative_base()

class Deputado(Base):
    """Modelo para dados dos deputados"""
    __tablename__ = 'deputados'
    
    id = Column(Integer, primary_key=True)
    nome_civil = Column(String(255), nullable=False)
    nome_parlamentar = Column(String(255), nullable=False)
    sigla_partido = Column(String(20))
    sigla_uf = Column(String(2))
    situacao = Column(String(50))
    data_nascimento = Column(String(20))
    escolaridade = Column(String(100))
    email = Column(String(255))
    telefone = Column(String(50))
    
    # Campos de controle
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dados_completos = Column(JSONB)  # Store complete API response
    
    # Relationships
    votos = relationship("Voto", back_populates="deputado")
    
    def __repr__(self):
        return f"<Deputado(id={self.id}, nome='{self.nome_parlamentar}', partido='{self.sigla_partido}')>"

class Proposicao(Base):
    """Modelo para proposições (PL, PEC, MP, etc.)"""
    __tablename__ = 'proposicoes'
    
    id = Column(Integer, primary_key=True)
    tipo = Column(String(10), nullable=False)  # PL, PEC, MP, etc.
    numero = Column(Integer, nullable=False)
    ano = Column(Integer, nullable=False)
    ementa = Column(Text)
    titulo = Column(Text)
    situacao = Column(String(255))
    status_proposicao = Column(JSONB)
    
    # URLs and references
    uri = Column(String(500))
    uri_orgao = Column(String(500))
    
    # Campos de controle
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dados_completos = Column(JSONB)  # Store complete API response
    
    # Relationships
    votacoes = relationship("Votacao", back_populates="proposicao")
    
    # Índices para busca eficiente
    __table_args__ = (
        UniqueConstraint('tipo', 'numero', 'ano', name='uq_proposicao_tipo_numero_ano'),
        Index('idx_proposicao_tipo_numero_ano', 'tipo', 'numero', 'ano'),
        Index('idx_proposicao_ano', 'ano'),
    )
    
    def __repr__(self):
        return f"<Proposicao(id={self.id}, tipo='{self.tipo}', numero={self.numero}, ano={self.ano})>"

class Votacao(Base):
    """Modelo para votações de uma proposição"""
    __tablename__ = 'votacoes'
    
    id = Column(String(50), primary_key=True)  # Format: "proposicao_id-sequencial"
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False)
    data_hora_inicio = Column(DateTime)
    data_hora_fim = Column(DateTime)
    data_hora_registro = Column(DateTime)
    descricao = Column(Text)
    sigla_orgao = Column(String(20))
    uri_orgao = Column(String(500))
    aprovacao = Column(Boolean)
    
    # Campos de controle
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    dados_completos = Column(JSONB)  # Store complete API response
    
    # Relationships
    proposicao = relationship("Proposicao", back_populates="votacoes")
    votos = relationship("Voto", back_populates="votacao")
    
    # Índices
    __table_args__ = (
        Index('idx_votacao_proposicao_id', 'proposicao_id'),
        Index('idx_votacao_data', 'data_hora_registro'),
    )
    
    def __repr__(self):
        return f"<Votacao(id='{self.id}', proposicao_id={self.proposicao_id}, orgao='{self.sigla_orgao}')>"

class Voto(Base):
    """Modelo para votos individuais dos deputados"""
    __tablename__ = 'votos'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=False)
    votacao_id = Column(String(50), ForeignKey('votacoes.id'), nullable=False)
    tipo_voto = Column(String(20), nullable=False)  # Sim, Não, Abstenção, Obstrução
    
    # Campos de controle
    criado_em = Column(DateTime, default=datetime.utcnow)
    dados_completos = Column(JSONB)  # Store complete API response
    
    # Relationships
    deputado = relationship("Deputado", back_populates="votos")
    votacao = relationship("Votacao", back_populates="votos")
    
    # Constraints e índices
    __table_args__ = (
        UniqueConstraint('deputado_id', 'votacao_id', name='uq_voto_deputado_votacao'),
        Index('idx_voto_deputado_id', 'deputado_id'),
        Index('idx_voto_votacao_id', 'votacao_id'),
        Index('idx_voto_tipo', 'tipo_voto'),
    )
    
    def __repr__(self):
        return f"<Voto(deputado_id={self.deputado_id}, votacao_id='{self.votacao_id}', tipo='{self.tipo_voto}')>"

class CacheStatus(Base):
    """Modelo para controlar status do cache e sincronização"""
    __tablename__ = 'cache_status'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chave = Column(String(255), unique=True, nullable=False)
    tipo = Column(String(50), nullable=False)  # 'deputado', 'proposicao', 'votacao', 'votos'
    ultima_atualizacao = Column(DateTime, nullable=False)
    expira_em = Column(DateTime)
    status = Column(String(20), default='ativo')  # ativo, expirado, erro
    
    # Metadata
    tentativas_atualizacao = Column(Integer, default=0)
    ultimo_erro = Column(Text)
    
    __table_args__ = (
        Index('idx_cache_chave', 'chave'),
        Index('idx_cache_tipo', 'tipo'),
        Index('idx_cache_expiracao', 'expira_em'),
    )
    
    def __repr__(self):
        return f"<CacheStatus(chave='{self.chave}', tipo='{self.tipo}', status='{self.status}')>"

class AnaliseDeputado(Base):
    """Modelo para armazenar análises processadas de deputados"""
    __tablename__ = 'analises_deputado'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=False)
    data_analise = Column(DateTime, default=datetime.utcnow)
    
    # Estatísticas calculadas
    total_votacoes = Column(Integer, default=0)
    presenca_percentual = Column(Integer, default=0)
    votos_favoraveis = Column(Integer, default=0)
    votos_contrarios = Column(Integer, default=0)
    abstencoes = Column(Integer, default=0)
    obstrucoes = Column(Integer, default=0)
    
    # Análise completa em JSON
    analise_completa = Column(JSONB)
    
    # Metadata
    versao_analise = Column(String(10), default='2.0')
    proposicoes_analisadas = Column(Integer, default=0)
    
    __table_args__ = (
        Index('idx_analise_deputado_id', 'deputado_id'),
        Index('idx_analise_data', 'data_analise'),
    )
    
    def __repr__(self):
        return f"<AnaliseDeputado(deputado_id={self.deputado_id}, votacoes={self.total_votacoes})>"