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
        
        if (response.success === false && response.dados.length === 0) {
          setError('Não foi possível carregar as votações recentes. Dados podem não estar disponíveis.');
          setVotacoes([]);
        } else {
          setVotacoes(response.dados || []);
          if (response.cached) {
            console.log('Dados carregados do cache');
          }
        }
      } catch (error) {
        console.error('Erro ao buscar votações:', error);
        setError('Erro na conexão. Tente novamente mais tarde.');
        setVotacoes([]);
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
        <h2 className="text-2xl font-bold mb-2">Votações em Proposições Relevantes</h2>
        <p className="text-gray-600 text-sm mb-4">
          Histórico de votações do deputado em proposições de alta relevância social e política
        </p>
        
        {loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">Carregando votações relevantes...</p>
          </div>
        )}

        {error && (
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
            <p className="font-semibold">ℹ️ Informação</p>
            <p>{error}</p>
            <p className="text-sm mt-2">
              As votações são baseadas em proposições pré-selecionadas de alta relevância. 
              Dados podem não estar disponíveis para todos os deputados.
            </p>
          </div>
        )}

        {!loading && !error && votacoes.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-2">
              Não há registros de votações deste deputado nas proposições relevantes analisadas.
            </p>
            <p className="text-gray-400 text-sm">
              Isso pode ocorrer se o deputado não participou das votações principais ou 
              se os dados ainda não foram processados.
            </p>
          </div>
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