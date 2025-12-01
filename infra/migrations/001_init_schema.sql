-- Enterprise DNA Database Schema

-- Migration tracking table (if not exists from 000_migration_tracking.sql)
CREATE TABLE IF NOT EXISTS edna_migrations (
    migration_id VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_edna_migrations_applied_at ON edna_migrations(applied_at);

-- Golden Objects Table
CREATE TABLE IF NOT EXISTS edna_objects (
    golden_id VARCHAR(255) PRIMARY KEY,
    source_system VARCHAR(100) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(source_system, source_id, object_type)
);

-- Events Table
CREATE TABLE IF NOT EXISTS edna_events (
    event_id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    golden_id VARCHAR(255),
    source_system VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    occurred_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Identity Rules Table
CREATE TABLE IF NOT EXISTS edna_identity_rules (
    rule_id VARCHAR(255) PRIMARY KEY,
    rule_name VARCHAR(255) NOT NULL,
    object_type VARCHAR(100) NOT NULL,
    source_system VARCHAR(100) NOT NULL,
    key_fields JSONB NOT NULL,
    normalization_rules JSONB NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_edna_objects_source_system ON edna_objects(source_system);
CREATE INDEX IF NOT EXISTS idx_edna_objects_object_type ON edna_objects(object_type);
CREATE INDEX IF NOT EXISTS idx_edna_objects_created_at ON edna_objects(created_at);

CREATE INDEX IF NOT EXISTS idx_edna_events_golden_id ON edna_events(golden_id);
CREATE INDEX IF NOT EXISTS idx_edna_events_event_type ON edna_events(event_type);
CREATE INDEX IF NOT EXISTS idx_edna_events_source_system ON edna_events(source_system);
CREATE INDEX IF NOT EXISTS idx_edna_events_occurred_at ON edna_events(occurred_at);

CREATE INDEX IF NOT EXISTS idx_edna_identity_rules_object_type ON edna_identity_rules(object_type);
CREATE INDEX IF NOT EXISTS idx_edna_identity_rules_source_system ON edna_identity_rules(source_system);
CREATE INDEX IF NOT EXISTS idx_edna_identity_rules_active ON edna_identity_rules(active);

-- Glossary Table
CREATE TABLE IF NOT EXISTS edna_glossary (
    term VARCHAR(255) PRIMARY KEY,
    definition TEXT NOT NULL,
    category VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- GIN indexes for JSONB columns
CREATE INDEX IF NOT EXISTS idx_edna_objects_attributes_gin ON edna_objects USING GIN (attributes);
CREATE INDEX IF NOT EXISTS idx_edna_events_payload_gin ON edna_events USING GIN (payload);
CREATE INDEX IF NOT EXISTS idx_edna_glossary_category ON edna_glossary(category);

