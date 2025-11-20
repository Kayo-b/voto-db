"""
Script para testar a API de proposições relevantes
"""

import requests
import json

BASE_URL = "http://localhost:8001"

def test_validate_proposicao():
    """Testa validação de proposição"""
    print("\n=== Testando Validação de Proposição ===")
    
    # Teste com proposição válida
    codigo = "PL 6787/2016"
    response = requests.post(
        f"{BASE_URL}/proposicoes/relevantes/validate",
        json={"codigo": codigo}
    )
    
    print(f"\nValidando: {codigo}")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_add_proposicao():
    """Testa adição de proposição"""
    print("\n=== Testando Adição de Proposição ===")
    
    codigo = "PL 6787/2016"
    response = requests.post(
        f"{BASE_URL}/proposicoes/relevantes",
        json={
            "codigo": codigo,
            "relevancia": "alta"
        }
    )
    
    print(f"\nAdicionando: {codigo}")
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_get_proposicoes():
    """Testa busca de proposições"""
    print("\n=== Testando Busca de Proposições ===")
    
    response = requests.get(f"{BASE_URL}/proposicoes/relevantes")
    
    print(f"\nStatus: {response.status_code}")
    result = response.json()
    print(f"Total de proposições: {len(result.get('data', {}).get('votacoes_historicas', []))}")
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def test_delete_proposicao(proposicao_id):
    """Testa remoção de proposição"""
    print(f"\n=== Testando Remoção de Proposição ID: {proposicao_id} ===")
    
    response = requests.delete(f"{BASE_URL}/proposicoes/relevantes/{proposicao_id}")
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Resposta: {json.dumps(result, indent=2, ensure_ascii=False)}")
    
    return result

def main():
    print("Iniciando testes da API de Proposições Relevantes")
    print("=" * 60)
    
    try:
        # 1. Validar proposição
        validation = test_validate_proposicao()
        
        if validation.get('success'):
            print("\n✓ Validação bem-sucedida!")
            
            # 2. Adicionar proposição
            add_result = test_add_proposicao()
            
            if add_result.get('success'):
                print("\n✓ Adição bem-sucedida!")
                
                # 3. Buscar proposições
                get_result = test_get_proposicoes()
                
                if get_result.get('success'):
                    print("\n✓ Busca bem-sucedida!")
                    
                    # 4. Tentar remover a primeira proposição (se houver ID)
                    proposicoes = get_result.get('data', {}).get('votacoes_historicas', [])
                    if proposicoes and proposicoes[0].get('id'):
                        delete_result = test_delete_proposicao(proposicoes[0]['id'])
                        
                        if delete_result.get('success'):
                            print("\n✓ Remoção bem-sucedida!")
                        else:
                            print("\n✗ Erro na remoção")
            else:
                print(f"\n✗ Erro na adição: {add_result.get('error')}")
        else:
            print(f"\n✗ Erro na validação: {validation.get('error')}")
            
    except requests.exceptions.ConnectionError:
        print("\n✗ Erro: Não foi possível conectar ao servidor")
        print("Certifique-se de que o servidor está rodando em http://localhost:8001")
    except Exception as e:
        print(f"\n✗ Erro inesperado: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Testes finalizados")

if __name__ == "__main__":
    main()
