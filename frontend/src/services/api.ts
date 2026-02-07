import axios, { AxiosResponse } from 'axios';
import { DeputadosResponse, VotacoesResponse, AnaliseDeputadoResponse } from '../types/api';

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
  }
};
