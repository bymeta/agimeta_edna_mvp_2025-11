-- Migration tracking table
CREATE TABLE IF NOT EXISTS edna_migrations (
    migration_id VARCHAR(255) PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    checksum VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_edna_migrations_applied_at ON edna_migrations(applied_at);

