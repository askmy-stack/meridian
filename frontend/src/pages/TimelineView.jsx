import { useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, Calendar, ChevronRight, Globe } from 'lucide-react';
import { fetchEventTimeline } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { useEntityDrawer } from '../context/EntityDrawerContext';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { riskColor, riskPillClass } from '../lib/risk';

export function TimelineView() {
  const [days, setDays] = useState(30);
  const { openEntity } = useEntityDrawer();

  const { data, isLoading, isError } = useQuery(
    ['event-timeline', days],
    () => fetchEventTimeline({ days }),
    { staleTime: 60_000 },
  );

  const events = data?.events ?? [];

  return (
    <div className="space-y-6">
      <DemoBanner />
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-400 mb-1">
          Event Intelligence
        </p>
        <h1 className="page-title">Geopolitical Timeline</h1>
        <p className="mt-2 text-slate-400">
          Chronological feed of active signals mapped to your supplier network.
        </p>
        <label className="mt-4 flex items-center gap-3 text-sm text-slate-400 max-w-md">
          <Calendar className="h-4 w-4 shrink-0" />
          <span className="shrink-0 w-16">{days}d window</span>
          <input
            type="range"
            min={7}
            max={90}
            step={7}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="flex-1 accent-violet-500"
            aria-label="Timeline window in days"
          />
        </label>
      </header>

      {isLoading && <LoadingState label="Loading timeline…" />}
      {isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm" role="alert">
          Could not load timeline — run <code>make seed-demo</code> after Neo4j is up.
        </div>
      )}

      <div className="relative">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-700/80 hidden sm:block" aria-hidden />
        <ul className="space-y-4" role="list">
          {events.map((evt, idx) => (
            <li key={evt.id} className="relative sm:pl-12">
              <span
                className="hidden sm:flex absolute left-2.5 top-5 w-3 h-3 rounded-full border-2 border-slate-900"
                style={{ backgroundColor: riskColor(evt.severity ?? 0.5) }}
                aria-hidden
              />
              <Panel className="hover:border-violet-500/30 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <span className={`risk-pill text-[10px] ${riskPillClass(evt.severity)}`}>
                        {Math.round((evt.severity ?? 0) * 100)}%
                      </span>
                      <span className="text-xs text-slate-500 capitalize">
                        {evt.event_type?.replace(/_/g, ' ')}
                      </span>
                    </div>
                    <h3 className="font-semibold text-white">{evt.title}</h3>
                    <p className="text-sm text-slate-400 mt-1">{evt.description}</p>
                    {evt.affected_suppliers?.length > 0 && (
                      <p className="text-xs text-slate-500 mt-2">
                        Affected: {evt.affected_suppliers.join(', ')}
                      </p>
                    )}
                  </div>
                  <Link
                    to="/map"
                    className="btn-ghost text-xs shrink-0 self-start"
                    aria-label={`View ${evt.title} on map`}
                  >
                    <Globe className="h-3.5 w-3.5" />
                    Map
                    <ChevronRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </Panel>
            </li>
          ))}
        </ul>
        {events.length === 0 && !isLoading && (
          <p className="text-center text-slate-500 py-12 flex items-center justify-center gap-2">
            <Calendar className="h-5 w-5" />
            No events in window — seed demo data first
          </p>
        )}
      </div>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex gap-3 text-sm text-amber-100/90">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
        <p>
          Timeline reflects seeded and graph-linked events. Live GDELT/ACLED ingestion will append here when the Kafka pipeline is connected.
        </p>
      </div>
    </div>
  );
}
