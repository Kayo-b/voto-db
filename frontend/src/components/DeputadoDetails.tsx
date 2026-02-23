import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { Deputado, DeputadoVotoAtividade } from '../types/api';

interface DeputadoDetailsProps {
  deputado: Deputado;
  onBack: () => void;
}

const DeputadoDetails: React.FC<DeputadoDetailsProps> = ({ deputado, onBack }) => {
  const PAGE_SIZE = 5;
  const [atividades, setAtividades] = useState<DeputadoVotoAtividade[]>([]);
  const [loadingInitial, setLoadingInitial] = useState<boolean>(false);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string>('');
  const [hasMore, setHasMore] = useState<boolean>(false);
  const [source, setSource] = useState<'db' | 'db_enriched' | null>(null);
  const [enrichmentInfo, setEnrichmentInfo] = useState<string>('');

  useEffect(() => {
    const controller = new AbortController();

    const fetchAtividadeInicial = async (): Promise<void> => {
      setLoadingInitial(true);
      setError('');
      setAtividades([]);
      setHasMore(false);
      setSource(null);
      setEnrichmentInfo('');

      try {
        const response = await api.getDeputadoVotosRecentes(deputado.id, PAGE_SIZE, 0);

        if (response.success) {
          setAtividades(response.data || []);
          setHasMore(Boolean(response.pagination?.has_more));
          setSource(response.source || null);

          const matched = response.enrichment?.matched_votacoes_for_deputado || 0;
          const newVotos = response.enrichment?.new_votos_stored || 0;
          if (matched > 0 || newVotos > 0) {
            setEnrichmentInfo(`${newVotos} votos salvos no banco local (${matched} votações do deputado encontradas nesta varredura).`);
          }
        } else {
          setError('Não foi possível carregar a atividade de votação do deputado.');
        }
      } catch (error) {
        if ((error as any)?.name !== 'CanceledError') {
          console.error('Erro ao carregar atividade:', error);
          setError('Erro na conexão. Tente novamente mais tarde.');
        }
      }

      if (!controller.signal.aborted) {
        setLoadingInitial(false);
      }
    };

    fetchAtividadeInicial();

    return () => {
      controller.abort();
    };
  }, [deputado.id]);

  const carregarMais = async (): Promise<void> => {
    if (loadingMore || !hasMore) return;

    setLoadingMore(true);
    setError('');

    try {
      const response = await api.getDeputadoVotosRecentes(deputado.id, PAGE_SIZE, atividades.length);
      if (response.success) {
        setAtividades((prev) => [...prev, ...(response.data || [])]);
        setHasMore(Boolean(response.pagination?.has_more));
      } else {
        setError('Não foi possível carregar mais votações.');
      }
    } catch (err) {
      console.error('Erro ao carregar mais votações:', err);
      setError('Erro ao carregar mais votações.');
    } finally {
      setLoadingMore(false);
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
            {deputado.id && (
              <p className="text-gray-500">ID: {deputado.id}</p>
            )}
          </div>
        </div>
      </div>
            
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <h2 className="text-2xl font-bold mb-2">Atividade Recente de Votação</h2>
        <p className="text-gray-600 text-sm mb-4">
          Últimas proposições votadas pelo deputado, com cache local incremental para consultas mais rápidas.
        </p>

        {source && (
          <div className="mb-4">
            <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${source === 'db' ? 'bg-blue-50 text-blue-700' : 'bg-green-50 text-green-700'}`}>
              {source === 'db' ? 'Dados do banco local' : 'Dados do banco local + API'}
            </span>
          </div>
        )}

        {enrichmentInfo && (
          <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded mb-4 text-sm">
            {enrichmentInfo}
          </div>
        )}

        {loadingInitial && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-gray-600">Escaneando atividade de votação...</p>
          </div>
        )}

        {error && (
          <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-4 py-3 rounded mb-4">
            <p className="font-semibold">ℹ️ Informação</p>
            <p>{error}</p>
            <p className="text-sm mt-2">
              A coleta depende da disponibilidade da API e do histórico já indexado localmente.
            </p>
          </div>
        )}

        {!loadingInitial && !error && atividades.length === 0 && (
          <div className="text-center py-8">
            <p className="text-gray-500 mb-2">
              Nenhuma atividade de votação encontrada para este deputado.
            </p>
            <p className="text-gray-400 text-sm">
              Isso pode ocorrer quando não há votos recentes já indexados ou quando a API não retornou registros no período escaneado.
            </p>
          </div>
        )}

        {!loadingInitial && atividades.length > 0 && (
          <div className="space-y-4">
            {atividades.map((votacao, index) => (
              <div
                key={index}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-2">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{votacao.proposicao_codigo}</h3>
                    <p className="text-gray-700">{votacao.titulo}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className="px-2 py-1 rounded-full text-xs font-medium text-slate-700 bg-slate-100">
                      {votacao.sigla_orgao || 'ORG'}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getVotoColor(votacao.voto)}`}>
                      {votacao.voto}
                    </span>
                  </div>
                </div>
                
                <div className="flex justify-between items-center text-sm text-gray-500">
                  <span>{formatDate(votacao.data)}</span>
                </div>
              </div>
            ))}

            {hasMore && (
              <div className="text-center mt-4">
                <button
                  onClick={carregarMais}
                  disabled={loadingMore}
                  className="bg-blue-600 text-white px-5 py-2 rounded hover:bg-blue-700 disabled:bg-blue-300"
                >
                  {loadingMore ? 'Carregando...' : 'Carregar mais'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default DeputadoDetails;
