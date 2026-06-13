import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Globe, Play, X, Zap } from 'lucide-react';
import { fetchSupplierExplanation } from '../api/client';
import { riskColor, riskLabel, riskPillClass } from '../lib/risk';

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

  if (!entity) return null;

  const score = entity.risk_score ?? explanation?.risk_score;
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
                <span className="text-sm text-slate-400">Risk score</span>
                <span className={`risk-pill text-xs ${riskPillClass(score)}`}>{riskLabel(score)}</span>
              </div>
              <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${score * 100}%`, backgroundColor: riskColor(score) }}
                />
              </div>
              <p className="text-2xl font-bold text-white mt-2">{Math.round(score * 100)}%</p>
            </div>
          )}

          {entity.country && (
            <p className="text-sm text-slate-400">
              Country: <span className="text-slate-200">{entity.country}</span>
            </p>
          )}

          {explanation?.shap_features?.length > 0 && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-400 mb-2">SHAP drivers</p>
              <ul className="space-y-2">
                {explanation.shap_features.slice(0, 5).map((f) => (
                  <li key={f.feature} className="flex justify-between text-sm">
                    <span className="text-slate-400">{f.feature}</span>
                    <span className={f.impact >= 0 ? 'text-red-400' : 'text-emerald-400'}>
                      {f.impact >= 0 ? '+' : ''}{(f.impact * 100).toFixed(1)}%
                    </span>
                  </li>
                ))}
              </ul>
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
