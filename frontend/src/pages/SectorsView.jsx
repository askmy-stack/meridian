import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { ArrowRight, Factory, TrendingUp } from 'lucide-react';
import { fetchSectorDashboard } from '../api/client';
import { COUNTRY_RISK_BY_SECTOR, SECTOR_PROFILES } from '../data/sectorIntelligence';
import { DemoBanner } from '../components/DemoBanner';
import { useEntityDrawer } from '../context/EntityDrawerContext';
import { CountryPriceTable } from '../components/ui/CountryPriceTable';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { LoadingState } from '../components/ui/LoadingState';
import { PageFooterNote, PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { RegionRiskMap } from '../components/ui/RegionRiskMap';
import { RiskBar, RiskListBody, RiskPill } from '../components/ui/RiskDisplay';
import { SectorInfoPanel } from '../components/ui/SectorInfoPanel';
import { DEMO_SECTOR_NOTE, ERRORS, LOADING, NAV_LABELS } from '../lib/uiCopy';

export function SectorsView() {
  const { openEntity } = useEntityDrawer();
  const [activeSector, setActiveSector] = useState('semiconductors');
  const { data, isLoading, isError, refetch } = useQuery(['sectors'], fetchSectorDashboard, {
    staleTime: 120_000,
  });

  const sectors = data?.sectors ?? [];
  const selected = sectors.find((s) => s.sector === activeSector) || sectors[0];
  const countryData = COUNTRY_RISK_BY_SECTOR[activeSector] || [];

  if (isLoading) return <LoadingState label={LOADING.sectors} />;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Portfolio analytics"
        title={NAV_LABELS.sectors}
        subtitle="Strategic sector exposure with regional price indices and human-impact context — modelled SCRI from XGBoost, regional bands are demo templates."
        badges={['Keyword taxonomy · demo']}
        gradient="violet"
        actions={
          <Link to="/suppliers" className="btn-ghost">
            Supplier registry
            <ArrowRight className="h-4 w-4" />
          </Link>
        }
      >
        <MetricTooltip
          label="Sector assignment"
          definition={DEMO_SECTOR_NOTE}
          reference="docs/LIMITATIONS.md"
        />
      </PageHeader>

      {isError && (
        <ErrorBanner message={ERRORS.sectors} onRetry={() => refetch()} />
      )}

      <div className="flex flex-wrap gap-2">
        {Object.keys(SECTOR_PROFILES).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveSector(key)}
            className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all capitalize ${
              activeSector === key
                ? 'border-violet-500/50 bg-violet-500/15 text-violet-200'
                : 'border-slate-700 text-slate-400 hover:border-slate-600'
            }`}
          >
            {SECTOR_PROFILES[key].label}
          </button>
        ))}
      </div>

      {selected && (
        <Panel
          title={SECTOR_PROFILES[activeSector]?.label || activeSector.replace(/_/g, ' ')}
          subtitle={`${selected.supplier_count} suppliers · ${selected.critical_count} critical · avg modelled index ${selected.supplier_count ? Math.round(selected.avg_risk * 100) : '—'}%`}
        >
          <SectorInfoPanel sectorKey={activeSector} classificationMethod={data?.classification_method} />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-6 mb-6">
            <div className="stat-card">
              <p className="text-3xl font-bold text-white tabular-nums">
                {selected.supplier_count ? `${Math.round(selected.avg_risk * 100)}%` : '—'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Avg modelled index</p>
            </div>
            <div className="stat-card">
              <p className="text-3xl font-bold text-orange-400 tabular-nums">
                {selected.supplier_count ? `${Math.round(selected.max_risk * 100)}%` : '—'}
              </p>
              <p className="text-xs text-slate-500 mt-1">Peak SCRI</p>
            </div>
            <div className="stat-card flex items-center justify-between">
              <div>
                <p className="text-3xl font-bold text-white tabular-nums">{selected.critical_count}</p>
                <p className="text-xs text-slate-500 mt-1">Critical band</p>
              </div>
              <TrendingUp className="h-6 w-6 text-slate-600" />
            </div>
          </div>

          {selected.top_suppliers?.length > 0 ? (
            <ul className="space-y-2 mb-8">
              {selected.top_suppliers.map((s) => (
                <li key={s.id}>
                  <button
                    type="button"
                    className="risk-list-row border-slate-700/50 hover:border-violet-500/40 hover:bg-slate-800/40"
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
                    <RiskListBody title={s.name} score={s.risk_score} />
                    <RiskPill score={s.risk_score} size="sm" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500 py-4 text-center mb-8">No suppliers matched this sector</p>
          )}

          <h3 className="text-sm font-semibold text-white mb-3">Regional risk & price levels</h3>
          <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
            <RegionRiskMap
              countries={countryData}
              height={340}
              title={`${SECTOR_PROFILES[activeSector]?.label} exposure map`}
            />
            <CountryPriceTable countries={countryData} />
          </div>
        </Panel>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sectors
          .filter((s) => s.sector !== activeSector)
          .map((sector) => (
            <button
              key={sector.sector}
              type="button"
              onClick={() => setActiveSector(sector.sector)}
              className="glass-panel p-5 text-left hover:border-violet-500/30 transition-all"
            >
              <p className="font-semibold text-white capitalize">{sector.sector.replace(/_/g, ' ')}</p>
              <p className="text-xs text-slate-500 mt-1">
                {sector.supplier_count} suppliers · peak {Math.round(sector.max_risk * 100)}%
              </p>
            </button>
          ))}
      </div>

      <PageFooterNote note="Regional price bands and sector taxonomy are demo templates — not ML classification." />
    </div>
  );
}
