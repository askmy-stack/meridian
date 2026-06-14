import { useState } from 'react';
import { useQuery } from 'react-query';
import { Network, RefreshCw } from 'lucide-react';
import { fetchNetwork } from '../api/client';
import { NetworkGraph } from '../components/NetworkGraph';
import { DemoBanner } from '../components/DemoBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { RiskBar, RiskPill } from '../components/ui/RiskDisplay';

export function NetworkView() {
  const [selectedNode, setSelectedNode] = useState(null);

  const { data: networkData, isLoading, isError, refetch, isFetching } = useQuery(
    ['network', 2],
    () => fetchNetwork({ depth: 2 }),
    { staleTime: 60_000 },
  );

  if (isLoading) return <LoadingState label="Building supply graph…" />;

  return (
    <div className="space-y-6">
      <DemoBanner />
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Supply Chain Graph</h1>
          <p className="mt-2 text-slate-400">Interactive knowledge graph — suppliers, ports, chokepoints</p>
        </div>
        <button type="button" onClick={() => refetch()} disabled={isFetching} className="btn-ghost">
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {isError && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm">
          Could not load graph — ensure Neo4j is running and seeded.
        </div>
      )}

      {networkData?.metadata && (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Nodes', val: networkData.metadata.total_nodes, icon: Network },
            { label: 'Edges', val: networkData.metadata.total_edges, icon: Network },
            { label: 'Depth', val: networkData.metadata.depth, icon: Network },
          ].map(({ label, val }) => (
            <div key={label} className="stat-card text-center">
              <p className="text-2xl font-bold text-white">{val}</p>
              <p className="text-xs text-slate-500">{label}</p>
            </div>
          ))}
        </div>
      )}

      {networkData?.nodes && (
        <div className="glass-panel p-4 overflow-hidden">
          <NetworkGraph
            nodes={networkData.nodes}
            edges={(networkData.edges || []).map((e) => ({
              source: e.source ?? e.from,
              target: e.target ?? e.to,
              type: e.type,
            }))}
          />
        </div>
      )}

      <Panel title="Network entities" subtitle="Click a node in the graph or select from list">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {(networkData?.nodes ?? []).slice(0, 30).map((node) => (
            <button
              key={node.id}
              type="button"
              onClick={() => setSelectedNode(node)}
              className={`text-left p-3 sm:p-4 rounded-xl border transition-all ${
                selectedNode?.id === node.id
                  ? 'border-blue-500/50 bg-blue-500/10'
                  : 'border-slate-700/50 hover:border-slate-600'
              }`}
            >
              <span className="text-[10px] uppercase tracking-wider text-slate-500">{node.type}</span>
              <p className="font-medium text-white mt-1 truncate">{node.label}</p>
              {node.risk_score > 0 && (
                <>
                  <RiskBar score={node.risk_score} className="mt-2" />
                  <RiskPill score={node.risk_score} size="sm" className="mt-2" />
                </>
              )}
            </button>
          ))}
        </div>
      </Panel>

      {selectedNode && (
        <Panel title={selectedNode.label} subtitle={`${selectedNode.type} · ${selectedNode.id}`}>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div><dt className="text-slate-500">Country</dt><dd className="text-white">{selectedNode.country || '—'}</dd></div>
            <div><dt className="text-slate-500">Risk</dt><dd className="text-white">{selectedNode.risk_score ? `${Math.round(selectedNode.risk_score * 100)}%` : 'N/A'}</dd></div>
            {selectedNode.latitude && (
              <>
                <div><dt className="text-slate-500">Lat</dt><dd className="text-white">{selectedNode.latitude.toFixed(4)}</dd></div>
                <div><dt className="text-slate-500">Lon</dt><dd className="text-white">{selectedNode.longitude.toFixed(4)}</dd></div>
              </>
            )}
          </dl>
        </Panel>
      )}
    </div>
  );
}
