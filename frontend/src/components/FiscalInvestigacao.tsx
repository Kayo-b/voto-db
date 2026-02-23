import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../services/api';
import { FiscalOverview, FiscalPersonRanking, FiscalSource, RadarGovInsight, RadarGovReport, RadarGovTimelineEvent } from '../types/api';

type DashboardTab = 'insights' | 'detalhe';
type SeverityFilter = 'Todos' | 'Crítico' | 'Alto' | 'Médio' | 'Baixo';
type TimelineCategory = 'JURÍDICO' | 'EMPRESA' | 'PESSOA' | 'AMBIENTAL' | 'FINANCEIRO' | 'REGULATÓRIO' | 'SAÚDE' | 'CONTRATO';

const categoryStyle: Record<TimelineCategory, string> = {
  'JURÍDICO': 'text-amber-300 border-amber-500 bg-amber-500/10',
  'EMPRESA': 'text-orange-300 border-orange-500 bg-orange-500/10',
  'PESSOA': 'text-yellow-300 border-yellow-500 bg-yellow-500/10',
  'AMBIENTAL': 'text-teal-300 border-teal-500 bg-teal-500/10',
  'FINANCEIRO': 'text-blue-300 border-blue-500 bg-blue-500/10',
  'REGULATÓRIO': 'text-cyan-300 border-cyan-500 bg-cyan-500/10',
  'SAÚDE': 'text-pink-300 border-pink-500 bg-pink-500/10',
  'CONTRATO': 'text-emerald-300 border-emerald-500 bg-emerald-500/10',
};

const severityStyle: Record<Exclude<SeverityFilter, 'Todos'>, string> = {
  'Crítico': 'text-red-300 border-red-500 bg-red-600/10',
  'Alto': 'text-orange-300 border-orange-500 bg-orange-600/10',
  'Médio': 'text-amber-300 border-amber-500 bg-amber-600/10',
  'Baixo': 'text-emerald-300 border-emerald-500 bg-emerald-600/10',
};

