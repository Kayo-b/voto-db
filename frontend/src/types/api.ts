export interface Deputado {
  id: number;
  nome: string;
  siglaPartido: string;
  siglaUf: string;
  urlFoto?: string;
  email?: string;
}

export interface DeputadosResponse {
  dados: Deputado[];
  links: Array<{ rel: string; href: string }>;
}

export interface Votacao {
  id: string;
  data: string;
  dataHoraRegistro: string;
  siglaOrgao: string;
  uriOrgao: string;
  voto: string;
  proposicao: {
    id: number;
    uri: string;
    siglaTipo: string;
    numero: string;
    ano: string;
    ementa: string;
  };
}

export interface VotacoesResponse {
  success?: boolean;
  dados: Votacao[];
  total?: number;
  cached?: boolean;
  links: Array<{ rel: string; href: string }>;
}

export interface AnaliseDeputado {
  deputado: {
    id: number;
    nome: string;
    nome_parlamentar: string;
    partido: string;
    uf: string;
    situacao: string;
  };
  historico_votacoes: Array<{
    proposicao: string;
    titulo: string;
    voto: string;
    data: string;
    relevancia: string;
  }>;
  estatisticas: {
    total_votacoes_analisadas: number;
    participacao: number;
    presenca_percentual: number;
    votos_favoraveis: number;
    votos_contrarios: number;
  };
}

export interface AnaliseDeputadoResponse {
  success: boolean;
  data?: AnaliseDeputado;
  message?: string;
}

export interface DeputadoVotoAtividade {
  proposicao: {
    id: number;
    codigo: string;
    tipo?: string;
    numero?: string;
    ano?: number;
    ementa?: string;
  } | null;
  proposicao_codigo: string;
  titulo: string;
  voto: string;
  data: string;
  votacao_id: string;
  sigla_orgao: string;
  tipo_votacao: string;
}

export interface DeputadoVotosRecentesResponse {
  success: boolean;
  data: DeputadoVotoAtividade[];
  total: number;
  deputado_id: number;
  source?: 'db' | 'db_enriched';
  pagination?: {
    offset: number;
    limit: number;
    total_cached: number;
    has_more: boolean;
  };
  enrichment?: {
    api_pages_scanned: number;
    votacoes_scanned: number;
    new_votacoes_stored: number;
    new_votos_stored: number;
    matched_votacoes_for_deputado: number;
  };
}
