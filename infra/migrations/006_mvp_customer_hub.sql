-- 006_mvp_customer_hub.sql
-- MVP Customer Data Hub schema: scan runs, profiling, golden customers, links, KPIs and event hooks

BEGIN;

-- Table: scan_run
CREATE TABLE IF NOT EXISTS scan_run (
    scan_run_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system    TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'PENDING', -- PENDING/RUNNING/SUCCESS/FAILED
    started_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ended_at         TIMESTAMPTZ,
    metrics_json     JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_scan_run_source_system
    ON scan_run (source_system);

CREATE INDEX IF NOT EXISTS idx_scan_run_status
    ON scan_run (status);


-- Table: scan_profile_table
CREATE TABLE IF NOT EXISTS scan_profile_table (
    id              BIGSERIAL PRIMARY KEY,
    scan_run_id     UUID NOT NULL REFERENCES scan_run(scan_run_id) ON DELETE CASCADE,
    source_system   TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    row_count       BIGINT,
    sample_hash     TEXT,
    profiled_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_profile_table_run_table
    ON scan_profile_table (scan_run_id, table_name);

CREATE INDEX IF NOT EXISTS idx_scan_profile_table_source
    ON scan_profile_table (source_system);


-- Table: scan_profile_column
CREATE TABLE IF NOT EXISTS scan_profile_column (
    id              BIGSERIAL PRIMARY KEY,
    scan_run_id     UUID NOT NULL REFERENCES scan_run(scan_run_id) ON DELETE CASCADE,
    source_system   TEXT NOT NULL,
    table_name      TEXT NOT NULL,
    column_name     TEXT NOT NULL,
    data_type       TEXT,
    row_count       BIGINT,
    distinct_count  BIGINT,
    null_count      BIGINT,
    null_rate       NUMERIC(5,4), -- 0.0000 - 1.0000
    sample_hash     TEXT,
    profiled_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_scan_profile_column_run_col
    ON scan_profile_column (scan_run_id, table_name, column_name);

CREATE INDEX IF NOT EXISTS idx_scan_profile_column_source
    ON scan_profile_column (source_system);


-- Table: object_customer (golden customers)
CREATE TABLE IF NOT EXISTS object_customer (
    customer_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT,
    email           TEXT,
    tax_id          TEXT,
    country         TEXT,
    source_expr     TEXT,          -- expression describing how attributes were derived
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_object_customer_email
    ON object_customer (LOWER(email));

CREATE INDEX IF NOT EXISTS idx_object_customer_tax_id
    ON object_customer (tax_id);

CREATE INDEX IF NOT EXISTS idx_object_customer_country
    ON object_customer (country);


-- Table: object_customer_source_link (links from golden to source rows)
CREATE TABLE IF NOT EXISTS object_customer_source_link (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     UUID NOT NULL REFERENCES object_customer(customer_id) ON DELETE CASCADE,
    source_system   TEXT NOT NULL,
    source_table    TEXT NOT NULL,
    source_pk       TEXT NOT NULL,
    match_rule      TEXT NOT NULL,   -- e.g. 'tax_id', 'email', 'name_country'
    confidence      NUMERIC(5,4),    -- 0.0000 - 1.0000
    explanation     TEXT,            -- short human-readable explanation
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_object_customer_source
    ON object_customer_source_link (source_system, source_table, source_pk);

CREATE INDEX IF NOT EXISTS idx_object_customer_source_customer
    ON object_customer_source_link (customer_id);


-- Table: kpi_fact (simple KPI store)
CREATE TABLE IF NOT EXISTS kpi_fact (
    id              BIGSERIAL PRIMARY KEY,
    kpi_key         TEXT NOT NULL,
    value           NUMERIC,
    scan_run_id     UUID REFERENCES scan_run(scan_run_id) ON DELETE SET NULL,
    computed_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details_json    JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_kpi_fact_key
    ON kpi_fact (kpi_key);

CREATE INDEX IF NOT EXISTS idx_kpi_fact_scan_run
    ON kpi_fact (scan_run_id);


-- Event hooks: raw and normalized events (schema only for now)
CREATE TABLE IF NOT EXISTS event_raw (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system   TEXT NOT NULL,
    case_key_hint   TEXT,
    payload         JSONB NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_raw_source_system
    ON event_raw (source_system);


CREATE TABLE IF NOT EXISTS event_normalized (
    event_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_system   TEXT NOT NULL,
    case_key_hint   TEXT,
    normalized_type TEXT,
    normalized_data JSONB NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_event_normalized_source_system
    ON event_normalized (source_system);

COMMIT;


