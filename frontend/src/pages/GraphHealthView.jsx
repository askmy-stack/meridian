import { useQuery } from 'react-query';
import { Activity, Database, MapPin, Network, Shield, Target } from 'lucide-react';
import { fetchBacktestSummary, fetchGraphHealth, fetchMetricsMethodology } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { StatCard } from '../components/ui/StatCard';

function pct(value, total) {
  if (!total) return '—';
  return `${Math.round((value / total) * 100)}%`;
}

export function GraphHealthView() {
  const healthQuery = useQuery(['graph-health'], fetchGraphHealth, { staleTime: 60_000 });
  const backtestQuery = useQuery(['backtest-summary'], fetchBacktestSummary, { staleTime: 120_000 });
  const methodologyQuery = useQuery(['metrics-methodology'], fetchMetricsMethodology, {
    staleTime: 120_000,
  });

  const health = healthQuery.data;
  const backtest = backtestQuery.data;
  const model = methodologyQuery.data?.model_status;
  const loading = healthQuery.isLoading;

  if (loading) return <LoadingState label="Loading graph health…" />;

  return (
    <div className="space-y-6">
      <DemoBanner />
      {healthQuery.isError && (
        <ErrorBanner
          message="Could not load graph health — Neo4j may be down or unseeded."
          onRetry={() => healthQuery.refetch()}
        />
      )}
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-emerald-400 mb-1">
          Ops · Graph completeness
        </p>
        <h1 className="page-title">Graph Health</h1>
        <p className="mt-2 text-slate-400 max-w-2xl">
          Knowledge graph coverage for portfolio demos — geo, events, tier-2 edges, and model calibration status.
        </p>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={<Database className="h-6 w-6" />}
          title="Suppliers"
          value={health?.suppliers ?? 0}
          subtitle={`${health?.suppliers_with_geo ?? 0} with coordinates`}
          accent="blue"
        />
        <StatCard
          icon={<MapPin className="h-6 w-6" />}
          title="Geo coverage"
          value={pct(health?.suppliers_with_geo, health?.suppliers)}
          subtitle={`${health?.suppliers_missing_geo ?? 0} missing lat/lon`}
          accent="green"
        />
        <StatCard
          icon={<Activity className="h-6 w-6" />}
          title="Events linked"
          value={health?.suppliers_with_events ?? 0}
          subtitle={`${health?.events ?? 0} total events`}
          accent="purple"
        />
        <StatCard
          icon={<Network className="h-6 w-6" />}
          title="Tier-2 edges"
          value={health?.tier2_link_count ?? 0}
          subtitle="SUPPLIES relationships"
          accent="amber"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Panel title="Completeness score" subtitle="Weighted geo · events · ports · tier coverage">
          <p className="text-5xl font-bold text-white tabular-nums">
            {health?.completeness_score != null
              ? `${Math.round(health.completeness_score * 100)}%`
              : '—'}
          </p>
          <ul className="mt-4 space-y-2 text-sm text-slate-400">
            <li>Suppliers without port links: {health?.suppliers_without_ports ?? 0}</li>
            <li>Graph status: {health?.status ?? 'unknown'}</li>
          </ul>
        </Panel>

        <Panel title="Model status" subtitle="SCRI calibration transparency">
          <div className="flex items-start gap-3">
            <Shield className="h-5 w-5 text-blue-400 mt-1" />
            <div className="space-y-2 text-sm">
              <p>
                <span className="text-slate-500">Source: </span>
                <span className="text-white">{model?.model_source ?? 'unknown'}</span>
              </p>
              <p>
                <span className="text-slate-500">Calibration: </span>
                <span className="text-white">{model?.calibration_status ?? methodologyQuery.data?.calibration_status ?? 'demo'}</span>
              </p>
              <p>
                <span className="text-slate-500">Labels validated: </span>
                <span className="text-white">{model?.labels_validated ? 'yes' : 'no'}</span>
              </p>
            </div>
          </div>
        </Panel>

        {backtest?.status === 'ok' && (
          <Panel title="SCRI backtest" subtitle="Digital twin lite — snapshot replay vs labels">
            <div className="flex items-start gap-3">
              <Target className="h-5 w-5 text-amber-400 mt-1" />
              <div className="grid grid-cols-2 gap-4 text-sm w-full">
                <div>
                  <p className="text-slate-500">Precision@{backtest.top_k ?? 10}</p>
                  <p className="text-2xl font-bold text-white tabular-nums">
                    {backtest.precision_at_k != null
                      ? `${Math.round(backtest.precision_at_k * 100)}%`
                      : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Recall</p>
                  <p className="text-2xl font-bold text-white tabular-nums">
                    {backtest.recall != null ? `${Math.round(backtest.recall * 100)}%` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Lead time (median)</p>
                  <p className="text-lg font-semibold text-white">
                    {backtest.lead_time_days_median != null
                      ? `${backtest.lead_time_days_median}d`
                      : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-slate-500">Labels evaluated</p>
                  <p className="text-lg font-semibold text-white">{backtest.evaluated_labels ?? 0}</p>
                </div>
              </div>
            </div>
          </Panel>
        )}
      </div>
    </div>
  );
}
