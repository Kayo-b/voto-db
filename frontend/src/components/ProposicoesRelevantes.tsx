import React, { useState, useEffect } from 'react';
import { api } from '../services/api';

interface ProposicaoStats {
  total_votacoes: number;
  votacoes_nominais: number;
  ultima_votacao?: string | null;
}

interface Proposicao {
  id?: number;
  tipo: string;
  numero: string;
  ano?: number;
  titulo: string;
  relevancia: string;
  ementa?: string;
  status?: string;
  em_votacao?: boolean;
  stats?: ProposicaoStats;
}

const ProposicoesRelevantes: React.FC = () => {
  const [proposicoes, setProposicoes] = useState<Proposicao[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [filtroRelevancia, setFiltroRelevancia] = useState<string>('todas');
  const [filtroEmVotacao, setFiltroEmVotacao] = useState<boolean>(false);
  const [ultimaSincronizacao, setUltimaSincronizacao] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string>('not_started');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  // Form states
  const [showForm, setShowForm] = useState<boolean>(false);
  const [formCodigo, setFormCodigo] = useState<string>('');
  const [formTitulo, setFormTitulo] = useState<string>('');
  const [formRelevancia, setFormRelevancia] = useState<string>('média');
  const [isValidating, setIsValidating] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string>('');
  const [formSuccess, setFormSuccess] = useState<string>('');
  const [validationInfo, setValidationInfo] = useState<any>(null);

  const fetchProposicoes = async () => {
    try {
      setLoading(true);
      const result = await api.getProposicoesMonitoradas({ limit: 200 });

      if (result.success && result.data?.proposicoes) {
        setProposicoes(result.data.proposicoes);
        setUltimaSincronizacao(result.data.metadata?.ultima_sincronizacao || null);
        setSyncStatus(result.data.metadata?.status_ultima_sincronizacao || 'unknown');
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

  useEffect(() => {
    fetchProposicoes();
  }, []);

  const handleSyncNow = async () => {
    try {
      setIsSyncing(true);
      await api.syncProposicoesMonitoradas();
      await fetchProposicoes();
    } catch (err) {
      console.error('Erro ao sincronizar:', err);
      alert('Erro ao sincronizar proposições');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleValidate = async () => {
    if (!formCodigo.trim()) {
      setFormError('Digite o código da proposição (ex: PL 6787/2016)');
      return;
    }

    setIsValidating(true);
    setFormError('');
    setValidationInfo(null);

    try {
      const result = await api.validateProposicao(formCodigo);

      if (result.success) {
        setValidationInfo(result.data);
        setFormError('');
        if (result.data.titulo && !formTitulo) {
          setFormTitulo(result.data.titulo);
        }
      } else {
        setFormError(result.error || 'Proposição inválida');
        setValidationInfo(null);
      }
    } catch (err: any) {
      setFormError(err.response?.data?.error || 'Erro ao validar proposição');
      setValidationInfo(null);
    } finally {
      setIsValidating(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formCodigo.trim()) {
      setFormError('Digite o código da proposição');
      return;
    }

    setIsSubmitting(true);
    setFormError('');
    setFormSuccess('');

    try {
      const result = await api.addProposicaoRelevante(
        formCodigo,
        formTitulo || undefined,
        formRelevancia
      );

      if (result.success) {
        setFormSuccess('Proposição adicionada com sucesso!');
        setFormCodigo('');
        setFormTitulo('');
        setFormRelevancia('média');
        setValidationInfo(null);

        await fetchProposicoes();

        setTimeout(() => {
          setShowForm(false);
          setFormSuccess('');
        }, 2000);
      } else {
        setFormError(result.error || 'Erro ao adicionar proposição');
      }
    } catch (err: any) {
      setFormError(err.response?.data?.error || 'Erro ao adicionar proposição');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!window.confirm('Tem certeza que deseja remover esta proposição?')) {
      return;
    }

    try {
      const result = await api.deleteProposicaoRelevante(id);

      if (result.success) {
        await fetchProposicoes();
      } else {
        alert('Erro ao remover proposição');
      }
    } catch (err) {
      alert('Erro ao remover proposição');
      console.error('Erro:', err);
    }
  };

  const proposicoesFiltradas = proposicoes.filter((prop) => {
    const matchesRelevancia = filtroRelevancia === 'todas' || prop.relevancia === filtroRelevancia;
    const matchesEmVotacao = !filtroEmVotacao || !!prop.em_votacao;
    return matchesRelevancia && matchesEmVotacao;
  });

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

    if (status.includes('votação')) {
      return 'text-blue-700 bg-blue-100';
    }
    return 'text-gray-600 bg-gray-100';
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Carregando proposições monitoradas...</p>
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
      <div className="mb-6 flex justify-between items-start gap-4">
        <div>
          <h1 className="text-3xl font-bold mb-2">Proposições Monitoradas</h1>
          <p className="text-gray-600">
            Lista automática com {proposicoes.length} proposições e estatísticas de votação.
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Sync automático a cada 15 minutos. Última sincronização: {ultimaSincronizacao ? new Date(ultimaSincronizacao).toLocaleString('pt-BR') : 'ainda não executada'} ({syncStatus})
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleSyncNow}
            disabled={isSyncing}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-medium transition-colors disabled:bg-indigo-300"
          >
            {isSyncing ? 'Sincronizando...' : 'Sincronizar Agora'}
          </button>
          <button
            onClick={() => setShowForm(!showForm)}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {showForm ? 'Cancelar' : '+ Adicionar Proposição'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="mb-6 bg-white border border-gray-200 rounded-lg p-6 shadow-sm">
          <h2 className="text-xl font-semibold mb-4">Adicionar Nova Proposição</h2>

          <form onSubmit={handleSubmit}>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Código da Proposição *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={formCodigo}
                    onChange={(e) => setFormCodigo(e.target.value)}
                    placeholder="Ex: PL 6787/2016"
                    className="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <button
                    type="button"
                    onClick={handleValidate}
                    disabled={isValidating}
                    className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded font-medium transition-colors disabled:bg-gray-400"
                  >
                    {isValidating ? 'Validando...' : 'Validar'}
                  </button>
                </div>
              </div>

              {validationInfo && (
                <div className="bg-green-50 border border-green-200 rounded p-4">
                  <p className="text-green-800 font-medium mb-2">✓ Proposição válida encontrada!</p>
                  <p className="text-sm text-gray-700 mb-1">
                    <strong>Votações Nominais:</strong> {validationInfo.total_votacoes_nominais}
                  </p>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Título (opcional)
                </label>
                <input
                  type="text"
                  value={formTitulo}
                  onChange={(e) => setFormTitulo(e.target.value)}
                  placeholder="Título personalizado da proposição"
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Relevância
                </label>
                <select
                  value={formRelevancia}
                  onChange={(e) => setFormRelevancia(e.target.value)}
                  className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="alta">Alta</option>
                  <option value="média">Média</option>
                  <option value="baixa">Baixa</option>
                </select>
              </div>

              {formError && (
                <div className="bg-red-50 border border-red-200 rounded p-3">
                  <p className="text-red-800 text-sm">{formError}</p>
                </div>
              )}

              {formSuccess && (
                <div className="bg-green-50 border border-green-200 rounded p-3">
                  <p className="text-green-800 text-sm">{formSuccess}</p>
                </div>
              )}

              <div className="flex gap-2 pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting || !validationInfo}
                  className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium transition-colors disabled:bg-blue-300"
                >
                  {isSubmitting ? 'Adicionando...' : 'Adicionar Proposição'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setShowForm(false);
                    setFormCodigo('');
                    setFormTitulo('');
                    setFormRelevancia('média');
                    setFormError('');
                    setFormSuccess('');
                    setValidationInfo(null);
                  }}
                  className="bg-gray-200 hover:bg-gray-300 text-gray-700 px-6 py-2 rounded font-medium transition-colors"
                >
                  Cancelar
                </button>
              </div>
            </div>
          </form>
        </div>
      )}

      <div className="mb-6 flex gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Filtrar por relevância:</label>
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

        <label className="inline-flex items-center gap-2 text-sm text-gray-700 pb-2">
          <input
            type="checkbox"
            checked={filtroEmVotacao}
            onChange={(e) => setFiltroEmVotacao(e.target.checked)}
            className="rounded border-gray-300"
          />
          Somente em votação
        </label>
      </div>

      <div className="space-y-4">
        {proposicoesFiltradas.map((proposicao, index) => (
          <div
            key={proposicao.id || index}
            className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white"
          >
            <div className="flex justify-between items-start mb-3">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <h3 className="text-xl font-semibold">
                    {proposicao.tipo} {proposicao.numero}/{proposicao.ano}
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
                <h4 className="text-lg font-medium text-gray-800 mb-2">{proposicao.titulo}</h4>
                <p className="text-gray-600 mb-3">{proposicao.ementa || 'Sem ementa disponível.'}</p>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
                  <div className="bg-gray-50 rounded p-3">
                    <div className="text-gray-500">Total de votações</div>
                    <div className="font-semibold text-gray-800">{proposicao.stats?.total_votacoes ?? 0}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="text-gray-500">Votações nominais</div>
                    <div className="font-semibold text-gray-800">{proposicao.stats?.votacoes_nominais ?? 0}</div>
                  </div>
                  <div className="bg-gray-50 rounded p-3">
                    <div className="text-gray-500">Última votação</div>
                    <div className="font-semibold text-gray-800">
                      {proposicao.stats?.ultima_votacao
                        ? new Date(proposicao.stats.ultima_votacao).toLocaleString('pt-BR')
                        : 'Sem registro'}
                    </div>
                  </div>
                </div>
              </div>

              {proposicao.id && (
                <button
                  onClick={() => handleDelete(proposicao.id!)}
                  className="ml-4 text-red-600 hover:text-red-800 hover:bg-red-50 p-2 rounded transition-colors"
                  title="Remover proposição"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {proposicoesFiltradas.length === 0 && (
        <div className="text-center py-8">
          <p className="text-gray-500">Nenhuma proposição encontrada com o filtro selecionado.</p>
        </div>
      )}

      <div className="mt-8 bg-blue-50 p-6 rounded-lg">
        <h3 className="text-lg font-semibold mb-4">Estatísticas</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{proposicoes.length}</div>
            <div className="text-sm text-gray-600">Total Monitoradas</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{proposicoes.filter((p) => p.relevancia === 'alta').length}</div>
            <div className="text-sm text-gray-600">Alta Relevância</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-indigo-600">{proposicoes.filter((p) => p.em_votacao).length}</div>
            <div className="text-sm text-gray-600">Em Votação</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{proposicoes.reduce((acc, p) => acc + (p.stats?.votacoes_nominais || 0), 0)}</div>
            <div className="text-sm text-gray-600">Votações Nominais</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProposicoesRelevantes;
