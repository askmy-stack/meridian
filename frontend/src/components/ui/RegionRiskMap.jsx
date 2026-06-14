import { useMemo } from 'react';
import MapboxMap, { Layer, Source } from 'react-map-gl';
import MapLibreMap from 'react-map-gl/maplibre';
import { riskBandColor } from '../../data/sectorIntelligence';
import 'mapbox-gl/dist/mapbox-gl.css';
import 'maplibre-gl/dist/maplibre-gl.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN?.trim();
const CARTO_DARK_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

/**
 * Choropleth-style country risk map using point markers (demo data).
 * Green / yellow / red bands from riskBand field.
 */
export function RegionRiskMap({ countries = [], height = 320, title }) {
  const geojson = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: countries
        .filter((c) => c.lat != null && c.lon != null)
        .map((c) => ({
          type: 'Feature',
          geometry: { type: 'Point', coordinates: [c.lon, c.lat] },
          properties: {
            iso: c.iso,
            name: c.name,
            riskBand: c.riskBand,
            priceIndex: c.priceIndex,
            color: riskBandColor(c.riskBand),
          },
        })),
    }),
    [countries],
  );

  const initialView = useMemo(() => {
    if (countries.length === 0) return { longitude: 20, latitude: 25, zoom: 1.2 };
    const lons = countries.map((c) => c.lon);
    const lats = countries.map((c) => c.lat);
    return {
      longitude: (Math.min(...lons) + Math.max(...lons)) / 2,
      latitude: (Math.min(...lats) + Math.max(...lats)) / 2,
      zoom: 1.4,
    };
  }, [countries]);

  const layers = (
    <Source id="country-risk" type="geojson" data={geojson}>
      <Layer
        id="country-risk-circles"
        type="circle"
        paint={{
          'circle-radius': ['interpolate', ['linear'], ['get', 'priceIndex'], 100, 10, 140, 18],
          'circle-color': ['get', 'color'],
          'circle-opacity': 0.82,
          'circle-stroke-width': 2,
          'circle-stroke-color': '#ffffff',
        }}
      />
    </Source>
  );

  const legend = (
    <div className="absolute bottom-3 left-3 right-3 flex flex-wrap items-center justify-between gap-2 z-10">
      <div className="flex flex-wrap gap-2 text-[10px]">
        {[
          { color: '#22c55e', label: 'Stable' },
          { color: '#eab308', label: 'Watch' },
          { color: '#ef4444', label: 'Elevated' },
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
      {title && <span className="text-[10px] text-slate-500">{title}</span>}
    </div>
  );

  const containerClass =
    'relative w-full rounded-2xl overflow-hidden border border-slate-700/60 bg-slate-950';

  if (countries.length === 0) {
    return (
      <div
        className={`${containerClass} flex items-center justify-center text-slate-500 text-sm`}
        style={{ height }}
      >
        No regional data for this view
      </div>
    );
  }

  if (MAPBOX_TOKEN) {
    return (
      <div className={containerClass} style={{ height }}>
        <MapboxMap
          initialViewState={initialView}
          mapboxAccessToken={MAPBOX_TOKEN}
          mapStyle="mapbox://styles/mapbox/dark-v11"
          style={{ width: '100%', height: '100%' }}
          interactive={false}
        >
          {layers}
        </MapboxMap>
        {legend}
      </div>
    );
  }

  return (
    <div className={containerClass} style={{ height }}>
      <MapLibreMap
        initialViewState={initialView}
        mapStyle={CARTO_DARK_STYLE}
        style={{ width: '100%', height: '100%' }}
        interactive={false}
      >
        {layers}
      </MapLibreMap>
      {legend}
    </div>
  );
}
