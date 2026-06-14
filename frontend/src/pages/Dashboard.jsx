import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import {
  AlertTriangle,
  ArrowRight,
  BookOpen,
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
import {
  fetchMetricsMethodology,
  fetchStats,
  fetchWeeklyDigest,
  getDigestExportUrl,
} from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { PageHeader } from '../components/ui/PageHeader';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { Panel } from '../components/ui/Panel';
import { StatCard } from '../components/ui/StatCard';
import { RiskBar, RiskListBody, RiskPill } from '../components/ui/RiskDisplay';
import { calibrationSublabel } from '../hooks/useMethodology';
import { riskColor } from '../lib/risk';

function kpiDefinition(methodology, id, fallback) {
  return methodology?.kpis?.find((k) => k.id === id)?.definition ?? fallback;
}

export function Dashboard() {
  const statsQuery = useQuery(['stats'], fetchStats, { staleTime: 60_000, retry: 1 });
  const digestQuery = useQuery(['weekly-digest'], fetchWeeklyDigest, {
    staleTime: 5 * 60_000,
    retry: 1,
  });
  const methodologyQuery = useQuery(['metrics-methodology'], fetchMetricsMethodology, {
    staleTime: 10 * 60_000,
    retry: 1,
  });

  const loading = statsQuery.isLoading && digestQuery.isLoading;
  const hasError = statsQuery.isError || digestQuery.isError;
  const stats = statsQuery.data;
  const digest = digestQuery.data;
  const methodology = methodologyQuery.data;
  const calLabel = calibrationSublabel(methodology);
  const scriLimitations = methodology?.limitations;
  const topRisks = digest?.top_risks ?? [];
  const criticalCount = topRisks.filter((r) => r.risk_category === 'CRITICAL').length;

  const chartData = topRisks.slice(0, 6).map((r) => ({
    name: r.name?.split(' ').slice(0, 2).join(' ') || r.supplier_id,
    scri: Math.round((r.risk_score ?? 0) * 100),
  }));

  if (loading) return <LoadingState label="Loading command center…" />;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      <DemoBanner />
      {hasError && (
        <ErrorBanner
          message="Could not load dashboard data — ensure the API is running on port 8002."
          onRetry={() => {
            statsQuery.refetch();
            digestQuery.refetch();
          }}
        />
      )}

      <PageHeader
        eyebrow="Supply Chain Command Center"
        title="Risk Intelligence"
        subtitle={
          methodology?.description ||
          digest?.narrative ||
          'Geopolitical signals mapped to your supplier network with explainable SCRI scores.'
        }
        badges={[`${methodology?.index_name ?? 'SCRI'} · modelled index 0–100`]}
        gradient="blue"
        actions={
          <>
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
          </>
        }
      >
        {digest?.narrative_type === 'template' && (
          <span className="inline-flex text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-md border border-slate-600 text-slate-400">
            Weekly digest · template narrative
          </span>
        )}
        <a
          href="https://github.com/askmy-stack/meridian/blob/main/docs/METRICS.md"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
        >
          <BookOpen className="h-3.5 w-3.5" />
          SCRI methodology & references
        </a>
      </PageHeader>

      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          icon={<Users className="h-6 w-6" />}
          title="Suppliers tracked"
          value={stats?.suppliers?.total ?? 0}
          subtitle="Canonical nodes in Neo4j"
          accent="blue"
          tooltip={
            <MetricTooltip
              label="Suppliers tracked"
              definition={kpiDefinition(
                methodology,
                'suppliers_tracked',
                'Count of Supplier nodes in the knowledge graph.'
              )}
            />
          }
        />
        <StatCard
          icon={<AlertTriangle className="h-6 w-6" />}
          title="Critical SCRI (≥75)"
          value={criticalCount}
          subtitle={criticalCount ? 'Executive escalation band' : 'No suppliers in CRITICAL band'}
          accent="red"
          trend={criticalCount ? '↑ elevated' : null}
          tooltip={
            <MetricTooltip
              label="Critical SCRI"
              definition={kpiDefinition(
                methodology,
                'critical_risks',
                'Suppliers with SCRI ≥ 0.75 per XGBoost + SHAP model.'
              )}
              limitations={scriLimitations}
              reference="docs/LIMITATIONS.md"
            />
          }
        />
        <StatCard
          icon={<Globe className="h-6 w-6" />}
          title="Active events (7d)"
          value={digest?.summary?.total_events ?? 0}
          subtitle="GDELT / ACLED ingested signals"
          accent="green"
          tooltip={
            <MetricTooltip
              label="Active events"
              definition={kpiDefinition(
                methodology,
                'active_events',
                'Event nodes ingested in the last 7 days.'
              )}
              reference="GDELT Goldstein-scale severity"
            />
          }
        />
        <StatCard
          icon={<TrendingUp className="h-6 w-6" />}
          title="Peak SCRI"
          value={
            topRisks[0]?.risk_score ? `${Math.round(topRisks[0].risk_score * 100)}` : '—'
          }
          subtitle={topRisks[0]?.name ?? 'Run make score-suppliers'}
          accent="purple"
          tooltip={
            <MetricTooltip
              label="Peak SCRI"
              definition={kpiDefinition(
                methodology,
                'peak_scri',
                'Highest supplier SCRI in the weekly digest.'
              )}
              reference="SHAP-explained XGBoost score"
            />
          }
        />
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <Panel
          title="Top supplier SCRI"
          subtitle="XGBoost + SHAP · 30-day disruption probability proxy"
          className="xl:col-span-2"
        >
          {chartData.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData} margin={{ top: 8, right: 8, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.1)" />
                  <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} />
                  <YAxis
                    tick={{ fill: '#94a3b8', fontSize: 11 }}
                    axisLine={false}
                    domain={[0, 100]}
                    tickFormatter={(v) => `${v}`}
                    label={{
                      value: 'SCRI',
                      angle: -90,
                      position: 'insideLeft',
                      fill: '#64748b',
                      fontSize: 11,
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#151f38',
                      border: '1px solid rgba(148,163,184,0.2)',
                      borderRadius: 12,
                      color: '#f1f5f9',
                    }}
                    formatter={(v) => [`${v} / 100`, 'SCRI']}
                  />
                  <Bar dataKey="scri" radius={[6, 6, 0, 0]} fill="url(#riskGradient)" />
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
            <p className="text-slate-500 text-sm py-12 text-center">
              Run <code className="text-blue-400">make seed-all</code> and{' '}
              <code className="text-blue-400">make score-suppliers</code>
            </p>
          )}
        </Panel>

        <Panel title="Demo workflow" subtitle="2–3 minute portfolio path">
          <div className="space-y-3">
            {[
              { to: '/map', icon: Globe, label: 'Global risk map', desc: 'Conflict + routes + events' },
              { to: '/simulate', icon: Zap, label: 'Disruption simulator', desc: 'BFS · 1,000-run Monte Carlo' },
              { to: '/suppliers', icon: Users, label: 'SHAP explanations', desc: 'Why SCRI is elevated' },
              { to: '/alerts', icon: AlertTriangle, label: 'Live alerts', desc: 'Tiered Slack-ready feed' },
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
                <ArrowRight className="h-4 w-4 text-slate-600 group-hover:text-blue-400 transition-colors shrink-0" />
              </Link>
            ))}
          </div>
        </Panel>
      </div>

      {topRisks.length > 0 && (
        <Panel title="Priority suppliers" subtitle="Ranked by SCRI (Supply Chain Risk Index)">
          <div className="space-y-2">
            {topRisks.map((risk, i) => (
              <Link
                key={risk.supplier_id}
                to={`/suppliers?highlight=${encodeURIComponent(risk.supplier_id)}`}
                className="risk-list-row border-slate-700/40 hover:border-blue-500/30 hover:bg-slate-800/30"
              >
                <span className="text-xl sm:text-2xl font-bold text-slate-600 w-7 sm:w-8 tabular-nums shrink-0">
                  #{i + 1}
                </span>
                <RiskListBody title={risk.name} score={risk.risk_score} />
                <div className="flex flex-col items-end gap-0.5 shrink-0 min-w-[2.75rem] sm:min-w-[3rem]">
                  <RiskPill
                    score={risk.risk_score}
                    variant="category"
                    label={risk.risk_category}
                    size="sm"
                    calibrationLabel={calLabel}
                  />
                </div>
              </Link>
            ))}
          </div>
        </Panel>
      )}

      {digest?.recommendations?.length > 0 && (
        <Panel title="Recommended actions" subtitle="Derived from digest — not LLM risk scores">
          <ul className="space-y-2">
            {digest.recommendations.map((rec, i) => (
              <li key={i} className="flex gap-3 text-sm text-slate-300 leading-relaxed">
                <span className="text-blue-400 font-bold tabular-nums">{i + 1}.</span>
                {rec}
              </li>
            ))}
          </ul>
        </Panel>
      )}
    </div>
  );
}
