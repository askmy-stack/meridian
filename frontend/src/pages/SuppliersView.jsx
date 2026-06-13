import { useState } from 'react';
import { useQuery } from 'react-query';
import { Factory, Search, ShieldAlert, TrendingUp } from 'lucide-react';
import { fetchSuppliers, fetchSupplierExplanation, fetchSupplierForecast } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { riskColor, riskPillClass } from '../lib/risk';

const FORECAST_HORIZONS = [7, 14, 30];

export function SuppliersView() {
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [forecastHorizon, setForecastHorizon] = useState(14);

  const suppliersQuery = useQuery(['suppliers'], () => fetchSuppliers({ limit: 100 }));
  const explanationQuery = useQuery(
    ['supplier-explanation', selectedId],
    () => fetchSupplierExplanation(selectedId),
    { enabled: Boolean(selectedId) },
  );
  const forecastQuery = useQuery(
    ['supplier-forecast', selectedId, forecastHorizon],
    () => fetchSupplierForecast(selectedId, forecastHorizon),
    { enabled: Boolean(selectedId) },
  );

  const suppliers = (suppliersQuery.data?.suppliers ?? []).filter(
    (s) =>
      !search ||
      s.name?.toLowerCase().includes(search.toLowerCase()) ||
      s.country_iso?.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="space-y-6">
      <DemoBanner />
      <div>
        <h1 className="page-title">Supplier Registry</h1>
        <p className="mt-2 text-slate-400">
          SCRI scores with SHAP explainability and TGN risk trajectory
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <Panel className="lg:col-span-2" title="Suppliers" subtitle={`${suppliers.length} in graph`}>
          <div className="relative mb-4">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="search"
              placeholder="Search name or country…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-900/50 border border-slate-700 text-sm text-white placeholder:text-slate-500 focus:border-blue-500/50 focus:outline-none"
            />
          </div>
          {suppliersQuery.isLoading && <LoadingState />}
          <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1">
            {suppliers.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setSelectedId(s.id)}
                className={`w-full text-left p-3 rounded-xl border transition-all ${
                  selectedId === s.id
                    ? 'border-blue-500/50 bg-blue-500/10'
                    : 'border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/30'
                }`}
              >
                <div className="flex justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium text-white truncate">{s.name}</p>
                    <p className="text-xs text-slate-500">{s.country_iso} · {s.city}</p>
                  </div>
                  {s.risk_score != null && (
                    <span className={`risk-pill shrink-0 ${riskPillClass(s.risk_score)}`}>
                      {Math.round(s.risk_score * 100)}%
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        </Panel>

        <Panel
          className="lg:col-span-3"
          title="SCRI explanation"
          subtitle={selectedId ? 'SHAP feature contributions' : 'Select a supplier'}
        >
          {!selectedId && (
            <div className="flex flex-col items-center py-16 text-slate-500">
              <Factory className="h-12 w-12 mb-3 opacity-40" />
              <p>Select a supplier to see why the model scored their risk</p>
            </div>
          )}
          {selectedId && explanationQuery.isLoading && <LoadingState />}
          {explanationQuery.data && (
            <div className="space-y-6">
              <div className="flex items-end gap-4">
                <p className="text-5xl font-bold" style={{ color: riskColor(explanationQuery.data.risk_score) }}>
                  {Math.round(explanationQuery.data.risk_score * 100)}%
                </p>
                <span className={`risk-pill mb-2 ${riskPillClass(explanationQuery.data.risk_score)}`}>
                  {explanationQuery.data.risk_category}
                </span>
                <MetricTooltip
                  label="SCRI"
                  definition="Supply Chain Risk Index — normalized 0–100% supplier disruption exposure."
                  reference="docs/METRICS.md"
                />
              </div>
              <div className="space-y-3">
                {(explanationQuery.data.explanations ?? []).map((item) => (
                  <div key={item.feature} className="p-4 rounded-xl bg-slate-900/50 border border-slate-700/50">
                    <div className="flex justify-between gap-2 mb-2">
                      <p className="font-medium text-white">{item.description || item.feature}</p>
                      <span className="text-xs text-slate-500">
                        {item.direction === 'increases' ? '↑ SCRI' : '↓ SCRI'}
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-blue-500 to-violet-500 rounded-full"
                        style={{ width: `${Math.min(Math.abs(item.contribution) * 100, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4">
                <div className="flex items-center gap-2 mb-3">
                  <TrendingUp className="h-4 w-4 text-violet-400" />
                  <p className="text-sm font-semibold text-violet-200">Risk trajectory</p>
                  <MetricTooltip
                    label="TGN forecast"
                    definition="7/14/30-day projected SCRI path (research track)."
                    reference="docs/METRICS.md#forecasting-tgn--research-track"
                  />
                </div>
                <div className="flex gap-2 mb-3">
                  {FORECAST_HORIZONS.map((days) => (
                    <button
                      key={days}
                      type="button"
                      onClick={() => setForecastHorizon(days)}
                      className={`px-3 py-1 text-xs rounded-lg border ${
                        forecastHorizon === days
                          ? 'border-violet-500/50 bg-violet-500/20 text-violet-200'
                          : 'border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      {days}d
                    </button>
                  ))}
                </div>
                {forecastQuery.isLoading && <LoadingState label="Loading forecast…" />}
                {forecastQuery.data && (
                  <p className="text-3xl font-bold text-white">
                    {Math.round((forecastQuery.data.predicted_risk_score ?? 0) * 100)}%
                    <span className="text-sm font-normal text-slate-500 ml-2">
                      projected · {forecastQuery.data.model === 'tgn' ? 'TGN' : 'LSTM'}
                    </span>
                  </p>
                )}
              </div>

              <p className="text-xs text-slate-600 flex items-center gap-1">
                <ShieldAlert className="h-3 w-3" />
                Model: {explanationQuery.data.model_version || 'xgboost-risk-scorer'}
              </p>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
