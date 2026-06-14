/**
 * Expand sparse API events into one daily timeline entry per day (demo-friendly).
 */

const ROUTINE_TEMPLATES = [
  'Routine graph scan — no new CRITICAL band crossings.',
  'GDELT tone stable; ACLED conflict density unchanged in watched regions.',
  'AIS lane throughput within seasonal norms for major chokepoints.',
  'Supplier SCRI refresh — modelled index bands unchanged for portfolio.',
  'Weather and sanctions layers reviewed — no new exposure flags.',
];

function dayKey(date) {
  return date.toISOString().slice(0, 10);
}

function parseDate(value) {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * @param {object[]} events - from /geopolitical/timeline
 * @param {number} days - window length (7–90)
 * @returns {object[]} one entry per calendar day, newest first
 */
export function buildDailyTimeline(events = [], days = 90) {
  const end = new Date();
  end.setHours(12, 0, 0, 0);
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);

  const byDay = new Map();
  for (const evt of events) {
    const when = parseDate(evt.occurred_at) || parseDate(evt.resolved_at) || end;
    const key = dayKey(when);
    if (!byDay.has(key)) byDay.set(key, []);
    byDay.get(key).push(evt);
  }

  const entries = [];
  const cursor = new Date(start);
  let templateIdx = 0;

  while (cursor <= end) {
    const key = dayKey(cursor);
    const dayEvents = byDay.get(key) || [];

    if (dayEvents.length > 0) {
      for (const evt of dayEvents) {
        entries.push({
          id: `${key}-${evt.id}`,
          date: key,
          kind: 'event',
          title: evt.title || 'Geopolitical signal',
          description: evt.description || evt.event_type?.replace(/_/g, ' ') || 'Graph-linked event',
          severity: evt.severity ?? 0.5,
          event_type: evt.event_type,
          affected_suppliers: evt.affected_suppliers || [],
          source: 'neo4j',
        });
      }
    } else {
      entries.push({
        id: `daily-${key}`,
        date: key,
        kind: 'digest',
        title: 'Daily intelligence digest',
        description: ROUTINE_TEMPLATES[templateIdx % ROUTINE_TEMPLATES.length],
        severity: 0.15 + (templateIdx % 5) * 0.03,
        event_type: 'monitoring',
        affected_suppliers: [],
        source: 'template',
      });
      templateIdx += 1;
    }

    cursor.setDate(cursor.getDate() + 1);
  }

  return entries.reverse();
}
