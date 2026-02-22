import axios, { AxiosResponse } from 'axios';
import {
  DeputadosResponse,
  VotacoesResponse,
  AnaliseDeputadoResponse,
  FiscalOverview,
  FiscalSource,
  FiscalSuspect,
  FiscalPersonRanking,
  RadarGovReport
} from '../types/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 60 seconds for votacoes recentes
});

export const api = {
  searchDeputados: async (nome?: string): Promise<DeputadosResponse> => {
    try {
      const response: AxiosResponse<DeputadosResponse> = await apiClient.get(
        `/deputados${nome ? `?nome=${nome}` : ''}`
      );
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar deputados:', error);
      throw error;
    }
  },
  
  getDeputadoVotacoes: async (id: number): Promise<VotacoesResponse> => {
    try {
      const response: AxiosResponse<VotacoesResponse> = await apiClient.get(
        `/deputados/${id}/votacoes`
      );
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar votações do deputado:', error);
      // Return empty response if error
      return {
        success: false,
        dados: [],
        total: 0,
        cached: false,
        links: []
      };
    }
  },

  getDeputadoDetalhes: async (id: number) => {
    try {
      const response = await apiClient.get(`/deputados/${id}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar detalhes do deputado:', error);
      throw error;
    }
  },

  getProposicoesRelevantes: async () => {
    try {
      const response = await apiClient.get('/proposicoes/relevantes');
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar proposições relevantes:', error);
      throw error;
    }
  },

  getProposicoesMonitoradas: async (params?: {
    relevancia?: string;
    somenteEmVotacao?: boolean;
    limit?: number;
  }) => {
    try {
      const query = new URLSearchParams();
      if (params?.relevancia) query.set('relevancia', params.relevancia);
      if (params?.somenteEmVotacao !== undefined) query.set('somente_em_votacao', String(params.somenteEmVotacao));
      if (params?.limit) query.set('limit', String(params.limit));

      const suffix = query.toString() ? `?${query.toString()}` : '';
      const response = await apiClient.get(`/proposicoes/monitoradas${suffix}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar proposições monitoradas:', error);
      throw error;
    }
  },

  syncProposicoesMonitoradas: async () => {
    try {
      const response = await apiClient.post('/proposicoes/monitoradas/sync');
      return response.data;
    } catch (error) {
      console.error('Erro ao sincronizar proposições monitoradas:', error);
      throw error;
    }
  },

  validateProposicao: async (codigo: string) => {
    try {
      const response = await apiClient.post('/proposicoes/relevantes/validate', {
        codigo
      });
      return response.data;
    } catch (error) {
      console.error('Erro ao validar proposição:', error);
      throw error;
    }
  },

  addProposicaoRelevante: async (codigo: string, titulo?: string, relevancia?: string) => {
    try {
      const response = await apiClient.post('/proposicoes/relevantes', {
        codigo,
        titulo,
        relevancia
      });
      return response.data;
    } catch (error) {
      console.error('Erro ao adicionar proposição:', error);
      throw error;
    }
  },

  deleteProposicaoRelevante: async (id: number) => {
    try {
      const response = await apiClient.delete(`/proposicoes/relevantes/${id}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao deletar proposição:', error);
      throw error;
    }
  },

  analisarDeputado: async (id: number, incluirTodas: boolean = false, signal?: AbortSignal): Promise<AnaliseDeputadoResponse> => {
    try {
      const url = `/deputados/${id}/analise${incluirTodas ? '?incluir_todas=true' : ''}`;
      const response = await apiClient.get(url, { signal });
      return response.data;
    } catch (error) {
      // Don't log cancelled requests as errors
      if ((error as any)?.name === 'CanceledError') {
        throw error;
      }
      
      console.error('Erro ao analisar deputado:', error);
      
      // Return error response structure
      return {
        success: false,
        message: 'Erro ao conectar com a API'
      };
    }
  },

  buscarVotacoesRecentes: async (dias: number, tipo: 'urgencia' | 'nominais' | 'todas') => {
    try {
      const response = await apiClient.get(`/votacoes/recentes?dias=${dias}&tipo=${tipo}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar votações recentes:', error);
      throw error;
    }
  },

  buscarVotosVotacao: async (votacaoId: string) => {
    try {
      const response = await apiClient.get(`/votacoes/${votacaoId}/votos`);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar votos da votação:', error);
      throw error;
    }
  },

  getDeputadoVotosRecentes: async (deputadoId: number, limit: number = 20) => {
    try {
      const response = await apiClient.get(`/deputados/${deputadoId}/votos-recentes?limit=${limit}`);
      return response.data;
    } catch (error) {
      console.error('Erro ao buscar votos recentes do deputado:', error);
      throw error;
    }
  },

  getFiscalSources: async (): Promise<{ success: boolean; sources: FiscalSource[]; notes: string[] }> => {
    const response = await apiClient.get('/fiscal-investigation/sources');
    return response.data;
  },

  getFiscalOverview: async (): Promise<{ success: boolean; data: FiscalOverview }> => {
    const response = await apiClient.get('/fiscal-investigation/overview');
    return response.data;
  },

  getFiscalSuspects: async (minRiskScore: number = 50, limit: number = 100): Promise<{ success: boolean; total: number; dados: FiscalSuspect[] }> => {
    const response = await apiClient.get(`/fiscal-investigation/suspects?min_risk_score=${minRiskScore}&limit=${limit}`);
    return response.data;
  },

  runFiscalAnalysis: async (params?: { anos?: string; minExcessoBrl?: number; minRatioCompatibilidade?: number }) => {
    const query = new URLSearchParams();
    if (params?.anos) query.set('anos', params.anos);
    if (params?.minExcessoBrl !== undefined) query.set('min_excesso_brl', String(params.minExcessoBrl));
    if (params?.minRatioCompatibilidade !== undefined) query.set('min_ratio_compatibilidade', String(params.minRatioCompatibilidade));
    const suffix = query.toString() ? `?${query.toString()}` : '';

    const response = await apiClient.post(`/fiscal-investigation/analyze${suffix}`);
    return response.data;
  },

  reconcileFiscalIdentities: async () => {
    const response = await apiClient.post('/fiscal-investigation/reconcile-identities');
    return response.data;
  },

  seedFiscalDemoData: async () => {
    const response = await apiClient.post('/fiscal-investigation/demo-seed');
    return response.data;
  },

  syncPortalTransparencia: async (payload?: { mesAno?: number; maxServidores?: number; paginaInicial?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/portal-transparencia',
      {
        mes_ano: payload?.mesAno,
        max_servidores: payload?.maxServidores ?? 50,
        pagina_inicial: payload?.paginaInicial ?? 1,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncPublicFinancing: async (payload?: { ano?: number; maxPaginas?: number; paginaInicial?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/public-financing',
      {
        ano: payload?.ano,
        max_paginas: payload?.maxPaginas ?? 10,
        pagina_inicial: payload?.paginaInicial ?? 1,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncCamaraExpenses: async (payload?: { ano?: number; maxDeputados?: number; maxPaginasDespesasPorDeputado?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/camara-expenses',
      {
        ano: payload?.ano,
        max_deputados: payload?.maxDeputados ?? 100,
        max_paginas_despesas_por_deputado: payload?.maxPaginasDespesasPorDeputado ?? 10,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncPncpContracts: async (payload: { dataInicial: string; dataFinal: string; maxPaginas?: number; tamanhoPagina?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/pncp-contracts',
      {
        data_inicial: payload.dataInicial,
        data_final: payload.dataFinal,
        max_paginas: payload.maxPaginas ?? 5,
        tamanho_pagina: payload.tamanhoPagina ?? 50,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncDonationsFromCsv: async (payload: { ano: number; csvUrl: string; maxLinhas?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/donations',
      {
        ano: payload.ano,
        csv_url: payload.csvUrl,
        max_linhas: payload.maxLinhas ?? 50000,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncAssetsFromCsv: async (payload: { ano: number; csvUrl: string; maxLinhas?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/assets',
      {
        ano: payload.ano,
        csv_url: payload.csvUrl,
        max_linhas: payload.maxLinhas ?? 50000,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncCandidatesFromCsv: async (payload: { ano: number; csvUrl: string; maxLinhas?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/candidates',
      {
        ano: payload.ano,
        csv_url: payload.csvUrl,
        max_linhas: payload.maxLinhas ?? 100000,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  syncTseAutoFromCkan: async (payload: { ano: number; maxLinhasDoacoes?: number; maxLinhasBens?: number; maxLinhasCandidatos?: number }) => {
    const response = await apiClient.post(
      '/fiscal-investigation/sync/tse-auto',
      {
        ano: payload.ano,
        max_linhas_doacoes: payload.maxLinhasDoacoes ?? 50000,
        max_linhas_bens: payload.maxLinhasBens ?? 50000,
        max_linhas_candidatos: payload.maxLinhasCandidatos ?? 100000,
      },
      { timeout: 240000 }
    );
    return response.data;
  },

  getFiscalPeopleRanking: async (
    limit: number = 5000,
    includeSemDados: boolean = false
  ): Promise<{ success: boolean; total: number; dados: FiscalPersonRanking[] }> => {
    const response = await apiClient.get(`/fiscal-investigation/people-ranking?limit=${limit}&include_sem_dados=${includeSemDados}`);
    return response.data;
  },

  getFiscalSyncStatus: async () => {
    const response = await apiClient.get('/fiscal-investigation/sync/status');
    return response.data;
  },

  getFiscalSourceDomains: async () => {
    const response = await apiClient.get('/fiscal-investigation/source-domains');
    return response.data;
  },

  getFiscalIntegrationsStatus: async () => {
    const response = await apiClient.get('/fiscal-investigation/integrations/status');
    return response.data;
  },

  analyzeCpf: async (cpf: string): Promise<{ success: boolean; report: RadarGovReport }> => {
    const response = await apiClient.get(`/fiscal-investigation/analyze/${cpf}`);
    return response.data;
  }
};
