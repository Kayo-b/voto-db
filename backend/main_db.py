"""
Enhanced FastAPI application with PostgreSQL database integration
Maintains backward compatibility while prioritizing database operations
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
import redis
import requests
import json
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

# Database imports
try:
    from database import (
        init_database, test_connection, get_db_session, 
        Deputado, Proposicao, Votacao, Voto, AnaliseDeputado
    )
    from database.service import VotoDBService
    from analisador_votacoes_db import AnalisadorVotacoesDB
    DATABASE_AVAILABLE = True
except ImportError:
    from analisador_votacoes import AnalisadorVotacoes
    DATABASE_AVAILABLE = False
    print("Database not available, using legacy file cache")

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="VotoDB - Sistema de Análise de Votações com PostgreSQL",
    description="API para análise de votações da Câmara dos Deputados com banco de dados PostgreSQL",
    version="3.0.0"
)

# Redis setup (still used for API response caching)
try:
    r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))
    r.ping() 
except:
    r = None
    logger.warning("Redis não disponível - cache de API desabilitado")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
CACHE_TTL = {"deputados": 604800, "votacoes": 86400, "proposicoes": 2592000}

# Initialize services
if DATABASE_AVAILABLE:
    analisador = AnalisadorVotacoesDB(use_database=True)
    db_service = VotoDBService(api_client=analisador)
else:
    analisador = AnalisadorVotacoes()
    db_service = None

class ProposicaoRequest(BaseModel):
    tipo: str
    numero: int
    ano: int
    titulo: str
    relevancia: str = "média"

class AnaliseDeputadoRequest(BaseModel):
    deputado_id: int
    incluir_proposicoes: Optional[List[str]] = None

# Dependency for database session
def get_database_service():
    if not DATABASE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    return db_service

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    if DATABASE_AVAILABLE:
        try:
            if test_connection():
                logger.info("Database connection successful")
                init_database()
                logger.info("Database initialized")
            else:
                logger.error("Database connection failed")
        except Exception as e:
            logger.error(f"Database startup error: {e}")
    else:
        logger.info("Starting without database integration")

# BACKGROUND TASKS FOR API UPDATES

async def update_deputados_from_api(nome: str = None, partido: str = None, uf: str = None):
    """Background task to update deputados from API"""
    try:
        if not DATABASE_AVAILABLE:
            return
            
        logger.info(f"Background update: Fetching deputados from API (nome={nome}, partido={partido}, uf={uf})")
        
        # Build API endpoint
        params = []
        if nome:
            params.append(f"nome={nome}")
        if partido:
            params.append(f"siglaPartido={partido}")
        if uf:
            params.append(f"siglaUf={uf}")
        
        endpoint = f"/deputados"
        if params:
            endpoint += "?" + "&".join(params)
        
        # Fetch from API
        api_data = analisador._fazer_requisicao(endpoint)
        if api_data and api_data.get('dados'):
            deputados_api = api_data['dados']
            
            # Update database with fresh data
            with get_db_session() as session:
                updated_count = 0
                for deputado_data in deputados_api:
                    try:
                        deputado = db_service._upsert_deputado(session, deputado_data)
                        session.commit()  # Commit each deputado to avoid session issues
                        updated_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to update deputado {deputado_data.get('id')}: {e}")
                        session.rollback()  # Rollback failed transaction
                        continue
                
                session.commit()
                logger.info(f"Background update completed: {updated_count} deputados updated")
        
    except Exception as e:
        logger.error(f"Background update failed: {e}")

def create_quick_analysis_from_db(deputado_id: int, deputado: Deputado, voting_history: List[Dict]) -> Dict:
    """Create quick analysis from database voting history"""
    if not voting_history:
        return {
            "deputado": {
                "id": deputado_id,
                "nome": deputado.nome_parlamentar if deputado else "Deputado não encontrado",
                "partido": deputado.sigla_partido if deputado else "",
                "uf": deputado.sigla_uf if deputado else ""
            },
            "historico_votacoes": [],
            "estatisticas": {
                "total_votacoes_analisadas": 0,
                "participacao": 0,
                "presenca_percentual": 0,
                "votos_favoraveis": 0,
                "votos_contrarios": 0
            }
        }
    
    # Simple vote counting
    votos_sim = len([v for v in voting_history if v['voto'] == 'Sim'])
    votos_nao = len([v for v in voting_history if v['voto'] == 'Não'])
    total_votos = len(voting_history)
    
    return {
        "deputado": {
            "id": deputado_id,
            "nome": deputado.nome_parlamentar if deputado else "Deputado não encontrado",
            "partido": deputado.sigla_partido if deputado else "",
            "uf": deputado.sigla_uf if deputado else ""
        },
        "historico_votacoes": voting_history[:10],  # Show recent 10
        "estatisticas": {
            "total_votacoes_analisadas": total_votos,
            "participacao": total_votos,
            "presenca_percentual": 100.0,  # We only have votes they participated in
            "votos_favoraveis": votos_sim,
            "votos_contrarios": votos_nao
        },
        "fonte": "database_quick_analysis"
    }

async def update_deputy_analysis_from_api(deputado_id: int, incluir_todas: bool = True, limite_proposicoes: int = None):
    """Background task to update deputy analysis with fresh API data"""
    try:
        if not DATABASE_AVAILABLE:
            return
            
        logger.info(f"Background update: Analyzing deputy {deputado_id} with fresh API data")
        
        # Update deputy information first
        deputado = db_service.get_or_fetch_deputado(deputado_id, force_update=True)
        
        # Get propositions and analyze with API data
        dados_proposicoes = analisador.carregar_dados("proposicoes.json")
        proposicoes_relevantes = dados_proposicoes.get("votacoes_historicas", [])
        
        if limite_proposicoes:
            proposicoes_relevantes = proposicoes_relevantes[:limite_proposicoes]
        
        proposicoes_analisadas = []
        for prop in proposicoes_relevantes[:5]:  # Limit to avoid long background tasks
            try:
                numero_completo = prop.get("numero", "")
                if "/" not in numero_completo:
                    continue
                    
                numero_str, ano_str = numero_completo.split("/")
                numero = int(numero_str)
                ano = int(ano_str)
                
                resultado = analisador.processar_proposicao_completa(
                    prop["tipo"], numero, ano, prop["titulo"], prop.get("relevancia", "média")
                )
                
                if resultado:
                    proposicoes_analisadas.append(resultado)
                    
            except Exception as e:
                logger.warning(f"Error processing proposition in background: {e}")
                continue
        
        if proposicoes_analisadas:
            # Run full analysis and save to database
            analise = analisador.analisar_deputado(deputado_id, proposicoes_analisadas)
            
            # Save analysis to database
            db_service.save_deputado_analysis(deputado_id, analise)
            
            logger.info(f"Background update completed: Deputy {deputado_id} analysis updated with {len(proposicoes_analisadas)} propositions")
        
    except Exception as e:
        logger.error(f"Background deputy analysis update failed: {e}")

# ENHANCED ENDPOINTS WITH DATABASE INTEGRATION

@app.get("/deputados")
async def get_deputados(
    background_tasks: BackgroundTasks,
    nome: str = None, 
    partido: str = None, 
    uf: str = None,
    limit: int = 50,
    db: VotoDBService = Depends(get_database_service)
):
    """Hybrid approach: Load from DB immediately, update from API in background"""
    try:
        if DATABASE_AVAILABLE:
            # Step 1: Load from database immediately (fast response)
            deputados = db.search_deputados(nome=nome, partido=partido, uf=uf, limit=limit)
            
            # Convert to API format
            deputados_data = []
            for dep in deputados:
                deputados_data.append({
                    "id": dep["id"],
                    "nome": dep["nome_parlamentar"],
                    "nomeCivil": dep["nome_civil"],
                    "siglaPartido": dep["sigla_partido"],
                    "siglaUf": dep["sigla_uf"],
                    "situacao": dep["situacao"],
                    "email": dep["email"]
                })
            
            # Step 2: Schedule background API update (if we have few results or specific search)
            if len(deputados_data) < 10 or nome:
                background_tasks.add_task(
                    update_deputados_from_api,
                    nome=nome, partido=partido, uf=uf
                )
            
            return {
                "success": True,
                "dados": deputados_data,
                "total": len(deputados_data),
                "fonte": "database",
                "background_update": len(deputados_data) < 10 or nome is not None
            }
        else:
            # Fallback to legacy API cache
            endpoint = f"/deputados{'?nome=' + nome if nome else ''}&ordem=ASC&ordenarPor=nome"
            cache_key = f"deputados:{nome or 'all'}"
            data = await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])
            return data or {"dados": []}
            
    except Exception as e:
        logger.error(f"Error in get_deputados: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.get("/deputados/{deputado_id}")
async def get_deputado_detalhes(
    deputado_id: int,
    force_update: bool = False,
    db: VotoDBService = Depends(get_database_service)
):
    """Get deputado details from database with API update if needed"""
    try:
        if DATABASE_AVAILABLE:
            deputado = db.get_or_fetch_deputado(deputado_id, force_update=force_update)
            
            if deputado:
                return {
                    "success": True,
                    "dados": deputado.dados_completos,
                    "cached_in_db": True,
                    "last_updated": deputado.atualizado_em.isoformat()
                }
            else:
                raise HTTPException(status_code=404, detail="Deputado não encontrado")
        else:
            # Legacy fallback
            endpoint = f"/deputados/{deputado_id}"
            cache_key = f"deputado:{deputado_id}:detalhes"
            return await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_deputado_detalhes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.get("/deputados/{deputado_id}/votacoes")
async def get_deputado_votacoes(
    deputado_id: int,
    limit: int = 50,
    db: VotoDBService = Depends(get_database_service)
):
    """Get deputado voting history with database-first approach"""
    try:
        if DATABASE_AVAILABLE:
            logger.info(f"Getting voting history from database for deputy {deputado_id}")
            
            # Use our new database method
            voting_history = db.get_deputado_voting_history(deputado_id, limit=limit)
            
            if voting_history:
                return {
                    "success": True,
                    "dados": voting_history,
                    "total": len(voting_history),
                    "cached": False,
                    "fonte": "database",
                    "message": f"Loaded {len(voting_history)} votes from database"
                }
            else:
                # Deputy exists but no votes found in DB - try to fetch from API
                deputado = db.get_or_fetch_deputado(deputado_id)
                if deputado:
                    logger.info(f"No votes in database for deputy {deputado_id}, trying API fallback")
                    # Try legacy API approach as fallback
                    endpoint = f"/deputados/{deputado_id}/votacoes"
                    cache_key = f"deputado:{deputado_id}:votacoes_relevantes"
                    legacy_data = await fetch_with_cache(endpoint, cache_key, CACHE_TTL["votacoes"])
                    
                    if legacy_data and legacy_data.get("dados"):
                        return {
                            "success": True,
                            "dados": legacy_data["dados"],
                            "total": len(legacy_data["dados"]),
                            "cached": True,
                            "fonte": "api_fallback",
                            "message": "No database votes found, loaded from API cache"
                        }
        else:
            # Use legacy method from main_v2.py
            cache_key = f"deputado:{deputado_id}:votacoes_relevantes"
            
            if r:
                try:
                    cached = r.get(cache_key)
                    if cached:
                        cached_data = json.loads(cached)
                        return {"success": True, "dados": cached_data, "cached": True, "total": len(cached_data)}
                except:
                    pass
            
            # Return demo data or empty
            return {
                "success": True,
                "dados": [],
                "total": 0,
                "fonte": "fallback"
            }
            
    except Exception as e:
        logger.error(f"Error in get_deputado_votacoes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.get("/proposicoes/buscar")
async def buscar_proposicao(
    tipo: str, 
    numero: int, 
    ano: int,
    force_update: bool = False,
    db: VotoDBService = Depends(get_database_service)
):
    """Search proposition in database with API fallback"""
    try:
        if DATABASE_AVAILABLE:
            proposicao = db.get_or_fetch_proposicao(tipo, numero, ano, force_update=force_update)
            
            if proposicao:
                return {
                    "success": True, 
                    "data": proposicao.dados_completos,
                    "database_cached": True,
                    "last_updated": proposicao.atualizado_em.isoformat()
                }
            else:
                raise HTTPException(status_code=404, detail="Proposição não encontrada")
        else:
            # Legacy method
            resultado = analisador.buscar_proposicao(tipo, numero, ano)
            if resultado:
                return {"success": True, "data": resultado}
            else:
                raise HTTPException(status_code=404, detail="Proposição não encontrada")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in buscar_proposicao: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.post("/proposicoes/analisar")
async def analisar_proposicao(
    proposicao: ProposicaoRequest, 
    background_tasks: BackgroundTasks,
    force_update: bool = False
):
    """Analyze proposition with enhanced database integration"""
    try:
        # Check Redis cache first for quick response
        cache_key = f"proposicao_analisada:{proposicao.tipo}_{proposicao.numero}_{proposicao.ano}"
        
        if not force_update and r:
            try:
                cached = r.get(cache_key)
                if cached:
                    return {
                        "success": True,
                        "data": json.loads(cached),
                        "cached": True,
                        "message": "Dados carregados do cache Redis"
                    }
            except:
                pass
        
        # Process with enhanced analisador
        resultado = analisador.processar_proposicao_completa(
            proposicao.tipo,
            proposicao.numero,
            proposicao.ano,
            proposicao.titulo,
            proposicao.relevancia
        )
        
        if resultado:
            # Cache in Redis for quick access
            if r:
                try:
                    r.setex(cache_key, CACHE_TTL["proposicoes"], json.dumps(resultado))
                except:
                    pass
            
            # Background task to save data
            background_tasks.add_task(
                salvar_proposicao_analisada,
                resultado
            )
            
            return {
                "success": True,
                "data": resultado,
                "cached": False,
                "database_integration": DATABASE_AVAILABLE,
                "message": "Proposição processada com sucesso"
            }
        else:
            raise HTTPException(status_code=404, detail="Não foi possível processar a proposição")
            
    except Exception as e:
        logger.error(f"Error in analisar_proposicao: {e}")
        raise HTTPException(status_code=500, detail=f"Erro no processamento: {str(e)}")

@app.get("/deputados/{deputado_id}/analise")
async def analisar_perfil_deputado(
    deputado_id: int,
    background_tasks: BackgroundTasks,
    incluir_todas: bool = True, 
    limite_proposicoes: int = None, 
    force_update: bool = False,
    db: VotoDBService = Depends(get_database_service)
):
    """Hybrid approach: Load from DB immediately, update from API in background"""
    try:
        # Step 1: Always return database data first (immediate response)
        if DATABASE_AVAILABLE:
            logger.info(f"Loading deputy {deputado_id} analysis from database")
            
            # Get deputy from database (don't fetch from API yet)
            with get_db_session() as session:
                deputado = session.query(Deputado).filter(Deputado.id == deputado_id).first()
            
            # Get existing voting history from database
            voting_history_from_db = db.get_deputado_voting_history(
                deputado_id, 
                limit=limite_proposicoes or 50
            )
            
            # Check for existing analysis
            cached_analysis = None
            if not force_update:
                cached_analysis = db.get_deputado_analysis(deputado_id)
            
            # Prepare response with available data
            response_data = {
                "success": True,
                "database_votes": len(voting_history_from_db),
                "deputado_in_db": deputado is not None,
                "background_update_scheduled": True
            }
            
            # If we have cached analysis, return it immediately
            if cached_analysis and not force_update:
                response_data.update({
                    "data": cached_analysis.analise_completa,
                    "cached": True,
                    "last_analyzed": cached_analysis.data_analise.isoformat(),
                    "message": "Análise carregada do banco de dados"
                })
            elif voting_history_from_db:
                # Quick analysis from database data
                quick_analysis = create_quick_analysis_from_db(deputado_id, deputado, voting_history_from_db)
                response_data.update({
                    "data": quick_analysis,
                    "cached": False,
                    "message": f"Análise rápida com {len(voting_history_from_db)} votos do banco de dados"
                })
            else:
                # No data available yet
                response_data.update({
                    "data": None,
                    "cached": False,
                    "message": "Nenhum dado disponível no banco. Buscando da API..."
                })
            
            # Step 2: Schedule background update to refresh from API
            background_tasks.add_task(
                update_deputy_analysis_from_api,
                deputado_id, incluir_todas, limite_proposicoes
            )
            
            return response_data
        else:
            # Fallback to legacy method if database not available
            logger.info("Database not available, using legacy analysis")
            # Fall back to processing propositions from config file
            proposicoes_analisadas = []
        
        if incluir_todas:
            dados_proposicoes = analisador.carregar_dados("proposicoes.json")
            proposicoes_relevantes = dados_proposicoes.get("votacoes_historicas", [])
            
            if limite_proposicoes:
                proposicoes_relevantes = proposicoes_relevantes[:limite_proposicoes]
            
            logger.info(f"Processando {len(proposicoes_relevantes)} proposições para o deputado {deputado_id}")
            
            for i, prop in enumerate(proposicoes_relevantes, 1):
                logger.info(f"[{i}/{len(proposicoes_relevantes)}] Processando: {prop.get('tipo')} {prop.get('numero')}")
                
                try:
                    numero_completo = prop.get("numero", "")
                    if "/" in numero_completo:
                        numero_str, ano_str = numero_completo.split("/")
                        numero = int(numero_str)
                        ano = int(ano_str)
                    else:
                        logger.warning(f"Formato de número inválido: {numero_completo}")
                        continue
                    
                    resultado = analisador.processar_proposicao_completa(
                        prop["tipo"], numero, ano, prop["titulo"], prop.get("relevancia", "média")
                    )
                    
                    if resultado:
                        proposicoes_analisadas.append(resultado)
                        logger.info(f"SUCESSO: Proposição processada - ID {resultado['proposicao']['id']}")
                    else:
                        logger.warning(f"Falha ao processar proposição {prop['tipo']} {numero}/{ano}")
                        
                except Exception as e:
                    logger.error(f"Erro ao processar proposição {prop.get('tipo', 'N/A')} {prop.get('numero', 'N/A')}: {str(e)}")
                    continue
        
        if not proposicoes_analisadas:
            return {
                "success": False,
                "message": "Nenhuma proposição analisada disponível para este deputado"
            }
        
        logger.info(f"Analisando perfil do deputado com {len(proposicoes_analisadas)} proposições processadas...")
        analise = analisador.analisar_deputado(deputado_id, proposicoes_analisadas)
        
        resultado_final = {
            "success": True,
            "data": analise,
            "proposicoes_analisadas": len(proposicoes_analisadas),
            "cached": False,
            "database_integration": DATABASE_AVAILABLE,
            "processamento": {
                "total_proposicoes_tentadas": len(proposicoes_relevantes) if incluir_todas else 0,
                "proposicoes_com_sucesso": len(proposicoes_analisadas),
                "taxa_sucesso": f"{len(proposicoes_analisadas)/len(proposicoes_relevantes)*100:.1f}%" if incluir_todas and proposicoes_relevantes else "N/A"
            }
        }
        
        return resultado_final
        
    except Exception as e:
        logger.error(f"Error in analisar_perfil_deputado: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na análise: {str(e)}")

# DATABASE SPECIFIC ENDPOINTS

@app.get("/database/stats")
async def get_database_stats(db: VotoDBService = Depends(get_database_service)):
    """Get database statistics"""
    try:
        stats = db.get_database_stats()
        return {
            "success": True,
            "data": stats,
            "database_available": DATABASE_AVAILABLE
        }
    except Exception as e:
        logger.error(f"Error getting database stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

@app.post("/database/cleanup")
async def cleanup_database(db: VotoDBService = Depends(get_database_service)):
    """Cleanup old database entries"""
    try:
        expired, deleted = db.cleanup_expired_cache()
        return {
            "success": True,
            "message": f"Limpeza concluída: {expired} expirados, {deleted} deletados"
        }
    except Exception as e:
        logger.error(f"Error in database cleanup: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na limpeza: {str(e)}")

@app.get("/cache/stats")
async def get_cache_stats():
    """Get enhanced cache statistics"""
    try:
        cache_stats = analisador.get_cache_stats()
        return {
            "success": True,
            "data": cache_stats
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas do cache: {str(e)}")

@app.post("/cache/clear")
async def clear_cache(cache_type: str = "all"):
    """Clear cache with database support"""
    try:
        analisador.clear_cache(cache_type)
        new_stats = analisador.get_cache_stats()
        return {
            "success": True,
            "message": f"Cache '{cache_type}' limpo com sucesso",
            "data": new_stats
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao limpar cache: {str(e)}")

@app.get("/health")
async def health_check():
    """Enhanced health check with database status"""
    database_status = "offline"
    
    if DATABASE_AVAILABLE:
        try:
            database_status = "online" if test_connection() else "offline"
        except:
            database_status = "error"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "3.0.0",
        "database": {
            "available": DATABASE_AVAILABLE,
            "status": database_status
        },
        "redis": r is not None,
        "services": {
            "api_camara": "online",
            "redis": "online" if r else "offline",
            "database": database_status,
            "analisador": "online"
        }
    }

# LEGACY COMPATIBILITY FUNCTIONS

async def fetch_with_cache(endpoint, cache_key, ttl):
    """Legacy cache function for backward compatibility"""
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

def salvar_proposicao_analisada(resultado: Dict):
    """Background task to save analyzed proposition"""
    try:
        filename = f"proposicao_{resultado['proposicao']['tipo']}_{resultado['proposicao']['numero']}_{resultado['proposicao']['ano']}.json"
        analisador.salvar_dados(resultado, filename)
        logger.info(f"Proposição salva: {filename}")
    except Exception as e:
        logger.error(f"Erro ao salvar proposição: {e}")

# Legacy endpoints for backward compatibility
@app.get("/proposicoes/relevantes")
async def get_proposicoes_relevantes():
    """Legacy endpoint - get relevant propositions"""
    try:
        dados = analisador.carregar_dados("proposicoes.json")
        return {
            "success": True,
            "data": dados,
            "total": len(dados.get("proposicoes_relevantes", []))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar proposições: {str(e)}")

@app.get("/estatisticas/geral")
async def get_estatisticas_gerais():
    """Enhanced general statistics"""
    try:
        dados_proposicoes = analisador.carregar_dados("proposicoes.json")
        
        cache_stats = analisador.get_cache_stats()
        
        return {
            "success": True,
            "data": {
                "proposicoes_relevantes": len(dados_proposicoes.get("proposicoes_relevantes", [])),
                "cache": cache_stats,
                "sistema": {
                    "versao": "3.0.0",
                    "database_integration": DATABASE_AVAILABLE,
                    "redis_disponivel": r is not None,
                    "ultima_atualizacao": dados_proposicoes.get("metadados", {}).get("ultima_atualizacao")
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting general stats: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter estatísticas: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)