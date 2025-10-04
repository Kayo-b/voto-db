import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Deputado, Votacao } from '../types/api';

interface DeputadoDetailsProps {
  deputado: Deputado;
  onBack: () => void;
}

const DeputadoDetails: React.FC<DeputadoDetailsProps> = ({ deputado, onBack }) => {
  const [votacoes, setVotacoes] = useState<Votacao[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    const fetchVotacoes = async (): Promise<void> => {
      setLoading(true);
      setError('');
      try {
        const response = await api.getDeputadoVotacoes(deputado.id);
        setVotacoes(response.dados || []);
      } catch (error) {
        console.error('Erro ao buscar votações:', error);
        setError('Erro ao buscar votações. Tente novamente.');
      }
      setLoading(false);
    };

    fetchVotacoes();
  }, [deputado.id]);

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

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('pt-BR');
  };

  return (
    <div className="p-4">
      <button
        onClick={onBack}
        className="mb-4 bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600"
      >
        ← Voltar
      </button>

      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-center gap-4">
          {deputado.urlFoto && (
            <img
              src={deputado.urlFoto}
              alt={deputado.nome}
              className="w-20 h-20 rounded-full object-cover"
            />
          )}
          <div>
            <h1 className="text-3xl font-bold">{deputado.nome}</h1>
            <p className="text-xl text-gray-600">{deputado.siglaPartido} - {deputado.siglaUf}</p>
            {deputado.email && (
              <p className="text-gray-500">{deputado.email}</p>
            )}
          </div>
        </div>
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-4">Votações Recentes</h2>
        
        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">Carregando votações...</p>
          </div>
        )}

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        {!loading && !error && votacoes.length === 0 && (
          <p className="text-gray-500 text-center py-8">
            Nenhuma votação encontrada.
          </p>
        )}

        {!loading && votacoes.length > 0 && (
          <div className="space-y-4">
            {votacoes.slice(0, 10).map((votacao) => (
              <div
                key={votacao.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-semibold text-lg">
                    {votacao.proposicao.siglaTipo} {votacao.proposicao.numero}/{votacao.proposicao.ano}
                  </h3>
                  <span
                    className={`px-3 py-1 rounded-full text-sm font-medium ${getVotoColor(votacao.voto)}`}
                  >
                    {votacao.voto}
                  </span>
                </div>
                
                <p className="text-gray-700 mb-2">{votacao.proposicao.ementa}</p>
                
                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>{votacao.siglaOrgao}</span>
                  <span>{formatDate(votacao.data)}</span>
                </div>
              </div>
            ))}
            
            {votacoes.length > 10 && (
              <p className="text-center text-gray-500 mt-4">
                Mostrando 10 de {votacoes.length} votações
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DeputadoDetails;