-- Object Candidates Staging Table
CREATE TABLE IF NOT EXISTS edna_object_candidates (
    candidate_id SERIAL PRIMARY KEY,
    schema VARCHAR(100) NOT NULL,
    table_name VARCHAR(255) NOT NULL,
    guess_type VARCHAR(100) NOT NULL,
    row_count BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE(schema, table_name)
);

CREATE INDEX IF NOT EXISTS idx_edna_object_candidates_schema ON edna_object_candidates(schema);
CREATE INDEX IF NOT EXISTS idx_edna_object_candidates_guess_type ON edna_object_candidates(guess_type);
CREATE INDEX IF NOT EXISTS idx_edna_object_candidates_created_at ON edna_object_candidates(created_at);

