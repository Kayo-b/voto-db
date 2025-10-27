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