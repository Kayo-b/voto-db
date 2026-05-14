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

export interface FiscalSource {
  codigo: string;
  nome: string;
  url: string;
  foco: string;
  requer_chave: boolean;
}

export interface FiscalOverview {
  pessoas_total: number;
  pessoas_ativas: number;
  registros_financeiros: number;
  analises_total: number;
  analises_sinalizadas: number;
}

export interface FiscalSuspect {
  person_id: number;
  nome: string;
  cargo: string;
  orgao?: string;
  ano: number;
  risco_score: number;
  indice_compatibilidade: number;
  excesso_nao_explicado: number;
  crescimento_patrimonial: number;
  inflows_conhecidos: number;
  regra_disparo?: string;
  analisado_em?: string;
}

export interface FiscalPersonRanking {
  person_id: number;
  nome: string;
  cargo: string;
  orgao?: string;
  ano_referencia?: number;
  risco_score: number;
  nivel_suspeita: 'CRITICO' | 'ALTO' | 'MEDIO' | 'BAIXO' | 'MINIMO' | 'SEM_DADOS';
  motivo_nivel?: string;
  indice_compatibilidade?: number;
  excesso_nao_explicado: number;
  sinalizado: boolean;
  totais_por_tipo?: Record<string, number>;
  cobertura?: {
    tipos: string[];
    registros_por_tipo: Record<string, number>;
    suficiente_para_analise: boolean;
  };
  raw_records?: FiscalRawRecord[];
}

export interface FiscalRawRecord {
  id: number;
  ano: number;
  tipo: string;
  valor: number;
  moeda: string;
  fonte: string;
  fonte_url?: string;
  confianca: number;
  data_referencia?: string;
  extra_json?: Record<string, unknown>;
}

export interface RadarGovInsight {
  pattern_id: string;
  titulo: string;
  descricao: string;
  impacto: number;
  confidence: number;
  severity: 'Crítico' | 'Alto' | 'Médio' | 'Baixo';
  fontes: string[];
  ano?: number;
}

export interface RadarGovTimelineEvent {
  date: string;
  category: string;
  source: string;
  text: string;
}

export interface RadarGovReport {
  cpf: string;
  found: boolean;
  message?: string;
  person?: {
    id: number;
    nome: string;
    cargo: string;
    orgao?: string;
  };
  summary: {
    exposicao_total: number;
    irregularidades: number;
    fontes: number;
    entidades: number;
    conexoes: number;
    alertas: number;
  };
  insights: RadarGovInsight[];
  timeline: RadarGovTimelineEvent[];
  entity_graph: {
    nodes: Array<{ id: string; label: string; type: string }>;
    edges: Array<{ from: string; to: string; label: string }>;
  };
  supported_patterns?: Array<{ id: string; name: string }>;
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
