/**
 * Demo sector intelligence — clearly labelled template data for portfolio demos.
 * Replace with live analytics API when country-level price indices are modelled.
 */

export const SECTOR_PROFILES = {
  semiconductors: {
    label: 'Semiconductors',
    whyImportant:
      'Advanced chips power AI, defence, automotive ADAS, and cloud infrastructure. A single fab outage can idle downstream assembly for weeks.',
    peopleImpact:
      'Disruption raises consumer electronics prices, delays medical devices, and affects ~12M direct semiconductor jobs globally — with multiplier effects in logistics and retail.',
    globalExposure: 'Taiwan, South Korea, and US fabs concentrate ~75% of leading-edge capacity.',
  },
  energy: {
    label: 'Energy',
    whyImportant:
      'Oil, LNG, and petrochemical feedstocks underpin transport, heating, and plastics. Chokepoint closures ripple into every sector within days.',
    peopleImpact:
      'Energy shocks hit household fuel bills first; developing economies face fuel subsidies strain and power rationing affecting hundreds of millions.',
    globalExposure: 'Strait of Hormuz, Red Sea, and North Sea hubs anchor Atlantic–Asia flows.',
  },
  automotive: {
    label: 'Automotive',
    whyImportant:
      'Just-in-time assembly depends on tier-2/3 parts crossing borders daily. Missing one sensor line stops entire plants.',
    peopleImpact:
      'Plant shutdowns furlough autoworkers and dealer networks; used-car prices and repair part availability spike for consumers.',
    globalExposure: 'Germany, Mexico, US Midwest, and Japan anchor global OEM supply webs.',
  },
  shipping: {
    label: 'Shipping & logistics',
    whyImportant:
      'Maritime lanes move ~80% of trade by volume. Port congestion and canal blockages are the fastest path from geopolitics to shelf stock-outs.',
    peopleImpact:
      'Delayed containers raise food and medicine costs in import-dependent regions; port workers face irregular shifts during surges.',
    globalExposure: 'Suez, Panama, Singapore, Rotterdam, and LA/Long Beach are systemic nodes.',
  },
};

