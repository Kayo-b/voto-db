from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import redis
import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
CACHE_TTL = {"deputados": 604800, "votacoes": 86400}

async def fetch_with_cache(endpoint, cache_key, ttl):
    cached = r.get(cache_key)
    if cached:
        return json.loads(cached)
    
    response = requests.get(f"{CAMARA_BASE_URL}{endpoint}")
    if response.status_code == 200:
        data = response.json()
        r.setex(cache_key, ttl, json.dumps(data))
        return data
    return None

@app.get("/deputados")
async def get_deputados(nome: str = None):
    endpoint = f"/deputados{'?nome=' + nome if nome else '' + '&ordem=ASC&ordenarPor=nome'}"
    cache_key = f"deputados:{nome or 'all'}"
    return await fetch_with_cache(endpoint, cache_key, CACHE_TTL["deputados"])

@app.get("/deputados/{deputado_id}/votacoes")
async def get_deputado_votacoes(deputado_id: int):
    endpoint = f"/deputados/{deputado_id}/votacoes"
    cache_key = f"deputado:{deputado_id}:votacoes"
    return await fetch_with_cache(endpoint, cache_key, CACHE_TTL["votacoes"])