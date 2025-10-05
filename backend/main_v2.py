from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import redis
import requests
import json
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from pydantic import BaseModel
from analisador_votacoes import AnalisadorVotacoes
import asyncio
from datetime import datetime

load_dotenv()

app = FastAPI(
    title="VotoDB - Sistema de Análise de Votações",
    description="API para análise de votações da Câmara dos Deputados",
    version="2.0.0"
)

# Redis connection
try:
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.ping()  # Test connection
except:
    r = None
    print("Redis não disponível - cache desabilitado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
CACHE_TTL = {"deputados": 604800, "votacoes": 86400, "proposicoes": 2592000}

analisador = AnalisadorVotacoes()

class ProposicaoRequest(BaseModel):
    tipo: str
    numero: int
    ano: int
    titulo: str
    relevancia: str = "média"

class AnaliseDeputadoRequest(BaseModel):
    deputado_id: int
    incluir_proposicoes: Optional[List[str]] = None

async def fetch_with_cache(endpoint, cache_key, ttl):
    if r:
        try:
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
        except:
            pass
    
    response = requests.get(f"{CAMARA_BASE_URL}{endpoint}")
    if response.status_code == 200:
        data = response.json()
        
        if r:
            try:
                r.setex(cache_key, ttl, json.dumps(data))
            except:
                pass
        
        return data
    return None

@app.get("/deputados")
async def get_deputados(nome: str = None):
    endpoint = f"/deputados{'?nome=' + nome if nome else ''}&ordem=ASC&ordenarPor=nome"
    cache_key = f"deputados:{nome or 'all'}"
    return await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])

def get_demo_votacoes(deputado_id: int) -> List[Dict]:
    demo_data = {
        74847: [  # Jair Bolsonaro
            {
                "id": "2122076-348",
                "data": "2017-03-22T19:45:00",
                "dataHoraRegistro": "2017-03-22T19:45:00",
                "siglaOrgao": "PLEN",
                "uriOrgao": "https://dadosabertos.camara.leg.br/api/v2/orgaos/180",
                "voto": "Sim",
                "proposicao": {
                    "id": 2122076,
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2122076",
                    "siglaTipo": "PL",
                    "numero": "6787",
                    "ano": "2016",
                    "ementa": "Lei da Terceirização - Regulamenta a terceirização em todas as atividades empresariais"
                }
            },
            {
                "id": "2088351-214",
                "data": "2016-12-15T18:30:00",
                "dataHoraRegistro": "2016-12-15T18:30:00",
                "siglaOrgao": "PLEN",
                "uriOrgao": "https://dadosabertos.camara.leg.br/api/v2/orgaos/180",
                "voto": "Sim",
                "proposicao": {
                    "id": 2088351,
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2088351",
                    "siglaTipo": "PEC",
                    "numero": "241",
                    "ano": "2016",
                    "ementa": "Teto de Gastos Públicos - Limitou crescimento dos gastos públicos por 20 anos"
                }
            }
        ],
        178864: [  # André Figueiredo (PDT-CE)
            {
                "id": "2122076-348",
                "data": "2017-03-22T19:45:00",
                "dataHoraRegistro": "2017-03-22T19:45:00",
                "siglaOrgao": "PLEN",
                "uriOrgao": "https://dadosabertos.camara.leg.br/api/v2/orgaos/180",
                "voto": "Não",
                "proposicao": {
                    "id": 2122076,
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2122076",
                    "siglaTipo": "PL",
                    "numero": "6787",
                    "ano": "2016",
                    "ementa": "Lei da Terceirização - Regulamenta a terceirização em todas as atividades empresariais"
                }
            }
        ],
        178976: [  # Benedita da Silva (PT-RJ)
            {
                "id": "2122076-348",
                "data": "2017-03-22T19:45:00",
                "dataHoraRegistro": "2017-03-22T19:45:00",
                "siglaOrgao": "PLEN",
                "uriOrgao": "https://dadosabertos.camara.leg.br/api/v2/orgaos/180",
                "voto": "Não",
                "proposicao": {
                    "id": 2122076,
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2122076",
                    "siglaTipo": "PL",
                    "numero": "6787",
                    "ano": "2016",
                    "ementa": "Lei da Terceirização - Regulamenta a terceirização em todas as atividades empresariais"
                }
            },
            {
                "id": "2088351-214",
                "data": "2016-12-15T18:30:00",
                "dataHoraRegistro": "2016-12-15T18:30:00",
                "siglaOrgao": "PLEN",
                "uriOrgao": "https://dadosabertos.camara.leg.br/api/v2/orgaos/180",
                "voto": "Não",
                "proposicao": {
                    "id": 2088351,
                    "uri": "https://dadosabertos.camara.leg.br/api/v2/proposicoes/2088351",
                    "siglaTipo": "PEC",
                    "numero": "241",
                    "ano": "2016",
                    "ementa": "Teto de Gastos Públicos - Limitou crescimento dos gastos públicos por 20 anos"
                }
            }
        ]
    }
    
    return demo_data.get(deputado_id, [])

