import { useEffect, useState } from 'react';
import { Network, RefreshCw } from 'lucide-react';
import { fetchNetwork } from '../api/client';
import { NetworkGraph } from '../components/NetworkGraph';

export function NetworkView() {
  const [networkData, setNetworkData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    refresh();
  }, []);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await fetchNetwork({ depth: 2 });
      setNetworkData(data);
    } catch (error) {
      console.error('Failed to fetch network:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Supply Chain Network</h1>
          <p className="mt-2 text-gray-600">Visualize supplier relationships and dependencies</p>
        </div>
        <button
          onClick={refresh}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      {/* Stats */}
      {networkData?.metadata && (
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-blue-600" />
              <span className="font-medium">Nodes</span>
            </div>
            <p className="mt-1 text-2xl font-semibold">{networkData.metadata.total_nodes}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-green-600" />
              <span className="font-medium">Relationships</span>
            </div>
            <p className="mt-1 text-2xl font-semibold">{networkData.metadata.total_edges}</p>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="flex items-center gap-2">
              <Network className="h-5 w-5 text-purple-600" />
              <span className="font-medium">Depth</span>
            </div>
            <p className="mt-1 text-2xl font-semibold">{networkData.metadata.depth}</p>
          </div>
        </div>
      )}

      {/* Visual graph */}
      {networkData?.nodes && (
        <NetworkGraph
          nodes={networkData.nodes}
          edges={(networkData.edges || []).map((e) => ({
            source: e.source ?? e.from,
            target: e.target ?? e.to,
            type: e.type,
          }))}
        />
      )}

      {/* Searchable node list */}
      <div className="bg-white rounded-lg shadow">
        <div className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Network Nodes</h2>
          
          {networkData?.nodes && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {networkData.nodes.slice(0, 50).map((node) => (
                <div
                  key={node.id}
                  onClick={() => setSelectedNode(node)}
                  className={`p-4 rounded-lg border cursor-pointer transition-colors ${
                    node.critical
                      ? 'bg-red-50 border-red-200 hover:bg-red-100'
                      : node.risk_score > 0.6
                      ? 'bg-orange-50 border-orange-200 hover:bg-orange-100'
                      : 'bg-gray-50 border-gray-200 hover:bg-gray-100'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="inline-block px-2 py-1 text-xs font-medium rounded bg-gray-200 text-gray-700 capitalize">
                        {node.type}
                      </span>
                      <h3 className="mt-2 font-medium text-gray-900">{node.label}</h3>
                      {node.country && (
                        <p className="text-sm text-gray-500">{node.country}</p>
                      )}
                    </div>
                    {node.risk_score > 0 && (
                      <span
                        className={`px-2 py-1 text-xs font-semibold rounded ${
                          node.risk_score > 0.8
                            ? 'bg-red-100 text-red-800'
                            : node.risk_score > 0.6
                            ? 'bg-orange-100 text-orange-800'
                            : 'bg-green-100 text-green-800'
                        }`}
                      >
                        {(node.risk_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Selected Node Details */}
      {selectedNode && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Node Details</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <span className="text-sm text-gray-500">ID</span>
              <p className="font-medium text-gray-900">{selectedNode.id}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Type</span>
              <p className="font-medium text-gray-900 capitalize">{selectedNode.type}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Name</span>
              <p className="font-medium text-gray-900">{selectedNode.label}</p>
            </div>
            <div>
              <span className="text-sm text-gray-500">Risk Score</span>
              <p className="font-medium text-gray-900">
                {selectedNode.risk_score ? `${(selectedNode.risk_score * 100).toFixed(0)}%` : 'N/A'}
              </p>
            </div>
            {selectedNode.latitude && (
              <>
                <div>
                  <span className="text-sm text-gray-500">Latitude</span>
                  <p className="font-medium text-gray-900">{selectedNode.latitude.toFixed(4)}</p>
                </div>
                <div>
                  <span className="text-sm text-gray-500">Longitude</span>
                  <p className="font-medium text-gray-900">{selectedNode.longitude.toFixed(4)}</p>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
