"""
Database operations and data access layer for Voto-DB.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from .model import (
    Deputado, Partido, Proposicao, Votacao, Voto, 
    EstatisticaDeputado, Legislatura, CacheMetadata
)


class DeputadoRepository:
    """Repository for deputado operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, deputado_id: int) -> Optional[Deputado]:
        """Get deputado by ID"""
        return self.db.query(Deputado).filter(Deputado.id == deputado_id).first()
    
    def search_by_name(self, name: str, limit: int = 50) -> List[Deputado]:
        """Search deputados by name (partial match)"""
        search_term = f"%{name.lower()}%"
        return self.db.query(Deputado).filter(
            or_(
                func.lower(Deputado.nome).contains(search_term),
                func.lower(Deputado.nome_parlamentar).contains(search_term)
            )
        ).limit(limit).all()
    
    def get_by_party(self, party_sigla: str) -> List[Deputado]:
        """Get all deputados from a specific party"""
        return self.db.query(Deputado).join(Partido).filter(
            Partido.sigla == party_sigla
        ).all()
    
    def get_by_uf(self, uf: str) -> List[Deputado]:
        """Get all deputados from a specific state"""
        return self.db.query(Deputado).filter(Deputado.sigla_uf == uf).all()
    
    def create_or_update(self, deputado_data: dict) -> Deputado:
        """Create or update deputado"""
        existing = self.get_by_id(deputado_data['id'])
        
        if existing:
            for key, value in deputado_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            deputado = existing
        else:
            deputado = Deputado(**deputado_data)
            self.db.add(deputado)
        
        self.db.commit()
        self.db.refresh(deputado)
        return deputado


class PartidoRepository:
    """Repository for partido operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_sigla(self, sigla: str) -> Optional[Partido]:
        """Get partido by sigla"""
        return self.db.query(Partido).filter(Partido.sigla == sigla).first()
    
    def get_all(self) -> List[Partido]:
        """Get all partidos"""
        return self.db.query(Partido).order_by(Partido.sigla).all()
    
    def create_or_update(self, partido_data: dict) -> Partido:
        """Create or update partido"""
        existing = self.get_by_sigla(partido_data['sigla'])
        
        if existing:
            for key, value in partido_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            partido = existing
        else:
            partido = Partido(**partido_data)
            self.db.add(partido)
        
        self.db.commit()
        self.db.refresh(partido)
        return partido


class ProposicaoRepository:
    """Repository for proposicao operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_codigo(self, codigo: str) -> Optional[Proposicao]:
        """Get proposicao by codigo"""
        return self.db.query(Proposicao).filter(Proposicao.codigo == codigo).first()
    
    def get_by_relevancia(self, relevancia: str) -> List[Proposicao]:
        """Get proposicoes by relevancia level"""
        return self.db.query(Proposicao).filter(
            Proposicao.relevancia == relevancia
        ).order_by(desc(Proposicao.ano)).all()
    
    def search_by_title(self, title_term: str, limit: int = 50) -> List[Proposicao]:
        """Search proposicoes by title"""
        search_term = f"%{title_term.lower()}%"
        return self.db.query(Proposicao).filter(
            func.lower(Proposicao.titulo).contains(search_term)
        ).limit(limit).all()
    
    def create_or_update(self, proposicao_data: dict) -> Proposicao:
        """Create or update proposicao"""
        existing = self.get_by_codigo(proposicao_data['codigo'])
        
        if existing:
            for key, value in proposicao_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            proposicao = existing
        else:
            proposicao = Proposicao(**proposicao_data)
            self.db.add(proposicao)
        
        self.db.commit()
        self.db.refresh(proposicao)
        return proposicao


