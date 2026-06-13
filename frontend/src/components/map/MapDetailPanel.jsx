import { AlertTriangle, Globe, Info, MapPin, Ship, Users } from 'lucide-react';
import { riskPillClass } from '../../lib/risk';

/**
 * Side panel for map drill-down — explains what / where / why / who / impact.
 */
export function MapDetailPanel({ feature, onClose }) {
  if (!feature) {
    return (
      <div className="glass-panel p-6 h-full flex flex-col items-center justify-center text-center text-slate-500">
        <Globe className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm">Click a zone, event, or supplier on the map to see intelligence context.</p>
      </div>
    );
  }

  const isZone = feature.layer?.includes('conflict') || feature.category;
  const isEvent = feature.event_type;

  return (
    <div className="glass-panel p-5 h-full overflow-y-auto space-y-4" role="region" aria-label="Map detail">
      <div className="flex justify-between gap-2">
        <h3 className="font-semibold text-white text-lg leading-tight">
          {feature.name || feature.title || feature.id}
        </h3>
        {feature.risk_score != null && (
          <span className={`risk-pill shrink-0 ${riskPillClass(feature.risk_score)}`}>
            {Math.round(feature.risk_score * 100)}%
          </span>
        )}
      </div>

      {feature.summary && (
        <p className="text-sm text-slate-400">{feature.summary}</p>
      )}
      {feature.description && (
        <p className="text-sm text-slate-400">{feature.description}</p>
      )}

      <dl className="space-y-3 text-sm">
        {feature.region && (
          <div className="flex gap-2">
            <dt className="text-slate-500 shrink-0 flex items-center gap-1"><MapPin className="h-3.5 w-3.5" /> Where</dt>
            <dd className="text-slate-300">{feature.region}</dd>
          </div>
        )}
        {feature.country && (
          <div className="flex gap-2">
            <dt className="text-slate-500 shrink-0">Country</dt>
            <dd className="text-slate-300">{feature.country}</dd>
          </div>
        )}
        {feature.event_type && (
          <div className="flex gap-2">
            <dt className="text-slate-500 shrink-0 flex items-center gap-1"><AlertTriangle className="h-3.5 w-3.5" /> What</dt>
            <dd className="text-slate-300 capitalize">{feature.event_type.replace(/_/g, ' ')}</dd>
          </div>
        )}
        {feature.supplier_name && (
          <div className="flex gap-2">
            <dt className="text-slate-500 shrink-0 flex items-center gap-1"><Users className="h-3.5 w-3.5" /> Who</dt>
            <dd className="text-slate-300">{feature.supplier_name}</dd>
          </div>
        )}
        {feature.sectors && (
          <div className="flex gap-2">
            <dt className="text-slate-500 shrink-0 flex items-center gap-1"><Ship className="h-3.5 w-3.5" /> Sectors</dt>
            <dd className="text-slate-300">{feature.sectors.join(', ')}</dd>
          </div>
        )}
      </dl>

      <div className="rounded-xl border border-blue-500/20 bg-blue-500/5 p-3 text-xs text-blue-200/90">
        <p className="flex items-center gap-1.5 font-medium mb-1">
          <Info className="h-3.5 w-3.5" /> Why it matters
        </p>
        <p>
          {isZone && 'Operational exposure in this zone propagates through chokepoints to tier-1 suppliers and SKUs.'}
          {isEvent && 'Active signal linked to your supplier graph — elevated risk may appear in digest and alerts within 24h.'}
          {!isZone && !isEvent && 'Node in your knowledge graph — trace dependencies in Supply Graph or run a simulation.'}
        </p>
      </div>

      {onClose && (
        <button type="button" onClick={onClose} className="btn-ghost w-full text-xs">
          Clear selection
        </button>
      )}
    </div>
  );
}
