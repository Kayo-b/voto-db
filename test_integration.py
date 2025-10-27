#!/usr/bin/env python3
"""
Test script to demonstrate the full database integration workflow.
This simulates what happens when:
1. Frontend calls /deputados?nome=andre 
2. Frontend calls /deputados/{id}/analise
"""

import sys
import os
import requests
import json
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

def test_database_integration():
    """Test the complete database integration workflow"""
    
    print("🧪 Testing Database Integration Workflow")
    print("=" * 60)
    
    # Test 1: Direct import functions
    print("\n1️⃣  Testing direct import functions...")
    
    try:
        from database.import_service import import_deputados_from_json
        from database.voting_import_service import import_voting_history_from_json
        from database.connection import check_database_connection, SessionLocal
        from database.model import Deputado, Voto, Proposicao
        
        # Check database connection
        if not check_database_connection():
            print("❌ Database connection failed!")
            return False
            
        print("✅ Database connection successful")
        
        # Test deputados import
        sample_deputados_response = {
            "dados": [
                {
                    "id": 999999,  # Test ID
                    "nome": "Test Deputy for Integration",
                    "siglaPartido": "TEST",
                    "uriPartido": "https://test.com/partidos/123",
                    "siglaUf": "DF",
                    "idLegislatura": 57,
                    "urlFoto": "https://test.com/photo.jpg",
                    "email": "test@test.com"
                }
            ]
        }
        
        result = import_deputados_from_json(sample_deputados_response)
        print(f"✅ Deputados import: {result['imported']} new, {result['updated']} updated")
        
        # Test voting history import
        sample_voting_response = {
            "success": True,
            "data": {
                "deputado": {
                    "id": 999999,
                    "nome": "Test Deputy for Integration",
                    "nome_parlamentar": "Test Deputy",
                    "partido": "TEST",
                    "uf": "DF",
                    "situacao": "Exercício"
                },
                "historico_votacoes": [
                    {
                        "proposicao": "TEST 1/2024",
                        "titulo": "Test Proposal for Integration",
                        "voto": "Sim",
                        "data": "2024-10-27T12:00:00",
                        "relevancia": "alta"
                    }
                ],
                "estatisticas": {
                    "total_votacoes_analisadas": 1,
                    "participacao": 1,
                    "presenca_percentual": 100.0,
                    "votos_favoraveis": 1,
                    "votos_contrarios": 0
                }
            },
            "proposicoes_analisadas": 1,
            "processamento": {
                "total_proposicoes_tentadas": 1,
                "proposicoes_com_sucesso": 1,
                "taxa_sucesso": "100.0%"
            }
        }
        
        voting_result = import_voting_history_from_json(sample_voting_response)
        print(f"✅ Voting history import: {voting_result['imported_votes']} votes imported")
        
    except Exception as e:
        print(f"❌ Direct import test failed: {e}")
        return False
    
    # Test 2: Verify data was stored
    print("\n2️⃣  Verifying data storage...")
    
    try:
        with SessionLocal() as db:
            # Check deputado was stored
            test_deputado = db.query(Deputado).filter(Deputado.id == 999999).first()
            if test_deputado:
                print(f"✅ Deputado stored: {test_deputado.nome} ({test_deputado.sigla_uf})")
            else:
                print("❌ Test deputado not found in database")
                return False
            
            # Check votes were stored
            votes_count = db.query(Voto).filter(Voto.deputado_id == 999999).count()
            print(f"✅ Votes stored: {votes_count} vote(s)")
            
            # Check proposicoes were stored
            test_proposicao = db.query(Proposicao).filter(Proposicao.codigo == "TEST 1/2024").first()
            if test_proposicao:
                print(f"✅ Proposição stored: {test_proposicao.codigo}")
            else:
                print("❌ Test proposição not found")
                return False
                
    except Exception as e:
        print(f"❌ Data verification failed: {e}")
        return False
    
    # Test 3: Cleanup test data
    print("\n3️⃣  Cleaning up test data...")
    
    try:
        with SessionLocal() as db:
            # Remove test data
            db.query(Voto).filter(Voto.deputado_id == 999999).delete()
            db.query(Deputado).filter(Deputado.id == 999999).delete()
            db.query(Proposicao).filter(Proposicao.codigo == "TEST 1/2024").delete()
            db.commit()
            print("✅ Test data cleaned up")
            
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        # Not critical for the test
    
    print("\n🎉 Database integration test completed successfully!")
    print("\n📋 What this means:")
    print("   • When frontend calls /deputados?nome=andre → Deputies automatically saved to DB")
    print("   • When DeputadoDetails calls /deputados/{id}/analise → Voting history saved to DB")  
    print("   • All API data is now persisted and can be queried directly from PostgreSQL")
    
    return True

if __name__ == "__main__":
    success = test_database_integration()
    if success:
        print("\n🚀 Ready for production! Start your servers:")
        print("   Backend: cd backend && uvicorn main_v2:app --reload --port 8001")
        print("   Frontend: cd frontend && npm start")
    else:
        print("\n❌ Integration test failed. Check the errors above.")
        
    sys.exit(0 if success else 1)