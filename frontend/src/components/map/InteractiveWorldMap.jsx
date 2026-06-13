import { useCallback, useMemo, useState } from 'react';
import { useQuery } from 'react-query';
import MapboxMap, { Layer, Source } from 'react-map-gl';
import MapLibreMap from 'react-map-gl/maplibre';
import { fetchConflictZones } from '../../api/client';
import { riskColor } from '../../lib/risk';
import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN?.trim();
const CARTO_DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

const ZONE_FILL = {
  id: 'conflict-zones-fill',
  type: 'fill',
  paint: {
    'fill-color': [
      'interpolate',
      ['linear'],
      ['get', 'severity'],
      0.5, '#f59e0b',
      0.7, '#f97316',
      0.85, '#ef4444',
      1, '#b91c1c',
    ],
    'fill-opacity': 0.22,
  },
};

const ZONE_OUTLINE = {
  id: 'conflict-zones-outline',
  type: 'line',
  paint: {
    'line-color': '#f87171',
    'line-width': 1.5,
    'line-opacity': 0.7,
  },
};

const ROUTE_LINE = {
  id: 'trade-routes-line',
  type: 'line',
  paint: {
    'line-color': [
      'interpolate',
      ['linear'],
      ['get', 'risk_score'],
      0, '#38bdf8',
      0.5, '#fbbf24',
      1, '#f43f5e',
    ],
    'line-width': 1.2,
    'line-opacity': 0.55,
  },
};

function MapLayers({
  layers,
  entityCollection,
  simulationOverlay,
  extraLayers = {},
}) {
  return (
    <>
      {layers?.conflict_zones?.features?.length > 0 && (
        <Source id="conflict-zones" type="geojson" data={layers.conflict_zones}>
          <Layer {...ZONE_FILL} />
          <Layer {...ZONE_OUTLINE} />
        </Source>
      )}

      {layers?.trade_routes?.features?.length > 0 && (
        <Source id="trade-routes" type="geojson" data={layers.trade_routes}>
          <Layer {...ROUTE_LINE} />
        </Source>
      )}

      {entityCollection.features?.length > 0 && (
        <Source id="entities" type="geojson" data={entityCollection}>
          <Layer
            id="entity-circles"
            type="circle"
            paint={{
              'circle-radius': ['interpolate', ['linear'], ['get', 'risk_score'], 0, 4, 1, 14],
              'circle-color': [
                'interpolate',
                ['linear'],
                ['get', 'risk_score'],
                0, '#22c55e',
                0.5, '#eab308',
                0.8, '#f97316',
                1, '#ef4444',
              ],
              'circle-opacity': 0.85,
              'circle-stroke-width': 1,
              'circle-stroke-color': '#ffffff',
            }}
          />
        </Source>
      )}

      {layers?.events?.features?.length > 0 && (
        <Source id="events" type="geojson" data={layers.events}>
          <Layer
            id="event-circles"
            type="circle"
            paint={{
              'circle-radius': 8,
              'circle-color': '#a855f7',
              'circle-opacity': 0.9,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fbbf24',
            }}
          />
        </Source>
      )}

      {simulationOverlay?.epicenter && (
        <Source
          id="simulation-epicenter"
          type="geojson"
          data={
            simulationOverlay.epicenter.type === 'FeatureCollection'
              ? simulationOverlay.epicenter
              : { type: 'FeatureCollection', features: [simulationOverlay.epicenter] }
          }
        >
          <Layer
            id="simulation-epicenter-circle"
            type="circle"
            paint={{
              'circle-radius': 14,
              'circle-color': '#fbbf24',
              'circle-opacity': 0.9,
              'circle-stroke-width': 3,
              'circle-stroke-color': '#ffffff',
            }}
          />
        </Source>
      )}

      {simulationOverlay?.affected_suppliers?.features?.length > 0 && (
        <Source id="simulation" type="geojson" data={simulationOverlay.affected_suppliers}>
          <Layer
            id="simulation-affected"
            type="circle"
            paint={{
              'circle-radius': 10,
              'circle-color': '#fb7185',
              'circle-opacity': 0.75,
              'circle-stroke-width': 2,
              'circle-stroke-color': '#fff',
            }}
          />
        </Source>
      )}

      {extraLayers?.weather?.features?.length > 0 && (
        <Source id="weather-alerts" type="geojson" data={extraLayers.weather}>
          <Layer
            id="weather-fill"
            type="fill"
            paint={{
              'fill-color': '#0ea5e9',
              'fill-opacity': 0.18,
            }}
          />
          <Layer
            id="weather-outline"
            type="line"
            paint={{ 'line-color': '#38bdf8', 'line-width': 1.2, 'line-opacity': 0.6 }}
          />
        </Source>
      )}

      {extraLayers?.sanctions?.features?.length > 0 && (
        <Source id="sanctions" type="geojson" data={extraLayers.sanctions}>
          <Layer
            id="sanctions-fill"
            type="fill"
            paint={{
              'fill-color': '#a855f7',
              'fill-opacity': 0.2,
            }}
          />
          <Layer
            id="sanctions-outline"
            type="line"
            paint={{ 'line-color': '#c084fc', 'line-width': 1.5, 'line-dasharray': [2, 2] }}
          />
        </Source>
      )}
    </>
  );
}

