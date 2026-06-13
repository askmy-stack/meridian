import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  AlertTriangle,
  ArrowRight,
  Download,
  Globe,
  Play,
  RefreshCw,
  TrendingUp,
  Users,
  Zap,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fetchStats, fetchWeeklyDigest, getDigestExportUrl } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { StatCard } from '../components/ui/StatCard';
import { riskColor, riskPillClass } from '../lib/risk';

export function Dashboard() {
  const statsQuery = useQuery(['stats'], fetchStats, { staleTime: 60_000, retry: 1 });
  const digestQuery = useQuery(['weekly-digest'], fetchWeeklyDigest, {
    staleTime: 5 * 60_000,
    retry: 1,
  });

  const loading = statsQuery.isLoading && digestQuery.isLoading;
  const stats = statsQuery.data;
  const digest = digestQuery.data;
  const topRisks = digest?.top_risks ?? [];
  const criticalCount = topRisks.filter((r) => r.risk_category === 'CRITICAL').length;

  const chartData = topRisks.slice(0, 6).map((r) => ({
    name: r.name?.split(' ').slice(0, 2).join(' ') || r.supplier_id,
    risk: Math.round((r.risk_score ?? 0) * 100),
  }));

  if (loading) return <LoadingState label="Loading command center…" />;

  return (
    <div className="space-y-8">
      <DemoBanner />

      {/* Hero */}
      <section className="relative overflow-hidden rounded-3xl border border-blue-500/20 p-8 sm:p-10"
        style={{
          background: 'linear-gradient(135deg, rgba(59,130,246,0.12) 0%, rgba(15,22,41,0.95) 50%, rgba(7,11,20,1) 100%)',
        }}
      >
        <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="relative flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-blue-400 mb-2">
              Supply Chain Command Center
            </p>
            <h1 className="page-title text-4xl sm:text-5xl">Risk Intelligence</h1>
            <p className="mt-3 text-slate-400 max-w-xl text-lg">
              {digest?.narrative ||
                'Real-time geopolitical signals mapped to your supplier network — before disruption hits production.'}
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => {
                statsQuery.refetch();
                digestQuery.refetch();
              }}
              className="btn-ghost"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
            <a href={getDigestExportUrl()} download className="btn-ghost">
              <Download className="h-4 w-4" />
              Export digest
            </a>
            <Link to="/simulate" className="btn-primary">
              <Play className="h-4 w-4" />
              Run scenario
            </Link>
          </div>
        </div>
      </section>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={<Users className="h-6 w-6" />}
          title="Suppliers tracked"
          value={stats?.suppliers?.total ?? 0}
          subtitle="In Neo4j knowledge graph"
          accent="blue"
        />
        <StatCard
          icon={<AlertTriangle className="h-6 w-6" />}
          title="Critical risks"
          value={criticalCount}
          subtitle={criticalCount ? 'Immediate review required' : 'All clear'}
          accent="red"
          trend={criticalCount ? '↑ elevated' : null}
        />
        <StatCard
          icon={<Globe className="h-6 w-6" />}
          title="Active events"
          value={digest?.summary?.total_events ?? 0}
          subtitle="Last 7 days"
          accent="green"
        />
        <StatCard
          icon={<TrendingUp className="h-6 w-6" />}
          title="Peak risk score"
          value={
            topRisks[0]?.risk_score
              ? `${Math.round(topRisks[0].risk_score * 100)}%`
              : '—'
          }
          subtitle={topRisks[0]?.name ?? 'Seed data to populate'}
          accent="purple"
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Chart */}
        <Panel
          title="Top supplier risk scores"
          subtitle="XGBoost-scored exposure from live graph"
          className="xl:col-span-2"
        >
          {chartData.length > 0 ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      background: '#151f38',
                      border: '1px solid rgba(148,163,184,0.2)',
                      borderRadius: 12,
                      color: '#f1f5f9',
                    }}
                    formatter={(v) => [`${v}%`, 'Risk']}
                  />
                  <Bar dataKey="risk" radius={[6, 6, 0, 0]} fill="url(#riskGradient)" />
                  <defs>
                    <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3b82f6" />
                      <stop offset="100%" stopColor="#6366f1" />
                    </linearGradient>
                  </defs>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="text-slate-500 text-sm py-12 text-center">Run make seed-all to populate risk scores</p>
          )}
        </Panel>

        {/* Quick actions */}
        <Panel title="Quick actions" subtitle="Demo workflow shortcuts">
          <div className="space-y-3">
            {[
              { to: '/simulate', icon: Zap, label: 'Red Sea disruption sim', desc: 'BFS + Monte Carlo' },
              { to: '/suppliers', icon: Users, label: 'SHAP explanations', desc: 'Why is risk elevated?' },
              { to: '/alerts', icon: AlertTriangle, label: 'Emit live alert', desc: 'Slack-ready pipeline' },
              { to: '/map', icon: Globe, label: 'Global risk map', desc: 'Geospatial heat view' },
            ].map(({ to, icon: Icon, label, desc }) => (
              <Link
                key={to}
                to={to}
                className="flex items-center gap-3 p-3 rounded-xl border border-slate-700/50 hover:border-blue-500/40 hover:bg-blue-500/5 transition-all group"
              >
                <div className="p-2 rounded-lg bg-slate-800 text-blue-400 group-hover:bg-blue-500/15">
                  <Icon className="h-4 w-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-white">{label}</p>
                  <p className="text-xs text-slate-500">{desc}</p>
                </div>
                <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-blue-400 transition-colors" />
              </Link>
            ))}
          </div>
        </Panel>
      </div>

      {/* Top risks list */}
      {topRisks.length > 0 && (
        <Panel title="Priority suppliers" subtitle="Ranked by composite risk score">
          <div className="space-y-2">
            {topRisks.map((risk, i) => (
              <Link
                key={risk.supplier_id}
                to="/suppliers"
                className="flex items-center gap-4 p-4 rounded-xl border border-slate-700/40 hover:border-blue-500/30 hover:bg-slate-800/30 transition-all"
              >
                <span className="text-2xl font-bold text-slate-600 w-8">#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-white truncate">{risk.name}</p>
                  <div className="mt-2 h-1.5 rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${(risk.risk_score ?? 0) * 100}%`,
                        backgroundColor: riskColor(risk.risk_score),
                      }}
                    />
                  </div>
                </div>
                <span className={`risk-pill ${riskPillClass(risk.risk_score)}`}>
                  {risk.risk_category}
                </span>
              </Link>
            ))}
          </div>
        </Panel>
      )}

      {digest?.recommendations?.length > 0 && (
        <Panel title="AI recommendations" subtitle="Generated from weekly digest analysis">
          <ul className="space-y-2">
            {digest.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300">
                <span className="text-blue-400 font-bold">{i + 1}.</span>
                {rec}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
