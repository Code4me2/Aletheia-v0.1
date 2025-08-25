-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS court_data;

-- Create unified opinions table
CREATE TABLE IF NOT EXISTS court_data.opinions_unified (
    id SERIAL PRIMARY KEY,
    
    -- CourtListener fields
    cl_id INTEGER UNIQUE,
    court_id VARCHAR(15),
    docket_number VARCHAR(500),
    case_name TEXT,
    date_filed DATE,
    author_str VARCHAR(200),
    per_curiam BOOLEAN DEFAULT FALSE,
    type VARCHAR(20),
    
    -- Content fields
    plain_text TEXT,
    html TEXT,
    pdf_url TEXT,
    
    -- FLP enhancement fields (JSONB for flexibility)
    citations JSONB DEFAULT '[]',
    judge_info JSONB DEFAULT '{}',
    court_info JSONB DEFAULT '{}',
    
    -- Unstructured.io fields
    structured_elements JSONB DEFAULT '{}',
    
    -- Deduplication
    document_hash VARCHAR(64) UNIQUE NOT NULL,
    
    -- Processing timestamps
    cl_processing_timestamp TIMESTAMPTZ,
    flp_processing_timestamp TIMESTAMPTZ,
    unstructured_processing_timestamp TIMESTAMPTZ,
    
    -- System fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient querying
CREATE INDEX idx_opinions_unified_court_id ON court_data.opinions_unified(court_id);
CREATE INDEX idx_opinions_unified_date_filed ON court_data.opinions_unified(date_filed);
CREATE INDEX idx_opinions_unified_case_name ON court_data.opinions_unified(case_name);
CREATE INDEX idx_opinions_unified_document_hash ON court_data.opinions_unified(document_hash);
CREATE INDEX idx_opinions_unified_created_at ON court_data.opinions_unified(created_at);

-- GIN indexes for JSONB fields
CREATE INDEX idx_opinions_unified_citations_gin ON court_data.opinions_unified USING GIN(citations);
CREATE INDEX idx_opinions_unified_structured_elements_gin ON court_data.opinions_unified USING GIN(structured_elements);

-- Full text search index
CREATE INDEX idx_opinions_unified_text_search ON court_data.opinions_unified 
    USING GIN(to_tsvector('english', COALESCE(plain_text, '') || ' ' || COALESCE(case_name, '')));

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_opinions_unified_updated_at 
    BEFORE UPDATE ON court_data.opinions_unified 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for easy querying
CREATE OR REPLACE VIEW court_data.opinions_unified_enhanced AS
SELECT 
    o.*,
    -- Extract specific citation data
    jsonb_array_length(o.citations) as citation_count,
    o.citations->0->>'citation_string' as first_citation,
    -- Extract judge data
    o.judge_info->>'name_full' as judge_name,
    o.judge_info->>'political_affiliation' as judge_party,
    -- Extract court data  
    o.court_info->>'full_name' as court_full_name,
    o.court_info->>'jurisdiction' as court_jurisdiction,
    -- Extract unstructured data
    o.structured_elements->>'full_text' as unstructured_text,
    jsonb_array_length(o.structured_elements->'structured_elements') as element_count
FROM court_data.opinions_unified o;

-- Grant permissions (adjust as needed)
GRANT SELECT, INSERT, UPDATE ON court_data.opinions_unified TO your_app_user;
GRANT SELECT ON court_data.opinions_unified_enhanced TO your_app_user;
GRANT USAGE ON court_data.opinions_unified_id_seq TO your_app_user;