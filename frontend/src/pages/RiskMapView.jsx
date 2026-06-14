import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { BookOpen, Layers, Play } from 'lucide-react';
import {
  fetchMapLayers,
  fetchMetricsMethodology,
  fetchSanctionsLayer,
  fetchWeatherLayer,
} from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { InteractiveWorldMap } from '../components/map/InteractiveWorldMap';
import { MapDetailPanel } from '../components/map/MapDetailPanel';
import { useEntityDrawer } from '../context/EntityDrawerContext';
import { ErrorBanner } from '../components/ui/ErrorBanner';
import { LoadingState } from '../components/ui/LoadingState';
import { MetricTooltip } from '../components/ui/MetricTooltip';
import { PageFooterNote, PageHeader } from '../components/ui/PageHeader';
import { Panel } from '../components/ui/Panel';
import { RiskBar, RiskPill } from '../components/ui/RiskDisplay';
import {
  ERRORS,
  LOADING,
  METRICS_LINK_TEXT,
  METRICS_URL,
  NAV_LABELS,
  SCRI_BADGE,
  SCRI_TOOLTIP,
} from '../lib/uiCopy';

function kpiDefinition(methodology, id, fallback) {
  return methodology?.kpis?.find((k) => k.id === id)?.definition ?? fallback;
}

const LAYER_TOGGLES = [
  { key: 'zones', label: 'Conflict zones' },
  { key: 'routes', label: 'Trade routes' },
  { key: 'events', label: 'Active events' },
  { key: 'weather', label: 'Weather (NOAA)' },
  { key: 'sanctions', label: 'Sanctions' },
];