class VotacaoRepository:
    """Repository for votacao operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_proposicao(self, proposicao_id: int) -> List[Votacao]:
        """Get all votacoes for a proposicao"""
        return self.db.query(Votacao).filter(
            Votacao.proposicao_id == proposicao_id
        ).order_by(desc(Votacao.data_votacao)).all()
    
    def get_recent(self, days: int = 30, limit: int = 100) -> List[Votacao]:
        """Get recent votacoes"""
        since = datetime.now() - timedelta(days=days)
        return self.db.query(Votacao).filter(
            Votacao.data_votacao >= since
        ).order_by(desc(Votacao.data_votacao)).limit(limit).all()
    
    def create_or_update(self, votacao_data: dict) -> Votacao:
        """Create or update votacao"""
        votacao = Votacao(**votacao_data)
        self.db.add(votacao)
        self.db.commit()
        self.db.refresh(votacao)
        return votacao


class VotoRepository:
    """Repository for voto operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_deputado(self, deputado_id: int, limit: int = 100) -> List[Voto]:
        """Get votos by deputado"""
        return self.db.query(Voto).filter(
            Voto.deputado_id == deputado_id
        ).join(Votacao).order_by(desc(Votacao.data_votacao)).limit(limit).all()
    
    def get_by_votacao(self, votacao_id: int) -> List[Voto]:
        """Get all votos for a votacao"""
        return self.db.query(Voto).filter(Voto.votacao_id == votacao_id).all()
    
    def get_deputado_vote_stats(self, deputado_id: int) -> Dict[str, int]:
        """Get vote statistics for a deputado"""
        votes = self.db.query(Voto.voto, func.count(Voto.id)).filter(
            Voto.deputado_id == deputado_id
        ).group_by(Voto.voto).all()
        
        return {vote_type: count for vote_type, count in votes}
    
    def create_or_update(self, voto_data: dict) -> Voto:
        """Create or update voto"""
        existing = self.db.query(Voto).filter(
            and_(
                Voto.deputado_id == voto_data['deputado_id'],
                Voto.votacao_id == voto_data['votacao_id']
            )
        ).first()
        
        if existing:
            existing.voto = voto_data['voto']
            voto = existing
        else:
            voto = Voto(**voto_data)
            self.db.add(voto)
        
        self.db.commit()
        self.db.refresh(voto)
        return voto


class EstatisticaDeputadoRepository:
    """Repository for deputy statistics"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_deputado(self, deputado_id: int) -> Optional[EstatisticaDeputado]:
        """Get statistics for a deputado"""
        return self.db.query(EstatisticaDeputado).filter(
            EstatisticaDeputado.deputado_id == deputado_id
        ).first()
    
    def create_or_update(self, stats_data: dict) -> EstatisticaDeputado:
        """Create or update deputy statistics"""
        existing = self.get_by_deputado(stats_data['deputado_id'])
        
        if existing:
            for key, value in stats_data.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
            stats = existing
        else:
            stats = EstatisticaDeputado(**stats_data)
            self.db.add(stats)
        
        self.db.commit()
        self.db.refresh(stats)
        return stats


class CacheRepository:
    """Repository for cache metadata operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_cache_entry(self, cache_key: str) -> Optional[CacheMetadata]:
        """Get cache entry by key"""
        return self.db.query(CacheMetadata).filter(
            CacheMetadata.cache_key == cache_key,
            CacheMetadata.expires_at > datetime.now()
        ).first()
    
    def create_cache_entry(self, cache_key: str, cache_type: str, ttl_hours: int = 24):
        """Create new cache entry"""
        expires_at = datetime.now() + timedelta(hours=ttl_hours)
        cache_entry = CacheMetadata(
            cache_key=cache_key,
            cache_type=cache_type,
            expires_at=expires_at
        )
        self.db.add(cache_entry)
        self.db.commit()
        return cache_entry
    
    def cleanup_expired(self):
        """Remove expired cache entries"""
        self.db.query(CacheMetadata).filter(
            CacheMetadata.expires_at < datetime.now()
        ).delete()
        self.db.commit()