import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Globe, Play, TrendingUp, X, Zap } from 'lucide-react';
import { fetchSupplierExplanation, fetchSupplierForecast } from '../api/client';
import { MetricTooltip } from './ui/MetricTooltip';
import { RiskBar, RiskPill } from './ui/RiskDisplay';
import { calibrationSublabel, useMethodology } from '../hooks/useMethodology';
import { formatRiskPercent, riskLabel } from '../lib/risk';

/**
 * Slide-over panel for any graph entity — unified across map, network, timeline.
 */
export function EntityDrawer({ entity, onClose }) {
  const supplierId = entity?.type === 'supplier' ? entity.id : null;

  const { data: explanation } = useQuery(
    ['supplier-explanation', supplierId],
    () => fetchSupplierExplanation(supplierId),
    { enabled: Boolean(supplierId), staleTime: 120_000 },
  );

  const { data: forecast } = useQuery(
    ['supplier-forecast', supplierId],
    () => fetchSupplierForecast(supplierId, 14),
    { enabled: Boolean(supplierId), staleTime: 120_000 },
  );
  const { data: methodology } = useMethodology();
  const calLabel = calibrationSublabel(methodology);

  if (!entity) return null;

  const score = entity.risk_score ?? explanation?.risk_score;
  const shapFactors = explanation?.explanations ?? explanation?.shap_features ?? [];
  const mapHref = entity.coordinates
    ? `/map?lat=${entity.coordinates[1]}&lon=${entity.coordinates[0]}&highlight=${entity.id ?? ''}`
    : `/map?highlight=${entity.id ?? ''}`;

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Entity details">
      <button
        type="button"
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-label="Close panel"
        onClick={onClose}
      />
      <aside className="relative w-full max-w-md h-full overflow-y-auto border-l border-slate-700 bg-[#0a1020] shadow-2xl animate-in slide-in-from-right">
        <div className="sticky top-0 z-10 flex items-center justify-between p-4 border-b border-slate-800 bg-[#0a1020]/95 backdrop-blur">
          <div>
            <p className="text-[10px] uppercase tracking-widest text-slate-500">{entity.type}</p>
            <h2 className="text-lg font-semibold text-white">{entity.name}</h2>
          </div>
          <button type="button" onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800 text-slate-400">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {typeof score === 'number' && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-slate-400 inline-flex items-center">
                  SCRI
                  <MetricTooltip
                    label="SCRI"
                    definition="Supply Chain Risk Index — band-first modelled index from XGBoost + SHAP."
                    limitations={methodology?.limitations}
                    reference="docs/LIMITATIONS.md"
                  />
                </span>
                <RiskPill score={score} variant="category" size="sm" calibrationLabel={calLabel} />
              </div>
              <RiskBar score={score} />
              <p className="text-2xl font-bold text-white mt-2 tabular-nums">
                {riskLabel(score)}
                <span className="text-sm font-normal text-slate-500 ml-2">
                  {formatRiskPercent(score)}% · {calLabel}
                </span>
              </p>
              {explanation?.feature_provenance && (
                <p className="text-xs text-amber-200/80 mt-2">
                  Data quality: {explanation.feature_provenance.summary}
                </p>
              )}
            </div>
          )}

          {entity.country && (
            <p className="text-sm text-slate-400">
              Country: <span className="text-slate-200">{entity.country}</span>
            </p>
          )}

          {shapFactors.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-400 mb-2">
                SHAP drivers
              </p>
              <ul className="space-y-2">
                {shapFactors.slice(0, 5).map((f) => {
                  const impact = f.contribution ?? f.impact ?? 0;
                  const label = f.description || f.feature;
                  return (
                    <li key={f.feature} className="flex justify-between text-sm gap-3">
                      <span className="text-slate-400 truncate">{label}</span>
                      <span className={impact >= 0 ? 'text-red-400 shrink-0' : 'text-emerald-400 shrink-0'}>
                        {impact >= 0 ? '+' : ''}{(impact * 100).toFixed(1)}%
                      </span>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {forecast && supplierId && (
            <div className="rounded-xl border border-slate-700/60 bg-slate-900/40 p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-4 w-4 text-violet-400" />
                <p className="text-xs font-semibold uppercase tracking-widest text-violet-300">
                  {forecast.horizon_days ?? 14}-day forecast
                </p>
                <MetricTooltip
                  label="TGN forecast"
                  definition="Research-track risk trajectory — complements SCRI point score, not a replacement."
                  reference={forecast.methodology || 'docs/METRICS.md#forecasting-tgn--research-track'}
                />
              </div>
              <p className="text-2xl font-bold text-white">
                {Math.round((forecast.predicted_risk_score ?? 0) * 100)}%
                <span className="text-sm font-normal text-slate-500 ml-2">
                  {forecast.model === 'tgn' ? 'TGN' : 'LSTM fallback'}
                </span>
              </p>
              {forecast.detected_patterns?.length > 0 && (
                <p className="text-xs text-slate-500 mt-2">{forecast.detected_patterns[0]}</p>
              )}
            </div>
          )}

          <div className="flex flex-col gap-2 pt-2">
            <Link to={mapHref} className="btn-ghost w-full justify-center" onClick={onClose}>
              <Globe className="h-4 w-4" />
              View on map
            </Link>
            <Link to="/simulate" className="btn-primary w-full justify-center" onClick={onClose}>
              <Play className="h-4 w-4" />
              Run scenario
            </Link>
            {supplierId && (
              <Link
                to={`/suppliers?highlight=${supplierId}`}
                className="btn-ghost w-full justify-center"
                onClick={onClose}
              >
                <Zap className="h-4 w-4" />
                Full supplier profile
              </Link>
            )}
          </div>
        </div>
      </aside>
    </div>
  );
}
