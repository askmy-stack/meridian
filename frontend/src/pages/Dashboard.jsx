import { useEffect, useState } from 'react';
import { AlertTriangle, TrendingUp, Globe, Users } from 'lucide-react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [digest, setDigest] = useState(null);

  useEffect(() => {
    fetchStats();
    fetchDigest();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE}/stats`);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDigest = async () => {
    try {
      const response = await axios.post(`${API_BASE}/intelligence/weekly-digest`);
      setDigest(response.data);
    } catch (error) {
      console.error('Failed to fetch digest:', error);
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
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Supply Chain Risk Dashboard</h1>
        <p className="mt-2 text-gray-600">Real-time risk intelligence and monitoring</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          icon={<Users className="h-6 w-6 text-blue-600" />}
          title="Suppliers"
          value={stats?.suppliers?.total || 0}
          trend="+2 this week"
        />
        <StatCard
          icon={<AlertTriangle className="h-6 w-6 text-red-600" />}
          title="Critical Risks"
          value={digest?.top_risks?.filter(r => r.risk_category === 'CRITICAL')?.length || 0}
          trend="Immediate attention"
        />
        <StatCard
          icon={<Globe className="h-6 w-6 text-green-600" />}
          title="Active Events"
          value={digest?.summary?.total_events || 0}
          trend="Last 7 days"
        />
        <StatCard
          icon={<TrendingUp className="h-6 w-6 text-purple-600" />}
          title="Risk Trend"
          value={digest?.top_risks?.[0]?.risk_score ? `${(digest.top_risks[0].risk_score * 100).toFixed(0)}%` : 'N/A'}
          trend="Highest risk"
        />
      </div>

      {/* Weekly Digest */}
      {digest && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Weekly Risk Digest</h2>
          <p className="text-gray-600 mb-4">{digest.narrative}</p>
          
          {digest.top_risks?.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Top Risk Suppliers</h3>
              <div className="space-y-2">
                {digest.top_risks.slice(0, 5).map((risk) => (
                  <div
                    key={risk.supplier_id}
                    className={`flex items-center justify-between p-3 rounded-lg ${
                      risk.risk_category === 'CRITICAL'
                        ? 'bg-red-50 border border-red-200'
                        : risk.risk_category === 'HIGH'
                        ? 'bg-orange-50 border border-orange-200'
                        : 'bg-yellow-50 border border-yellow-200'
                    }`}
                  >
                    <div>
                      <span className="font-medium text-gray-900">{risk.name}</span>
                      <span className="ml-2 text-sm text-gray-500">
                        {(risk.risk_score * 100).toFixed(0)}% risk
                      </span>
                    </div>
                    <span
                      className={`px-2 py-1 text-xs font-semibold rounded ${
                        risk.risk_category === 'CRITICAL'
                          ? 'bg-red-100 text-red-800'
                          : risk.risk_category === 'HIGH'
                          ? 'bg-orange-100 text-orange-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {risk.risk_category}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {digest.recommendations?.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-gray-700 mb-2">Recommendations</h3>
              <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
                {digest.recommendations.map((rec, i) => (
                  <li key={i}>{rec}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({ icon, title, value, trend }) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center">
        <div className="p-3 rounded-lg bg-gray-100">{icon}</div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-600">{title}</p>
          <p className="text-2xl font-semibold text-gray-900">{value}</p>
        </div>
      </div>
      <p className="mt-2 text-sm text-gray-500">{trend}</p>
    </div>
  );
}
