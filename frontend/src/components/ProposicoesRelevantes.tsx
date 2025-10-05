import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface Proposicao {
  tipo: string;
  numero: string;
  titulo: string;
  relevancia: string;
  impacto: string;
  status?: string;
  data_aprovacao?: string;
}

interface ProposicoesRelevantesData {
  votacoes_historicas: Proposicao[];
  metadata: {
    total_proposicoes: number;
    periodo: string;
  };
}

const ProposicoesRelevantes: React.FC = () => {
  const [proposicoes, setProposicoes] = useState<Proposicao[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [filtroRelevancia, setFiltroRelevancia] = useState<string>('todas');

  useEffect(() => {
    const fetchProposicoes = async () => {
      try {
        setLoading(true);
        const response = await fetch('http://localhost:8001/proposicoes/relevantes');
        const result = await response.json();
        
        if (result.success && result.data.votacoes_historicas) {
          setProposicoes(result.data.votacoes_historicas);
        } else {
          setError('Erro ao carregar proposições');
        }
      } catch (err) {
        setError('Erro na conexão com a API');
        console.error('Erro:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchProposicoes();
  }, []);

  const proposicoesFiltradas = proposicoes.filter(prop => 
    filtroRelevancia === 'todas' || prop.relevancia === filtroRelevancia
  );

  const getRelevanciaColor = (relevancia: string): string => {
    switch (relevancia) {
      case 'alta':
        return 'text-red-600 bg-red-100';
      case 'média':
        return 'text-yellow-600 bg-yellow-100';
      case 'baixa':
        return 'text-green-600 bg-green-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getStatusColor = (status?: string): string => {
    if (!status) return 'text-gray-600 bg-gray-100';
    
    if (status.includes('Aprovado') || status.includes('Lei')) {
      return 'text-green-600 bg-green-100';
    } else if (status.includes('tramitação')) {
      return 'text-blue-600 bg-blue-100';
    } else {
      return 'text-gray-600 bg-gray-100';
    }
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando proposições relevantes...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Proposições Relevantes</h1>
        <p className="text-gray-600">
          Análise de {proposicoes.length} proposições de alta relevância social e política
        </p>
      </div>

      {/* Filtros */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Filtrar por relevância:
        </label>
        <select
          value={filtroRelevancia}
          onChange={(e) => setFiltroRelevancia(e.target.value)}
          className="border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="todas">Todas</option>
          <option value="alta">Alta</option>
          <option value="média">Média</option>
          <option value="baixa">Baixa</option>
        </select>
      </div>

      {/* Lista de Proposições */}
      <div className="space-y-4">
        {proposicoesFiltradas.map((proposicao, index) => (
          <div
            key={index}
            className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <h3 className="text-xl font-semibold">
                    {proposicao.tipo} {proposicao.numero}
                  </h3>
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRelevanciaColor(proposicao.relevancia)}`}>
                    {proposicao.relevancia}
                  </span>
                  {proposicao.status && (
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(proposicao.status)}`}>
                      {proposicao.status}
                    </span>
                  )}
                </div>
                <h4 className="text-lg font-medium text-gray-800 mb-2">
                  {proposicao.titulo}
                </h4>
                <p className="text-gray-600 mb-3">
                  {proposicao.impacto}
                </p>
                {proposicao.data_aprovacao && (
                  <p className="text-sm text-gray-500">
                    Aprovado em: {new Date(proposicao.data_aprovacao).toLocaleDateString('pt-BR')}
                  </p>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {proposicoesFiltradas.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">
            Nenhuma proposição encontrada com o filtro selecionado.
          </p>
        </div>
      )}

            <div className="mt-8 bg-blue-50 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Estatísticas</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {proposicoes.filter(p => p.relevancia === 'alta').length}
            </div>
            <div className="text-sm text-gray-600">Alta Relevância</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-yellow-600">
              {proposicoes.filter(p => p.relevancia === 'média').length}
            </div>
            <div className="text-sm text-gray-600">Média Relevância</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {proposicoes.filter(p => p.data_aprovacao).length}
            </div>
            <div className="text-sm text-gray-600">Aprovadas</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProposicoesRelevantes;