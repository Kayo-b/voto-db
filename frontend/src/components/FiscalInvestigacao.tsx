import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { FiscalOverview, FiscalPersonRanking, FiscalSource, RadarGovInsight, RadarGovReport, RadarGovTimelineEvent } from '../types/api';

type DashboardTab = 'insights' | 'detalhe';
type SeverityFilter = 'Todos' | 'Crítico' | 'Alto' | 'Médio' | 'Baixo';
type TimelineCategory = 'JURÍDICO' | 'EMPRESA' | 'PESSOA' | 'AMBIENTAL' | 'FINANCEIRO' | 'REGULATÓRIO' | 'SAÚDE' | 'CONTRATO';

const categoryStyle: Record<TimelineCategory, string> = {
  'JURÍDICO': 'text-amber-700 border-amber-200 bg-amber-50',
  'EMPRESA': 'text-orange-700 border-orange-200 bg-orange-50',
  'PESSOA': 'text-yellow-700 border-yellow-200 bg-yellow-50',
  'AMBIENTAL': 'text-teal-700 border-teal-200 bg-teal-50',
  'FINANCEIRO': 'text-blue-700 border-blue-200 bg-blue-50',
  'REGULATÓRIO': 'text-cyan-700 border-cyan-200 bg-cyan-50',
  'SAÚDE': 'text-pink-700 border-pink-200 bg-pink-50',
  'CONTRATO': 'text-emerald-700 border-emerald-200 bg-emerald-50',
};

const severityStyle: Record<Exclude<SeverityFilter, 'Todos'>, string> = {
  'Crítico': 'text-red-700 border-red-200 bg-red-50',
  'Alto': 'text-orange-700 border-orange-200 bg-orange-50',
  'Médio': 'text-amber-700 border-amber-200 bg-amber-50',
  'Baixo': 'text-emerald-700 border-emerald-200 bg-emerald-50',
};

function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 1 }).format(value || 0);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('pt-BR').format(value || 0);
}

function redact(text: string, enabled: boolean): string {
  if (!enabled) return text;
  const tokens = text.split(' ');
  return tokens.map((token, idx) => (idx > 1 && token.length > 4 ? '██████' : token)).join(' ');
}

function normalizeSeverity(value: string): Exclude<SeverityFilter, 'Todos'> {
  const v = (value || '').toLowerCase();
  if (v.includes('crí') || v.includes('crit')) return 'Crítico';
  if (v.includes('alto')) return 'Alto';
  if (v.includes('méd') || v.includes('med')) return 'Médio';
  return 'Baixo';
}

function getRequestErrorMessage(err: any, fallback: string): string {
  if (err?.code === 'ECONNABORTED') {
    return 'Tempo limite da operação excedido. A sincronização/análise pode estar pesada; tente novamente.';
  }
  if (!err?.response) {
    return `Backend indisponível em ${api.getBaseUrl()}. Inicie o backend e tente novamente.`;
  }
  return err?.response?.data?.detail || fallback;
}

