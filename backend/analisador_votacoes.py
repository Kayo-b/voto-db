import requests
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

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

class AnalisadorVotacoes:
    """
    Classe principal para análise de votações da Câmara dos Deputados
    """
    
    BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
    DELAY_REQUEST = 1.0
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
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
        
        # Load existing caches
        self._load_caches()
        
    def _load_caches(self):
        """Load existing cache data"""
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
        Busca proposição por tipo/número/ano
        
        Args:
            tipo: Sigla do tipo (PL, PEC, MP, etc.)
            numero: Número da proposição
            ano: Ano da proposição
            
        Returns:
            Dados da proposição ou None se não encontrada
        """
        # Check cache first
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
        
        # Save to cache
        if result:
            self.proposicoes_cache_data[cache_key] = result
            self._save_cache_file(self.proposicoes_cache, self.proposicoes_cache_data)
        
        return result
    
    def buscar_detalhes_proposicao(self, id_proposicao: int) -> Optional[Dict]:
        """Busca detalhes completos de uma proposição"""
        # Check cache first
        cache_key = str(id_proposicao)
        if cache_key in self.detalhes_cache_data:
            print(f"[CACHE] Detalhes da proposição {id_proposicao} encontrados no cache")
            return self.detalhes_cache_data[cache_key]
        
        print(f"[API] Buscando detalhes da proposição {id_proposicao}...")
        response = self._fazer_requisicao(f"/proposicoes/{id_proposicao}")
        result = response.get('dados')
        
        # Save to cache
        if result:
            self.detalhes_cache_data[cache_key] = result
            self._save_cache_file(self.detalhes_cache, self.detalhes_cache_data)
        
        return result
    
    def buscar_votacoes_proposicao(self, id_proposicao: int) -> List[Dict]:
        """
        Busca todas as votações de uma proposição
        
        Args:
            id_proposicao: ID da proposição
            
        Returns:
            Lista de votações da proposição
        """
        # Check cache first
        cache_key = str(id_proposicao)
        if cache_key in self.votacoes_cache_data:
            print(f"[CACHE] Votações da proposição {id_proposicao} encontradas no cache")
            return self.votacoes_cache_data[cache_key]
        
        print(f"[API] Buscando votações da proposição {id_proposicao}...")
        response = self._fazer_requisicao(f"/proposicoes/{id_proposicao}/votacoes")
        result = response.get('dados', [])
        
        # Save to cache
        if result:
            self.votacoes_cache_data[cache_key] = result
            self._save_cache_file(self.votacoes_cache, self.votacoes_cache_data)
        
        return result
    
    def identificar_votacao_principal(self, votacoes: List[Dict]) -> Optional[Dict]:
        """
        Identifica a votação principal de uma proposição
        
        Args:
            votacoes: Lista de votações da proposição
            
        Returns:
            Votação principal ou None se não encontrada
        """

        termos_inicio = ['aprovado', 'aprovada', 'rejeitado', 'rejeitada', 'sim', 'não']
        for v in votacoes: 
            if any(v.get('descricao', '').lower() == termo for termo in termos_inicio):
                print(v,'<<<<<<<<<<')

        votacoes_plenario = [
            v for v in votacoes 
            if any(v.get('descricao', '').lower().startswith(termo) for termo in termos_inicio)
        ] 
        # votacoes_plenario = [
        #     v for v in votacoes if v.get('id') == '2270800-160'
        # ]   
        # votacoes_plenario = [v for v in votacoes if v.get('siglaOrgao') == 'PLEN']
        if not votacoes_plenario:
            return None
        else:
            print(len(votacoes_plenario),'LENGHT votacoes_plenario((((111<<<<<))))')        
            print(votacoes_plenario,'LENGHT votacoes_plenario((((111<<<<<))))')
            
        # votacoes_plenario.sort(key=lambda x: x.get('dataHoraRegistro', ''), reverse=True)
        # print(votacoes_plenario,'votacoes_plenario((((222<<<<<))))') 


        # termos_principais = [
        #     'aprovado', 'aprovada', 'rejeitado', 'rejeitada'
        # ]


        # for votacao in votacoes_plenario:
        #     print(f"Analisando votação: {votacao.get('descricao', '')}")
        #     desc = votacao.get('descricao', '').lower()
        #     if any(termo in desc for termo in termos_principais):
        #         return votacao
        
        # print(f"VOTAÇÕES PLENÁRIO>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>> {votacoes_plenario[0]}")
        return votacoes_plenario if votacoes_plenario else None
    
    def buscar_votos_votacao(self, id_votacao: str) -> List[Dict]:
        """
        Busca votos individuais de uma votação
        
        Args:
            id_votacao: ID da votação (formato: proposicao-sequencial)
            
        Returns:
            Lista de votos dos deputados
        """
        # Check cache first
        cache_key = str(id_votacao)
        if cache_key in self.votos_cache_data:
            print(f"[CACHE] Votos da votação {id_votacao} encontrados no cache")
            return self.votos_cache_data[cache_key]
        
        print(f"[API] Buscando votos da votação {id_votacao}...")
        

        todos_votos = []
        pagina = 1
        
        while True:
            # params = {'pagina': pagina, 'itens': 100}
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
        
        # Save to cache
        if todos_votos:
            self.votos_cache_data[cache_key] = todos_votos
            self._save_cache_file(self.votos_cache, self.votos_cache_data)
        
        return todos_votos
    
    def clear_cache(self, cache_type: str = "all"):
        """
        Clear cache files
        
        Args:
            cache_type: Type of cache to clear ('all', 'proposicoes', 'detalhes', 'votacoes', 'votos')
        """
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
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "proposicoes_cached": len(self.proposicoes_cache_data),
            "detalhes_cached": len(self.detalhes_cache_data),
            "votacoes_cached": len(self.votacoes_cache_data),
            "votos_cached": len(self.votos_cache_data),
            "total_cached_items": (
                len(self.proposicoes_cache_data) +
                len(self.detalhes_cache_data) +
                len(self.votacoes_cache_data) +
                len(self.votos_cache_data)
            )
        }
    
    def processar_proposicao_completa(self, tipo: str, numero: int, ano: int, 
                                    titulo: str, relevancia: str = "alta") -> Optional[Dict]:
        """
        Processa uma proposição completa: busca dados, identifica votação principal e coleta votos
        
        Args:
            tipo: Tipo da proposição (PL, PEC, etc.)
            numero: Número da proposição
            ano: Ano da proposição
            titulo: Título descritivo da proposição
            relevancia: Nível de relevância (alta, média, baixa)
            
        Returns:
            Dados completos da proposição processada
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

        # Get the first voting as the main one
        primeira_votacao = votacao_principal[0]
        id_votacao = primeira_votacao['id']

        print(f"Votação principal identificada - ID: {id_votacao}")
        print(f"   Descrição: {primeira_votacao.get('descricao', 'N/A')}")
        print(f"   Data: {primeira_votacao.get('dataHoraRegistro', 'N/A')}")
        
        # Get votes for the main voting
        print(f"Buscando votos da votação {id_votacao}...")
        votos = self.buscar_votos_votacao(id_votacao)
        
        # If no votes found, try other votings in the list
        if not votos and len(votacao_principal) > 1:
            for i, votacao_alt in enumerate(votacao_principal[1:], 1):
                print(f"Tentando votação alternativa {i} - ID: {votacao_alt['id']}")
                votos_alt = self.buscar_votos_votacao(votacao_alt['id'])
                if votos_alt:
                    primeira_votacao = votacao_alt
                    id_votacao = votacao_alt['id']
                    votos = votos_alt
                    print(f"✓ Usando votação {id_votacao} com {len(votos)} votos")
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
        """Calcula estatísticas da votação"""
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
    
    def salvar_dados(self, dados: Dict, arquivo: str):
        """Salva dados em arquivo JSON"""
        filepath = os.path.join(self.data_dir, arquivo)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"Dados salvos em: {filepath}")
    
    def carregar_dados(self, arquivo: str) -> Dict:
        """Carrega dados de arquivo JSON"""
        filepath = os.path.join(self.data_dir, arquivo)
        print("Carregando dados de: filepath",filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                print("Dados carregados com sucesso.",f)
                return json.load(f)
        except FileNotFoundError:
            return {'ARQUIVO_NAO_ENCONTRADO': True}
    
    def analisar_deputado(self, deputado_id: int, proposicoes_analisadas: List[Dict]) -> Dict:
        """
        Analisa o perfil de votação de um deputado específico
        
        Args:
            deputado_id: ID do deputado
            proposicoes_analisadas: Lista de proposições já processadas
            
        Returns:
            Análise completa do deputado
        """
        print(f"\nAnalisando deputado ID: {deputado_id}")
        

        response = self._fazer_requisicao(f"/deputados/{deputado_id}")
        deputado_info = response.get('dados')
        
        if not deputado_info:
            return {"erro": "Deputado não encontrado"}
        

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
        
        return {
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


if __name__ == "__main__":
    analisador = AnalisadorVotacoes()
    
    resultado = analisador.processar_proposicao_completa(
        tipo="PL",
        numero=6787,
        ano=2016,
        titulo="Lei da Terceirização",
        relevancia="alta"
    )
    
    if resultado:
        analisador.salvar_dados(resultado, "exemplo_proposicao.json")