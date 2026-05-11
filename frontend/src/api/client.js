/**
 * Shared API client for the Meridian frontend.
 *
 * Reads `VITE_API_BASE_URL` from frontend env (defaults to /api proxy).
 * In dev, vite.config.js proxies /api/* to the FastAPI backend.
 */
import axios from 'axios';

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

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
