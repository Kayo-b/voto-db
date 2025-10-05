#!/usr/bin/env python3
"""
Script para testar o sistema de análise de votações
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analisador_votacoes import AnalisadorVotacoes
import json
from datetime import datetime

def main():
    print("🚀 Testando Sistema de Análise de Votações")
    print("=" * 60)
    
    # Initialize analyzer
    analisador = AnalisadorVotacoes()
    
    # Test 1: Search for a proposition
    print("\n📋 TESTE 1: Buscar Proposição")
    print("-" * 40)
    proposicao = analisador.buscar_proposicao("PL", 6787, 2016)
    
    if proposicao:
        print(f"✅ Proposição encontrada:")
        print(f"   ID: {proposicao['id']}")
        print(f"   Ementa: {proposicao.get('ementa', 'N/A')[:100]}...")
    else:
        print("❌ Proposição não encontrada")
        return
    
    # Test 2: Process complete proposition analysis
    print("\n🔍 TESTE 2: Análise Completa de Proposição")
    print("-" * 40)
    
    resultado = analisador.processar_proposicao_completa(
        tipo="PL",
        numero=6787,
        ano=2016,
        titulo="Lei da Terceirização",
        relevancia="alta"
    )
    
    if resultado:
        print(f"✅ Análise concluída:")
        print(f"   Proposição: {resultado['proposicao']['titulo']}")
        print(f"   ID Votação Principal: {resultado['votacao_principal']['id']}")
        print(f"   Total de Votos: {resultado['votacao_principal']['total_votos']}")
        
        # Show voting statistics
        stats = resultado['estatisticas_votacao']
        print(f"   Distribuição de Votos:")
        for tipo, quantidade in stats['distribuicao_votos'].items():
            if quantidade > 0:
                print(f"     {tipo}: {quantidade}")
        
        # Save result
        analisador.salvar_dados(resultado, "teste_proposicao_6787_2016.json")
    else:
        print("❌ Não foi possível processar a proposição")
        return
    
    # Test 3: Analyze deputy profile
    print("\n👤 TESTE 3: Análise de Perfil de Deputado")
    print("-" * 40)
    
    # Find a deputy ID from the voting results
    votos = resultado.get('votos', [])
    if votos:
        primeiro_voto = votos[0]
        deputado_data = primeiro_voto.get('deputado_', {})
        deputado_id = deputado_data.get('id')
        deputado_nome = deputado_data.get('nome')
        
        if deputado_id:
            print(f"🔍 Analisando deputado: {deputado_nome} (ID: {deputado_id})")
            
            analise = analisador.analisar_deputado(deputado_id, [resultado])
            
            if analise.get('deputado'):
                dep_info = analise['deputado']
                stats = analise['estatisticas']
                
                print(f"✅ Análise do deputado:")
                print(f"   Nome: {dep_info['nome_parlamentar']}")
                print(f"   Partido: {dep_info['partido']} - {dep_info['uf']}")
                print(f"   Participação: {stats['participacao']}/{stats['total_votacoes_analisadas']}")
                print(f"   Presença: {stats['presenca_percentual']}%")
                
                # Save deputy analysis
                analisador.salvar_dados(analise, f"teste_deputado_{deputado_id}.json")
            else:
                print("❌ Erro na análise do deputado")
    
    # Test 4: Load propositions data
    print("\n📊 TESTE 4: Carregar Proposições Relevantes")
    print("-" * 40)
    
    try:
        dados_proposicoes = analisador.carregar_dados("proposicoes.json")
        if dados_proposicoes:
            proposicoes = dados_proposicoes.get("proposicoes_relevantes", [])
            print(f"✅ {len(proposicoes)} proposições relevantes carregadas:")
            
            for i, prop in enumerate(proposicoes[:5], 1):  # Show first 5
                print(f"   {i}. {prop['tipo']} {prop['numero']}/{prop['ano']} - {prop['titulo']}")
            
            if len(proposicoes) > 5:
                print(f"   ... e mais {len(proposicoes) - 5} proposições")
        else:
            print("❌ Não foi possível carregar dados de proposições")
    except Exception as e:
        print(f"❌ Erro ao carregar proposições: {e}")
    
    print(f"\n🎉 Testes concluídos em {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    # Summary
    print("\n📋 RESUMO DOS ARQUIVOS GERADOS:")
    data_dir = analisador.data_dir
    try:
        arquivos = os.listdir(data_dir)
        arquivos_json = [f for f in arquivos if f.endswith('.json')]
        
        for arquivo in arquivos_json:
            caminho = os.path.join(data_dir, arquivo)
            tamanho = os.path.getsize(caminho) / 1024  # KB
            print(f"   📄 {arquivo} ({tamanho:.1f} KB)")
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")

if __name__ == "__main__":
    main()