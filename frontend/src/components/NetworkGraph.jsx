import { useMemo, useState } from 'react';

/**
 * Lightweight SVG network graph (radial layout — no physics simulation).
 *
 * Renders nodes on concentric rings grouped by node.type, with edges drawn
 * between linked nodes. Click a node to highlight its neighborhood.
 *
 * Inputs:
 *   nodes: [{ id, label, type, riskScore? }]
 *   edges: [{ source, target, type? }]
 *   width / height: SVG canvas size
 */
const TYPE_COLORS = {
  supplier: '#2563eb',
  port: '#0891b2',
  chokepoint: '#dc2626',
  sku: '#7c3aed',
  region: '#65a30d',
  event: '#a855f7',
  country: '#eab308',
  unknown: '#64748b',
  default: '#6b7280',
};

const TYPE_DISPLAY = {
  supplier: 'Supplier',
  port: 'Port',
  chokepoint: 'Chokepoint',
  sku: 'SKU',
  region: 'Region',
  event: 'Event',
  country: 'Country',
  unknown: 'Entity',
};

export function NetworkGraph({ nodes = [], edges = [], width = 720, height = 520 }) {
  const [selectedId, setSelectedId] = useState(null);

  const layout = useMemo(() => {
    if (nodes.length === 0) return { positions: new Map(), groups: [] };

    // Group nodes by type so each type gets its own concentric ring
    const groups = new Map();
    for (const node of nodes) {
      const key = (node.type || 'unknown').toLowerCase();
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(node);
    }

    const cx = width / 2;
    const cy = height / 2;
    const ringStep = Math.min(cx, cy) / Math.max(groups.size, 2);

    const positions = new Map();
    let ringIndex = 1;
    for (const [, members] of groups) {
      const radius = ringStep * ringIndex;
      const step = (2 * Math.PI) / Math.max(members.length, 1);
      members.forEach((node, i) => {
        const angle = i * step + ringIndex * 0.3;
        positions.set(node.id, {
          x: cx + radius * Math.cos(angle),
          y: cy + radius * Math.sin(angle),
        });
      });
      ringIndex += 1;
    }

    return { positions, groups: Array.from(groups.keys()) };
  }, [nodes, width, height]);

  const neighborIds = useMemo(() => {
    if (!selectedId) return null;
    const set = new Set([selectedId]);
    for (const e of edges) {
      if (e.source === selectedId) set.add(e.target);
      if (e.target === selectedId) set.add(e.source);
    }
    return set;
  }, [selectedId, edges]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-500">
        No network data to display.
      </div>
    );
  }

  return (
    <div className="p-2">
      <svg width={width} height={height} className="w-full">
        {/* Edges */}
        <g stroke="#cbd5e1" strokeWidth="1">
          {edges.map((edge, idx) => {
            const a = layout.positions.get(edge.source);
            const b = layout.positions.get(edge.target);
            if (!a || !b) return null;
            const dim =
              neighborIds && !(neighborIds.has(edge.source) && neighborIds.has(edge.target));
            return (
              <line
                key={`${edge.source}-${edge.target}-${idx}`}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                stroke={dim ? '#e5e7eb' : '#94a3b8'}
                strokeOpacity={dim ? 0.3 : 1}
              />
            );
          })}
        </g>

        {/* Nodes */}
        <g>
          {nodes.map((node) => {
            const pos = layout.positions.get(node.id);
            if (!pos) return null;
            const color = TYPE_COLORS[node.type?.toLowerCase()] || TYPE_COLORS.default;
            const isSelected = selectedId === node.id;
            const isNeighbor = neighborIds?.has(node.id);
            const dim = neighborIds && !isNeighbor;
            const radius = isSelected ? 11 : 7;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                style={{ cursor: 'pointer' }}
                onClick={() => setSelectedId(isSelected ? null : node.id)}
                opacity={dim ? 0.25 : 1}
              >
                <circle
                  r={radius}
                  fill={color}
                  stroke={isSelected ? '#0f172a' : 'white'}
                  strokeWidth={isSelected ? 3 : 1.5}
                />
                {(isSelected || isNeighbor) && (
                  <text
                    x={radius + 4}
                    y={4}
                    fontSize="11"
                    fill="#1e293b"
                    style={{ pointerEvents: 'none' }}
                  >
                    {node.label || node.id}
                  </text>
                )}
              </g>
            );
          })}
        </g>
      </svg>

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-slate-700/40 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-xs text-slate-400">
          {layout.groups.map((g) => (
            <span key={g} className="inline-flex items-center gap-1.5">
              <span
                className="inline-block w-3 h-3 rounded-full shrink-0"
                style={{ backgroundColor: TYPE_COLORS[g] || TYPE_COLORS.default }}
              />
              {TYPE_DISPLAY[g] || g}
            </span>
          ))}
        </div>
        <span className="text-xs text-slate-500">
          Click a node to focus neighborhood · {nodes.length} nodes · {edges.length} edges
        </span>
      </div>
    </div>
  );
}
