"""
Database package for Voto-DB.
Provides SQLAlchemy models, connection management, and data repositories.
"""

from .model import (
    Base,
    Deputado,
    Partido, 
    Proposicao,
    Votacao,
    Voto,
    EstatisticaDeputado,
    Legislatura,
    CacheMetadata
)

from .connection import (
    engine,
    SessionLocal,
    get_database,
    create_tables,
    drop_tables,
    check_database_connection
)

from .repository import (
    DeputadoRepository,
    PartidoRepository,
    ProposicaoRepository,
    VotacaoRepository,
    VotoRepository,
    EstatisticaDeputadoRepository,
    CacheRepository
)

__all__ = [
    # Models
    'Base',
    'Deputado',
    'Partido',
    'Proposicao', 
    'Votacao',
    'Voto',
    'EstatisticaDeputado',
    'Legislatura',
    'CacheMetadata',
    
    # Connection
    'engine',
    'SessionLocal',
    'get_database',
    'create_tables',
    'drop_tables',
    'check_database_connection',
    
    # Repositories
    'DeputadoRepository',
    'PartidoRepository', 
    'ProposicaoRepository',
    'VotacaoRepository',
    'VotoRepository',
    'EstatisticaDeputadoRepository',
    'CacheRepository'
]