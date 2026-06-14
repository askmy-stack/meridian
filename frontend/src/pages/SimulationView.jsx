import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  BookOpen,
  Clock,
  GitCompare,
  Globe,
  Lightbulb,
  Play,
  ShieldAlert,
  TrendingDown,
  Users,
  Zap,
} from 'lucide-react';
import {
  compareSimulationScenarios,
  fetchMetricsMethodology,
  fetchSimulationScenarios,
  runSimulationScenario,
} from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { InteractiveWorldMap } from '../components/map/InteractiveWorldMap';
import { LoadingState } from '../components/ui/LoadingState';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { Panel } from '../components/ui/Panel';

function kpiDefinition(methodology, id, fallback) {
  return methodology?.kpis?.find((k) => k.id === id)?.definition ?? fallback;
}

export function SimulationView() {
  const location = useLocation();
  const [result, setResult] = useState(null);
  const [runningId, setRunningId] = useState(null);
  const [runError, setRunError] = useState(null);
  const [compareA, setCompareA] = useState('red-sea-bab-el-mandeb');
  const [compareB, setCompareB] = useState('suez-canal-blockage');
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);

  const { data, isLoading, isError, refetch } = useQuery(['simulation-scenarios'], fetchSimulationScenarios, {
    staleTime: 5 * 60_000,
  });

  const { data: methodology } = useQuery(['metrics-methodology'], fetchMetricsMethodology, {
    staleTime: 10 * 60_000,
    retry: 1,
  });

  const scenarios = data?.scenarios ?? [];
  const preselect = location.state?.scenarioId;

  const handleRun = async (scenarioId) => {
    setRunningId(scenarioId);
    setRunError(null);
    try {
      setResult(await runSimulationScenario(scenarioId));
    } catch {
      setResult(null);
      setRunError('Simulation failed — check API logs and Neo4j connectivity.');
    } finally {
      setRunningId(null);
    }
  };

  const handleCompare = async () => {
    setComparing(true);
    try {
      setCompareResult(await compareSimulationScenarios([compareA, compareB]));
    } catch {
      setCompareResult(null);
    } finally {
      setComparing(false);
    }
  };

  return (
    <div className="space-y-6">
      <DemoBanner />
      <header className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <p className="text-xs font-semibold uppercase tracking-widest text-amber-400">
              Scenario Engine
            </p>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-300 border border-amber-500/25">
              BFS · Monte Carlo · SCRI context
            </span>
          </div>
          <h1 className="page-title">Disruption Simulator</h1>
          <p className="mt-2 text-slate-400 max-w-2xl">
            Trade disruptions, port closures, sanctions, conflicts, shortages — BFS propagation plus
            1,000-iteration Monte Carlo with map visualization.
          </p>
          <a
            href="https://github.com/askmy-stack/meridian/blob/main/docs/METRICS.md#simulation-metrics"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 mt-3 text-xs text-amber-400 hover:text-amber-300"
          >
            <BookOpen className="h-3.5 w-3.5" />
            Simulation metrics methodology
          </a>
        </div>
        <Link to="/map" className="btn-ghost shrink-0">
          <Globe className="h-4 w-4" />
          Open world map
        </Link>
      </header>

      {isLoading && <LoadingState />}
      {isError && (
        <ErrorBanner
          message="Could not load simulation scenarios."
          onRetry={() => refetch()}
        />
      )}
      {runError && <ErrorBanner message={runError} />}
      {preselect && !result && (
        <p className="text-sm text-cyan-400">
          Copilot suggested scenario: <button type="button" className="underline" onClick={() => handleRun(preselect)}>{preselect}</button>
        </p>
      )}

      <Panel
        title="Compare scenarios"
        subtitle="Graph-derived propagation · Monte Carlo tail risk per docs/METRICS.md"
      >
        <div className="flex flex-col sm:flex-row gap-3 items-end">
          <label className="flex-1 text-sm text-slate-400">
            Scenario A
            <select
              value={compareA}
              onChange={(e) => setCompareA(e.target.value)}
              className="mt-1 w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </label>
          <label className="flex-1 text-sm text-slate-400">
            Scenario B
            <select
              value={compareB}
              onChange={(e) => setCompareB(e.target.value)}
              className="mt-1 w-full px-3 py-2 rounded-xl bg-slate-900 border border-slate-700 text-white"
            >
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </label>
          <button type="button" className="btn-primary shrink-0" disabled={comparing} onClick={handleCompare}>
            <GitCompare className="h-4 w-4" />
            {comparing ? 'Comparing…' : 'Compare'}
          </button>
        </div>
        {compareResult?.comparisons?.length > 0 && (
          <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
            {compareResult.comparisons.map((c) => (
              <div
                key={c.scenario_id}
                className={`p-4 rounded-xl border ${
                  c.scenario_id === compareResult.highest_impact
                    ? 'border-amber-500/40 bg-amber-500/10'
                    : 'border-slate-700'
                }`}
              >
                <p className="font-medium text-white">{c.name}</p>
                <p className="text-xs text-slate-500 mt-1">{c.region}</p>
                <p className="text-2xl font-bold text-white mt-2">{c.suppliers_affected} suppliers</p>
                <p className="text-sm text-slate-400 inline-flex items-center">
                  Disruption probability{' '}
                  {((c.monte_carlo?.disruption_probability ?? 0) * 100).toFixed(1)}%
                  <MetricTooltip
                    label="Disruption probability"
                    definition="Share of Monte Carlo runs exceeding the disruption threshold (≥1,000 iterations)."
                    reference="docs/METRICS.md#monte-carlo-financial-exposure"
                  />
                </p>
              </div>
            ))}
          </div>
        )}
      </Panel>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {scenarios.map((scenario) => (
          <article
            key={scenario.id}
            className="glass-panel p-6 flex flex-col hover:border-amber-500/30 transition-all"
          >
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-5 w-5 text-amber-400" aria-hidden />
              <h3 className="font-semibold text-white">{scenario.name}</h3>
            </div>
            <p className="text-xs text-violet-400 mb-2">{scenario.region}</p>
            <p className="text-sm text-slate-400 flex-1">{scenario.description}</p>
            <div className="mt-3 flex flex-wrap gap-1">
              {(scenario.sectors ?? []).map((s) => (
                <span key={s} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400">
                  {s.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <div className="mt-4 flex gap-2 text-xs text-slate-500">
              <span>Severity {(scenario.severity * 100).toFixed(0)}%</span>
              <span aria-hidden>·</span>
              <span>P={(scenario.probability * 100).toFixed(0)}%</span>
              <span aria-hidden>·</span>
              <span>{scenario.duration_days}d horizon</span>
            </div>
            <button
              type="button"
              disabled={runningId === scenario.id}
              onClick={() => handleRun(scenario.id)}
              className="btn-primary mt-5 w-full"
              aria-busy={runningId === scenario.id}
            >
              <Play className="h-4 w-4" />
              {runningId === scenario.id ? 'Simulating…' : 'Run scenario'}
            </button>
          </article>
        ))}
      </div>

      {result && (
        <>
          <Panel
            title={`Impact: ${result.scenario?.name}`}
            subtitle="BFS propagation + Monte Carlo · complements SCRI point scores"
          >
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4 mb-6">
              {[
                {
                  icon: Users,
                  label: 'Suppliers hit',
                  val: result.propagation?.suppliers_affected ?? 0,
                  sub: null,
                  tooltip: null,
                },
                {
                  icon: TrendingDown,
                  label: 'Revenue at risk',
                  val: `$${Number(result.propagation?.revenue_at_risk ?? 0).toLocaleString()}`,
                  sub: null,
                  tooltip: (
                    <MetricTooltip
                      label="Revenue at risk"
                      definition="Financial exposure from graph propagation — not a SCRI score."
                      reference="docs/METRICS.md#propagation-impact"
                    />
                  ),
                },
                {
                  icon: ShieldAlert,
                  label: 'Disruption prob.',
                  val: `${((result.monte_carlo?.disruption_probability ?? 0) * 100).toFixed(1)}%`,
                  sub: null,
                  tooltip: (
                    <MetricTooltip
                      label="Disruption probability"
                      definition={kpiDefinition(
                        methodology,
                        'probability_disruption',
                        'Share of Monte Carlo runs exceeding disruption threshold.',
                      )}
                      reference="docs/METRICS.md#monte-carlo-financial-exposure"
                    />
                  ),
                },
                {
                  icon: Clock,
                  label: 'Delay band (p10–p90)',
                  val: `${result.monte_carlo?.p10_delay_days ?? 0}–${result.monte_carlo?.p90_delay_days ?? 0}d`,
                  sub: `p50 ${result.monte_carlo?.p50_delay_days ?? 0}d`,
                  tooltip: (
                    <MetricTooltip
                      label="Delay percentiles"
                      definition="Monte Carlo delay distribution — p10/p50/p90 days across disrupted iterations (not a single point estimate)."
                      reference="docs/METRICS.md#monte-carlo-financial-exposure"
                    />
                  ),
                },
                {
                  icon: Clock,
                  label: 'Recovery est.',
                  val: `${result.propagation?.recovery_time_days ?? 0}d`,
                  sub: null,
                  tooltip: (
                    <MetricTooltip
                      label="Graph recovery"
                      definition="BFS propagation recovery estimate from knowledge graph — complements MC bands."
                      reference="docs/METRICS.md#propagation-impact"
                    />
                  ),
                },
              ].map(({ icon: Icon, label, val, sub, tooltip }) => (
                <div key={label} className="stat-card text-center py-4">
                  <Icon className="h-5 w-5 text-blue-400 mx-auto mb-2" aria-hidden />
                  <p className="text-2xl font-bold text-white">{val}</p>
                  {sub && <p className="text-[10px] text-slate-500 mt-0.5">{sub}</p>}
                  <p className="text-xs text-slate-500 mt-1 inline-flex items-center justify-center gap-0.5">
                    {label}
                    {tooltip}
                  </p>
                </div>
              ))}
            </div>
            <p className="text-sm text-slate-400">
              Monte Carlo: {result.monte_carlo?.iterations ?? 1000} iterations · Expected duration{' '}
              {result.monte_carlo?.expected_duration_days ?? 0} days (mean of disrupted runs) · Revenue band p50 $
              {Number(result.monte_carlo?.p50_revenue_at_risk ?? 0).toLocaleString()} · Timeline projection{' '}
              {result.map_overlay?.timeline_projection_days ?? 0} days to baseline recovery.
              {result.impact_summary?.headline && (
                <span className="block mt-2 text-slate-300">{result.impact_summary.headline}</span>
              )}
            </p>
          </Panel>

          {result.map_overlay && (
            <Panel title="Propagation on map">
              <InteractiveWorldMap
                layers={{}}
                simulationOverlay={result.map_overlay}
                height={400}
              />
            </Panel>
          )}

          {result.mitigations?.length > 0 && (
            <Panel title="Mitigation playbook" subtitle="Recommended actions — not LLM-generated SCRI scores">
              <ul className="space-y-2">
                {result.mitigations.map((item) => (
                  <li
                    key={item}
                    className="flex gap-2 text-sm text-slate-300 p-3 rounded-xl bg-slate-900/40 border border-slate-800"
                  >
                    <Lightbulb className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" aria-hidden />
                    {item}
                  </li>
                ))}
              </ul>
            </Panel>
          )}
        </>
      )}
    </div>
  );
}
