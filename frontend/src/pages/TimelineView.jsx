import { useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { Link } from 'react-router-dom';
import { AlertTriangle, Calendar, ChevronRight, Globe } from 'lucide-react';
import { fetchEventTimeline } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { RiskPill } from '../components/ui/RiskDisplay';
import { buildDailyTimeline } from '../lib/timelineUtils';
import { riskColor } from '../lib/risk';

export function TimelineView() {
  const [days, setDays] = useState(90);

  const { data, isLoading, isError } = useQuery(
    ['event-timeline', days],
    () => fetchEventTimeline({ days }),
    { staleTime: 60_000 },
  );

  const dailyEntries = useMemo(
    () => buildDailyTimeline(data?.events ?? [], days),
    [data?.events, days],
  );

  const eventCount = dailyEntries.filter((e) => e.kind === 'event').length;
  const digestCount = dailyEntries.filter((e) => e.kind === 'digest').length;

  return (
    <div className="space-y-8 max-w-4xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Event Intelligence"
        title="Geopolitical Timeline"
        subtitle="One update per day over your selected window — graph-linked events plus daily monitoring digests."
        badges={[`${days}-day window`, `${dailyEntries.length} daily entries`]}
        gradient="violet"
      >
        <label className="flex items-center gap-3 text-sm text-slate-400 max-w-lg pt-1">
          <Calendar className="h-4 w-4 shrink-0" />
          <span className="shrink-0 w-20 tabular-nums">{days} days</span>
          <input
            type="range"
            min={7}
            max={90}
            step={1}
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="flex-1 accent-violet-500"
            aria-label="Timeline window in days"
          />
        </label>
        <p className="text-xs text-slate-500">
          {eventCount} graph events · {digestCount} routine digests (template on quiet days)
        </p>
      </PageHeader>

      {isLoading && <LoadingState label="Loading timeline…" />}
      {isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm" role="alert">
          Could not load timeline — run <code>make seed-demo</code> after Neo4j is up.
        </div>
      )}

      <div className="relative max-h-[70vh] overflow-y-auto pr-1">
        <div className="absolute left-4 top-0 bottom-0 w-px bg-slate-700/80 hidden sm:block" aria-hidden />
        <ul className="space-y-3" role="list">
          {dailyEntries.map((evt) => (
            <li key={evt.id} className="relative sm:pl-12">
              <span
                className="hidden sm:flex absolute left-2.5 top-6 w-3 h-3 rounded-full border-2 border-slate-900"
                style={{ backgroundColor: riskColor(evt.severity ?? 0.5) }}
                aria-hidden
              />
              <Panel className="hover:border-violet-500/30 transition-colors">
                <div className="flex flex-col sm:flex-row sm:items-start gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      <time className="text-xs font-mono text-slate-500">{evt.date}</time>
                      <RiskPill score={evt.severity ?? 0.5} size="sm" />
                      <span className="text-xs text-slate-500 capitalize">
                        {evt.event_type?.replace(/_/g, ' ')}
                      </span>
                      {evt.source === 'template' && (
                        <span className="text-[10px] uppercase tracking-wider px-1.5 py-0.5 rounded border border-amber-500/30 text-amber-300/80">
                          demo digest
                        </span>
                      )}
                    </div>
                    <h3 className="font-semibold text-white">{evt.title}</h3>
                    <p className="text-sm text-slate-400 mt-1">{evt.description}</p>
                    {evt.affected_suppliers?.length > 0 && (
                      <p className="text-xs text-slate-500 mt-2">
                        Affected: {evt.affected_suppliers.slice(0, 3).join(', ')}
                        {evt.affected_suppliers.length > 3
                          ? ` +${evt.affected_suppliers.length - 3} more`
                          : ''}
                      </p>
                    )}
                  </div>
                  {evt.kind === 'event' && (
                    <Link
                      to="/map"
                      className="btn-ghost text-xs shrink-0 self-start"
                      aria-label={`View ${evt.title} on map`}
                    >
                      <Globe className="h-3.5 w-3.5" />
                      Map
                      <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>
              </Panel>
            </li>
          ))}
        </ul>
        {dailyEntries.length === 0 && !isLoading && (
          <p className="text-center text-slate-500 py-12 flex items-center justify-center gap-2">
            <Calendar className="h-5 w-5" />
            No entries in window — seed demo data first
          </p>
        )}
      </div>

      <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 flex gap-3 text-sm text-amber-100/90">
        <AlertTriangle className="h-5 w-5 shrink-0 text-amber-400" />
        <p>
          Quiet days show template monitoring digests (clearly labelled). Graph-linked events come from Neo4j.
          Live GDELT/ACLED ingestion will replace digests when the Kafka pipeline is connected.
        </p>
      </div>
    </div>
  );
}