export function RiskMapView() {
  const [searchParams] = useSearchParams();
  const { openEntity } = useEntityDrawer();
  const [entityType, setEntityType] = useState('supplier');
  const [selected, setSelected] = useState(null);
  const [toggles, setToggles] = useState({
    zones: true,
    routes: true,
    events: true,
    weather: false,
    sanctions: false,
  });

  const highlightId = searchParams.get('highlight');
  const latParam = searchParams.get('lat');
  const lonParam = searchParams.get('lon');

  const initialView = useMemo(() => {
    if (latParam && lonParam) {
      return { longitude: Number(lonParam), latitude: Number(latParam), zoom: 4 };
    }
    return undefined;
  }, [latParam, lonParam]);

  const { data, isLoading, isError, refetch } = useQuery(
    ['map-layers', entityType, toggles.zones, toggles.routes, toggles.events],
    () =>
      fetchMapLayers({
        entityType,
        includeZones: toggles.zones,
        includeRoutes: toggles.routes,
        includeEvents: toggles.events,
      }),
    { staleTime: 60_000 },
  );

  const { data: weatherData } = useQuery(['weather-layer'], fetchWeatherLayer, {
    enabled: toggles.weather,
    staleTime: 300_000,
  });

  const { data: sanctionsData } = useQuery(['sanctions-layer'], fetchSanctionsLayer, {
    enabled: toggles.sanctions,
    staleTime: 300_000,
  });

  const { data: methodology } = useQuery(['metrics-methodology'], fetchMetricsMethodology, {
    staleTime: 10 * 60_000,
    retry: 1,
  });

  const layers = data?.layers ?? {};
  const extraLayers = {
    weather: toggles.weather ? weatherData : null,
    sanctions: toggles.sanctions ? sanctionsData : null,
  };

  const handleSelect = (feature) => {
    setSelected(feature);
    openEntity(feature);
  };

  useEffect(() => {
    if (!highlightId || !layers.entities) return;
    const collection =
      layers.entities?.features ?? layers.entities?.[entityType]?.features ?? [];
    const match = collection.find((f) => f.properties?.id === highlightId);
    if (match) {
      const payload = { ...match.properties, coordinates: match.geometry?.coordinates };
      setSelected(payload);
      openEntity(payload);
    }
  }, [highlightId, layers, entityType, openEntity]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <DemoBanner />

      <PageHeader
        eyebrow="Geopolitical intelligence"
        title={NAV_LABELS.map}
        subtitle="What is happening, where, why it matters, who is affected, and how disruption propagates through your network."
        badges={[SCRI_BADGE]}
        gradient="blue"
        actions={
          <Link to="/simulate" className="btn-primary shrink-0">
            <Play className="h-4 w-4" />
            Run scenario on map
          </Link>
        }
      >
        <a
          href={METRICS_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300"
        >
          <BookOpen className="h-3.5 w-3.5" />
          {METRICS_LINK_TEXT}
        </a>
      </PageHeader>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row flex-wrap gap-4">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Entity layer">
          {['supplier', 'port', 'chokepoint'].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setEntityType(t)}
              aria-pressed={entityType === t}
              className={`px-4 py-2 text-sm rounded-xl border capitalize transition-all ${
                entityType === t
                  ? 'bg-blue-500/20 border-blue-500/40 text-blue-300'
                  : 'border-slate-700 text-slate-400 hover:border-slate-600'
              }`}
            >
              {t}s
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2 items-center text-slate-500 text-xs">
          <Layers className="h-4 w-4" />
          {LAYER_TOGGLES.map(({ key, label }) => (
            <label key={key} className="flex items-center gap-1.5 cursor-pointer px-2 py-1 rounded-lg border border-slate-800">
              <input
                type="checkbox"
                checked={toggles[key]}
                onChange={(e) => setToggles((t) => ({ ...t, [key]: e.target.checked }))}
                className="rounded border-slate-600"
              />
              {label}
            </label>
          ))}
        </div>
      </div>

      {isError && (
        <ErrorBanner message={ERRORS.map} onRetry={() => refetch()} />
      )}
      {isLoading && <LoadingState label={LOADING.map} />}

      {!isLoading && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          <div className="xl:col-span-2 min-h-[480px]">
            <InteractiveWorldMap
              layers={layers}
              entityType={entityType}
              extraLayers={extraLayers}
              initialView={initialView}
              onSelectFeature={handleSelect}
              height={520}
            />
          </div>
          <div className="min-h-[320px] xl:min-h-[520px]">
            <MapDetailPanel feature={selected} onClose={() => setSelected(null)} />
          </div>
        </div>
      )}

      {/* Executive strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
        {[
          { label: 'Conflict zones', val: layers.conflict_zones?.metadata?.count ?? 0 },
          { label: 'Active events', val: layers.events?.metadata?.count ?? 0 },
          { label: 'Trade routes', val: layers.trade_routes?.metadata?.count ?? 0 },
          {
            label: `${entityType}s mapped`,
            val: layers.entities?.metadata?.count ?? layers.entities?.[entityType]?.metadata?.count ?? 0,
          },
        ].map(({ label, val }) => (
          <div key={label} className="stat-card py-3 text-center">
            <p className="text-2xl font-bold text-white">{val}</p>
            <p className="text-xs text-slate-500 mt-1">{label}</p>
          </div>
        ))}
      </div>

      <Panel
        title="High SCRI entities"
        subtitle="Modelled index from XGBoost + SHAP · click map markers for drill-down"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 max-h-64 overflow-y-auto">
          {(layers.entities?.features ?? layers.entities?.[entityType]?.features ?? [])
            .slice(0, 12)
            .map((f) => (
              <button
                key={f.properties.id}
                type="button"
                onClick={() =>
                  handleSelect({ ...f.properties, coordinates: f.geometry.coordinates })
                }
                className="text-left p-3 rounded-xl border border-slate-700/50 bg-slate-900/30 hover:border-blue-500/40 transition-colors"
              >
                <div className="flex justify-between gap-2 sm:gap-3 items-start">
                  <span className="font-medium text-white truncate text-sm min-w-0">{f.properties.name}</span>
                  <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <RiskPill score={f.properties.risk_score} size="sm" />
                    <p className="text-[9px] sm:text-[10px] text-slate-500 uppercase tracking-wide inline-flex items-center justify-end">
                      SCRI
                      <MetricTooltip
                        label="SCRI"
                        definition={kpiDefinition(methodology, 'peak_scri', SCRI_TOOLTIP)}
                        reference="docs/METRICS.md"
                      />
                    </p>
                  </div>
                </div>
                <RiskBar score={f.properties.risk_score} className="mt-2" />
                <p className="text-xs text-slate-500 mt-1">{f.properties.country || f.properties.entity_type}</p>
              </button>
            ))}
        </div>
      </Panel>

      <PageFooterNote />
    </div>
  );
}