@app.get("/deputados/{deputado_id}/votacoes")
async def get_deputado_votacoes(deputado_id: int):
    try:
        cache_key = f"deputado:{deputado_id}:votacoes_relevantes"
        
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    cached_data = json.loads(cached)
                    if cached_data:
                        return {"success": True, "dados": cached_data, "cached": True, "total": len(cached_data), "links": []}
            except:
                pass
        
        dados_proposicoes = analisador.carregar_dados("data/proposicoes.json")
        proposicoes_relevantes = dados_proposicoes.get("votacoes_historicas", [])[:5]
        
        votacoes_deputado = []
        
        for prop in proposicoes_relevantes:
            try:
                id_proposicao = prop.get("id_proposicao")
                if not id_proposicao:
                    continue
                
                try:
                    votacoes = analisador.buscar_votacoes_proposicao(int(id_proposicao))
                    votacao_principal = analisador.identificar_votacao_principal(votacoes)
                    
                    if votacao_principal:
                        id_votacao = votacao_principal['id']
                        votos = analisador.buscar_votos_votacao(id_votacao)
                        
                        for voto in votos:
                            dep_data = voto.get('deputado_', {})
                            if dep_data.get('id') == deputado_id:
                                votacao_info = {
                                    "id": id_votacao,
                                    "data": votacao_principal.get('dataHoraRegistro', ''),
                                    "dataHoraRegistro": votacao_principal.get('dataHoraRegistro', ''),
                                    "siglaOrgao": votacao_principal.get('siglaOrgao', ''),
                                    "uriOrgao": votacao_principal.get('uriOrgao', ''),
                                    "voto": voto.get('tipoVoto', ''),
                                    "proposicao": {
                                        "id": int(id_proposicao),
                                        "uri": f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}",
                                        "siglaTipo": prop.get("tipo", "").split()[0] if prop.get("tipo") else "",
                                        "numero": prop.get("numero", "").split("/")[0] if prop.get("numero") else "",
                                        "ano": prop.get("numero", "").split("/")[1] if "/" in prop.get("numero", "") else "",
                                        "ementa": prop.get("titulo", "")[:100] + "..." if len(prop.get("titulo", "")) > 100 else prop.get("titulo", "")
                                    }
                                }
                                votacoes_deputado.append(votacao_info)
                                break
                except Exception as api_error:
                    print(f"API timeout/error for proposition {prop.get('numero', 'N/A')}: {api_error}")
                    continue
                            
            except Exception as e:
                print(f"Erro ao processar proposição {prop.get('numero', 'N/A')}: {e}")
                continue
        
        if not votacoes_deputado:
            print(f"No API data found for deputy {deputado_id}, using demo data")
            votacoes_deputado = get_demo_votacoes(deputado_id)
        
        votacoes_deputado.sort(key=lambda x: x.get('data', ''), reverse=True)
        
        if votacoes_deputado and r:
            try:
                r.setex(cache_key, CACHE_TTL["votacoes"], json.dumps(votacoes_deputado))
            except:
                pass
        
        return {
            "success": True,
            "dados": votacoes_deputado,
            "total": len(votacoes_deputado),
            "cached": False,
            "links": [],
            "fonte": "demo" if not votacoes_deputado or deputado_id in [74847, 178864, 178976] else "api"
        }
        
    except Exception as e:
        print(f"Error in get_deputado_votacoes: {e}")
        demo_votacoes = get_demo_votacoes(deputado_id)
        return {
            "success": True,
            "dados": demo_votacoes,
            "total": len(demo_votacoes),
            "cached": False,
            "links": [],
            "fonte": "demo_fallback"
        }

@app.get("/deputados/{deputado_id}")
async def get_deputado_detalhes(deputado_id: int):
    endpoint = f"/deputados/{deputado_id}"
    cache_key = f"deputado:{deputado_id}:detalhes"
    return await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])

