/**
 * Normalize and deduplicate network graph nodes from /visualization/network.
 */

const TYPE_LABELS = {
  supplier: 'Supplier',
  port: 'Port',
  chokepoint: 'Chokepoint',
  sku: 'SKU',
  region: 'Region',
  event: 'Event',
  country: 'Country',
  unknown: 'Entity',
};

const TYPE_ALIASES = {
  suppliers: 'supplier',
  ports: 'port',
  chokepoints: 'chokepoint',
  events: 'event',
  regions: 'region',
};

/** Resolve display type from node properties and Neo4j labels. */
export function normalizeNodeType(node) {
  const raw = (node?.type || node?.entity_type || 'unknown').toString().toLowerCase().trim();
  const canonical = TYPE_ALIASES[raw] || raw;
  if (canonical !== 'unknown' && TYPE_LABELS[canonical]) {
    return { key: canonical, label: TYPE_LABELS[canonical] };
  }

  const id = (node?.id || '').toLowerCase();
  const label = (node?.label || '').toLowerCase();
  if (id.includes('port') || label.includes('port')) return { key: 'port', label: 'Port' };
  if (id.includes('choke') || label.includes('strait') || label.includes('canal')) {
    return { key: 'chokepoint', label: 'Chokepoint' };
  }
  if (id.includes('event') || node?.event_type) return { key: 'event', label: 'Event' };
  if (node?.country && !node?.risk_score) return { key: 'region', label: 'Region' };
  if (node?.risk_score != null || node?.critical != null) {
    return { key: 'supplier', label: 'Supplier' };
  }
  return { key: 'unknown', label: 'Entity' };
}

/** Best-effort risk score across entity types. */
export function resolveNodeRiskScore(node) {
  const score =
    node?.risk_score ??
    node?.congestion_score ??
    node?.current_risk_score ??
    node?.severity ??
    null;
  if (score == null || Number.isNaN(Number(score))) return null;
  return Number(score);
}

/** Deduplicate nodes by id, keeping highest risk score. */
export function dedupeNetworkNodes(nodes = []) {
  const byId = new Map();
  for (const node of nodes) {
    const id = node?.id;
    if (!id) continue;
    const existing = byId.get(id);
    const risk = resolveNodeRiskScore(node);
    const normalized = {
      ...node,
      type: normalizeNodeType(node).key,
      typeLabel: normalizeNodeType(node).label,
      risk_score: risk ?? existing?.risk_score ?? null,
    };
    if (!existing) {
      byId.set(id, normalized);
      continue;
    }
    const existingRisk = resolveNodeRiskScore(existing) ?? 0;
    const newRisk = risk ?? 0;
    if (newRisk >= existingRisk) {
      byId.set(id, { ...existing, ...normalized });
    }
  }
  return Array.from(byId.values()).sort((a, b) => (b.risk_score ?? 0) - (a.risk_score ?? 0));
}
