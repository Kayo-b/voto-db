#!/usr/bin/env python3
"""
Database initialization and testing script for Voto-DB.
Run this script to initialize the database schema and test connections.
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

def main():
    """Main function to initialize and test the database"""
    
    print("🔧 Voto-DB Database Initialization")
    print("=" * 50)
    
    # Test database connection
    print("1. Testing database connection...")
    try:
        from database.connection import check_database_connection
        if check_database_connection():
            print("   ✅ Database connection successful!")
        else:
            print("   ❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"   ❌ Error testing connection: {e}")
        print("   💡 Make sure PostgreSQL is running and accessible")
        return False
    
    # Create tables using SQLAlchemy
    print("\n2. Creating database tables...")
    try:
        from database.connection import create_tables
        create_tables()
        print("   ✅ Tables created successfully!")
    except Exception as e:
        print(f"   ❌ Error creating tables: {e}")
        return False
    
    # Test basic operations
    print("\n3. Testing basic database operations...")
    try:
        from database.connection import SessionLocal
        from database.repository import PartidoRepository, DeputadoRepository
        
        with SessionLocal() as db:
            # Test partido operations
            partido_repo = PartidoRepository(db)
            
            # Check if parties exist
            partidos = partido_repo.get_all()
            print(f"   📊 Found {len(partidos)} political parties in database")
            
            # Test deputado repository
            deputado_repo = DeputadoRepository(db)
            print("   ✅ Repository operations working correctly!")
            
    except Exception as e:
        print(f"   ❌ Error testing operations: {e}")
        return False
    
    print("\n🎉 Database initialization completed successfully!")
    print("\n📋 Database Summary:")
    print("   • Tables: legislaturas, partidos, deputados, proposicoes, votacoes, votos, estatisticas_deputados, cache_metadata")
    print("   • View: view_deputados_completo")
    print("   • Triggers: Auto-updating timestamps")
    print("\n💡 Next steps:")
    print("   1. Run the SQL migration script if you prefer SQL: psql -U postgres -d votodb -f database_migration.sql")
    print("   2. Use the repository classes to interact with the database")
    print("   3. Import data from the Chamber of Deputies API")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)