/**
 * Interactive world map — Mapbox when token is set, otherwise free Carto tiles via MapLibre.
 */
export function InteractiveWorldMap({
  layers = {},
  entityType = 'supplier',
  simulationOverlay = null,
  extraLayers = {},
  onSelectFeature,
  height = 560,
  initialView,
}) {
  const [viewState, setViewState] = useState(
    initialView ?? {
      longitude: 25,
      latitude: 22,
      zoom: 1.35,
    },
  );

  const needsZones = !layers?.conflict_zones?.features?.length;
  const { data: zoneFallback } = useQuery(
    ['conflict-zones'],
    fetchConflictZones,
    { enabled: needsZones, staleTime: 10 * 60_000 },
  );

  const mergedLayers = useMemo(() => {
    const base = { ...layers };
    if (needsZones && zoneFallback?.features?.length) {
      base.conflict_zones = zoneFallback;
    }
    return base;
  }, [layers, needsZones, zoneFallback]);

  const entityCollection = useMemo(() => {
    if (!mergedLayers?.entities) return { type: 'FeatureCollection', features: [] };
    if (mergedLayers.entities.type === 'FeatureCollection') return mergedLayers.entities;
    return mergedLayers.entities[entityType] ?? { type: 'FeatureCollection', features: [] };
  }, [mergedLayers, entityType]);

  const flyTo = useCallback((lon, lat, zoom = 3.5) => {
    setViewState((v) => ({ ...v, longitude: lon, latitude: lat, zoom }));
  }, []);

  const handleMapClick = useCallback(
    (event) => {
      const feature = event.features?.[0];
      if (!feature) return;
      const [lon, lat] = feature.geometry.type === 'Point'
        ? feature.geometry.coordinates
        : feature.geometry.coordinates?.[0]?.[0]
          ? feature.geometry.coordinates[0][0]
          : [viewState.longitude, viewState.latitude];
      flyTo(lon, lat);
      onSelectFeature?.({
        ...feature.properties,
        layer: feature.layer?.id,
        coordinates: feature.geometry.type === 'Point' ? feature.geometry.coordinates : null,
      });
    },
    [flyTo, onSelectFeature, viewState.longitude, viewState.latitude],
  );

  const interactiveLayerIds = [
    'entity-circles',
    'event-circles',
    'conflict-zones-fill',
    'simulation-affected',
    'simulation-epicenter-circle',
  ];

  const mapChildren = (
    <MapLayers
      layers={mergedLayers}
      entityCollection={entityCollection}
      simulationOverlay={simulationOverlay}
      extraLayers={extraLayers}
    />
  );

  const legend = (
    <div className="absolute bottom-3 left-3 flex flex-wrap gap-2 text-[10px] z-10">
      {[
        { color: '#ef4444', label: 'Conflict zones' },
        { color: '#38bdf8', label: 'Trade routes' },
        { color: '#a855f7', label: 'Active events' },
        { color: '#f97316', label: 'Risk entities' },
        ...(extraLayers?.weather?.features?.length ? [{ color: '#38bdf8', label: 'Weather alerts' }] : []),
        ...(extraLayers?.sanctions?.features?.length ? [{ color: '#c084fc', label: 'Sanctions zones' }] : []),
        ...(simulationOverlay ? [{ color: '#fbbf24', label: 'Epicenter' }] : []),
      ].map(({ color, label }) => (
        <span
          key={label}
          className="px-2 py-1 rounded-lg bg-slate-900/90 border border-slate-700 text-slate-300 flex items-center gap-1.5"
        >
          <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
          {label}
        </span>
      ))}
    </div>
  );

  const containerClass =
    'relative w-full rounded-2xl overflow-hidden border border-slate-700/60 bg-slate-950';

  if (MAPBOX_TOKEN) {
    return (
      <div className={containerClass} style={{ height }}>
        <MapboxMap
          {...viewState}
          onMove={(evt) => setViewState(evt.viewState)}
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          style={{ width: '100%', height: '100%' }}
          interactiveLayerIds={interactiveLayerIds}
          onClick={handleMapClick}
        >
          {mapChildren}
        </MapboxMap>
        {legend}
      </div>
    );
  }

  return (
    <div className={containerClass} style={{ height }}>
      <MapLibreMap
        {...viewState}
        onMove={(evt) => setViewState(evt.viewState)}
        mapStyle={CARTO_DARK_STYLE}
        style={{ width: '100%', height: '100%' }}
        interactiveLayerIds={interactiveLayerIds}
        onClick={handleMapClick}
      >
        {mapChildren}
      </MapLibreMap>
      {legend}
    </div>
  );
}
