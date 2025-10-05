import axios, { AxiosResponse } from 'axios';
import { DeputadosResponse, VotacoesResponse } from '../types/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8001';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
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

  analisarDeputado: async (id: number, incluirTodas: boolean = false) => {
    try {
      const response = await apiClient.get(
        `/deputados/${id}/analise${incluirTodas ? '?incluir_todas=true' : ''}`
      );
      return response.data;
    } catch (error) {
      console.error('Erro ao analisar deputado:', error);
      throw error;
    }
  }
};