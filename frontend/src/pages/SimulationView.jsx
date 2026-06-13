import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
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
import { compareSimulationScenarios, fetchSimulationScenarios, runSimulationScenario } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { InteractiveWorldMap } from '../components/map/InteractiveWorldMap';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';

export function SimulationView() {
  const location = useLocation();
  const [result, setResult] = useState(null);
  const [runningId, setRunningId] = useState(null);
  const [compareA, setCompareA] = useState('red-sea-bab-el-mandeb');
  const [compareB, setCompareB] = useState('suez-canal-blockage');
  const [compareResult, setCompareResult] = useState(null);
  const [comparing, setComparing] = useState(false);

  const { data, isLoading } = useQuery(['simulation-scenarios'], fetchSimulationScenarios, {
    staleTime: 5 * 60_000,
  });

  const scenarios = data?.scenarios ?? [];
  const preselect = location.state?.scenarioId;

  const handleRun = async (scenarioId) => {
    setRunningId(scenarioId);
    try {
      setResult(await runSimulationScenario(scenarioId));
    } catch {
      setResult(null);
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
          <p className="text-xs font-semibold uppercase tracking-widest text-amber-400 mb-1">
            Scenario Engine
          </p>
          <h1 className="page-title">Disruption Simulator</h1>
          <p className="mt-2 text-slate-400 max-w-2xl">
            Trade disruptions, port closures, sanctions, conflicts, shortages — BFS propagation plus
            1,000-iteration Monte Carlo with map visualization.
          </p>
        </div>
        <Link to="/map" className="btn-ghost shrink-0">
          <Globe className="h-4 w-4" />
          Open world map
        </Link>
      </header>

      {isLoading && <LoadingState />}
      {preselect && !result && (
        <p className="text-sm text-cyan-400">
          Copilot suggested scenario: <button type="button" className="underline" onClick={() => handleRun(preselect)}>{preselect}</button>
        </p>
      )}

      <Panel title="Compare scenarios" subtitle="Side-by-side impact metrics (Phase 4)">
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
                <p className="text-sm text-slate-400">
                  P(disruption) {((c.monte_carlo?.disruption_probability ?? 0) * 100).toFixed(1)}%
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
            subtitle={result.impact_summary?.headline}
          >
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              {[
                { icon: Users, label: 'Suppliers hit', val: result.propagation?.suppliers_affected ?? 0 },
                {
                  icon: TrendingDown,
                  label: 'Revenue at risk',
                  val: `$${Number(result.propagation?.revenue_at_risk ?? 0).toLocaleString()}`,
                },
                {
                  icon: ShieldAlert,
                  label: 'Disruption prob.',
                  val: `${((result.monte_carlo?.disruption_probability ?? 0) * 100).toFixed(1)}%`,
                },
                {
                  icon: Clock,
                  label: 'Recovery est.',
                  val: `${result.propagation?.recovery_time_days ?? 0}d`,
                },
              ].map(({ icon: Icon, label, val }) => (
                <div key={label} className="stat-card text-center py-4">
                  <Icon className="h-5 w-5 text-blue-400 mx-auto mb-2" aria-hidden />
                  <p className="text-2xl font-bold text-white">{val}</p>
                  <p className="text-xs text-slate-500 mt-1">{label}</p>
                </div>
              ))}
            </div>
            <p className="text-sm text-slate-400">
              Monte Carlo: {result.monte_carlo?.iterations ?? 1000} iterations · Expected duration{' '}
              {result.monte_carlo?.expected_duration_days ?? 0} days · Timeline projection{' '}
              {result.map_overlay?.timeline_projection_days ?? 0} days to baseline recovery.
            </p>
          </Panel>

          {result.map_overlay && (
            <Panel title="Propagation on map" subtitle="Epicenter and affected suppliers">
              <InteractiveWorldMap
                layers={{}}
                simulationOverlay={result.map_overlay}
                height={400}
              />
            </Panel>
          )}

          {result.mitigations?.length > 0 && (
            <Panel title="Mitigation playbook" subtitle="Recommended actions">
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
