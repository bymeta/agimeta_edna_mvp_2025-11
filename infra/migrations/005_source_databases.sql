-- Source Databases Table
-- Stores connection information for PostgreSQL databases to be scanned
CREATE TABLE IF NOT EXISTS edna_source_databases (
    source_db_id VARCHAR(255) PRIMARY KEY,
    source_db_name VARCHAR(255) NOT NULL,
    description TEXT,
    host VARCHAR(255) NOT NULL,
    port INTEGER NOT NULL DEFAULT 5432,
    database_name VARCHAR(255) NOT NULL,
    username VARCHAR(255) NOT NULL,
    password_encrypted TEXT,  -- Encrypted password (for future use)
    schemas TEXT[],  -- Array of schema names to scan (empty = all schemas)
    table_blacklist TEXT[],  -- Array of table name patterns to exclude (e.g., ['edna_%', 'pg_%'])
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_scan_at TIMESTAMP WITH TIME ZONE,
    last_scan_status VARCHAR(50),  -- 'success', 'failed', 'pending'
    last_scan_error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_edna_source_databases_active ON edna_source_databases(active);
CREATE INDEX IF NOT EXISTS idx_edna_source_databases_last_scan_at ON edna_source_databases(last_scan_at);
CREATE INDEX IF NOT EXISTS idx_edna_source_databases_source_db_name ON edna_source_databases(source_db_name);

-- Comments
COMMENT ON TABLE edna_source_databases IS 'Configuration for external PostgreSQL databases to be scanned';
COMMENT ON COLUMN edna_source_databases.source_db_id IS 'Unique identifier for the source database';
COMMENT ON COLUMN edna_source_databases.schemas IS 'List of schemas to scan. Empty array means scan all schemas';
COMMENT ON COLUMN edna_source_databases.table_blacklist IS 'Table name patterns to exclude from scanning (supports % wildcard)';

