import React, { useState } from 'react';

interface AnaliseDeputado {
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

interface AnaliseAvancadaProps {
  deputadoId?: number;
}

const AnaliseAvancada: React.FC<AnaliseAvancadaProps> = ({ deputadoId }) => {
  const [deputadoInput, setDeputadoInput] = useState<string>(deputadoId?.toString() || '');
  const [analise, setAnalise] = useState<AnaliseDeputado | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  const analisarDeputado = async (incluirTodas: boolean = false) => {
    if (!deputadoInput.trim()) {
      setError('Digite o ID do deputado');
      return;
    }

    try {
      setLoading(true);
      setError('');
      
      const url = `http://localhost:8001/deputados/${deputadoInput}/analise${incluirTodas ? '?incluir_todas=true' : ''}`;
      const response = await fetch(url);
      const result = await response.json();

      if (result.success) {
        setAnalise(result.data);
        // console.log(result.dat.deputado, 'DATA');
      } else {
        setError(result.message || 'Erro na análise do deputado');
      }
    } catch (err) {
      setError('Erro na conexão com a API');
      console.error('Erro:', err);
    } finally {
      setLoading(false);
    }
  };

  const getVotoColor = (voto: string): string => {
    switch (voto.toLowerCase()) {
      case 'sim':
        return 'text-green-600 bg-green-100';
      case 'não':
      case 'nao':
        return 'text-red-600 bg-red-100';
      case 'abstenção':
      case 'abstencao':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getRelevanciaColor = (relevancia: string): string => {
    switch (relevancia) {
      case 'alta':
        return 'text-red-600 bg-red-100';
      case 'média':
        return 'text-yellow-600 bg-yellow-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Análise Avançada de Deputado</h1>
        <p className="text-gray-600">
          Análise do perfil de votação em proposições de alta relevância
        </p>
      </div>


      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex gap-4 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ID do Deputado
            </label>
            <input
              type="number"
              value={deputadoInput}
              onChange={(e) => setDeputadoInput(e.target.value)}
              placeholder="Ex: 178864"
              className="border border-gray-300 rounded px-3 py-2 w-full focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <p className="text-xs text-gray-500 mt-1">
              Use a busca de deputados para encontrar o ID
            </p>
          </div>
          <button
            onClick={() => analisarDeputado(false)}
            disabled={loading}
            className="bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:bg-blue-300"
          >
            {loading ? 'Analisando...' : 'Análise Rápida'}
          </button>
          <button
            onClick={() => analisarDeputado(true)}
            disabled={loading}
            className="bg-green-500 text-white px-6 py-2 rounded hover:bg-green-600 disabled:bg-green-300"
          >
            {loading ? 'Analisando...' : 'Análise Completa'}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          <strong>Análise Rápida:</strong> Usa dados em cache | 
          <strong> Análise Completa:</strong> Processa proposições em tempo real (mais lenta)
        </p>
      </div>

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">
            Processando análise... Isso pode levar alguns segundos.
          </p>
        </div>
      )}
      {analise && (
        <div className="space-y-6">

          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h2 className="text-2xl font-bold mb-4">Perfil do Deputado</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h3 className="font-semibold text-lg">{analise.deputado.nome_parlamentar}</h3>
                <p className="text-gray-600">{analise.deputado.nome}</p>
                <p className="text-gray-600">
                  {analise.deputado.partido} - {analise.deputado.uf}
                </p>
                <p className="text-sm text-gray-500">
                  ID: {analise.deputado.id} | Status: {analise.deputado.situacao}
                </p>
              </div>
              

              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {analise.estatisticas.presenca_percentual}%
                  </div>
                  <div className="text-sm text-gray-600">Presença</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {analise.estatisticas.participacao}
                  </div>
                  <div className="text-sm text-gray-600">Votações</div>
                </div>
              </div>
            </div>
          </div>


          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-semibold mb-4">Estatísticas de Votação</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded">
                <div className="text-lg font-bold text-gray-800">
                  {analise.estatisticas.total_votacoes_analisadas}
                </div>
                <div className="text-sm text-gray-600">Total Analisadas</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <div className="text-lg font-bold text-green-600">
                  {analise.estatisticas.votos_favoraveis}
                </div>
                <div className="text-sm text-gray-600">Votos Favoráveis</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <div className="text-lg font-bold text-red-600">
                  {analise.estatisticas.votos_contrarios}
                </div>
                <div className="text-sm text-gray-600">Votos Contrários</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded">
                <div className="text-lg font-bold text-blue-600">
                  {analise.estatisticas.participacao}
                </div>
                <div className="text-sm text-gray-600">Participação</div>
              </div>
            </div>
          </div>


          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h3 className="text-xl font-semibold mb-4">Histórico de Votações</h3>
            
            {analise.historico_votacoes.length === 0 ? (
              <p className="text-gray-500 text-center py-4">
                Não há dados de votações disponíveis para este deputado.
              </p>
            ) : (
              <div className="space-y-4">
                {analise.historico_votacoes.map((votacao, index) => (
                  <div
                    key={index}
                    className="border border-gray-200 rounded p-4 hover:bg-gray-50 transition-colors"
                  >
                    <div className="flex justify-between items-start mb-2">
                      <div className="flex-1">
                        <h4 className="font-semibold text-lg">{votacao.proposicao}</h4>
                        <p className="text-gray-700">{votacao.titulo}</p>
                        <p className="text-sm text-gray-500">
                          {new Date(votacao.data).toLocaleDateString('pt-BR')}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <span className={`px-2 py-1 rounded-full text-sm font-medium ${getRelevanciaColor(votacao.relevancia)}`}>
                          {votacao.relevancia}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getVotoColor(votacao.voto)}`}>
                          {votacao.voto}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default AnaliseAvancada;