function formatBRL(value: number): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 1 }).format(value || 0);
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
      if (!err?.response) {
        setError('Backend indisponível em http://localhost:8001. Inicie o backend e tente novamente.');
      } else {
        setError(err?.response?.data?.detail || 'Falha ao analisar CPF.');
      }
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
      if (!err?.response) {
        setError('Backend indisponível em http://localhost:8001. Inicie o backend e tente novamente.');
      } else {
        setError(err?.response?.data?.detail || 'Falha ao sincronizar conectores.');
      }
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-[#060b11] p-8 text-slate-200">
        <p className="animate-pulse">Inicializando RadarGov...</p>
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl border border-slate-800 bg-[#04080d] text-slate-200 p-4 md:p-6"
      style={{
        fontFamily: '"JetBrains Mono", "IBM Plex Mono", "Fira Code", ui-monospace, SFMono-Regular, Menlo, monospace',
        backgroundImage: 'radial-gradient(circle at 20% 0%, rgba(251,146,60,0.08), transparent 25%), linear-gradient(rgba(56, 189, 248, 0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(56, 189, 248, 0.04) 1px, transparent 1px)',
        backgroundSize: 'auto, 64px 64px, 64px 64px',
      }}
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-3">
        <div className="flex items-center gap-3 text-xs tracking-widest uppercase">
          <span className="inline-flex h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
          <span className="text-red-300">LIVE</span>
          <span className="text-slate-500">{syncStatusText}</span>
          <span className="text-emerald-400">Integrações {integrationsImplemented}</span>
          <span className="text-amber-400">Pendências {integrationsPending}</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <button onClick={() => setRedactionEnabled((prev) => !prev)} className="rounded border border-slate-700 px-2 py-1 text-slate-300 hover:border-slate-500">
            {redactionEnabled ? 'Redação ON' : 'Redação OFF'}
          </button>
          <button onClick={handleSyncAllConnectors} disabled={running} className="rounded border border-orange-500/60 px-3 py-1 text-orange-300 hover:bg-orange-500/10 disabled:opacity-40">
            {running ? 'Sincronizando...' : 'Sync Pipeline'}
          </button>
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-end gap-2">
        <div className="flex-1 min-w-[240px]">
          <label className="text-[10px] uppercase tracking-[0.18em] text-slate-500">CPF alvo</label>
          <input
            value={cpfInput}
            onChange={(e) => setCpfInput(e.target.value)}
            placeholder="000.000.000-00"
            className="mt-1 w-full rounded border border-slate-700 bg-black/50 px-3 py-2 text-sm text-slate-100"
          />
        </div>
        <button onClick={handleAnalyzeCpf} disabled={analyzingCpf} className="rounded border border-cyan-500/60 px-3 py-2 text-cyan-300 hover:bg-cyan-500/10 disabled:opacity-40 text-sm">
          {analyzingCpf ? 'Analisando...' : 'Analisar CPF'}
        </button>
      </div>

      <div className="mb-5 grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
        <TopMetric label="ENTIDADES" value={String(summary?.entidades ?? overview?.pessoas_total ?? 0)} tone="text-blue-300" />
        <TopMetric label="CONEXÕES" value={String(summary?.conexoes ?? overview?.registros_financeiros ?? 0)} tone="text-cyan-300" />
        <TopMetric label="FONTES" value={String(summary?.fontes ?? (sourceDomainCount || sources.length))} tone="text-amber-300" />
        <TopMetric label="ALERTAS" value={String(summary?.alertas ?? overview?.analises_sinalizadas ?? 0)} tone="text-red-300" />
      </div>

      <section className="mb-5 rounded-xl border border-slate-800 bg-black/30 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="text-xs tracking-[0.2em] uppercase text-orange-300">Ranking de risco dos agentes públicos</h3>
          <div className="flex items-center gap-3">
            <p className="text-xs text-slate-500">
              Total {rankingSummary.total} · Crítico {rankingSummary.critico} · Alto {rankingSummary.alto} · Médio {rankingSummary.medio} · Baixo {rankingSummary.baixo} · Sem dados {rankingSummary.semDados}
            </p>
            <label className="text-xs text-slate-400 inline-flex items-center gap-1">
              <input type="checkbox" checked={includeSemDados} onChange={(e) => setIncludeSemDados(e.target.checked)} />
              Mostrar SEM_DADOS
            </label>
          </div>
        </div>
        <div className="max-h-52 overflow-auto rounded border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-slate-950 text-slate-400">
              <tr>
                <th className="px-3 py-2">Nome</th>
                <th className="px-3 py-2">Cargo</th>
                <th className="px-3 py-2">Órgão</th>
                <th className="px-3 py-2">Nível</th>
                <th className="px-3 py-2">Risco</th>
                <th className="px-3 py-2">Excesso (R$)</th>
                <th className="px-3 py-2">Cobertura</th>
              </tr>
            </thead>
            <tbody>
              {ranking.length === 0 ? (
                <tr><td className="px-3 py-3 text-slate-500" colSpan={7}>Execute a pipeline para gerar o ranking.</td></tr>
              ) : (
                ranking.slice(0, 120).map((item) => (
                  <tr key={item.person_id} className="border-t border-slate-900/70">
                    <td className="px-3 py-2 text-slate-200">{redact(item.nome, redactionEnabled)}</td>
                    <td className="px-3 py-2 text-slate-400">{item.cargo || '-'}</td>
                    <td className="px-3 py-2 text-slate-500">{item.orgao || '-'}</td>
                    <td className="px-3 py-2"><span className={`rounded border px-2 py-[1px] ${riskTierStyle(item.nivel_suspeita)}`}>{item.nivel_suspeita}</span></td>
                    <td className="px-3 py-2 text-slate-300">{Math.round(item.risco_score || 0)}</td>
                    <td className="px-3 py-2 text-amber-300">{formatBRL(item.excesso_nao_explicado || 0)}</td>
                    <td className="px-3 py-2 text-[10px] text-slate-500">{(item.cobertura?.tipos || []).join(', ') || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      {error && <div className="mb-4 rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-300">{error}</div>}
      {report && !report.found && <div className="mb-4 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-sm text-amber-300">{report.message}</div>}

      <div className="mb-4 flex gap-2 border-b border-slate-800">
        <button onClick={() => setActiveTab('insights')} className={`px-4 py-2 text-sm tracking-widest uppercase border-b-2 ${activeTab === 'insights' ? 'border-orange-400 text-orange-300' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>
          Insights {severityCounts.Todos}
        </button>
        <button onClick={() => setActiveTab('detalhe')} className={`px-4 py-2 text-sm tracking-widest uppercase border-b-2 ${activeTab === 'detalhe' ? 'border-orange-400 text-orange-300' : 'border-transparent text-slate-500 hover:text-slate-300'}`}>
          Detalhe
        </button>
      </div>

      {activeTab === 'insights' ? (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <aside className="xl:col-span-1 rounded-xl border border-slate-800 bg-black/30 p-4">
            <h3 className="mb-4 text-xs tracking-[0.2em] text-orange-300 uppercase">Linha do tempo — eventos cronológicos</h3>
            <div className="space-y-3 max-h-[920px] overflow-auto pr-1">
              {timeline.length === 0 ? <p className="text-sm text-slate-500">Sem eventos para o CPF informado.</p> : timeline.map((event, idx) => {
                const cat = (event.category || 'FINANCEIRO').toUpperCase() as TimelineCategory;
                const style = categoryStyle[cat] || categoryStyle.FINANCEIRO;
                return (
                  <div key={`${event.date}-${idx}`} className="relative rounded border border-slate-800/80 bg-slate-900/30 p-3">
                    <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
                      <span>{event.date}</span>
                      <span className={`rounded border px-2 py-[2px] ${style}`}>{cat}</span>
                      <span className="ml-auto text-[10px] text-slate-500">{event.source}</span>
                    </div>
                    <p className="text-sm text-slate-200">{redact(event.text, redactionEnabled)}</p>
                  </div>
                );
              })}
            </div>
          </aside>

          <section className="xl:col-span-2 space-y-4">
            <div className="rounded-xl border border-slate-800 bg-black/40 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.2em] text-red-300">Exposição total</p>
                  <p className="text-4xl font-bold text-slate-100 mt-1">{formatBRL(summary?.exposicao_total || 0)}</p>
                </div>
                <div className="text-right text-sm text-slate-400">
                  <p>{summary?.irregularidades || 0} irregularidades</p>
                  <p>{summary?.fontes || 0} fontes</p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {(['Todos', 'Crítico', 'Alto', 'Médio', 'Baixo'] as SeverityFilter[]).map((filter) => {
                const active = severityFilter === filter;
                return (
                  <button key={filter} onClick={() => setSeverityFilter(filter)} className={`rounded border px-3 py-1 text-xs ${active ? 'border-orange-400 text-orange-300 bg-orange-500/10' : 'border-slate-700 text-slate-400 hover:border-slate-500'}`}>
                    {filter} {severityCounts[filter]}
                  </button>
                );
              })}
            </div>

            <div className="space-y-3">
              {filteredInsights.length === 0 ? (
                <div className="rounded-xl border border-slate-800 bg-slate-900/20 p-6 text-sm text-slate-400">Nenhuma irregularidade encontrada para o CPF/filtro atual.</div>
              ) : (
                filteredInsights.map((insight: RadarGovInsight, idx: number) => (
                  <article key={`${insight.pattern_id}-${idx}`} className="rounded-xl border border-red-700/30 bg-slate-950/80 p-4 shadow-[inset_2px_0_0_0_rgba(239,68,68,0.8)]">
                    <div className="mb-2 flex items-center gap-3">
                      <span className={`rounded border px-2 py-[2px] text-[11px] uppercase ${severityStyle[insight.severity]}`}>{insight.severity}</span>
                      <span className="text-[11px] text-slate-500">{report?.person?.orgao || 'órgão não informado'} · {insight.ano || '-'}</span>
                      <span className="ml-auto text-sm text-red-300">{insight.confidence}%</span>
                    </div>

                    <h4 className="text-2xl text-slate-100 leading-tight">{redact(insight.titulo, redactionEnabled)}</h4>
                    <p className="mt-2 text-amber-300 text-lg">💰 {formatBRL(insight.impacto)}</p>
                    <p className="mt-3 text-sm text-slate-300 leading-relaxed">{redact(insight.descricao, redactionEnabled)}</p>

                    <div className="mt-3 rounded border border-slate-800 bg-black/40 p-3">
                      <p className="text-[10px] tracking-[0.2em] uppercase text-slate-500">Pattern</p>
                      <p className="mt-1 text-sm text-red-300">{insight.pattern_id} → {insight.titulo.toUpperCase()}</p>
                    </div>

                    <div className="mt-3 flex flex-wrap gap-2">
                      {insight.fontes.map((source) => (
                        <span key={source} className="rounded border border-slate-700 px-2 py-1 text-[10px] text-slate-400">{source}</span>
                      ))}
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
          <section className="xl:col-span-2 rounded-xl border border-slate-800 bg-black/30 p-4">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-xs tracking-[0.2em] uppercase text-orange-300">Entity Graph</h3>
              <div className="text-xs text-slate-500">CPF root: {report?.cpf || '-'}</div>
            </div>

            <div className="relative h-[380px] rounded border border-slate-800 bg-[#050b12] overflow-hidden">
              <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(circle, rgba(251,146,60,0.15) 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
              <div className="absolute left-1/2 top-1/2 h-10 w-10 -translate-x-1/2 -translate-y-1/2 rounded-full border border-orange-400 bg-orange-500/20 shadow-[0_0_24px_rgba(251,146,60,0.45)]" />
              {(report?.entity_graph?.nodes || []).slice(0, 16).map((item, idx) => {
                const angle = (idx / 16) * Math.PI * 2;
                const radius = 110 + (idx % 4) * 24;
                const x = Math.cos(angle) * radius;
                const y = Math.sin(angle) * radius;
                return (
                  <div key={item.id}>
                    <span className="absolute left-1/2 top-1/2 text-[10px] text-slate-400" style={{ transform: `translate(${x * 0.6}px, ${y * 0.6}px)` }}>•</span>
                    <span className="absolute rounded-full border border-slate-700 bg-slate-900/80 px-2 py-1 text-[10px] text-slate-300" style={{ transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`, left: '50%', top: '50%' }}>
                      {redact(item.label, redactionEnabled)}
                    </span>
                  </div>
                );
              })}
            </div>
          </section>

          <aside className="xl:col-span-1 rounded-xl border border-slate-800 bg-black/30 p-4">
            <h3 className="text-xs tracking-[0.2em] uppercase text-orange-300 mb-3">Detalhe da entidade</h3>
            {!report?.person ? (
              <p className="text-sm text-slate-500">Analise um CPF para visualizar detalhes.</p>
            ) : (
              <div className="space-y-4">
                <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                  <p className="text-xs text-slate-400">Pessoa</p>
                  <p className="text-lg text-slate-100 mt-1">{redact(report.person.nome, redactionEnabled)}</p>
                  <p className="text-sm text-slate-500">{report.person.cargo} · {report.person.orgao || '-'}</p>
                </div>

                <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                  <p className="text-xs tracking-[0.2em] uppercase text-slate-500">Insights relacionados</p>
                  <div className="mt-2 space-y-2">
                    {insights.slice(0, 4).map((insight, idx) => (
                      <div key={`${insight.pattern_id}-${idx}`} className="rounded border border-slate-800 px-2 py-2 text-sm text-slate-300">
                        <span className={`mr-2 rounded px-1.5 py-0.5 text-[10px] ${severityStyle[insight.severity]}`}>{insight.severity}</span>
                        {redact(insight.titulo, redactionEnabled)}
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded border border-slate-800 bg-slate-900/30 p-3">
                  <p className="text-xs tracking-[0.2em] uppercase text-slate-500">Padrões suportados</p>
                  <ul className="mt-2 space-y-1 text-sm text-slate-300">
                    {(report.supported_patterns || []).slice(0, 10).map((p) => <li key={p.id}>• {p.id} {p.name}</li>)}
                  </ul>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      <details className="mt-6 rounded border border-slate-800 bg-black/20 p-3">
        <summary className="cursor-pointer text-xs uppercase tracking-[0.2em] text-slate-400">Configuração da ingestão</summary>
        <div className="mt-3 grid grid-cols-1 md:grid-cols-3 gap-3 text-xs">
          <label className="space-y-1"><span className="text-slate-500">Mês/Ano salários (YYYYMM)</span><input type="number" value={mesAno} onChange={(e) => setMesAno(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. servidores</span><input type="number" min={1} value={maxServidores} onChange={(e) => setMaxServidores(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano emendas</span><input type="number" value={anoEmendas} onChange={(e) => setAnoEmendas(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. páginas emendas</span><input type="number" min={1} value={maxPaginasEmendas} onChange={(e) => setMaxPaginasEmendas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano despesas Câmara</span><input type="number" value={anoCamaraDespesas} onChange={(e) => setAnoCamaraDespesas(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. deputados Câmara</span><input type="number" min={1} value={maxDeputadosCamara} onChange={(e) => setMaxDeputadosCamara(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. páginas despesas/deputado</span><input type="number" min={1} value={maxPaginasDespesasPorDeputado} onChange={(e) => setMaxPaginasDespesasPorDeputado(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">PNCP data inicial (YYYYMMDD)</span><input type="text" value={pncpDataInicial} onChange={(e) => setPncpDataInicial(e.target.value)} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">PNCP data final (YYYYMMDD)</span><input type="text" value={pncpDataFinal} onChange={(e) => setPncpDataFinal(e.target.value)} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">PNCP máx. páginas</span><input type="number" min={1} value={pncpMaxPaginas} onChange={(e) => setPncpMaxPaginas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">PNCP tamanho página (&gt;=10)</span><input type="number" min={10} value={pncpTamanhoPagina} onChange={(e) => setPncpTamanhoPagina(Number(e.target.value || 10))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano PGFN</span><input type="number" value={pgfnAno} onChange={(e) => setPgfnAno(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1 md:col-span-2"><span className="text-slate-500">URL CSV/ZIP PGFN dívida ativa</span><input type="text" value={pgfnCsvUrl} onChange={(e) => setPgfnCsvUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. linhas PGFN</span><input type="number" min={1} value={pgfnMaxLinhas} onChange={(e) => setPgfnMaxLinhas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano SICAF</span><input type="number" value={sicafAno} onChange={(e) => setSicafAno(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1 md:col-span-2"><span className="text-slate-500">URL CSV/ZIP SICAF habilitação</span><input type="text" value={sicafCsvUrl} onChange={(e) => setSicafCsvUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. linhas SICAF</span><input type="number" min={1} value={sicafMaxLinhas} onChange={(e) => setSicafMaxLinhas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano doações</span><input type="number" value={anoDoacoes} onChange={(e) => setAnoDoacoes(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1 md:col-span-2"><span className="text-slate-500">URL CSV/ZIP doações TSE</span><input type="text" value={doacoesCsvUrl} onChange={(e) => setDoacoesCsvUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. linhas doações</span><input type="number" min={1} value={doacoesMaxLinhas} onChange={(e) => setDoacoesMaxLinhas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano bens TSE</span><input type="number" value={anoBens} onChange={(e) => setAnoBens(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1 md:col-span-2"><span className="text-slate-500">URL CSV/ZIP bens declarados TSE</span><input type="text" value={bensCsvUrl} onChange={(e) => setBensCsvUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. linhas bens</span><input type="number" min={1} value={bensMaxLinhas} onChange={(e) => setBensMaxLinhas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Ano candidaturas TSE</span><input type="number" value={anoCandidaturas} onChange={(e) => setAnoCandidaturas(Number(e.target.value || 0))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1 md:col-span-2"><span className="text-slate-500">URL CSV/ZIP candidaturas TSE</span><input type="text" value={candidaturasCsvUrl} onChange={(e) => setCandidaturasCsvUrl(e.target.value)} placeholder="https://..." className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
          <label className="space-y-1"><span className="text-slate-500">Máx. linhas candidaturas</span><input type="number" min={1} value={candidaturasMaxLinhas} onChange={(e) => setCandidaturasMaxLinhas(Number(e.target.value || 1))} className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 text-slate-200" /></label>
        </div>
      </details>
    </div>
  );
}

function TopMetric({ label, value, tone }: { label: string; value: string; tone: string }) {
  return (
    <div className="rounded border border-slate-800 bg-black/40 py-2 px-3">
      <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className={`text-2xl ${tone}`}>{value}</p>
    </div>
  );
}

function riskTierStyle(level: FiscalPersonRanking['nivel_suspeita']): string {
  if (level === 'CRITICO') return 'border-red-500/80 bg-red-600/10 text-red-300';
  if (level === 'ALTO') return 'border-orange-500/80 bg-orange-600/10 text-orange-300';
  if (level === 'MEDIO') return 'border-amber-500/80 bg-amber-600/10 text-amber-300';
  if (level === 'BAIXO') return 'border-emerald-500/80 bg-emerald-600/10 text-emerald-300';
  if (level === 'MINIMO') return 'border-teal-500/80 bg-teal-600/10 text-teal-300';
  return 'border-slate-600 bg-slate-700/20 text-slate-300';
}
