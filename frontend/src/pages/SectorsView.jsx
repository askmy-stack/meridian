import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { ArrowRight, Factory, TrendingUp } from 'lucide-react';
import { fetchSectorDashboard } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { useEntityDrawer } from '../context/EntityDrawerContext';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { riskColor, riskPillClass } from '../lib/risk';

export function SectorsView() {
  const { openEntity } = useEntityDrawer();
  const { data, isLoading, isError } = useQuery(['sectors'], fetchSectorDashboard, {
    staleTime: 120_000,
  });

  const sectors = data?.sectors ?? [];

  if (isLoading) return <LoadingState label="Loading sector dashboard…" />;

  return (
    <div className="space-y-6">
      <DemoBanner />
      <header>
        <p className="text-xs font-semibold uppercase tracking-widest text-violet-400 mb-1">
          Portfolio analytics
        </p>
        <h1 className="page-title">Sector Risk Dashboard</h1>
        <p className="mt-2 text-slate-400 max-w-2xl">
          Aggregate exposure across semiconductors, energy, automotive, and shipping — ranked by live graph scores.
        </p>
      </header>

      {isError && (
        <p className="text-red-400 text-sm">Failed to load sector data. Ensure Neo4j is seeded.</p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sectors.map((sector) => (
          <Panel
            key={sector.sector}
            title={sector.sector.replace(/_/g, ' ')}
            subtitle={`${sector.supplier_count} suppliers · ${sector.critical_count} critical`}
          >
            <div className="flex items-end gap-4 mb-4">
              <div>
                <p className="text-3xl font-bold text-white">
                  {sector.supplier_count ? `${Math.round(sector.avg_risk * 100)}%` : '—'}
                </p>
                <p className="text-xs text-slate-500">Avg risk</p>
              </div>
              <div>
                <p className="text-xl font-semibold text-orange-400">
                  {sector.supplier_count ? `${Math.round(sector.max_risk * 100)}%` : '—'}
                </p>
                <p className="text-xs text-slate-500">Peak</p>
              </div>
              <TrendingUp className="h-5 w-5 text-slate-600 ml-auto" />
            </div>

            {sector.top_suppliers?.length > 0 ? (
              <ul className="space-y-2">
                {sector.top_suppliers.map((s) => (
                  <li key={s.id}>
                    <button
                      type="button"
                      className="w-full flex items-center gap-3 p-3 rounded-xl border border-slate-700/50 hover:border-violet-500/40 hover:bg-slate-800/40 text-left transition-all"
                      onClick={() =>
                        openEntity({
                          id: s.id,
                          name: s.name,
                          type: 'supplier',
                          risk_score: s.risk_score,
                          country: s.country,
                        })
                      }
                    >
                      <Factory className="h-4 w-4 text-violet-400 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white truncate">{s.name}</p>
                        <div className="mt-1 h-1 rounded-full bg-slate-800 overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${(s.risk_score ?? 0) * 100}%`,
                              backgroundColor: riskColor(s.risk_score),
                            }}
                          />
                        </div>
                      </div>
                      <span className={`risk-pill text-[10px] ${riskPillClass(s.risk_score)}`}>
                        {Math.round((s.risk_score ?? 0) * 100)}%
                      </span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-slate-500 py-4 text-center">No suppliers matched this sector</p>
            )}
          </Panel>
        ))}
      </div>

      <div className="flex justify-end">
        <Link to="/suppliers" className="btn-ghost">
          View all suppliers
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
