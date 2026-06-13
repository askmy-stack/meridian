import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { AlertTriangle, Bell, Globe, Info, AlertCircle, RefreshCw, Zap } from 'lucide-react';
import { fetchAlerts, fetchAlertStats, sendTestAlert } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';

const TIER_FILTERS = ['all', 'critical', 'warning', 'info'];

function normalizeTier(tier) {
  if (!tier) return 'INFO';
  return tier.toUpperCase();
}

const TIER_STYLES = {
  CRITICAL: 'border-red-500/30 bg-red-500/10',
  WARNING: 'border-orange-500/30 bg-orange-500/10',
  INFO: 'border-blue-500/30 bg-blue-500/10',
};

export function AlertsView() {
  const [tierFilter, setTierFilter] = useState('all');
  const [testPending, setTestPending] = useState(false);

  const statsQuery = useQuery(['alert-stats'], fetchAlertStats, { refetchInterval: 30_000 });
  const { data, isLoading, isError, error, refetch, isFetching } = useQuery(
    ['alerts', tierFilter],
    () => fetchAlerts({ tier: tierFilter === 'all' ? undefined : tierFilter, limit: 100 }),
    { refetchInterval: 30_000 },
  );

  const alerts = (data?.alerts ?? []).map((a, idx) => ({
    id: `${a.timestamp}-${idx}`,
    tier: normalizeTier(a.tier),
    title: a.title,
    message: a.message,
    timestamp: a.timestamp,
    entity: a.entity_id,
    entityType: a.entity_type,
    riskScore: a.risk_score,
    recommendations: a.recommendations || [],
  }));

  const getTierIcon = (tier) => {
    if (tier === 'CRITICAL') return <AlertTriangle className="h-5 w-5 text-red-400" />;
    if (tier === 'WARNING') return <AlertCircle className="h-5 w-5 text-orange-400" />;
    return <Info className="h-5 w-5 text-blue-400" />;
  };

  return (
    <div className="space-y-6">
      <DemoBanner />
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Risk Alerts</h1>
          <p className="mt-2 text-slate-400">Real-time supply chain disruption notifications</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => refetch()} disabled={isFetching} className="btn-ghost">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            type="button"
            disabled={testPending}
            className="btn-primary"
            onClick={async () => {
              setTestPending(true);
              try {
                await sendTestAlert();
                refetch();
                statsQuery.refetch();
              } finally {
                setTestPending(false);
              }
            }}
          >
            <Zap className="h-4 w-4" />
            {testPending ? 'Emitting…' : 'Emit test alert'}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {TIER_FILTERS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTierFilter(t)}
            className={`px-4 py-2 text-sm rounded-xl border transition-all capitalize ${
              tierFilter === t
                ? 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                : 'border-slate-700 text-slate-400 hover:border-slate-600'
            }`}
          >
            {t === 'all' ? 'All tiers' : t}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { label: 'Critical', val: statsQuery.data?.by_tier?.critical ?? alerts.filter((a) => a.tier === 'CRITICAL').length, color: 'text-red-400' },
          { label: 'Warning', val: statsQuery.data?.by_tier?.warning ?? alerts.filter((a) => a.tier === 'WARNING').length, color: 'text-orange-400' },
          { label: 'Total', val: statsQuery.data?.total ?? alerts.length, color: 'text-blue-400' },
        ].map(({ label, val, color }) => (
          <div key={label} className="stat-card text-center">
            <p className={`text-3xl font-bold ${color}`}>{val}</p>
            <p className="text-sm text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <Panel title="Alert feed" subtitle="Newest first · auto-refreshes every 30s">
        {isError && (
          <p className="text-red-400 text-sm mb-4">Failed to load: {error?.message}</p>
        )}
        {isLoading && <LoadingState label="Loading alerts…" />}
        {!isLoading && alerts.length === 0 && (
          <div className="text-center py-12">
            <Bell className="h-12 w-12 text-slate-600 mx-auto mb-3" />
            <p className="text-slate-400">No alerts yet — emit a test alert to demo the pipeline</p>
          </div>
        )}
        <div className="space-y-3">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 rounded-xl border ${TIER_STYLES[alert.tier] || TIER_STYLES.INFO}`}
            >
              <div className="flex gap-3">
                {getTierIcon(alert.tier)}
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-white">{alert.title}</h3>
                    <span className="risk-pill text-[10px] bg-black/20">{alert.tier}</span>
                  </div>
                  <p className="text-sm text-slate-300 mt-1">{alert.message}</p>
                  <p className="text-xs text-slate-500 mt-2">
                    {new Date(alert.timestamp).toLocaleString()}
                    {alert.entity && ` · ${alert.entity}`}
                    {typeof alert.riskScore === 'number' && ` · ${(alert.riskScore * 100).toFixed(0)}% risk`}
                  </p>
                  {alert.entity && (
                    <Link
                      to={`/map?highlight=${encodeURIComponent(alert.entity)}`}
                      className="inline-flex items-center gap-1 mt-3 text-xs text-blue-400 hover:text-blue-300"
                    >
                      <Globe className="h-3.5 w-3.5" />
                      View on map
                    </Link>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
