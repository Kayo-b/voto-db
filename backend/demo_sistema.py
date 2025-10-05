#!/usr/bin/env python3
"""
Demo script para mostrar o funcionamento do sistema de análise
com dados simulados para evitar timeouts da API
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import json
from datetime import datetime
from typing import Dict, List

class DemoAnaliseVotacoes:
    """Versão demo com dados simulados"""
    
    def __init__(self):
        self.data_dir = "data"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_demo_data(self) -> Dict:
        """Retorna dados simulados de uma proposição completa"""
        return {
            "proposicao": {
                "id": 2122076,
                "tipo": "PL",
                "numero": 6787,
                "ano": 2016,
                "titulo": "Lei da Terceirização",
                "relevancia": "alta",
                "ementa": "Altera o Decreto-Lei nº 5.452, de 1º de maio de 1943 - Consolidação das Leis do Trabalho",
                "situacao": "Transformado na Lei Ordinária 13429/2017"
            },
            "votacao_principal": {
                "id": "2122076-348",
                "descricao": "Votação do texto-base do Substitutivo da Comissão Especial ao Projeto de Lei",
                "data": "2017-03-22T19:45:00",
                "aprovacao": True,
                "total_votos": 487
            },
            "votos": [
                {
                    "deputado_": {
                        "id": 178864,
                        "nome": "André Figueiredo",
                        "siglaPartido": "PDT",
                        "siglaUf": "CE"
                    },
                    "tipoVoto": "Não"
                },
                {
                    "deputado_": {
                        "id": 74693,
                        "nome": "Antonio Carlos Mendes Thame",
                        "siglaPartido": "PV",
                        "siglaUf": "SP"
                    },
                    "tipoVoto": "Sim"
                },
                {
                    "deputado_": {
                        "id": 178957,
                        "nome": "Átila Lira",
                        "siglaPartido": "PSB",
                        "siglaUf": "PI"
                    },
                    "tipoVoto": "Sim"
                },
                {
                    "deputado_": {
                        "id": 178976,
                        "nome": "Benedita da Silva",
                        "siglaPartido": "PT",
                        "siglaUf": "RJ"
                    },
                    "tipoVoto": "Não"
                },
                {
                    "deputado_": {
                        "id": 178979,
                        "nome": "Beto Mansur",
                        "siglaPartido": "PRB",
                        "siglaUf": "SP"
                    },
                    "tipoVoto": "Sim"
                },
                {
                    "deputado_": {
                        "id": 178980,
                        "nome": "Carlos Zarattini",
                        "siglaPartido": "PT",
                        "siglaUf": "SP"
                    },
                    "tipoVoto": "Não"
                },
                {
                    "deputado_": {
                        "id": 161549,
                        "nome": "Eduardo Bolsonaro",
                        "siglaPartido": "PSL",
                        "siglaUf": "SP"
                    },
                    "tipoVoto": "Sim"
                },
                {
                    "deputado_": {
                        "id": 74847,
                        "nome": "Jair Bolsonaro",
                        "siglaPartido": "PSL",
                        "siglaUf": "RJ"
                    },
                    "tipoVoto": "Sim"
                },
                {
                    "deputado_": {
                        "id": 178983,
                        "nome": "Jean Wyllys",
                        "siglaPartido": "PSOL",
                        "siglaUf": "RJ"
                    },
                    "tipoVoto": "Não"
                },
                {
                    "deputado_": {
                        "id": 178984,
                        "nome": "João Derly",
                        "siglaPartido": "REDE",
                        "siglaUf": "RS"
                    },
                    "tipoVoto": "Abstenção"
                }
            ],
            "estatisticas_votacao": {
                "total_deputados": 10,
                "distribuicao_votos": {
                    "Sim": 5,
                    "Não": 4,
                    "Abstenção": 1,
                    "Obstrução": 0
                },
                "por_partido": {
                    "PDT": {"Sim": 0, "Não": 1, "Abstenção": 0, "total": 1},
                    "PV": {"Sim": 1, "Não": 0, "Abstenção": 0, "total": 1},
                    "PSB": {"Sim": 1, "Não": 0, "Abstenção": 0, "total": 1},
                    "PT": {"Sim": 0, "Não": 2, "Abstenção": 0, "total": 2},
                    "PRB": {"Sim": 1, "Não": 0, "Abstenção": 0, "total": 1},
                    "PSL": {"Sim": 2, "Não": 0, "Abstenção": 0, "total": 2},
                    "PSOL": {"Sim": 0, "Não": 1, "Abstenção": 0, "total": 1},
                    "REDE": {"Sim": 0, "Não": 0, "Abstenção": 1, "total": 1}
                }
            },
            "processado_em": datetime.now().isoformat()
        }
    
    def analisar_deputado_demo(self, deputado_id: int, proposicoes_analisadas: List[Dict]) -> Dict:
        """Análise demo de um deputado"""
        
        # Dados simulados de deputados
        deputados_info = {
            178864: {
                "nome": "André Figueiredo",
                "nome_parlamentar": "ANDRÉ FIGUEIREDO",
                "partido": "PDT",
                "uf": "CE",
                "situacao": "Exercício"
            },
            74847: {
                "nome": "Jair Messias Bolsonaro",
                "nome_parlamentar": "JAIR BOLSONARO",
                "partido": "PSL",
                "uf": "RJ",
                "situacao": "Exercício"
            },
            178976: {
                "nome": "Benedita Souza da Silva Sampaio",
                "nome_parlamentar": "BENEDITA DA SILVA",
                "partido": "PT",
                "uf": "RJ", 
                "situacao": "Exercício"
            }
        }
        
        deputado_info = deputados_info.get(deputado_id)
        if not deputado_info:
            return {"erro": "Deputado não encontrado"}
        
        # Analisar votos em proposições
        historico_votacoes = []
        total_votacoes = 0
        votos_favor = 0
        
        for prop_data in proposicoes_analisadas:
            proposicao = prop_data['proposicao']
            votos = prop_data.get('votos', [])
            
            # Encontrar voto deste deputado
            voto_deputado = None
            for voto in votos:
                dep_data = voto.get('deputado_', {})
                if dep_data.get('id') == deputado_id:
                    voto_deputado = voto
                    break
            
            if voto_deputado:
                total_votacoes += 1
                tipo_voto = voto_deputado.get('tipoVoto', '')
                
                if tipo_voto == 'Sim':
                    votos_favor += 1
                
                historico_votacoes.append({
                    "proposicao": f"{proposicao['tipo']} {proposicao['numero']}/{proposicao['ano']}",
                    "titulo": proposicao['titulo'],
                    "voto": tipo_voto,
                    "data": prop_data['votacao_principal']['data'],
                    "relevancia": proposicao['relevancia']
                })
        
        # Calcular estatísticas
        presenca = (total_votacoes / len(proposicoes_analisadas) * 100) if proposicoes_analisadas else 0
        
        return {
            "deputado": {
                "id": deputado_id,
                "nome": deputado_info['nome'],
                "nome_parlamentar": deputado_info['nome_parlamentar'],
                "partido": deputado_info['partido'],
                "uf": deputado_info['uf'],
                "situacao": deputado_info['situacao']
            },
            "historico_votacoes": historico_votacoes,
            "estatisticas": {
                "total_votacoes_analisadas": len(proposicoes_analisadas),
                "participacao": total_votacoes,
                "presenca_percentual": round(presenca, 1),
                "votos_favoraveis": votos_favor,
                "votos_contrarios": total_votacoes - votos_favor
            },
            "analisado_em": datetime.now().isoformat()
        }
    
    def salvar_dados(self, dados: Dict, arquivo: str):
        """Salva dados em arquivo JSON"""
        filepath = os.path.join(self.data_dir, arquivo)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {filepath}")

def main():
    print("DEMO - Sistema de Análise de Votações")
    print("=" * 60)
    print("(Usando dados simulados para demonstração)")
    
    demo = DemoAnaliseVotacoes()
    
    # Dados da proposição simulada
    print("\nANÁLISE DE PROPOSIÇÃO")
    print("-" * 40)
    
    resultado = demo.get_demo_data()
    proposicao = resultado['proposicao']
    votacao = resultado['votacao_principal']
    stats = resultado['estatisticas_votacao']
    
    print(f"Proposição: {proposicao['titulo']}")
    print(f"   {proposicao['tipo']} {proposicao['numero']}/{proposicao['ano']}")
    print(f"   Status: {proposicao['situacao']}")
    print(f"   ID Votação: {votacao['id']}")
    print(f"   Data: {votacao['data']}") 
    print(f"   Resultado: {'Aprovado' if votacao['aprovacao'] else 'Rejeitado'}")
    print(f"   Total de Votos: {votacao['total_votos']}")
    
    print(f"\nDistribuição de Votos:")
    for tipo, quantidade in stats['distribuicao_votos'].items():
        if quantidade > 0:
            porcentagem = (quantidade / stats['total_deputados']) * 100
            print(f"   {tipo}: {quantidade} ({porcentagem:.1f}%)")
    
    print(f"\nVotos por Partido:")
    for partido, votos_partido in stats['por_partido'].items():
        total_partido = votos_partido['total']
        sims = votos_partido['Sim']
        noes = votos_partido['Não']
        print(f"   {partido}: {sims} Sim, {noes} Não (total: {total_partido})")
    
    # Salvar dados da proposição
    demo.salvar_dados(resultado, "demo_proposicao_terceirizacao.json")
    
    # Análise de deputados específicos
    print(f"\nANÁLISE DE DEPUTADOS")
    print("-" * 40)
    
    deputados_analisar = [178864, 74847, 178976]  # André Figueiredo, Jair Bolsonaro, Benedita
    
    for deputado_id in deputados_analisar:
        print(f"\nAnalisando deputado ID: {deputado_id}")
        
        analise = demo.analisar_deputado_demo(deputado_id, [resultado])
        
        if 'erro' not in analise:
            dep_info = analise['deputado']
            stats_dep = analise['estatisticas']
            historico = analise['historico_votacoes']
            
            print(f"   Nome: {dep_info['nome_parlamentar']}")
            print(f"   Partido: {dep_info['partido']} - {dep_info['uf']}")
            print(f"   Participação: {stats_dep['participacao']}/{stats_dep['total_votacoes_analisadas']}")
            print(f"   Presença: {stats_dep['presenca_percentual']}%")
            
            if historico:
                voto_terceirizacao = historico[0]
                print(f"   Voto na Lei da Terceirização: {voto_terceirizacao['voto']}")
            
            # Salvar análise do deputado
            filename = f"demo_deputado_{dep_info['nome_parlamentar'].replace(' ', '_').lower()}.json"
            demo.salvar_dados(analise, filename)
        else:
            print(f"   ❌ {analise['erro']}")
    
    # Resumo final
    print(f"\nDemo concluída!")
    print("=" * 60)
    
    print(f"\nINSIGHTS DA ANÁLISE:")
    print(f"   • A Lei da Terceirização foi APROVADA")
    print(f"   • 5 deputados votaram SIM, 4 votaram NÃO, 1 se absteve")
    print(f"   • Partidos de direita (PSL, PRB) tenderam a votar SIM")
    print(f"   • Partidos de esquerda (PT, PSOL) tenderam a votar NÃO")
    print(f"   • PDT votou NÃO, alinhado com oposição")
    
    print(f"\nArquivos gerados:")
    try:
        arquivos = os.listdir(demo.data_dir)
        arquivos_demo = [f for f in arquivos if f.startswith('demo_')]
        
        for arquivo in arquivos_demo:
            caminho = os.path.join(demo.data_dir, arquivo)
            tamanho = os.path.getsize(caminho) / 1024  # KB
            print(f"   {arquivo} ({tamanho:.1f} KB)")
    except Exception as e:
        print(f"❌ Erro ao listar arquivos: {e}")
    
    print(f"\nSistema pronto para uso!")
    print(f"   • Use os endpoints da API para consultas em tempo real")
    print(f"   • Dados são cacheados para melhor performance")
    print(f"   • Análises completas são salvas automaticamente")

if __name__ == "__main__":
    main()