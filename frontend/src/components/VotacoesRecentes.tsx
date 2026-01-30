import React, { useState } from 'react';
import { api } from '../services/api';

interface Votacao {
  id: string;
  data: string;
  dataHoraRegistro: string;
  descricao: string;
  siglaOrgao: string;
  proposicao?: {
    id: number;
    siglaTipo: string;
    numero: number;
    ano: number;
    ementa: string;
  };
  aprovacao?: number;
  ultimaAberturaVotacao?: {
    descricao: string;
  };
  source?: 'db' | 'api';
  tipo_votacao?: string;
  votos_count?: number;
}

interface Voto {
  deputado: {
    id: number;
    nome: string;
    siglaPartido: string;
    siglaUf: string;
  };
  voto: string;
}

interface VotosResponse {
  success: boolean;
  data: Voto[];
  total: number;
  source?: 'db' | 'api';
}

interface VotacoesResponse {
  success: boolean;
  data: Votacao[];
  total: number;
  stats?: {
    from_db: number;
    from_api: number;
    new_stored: number;
    votos_updated?: number;
  };
}

const VotacoesRecentes: React.FC = () => {
  const [periodo, setPeriodo] = useState<'24h' | '7dias'>('24h');
  const [tipoConsulta, setTipoConsulta] = useState<'urgencia' | 'nominais' | 'todas'>('nominais');
  const [votacoes, setVotacoes] = useState<Votacao[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [votosDetalhados, setVotosDetalhados] = useState<{[key: string]: Voto[]}>({});
  const [loadingVotos, setLoadingVotos] = useState<{[key: string]: boolean}>({});
  const [mostrarVotos, setMostrarVotos] = useState<{[key: string]: boolean}>({});
  const [votosSource, setVotosSource] = useState<{[key: string]: 'db' | 'api'}>({});
  const [searchStats, setSearchStats] = useState<{from_db: number; from_api: number; new_stored: number; votos_updated?: number} | null>(null);

  const buscarVotacoes = async () => {
    setLoading(true);
    setError('');

    try {
      const dias = periodo === '24h' ? 1 : 7;
      const response: VotacoesResponse = await api.buscarVotacoesRecentes(dias, tipoConsulta);

      if (response.success) {
        setVotacoes(response.data || []);
        setSearchStats(response.stats || null);
      } else {
        setError((response as any).message || 'Erro ao buscar votações');
      }
    } catch (err: any) {
      setError('Erro na conexão com a API');
      console.error('Erro:', err);
    } finally {
      setLoading(false);
    }
  };

  const buscarVotosDetalhados = async (votacaoId: string) => {
    if (votosDetalhados[votacaoId]) {
      // Se já tem os votos, apenas toggle mostrar/ocultar
      setMostrarVotos(prev => ({ ...prev, [votacaoId]: !prev[votacaoId] }));
      return;
    }

    setLoadingVotos(prev => ({ ...prev, [votacaoId]: true }));

    try {
      const response: VotosResponse = await api.buscarVotosVotacao(votacaoId);

      if (response.success) {
        setVotosDetalhados(prev => ({ ...prev, [votacaoId]: response.data }));
        setMostrarVotos(prev => ({ ...prev, [votacaoId]: true }));
        if (response.source) {
          setVotosSource(prev => ({ ...prev, [votacaoId]: response.source! }));
        }
      } else {
        alert('Erro ao buscar votos');
      }
    } catch (err: any) {
      console.error('Erro ao buscar votos:', err);
      alert('Erro ao buscar votos da votação');
    } finally {
      setLoadingVotos(prev => ({ ...prev, [votacaoId]: false }));
    }
  };

  const adicionarProposicao = async (votacao: Votacao) => {
    if (!votacao.proposicao) {
      alert('Esta votação não possui proposição associada');
      return;
    }

    const prop = votacao.proposicao;
    const codigo = `${prop.siglaTipo} ${prop.numero}/${prop.ano}`;
    
    if (!window.confirm(`Adicionar ${codigo} às proposições relevantes?`)) {
      return;
    }

    try {
      const result = await api.addProposicaoRelevante(codigo, undefined, 'média');
      
      if (result.success) {
        alert('✓ Proposição adicionada com sucesso!');
      } else {
        alert(`Erro: ${result.error || 'Não foi possível adicionar'}`);
      }
    } catch (err: any) {
      alert(`Erro: ${err.response?.data?.error || 'Erro ao adicionar proposição'}`);
    }
  };

  const formatarData = (dataStr: string) => {
    try {
      const data = new Date(dataStr);
      return data.toLocaleString('pt-BR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dataStr;
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold mb-2">Votações Recentes</h1>
        <p className="text-gray-600">
          Monitore as últimas votações da Câmara dos Deputados
        </p>
      </div>

      {/* Filtros */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Tipo de Votação
            </label>
            <select
              value={tipoConsulta}
              onChange={(e) => setTipoConsulta(e.target.value as 'urgencia' | 'nominais' | 'todas')}
              className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="nominais">Votações Nominais</option>
              <option value="urgencia">Regime de Urgência</option>
              <option value="todas">Todas as Votações</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Período
            </label>
            <select
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value as '24h' | '7dias')}
              className="w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="24h">Últimas 24 horas</option>
              <option value="7dias">Últimos 7 dias</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={buscarVotacoes}
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded font-medium transition-colors disabled:bg-blue-300"
            >
              {loading ? 'Buscando...' : 'Buscar Votações'}
            </button>
          </div>
        </div>

        {tipoConsulta === 'urgencia' && (
          <p className="text-xs text-gray-500 mt-2">
            Regime de urgência: proposições que tramitam em caráter prioritário
          </p>
        )}
        {tipoConsulta === 'nominais' && (
          <p className="text-xs text-gray-500 mt-2">
            Votações nominais: cada deputado registra seu voto individualmente
          </p>
        )}
        {tipoConsulta === 'todas' && (
          <p className="text-xs text-gray-500 mt-2">
            Todas as votações: inclui nominais, urgência e simbólicas
          </p>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p className="mt-4 text-gray-600">Buscando votações...</p>
        </div>
      )}

      {/* Results */}
      {!loading && votacoes.length > 0 && (
        <div>
          <div className="mb-4 flex justify-between items-center">
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl font-semibold">
                {votacoes.length} votação(ões) encontrada(s)
              </h2>
              {searchStats && (
                <div className="flex gap-2">
                  {searchStats.from_db > 0 && (
                    <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                      {searchStats.from_db} do banco local
                    </span>
                  )}
                  {searchStats.from_api > 0 && (
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                      {searchStats.from_api} novas da API
                    </span>
                  )}
                  {searchStats.new_stored > 0 && (
                    <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded">
                      +{searchStats.new_stored} salvas
                    </span>
                  )}
                  {searchStats.votos_updated !== undefined && searchStats.votos_updated > 0 && (
                    <span className="text-xs bg-orange-100 text-orange-700 px-2 py-1 rounded">
                      {searchStats.votos_updated} votos atualizados
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>

          <div className="space-y-4">
            {votacoes.map((votacao) => (
              <div
                key={votacao.id}
                className="border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow bg-white"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    {/* Header */}
                    <div className="flex items-center gap-3 mb-3">
                      <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
                        {votacao.siglaOrgao}
                      </span>
                      <span className="text-sm text-gray-500">
                        {formatarData(votacao.dataHoraRegistro || votacao.data)}
                      </span>
                      {votacao.source === 'db' && (
                        <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs">
                          Banco Local
                        </span>
                      )}
                      {votacao.source === 'api' && (
                        <span className="px-2 py-0.5 bg-green-50 text-green-600 rounded text-xs">
                          Nova
                        </span>
                      )}
                      {votacao.votos_count !== undefined && votacao.votos_count > 0 && (
                        <span className="px-2 py-0.5 bg-purple-50 text-purple-600 rounded text-xs" title="Votos armazenados no banco local">
                          {votacao.votos_count} votos
                        </span>
                      )}
                    </div>

                    {/* Proposição */}
                    {votacao.proposicao && (
                      <div className="mb-3">
                        <h3 className="text-lg font-semibold mb-1">
                          {votacao.proposicao.siglaTipo} {votacao.proposicao.numero}/{votacao.proposicao.ano}
                        </h3>
                        <p className="text-gray-700">
                          {votacao.proposicao.ementa}
                        </p>
                      </div>
                    )}

                    {/* Descrição */}
                    <p className="text-gray-600 mb-2">
                      {votacao.descricao || votacao.ultimaAberturaVotacao?.descricao || 'Sem descrição'}
                    </p>

                    {/* Aprovação */}
                    {votacao.aprovacao !== undefined && (
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium">Resultado:</span>
                        <span className={`px-2 py-1 rounded text-sm ${
                          votacao.aprovacao === 1 
                            ? 'bg-green-100 text-green-800' 
                            : votacao.aprovacao === 0 
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {votacao.aprovacao === 1 ? 'Aprovado' : votacao.aprovacao === 0 ? 'Rejeitado' : 'Pendente'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  <div className="ml-4 flex gap-2">
                    <button
                      onClick={() => buscarVotosDetalhados(votacao.id)}
                      disabled={loadingVotos[votacao.id]}
                      className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium transition-colors disabled:bg-blue-300"
                      title="Ver quem votou"
                    >
                      {loadingVotos[votacao.id] ? 'Carregando...' : mostrarVotos[votacao.id] ? 'Ocultar Votos' : 'Ver Detalhes'}
                    </button>
                    
                    {votacao.proposicao && (
                      <button
                        onClick={() => adicionarProposicao(votacao)}
                        className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded font-medium transition-colors"
                        title="Adicionar às proposições relevantes"
                      >
                        + Adicionar
                      </button>
                    )}
                  </div>
                </div>

                {/* Detalhes dos Votos */}
                {mostrarVotos[votacao.id] && votosDetalhados[votacao.id] && (
                  <div className="mt-4 border-t pt-4">
                    <div className="flex items-center gap-3 mb-3">
                      <h4 className="font-semibold text-lg">Detalhes da Votação</h4>
                      {votosSource[votacao.id] === 'db' && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
                          Cache local
                        </span>
                      )}
                      {votosSource[votacao.id] === 'api' && (
                        <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          API
                        </span>
                      )}
                    </div>
                    
                    {/* Resumo */}
                    <div className="grid grid-cols-4 gap-4 mb-4">
                      {Object.entries(
                        votosDetalhados[votacao.id].reduce((acc: any, voto: Voto) => {
                          acc[voto.voto] = (acc[voto.voto] || 0) + 1;
                          return acc;
                        }, {})
                      ).map(([tipoVoto, quantidade]) => (
                        <div key={tipoVoto} className={`p-3 rounded ${
                          tipoVoto === 'Sim' ? 'bg-green-100' :
                          tipoVoto === 'Não' ? 'bg-red-100' :
                          tipoVoto === 'Abstenção' ? 'bg-yellow-100' :
                          'bg-gray-100'
                        }`}>
                          <div className="text-sm font-medium">{tipoVoto}</div>
                          <div className="text-2xl font-bold">{quantidade as number}</div>
                        </div>
                      ))}
                    </div>

                    {/* Lista de Deputados */}
                    <div className="max-h-96 overflow-y-auto">
                      <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50 sticky top-0">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Deputado</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Partido</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">UF</th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Voto</th>
                          </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                          {votosDetalhados[votacao.id].map((voto: Voto, idx: number) => (
                            <tr key={idx} className="hover:bg-gray-50">
                              <td className="px-4 py-2 text-sm">{voto.deputado.nome}</td>
                              <td className="px-4 py-2 text-sm">{voto.deputado.siglaPartido}</td>
                              <td className="px-4 py-2 text-sm">{voto.deputado.siglaUf}</td>
                              <td className="px-4 py-2">
                                <span className={`px-2 py-1 rounded text-xs font-medium ${
                                  voto.voto === 'Sim' ? 'bg-green-100 text-green-800' :
                                  voto.voto === 'Não' ? 'bg-red-100 text-red-800' :
                                  voto.voto === 'Abstenção' ? 'bg-yellow-100 text-yellow-800' :
                                  'bg-gray-100 text-gray-800'
                                }`}>
                                  {voto.voto}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && votacoes.length === 0 && (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500 text-lg">
            Clique em "Buscar Votações" para ver os resultados
          </p>
        </div>
      )}
    </div>
  );
};

export default VotacoesRecentes;
