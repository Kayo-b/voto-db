from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
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
import sys

# Add database imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))
from database.import_service import import_deputados_from_json
from database.voting_import_service import import_voting_history_from_json
from database.connection import get_database
from sqlalchemy.orm import Session

load_dotenv()

app = FastAPI(
    title="VotoDB - Sistema de Análise de Votações",
    description="API para análise de votações da Câmara dos Deputados",
    version="2.0.0"
)

try:
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.ping() 
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

class AddProposicaoRequest(BaseModel):
    codigo: str  # Format: "PL 6787/2016"
    titulo: Optional[str] = None
    relevancia: str = "média"

class ValidateProposicaoRequest(BaseModel):
    codigo: str  # Format: "PL 6787/2016"

class AnaliseDeputadoRequest(BaseModel):
    deputado_id: int
    incluir_proposicoes: Optional[List[str]] = None

async def fetch_with_cache(endpoint, cache_key, ttl):
    # Redis cache commented out - using database-first approach instead
    # if r:
    #     try:
    #         cached = r.get(cache_key)
    #         if cached:
    #             return json.loads(cached)
    #     except:
    #         pass
    
    response = requests.get(f"{CAMARA_BASE_URL}{endpoint}")
    if response.status_code == 200:
        data = response.json()
        
        # Redis cache commented out - using database-first approach instead
        # if r:
        #     try:
        #         r.setex(cache_key, ttl, json.dumps(data))
        #     except:
        #         pass
        
        return data
    return None

