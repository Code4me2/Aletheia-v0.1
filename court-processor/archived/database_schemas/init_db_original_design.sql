-- Court opinion database schema for data-compose integration
-- Focused on judge-based retrieval for RAG pipeline

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS court_data;

-- Judges table (simple, focused on name as primary identifier)
CREATE TABLE IF NOT EXISTS court_data.judges (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    court VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on judge name for fast lookups
CREATE INDEX IF NOT EXISTS idx_judges_name ON court_data.judges(name);
CREATE INDEX IF NOT EXISTS idx_judges_court ON court_data.judges(court);

-- Opinions table (optimized for judge-based retrieval)
CREATE TABLE IF NOT EXISTS court_data.opinions (
    id SERIAL PRIMARY KEY,
    judge_id INTEGER REFERENCES court_data.judges(id),
    case_name TEXT,
    case_date DATE NOT NULL,
    docket_number VARCHAR(100),
    court_code VARCHAR(50),
    
    -- PDF and text storage
    pdf_url TEXT,
    pdf_path VARCHAR(500),
    text_content TEXT NOT NULL,
    
    -- Metadata storage
    metadata JSONB DEFAULT '{}',
    pdf_metadata JSONB DEFAULT '{}',
    
    -- Processing status
    processing_status VARCHAR(50) DEFAULT 'completed',
    processing_error TEXT,
    
    -- Integration with data-compose
    vector_indexed BOOLEAN DEFAULT false,
    hierarchical_doc_id INTEGER,  -- Reference to hierarchical_documents if integrated
    
    -- Timestamps
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Constraints
    CONSTRAINT unique_opinion UNIQUE (court_code, docket_number, case_date)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_opinions_judge_date ON court_data.opinions(judge_id, case_date DESC);
CREATE INDEX IF NOT EXISTS idx_opinions_date ON court_data.opinions(case_date DESC);
CREATE INDEX IF NOT EXISTS idx_opinions_court ON court_data.opinions(court_code);
CREATE INDEX IF NOT EXISTS idx_opinions_docket ON court_data.opinions(docket_number);
CREATE INDEX IF NOT EXISTS idx_opinions_vector ON court_data.opinions(vector_indexed) WHERE vector_indexed = false;

-- Full text search index
CREATE INDEX IF NOT EXISTS idx_opinions_text_search 
ON court_data.opinions 
USING gin(to_tsvector('english', text_content));

-- Processing log table (for monitoring and debugging)
CREATE TABLE IF NOT EXISTS court_data.processing_log (
    id SERIAL PRIMARY KEY,
    court_code VARCHAR(50),
    run_date DATE,
    opinions_found INTEGER DEFAULT 0,
    opinions_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'running'
);

-- Create function to update timestamps
CREATE OR REPLACE FUNCTION court_data.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_judges_updated_at BEFORE UPDATE ON court_data.judges
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

CREATE TRIGGER update_opinions_updated_at BEFORE UPDATE ON court_data.opinions
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

-- Helper view for judge statistics
CREATE OR REPLACE VIEW court_data.judge_stats AS
SELECT 
    j.id,
    j.name,
    j.court,
    COUNT(o.id) as opinion_count,
    MIN(o.case_date) as earliest_opinion,
    MAX(o.case_date) as latest_opinion,
    COUNT(o.id) FILTER (WHERE o.vector_indexed = false) as pending_indexing
FROM court_data.judges j
LEFT JOIN court_data.opinions o ON j.id = o.judge_id
GROUP BY j.id, j.name, j.court;

-- Helper function to get or create judge
CREATE OR REPLACE FUNCTION court_data.get_or_create_judge(
    p_judge_name VARCHAR(255),
    p_court VARCHAR(100)
) RETURNS INTEGER AS $$
DECLARE
    v_judge_id INTEGER;
BEGIN
    -- Try to find existing judge
    SELECT id INTO v_judge_id
    FROM court_data.judges
    WHERE name = p_judge_name;
    
    -- If not found, create new judge
    IF v_judge_id IS NULL THEN
        INSERT INTO court_data.judges (name, court)
        VALUES (p_judge_name, p_court)
        ON CONFLICT (name) DO UPDATE SET court = EXCLUDED.court
        RETURNING id INTO v_judge_id;
    END IF;
    
    RETURN v_judge_id;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions (adjust as needed for your setup)
-- GRANT USAGE ON SCHEMA court_data TO your_app_user;
-- GRANT ALL ON ALL TABLES IN SCHEMA court_data TO your_app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA court_data TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA court_data TO your_app_user;