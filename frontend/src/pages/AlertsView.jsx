import { useState } from 'react';
import { useQuery } from 'react-query';
import { AlertTriangle, Bell, Info, AlertCircle, RefreshCw } from 'lucide-react';
import { fetchAlerts } from '../api/client';

const TIER_FILTERS = ['all', 'critical', 'warning', 'info'];

function normalizeTier(tier) {
  if (!tier) return 'INFO';
  return tier.toUpperCase();
}

export function AlertsView() {
  const [tierFilter, setTierFilter] = useState('all');

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery(
    ['alerts', tierFilter],
    () => fetchAlerts({ tier: tierFilter === 'all' ? undefined : tierFilter, limit: 100 }),
    { refetchInterval: 30_000 }
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
    switch (tier) {
      case 'CRITICAL':
        return <AlertTriangle className="h-5 w-5 text-red-600" />;
      case 'WARNING':
        return <AlertCircle className="h-5 w-5 text-orange-600" />;
      default:
        return <Info className="h-5 w-5 text-blue-600" />;
    }
  };

  const getTierClass = (tier) => {
    switch (tier) {
      case 'CRITICAL':
        return 'bg-red-50 border-red-200';
      case 'WARNING':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-blue-50 border-blue-200';
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Risk Alerts</h1>
          <p className="mt-2 text-gray-600">Monitor and manage supply chain risk alerts</p>
        </div>
        <button
          onClick={() => refetch()}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50"
          disabled={isFetching}
        >
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {TIER_FILTERS.map((t) => (
          <button
            key={t}
            onClick={() => setTierFilter(t)}
            className={`px-3 py-1.5 text-sm rounded-full border ${
              tierFilter === t
                ? 'bg-gray-900 text-white border-gray-900'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {t === 'all' ? 'All' : t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {isError && (
        <div className="p-4 rounded-md border border-red-200 bg-red-50 text-red-800">
          Failed to load alerts: {error?.message || 'Unknown error'}
        </div>
      )}

      {isLoading && (
        <div className="p-8 text-center text-gray-500">Loading alerts…</div>
      )}

      {/* Alert Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-red-50 rounded-lg p-4 border border-red-200">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5 text-red-600" />
            <span className="font-medium text-red-800">Critical</span>
          </div>
          <p className="mt-1 text-2xl font-semibold text-red-900">
            {alerts.filter(a => a.tier === 'CRITICAL').length}
          </p>
        </div>
        <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-orange-600" />
            <span className="font-medium text-orange-800">Warning</span>
          </div>
          <p className="mt-1 text-2xl font-semibold text-orange-900">
            {alerts.filter(a => a.tier === 'WARNING').length}
          </p>
        </div>
        <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <div className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-blue-600" />
            <span className="font-medium text-blue-800">Total</span>
          </div>
          <p className="mt-1 text-2xl font-semibold text-blue-900">{alerts.length}</p>
        </div>
      </div>

      {/* Alerts List */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Alerts</h2>
          
          <div className="space-y-4">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={`p-4 rounded-lg border ${getTierClass(alert.tier)}`}
              >
                <div className="flex items-start gap-4">
                  {getTierIcon(alert.tier)}
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-gray-900">{alert.title}</h3>
                      <span
                        className={`px-2 py-1 text-xs font-medium rounded ${
                          alert.tier === 'CRITICAL'
                            ? 'bg-red-100 text-red-800'
                            : alert.tier === 'WARNING'
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-blue-100 text-blue-800'
                        }`}
                      >
                        {alert.tier}
                      </span>
                    </div>
                    <p className="mt-1 text-gray-600">{alert.message}</p>
                    <div className="mt-2 flex items-center gap-4 text-sm text-gray-500">
                      <span>{new Date(alert.timestamp).toLocaleString()}</span>
                      {alert.entity && (
                        <span className="font-mono">Entity: {alert.entity}</span>
                      )}
                      {alert.entityType && (
                        <span>Type: {alert.entityType}</span>
                      )}
                      {typeof alert.riskScore === 'number' && (
                        <span>Risk: {(alert.riskScore * 100).toFixed(0)}%</span>
                      )}
                    </div>
                    {alert.recommendations.length > 0 && (
                      <ul className="mt-2 list-disc list-inside text-sm text-gray-600">
                        {alert.recommendations.map((rec, i) => (
                          <li key={i}>{rec}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          
          {!isLoading && alerts.length === 0 && (
            <div className="text-center py-12">
              <Bell className="h-12 w-12 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No alerts at this time</p>
              <p className="text-xs text-gray-400 mt-1">
                POST <code>/alerts/test</code> to emit a synthetic one in dev.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