@app.get("/deputados")
async def get_deputados(nome: str = None, db: Session = Depends(get_database)):
    """
    Get deputados - first from database, then from government API if needed
    """
    from database.model import Deputado, Partido
    
    try:
        # STEP 1: Try to get from database first (persistent storage)
        query = db.query(Deputado)
        if nome:
            query = query.filter(Deputado.nome.ilike(f"%{nome}%"))
        
        db_deputados = query.order_by(Deputado.nome).all()
        
        # If we found deputados in database, return them
        if db_deputados:
            print(f"DB Hit: Found {len(db_deputados)} deputados in database")
            
            # Convert to API format
            dados = []
            for dep in db_deputados:
                dados.append({
                    "id": dep.id,
                    "uri": f"https://dadosabertos.camara.leg.br/api/v2/deputados/{dep.id}",
                    "nome": dep.nome,
                    "siglaPartido": dep.partido.sigla if dep.partido else None,
                    "uriPartido": f"https://dadosabertos.camara.leg.br/api/v2/partidos/{dep.partido_id}" if dep.partido_id else None,
                    "siglaUf": dep.sigla_uf,
                    "idLegislatura": dep.legislatura_id,
                    "urlFoto": dep.url_foto,
                    "email": dep.email
                })
            
            return {
                "dados": dados,
                "links": [{"rel": "self", "href": f"/deputados{'?nome=' + nome if nome else ''}"}]
            }
        
        # STEP 2: Not found in database, fetch from government API
        print(f"DB Miss: Deputados not found in database, fetching from government API")
        
        endpoint = f"/deputados{'?nome=' + nome if nome else ''}&ordem=ASC&ordenarPor=nome"
        cache_key = f"deputados:{nome or 'all'}"
        
        # Fetch from government API
        data = await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])
        
        # Import to database if data exists
        if data and 'dados' in data and data['dados']:
            try:
                import_result = import_deputados_from_json(data)
                print(f"DB Import: {import_result['imported']} new, {import_result['updated']} updated deputados")
            except Exception as e:
                print(f"Database import error: {e}")
                # Continue even if DB import fails
        
        return data
    
    except Exception as e:
        print(f"Error in get_deputados: {e}")
        # Fallback to API if database fails
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
async def get_deputado_votacoes(deputado_id: int, db: Session = Depends(get_database)):
    """
    Get deputado voting history - first from database, then from government API if needed
    """
    from database.voting_data_service import (
        get_deputado_votacoes_from_database, 
        check_deputado_has_voting_data,
        import_voting_data_from_json
    )
    
    try:
        # STEP 1: Try to get from database first (persistent storage)
        if check_deputado_has_voting_data(deputado_id):
            print(f"DB Hit: Found voting data for deputado {deputado_id} in database")
            
            db_votacoes = get_deputado_votacoes_from_database(deputado_id, limit=10)
            
            return {
                "success": True,
                "dados": db_votacoes,
                "total": len(db_votacoes),
                "cached": False,  # From database, not cache
                "links": []
            }
        
        # STEP 2: Not found in database, fetch from government API and import
        print(f"DB Miss: Voting data for deputado {deputado_id} not found, fetching from government API")
        
        # Redis cache check (commented out as requested)
        # cache_key = f"deputado:{deputado_id}:votacoes_relevantes"
        # if r:
        #     try:
        #         cached = r.get(cache_key)
        #         if cached:
        #             cached_data = json.loads(cached)
        #             if cached_data:
        #                 return {"success": True, "dados": cached_data, "cached": True, "total": len(cached_data), "links": []}
        #     except:
        #         pass
        
        # Get proposições from database instead of hardcoded JSON
        from database.proposicao_service import get_all_proposicoes_relevantes
        proposicoes_db = get_all_proposicoes_relevantes()
        
        # Convert to format expected by the rest of the code
        proposicoes_relevantes = []
        for prop in proposicoes_db[:5]:  # Limit to 5 for now
            proposicoes_relevantes.append({
                "id_proposicao": prop['id'],
                "tipo": f"{prop['tipo']} {prop['numero']}/{prop['ano']}",
                "numero": f"{prop['numero']}/{prop['ano']}",
                "titulo": prop['titulo']
            })
        
        votacoes_deputado = []
        import_stats = {
            'total_imported': 0,
            'total_errors': 0
        }
        
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
                        
                        # Import to database
                        try:
                            proposicao_data = {
                                'id': int(id_proposicao),
                                'siglaTipo': prop.get("tipo", "").split()[0] if prop.get("tipo") else "",
                                'numero': prop.get("numero", "").split("/")[0] if prop.get("numero") else "",
                                'ano': int(prop.get("numero", "").split("/")[1]) if "/" in prop.get("numero", "") else datetime.now().year,
                                'ementa': prop.get("titulo", ""),
                                'uri': f"https://dadosabertos.camara.leg.br/api/v2/proposicoes/{id_proposicao}"
                            }
                            
                            import_result = import_voting_data_from_json(
                                proposicao_data, 
                                votacao_principal, 
                                votos
                            )
                            import_stats['total_imported'] += 1
                            
                        except Exception as import_error:
                            print(f"Import error for proposição {id_proposicao}: {import_error}")
                            import_stats['total_errors'] += 1
                        
                        # Build response data (regardless of import success/failure)
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
                    import_stats['total_errors'] += 1
                    continue
                            
            except Exception as e:
                print(f"Erro ao processar proposição {prop.get('numero', 'N/A')}: {e}")
                import_stats['total_errors'] += 1
                continue
        
        # Fallback to demo data if no API data found
        if not votacoes_deputado:
            print(f"No API data found for deputy {deputado_id}, using demo data")
            votacoes_deputado = get_demo_votacoes(deputado_id)
        
        votacoes_deputado.sort(key=lambda x: x.get('data', ''), reverse=True)
        
        print(f"DB Import Stats: {import_stats['total_imported']} imported, {import_stats['total_errors']} errors")
        
        # Redis cache save (commented out as requested)
        # if votacoes_deputado and r:
        #     try:
        #         r.setex(cache_key, CACHE_TTL["votacoes"], json.dumps(votacoes_deputado))
        #     except:
        #         pass
        
        return {
            "success": True,
            "dados": votacoes_deputado,
            "total": len(votacoes_deputado),
            "cached": False,
            "links": []
        }
    
    except Exception as e:
        print(f"Error in get_deputado_votacoes: {e}")
        return {
            "success": False,
            "message": f"Erro ao buscar votações: {str(e)}",
            "dados": [],
            "total": 0,
            "cached": False,
            "links": []
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

# OLD ENDPOINT - Replaced by database-based version below (line ~900)
# Keeping for backward compatibility but should be removed later
@app.get("/proposicoes/relevantes/legacy")
async def get_proposicoes_relevantes_legacy():
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
async def analisar_perfil_deputado(deputado_id: int, incluir_todas: bool = True, limite_proposicoes: int = None, usar_cache: bool = True, db: Session = Depends(get_database)):
    """
    Analyze deputy profile - first from database, then from government API if needed
    """
    from database.model import EstatisticaDeputado
    
    try:
        # STEP 1: Try to get analysis from database first (persistent storage)
        estatisticas = db.query(EstatisticaDeputado).filter(
            EstatisticaDeputado.deputado_id == deputado_id
        ).first()
        
        if estatisticas and estatisticas.total_votacoes_analisadas > 0:
            print(f"DB Hit: Found analysis for deputado {deputado_id} in database")
            
            # Get deputado info
            from database.model import Deputado, Voto, Votacao, Proposicao
            deputado = db.query(Deputado).filter(Deputado.id == deputado_id).first()
            
            # Get voting history from database
            votos = db.query(Voto).join(Votacao).join(Proposicao).filter(
                Voto.deputado_id == deputado_id
            ).order_by(Votacao.data_votacao.desc()).limit(10).all()
            
            # Build historico_votacoes
            historico_votacoes = []
            for voto in votos:
                votacao = voto.votacao
                proposicao = votacao.proposicao
                
                historico_votacoes.append({
                    "proposicao": proposicao.codigo or f"{proposicao.tipo} {proposicao.numero}/{proposicao.ano}",
                    "titulo": proposicao.titulo or proposicao.ementa or "",
                    "voto": voto.voto,
                    "data": votacao.data_votacao.isoformat() if votacao.data_votacao else "",
                    "relevancia": proposicao.relevancia or "media"
                })
            
            # Convert database statistics to expected frontend format
            analysis_data = {
                "deputado": {
                    "id": deputado_id,
                    "nome": deputado.nome if deputado else f"Deputado {deputado_id}",
                    "nome_parlamentar": deputado.nome_parlamentar if deputado and deputado.nome_parlamentar else (deputado.nome if deputado else f"Deputado {deputado_id}"),
                    "partido": deputado.partido.sigla if deputado and deputado.partido else "N/A",
                    "uf": deputado.sigla_uf if deputado else "N/A",
                    "situacao": deputado.situacao if deputado else "N/A"
                },
                "historico_votacoes": historico_votacoes,
                "estatisticas": {
                    "total_votacoes_analisadas": estatisticas.total_votacoes_analisadas,
                    "participacao": estatisticas.participacao,
                    "presenca_percentual": estatisticas.presenca_percentual,
                    "votos_favoraveis": estatisticas.votos_favoraveis,
                    "votos_contrarios": estatisticas.votos_contrarios
                }
            }
            
            return {
                "success": True,
                "data": analysis_data,
                "message": "Análise carregada do banco de dados"
            }
        
        # STEP 2: Not found in database, proceed with API analysis
        print(f"DB Miss: Analysis for deputado {deputado_id} not found, generating from government API")
        
        # Verificar cache Redis (commented out as requested)
        # cache_key = f"analise_completa:{deputado_id}:{limite_proposicoes or 'todas'}"
        # 
        # if usar_cache and r:
        #     try:
        #         cached = r.get(cache_key)
        #         if cached:
        #             print(f"Análise encontrada no cache para deputado {deputado_id}")
        #             return {
        #                 "success": True,
        #                 "data": json.loads(cached),
        #                 "cached": True,
        #                 "message": "Análise carregada do cache"
        #             }
        #     except:
        #         pass
        
        proposicoes_analisadas = []
        
        if incluir_todas:
            # Get proposições from database instead of hardcoded JSON
            from database.proposicao_service import get_all_proposicoes_relevantes
            proposicoes_db = get_all_proposicoes_relevantes()
            
            # Convert to format expected by analisador
            proposicoes_relevantes = []
            for prop in proposicoes_db:
                proposicoes_relevantes.append({
                    "id_proposicao": prop['id'],
                    "tipo": f"{prop['tipo']} {prop['numero']}/{prop['ano']}",
                    "numero": f"{prop['numero']}/{prop['ano']}",
                    "titulo": prop['titulo']
                })
            
            if limite_proposicoes:
                proposicoes_relevantes = proposicoes_relevantes[:limite_proposicoes]
            
            print(f"Processando {len(proposicoes_relevantes)} proposições para o deputado {deputado_id}")
            
            for i, prop in enumerate(proposicoes_relevantes, 1):
                print(f"\n[{i}/{len(proposicoes_relevantes)}] Processando proposição: {prop.get('tipo')} {prop.get('numero')} - {prop.get('titulo')}")
                
                try:
                    numero_completo = prop.get("numero", "")
                    if "/" in numero_completo:
                        numero_str, ano_str = numero_completo.split("/")
                        numero = int(numero_str)
                        ano = int(ano_str)
                    else:
                        print(f"ERRO: Formato de número inválido: {numero_completo}")
                        continue
                    
                    print(f"Buscando votos do deputado {deputado_id} para: {prop['tipo']} {numero}/{ano}")
                    resultado = analisador.processar_proposicao_completa(
                        prop["tipo"],
                        numero,
                        ano,
                        prop["titulo"],
                        prop.get("relevancia", "média")
                    )
                    print(f"")
                    if resultado:
                        proposicoes_analisadas.append(resultado)
                        print(f"SUCESSO: Proposição processada com sucesso: ID {resultado['proposicao']['id']}")
                    else:
                        print(f"AVISO: Falha ao processar proposição {prop['tipo']} {numero}/{ano} - dados não encontrados")
                        
                except Exception as e:
                    print(f"ERRO: Erro ao processar proposição {prop.get('tipo', 'N/A')} {prop.get('numero', 'N/A')}: {str(e)}")
                    continue
            
            print(f"\nResumo do processamento:")
            print(f"  - Total de proposições tentadas: {len(proposicoes_relevantes)}")
            print(f"  - Proposições processadas com sucesso: {len(proposicoes_analisadas)}")
            print(f"  - Taxa de sucesso: {len(proposicoes_analisadas)/len(proposicoes_relevantes)*100:.1f}%")
        
        if not proposicoes_analisadas:
            return {
                "success": False,
                "message": "Nenhuma proposição analisada disponível para este deputado. Verifique se o deputado possui votos registrados nas proposições."
            }
        
        print(f"Analisando perfil do deputado com {len(proposicoes_analisadas)} proposições processadas...")
        analise = analisador.analisar_deputado(deputado_id, proposicoes_analisadas)
        
        resultado_final = {
            "success": True,
            "data": analise,
            "proposicoes_analisadas": len(proposicoes_analisadas),
            "cached": False,
            "processamento": {
                "total_proposicoes_tentadas": len(proposicoes_relevantes) if incluir_todas else 0,
                "proposicoes_com_sucesso": len(proposicoes_analisadas),
                "taxa_sucesso": f"{len(proposicoes_analisadas)/len(proposicoes_relevantes)*100:.1f}%" if incluir_todas and proposicoes_relevantes else "N/A"
            }
        }
        
        # Import voting history to database
        try:
            import_result = import_voting_history_from_json(resultado_final)
            print(f"DB Import: {import_result.get('imported_votes', 0)} votes imported for deputado {deputado_id}")
        except Exception as e:
            print(f"Database voting history import error: {e}")
            # Continue even if DB import fails
        
        # Redis cache save (commented out as requested)
        # cache_key = f"analise_completa:{deputado_id}:{limite_proposicoes or 'todas'}"
        # if usar_cache and r and analise:
        #     try:
        #         r.setex(cache_key, CACHE_TTL["deputados"], json.dumps(resultado_final))
        #         print(f"Análise salva no cache para deputado {deputado_id}")
        #     except:
        #         pass
        
        return resultado_final
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

@app.get("/deputados/{deputado_id}/analise/completa")
async def analisar_perfil_deputado_completa(
    deputado_id: int,
    forcar_reprocessamento: bool = False,
    batch_size: int = 5,  # Processar em lotes para evitar timeout
    db: Session = Depends(get_database)
):
    """
    Análise completa do deputado processando TODAS as proposições em lotes
    """
    try:
        cache_key = f"analise_total:{deputado_id}"
        
        if not forcar_reprocessamento and r:
            try:
                cached = r.get(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": json.loads(cached),
                        "cached": True,
                        "message": "Análise completa carregada do cache"
                    }
            except:
                pass
        
        # Get proposições from database instead of hardcoded JSON
        from database.proposicao_service import get_all_proposicoes_relevantes
        proposicoes_db = get_all_proposicoes_relevantes()
        
        # Convert to format expected by analisador
        proposicoes_relevantes = []
        for prop in proposicoes_db:
            proposicoes_relevantes.append({
                "id_proposicao": prop['id'],
                "tipo": f"{prop['tipo']} {prop['numero']}/{prop['ano']}",
                "numero": f"{prop['numero']}/{prop['ano']}",
                "titulo": prop['titulo']
            })
        
        print(f"Iniciando análise COMPLETA para deputado {deputado_id}")
        print(f"Total de proposições a processar: {len(proposicoes_relevantes)}")
        
        proposicoes_analisadas = []
        total_processadas = 0
        total_com_erro = 0
        
        for batch_start in range(0, len(proposicoes_relevantes), batch_size):
            batch_end = min(batch_start + batch_size, len(proposicoes_relevantes))
            batch = proposicoes_relevantes[batch_start:batch_end]
            
            print(f"\nProcessando lote {batch_start//batch_size + 1}/{(len(proposicoes_relevantes)-1)//batch_size + 1}")
            print(f"   Proposições {batch_start + 1} a {batch_end} de {len(proposicoes_relevantes)}")
            
            for i, prop in enumerate(batch):
                prop_index = batch_start + i + 1
                try:
                    numero_completo = prop.get("numero", "")
                    if "/" in numero_completo:
                        numero_str, ano_str = numero_completo.split("/")
                        numero = int(numero_str)
                        ano = int(ano_str)
                    else:
                        print(f"   ERRO [{prop_index}] Formato inválido: {numero_completo}")
                        total_com_erro += 1
                        continue
                    
                    print(f"   INFO [{prop_index}] {prop['tipo']} {numero}/{ano}")
                    resultado = analisador.processar_proposicao_completa(
                        prop["tipo"], numero, ano, prop["titulo"], prop.get("relevancia", "média")
                    )
                    
                    if resultado:
                        proposicoes_analisadas.append(resultado)
                        print(f"   SUCESSO [{prop_index}] Processado")
                    else:
                        print(f"   AVISO [{prop_index}] Sem dados")
                        total_com_erro += 1
                    
                    total_processadas += 1
                    
                except Exception as e:
                    print(f"   ERRO [{prop_index}] Erro: {str(e)}")
                    total_com_erro += 1
                    total_processadas += 1
        
        if not proposicoes_analisadas:
            return {
                "success": False,
                "message": f"Nenhuma proposição processada com sucesso para o deputado {deputado_id}",
                "estatisticas": {
                    "total_tentativas": total_processadas,
                    "sucessos": 0,
                    "erros": total_com_erro
                }
            }
        
        analise = analisador.analisar_deputado(deputado_id, proposicoes_analisadas)
        
        resultado_final = {
            "deputado_id": deputado_id,
            "analise": analise,
            "estatisticas_processamento": {
                "total_proposicoes_disponiveis": len(proposicoes_relevantes),
                "total_processadas": total_processadas,
                "sucessos": len(proposicoes_analisadas),
                "erros": total_com_erro,
                "taxa_sucesso": f"{len(proposicoes_analisadas)/total_processadas*100:.1f}%" if total_processadas > 0 else "0%"
            },
            "processado_em": datetime.now().isoformat()
        }
        
        # Import voting history to database
        try:
            # Transform result format to match the expected voting history format
            voting_response_format = {
                "success": True,
                "data": analise,
                "proposicoes_analisadas": len(proposicoes_analisadas),
                "processamento": resultado_final["estatisticas_processamento"]
            }
            import_result = import_voting_history_from_json(voting_response_format)
            print(f"DB Import (Complete): {import_result.get('imported_votes', 0)} votes imported for deputado {deputado_id}")
        except Exception as e:
            print(f"Database voting history import error (complete): {e}")
            # Continue even if DB import fails

        if r:
            try:
                r.setex(cache_key, 604800, json.dumps(resultado_final))
            except:
                pass
        
        return {
            "success": True,
            "data": resultado_final,
            "cached": False
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na análise completa: {str(e)}")

@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache_stats = analisador.get_cache_stats()
        return {
            "success": True,
            "data": cache_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas do cache: {str(e)}")

@app.post("/cache/clear")
async def clear_cache(cache_type: str = "all"):
    """Clear cache files"""
    try:
        analisador.clear_cache(cache_type)
        new_stats = analisador.get_cache_stats()
        return {
            "success": True,
            "message": f"Cache '{cache_type}' limpo com sucesso",
            "data": new_stats
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@app.get("/estatisticas/geral")
async def get_estatisticas_gerais():
    try:
        # Get proposições from database instead of hardcoded JSON
        from database.proposicao_service import get_all_proposicoes_relevantes
        proposicoes_db = get_all_proposicoes_relevantes()
        
        # Convert to expected format
        dados_proposicoes = {
            "votacoes_historicas": [{
                "id_proposicao": prop['id'],
                "tipo": f"{prop['tipo']} {prop['numero']}/{prop['ano']}",
                "numero": f"{prop['numero']}/{prop['ano']}",
                "titulo": prop['titulo']
            } for prop in proposicoes_db]
        }
        
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

# ============================================================
# PROPOSIÇÕES RELEVANTES - CRUD ENDPOINTS
# ============================================================

@app.get("/proposicoes/relevantes")
async def get_proposicoes_relevantes(relevancia: Optional[str] = None):
    """
    Get all relevant proposições from database.
    Replaces hardcoded JSON file system.
    """
    from database.proposicao_service import get_all_proposicoes_relevantes
    
    try:
        proposicoes = get_all_proposicoes_relevantes(relevancia)
        
        # Format to match frontend expectation
        votacoes_historicas = []
        for prop in proposicoes:
            # Generate impacto text
            ementa = prop.get("ementa", "")
            impacto = ementa if ementa else f"Proposição de relevância {prop.get('relevancia', 'média')} para análise de votações dos deputados"
            
            votacoes_historicas.append({
                "id": prop.get("id"),
                "tipo": prop.get("tipo", ""),
                "numero": prop.get("numero", ""),
                "titulo": prop.get("titulo", ""),
                "relevancia": prop.get("relevancia", ""),
                "impacto": impacto,
                "status": None,  # Can be populated later if needed
                "data_aprovacao": None  # Can be populated later if needed
            })
        
        return {
            "success": True,
            "data": {
                "votacoes_historicas": votacoes_historicas,
                "metadata": {
                    "total_proposicoes": len(votacoes_historicas),
                    "periodo": "Sistema"
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar proposições: {str(e)}")

@app.post("/proposicoes/relevantes")
async def add_proposicao_relevante(request: AddProposicaoRequest):
    """
    Add a new relevant proposição after validating with government API.
    Validates that the proposição exists and has nominal voting sessions.
    """
    from database.proposicao_service import add_proposicao
    
    try:
        result = add_proposicao(
            codigo=request.codigo,
            titulo=request.titulo,
            relevancia=request.relevancia
        )
        
        if result['success']:
            return {
                "success": True,
                "message": f"Proposição {request.codigo} adicionada com sucesso",
                "data": result['data']
            }
        else:
            raise HTTPException(status_code=400, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao adicionar proposição: {str(e)}")

@app.post("/proposicoes/relevantes/validate")
async def validate_proposicao(request: ValidateProposicaoRequest):
    """
    Validate a proposição without adding it to database.
    Checks if it exists in government API and has nominal voting.
    """
    from database.proposicao_service import validate_proposicao_exists
    
    try:
        validation = validate_proposicao_exists(request.codigo)
        
        if validation['valid']:
            return {
                "success": True,
                "message": "Proposição válida e possui votações nominais",
                "data": {
                    "codigo": validation['codigo'],
                    "proposicao_id": validation['proposicao_id'],
                    "tipo": validation['tipo'],
                    "ementa": validation['ementa'][:200] + "..." if len(validation.get('ementa', '')) > 200 else validation.get('ementa', ''),
                    "total_votacoes_nominais": validation['total_votacoes_nominais'],
                    "nominal_votacoes": validation['nominal_votacoes']
                }
            }
        else:
            return {
                "success": False,
                "error": validation['error']
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao validar proposição: {str(e)}")

@app.delete("/proposicoes/relevantes/{proposicao_id}")
async def delete_proposicao_relevante(proposicao_id: int):
    """
    Remove a proposição from the relevant list.
    """
    from database.proposicao_service import remove_proposicao
    
    try:
        result = remove_proposicao(proposicao_id)
        
        if result['success']:
            return {
                "success": True,
                "message": result['message']
            }
        else:
            raise HTTPException(status_code=404, detail=result['error'])
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao remover proposição: {str(e)}")

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
    uvicorn.run(app, host="0.0.0.0", port=8001)