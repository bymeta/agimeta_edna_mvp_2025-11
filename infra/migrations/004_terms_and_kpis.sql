-- Terms Table
CREATE TABLE IF NOT EXISTS edna_terms (
    term_id VARCHAR(255) PRIMARY KEY,
    term_name VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    object_type VARCHAR(100),
    category VARCHAR(100),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- KPIs Table
CREATE TABLE IF NOT EXISTS edna_kpis (
    kpi_id VARCHAR(255) PRIMARY KEY,
    kpi_name VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    metric_type VARCHAR(100),
    unit VARCHAR(50),
    object_type VARCHAR(100),
    calculation_formula TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_edna_terms_object_type ON edna_terms(object_type);
CREATE INDEX IF NOT EXISTS idx_edna_terms_category ON edna_terms(category);
CREATE INDEX IF NOT EXISTS idx_edna_terms_created_at ON edna_terms(created_at);

CREATE INDEX IF NOT EXISTS idx_edna_kpis_object_type ON edna_kpis(object_type);
CREATE INDEX IF NOT EXISTS idx_edna_kpis_metric_type ON edna_kpis(metric_type);
CREATE INDEX IF NOT EXISTS idx_edna_kpis_created_at ON edna_kpis(created_at);

