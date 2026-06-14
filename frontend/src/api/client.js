/**
 * Shared API client for the Meridian frontend.
 *
 * Reads `VITE_API_BASE_URL` from frontend env (defaults to /api proxy).
 * In dev, vite.config.js proxies /api/* to the FastAPI backend.
 */
import axios from 'axios';

const baseURL =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  '/api';

export const apiClient = axios.create({
  baseURL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
});

// Attach JWT if present in localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('meridian_access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export async function fetchAlerts({ tier, limit = 50 } = {}) {
  const params = { limit };
  if (tier) params.tier = tier;
  const { data } = await apiClient.get('/alerts', { params });
  return data;
}

export async function fetchAlertStats() {
  const { data } = await apiClient.get('/alerts/stats');
  return data;
}

export async function fetchNetwork({ depth = 2 } = {}) {
  const { data } = await apiClient.get('/visualization/network', {
    params: { depth },
  });
  return data;
}

export async function fetchStats() {
  const { data } = await apiClient.get('/stats');
  return data;
}

export async function fetchMetricsMethodology() {
  const { data } = await apiClient.get('/metrics/methodology');
  return data;
}

export async function fetchWeeklyDigest() {
  const { data } = await apiClient.post('/intelligence/weekly-digest');
  return data;
}

export async function sendTestAlert() {
  const { data } = await apiClient.post('/alerts/test');
  return data;
}

export async function fetchMapLayers({
  entityType = 'supplier',
  includeZones = true,
  includeRoutes = true,
  includeEvents = true,
} = {}) {
  const { data } = await apiClient.get('/geopolitical/map-layers', {
    params: {
      entity_type: entityType,
      include_zones: includeZones,
      include_routes: includeRoutes,
      include_events: includeEvents,
    },
  });
  return data;
}

export async function fetchEventTimeline({ days = 30 } = {}) {
  const { data } = await apiClient.get('/geopolitical/timeline', { params: { days } });
  return data;
}

export async function fetchConflictZones() {
  const { data } = await apiClient.get('/geopolitical/conflict-zones');
  return data;
}

export async function fetchTradeRoutes({ limit = 120 } = {}) {
  const { data } = await apiClient.get('/geopolitical/trade-routes', { params: { limit } });
  return data;
}

export async function fetchGeopoliticalEvents({ days = 30, eventType } = {}) {
  const params = { days };
  if (eventType) params.event_type = eventType;
  const { data } = await apiClient.get('/geopolitical/events', { params });
  return data;
}

export async function fetchRiskMap({ entityType = 'supplier', minRisk = 0 } = {}) {
  const { data } = await apiClient.get('/visualization/risk-map', {
    params: { entity_type: entityType, min_risk: minRisk },
  });
  return data;
}

export async function fetchSuppliers({ limit = 100, country } = {}) {
  const params = { limit };
  if (country) params.country = country;
  const { data } = await apiClient.get('/suppliers', { params });
  return data;
}

export async function fetchSupplierExplanation(supplierId) {
  const { data } = await apiClient.get(`/suppliers/${supplierId}/explanation`);
  return data;
}

export async function fetchSupplierForecast(supplierId, horizonDays = 7) {
  const { data } = await apiClient.get(`/intelligence/forecast/${supplierId}`, {
    params: { horizon_days: horizonDays },
  });
  return data;
}

export async function fetchSimulationScenarios() {
  const { data } = await apiClient.get('/simulation/scenarios');
  return data;
}

export async function runSimulationScenario(scenarioId) {
  const { data } = await apiClient.post(`/simulation/scenarios/${scenarioId}/run`);
  return data;
}

export async function compareSimulationScenarios(scenarioIds) {
  const { data } = await apiClient.post('/simulation/compare', { scenario_ids: scenarioIds });
  return data;
}

export async function fetchSectorDashboard() {
  const { data } = await apiClient.get('/analytics/sectors');
  return data;
}

export async function fetchGraphHealth() {
  const { data } = await apiClient.get('/analytics/graph/health');
  return data;
}

export function getDigestExportUrl() {
  const base =
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    '/api';
  return `${base}/analytics/export/digest.md`;
}

export async function fetchWeatherLayer() {
  const { data } = await apiClient.get('/intelligence/layers/weather');
  return data;
}

export async function fetchSanctionsLayer() {
  const { data } = await apiClient.get('/intelligence/layers/sanctions');
  return data;
}

export async function fetchBacktest(scenarioId) {
  const { data } = await apiClient.get(`/intelligence/backtest/${scenarioId}`);
  return data;
}

export async function askCopilot(question) {
  const { data } = await apiClient.post('/intelligence/copilot', { question });
  return data;
}

export async function login(username, password) {
  const body = new URLSearchParams({ username, password });
  const { data } = await apiClient.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  });
  localStorage.setItem('meridian_access_token', data.access_token);
  localStorage.setItem('meridian_refresh_token', data.refresh_token);
  return data;
}

export async function fetchCurrentUser() {
  const { data } = await apiClient.get('/auth/me');
  return data;
}

export function logout() {
  localStorage.removeItem('meridian_access_token');
  localStorage.removeItem('meridian_refresh_token');
}
