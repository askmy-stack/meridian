import { useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import { GitBranch, Network, RefreshCw, Share2 } from 'lucide-react';
import { fetchNetwork } from '../api/client';
import { NetworkGraph } from '../components/NetworkGraph';
import { DemoBanner } from '../components/DemoBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { RiskBar, RiskPill } from '../components/ui/RiskDisplay';
import { dedupeNetworkNodes, normalizeNodeType, resolveNodeRiskScore } from '../lib/networkUtils';
import { formatRiskPercent } from '../lib/risk';

export function NetworkView() {
  const [selectedNode, setSelectedNode] = useState(null);

  const { data: networkData, isLoading, isError, refetch, isFetching } = useQuery(
    ['network', 2],
    () => fetchNetwork({ depth: 2 }),
    { staleTime: 60_000 },
  );

  const nodes = useMemo(
    () => dedupeNetworkNodes(networkData?.nodes ?? []),
    [networkData?.nodes],
  );

  const edges = useMemo(
    () =>
      (networkData?.edges || []).map((e) => ({
        source: e.source ?? e.from,
        target: e.target ?? e.to,
        type: e.type,
      })),
    [networkData?.edges],
  );

  if (isLoading) return <LoadingState label="Building supply graph…" />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Knowledge graph"
        title="Supply Chain Graph"
        subtitle="Interactive network — suppliers, ports, chokepoints, and linked events with modelled SCRI where available."
        badges={['Neo4j · BFS depth 2']}
        gradient="violet"
        actions={
          <button type="button" onClick={() => refetch()} disabled={isFetching} className="btn-ghost">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        }
      />

      {isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">
          Could not load graph — ensure Neo4j is running and seeded.
        </div>
      )}

      {networkData?.metadata && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
            { label: 'Nodes', val: nodes.length, icon: Network },
            { label: 'Edges', val: networkData.metadata.total_edges, icon: Share2 },
            { label: 'Depth', val: networkData.metadata.depth, icon: GitBranch },
          ].map(({ label, val, icon: Icon }) => (
            <div key={label} className="stat-card flex items-center gap-4">
              <div className="p-2.5 rounded-xl bg-violet-500/10 text-violet-400">
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-2xl font-bold text-white tabular-nums">{val}</p>
                <p className="text-xs text-slate-500 uppercase tracking-wider">{label}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {nodes.length > 0 && (
        <div className="glass-panel p-5 sm:p-6 overflow-hidden">
          <NetworkGraph nodes={nodes} edges={edges} />
        </div>
      )}

      <Panel title="Network entities" subtitle={`${nodes.length} unique nodes · deduplicated by ID`}>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {nodes.slice(0, 36).map((node) => {
            const { label: typeLabel } = normalizeNodeType(node);
            const risk = resolveNodeRiskScore(node);
            return (
              <button
                key={node.id}
                type="button"
                onClick={() => setSelectedNode(node)}
                className={`text-left p-4 rounded-xl border transition-all min-h-[7.5rem] flex flex-col ${
                  selectedNode?.id === node.id
                    ? 'border-violet-500/50 bg-violet-500/10'
                    : 'border-slate-700/50 hover:border-slate-600 bg-slate-900/20'
                }`}
              >
                <span className="text-[10px] uppercase tracking-wider font-semibold text-violet-400/90">
                  {typeLabel}
                </span>
                <p className="font-medium text-white mt-1 truncate flex-1">{node.label || node.id}</p>
                {risk != null && risk > 0 ? (
                  <div className="mt-auto pt-2">
                    <RiskBar score={risk} className="mb-2" />
                    <RiskPill score={risk} size="sm" />
                  </div>
                ) : (
                  <p className="text-xs text-slate-500 mt-auto pt-2">
                    {typeLabel === 'Supplier'
                      ? 'SCRI pending — run score-suppliers'
                      : 'Infrastructure node · no modelled index'}
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </Panel>

      {selectedNode && (
        <Panel
          title={selectedNode.label || selectedNode.id}
          subtitle={`${normalizeNodeType(selectedNode).label} · ${selectedNode.id}`}
        >
          <dl className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            <div>
              <dt className="text-slate-500">Type</dt>
              <dd className="text-white">{normalizeNodeType(selectedNode).label}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Country</dt>
              <dd className="text-white">{selectedNode.country || '—'}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Modelled index</dt>
              <dd className="text-white">
                {resolveNodeRiskScore(selectedNode) != null
                  ? `${formatRiskPercent(resolveNodeRiskScore(selectedNode))}%`
                  : 'N/A'}
              </dd>
            </div>
            {selectedNode.latitude && (
              <>
                <div>
                  <dt className="text-slate-500">Coordinates</dt>
                  <dd className="text-white tabular-nums text-xs">
                    {selectedNode.latitude.toFixed(4)}, {selectedNode.longitude.toFixed(4)}
                  </dd>
                </div>
              </>
            )}
          </dl>
        </Panel>
      )}
    </div>
  );
}