export default function FiscalInvestigacao(): React.ReactElement {
  const [loading, setLoading] = useState<boolean>(true);
  const [running, setRunning] = useState<boolean>(false);
  const [analyzingCpf, setAnalyzingCpf] = useState<boolean>(false);
  const [activeTab, setActiveTab] = useState<DashboardTab>('insights');
  const [severityFilter, setSeverityFilter] = useState<SeverityFilter>('Todos');
  const [redactionEnabled, setRedactionEnabled] = useState<boolean>(true);

  const [sources, setSources] = useState<FiscalSource[]>([]);
  const [overview, setOverview] = useState<FiscalOverview | null>(null);
  const [sourceDomainCount, setSourceDomainCount] = useState<number>(0);
  const [ranking, setRanking] = useState<FiscalPersonRanking[]>([]);
  const [includeSemDados, setIncludeSemDados] = useState<boolean>(false);
  const [integrationsImplemented, setIntegrationsImplemented] = useState<number>(0);
  const [integrationsPending, setIntegrationsPending] = useState<number>(0);
  const [report, setReport] = useState<RadarGovReport | null>(null);

  const [cpfInput, setCpfInput] = useState<string>('');

  const [mesAno, setMesAno] = useState<number>(Number(new Date().toISOString().slice(0, 7).replace('-', '')));
  const [maxServidores, setMaxServidores] = useState<number>(20);
  const [anoEmendas, setAnoEmendas] = useState<number>(new Date().getFullYear());
  const [maxPaginasEmendas, setMaxPaginasEmendas] = useState<number>(3);
  const [anoCamaraDespesas, setAnoCamaraDespesas] = useState<number>(new Date().getFullYear());
  const [maxDeputadosCamara, setMaxDeputadosCamara] = useState<number>(60);
  const [maxPaginasDespesasPorDeputado, setMaxPaginasDespesasPorDeputado] = useState<number>(5);
  const [pncpDataInicial, setPncpDataInicial] = useState<string>(`${new Date().getFullYear()}0101`);
  const [pncpDataFinal, setPncpDataFinal] = useState<string>(new Date().toISOString().slice(0, 10).replace(/-/g, ''));
  const [pncpMaxPaginas, setPncpMaxPaginas] = useState<number>(3);
  const [pncpTamanhoPagina, setPncpTamanhoPagina] = useState<number>(50);
  const [pgfnAno, setPgfnAno] = useState<number>(new Date().getFullYear());
  const [pgfnCsvUrl, setPgfnCsvUrl] = useState<string>('');
  const [pgfnMaxLinhas, setPgfnMaxLinhas] = useState<number>(200000);
  const [sicafAno, setSicafAno] = useState<number>(new Date().getFullYear());
  const [sicafCsvUrl, setSicafCsvUrl] = useState<string>('');
  const [sicafMaxLinhas, setSicafMaxLinhas] = useState<number>(200000);
  const [anoDoacoes, setAnoDoacoes] = useState<number>(new Date().getFullYear());
  const [doacoesCsvUrl, setDoacoesCsvUrl] = useState<string>('');
  const [doacoesMaxLinhas, setDoacoesMaxLinhas] = useState<number>(50000);
  const [anoBens, setAnoBens] = useState<number>(new Date().getFullYear());
  const [bensCsvUrl, setBensCsvUrl] = useState<string>('');
  const [bensMaxLinhas, setBensMaxLinhas] = useState<number>(50000);
  const [anoCandidaturas, setAnoCandidaturas] = useState<number>(new Date().getFullYear());
  const [candidaturasCsvUrl, setCandidaturasCsvUrl] = useState<string>('');
  const [candidaturasMaxLinhas, setCandidaturasMaxLinhas] = useState<number>(100000);

  const [syncStatusText, setSyncStatusText] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const loadAll = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setError(null);

      const [sourcesResp, overviewResp, syncStatusResp, domainsResp, rankingResp] = await Promise.all([
        api.getFiscalSources(),
        api.getFiscalOverview(),
        api.getFiscalSyncStatus(),
        api.getFiscalSourceDomains(),
        api.getFiscalPeopleRanking(300, includeSemDados),
      ]);
      const integrationsResp = await api.getFiscalIntegrationsStatus().catch(() => null);

      setSources(sourcesResp.sources || []);
      setOverview(overviewResp.data || null);
      setSourceDomainCount(Number(domainsResp?.data?.total_sources || 0));
      setRanking(rankingResp?.dados || []);
      setIntegrationsImplemented(Number(integrationsResp?.data?.implemented_count || 0));
      setIntegrationsPending(Number((integrationsResp?.data?.high_impact_pending || []).length || 0));
      setSyncStatusText(syncStatusResp?.enabled ? `LIVE · atualização a cada ${syncStatusResp.interval_seconds}s` : 'LIVE · modo manual');
    } catch (err) {
      console.error(err);
      setError('Erro ao carregar o dashboard RadarGov.');
    } finally {
      setLoading(false);
    }
  }, [includeSemDados]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const insights = useMemo(() => (report?.insights || []).map((i) => ({ ...i, severity: normalizeSeverity(i.severity) })), [report]);
  const timeline = useMemo(() => (report?.timeline || []) as RadarGovTimelineEvent[], [report]);

  const filteredInsights = useMemo(() => {
    if (severityFilter === 'Todos') return insights;
    return insights.filter((item) => item.severity === severityFilter);
  }, [insights, severityFilter]);

  const summary = report?.summary;
  const rankingSummary = useMemo(() => {
    return {
      total: ranking.length,
      critico: ranking.filter((p) => p.nivel_suspeita === 'CRITICO').length,
      alto: ranking.filter((p) => p.nivel_suspeita === 'ALTO').length,
      medio: ranking.filter((p) => p.nivel_suspeita === 'MEDIO').length,
      baixo: ranking.filter((p) => p.nivel_suspeita === 'BAIXO').length,
      semDados: ranking.filter((p) => p.nivel_suspeita === 'SEM_DADOS').length,
    };
  }, [ranking]);
  const severityCounts = useMemo(() => {
    return {
      Todos: insights.length,
      Crítico: insights.filter((i) => i.severity === 'Crítico').length,
      Alto: insights.filter((i) => i.severity === 'Alto').length,
      Médio: insights.filter((i) => i.severity === 'Médio').length,
      Baixo: insights.filter((i) => i.severity === 'Baixo').length,
    };
  }, [insights]);
  const rawRecordsCount = useMemo(
    () => ranking.reduce((acc, item) => acc + (item.raw_records?.length || 0), 0),
    [ranking]
  );

  const handleAnalyzeCpf = async (): Promise<void> => {
    if (!cpfInput.trim()) {
      setError('Informe um CPF para análise.');
      return;
    }
    try {
      setAnalyzingCpf(true);
      setError(null);
      const response = await api.analyzeCpf(cpfInput.trim());
      setReport(response.report);
    } catch (err: any) {
      console.error(err);
      setError(getRequestErrorMessage(err, 'Falha ao analisar CPF.'));
    } finally {
      setAnalyzingCpf(false);
    }
  };

  const handleSyncAllConnectors = async (): Promise<void> => {
    try {
      setRunning(true);
      setError(null);
      const errors: string[] = [];

      try {
        await api.syncPortalTransparencia({ mesAno, maxServidores });
      } catch (err: any) {
        errors.push(`Salários: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      try {
        await api.syncPublicFinancing({ ano: anoEmendas, maxPaginas: maxPaginasEmendas });
      } catch (err: any) {
        errors.push(`Emendas: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      try {
        await api.syncCamaraExpenses({
          ano: anoCamaraDespesas,
          maxDeputados: maxDeputadosCamara,
          maxPaginasDespesasPorDeputado,
        });
      } catch (err: any) {
        errors.push(`Câmara despesas: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      try {
        await api.syncSenadoExpenses({
          ano: anoCamaraDespesas,
          maxSenadores: 100,
          maxLinhas: 200000,
        });
      } catch (err: any) {
        errors.push(`Senado CEAPS: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      for (const cadastro of ['ceis', 'cnep', 'ceaf', 'cepim'] as const) {
        try {
          await api.syncSanctions({ cadastro, maxPaginas: 2, paginaInicial: 1, matchOnlyExisting: true });
        } catch (err: any) {
          errors.push(`Sanções ${cadastro.toUpperCase()}: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      try {
        await api.syncPncpContracts({
          dataInicial: pncpDataInicial,
          dataFinal: pncpDataFinal,
          maxPaginas: pncpMaxPaginas,
          tamanhoPagina: pncpTamanhoPagina,
        });
      } catch (err: any) {
        errors.push(`PNCP contratos: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      if (pgfnCsvUrl.trim()) {
        try {
          await api.syncPgfnDebts({
            csvUrl: pgfnCsvUrl.trim(),
            ano: pgfnAno,
            maxLinhas: pgfnMaxLinhas,
            matchOnlyExisting: true,
          });
        } catch (err: any) {
          errors.push(`PGFN dívida ativa: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      if (sicafCsvUrl.trim()) {
        try {
          await api.syncSicaf({
            csvUrl: sicafCsvUrl.trim(),
            ano: sicafAno,
            maxLinhas: sicafMaxLinhas,
            matchOnlyExisting: true,
          });
        } catch (err: any) {
          errors.push(`SICAF restrições: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      if (doacoesCsvUrl.trim()) {
        try {
          await api.syncDonationsFromCsv({ ano: anoDoacoes, csvUrl: doacoesCsvUrl.trim(), maxLinhas: doacoesMaxLinhas });
        } catch (err: any) {
          errors.push(`Doações TSE: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      if (bensCsvUrl.trim()) {
        try {
          await api.syncAssetsFromCsv({ ano: anoBens, csvUrl: bensCsvUrl.trim(), maxLinhas: bensMaxLinhas });
        } catch (err: any) {
          errors.push(`Bens TSE: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      if (candidaturasCsvUrl.trim()) {
        try {
          await api.syncCandidatesFromCsv({ ano: anoCandidaturas, csvUrl: candidaturasCsvUrl.trim(), maxLinhas: candidaturasMaxLinhas });
        } catch (err: any) {
          errors.push(`Candidaturas TSE: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      // Auto-discovery fallback from TSE CKAN when manual URLs are not provided.
      if (!doacoesCsvUrl.trim() || !bensCsvUrl.trim() || !candidaturasCsvUrl.trim()) {
        try {
          await api.syncTseAutoFromCkan({
            ano: anoCandidaturas,
            maxLinhasDoacoes: doacoesMaxLinhas,
            maxLinhasBens: bensMaxLinhas,
            maxLinhasCandidatos: candidaturasMaxLinhas,
          });
        } catch (err: any) {
          errors.push(`TSE auto CKAN: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
        }
      }

      try {
        await api.reconcileFiscalIdentities();
      } catch (err: any) {
        errors.push(`Reconciliação: ${err?.response?.data?.detail || err?.message || 'falha desconhecida'}`);
      }

      await api.runFiscalAnalysis({ minExcessoBrl: 100000, minRatioCompatibilidade: 0.7 });
      await loadAll();

      if (cpfInput.trim()) {
        const response = await api.analyzeCpf(cpfInput.trim());
        setReport(response.report);
      }

      if (errors.length > 0) {
        setError(`Pipeline concluído com falhas parciais: ${errors.join(' | ')}`);
      }
    } catch (err: any) {
      console.error(err);
      setError(getRequestErrorMessage(err, 'Falha ao sincronizar conectores.'));
    } finally {
      setRunning(false);
    }
  };

  const tabButtonBase = 'inline-flex items-center rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2';

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="card p-6 animate-pulse">
          <div className="h-5 w-56 rounded bg-slate-200" />
          <div className="mt-3 h-4 w-full max-w-2xl rounded bg-slate-100" />
          <div className="mt-6 grid grid-cols-1 gap-3 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="stat-card">
                <div className="h-3 w-20 rounded bg-slate-200" />
                <div className="mt-3 h-7 w-16 rounded bg-slate-100" />
              </div>
            ))}
          </div>
        </div>
        <div className="card p-6 animate-pulse">
          <div className="h-4 w-48 rounded bg-slate-200" />
          <div className="mt-4 h-48 rounded-xl bg-slate-100" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="card p-6">
        <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-semibold text-slate-900">Radar patrimonial</h3>
              <p className="mt-1 max-w-3xl text-sm text-slate-600">
                Acompanhe integrações, ranking de risco e análise por CPF em uma interface alinhada ao restante do VotoDB.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className="inline-flex items-center rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
                <span className="mr-2 h-2 w-2 rounded-full bg-blue-500" />
                {syncStatusText}
              </span>
              <span className="inline-flex items-center rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
                Integrações {formatNumber(integrationsImplemented)}
              </span>
              <span className="inline-flex items-center rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700">
                Pendências {formatNumber(integrationsPending)}
              </span>
              <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                Fontes {formatNumber(sourceDomainCount || sources.length)}
              </span>
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row xl:flex-col xl:items-stretch">
            <button onClick={() => setRedactionEnabled((prev) => !prev)} className="btn-secondary">
              {redactionEnabled ? 'Redação ativada' : 'Redação desativada'}
            </button>
            <button onClick={handleSyncAllConnectors} disabled={running} className="btn-primary">
              {running ? 'Sincronizando...' : 'Sincronizar pipeline'}
            </button>
          </div>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto]">
          <div>
            <label htmlFor="cpf-alvo" className="mb-2 block text-sm font-medium text-slate-700">
              CPF alvo
            </label>
            <input
              id="cpf-alvo"
              value={cpfInput}
              onChange={(e) => setCpfInput(e.target.value)}
              placeholder="000.000.000-00"
              className="input"
            />
            <p className="mt-2 text-xs text-slate-500">Informe um CPF para consultar o relatório consolidado do RadarGov.</p>
          </div>
          <div className="flex items-end">
            <button onClick={handleAnalyzeCpf} disabled={analyzingCpf} className="btn-primary w-full lg:w-auto">
              {analyzingCpf ? 'Analisando...' : 'Analisar CPF'}
            </button>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <TopMetric label="Entidades" value={formatNumber(summary?.entidades ?? overview?.pessoas_total ?? 0)} tone="text-blue-600" />
        <TopMetric label="Conexões" value={formatNumber(summary?.conexoes ?? overview?.registros_financeiros ?? 0)} tone="text-cyan-600" />
        <TopMetric label="Fontes" value={formatNumber(summary?.fontes ?? (sourceDomainCount || sources.length))} tone="text-amber-600" />
        <TopMetric label="Alertas" value={formatNumber(summary?.alertas ?? overview?.analises_sinalizadas ?? 0)} tone="text-red-600" />
      </div>

      <section className="card p-6">
        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Ranking de risco dos agentes públicos</h3>
            <p className="mt-1 text-sm text-slate-500">
              Total {formatNumber(rankingSummary.total)} · Crítico {formatNumber(rankingSummary.critico)} · Alto {formatNumber(rankingSummary.alto)} · Médio {formatNumber(rankingSummary.medio)} · Baixo {formatNumber(rankingSummary.baixo)} · Sem dados {formatNumber(rankingSummary.semDados)} · Registros brutos {formatNumber(rawRecordsCount)}
            </p>
          </div>
          <label className="inline-flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
            <input type="checkbox" checked={includeSemDados} onChange={(e) => setIncludeSemDados(e.target.checked)} className="rounded border-slate-300 text-blue-600 focus:ring-blue-500" />
            Mostrar SEM_DADOS
          </label>
        </div>

        <div className="overflow-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Nome</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Cargo</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Órgão</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Nível</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Risco</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Excesso</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Cobertura</th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-500">Motivo</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {ranking.length === 0 ? (
                <tr>
                  <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={8}>
                    Execute a pipeline para gerar o ranking.
                  </td>
                </tr>
              ) : (
                ranking.slice(0, 120).map((item) => (
                  <tr key={item.person_id} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-medium text-slate-900">{redact(item.nome, redactionEnabled)}</td>
                    <td className="px-4 py-3 text-slate-600">{item.cargo || '-'}</td>
                    <td className="px-4 py-3 text-slate-500">{item.orgao || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${riskTierStyle(item.nivel_suspeita)}`}>
                        {item.nivel_suspeita}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-700">{formatNumber(Math.round(item.risco_score || 0))}</td>
                    <td className="px-4 py-3 font-medium text-amber-700">{formatBRL(item.excesso_nao_explicado || 0)}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{(item.cobertura?.tipos || []).join(', ') || '-'}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">{item.motivo_nivel || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card p-6">
        <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Dados brutos por agente público</h3>
            <p className="mt-1 text-sm text-slate-500">Exibindo {formatNumber(rawRecordsCount)} registros financeiros ingeridos.</p>
          </div>
        </div>

        <div className="max-h-[640px] space-y-3 overflow-auto pr-1">
          {ranking.length === 0 ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 px-4 py-6 text-sm text-slate-500">
              Sem pessoas para exibir dados brutos.
            </div>
          ) : (
            ranking.map((person, personIdx) => {
              const records = person.raw_records || [];
              const totalsByType = Object.entries(person.totais_por_tipo || {});

              return (
                <details key={person.person_id} className="rounded-xl border border-slate-200 bg-slate-50" open={personIdx < 2}>
                  <summary className="cursor-pointer list-none px-4 py-3">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                      <div>
                        <p className="font-medium text-slate-900">{redact(person.nome, redactionEnabled)}</p>
                        <p className="text-sm text-slate-500">{person.cargo || '-'} · {person.orgao || '-'} · {formatNumber(records.length)} registro(s)</p>
                      </div>
                      <span className={`inline-flex rounded-full border px-2.5 py-1 text-xs font-medium ${riskTierStyle(person.nivel_suspeita)}`}>
                        {person.nivel_suspeita}
                      </span>
                    </div>
                  </summary>

                  <div className="space-y-4 border-t border-slate-200 px-4 py-4">
                    <div className="grid gap-3 md:grid-cols-3">
                      <div className="rounded-lg bg-white px-3 py-3">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Órgão</p>
                        <p className="mt-1 text-sm text-slate-700">{person.orgao || '-'}</p>
                      </div>
                      <div className="rounded-lg bg-white px-3 py-3 md:col-span-2">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Motivo do nível</p>
                        <p className="mt-1 text-sm text-slate-700">{person.motivo_nivel || '-'}</p>
                      </div>
                    </div>

                    <div className="rounded-lg bg-white px-3 py-3">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Totais por tipo</p>
                      <p className="mt-1 text-sm text-slate-700">
                        {totalsByType.length === 0
                          ? '-'
                          : totalsByType.map(([tipo, total]) => `${tipo}: ${formatBRL(Number(total || 0))}`).join(' | ')}
                      </p>
                    </div>

                    {records.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-slate-300 bg-white px-4 py-5 text-sm text-slate-500">
                        Nenhum registro financeiro bruto para este agente.
                      </div>
                    ) : (
                      <div className="overflow-auto rounded-xl border border-slate-200 bg-white">
                        <table className="min-w-[980px] w-full divide-y divide-slate-200 text-left text-xs">
                          <thead className="bg-slate-50">
                            <tr>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Ano</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Tipo</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Valor</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Fonte</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Data ref.</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Confiança</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Fonte URL</th>
                              <th className="px-3 py-2 font-semibold uppercase tracking-wide text-slate-500">Raw JSON</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {records.map((rec) => (
                              <tr key={`${person.person_id}-${rec.id}`} className="align-top hover:bg-slate-50">
                                <td className="px-3 py-3 text-slate-700">{rec.ano}</td>
                                <td className="px-3 py-3 text-slate-700">{rec.tipo}</td>
                                <td className="px-3 py-3 font-medium text-cyan-700">{formatBRL(rec.valor || 0)}</td>
                                <td className="px-3 py-3 text-slate-600">{rec.fonte}</td>
                                <td className="px-3 py-3 text-slate-500">{rec.data_referencia ? new Date(rec.data_referencia).toLocaleString('pt-BR') : '-'}</td>
                                <td className="px-3 py-3 text-slate-500">{formatNumber(Math.round((rec.confianca || 0) * 100))}%</td>
                                <td className="px-3 py-3 text-xs text-slate-500">
                                  {rec.fonte_url ? <a className="font-medium text-blue-600 hover:text-blue-700" href={rec.fonte_url} target="_blank" rel="noreferrer">Abrir</a> : '-'}
                                </td>
                                <td className="px-3 py-3">
                                  <pre className="max-h-28 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-2 text-[11px] text-slate-600">
                                    {JSON.stringify(rec.extra_json || {}, null, 2)}
                                  </pre>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </details>
              );
            })
          )}
        </div>
      </section>

      {error && (
        <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {report && !report.found && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
          {report.message}
        </div>
      )}

      <section className="card p-6">
        <div className="flex flex-wrap gap-2 border-b border-slate-200 pb-4">
          <button
            onClick={() => setActiveTab('insights')}
            className={`${tabButtonBase} ${activeTab === 'insights' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
          >
            Insights {formatNumber(severityCounts.Todos)}
          </button>
          <button
            onClick={() => setActiveTab('detalhe')}
            className={`${tabButtonBase} ${activeTab === 'detalhe' ? 'bg-blue-50 text-blue-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
          >
            Detalhe
          </button>
        </div>

        {activeTab === 'insights' ? (
          <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-3">
            <aside className="rounded-xl border border-slate-200 bg-slate-50 p-4 xl:col-span-1">
              <h3 className="mb-4 text-sm font-semibold text-slate-900">Linha do tempo</h3>
              <div className="max-h-[920px] space-y-3 overflow-auto pr-1">
                {timeline.length === 0 ? (
                  <p className="text-sm text-slate-500">Sem eventos para o CPF informado.</p>
                ) : (
                  timeline.map((event, idx) => {
                    const cat = (event.category || 'FINANCEIRO').toUpperCase() as TimelineCategory;
                    const style = categoryStyle[cat] || categoryStyle.FINANCEIRO;

                    return (
                      <div key={`${event.date}-${idx}`} className="rounded-xl border border-slate-200 bg-white p-3">
                        <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                          <span>{event.date}</span>
                          <span className={`rounded-full border px-2 py-0.5 font-medium ${style}`}>{cat}</span>
                          <span className="sm:ml-auto">{event.source}</span>
                        </div>
                        <p className="text-sm text-slate-700">{redact(event.text, redactionEnabled)}</p>
                      </div>
                    );
                  })
                )}
              </div>
            </aside>

            <section className="space-y-4 xl:col-span-2">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Exposição total</p>
                    <p className="mt-2 text-3xl font-bold text-slate-900">{formatBRL(summary?.exposicao_total || 0)}</p>
                  </div>
                  <div className="text-sm text-slate-500">
                    <p>{formatNumber(summary?.irregularidades || 0)} irregularidades</p>
                    <p>{formatNumber(summary?.fontes || 0)} fontes</p>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {(['Todos', 'Crítico', 'Alto', 'Médio', 'Baixo'] as SeverityFilter[]).map((filter) => {
                  const active = severityFilter === filter;
                  return (
                    <button
                      key={filter}
                      onClick={() => setSeverityFilter(filter)}
                      className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                        active
                          ? 'border-blue-200 bg-blue-50 text-blue-700'
                          : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-900'
                      }`}
                    >
                      {filter} {formatNumber(severityCounts[filter])}
                    </button>
                  );
                })}
              </div>

              <div className="space-y-3">
                {filteredInsights.length === 0 ? (
                  <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-sm text-slate-500">
                    Nenhuma irregularidade encontrada para o CPF ou filtro atual.
                  </div>
                ) : (
                  filteredInsights.map((insight: RadarGovInsight, idx: number) => (
                    <article key={`${insight.pattern_id}-${idx}`} className="rounded-xl border border-slate-200 bg-white p-5">
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${severityStyle[insight.severity]}`}>
                          {insight.severity}
                        </span>
                        <span className="text-xs text-slate-500">{report?.person?.orgao || 'Órgão não informado'} · {insight.ano || '-'}</span>
                        <span className="sm:ml-auto text-sm font-medium text-slate-700">{formatNumber(insight.confidence)}%</span>
                      </div>

                      <h4 className="text-xl font-semibold text-slate-900">{redact(insight.titulo, redactionEnabled)}</h4>
                      <p className="mt-2 text-lg font-semibold text-amber-700">{formatBRL(insight.impacto)}</p>
                      <p className="mt-3 text-sm leading-relaxed text-slate-700">{redact(insight.descricao, redactionEnabled)}</p>

                      <div className="mt-4 rounded-lg bg-slate-50 p-3">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Padrão identificado</p>
                        <p className="mt-1 text-sm text-slate-700">{insight.pattern_id} → {insight.titulo.toUpperCase()}</p>
                      </div>

                      <div className="mt-4 flex flex-wrap gap-2">
                        {insight.fontes.map((source) => (
                          <span key={source} className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-600">
                            {source}
                          </span>
                        ))}
                      </div>
                    </article>
                  ))
                )}
              </div>
            </section>
          </div>
        ) : (
          <div className="mt-6 grid grid-cols-1 gap-5 xl:grid-cols-3">
            <section className="rounded-xl border border-slate-200 bg-slate-50 p-4 xl:col-span-2">
              <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-sm font-semibold text-slate-900">Mapa de entidades</h3>
                <div className="text-xs text-slate-500">CPF raiz: {report?.cpf || '-'}</div>
              </div>

              <div className="relative h-[380px] overflow-hidden rounded-xl border border-slate-200 bg-white">
                <div className="absolute inset-0 bg-[radial-gradient(circle,_rgba(148,163,184,0.2)_1px,_transparent_1px)] bg-[length:24px_24px]" />
                <div className="absolute left-1/2 top-1/2 h-12 w-12 -translate-x-1/2 -translate-y-1/2 rounded-full border border-blue-200 bg-blue-50 shadow-sm" />
                {(report?.entity_graph?.nodes || []).slice(0, 16).map((item, idx) => {
                  const angle = (idx / 16) * Math.PI * 2;
                  const radius = 110 + (idx % 4) * 24;
                  const x = Math.cos(angle) * radius;
                  const y = Math.sin(angle) * radius;

                  return (
                    <div key={item.id}>
                      <span className="absolute left-1/2 top-1/2 text-[10px] text-slate-300" style={{ transform: `translate(${x * 0.6}px, ${y * 0.6}px)` }}>•</span>
                      <span
                        className="absolute rounded-full border border-slate-200 bg-white px-2 py-1 text-[10px] text-slate-700 shadow-sm"
                        style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`, left: '50%', top: '50%' }}
                      >
                        {redact(item.label, redactionEnabled)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </section>

            <aside className="rounded-xl border border-slate-200 bg-slate-50 p-4 xl:col-span-1">
              <h3 className="mb-3 text-sm font-semibold text-slate-900">Detalhe da entidade</h3>
              {!report?.person ? (
                <p className="text-sm text-slate-500">Analise um CPF para visualizar detalhes.</p>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Pessoa</p>
                    <p className="mt-1 text-lg font-semibold text-slate-900">{redact(report.person.nome, redactionEnabled)}</p>
                    <p className="text-sm text-slate-500">{report.person.cargo} · {report.person.orgao || '-'}</p>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Insights relacionados</p>
                    <div className="mt-3 space-y-2">
                      {insights.slice(0, 4).map((insight, idx) => (
                        <div key={`${insight.pattern_id}-${idx}`} className="rounded-lg bg-slate-50 px-3 py-2 text-sm text-slate-700">
                          <span className={`mr-2 rounded-full border px-2 py-0.5 text-[10px] font-medium ${severityStyle[insight.severity]}`}>
                            {insight.severity}
                          </span>
                          {redact(insight.titulo, redactionEnabled)}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-white p-3">
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Padrões suportados</p>
                    <ul className="mt-2 space-y-1 text-sm text-slate-700">
                      {(report.supported_patterns || []).slice(0, 10).map((p) => <li key={p.id}>• {p.id} {p.name}</li>)}
                    </ul>
                  </div>
                </div>
              )}
            </aside>
          </div>
        )}
      </section>

      <details className="card p-5">
        <summary className="cursor-pointer text-sm font-medium text-slate-900">Configuração da ingestão</summary>
        <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Mês/Ano salários (YYYYMM)</span><input type="number" value={mesAno} onChange={(e) => setMesAno(Number(e.target.value || 0))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. servidores</span><input type="number" min={1} value={maxServidores} onChange={(e) => setMaxServidores(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano emendas</span><input type="number" value={anoEmendas} onChange={(e) => setAnoEmendas(Number(e.target.value || 0))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. páginas emendas</span><input type="number" min={1} value={maxPaginasEmendas} onChange={(e) => setMaxPaginasEmendas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano despesas Câmara</span><input type="number" value={anoCamaraDespesas} onChange={(e) => setAnoCamaraDespesas(Number(e.target.value || 0))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. deputados Câmara</span><input type="number" min={1} value={maxDeputadosCamara} onChange={(e) => setMaxDeputadosCamara(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. páginas despesas/deputado</span><input type="number" min={1} value={maxPaginasDespesasPorDeputado} onChange={(e) => setMaxPaginasDespesasPorDeputado(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">PNCP data inicial (YYYYMMDD)</span><input type="text" value={pncpDataInicial} onChange={(e) => setPncpDataInicial(e.target.value)} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">PNCP data final (YYYYMMDD)</span><input type="text" value={pncpDataFinal} onChange={(e) => setPncpDataFinal(e.target.value)} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">PNCP máx. páginas</span><input type="number" min={1} value={pncpMaxPaginas} onChange={(e) => setPncpMaxPaginas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">PNCP tamanho página (&gt;=10)</span><input type="number" min={10} value={pncpTamanhoPagina} onChange={(e) => setPncpTamanhoPagina(Number(e.target.value || 10))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano PGFN</span><input type="number" value={pgfnAno} onChange={(e) => setPgfnAno(Number(e.target.value || 0))} className="input" /></label>
          <label className="block md:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">URL CSV/ZIP PGFN dívida ativa</span><input type="text" value={pgfnCsvUrl} onChange={(e) => setPgfnCsvUrl(e.target.value)} placeholder="https://..." className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. linhas PGFN</span><input type="number" min={1} value={pgfnMaxLinhas} onChange={(e) => setPgfnMaxLinhas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano SICAF</span><input type="number" value={sicafAno} onChange={(e) => setSicafAno(Number(e.target.value || 0))} className="input" /></label>
          <label className="block md:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">URL CSV/ZIP SICAF habilitação</span><input type="text" value={sicafCsvUrl} onChange={(e) => setSicafCsvUrl(e.target.value)} placeholder="https://..." className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. linhas SICAF</span><input type="number" min={1} value={sicafMaxLinhas} onChange={(e) => setSicafMaxLinhas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano doações</span><input type="number" value={anoDoacoes} onChange={(e) => setAnoDoacoes(Number(e.target.value || 0))} className="input" /></label>
          <label className="block md:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">URL CSV/ZIP doações TSE</span><input type="text" value={doacoesCsvUrl} onChange={(e) => setDoacoesCsvUrl(e.target.value)} placeholder="https://..." className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. linhas doações</span><input type="number" min={1} value={doacoesMaxLinhas} onChange={(e) => setDoacoesMaxLinhas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano bens TSE</span><input type="number" value={anoBens} onChange={(e) => setAnoBens(Number(e.target.value || 0))} className="input" /></label>
          <label className="block md:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">URL CSV/ZIP bens declarados TSE</span><input type="text" value={bensCsvUrl} onChange={(e) => setBensCsvUrl(e.target.value)} placeholder="https://..." className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. linhas bens</span><input type="number" min={1} value={bensMaxLinhas} onChange={(e) => setBensMaxLinhas(Number(e.target.value || 1))} className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Ano candidaturas TSE</span><input type="number" value={anoCandidaturas} onChange={(e) => setAnoCandidaturas(Number(e.target.value || 0))} className="input" /></label>
          <label className="block md:col-span-2"><span className="mb-2 block text-sm font-medium text-slate-700">URL CSV/ZIP candidaturas TSE</span><input type="text" value={candidaturasCsvUrl} onChange={(e) => setCandidaturasCsvUrl(e.target.value)} placeholder="https://..." className="input" /></label>
          <label className="block"><span className="mb-2 block text-sm font-medium text-slate-700">Máx. linhas candidaturas</span><input type="number" min={1} value={candidaturasMaxLinhas} onChange={(e) => setCandidaturasMaxLinhas(Number(e.target.value || 1))} className="input" /></label>
        </div>
      </details>
    </div>
  );
}

function TopMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="stat-card">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold ${tone}`}>{value}</p>
    </div>
  );
}

function riskTierStyle(level: FiscalPersonRanking['nivel_suspeita']): string {
  if (level === 'CRITICO') return 'border-red-200 bg-red-50 text-red-700';
  if (level === 'ALTO') return 'border-orange-200 bg-orange-50 text-orange-700';
  if (level === 'MEDIO') return 'border-amber-200 bg-amber-50 text-amber-700';
  if (level === 'BAIXO') return 'border-emerald-200 bg-emerald-50 text-emerald-700';
  if (level === 'MINIMO') return 'border-teal-200 bg-teal-50 text-teal-700';
  return 'border-slate-200 bg-slate-100 text-slate-700';
}
