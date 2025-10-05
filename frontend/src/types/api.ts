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