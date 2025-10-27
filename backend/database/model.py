"""
Database models for the Voto-DB system.
This module contains SQLAlchemy models for storing deputados, parties, proposals, 
votes, and voting sessions from the Brazilian Chamber of Deputies API.
"""

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Legislatura(Base):
    """Legislative period/session"""
    __tablename__ = 'legislaturas'
    
    id = Column(Integer, primary_key=True)
    numero = Column(Integer, unique=True, nullable=False)
    inicio = Column(DateTime)
    fim = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    deputados = relationship("Deputado", back_populates="legislatura")


class Partido(Base):
    """Political party"""
    __tablename__ = 'partidos'
    
    id = Column(Integer, primary_key=True)
    sigla = Column(String(10), unique=True, nullable=False, index=True)
    nome = Column(String(255))
    uri = Column(String(500))
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    deputados = relationship("Deputado", back_populates="partido")


class Deputado(Base):
    """Deputy/Congressperson"""
    __tablename__ = 'deputados'
    
    id = Column(Integer, primary_key=True)
    nome = Column(String(255), nullable=False, index=True)
    nome_parlamentar = Column(String(255), index=True)
    uri = Column(String(500))
    sigla_uf = Column(String(2), nullable=False, index=True)
    url_foto = Column(String(500))
    email = Column(String(255))
    situacao = Column(String(50))
    
    # Foreign keys
    partido_id = Column(Integer, ForeignKey('partidos.id'), nullable=False)
    legislatura_id = Column(Integer, ForeignKey('legislaturas.id'), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    partido = relationship("Partido", back_populates="deputados")
    legislatura = relationship("Legislatura", back_populates="deputados")
    votos = relationship("Voto", back_populates="deputado")
    estatisticas = relationship("EstatisticaDeputado", back_populates="deputado", uselist=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_deputado_partido_uf', 'partido_id', 'sigla_uf'),
        Index('idx_deputado_nome', 'nome'),
    )


class Proposicao(Base):
    """Legislative proposal"""
    __tablename__ = 'proposicoes'
    
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)  # e.g., "PEC 3/2021"
    titulo = Column(Text, nullable=False)
    ementa = Column(Text)
    tipo = Column(String(50))  # PEC, PL, etc.
    numero = Column(String(20))
    ano = Column(Integer)
    uri = Column(String(500))
    relevancia = Column(String(20), default='baixa')  # alta, média, baixa
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    votacoes = relationship("Votacao", back_populates="proposicao")
    
    # Indexes
    __table_args__ = (
        Index('idx_proposicao_tipo_ano', 'tipo', 'ano'),
        Index('idx_proposicao_relevancia', 'relevancia'),
    )


class Votacao(Base):
    """Voting session for a specific proposal"""
    __tablename__ = 'votacoes'
    
    id = Column(Integer, primary_key=True)
    proposicao_id = Column(Integer, ForeignKey('proposicoes.id'), nullable=False)
    data_votacao = Column(DateTime, nullable=False, index=True)
    descricao = Column(Text)
    resultado = Column(String(50))  # Aprovado, Rejeitado, etc.
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    proposicao = relationship("Proposicao", back_populates="votacoes")
    votos = relationship("Voto", back_populates="votacao")


class Voto(Base):
    """Individual vote by a deputy in a voting session"""
    __tablename__ = 'votos'
    
    id = Column(Integer, primary_key=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=False)
    votacao_id = Column(Integer, ForeignKey('votacoes.id'), nullable=False)
    voto = Column(String(20), nullable=False)  # Sim, Não, Abstenção, Obstrução, Ausente
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    deputado = relationship("Deputado", back_populates="votos")
    votacao = relationship("Votacao", back_populates="votos")
    
    # Unique constraint to prevent duplicate votes
    __table_args__ = (
        UniqueConstraint('deputado_id', 'votacao_id', name='unique_deputado_votacao'),
        Index('idx_voto_deputado_votacao', 'deputado_id', 'votacao_id'),
    )


class EstatisticaDeputado(Base):
    """Statistics for a deputy's voting behavior"""
    __tablename__ = 'estatisticas_deputados'
    
    id = Column(Integer, primary_key=True)
    deputado_id = Column(Integer, ForeignKey('deputados.id'), nullable=False, unique=True)
    
    # Voting statistics
    total_votacoes_analisadas = Column(Integer, default=0)
    participacao = Column(Integer, default=0)
    presenca_percentual = Column(Float, default=0.0)
    votos_favoraveis = Column(Integer, default=0)
    votos_contrarios = Column(Integer, default=0)
    abstencoes = Column(Integer, default=0)
    obstrucoes = Column(Integer, default=0)
    ausencias = Column(Integer, default=0)
    
    # Analysis metadata
    analisado_em = Column(DateTime, default=func.now())
    proposicoes_analisadas = Column(Integer, default=0)
    proposicoes_tentadas = Column(Integer, default=0)
    taxa_sucesso = Column(Float, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    deputado = relationship("Deputado", back_populates="estatisticas")


class CacheMetadata(Base):
    """Metadata for API response caching"""
    __tablename__ = 'cache_metadata'
    
    id = Column(Integer, primary_key=True)
    cache_key = Column(String(255), unique=True, nullable=False, index=True)
    cache_type = Column(String(50), nullable=False)  # deputados, proposicoes, votacoes, etc.
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    # Indexes
    __table_args__ = (
        Index('idx_cache_type_expires', 'cache_type', 'expires_at'),
    )


# Utility views or functions could be added here for common queries
class ViewDeputadoCompleto(Base):
    """View combining deputy information with party and statistics"""
    __tablename__ = 'view_deputados_completo'
    __table_args__ = {'info': {'is_view': True}}
    
    deputado_id = Column(Integer, primary_key=True)
    nome = Column(String(255))
    nome_parlamentar = Column(String(255))
    partido_sigla = Column(String(10))
    partido_nome = Column(String(255))
    uf = Column(String(2))
    situacao = Column(String(50))
    total_votacoes = Column(Integer)
    presenca_percentual = Column(Float)
    votos_favoraveis = Column(Integer)
    votos_contrarios = Column(Integer)
