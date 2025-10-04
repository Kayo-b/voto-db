import axios, { AxiosResponse } from 'axios';
import { DeputadosResponse, VotacoesResponse } from '../types/api';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
});

export const api = {
  searchDeputados: async (nome?: string): Promise<DeputadosResponse> => {
    const response: AxiosResponse<DeputadosResponse> = await apiClient.get(
      `/deputados${nome ? `?nome=${nome}` : ''}`
    );
    return response.data;
  },
  
  getDeputadoVotacoes: async (id: number): Promise<VotacoesResponse> => {
    const response: AxiosResponse<VotacoesResponse> = await apiClient.get(
      `/deputados/${id}/votacoes`
    );
    return response.data;
  }
};