import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from 'react-query';
import { Layers, Play } from 'lucide-react';
import { fetchMapLayers, fetchSanctionsLayer, fetchWeatherLayer } from '../api/client';
import { DemoBanner } from '../components/DemoBanner';
import { InteractiveWorldMap } from '../components/map/InteractiveWorldMap';
import { MapDetailPanel } from '../components/map/MapDetailPanel';
import { useEntityDrawer } from '../context/EntityDrawerContext';
import { LoadingState } from '../components/ui/LoadingState';
import { Panel } from '../components/ui/Panel';
import { riskPillClass } from '../lib/risk';

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

  const { data, isLoading, isError } = useQuery(
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
    <div className="space-y-6">
      <DemoBanner />

      <header className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-blue-400 mb-1">
            Geopolitical Intelligence
          </p>
          <h1 className="page-title">Interactive World Map</h1>
          <p className="mt-2 text-slate-400 max-w-2xl">
            What is happening, where, why it matters, who is affected, and how disruption propagates through your network.
          </p>
        </div>
        <Link to="/simulate" className="btn-primary shrink-0">
          <Play className="h-4 w-4" />
          Run scenario on map
        </Link>
      </header>

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
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-red-300 text-sm" role="alert">
          Failed to load map intelligence layers. Ensure API and Neo4j are running, then run <code>make seed-all</code>.
        </div>
      )}
      {isLoading && <LoadingState label="Loading global risk layers…" />}

      {!isLoading && (
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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

      <Panel title="High-risk entities" subtitle="Click map markers for drill-down">
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
                <div className="flex justify-between gap-2">
                  <span className="font-medium text-white truncate text-sm">{f.properties.name}</span>
                  <span className={`risk-pill text-[10px] ${riskPillClass(f.properties.risk_score)}`}>
                    {Math.round((f.properties.risk_score ?? 0) * 100)}%
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">{f.properties.country || f.properties.entity_type}</p>
              </button>
            ))}
        </div>
      </Panel>
    </div>
  );
}
