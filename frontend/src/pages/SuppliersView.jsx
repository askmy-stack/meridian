import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Factory, GitBranch, Layers, Search, ShieldAlert, TrendingUp } from 'lucide-react';
import { fetchSuppliers, fetchSupplierExplanation, fetchSupplierForecast } from '../api/client';
import { inferSupplierSector, SECTOR_PROFILES } from '../data/sectorIntelligence';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { LoadingState } from '../components/ui/LoadingState';
import { PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { RiskBar, RiskPill } from '../components/ui/RiskDisplay';
import { calibrationSublabel, useMethodology } from '../hooks/useMethodology';
import { riskColor, formatRiskPercent, riskLabel } from '../lib/risk';

const FORECAST_HORIZONS = [7, 14, 30];

export function SuppliersView() {
  const [selectedId, setSelectedId] = useState(null);
  const [search, setSearch] = useState('');
  const [sectorFilter, setSectorFilter] = useState('all');
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
  const { data: methodology } = useMethodology();
  const calLabel = calibrationSublabel(methodology);

  const enrichedSuppliers = (suppliersQuery.data?.suppliers ?? []).map((s) => ({
    ...s,
    sector: inferSupplierSector(s.name, s.industry),
    tier: s.tier ?? 1,
  }));

  const suppliers = enrichedSuppliers.filter((s) => {
    const matchesSearch =
      !search ||
      s.name?.toLowerCase().includes(search.toLowerCase()) ||
      s.country_iso?.toLowerCase().includes(search.toLowerCase());
    const matchesSector = sectorFilter === 'all' || s.sector === sectorFilter;
    return matchesSearch && matchesSector;
  });

  const selected = enrichedSuppliers.find((s) => s.id === selectedId);

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Supplier registry"
        title="Supplier Registry"
        subtitle="SCRI modelled index with SHAP explainability, sector assignment, and supply-chain tier — aligned with sector dashboard taxonomy."
        badges={['XGBoost · SHAP', `${suppliers.length} visible`]}
        gradient="blue"
        actions={
          <Link to="/sectors" className="btn-ghost">
            <Layers className="h-4 w-4" />
            Sector dashboard
          </Link>
        }
      />

      {suppliersQuery.isError && (
        <ErrorBanner
          message="Could not load suppliers — ensure Neo4j is seeded (`make seed-all`)."
          onRetry={() => suppliersQuery.refetch()}
        />
      )}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setSectorFilter('all')}
          className={`px-3 py-1.5 rounded-lg text-xs border ${
            sectorFilter === 'all'
              ? 'border-blue-500/50 bg-blue-500/15 text-blue-200'
              : 'border-slate-700 text-slate-400'
          }`}
        >
          All sectors
        </button>
        {Object.entries(SECTOR_PROFILES).map(([key, profile]) => (
          <button
            key={key}
            type="button"
            onClick={() => setSectorFilter(key)}
            className={`px-3 py-1.5 rounded-lg text-xs border capitalize ${
              sectorFilter === key
                ? 'border-violet-500/50 bg-violet-500/15 text-violet-200'
                : 'border-slate-700 text-slate-400'
            }`}
          >
            {profile.label}
          </button>
        ))}
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
                className={`risk-list-row min-h-[4.5rem] ${
                  selectedId === s.id
                    ? 'border-blue-500/50 bg-blue-500/10'
                    : 'border-slate-700/50 hover:border-slate-600 hover:bg-slate-800/30'
                }`}
              >
                <div className="risk-list-body min-w-0">
                  <p className="risk-list-title">{s.name}</p>
                  <div className="flex flex-wrap items-center gap-2 mt-1">
                    <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-violet-500/30 text-violet-300/90">
                      {SECTOR_PROFILES[s.sector]?.label || s.sector}
                    </span>
                    <span className="text-[10px] text-slate-500 flex items-center gap-0.5">
                      <GitBranch className="h-3 w-3" />
                      Tier {s.tier}
                    </span>
                    <span className="text-xs text-slate-500">
                      {s.country_iso} · {s.city}
                    </span>
                  </div>
                  {s.risk_score != null && (
                    <RiskBar score={s.risk_score} className="mt-1.5 sm:mt-2 md:hidden" />
                  )}
                </div>
                {s.risk_score != null && (
                  <RiskPill score={s.risk_score} size="sm" calibrationLabel={calLabel} />
                )}
              </button>
            ))}
          </div>
        </Panel>

        <Panel
          className="lg:col-span-3"
          title="SCRI explanation"
          subtitle={selectedId ? `${selected?.name} · Tier ${selected?.tier ?? 1}` : 'Select a supplier'}
        >
          {!selectedId && (
            <div className="flex flex-col items-center py-16 text-slate-500">
              <Factory className="h-12 w-12 mb-3 opacity-40" />
              <p>Select a supplier to see why the model scored their risk</p>
            </div>
          )}
          {selectedId && explanationQuery.isLoading && <LoadingState />}
          {selectedId && explanationQuery.isError && (
            <ErrorBanner
              message="Could not load SCRI explanation for this supplier."
              onRetry={() => explanationQuery.refetch()}
            />
          )}
          {explanationQuery.data && (
            <div className="space-y-6">
              {selected && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs px-2 py-1 rounded-lg border border-violet-500/30 text-violet-300">
                    {SECTOR_PROFILES[selected.sector]?.label}
                  </span>
                  <span className="text-xs px-2 py-1 rounded-lg border border-slate-600 text-slate-400">
                    Tier {selected.tier} supplier
                  </span>
                  {selected.parent_id && (
                    <span className="text-xs px-2 py-1 rounded-lg border border-slate-600 text-slate-400">
                      Reports to {selected.parent_id}
                    </span>
                  )}
                </div>
              )}

              <div className="flex flex-wrap items-end gap-3 sm:gap-4">
                <div>
                  <p
                    className="text-4xl sm:text-5xl font-bold tabular-nums"
                    style={{ color: riskColor(explanationQuery.data.risk_score) }}
                  >
                    {riskLabel(explanationQuery.data.risk_score)}
                  </p>
                  <p className="text-sm text-slate-500 mt-1">
                    {formatRiskPercent(explanationQuery.data.risk_score)}% modelled index
                    {explanationQuery.data.score_interval && (
                      <span className="text-slate-400">
                        {' '}
                        [{Math.round(explanationQuery.data.score_interval.lower * 100)}–
                        {Math.round(explanationQuery.data.score_interval.upper * 100)}%]
                      </span>
                    )}{' '}
                    · {calLabel}
                  </p>
                </div>
                <RiskPill
                  score={explanationQuery.data.risk_score}
                  variant="category"
                  label={explanationQuery.data.risk_category}
                  size="sm"
                  calibrationLabel={calLabel}
                  className="mb-1"
                />
                <MetricTooltip
                  label="SCRI"
                  definition="Supply Chain Risk Index — band-first modelled disruption exposure (0–100% secondary)."
                  limitations={methodology?.limitations}
                  reference="docs/LIMITATIONS.md"
                />
              </div>
              {explanationQuery.data.feature_provenance && (
                <p className="text-xs text-amber-200/80 bg-amber-500/10 border border-amber-500/20 rounded-lg px-3 py-2">
                  Data quality: {explanationQuery.data.feature_provenance.summary} — see docs/LIMITATIONS.md
                </p>
              )}
              {explanationQuery.data.pillar_scores && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(explanationQuery.data.pillar_scores).map(([pillar, score]) => (
                    <div
                      key={pillar}
                      className="rounded-lg border border-slate-700/60 bg-slate-900/40 px-3 py-2"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-slate-500">{pillar}</p>
                      <p className="text-lg font-semibold text-white tabular-nums">
                        {Math.round(score * 100)}%
                      </p>
                      <div className="risk-bar mt-1.5 h-1">
                        <div
                          className="risk-bar-fill bg-gradient-to-r from-cyan-500 to-blue-500"
                          style={{ width: `${Math.round(score * 100)}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
              <div className="space-y-3">
                {(explanationQuery.data.explanations ?? []).map((item) => (
                  <div key={item.feature} className="p-4 rounded-xl bg-slate-900/50 border border-slate-700/50">
                    <div className="flex justify-between gap-2 mb-2">
                      <p className="font-medium text-white">{item.description || item.feature}</p>
                      <span className="text-xs text-slate-500">
                        {item.direction === 'increases' ? '↑ SCRI' : '↓ SCRI'}
                      </span>
                    </div>
                    <div className="risk-bar mt-2">
                      <div
                        className="risk-bar-fill bg-gradient-to-r from-blue-500 to-violet-500"
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
                  <>
                    <span
                      className={`inline-flex text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border mb-2 ${
                        forecastQuery.data.model === 'tgn'
                          ? 'border-violet-500/40 text-violet-300 bg-violet-500/10'
                          : 'border-amber-500/40 text-amber-300 bg-amber-500/10'
                      }`}
                    >
                      {forecastQuery.data.model === 'tgn'
                        ? 'Research track · TGN'
                        : 'Research track · LSTM fallback'}
                    </span>
                    <p className="text-3xl font-bold text-white">
                      {Math.round((forecastQuery.data.predicted_risk_score ?? 0) * 100)}%
                      <span className="text-sm font-normal text-slate-500 ml-2">projected band path</span>
                    </p>
                  </>
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