/** Country risk band + price index by sector (demo template). */
export const COUNTRY_RISK_BY_SECTOR = {
  semiconductors: [
    { iso: 'TWN', name: 'Taiwan', riskBand: 'high', priceIndex: 142, lat: 23.7, lon: 121.0, populationAtRisk: 23.5 },
    { iso: 'KOR', name: 'South Korea', riskBand: 'medium', priceIndex: 118, lat: 36.5, lon: 127.9, populationAtRisk: 8.2 },
    { iso: 'USA', name: 'United States', riskBand: 'low', priceIndex: 105, lat: 37.1, lon: -95.7, populationAtRisk: 4.1 },
    { iso: 'CHN', name: 'China', riskBand: 'medium', priceIndex: 112, lat: 35.9, lon: 104.2, populationAtRisk: 18.6 },
    { iso: 'JPN', name: 'Japan', riskBand: 'low', priceIndex: 108, lat: 36.2, lon: 138.3, populationAtRisk: 2.8 },
    { iso: 'NLD', name: 'Netherlands', riskBand: 'low', priceIndex: 103, lat: 52.1, lon: 5.3, populationAtRisk: 1.2 },
  ],
  energy: [
    { iso: 'SAU', name: 'Saudi Arabia', riskBand: 'medium', priceIndex: 125, lat: 23.9, lon: 45.1, populationAtRisk: 12.4 },
    { iso: 'IRN', name: 'Iran', riskBand: 'high', priceIndex: 138, lat: 32.4, lon: 53.7, populationAtRisk: 9.8 },
    { iso: 'RUS', name: 'Russia', riskBand: 'high', priceIndex: 135, lat: 61.5, lon: 105.3, populationAtRisk: 11.2 },
    { iso: 'NOR', name: 'Norway', riskBand: 'low', priceIndex: 102, lat: 60.5, lon: 8.5, populationAtRisk: 0.9 },
    { iso: 'QAT', name: 'Qatar', riskBand: 'medium', priceIndex: 119, lat: 25.3, lon: 51.2, populationAtRisk: 2.1 },
    { iso: 'USA', name: 'United States', riskBand: 'low', priceIndex: 104, lat: 39.8, lon: -98.6, populationAtRisk: 3.5 },
  ],
  automotive: [
    { iso: 'DEU', name: 'Germany', riskBand: 'medium', priceIndex: 115, lat: 51.2, lon: 10.5, populationAtRisk: 6.7 },
    { iso: 'MEX', name: 'Mexico', riskBand: 'medium', priceIndex: 110, lat: 23.6, lon: -102.6, populationAtRisk: 5.4 },
    { iso: 'JPN', name: 'Japan', riskBand: 'low', priceIndex: 106, lat: 36.2, lon: 138.3, populationAtRisk: 3.2 },
    { iso: 'USA', name: 'United States', riskBand: 'low', priceIndex: 104, lat: 39.8, lon: -98.6, populationAtRisk: 4.8 },
    { iso: 'CHN', name: 'China', riskBand: 'medium', priceIndex: 111, lat: 35.9, lon: 104.2, populationAtRisk: 14.2 },
    { iso: 'THA', name: 'Thailand', riskBand: 'low', priceIndex: 107, lat: 15.9, lon: 100.9, populationAtRisk: 2.3 },
  ],
  shipping: [
    { iso: 'EGY', name: 'Egypt', riskBand: 'high', priceIndex: 128, lat: 30.0, lon: 31.2, populationAtRisk: 7.5 },
    { iso: 'SGP', name: 'Singapore', riskBand: 'medium', priceIndex: 114, lat: 1.35, lon: 103.8, populationAtRisk: 2.9 },
    { iso: 'NLD', name: 'Netherlands', riskBand: 'low', priceIndex: 105, lat: 52.1, lon: 4.5, populationAtRisk: 1.8 },
    { iso: 'PAN', name: 'Panama', riskBand: 'medium', priceIndex: 116, lat: 9.0, lon: -79.5, populationAtRisk: 1.4 },
    { iso: 'YEM', name: 'Yemen', riskBand: 'high', priceIndex: 132, lat: 15.6, lon: 48.5, populationAtRisk: 8.1 },
    { iso: 'CHN', name: 'China', riskBand: 'medium', priceIndex: 109, lat: 31.2, lon: 121.5, populationAtRisk: 6.3 },
  ],
};

/** Scenario-specific country overlays for simulator (demo). */
export const SCENARIO_COUNTRY_OVERLAY = {
  'red-sea-bab-el-mandeb': COUNTRY_RISK_BY_SECTOR.shipping,
  'suez-canal-blockage': COUNTRY_RISK_BY_SECTOR.shipping,
  'taiwan-strait-tension': COUNTRY_RISK_BY_SECTOR.semiconductors,
  'russia-ukraine-supply': COUNTRY_RISK_BY_SECTOR.energy,
  'us-iran-hormuz': COUNTRY_RISK_BY_SECTOR.energy,
  'china-us-trade': COUNTRY_RISK_BY_SECTOR.semiconductors,
};

export function inferSupplierSector(name = '', industry = '') {
  const text = `${name} ${industry}`.toLowerCase();
  if (/semiconductor|chip|electronics|taiwan/.test(text)) return 'semiconductors';
  if (/energy|oil|lng|chemical/.test(text)) return 'energy';
  if (/auto|motor|vehicle|parts/.test(text)) return 'automotive';
  if (/port|shipping|maritime|logistics/.test(text)) return 'shipping';
  return 'automotive';
}

export function riskBandColor(band) {
  if (band === 'high') return '#ef4444';
  if (band === 'medium') return '#eab308';
  return '#22c55e';
}

export function riskBandLabel(band) {
  if (band === 'high') return 'Elevated';
  if (band === 'medium') return 'Watch';
  return 'Stable';
}
