-- TimescaleDB schema for Meridian Phase A (score + event history)
CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS supplier_score_history (
    supplier_id TEXT NOT NULL,
    risk_score DOUBLE PRECISION NOT NULL,
    risk_category TEXT NOT NULL,
    model_version TEXT NOT NULL,
    feature_snapshot JSONB,
    scored_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('supplier_score_history', 'scored_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_supplier_score_history_supplier
    ON supplier_score_history (supplier_id, scored_at DESC);

CREATE TABLE IF NOT EXISTS event_signal_history (
    event_id TEXT,
    severity DOUBLE PRECISION,
    source TEXT NOT NULL,
    linked_supplier_count INTEGER NOT NULL DEFAULT 0,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

SELECT create_hypertable('event_signal_history', 'ingested_at', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_event_signal_history_source
    ON event_signal_history (source, ingested_at DESC);
