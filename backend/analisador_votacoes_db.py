"""
Enhanced AnalisadorVotacoes with PostgreSQL database integration
Maintains backward compatibility while adding database-first approach
"""
import requests
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

# Import database components
try:
    from database.service import VotoDBService
    from database.models import Deputado, Proposicao, Votacao, Voto
    from database.connection import get_db_session
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    print("Database components not available, falling back to file cache only")

@dataclass
class Proposicao:
    id: int
    tipo: str
    numero: int
    ano: int
    titulo: str
    relevancia: str
    ementa: str = ""

@dataclass
class Votacao:
    id: str
    id_proposicao: int
    descricao: str
    data: str
    sigla_orgao: str
    aprovacao: bool

@dataclass
class VotoDeputado:
    deputado_id: int
    deputado_nome: str
    partido: str
    uf: str
    tipo_voto: str
    proposicao_id: int
    votacao_id: str

class AnalisadorVotacoesDB:
    """
    Enhanced version with database integration
    Falls back to file cache if database is unavailable
    """
    
    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
    DELAY_REQUEST = 1.0
    
    def __init__(self, data_dir: str = "data", use_database: bool = True):
        self.data_dir = data_dir
        self.use_database = use_database and DATABASE_AVAILABLE
        
        # Initialize database service if available
        if self.use_database:
            self.db_service = VotoDBService(api_client=self)
            print("Database integration enabled")
        else:
            self.db_service = None
            print("Using file cache only")
        
        # Legacy file cache setup (kept for fallback)
        os.makedirs(data_dir, exist_ok=True)
        self.proposicoes_file = os.path.join(data_dir, "proposicoes.json")
        self.votacoes_file = os.path.join(data_dir, "votacoes.json")
        self.votos_file = os.path.join(data_dir, "votos.json")
        
        # Cache files for different types of data
        self.cache_dir = os.path.join(data_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.proposicoes_cache = os.path.join(self.cache_dir, "proposicoes_cache.json")
        self.detalhes_cache = os.path.join(self.cache_dir, "detalhes_cache.json")
        self.votacoes_cache = os.path.join(self.cache_dir, "votacoes_cache.json")
        self.votos_cache = os.path.join(self.cache_dir, "votos_cache.json")
        
        # Load existing caches (fallback)
        if not self.use_database:
            self._load_caches()
    
    def _load_caches(self):
        """Load existing cache data (legacy fallback)"""
        self.proposicoes_cache_data = self._load_cache_file(self.proposicoes_cache)
        self.detalhes_cache_data = self._load_cache_file(self.detalhes_cache)
        self.votacoes_cache_data = self._load_cache_file(self.votacoes_cache)
        self.votos_cache_data = self._load_cache_file(self.votos_cache)
        
    def _load_cache_file(self, filepath: str) -> Dict:
        """Load cache file or return empty dict"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_cache_file(self, filepath: str, data: Dict):
        """Save cache data to file"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache {filepath}: {e}")
    
    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        return "_".join(str(arg) for arg in args)
        
    def _delay(self):
        """Aplica delay para respeitar rate limiting"""
        time.sleep(self.DELAY_REQUEST)
    
    def _fazer_requisicao(self, endpoint: str, params: Dict = None) -> Dict:
        """Faz requisição para API com tratamento de erros"""
        try:
            self._delay()
            response = requests.get(f"{self.BASE_URL}{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição para {endpoint}: {e}")
            return {"dados": []}
    
    def buscar_proposicao(self, tipo: str, numero: int, ano: int) -> Optional[Dict]:
        """
        Busca proposição - DATABASE FIRST approach
        """
        if self.use_database:
            # Try database first
            proposicao_obj = self.db_service.get_or_fetch_proposicao(tipo, numero, ano)
            if proposicao_obj:
                print(f"[DB] Proposição {tipo} {numero}/{ano} encontrada")
                return proposicao_obj.dados_completos
            else:
                print(f"[DB] Proposição {tipo} {numero}/{ano} não encontrada")
                return None
        else:
            # Fallback to legacy file cache method
            return self._buscar_proposicao_legacy(tipo, numero, ano)
    
    def _buscar_proposicao_legacy(self, tipo: str, numero: int, ano: int) -> Optional[Dict]:
        """Legacy file cache method"""
        cache_key = self._get_cache_key(tipo, numero, ano)
        if cache_key in self.proposicoes_cache_data:
            print(f"[CACHE] Proposição {tipo} {numero}/{ano} encontrada no cache")
            return self.proposicoes_cache_data[cache_key]
        
        params = {
            'siglaTipo': tipo,
            'numero': numero,
            'ano': ano
        }
        
        print(f"[API] Buscando proposição {tipo} {numero}/{ano}...")
        response = self._fazer_requisicao("/proposicoes", params)
        dados = response.get('dados', [])
        
        result = dados[0] if dados else None
        
        if result:
            self.proposicoes_cache_data[cache_key] = result
            self._save_cache_file(self.proposicoes_cache, self.proposicoes_cache_data)
        
        return result
    
    def buscar_detalhes_proposicao(self, id_proposicao: int) -> Optional[Dict]:
        """Busca detalhes completos de uma proposição"""
        if self.use_database:
            # Database approach - get from proposicao record
            with get_db_session() as session:
                from database.models import Proposicao
                proposicao = session.query(Proposicao).filter(Proposicao.id == id_proposicao).first()
                if proposicao and proposicao.dados_completos:
                    print(f"[DB] Detalhes da proposição {id_proposicao} encontrados")
                    return proposicao.dados_completos
        
        # Fallback to API call
        print(f"[API] Buscando detalhes da proposição {id_proposicao}...")
        response = self._fazer_requisicao(f"/proposicoes/{id_proposicao}")
        return response.get('dados')
    
    def buscar_votacoes_proposicao(self, id_proposicao: int) -> List[Dict]:
        """
        Busca todas as votações de uma proposição - DATABASE FIRST
        """
        if self.use_database:
            votacoes_obj = self.db_service.get_or_fetch_votacoes(id_proposicao)
            if votacoes_obj:
                print(f"[DB] {len(votacoes_obj)} votações encontradas para proposição {id_proposicao}")
                return [v.dados_completos for v in votacoes_obj if v.dados_completos]
            else:
                return []
        else:
            # Legacy method
            return self._buscar_votacoes_legacy(id_proposicao)
    
    def _buscar_votacoes_legacy(self, id_proposicao: int) -> List[Dict]:
        """Legacy file cache method for votações"""
        cache_key = str(id_proposicao)
        if cache_key in self.votacoes_cache_data:
            print(f"[CACHE] Votações da proposição {id_proposicao} encontradas no cache")
            return self.votacoes_cache_data[cache_key]
        
        print(f"[API] Buscando votações da proposição {id_proposicao}...")
        response = self._fazer_requisicao(f"/proposicoes/{id_proposicao}/votacoes")
        result = response.get('dados', [])
        
        if result:
            self.votacoes_cache_data[cache_key] = result
            self._save_cache_file(self.votacoes_cache, self.votacoes_cache_data)
        
        return result
    
    def buscar_votos_votacao(self, id_votacao: str) -> List[Dict]:
        """
        Busca votos individuais de uma votação - DATABASE FIRST
        """
        if self.use_database:
            votos_obj = self.db_service.get_or_fetch_votos(id_votacao)
            if votos_obj:
                print(f"[DB] {len(votos_obj)} votos encontrados para votação {id_votacao}")
                return [v.dados_completos for v in votos_obj if v.dados_completos]
            else:
                return []
        else:
            # Legacy method
            return self._buscar_votos_legacy(id_votacao)
    
    def _buscar_votos_legacy(self, id_votacao: str) -> List[Dict]:
        """Legacy file cache method for votos"""
        cache_key = str(id_votacao)
        if cache_key in self.votos_cache_data:
            print(f"[CACHE] Votos da votação {id_votacao} encontrados no cache")
            return self.votos_cache_data[cache_key]
        
        print(f"[API] Buscando votos da votação {id_votacao}...")
        
        todos_votos = []
        pagina = 1
        
        while True:
            response = self._fazer_requisicao(f"/votacoes/{id_votacao}/votos")
            votos = response.get('dados', [])
            
            if not votos:
                break
                
            todos_votos.extend(votos)
            
            links = response.get('links', [])
            tem_proxima = any(link.get('rel') == 'next' for link in links)
            
            if not tem_proxima:
                break
                
            pagina += 1
        
        if todos_votos:
            self.votos_cache_data[cache_key] = todos_votos
            self._save_cache_file(self.votos_cache, self.votos_cache_data)
        
        return todos_votos
    
    def analisar_deputado(self, deputado_id: int, proposicoes_analisadas: List[Dict]) -> Dict:
        """
        Analisa o perfil de votação de um deputado específico
        Uses database when available for better performance
        """
        print(f"\nAnalisando deputado ID: {deputado_id}")
        
        # Try to get cached analysis first
        if self.use_database:
            cached_analysis = self.db_service.get_deputado_analysis(deputado_id)
            if cached_analysis:
                print(f"[DB] Análise cached encontrada para deputado {deputado_id}")
                return cached_analysis.analise_completa
        
        # Get deputado info
        if self.use_database:
            deputado_obj = self.db_service.get_or_fetch_deputado(deputado_id)
            if deputado_obj:
                deputado_info = {
                    'nomeCivil': deputado_obj.nome_civil,
                    'ultimoStatus': {
                        'nome': deputado_obj.nome_parlamentar,
                        'siglaPartido': deputado_obj.sigla_partido,
                        'siglaUf': deputado_obj.sigla_uf,
                        'situacao': deputado_obj.situacao
                    }
                }
            else:
                return {"erro": "Deputado não encontrado"}
        else:
            # Legacy API call
            response = self._fazer_requisicao(f"/deputados/{deputado_id}")
            deputado_info = response.get('dados')
            if not deputado_info:
                return {"erro": "Deputado não encontrado"}
        
        # Analyze voting history
        historico_votacoes = []
        total_votacoes = 0
        votos_favor = 0
        
        for prop_data in proposicoes_analisadas:
            proposicao = prop_data['proposicao']
            votos = prop_data.get('votos', [])
            
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
        
        presenca = (total_votacoes / len(proposicoes_analisadas) * 100) if proposicoes_analisadas else 0
        
        resultado = {
            "deputado": {
                "id": deputado_id,
                "nome": deputado_info.get('nomeCivil', ''),
                "nome_parlamentar": deputado_info.get('ultimoStatus', {}).get('nome', ''),
                "partido": deputado_info.get('ultimoStatus', {}).get('siglaPartido', ''),
                "uf": deputado_info.get('ultimoStatus', {}).get('siglaUf', ''),
                "situacao": deputado_info.get('ultimoStatus', {}).get('situacao', '')
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
        
        # Save analysis to database if available
        if self.use_database:
            self.db_service.save_deputado_analysis(deputado_id, resultado)
            print(f"[DB] Análise salva para deputado {deputado_id}")
        
        return resultado
    
    def identificar_votacao_principal(self, votacoes: List[Dict]) -> Optional[Dict]:
        """Identifica a votação principal de uma proposição (unchanged)"""
        termos_inicio = ['aprovado', 'aprovada', 'rejeitado', 'rejeitada', 'sim', 'não']
        
        votacoes_plenario = [
            v for v in votacoes 
            if any(v.get('descricao', '').lower().startswith(termo) for termo in termos_inicio)
        ] 
        
        if not votacoes_plenario:
            return None
            
        return votacoes_plenario if votacoes_plenario else None
    
    def processar_proposicao_completa(self, tipo: str, numero: int, ano: int, 
                                    titulo: str, relevancia: str = "alta") -> Optional[Dict]:
        """
        Processa uma proposição completa - enhanced with database integration
        """
        try:
            print(f"\n{'='*60}")
            print(f"PROCESSANDO: {tipo} {numero}/{ano} - {titulo}")
            print(f"{'='*60}")
            
            print('Iniciando processamento da proposição...')
            proposicao = self.buscar_proposicao(tipo, numero, ano)
            if not proposicao:
                print(f"Proposição não encontrada: {tipo} {numero}/{ano}")
                return None
            
            id_proposicao = proposicao['id']
            print(f"Proposição encontrada - ID: {id_proposicao}")
        except Exception as e:
            print(f"Erro ao buscar proposição {tipo} {numero}/{ano}: {str(e)}")
            return None
        
        detalhes = self.buscar_detalhes_proposicao(id_proposicao)
        
        votacoes = self.buscar_votacoes_proposicao(id_proposicao)
        print(f"Encontradas {len(votacoes)} votações")
        
        votacao_principal = self.identificar_votacao_principal(votacoes)
        if not votacao_principal:
            print("Votação principal não encontrada")
            return None

        primeira_votacao = votacao_principal[0]
        id_votacao = primeira_votacao['id']

        print(f"Votação principal identificada - ID: {id_votacao}")
        print(f"   Descrição: {primeira_votacao.get('descricao', 'N/A')}")
        print(f"   Data: {primeira_votacao.get('dataHoraRegistro', 'N/A')}")
        
        print(f"Buscando votos da votação {id_votacao}...")
        votos = self.buscar_votos_votacao(id_votacao)
        
        if not votos and len(votacao_principal) > 1:
            for i, votacao_alt in enumerate(votacao_principal[1:], 1):
                print(f"Tentando votação alternativa {i} - ID: {votacao_alt['id']}")
                votos_alt = self.buscar_votos_votacao(votacao_alt['id'])
                if votos_alt:
                    primeira_votacao = votacao_alt
                    id_votacao = votacao_alt['id']
                    votos = votos_alt
                    print(f"Usando votação {id_votacao} com {len(votos)} votos")
                    break
        
        print(f"Coletados {len(votos)} votos individuais")
        
        resultado = {
            "proposicao": {
                "id": id_proposicao,
                "tipo": tipo,
                "numero": numero,
                "ano": ano,
                "titulo": titulo,
                "relevancia": relevancia,
                "ementa": detalhes.get('ementa', '') if detalhes else '',
                "situacao": detalhes.get('statusProposicao', {}).get('descricaoSituacao', '') if detalhes else ''
            },
            "votacao_principal": {
                "id": id_votacao,
                "descricao": primeira_votacao.get('descricao', ''),
                "data": primeira_votacao.get('dataHoraRegistro', ''),
                "aprovacao": primeira_votacao.get('aprovacao', False),
                "total_votos": len(votos)
            },
            "votos": votos,
            "estatisticas_votacao": self._calcular_estatisticas_votacao(votos),
            "processado_em": datetime.now().isoformat()
        }
        
        return resultado
    
    def _calcular_estatisticas_votacao(self, votos: List[Dict]) -> Dict:
        """Calcula estatísticas da votação (unchanged)"""
        if not votos:
            return {}
        
        stats = {"Sim": 0, "Não": 0, "Abstenção": 0, "Obstrução": 0, "Outros": 0}
        partidos = {}
        
        for voto in votos:
            tipo_voto = voto.get('tipoVoto', 'Outros')
            stats[tipo_voto] = stats.get(tipo_voto, 0) + 1
            
            deputado = voto.get('deputado_', {})
            partido = deputado.get('siglaPartido', 'Sem partido')
            
            if partido not in partidos:
                partidos[partido] = {"Sim": 0, "Não": 0, "Abstenção": 0, "Obstrução": 0, "total": 0}
            
            partidos[partido][tipo_voto] = partidos[partido].get(tipo_voto, 0) + 1
            partidos[partido]["total"] += 1
        
        return {
            "total_deputados": len(votos),
            "distribuicao_votos": stats,
            "por_partido": partidos
        }
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics - enhanced with database stats"""
        if self.use_database:
            db_stats = self.db_service.get_database_stats()
            return {
                "database_enabled": True,
                **db_stats,
                "cache_type": "PostgreSQL Database"
            }
        else:
            # Legacy file cache stats
            return {
                "database_enabled": False,
                "proposicoes_cached": len(getattr(self, 'proposicoes_cache_data', {})),
                "detalhes_cached": len(getattr(self, 'detalhes_cache_data', {})),
                "votacoes_cached": len(getattr(self, 'votacoes_cache_data', {})),
                "votos_cached": len(getattr(self, 'votos_cache_data', {})),
                "cache_type": "File-based JSON"
            }
    
    def clear_cache(self, cache_type: str = "all"):
        """Clear cache - enhanced for database"""
        if self.use_database:
            # Clear database cache entries
            self.db_service.cleanup_expired_cache()
            print("Database cache cleaned")
        else:
            # Legacy file cache clearing
            cache_files = {
                'proposicoes': (self.proposicoes_cache, 'proposicoes_cache_data'),
                'detalhes': (self.detalhes_cache, 'detalhes_cache_data'),
                'votacoes': (self.votacoes_cache, 'votacoes_cache_data'),
                'votos': (self.votos_cache, 'votos_cache_data')
            }
            
            if cache_type == "all":
                for cache_name, (file_path, attr_name) in cache_files.items():
                    setattr(self, attr_name, {})
                    self._save_cache_file(file_path, {})
                print("Todos os caches foram limpos")
            elif cache_type in cache_files:
                file_path, attr_name = cache_files[cache_type]
                setattr(self, attr_name, {})
                self._save_cache_file(file_path, {})
                print(f"Cache de {cache_type} foi limpo")
            else:
                print(f"Tipo de cache inválido: {cache_type}")
    
    # Legacy methods for backward compatibility
    def salvar_dados(self, dados: Dict, arquivo: str):
        """Salva dados em arquivo JSON (legacy method)"""
        filepath = os.path.join(self.data_dir, arquivo)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {filepath}")
    
    def carregar_dados(self, arquivo: str) -> Dict:
        """Carrega dados de arquivo JSON (legacy method)"""
        filepath = os.path.join(self.data_dir, arquivo)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {'ARQUIVO_NAO_ENCONTRADO': True}

# Backward compatibility - create alias
AnalisadorVotacoes = AnalisadorVotacoesDB

if __name__ == "__main__":
    # Test with database integration
    analisador = AnalisadorVotacoesDB(use_database=True)
    
    resultado = analisador.processar_proposicao_completa(
        tipo="PL",
        numero=6787,
        ano=2016,
        titulo="Lei da Terceirização",
        relevancia="alta"
    )
    
    if resultado:
        print("Análise completa concluída com integração de banco de dados!")
        print(f"Database enabled: {analisador.use_database}")
        print("Cache stats:", analisador.get_cache_stats())
    else:
        print("Falha na análise")