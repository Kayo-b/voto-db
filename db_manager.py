#!/usr/bin/env python3
"""
Database management utility for Voto-DB.
Provides common database operations and data import functions.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

def show_database_info():
    """Display current database information"""
    try:
        from database.connection import SessionLocal
        from database.model import *
        
        with SessionLocal() as db:
            print("📊 DATABASE SUMMARY")
            print("=" * 50)
            
            # Count records in each table
            counts = {
                'Political Parties': db.query(Partido).count(),
                'Deputies': db.query(Deputado).count(),
                'Proposals': db.query(Proposicao).count(),
                'Voting Sessions': db.query(Votacao).count(),
                'Individual Votes': db.query(Voto).count(),
                'Deputy Statistics': db.query(EstatisticaDeputado).count(),
                'Legislatures': db.query(Legislatura).count(),
                'Cache Entries': db.query(CacheMetadata).count()
            }
            
            for name, count in counts.items():
                print(f"{name:20}: {count:>6} records")
                
            # Show sample data
            print(f"\n📋 SAMPLE DATA")
            print("-" * 30)
            
            # Show parties
            partidos = db.query(Partido).limit(5).all()
            if partidos:
                print("Political Parties:")
                for p in partidos:
                    print(f"  • {p.sigla}: {p.nome}")
            
            # Show deputies
            deputados = db.query(Deputado).limit(3).all()
            if deputados:
                print(f"\nDeputies:")
                for d in deputados:
                    partido = db.query(Partido).filter_by(id=d.partido_id).first()
                    print(f"  • {d.nome_parlamentar} ({d.sigla_uf}-{partido.sigla if partido else 'N/A'})")
            
            # Show proposals
            proposicoes = db.query(Proposicao).limit(3).all()
            if proposicoes:
                print(f"\nProposals:")
                for p in proposicoes:
                    print(f"  • {p.codigo}: {p.titulo[:60]}...")
            
    except Exception as e:
        print(f"❌ Error accessing database: {e}")


def create_sample_data():
    """Create additional sample data based on API responses"""
    try:
        from database.connection import SessionLocal
        from database.repository import *
        from datetime import datetime
        
        with SessionLocal() as db:
            print("📥 CREATING SAMPLE DATA")
            print("=" * 50)
            
            # Add more parties from the API examples
            partido_repo = PartidoRepository(db)
            
            additional_parties = [
                {'sigla': 'PSOL', 'nome': 'Partido Socialismo e Liberdade'},
                {'sigla': 'NOVO', 'nome': 'Partido Novo'},
                {'sigla': 'REPUBLICANOS', 'nome': 'Republicanos'},
                {'sigla': 'UNIÃO', 'nome': 'União Brasil'},
                {'sigla': 'CIDADANIA', 'nome': 'Cidadania'}
            ]
            
            for party_data in additional_parties:
                if not partido_repo.get_by_sigla(party_data['sigla']):
                    partido_repo.create_or_update(party_data)
                    print(f"✅ Created party: {party_data['sigla']}")
            
            # Add more deputies from API example
            deputado_repo = DeputadoRepository(db)
            legislatura = db.query(Legislatura).first()
            
            sample_deputies = [
                {
                    'id': 220554, 'nome': 'Alexandre Lindenmeyer', 'nome_parlamentar': 'Alexandre Lindenmeyer',
                    'sigla_uf': 'RS', 'email': 'dep.alexandrelindenmeyer@camara.leg.br',
                    'situacao': 'Exercício', 'party_sigla': 'PT'
                },
                {
                    'id': 178831, 'nome': 'André Abdon', 'nome_parlamentar': 'André Abdon',
                    'sigla_uf': 'AP', 'email': 'dep.andreabdon@camara.leg.br',
                    'situacao': 'Exercício', 'party_sigla': 'PP'
                },
                {
                    'id': 133439, 'nome': 'André Figueiredo', 'nome_parlamentar': 'André Figueiredo',
                    'sigla_uf': 'CE', 'email': 'dep.andrefigueiredo@camara.leg.br',
                    'situacao': 'Exercício', 'party_sigla': 'PDT'
                }
            ]
            
            for deputy_data in sample_deputies:
                if not deputado_repo.get_by_id(deputy_data['id']):
                    partido = partido_repo.get_by_sigla(deputy_data.pop('party_sigla'))
                    if partido and legislatura:
                        deputy_data['partido_id'] = partido.id
                        deputy_data['legislatura_id'] = legislatura.id
                        deputado_repo.create_or_update(deputy_data)
                        print(f"✅ Created deputy: {deputy_data['nome']}")
            
            # Add sample proposals
            proposicao_repo = ProposicaoRepository(db)
            
            sample_proposals = [
                {
                    'codigo': 'PL 1234/2023',
                    'titulo': 'Marco Civil da Internet - Atualização',
                    'ementa': 'Atualiza o Marco Civil da Internet',
                    'tipo': 'PL', 'numero': '1234', 'ano': 2023,
                    'relevancia': 'alta'
                },
                {
                    'codigo': 'PEC 15/2022',
                    'titulo': 'PEC do Auxílio Emergencial Permanente',
                    'ementa': 'Institui auxílio emergencial permanente',
                    'tipo': 'PEC', 'numero': '15', 'ano': 2022,
                    'relevancia': 'alta'
                }
            ]
            
            for prop_data in sample_proposals:
                if not proposicao_repo.get_by_codigo(prop_data['codigo']):
                    proposicao_repo.create_or_update(prop_data)
                    print(f"✅ Created proposal: {prop_data['codigo']}")
            
            print(f"\n✅ Sample data creation completed!")
            
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Voto-DB Database Management')
    parser.add_argument('action', choices=['info', 'sample', 'reset'], 
                      help='Action to perform')
    
    args = parser.parse_args()
    
    print("🗳️  VOTO-DB DATABASE MANAGER")
    print("=" * 50)
    
    if args.action == 'info':
        show_database_info()
    
    elif args.action == 'sample':
        create_sample_data()
        show_database_info()
    
    elif args.action == 'reset':
        print("⚠️  WARNING: This will delete ALL data!")
        confirm = input("Type 'RESET' to confirm: ")
        if confirm == 'RESET':
            os.system('docker exec -i votodb-postgres psql -U postgres -d votodb < reset_database_schema.sql')
            print("✅ Database reset completed!")
        else:
            print("❌ Reset cancelled")
    
    print(f"\n💡 Usage tips:")
    print(f"   • Use: python db_manager.py info     - Show database information")
    print(f"   • Use: python db_manager.py sample   - Add sample data")  
    print(f"   • Use: python db_manager.py reset    - Reset entire database")


if __name__ == "__main__":
    main()