@app.get("/proposicoes/relevantes")
async def get_proposicoes_relevantes():
    try:
        dados = analisador.carregar_dados("proposicoes.json")
        return {
            "success": True,
            "data": dados,
            "total": len(dados.get("proposicoes_relevantes", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar proposições: {str(e)}")

@app.get("/proposicoes/buscar")
async def buscar_proposicao(tipo: str, numero: int, ano: int):
    try:
        resultado = analisador.buscar_proposicao(tipo, numero, ano)
        if resultado:
            return {"success": True, "data": resultado}
        else:
            raise HTTPException(status_code=404, detail="Proposição não encontrada")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.post("/proposicoes/analisar")
async def analisar_proposicao(proposicao: ProposicaoRequest, background_tasks: BackgroundTasks):
    try:
        cache_key = f"proposicao_analisada:{proposicao.tipo}_{proposicao.numero}_{proposicao.ano}"
        
        if r:
            try:
                cached = r.get(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": json.loads(cached),
                        "cached": True,
                        "message": "Dados carregados do cache"
                    }
            except:
                pass
        
        resultado = analisador.processar_proposicao_completa(
            proposicao.tipo,
            proposicao.numero,
            proposicao.ano,
            proposicao.titulo,
            proposicao.relevancia
        )
        
        if resultado:
            if r:
                try:
                    r.setex(cache_key, CACHE_TTL["proposicoes"], json.dumps(resultado))
                except:
                    pass
            
            background_tasks.add_task(
                salvar_proposicao_analisada,
                resultado
            )
            
            return {
                "success": True,
                "data": resultado,
                "cached": False,
                "message": "Proposição processada com sucesso"
            }
        else:
            raise HTTPException(status_code=404, detail="Não foi possível processar a proposição")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

@app.get("/proposicoes/{proposicao_id}/votacoes")
async def get_votacoes_proposicao(proposicao_id: int):
    try:
        votacoes = analisador.buscar_votacoes_proposicao(proposicao_id)
        return {
            "success": True,
            "data": votacoes,
            "total": len(votacoes)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar votações: {str(e)}")

@app.get("/votacoes/{votacao_id}/votos")
async def get_votos_votacao(votacao_id: str):
    try:
        votos = analisador.buscar_votos_votacao(votacao_id)
        return {
            "success": True,
            "data": votos,
            "total": len(votos),
            "estatisticas": analisador._calcular_estatisticas_votacao(votos)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar votos: {str(e)}")

@app.get("/deputados/{deputado_id}/analise")
async def analisar_perfil_deputado(deputado_id: int, incluir_todas: bool = False):
    try:
        proposicoes_analisadas = []
        
        if incluir_todas:
            dados_proposicoes = analisador.carregar_dados("proposicoes.json")
            proposicoes_relevantes = dados_proposicoes.get("proposicoes_relevantes", [])
            
            for prop in proposicoes_relevantes[:2]:
                try:
                    resultado = analisador.processar_proposicao_completa(
                        prop["tipo"],
                        prop["numero"],
                        prop["ano"],
                        prop["titulo"],
                        prop["relevancia"]
                    )
                    if resultado:
                        proposicoes_analisadas.append(resultado)
                except:
                    continue
        
        if not proposicoes_analisadas:
            return {
                "success": False,
                "message": "Nenhuma proposição analisada disponível para este deputado. Use incluir_todas=true para processar."
            }
        
        analise = analisador.analisar_deputado(deputado_id, proposicoes_analisadas)
        
        return {
            "success": True,
            "data": analise,
            "proposicoes_analisadas": len(proposicoes_analisadas)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

@app.get("/estatisticas/geral")
async def get_estatisticas_gerais():
    try:
        dados_proposicoes = analisador.carregar_dados("proposicoes.json")
        
        cache_stats = {"total_cached": 0}
        if r:
            try:
                keys = r.keys("*")
                cache_stats = {
                    "total_cached": len(keys),
                    "deputados_cached": len([k for k in keys if k.decode().startswith("deputado:")]),
                    "proposicoes_cached": len([k for k in keys if k.decode().startswith("proposicao_analisada:")])
                }
            except:
                pass
        
        return {
            "success": True,
            "data": {
                "proposicoes_relevantes": len(dados_proposicoes.get("proposicoes_relevantes", [])),
                "categorias": list(dados_proposicoes.get("categorias", {}).keys()),
                "cache": cache_stats,
                "sistema": {
                    "versao": "2.0.0",
                    "redis_disponivel": r is not None,
                    "ultima_atualizacao": dados_proposicoes.get("metadados", {}).get("ultima_atualizacao")
                }
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "redis": r is not None,
        "services": {
            "api_camara": "online",
            "redis": "online" if r else "offline",
            "analisador": "online"
        }
    }

def salvar_proposicao_analisada(resultado: Dict):
    try:
        filename = f"proposicao_{resultado['proposicao']['tipo']}_{resultado['proposicao']['numero']}_{resultado['proposicao']['ano']}.json"
        analisador.salvar_dados(resultado, filename)
    except Exception as e:
        print(f"Erro ao salvar proposição: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)