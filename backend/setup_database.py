#!/usr/bin/env python3
"""
Database setup and migration script for VotoDB
Creates tables, imports existing cache data, and initializes the system
"""

import sys
import os
import json
from datetime import datetime
from typing import Dict, List

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database import (
        init_database, test_connection, get_db_session,
        Deputado, Proposicao, Votacao, Voto, CacheStatus
    )
    from database.service import VotoDBService
    DATABASE_AVAILABLE = True
except ImportError as e:
    print(f"Database components not available: {e}")
    print("Please install required dependencies:")
    print("pip install sqlalchemy psycopg2-binary")
    DATABASE_AVAILABLE = False
    sys.exit(1)

class DatabaseSetup:
    """Setup and migration handler"""
    
    def __init__(self):
        self.cache_dir = "data/cache"
        self.data_dir = "data"
        
    def setup_database(self):
        """Complete database setup process"""
        print("Iniciando configuração do banco de dados VotoDB")
        print("=" * 60)
        
        # Test connection
        print("\n1. Testando conexão com PostgreSQL...")
        if not test_connection():
            print("Falha na conexão com PostgreSQL")
            print("\nVerifique as variáveis de ambiente:")
            print("  - DATABASE_URL ou")
            print("  - DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME")
            return False
        
        print("Conexão com PostgreSQL estabelecida")
        
        # Initialize tables
        print("\n2. Criando tabelas...")
        try:
            init_database()
            print("Tabelas criadas com sucesso")
        except Exception as e:
            print(f"Erro ao criar tabelas: {e}")
            return False
        
        # Import existing cache data
        print("\n3. Importando dados do cache existente...")
        imported_counts = self.import_cache_data()
        
        if any(imported_counts.values()):
            print("Dados importados com sucesso:")
            for data_type, count in imported_counts.items():
                if count > 0:
                    print(f"  - {data_type}: {count} registros")
        else:
            print("Nenhum dado de cache encontrado para importar")
        
        # Verify setup
        print("\n4. Verificando configuração...")
        stats = self.get_database_stats()
        print("Configuração completa!")
        print("\nEstatísticas do banco:")
        for table, count in stats.items():
            print(f"  - {table}: {count} registros")
        
        print(f"\nBanco de dados VotoDB configurado com sucesso!")
        print("=" * 60)
        return True
    
    def import_cache_data(self) -> Dict[str, int]:
        """Import existing JSON cache files into database"""
        imported = {"deputados": 0, "proposicoes": 0, "votacoes": 0, "votos": 0}
        
        try:
            with get_db_session() as session:
                # Import proposições cache
                proposicoes_file = os.path.join(self.cache_dir, "proposicoes_cache.json")
                if os.path.exists(proposicoes_file):
                    with open(proposicoes_file, 'r', encoding='utf-8') as f:
                        proposicoes_cache = json.load(f)
                    
                    for cache_key, prop_data in proposicoes_cache.items():
                        if isinstance(prop_data, dict) and prop_data.get('id'):
                            self._import_proposicao(session, prop_data)
                            imported["proposicoes"] += 1
                
                # Import detalhes cache (more complete proposição data)
                detalhes_file = os.path.join(self.cache_dir, "detalhes_cache.json")
                if os.path.exists(detalhes_file):
                    with open(detalhes_file, 'r', encoding='utf-8') as f:
                        detalhes_cache = json.load(f)
                    
                    for prop_id, prop_data in detalhes_cache.items():
                        if isinstance(prop_data, dict):
                            self._import_proposicao(session, prop_data)
                
                # Import votações cache
                votacoes_file = os.path.join(self.cache_dir, "votacoes_cache.json")
                if os.path.exists(votacoes_file):
                    with open(votacoes_file, 'r', encoding='utf-8') as f:
                        votacoes_cache = json.load(f)
                    
                    for prop_id, votacoes_list in votacoes_cache.items():
                        if isinstance(votacoes_list, list):
                            for votacao_data in votacoes_list:
                                if isinstance(votacao_data, dict):
                                    self._import_votacao(session, int(prop_id), votacao_data)
                                    imported["votacoes"] += 1
                
                # Import votos cache
                votos_file = os.path.join(self.cache_dir, "votos_cache.json")
                if os.path.exists(votos_file):
                    with open(votos_file, 'r', encoding='utf-8') as f:
                        votos_cache = json.load(f)
                    
                    for votacao_id, votos_list in votos_cache.items():
                        if isinstance(votos_list, list):
                            for voto_data in votos_list:
                                if isinstance(voto_data, dict):
                                    self._import_voto(session, votacao_id, voto_data)
                                    imported["votos"] += 1
                
                session.commit()
        
        except Exception as e:
            print(f"Erro durante importação: {e}")
        
        return imported
    
    def _import_proposicao(self, session, prop_data: Dict):
        """Import single proposição"""
        try:
            prop_id = prop_data.get('id')
            if not prop_id:
                return
            
            # Check if exists
            existing = session.query(Proposicao).filter(Proposicao.id == prop_id).first()
            if existing:
                return
            
            proposicao = Proposicao(
                id=prop_id,
                tipo=prop_data.get('siglaTipo', ''),
                numero=prop_data.get('numero', 0),
                ano=prop_data.get('ano', 0),
                ementa=prop_data.get('ementa', ''),
                titulo=prop_data.get('ementa', ''),
                uri=prop_data.get('uri', ''),
                dados_completos=prop_data
            )
            
            session.add(proposicao)
            
        except Exception as e:
            print(f"Erro ao importar proposição {prop_data.get('id', 'N/A')}: {e}")
    
    def _import_votacao(self, session, proposicao_id: int, votacao_data: Dict):
        """Import single votação"""
        try:
            votacao_id = votacao_data.get('id')
            if not votacao_id:
                return
            
            # Check if exists
            existing = session.query(Votacao).filter(Votacao.id == votacao_id).first()
            if existing:
                return
            
            # Parse datetime
            data_hora_registro = None
            if votacao_data.get('dataHoraRegistro'):
                try:
                    data_hora_registro = datetime.fromisoformat(
                        votacao_data['dataHoraRegistro'].replace('Z', '+00:00')
                    )
                except:
                    pass
            
            votacao = Votacao(
                id=votacao_id,
                proposicao_id=proposicao_id,
                data_hora_registro=data_hora_registro,
                descricao=votacao_data.get('descricao', ''),
                sigla_orgao=votacao_data.get('siglaOrgao', ''),
                uri_orgao=votacao_data.get('uriOrgao', ''),
                aprovacao=votacao_data.get('aprovacao', False),
                dados_completos=votacao_data
            )
            
            session.add(votacao)
            
        except Exception as e:
            print(f"Erro ao importar votação {votacao_data.get('id', 'N/A')}: {e}")
    
    def _import_voto(self, session, votacao_id: str, voto_data: Dict):
        """Import single voto"""
        try:
            deputado_data = voto_data.get('deputado_', {})
            deputado_id = deputado_data.get('id')
            
            if not deputado_id:
                return
            
            # Import deputado first
            self._import_deputado(session, deputado_data)
            
            # Check if voto exists
            existing = session.query(Voto).filter(
                Voto.deputado_id == deputado_id,
                Voto.votacao_id == votacao_id
            ).first()
            
            if existing:
                return
            
            voto = Voto(
                deputado_id=deputado_id,
                votacao_id=votacao_id,
                tipo_voto=voto_data.get('tipoVoto', ''),
                dados_completos=voto_data
            )
            
            session.add(voto)
            
        except Exception as e:
            print(f"Erro ao importar voto: {e}")
    
    def _import_deputado(self, session, deputado_data: Dict):
        """Import single deputado"""
        try:
            deputado_id = deputado_data.get('id')
            if not deputado_id:
                return
            
            # Check if exists
            existing = session.query(Deputado).filter(Deputado.id == deputado_id).first()
            if existing:
                return
            
            deputado = Deputado(
                id=deputado_id,
                nome_civil=deputado_data.get('nome', ''),
                nome_parlamentar=deputado_data.get('nome', ''),
                sigla_partido=deputado_data.get('siglaPartido', ''),
                sigla_uf=deputado_data.get('siglaUf', ''),
                dados_completos=deputado_data
            )
            
            session.add(deputado)
            
        except Exception as e:
            print(f"Erro ao importar deputado {deputado_data.get('id', 'N/A')}: {e}")
    
    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        try:
            with get_db_session() as session:
                return {
                    "deputados": session.query(Deputado).count(),
                    "proposicoes": session.query(Proposicao).count(),
                    "votacoes": session.query(Votacao).count(),
                    "votos": session.query(Voto).count(),
                    "cache_status": session.query(CacheStatus).count()
                }
        except Exception as e:
            print(f"Erro ao obter estatísticas: {e}")
            return {}
    
    def create_sample_data(self):
        """Create sample data for testing"""
        print("\n5. Criando dados de exemplo...")
        
        sample_data = {
            "deputado": {
                "id": 999999,
                "nome": "Deputado Exemplo",
                "siglaPartido": "EX",
                "siglaUf": "DF"
            },
            "proposicao": {
                "id": 999999,
                "siglaTipo": "PL",
                "numero": 9999,
                "ano": 2025,
                "ementa": "Proposição de exemplo para testes"
            }
        }
        
        try:
            with get_db_session() as session:
                # Sample deputado
                deputado = Deputado(
                    id=sample_data["deputado"]["id"],
                    nome_civil=sample_data["deputado"]["nome"],
                    nome_parlamentar=sample_data["deputado"]["nome"],
                    sigla_partido=sample_data["deputado"]["siglaPartido"],
                    sigla_uf=sample_data["deputado"]["siglaUf"],
                    dados_completos=sample_data["deputado"]
                )
                
                # Sample proposição
                proposicao = Proposicao(
                    id=sample_data["proposicao"]["id"],
                    tipo=sample_data["proposicao"]["siglaTipo"],
                    numero=sample_data["proposicao"]["numero"],
                    ano=sample_data["proposicao"]["ano"],
                    ementa=sample_data["proposicao"]["ementa"],
                    dados_completos=sample_data["proposicao"]
                )
                
                session.add(deputado)
                session.add(proposicao)
                session.commit()
                
                print("Dados de exemplo criados")
                
        except Exception as e:
            print(f"Erro ao criar dados de exemplo: {e}")

def main():
    """Main setup function"""
    if not DATABASE_AVAILABLE:
        return False
    
    setup = DatabaseSetup()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "init":
            return setup.setup_database()
        elif command == "stats":
            stats = setup.get_database_stats()
            print("Estatísticas do banco de dados:")
            for table, count in stats.items():
                print(f"  {table}: {count}")
            return True
        elif command == "sample":
            setup.create_sample_data()
            return True
        elif command == "test":
            return test_connection()
        else:
            print(f"Comando desconhecido: {command}")
            print("Comandos disponíveis: init, stats, sample, test")
            return False
    else:
        return setup.setup_database()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)