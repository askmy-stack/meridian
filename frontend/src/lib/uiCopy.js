/** Shared UI copy — terminology must stay identical across all pages. */

export const SCRI_SUBLABEL = 'Modelled index';
export const SCRI_BADGE = 'SCRI · modelled index 0–100';
export const SCRI_TOOLTIP =
  'Supply Chain Risk Index — band-first modelled disruption exposure (0–100% secondary) from XGBoost + SHAP.';

export const DEMO_SECTOR_NOTE = 'Sector assignment: keyword match (demo)';
export const TIMELINE_DIGEST_LABEL = 'Daily digest · template';
export const TIMELINE_QUIET_DAYS_NOTE =
  'Quiet days show Daily digest · template entries (clearly labelled). Graph-linked events come from Neo4j.';
export const TEMPLATE_NARRATIVE_BADGE = 'Weekly digest · template narrative';

export const COPILOT_DISCLAIMER =
  'RAG-grounded answers cite retrieved documents and graph facts. Numeric SCRI always from XGBoost, never from the LLM.';

export const METRICS_URL = 'https://github.com/askmy-stack/meridian/blob/main/docs/METRICS.md';
export const LIMITATIONS_URL = 'https://github.com/askmy-stack/meridian/blob/main/docs/LIMITATIONS.md';
export const LIMITATIONS_LINK_TEXT = 'Known limitations';
export const METRICS_LINK_TEXT = 'SCRI methodology & references';

export const FOOTER_MODEL_NOTE =
  'SCRI bands are modelled indices from XGBoost + SHAP — not validated probabilities.';

/** Nav labels must match PageHeader `title` exactly. */
export const NAV_LABELS = {
  dashboard: 'Risk Intelligence',
  network: 'Supply Chain Graph',
  map: 'Risk Map',
  timeline: 'Geopolitical Timeline',
  sectors: 'Sector Risk Dashboard',
  suppliers: 'Supplier Registry',
  simulate: 'Disruption Simulator',
  copilot: 'Intelligence Copilot',
  alerts: 'Risk Alerts',
  graphHealth: 'Graph Health',
};

export const LOADING = {
  dashboard: 'Loading command center…',
  network: 'Building supply graph…',
  map: 'Loading global risk layers…',
  timeline: 'Loading timeline…',
  sectors: 'Loading sector dashboard…',
  suppliers: 'Loading suppliers…',
  simulation: 'Loading scenarios…',
  copilot: 'Analyzing graph context…',
  graphHealth: 'Loading graph health…',
  alerts: 'Loading alerts…',
};

export const ERRORS = {
  dashboard: 'Could not load dashboard data — ensure the API is running on port 8002.',
  network: 'Could not load graph — ensure Neo4j is running and seeded.',
  map: 'Failed to load map intelligence layers. Ensure API and Neo4j are running, then run make seed-all.',
  timeline: 'Could not load timeline — run make seed-demo after Neo4j is up.',
  sectors: 'Failed to load sector data. Ensure Neo4j is seeded.',
  suppliers: 'Could not load suppliers — ensure Neo4j is seeded (`make seed-all`).',
  supplierExplanation: 'Could not load SCRI explanation for this supplier.',
  simulation: 'Could not load simulation scenarios.',
  simulationRun: 'Simulation failed — check API logs and Neo4j connectivity.',
  copilot: 'Copilot request failed — check API, Qdrant, and Neo4j are running.',
  graphHealth: 'Could not load graph health — Neo4j may be down or unseeded.',
  alerts: 'Could not load alerts — ensure the API is running.',
  backtest: 'Could not load backtest data — run `make backtest-scri` and ensure the API is up.',
};
