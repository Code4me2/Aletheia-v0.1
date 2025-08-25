-- CourtListener Integration Schema
-- Extends the existing court_data schema with CourtListener-specific tables
-- Designed to work alongside existing juriscraper opinions table

-- Ensure schema exists
CREATE SCHEMA IF NOT EXISTS court_data;

-- CourtListener Dockets table (main case information)
CREATE TABLE IF NOT EXISTS court_data.cl_dockets (
    id BIGINT PRIMARY KEY,  -- CourtListener docket ID
    court_id VARCHAR(50) NOT NULL,
    case_name TEXT,
    case_name_short TEXT,
    case_name_full TEXT,
    docket_number VARCHAR(255),
    docket_number_core VARCHAR(100),
    
    -- Dates
    date_filed DATE,
    date_terminated DATE,
    date_last_filing DATE,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    
    -- Case details
    nature_of_suit VARCHAR(100),
    cause TEXT,
    jury_demand VARCHAR(50),
    jurisdiction_type VARCHAR(50),
    
    -- Judge information
    assigned_to_str TEXT,
    referred_to_str TEXT,
    
    -- Source and metadata
    source INTEGER,
    pacer_case_id VARCHAR(100),
    filepath_ia TEXT,
    filepath_local TEXT,
    
    -- URLs
    absolute_url TEXT,
    docket_entries_url TEXT,
    
    -- Processing flags
    is_patent_case BOOLEAN DEFAULT false,
    vector_indexed BOOLEAN DEFAULT false,
    
    -- Raw data storage
    raw_data JSONB,
    
    -- Timestamps
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- CourtListener Opinions table (extends existing opinions with CL-specific data)
CREATE TABLE IF NOT EXISTS court_data.cl_opinions (
    id BIGINT PRIMARY KEY,  -- CourtListener opinion ID
    cluster_id BIGINT,
    docket_id BIGINT REFERENCES court_data.cl_dockets(id),
    
    -- Author information
    author_str TEXT,
    author_id INTEGER,
    per_curiam BOOLEAN DEFAULT false,
    joined_by_str TEXT,
    
    -- Opinion details
    type VARCHAR(50),
    sha1 VARCHAR(40),
    page_count INTEGER,
    
    -- Text content (multiple formats)
    plain_text TEXT,
    html TEXT,
    html_lawbox TEXT,
    html_columbia TEXT,
    html_anon_2020 TEXT,
    html_with_citations TEXT,
    xml_harvard TEXT,
    
    -- URLs and paths
    download_url TEXT,
    local_path TEXT,
    absolute_url TEXT,
    
    -- Citations
    opinions_cited JSONB,
    
    -- Metadata
    extracted_by_ocr BOOLEAN DEFAULT false,
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    
    -- Processing flags
    vector_indexed BOOLEAN DEFAULT false,
    
    -- Raw data
    raw_data JSONB,
    
    -- Timestamps
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Opinion Clusters table (groups related opinions)
CREATE TABLE IF NOT EXISTS court_data.cl_clusters (
    id BIGINT PRIMARY KEY,
    docket_id BIGINT REFERENCES court_data.cl_dockets(id),
    
    -- Cluster metadata
    judges TEXT,
    date_filed DATE,
    date_filed_is_approximate BOOLEAN DEFAULT false,
    
    -- Citation information
    slug TEXT,
    citation_count INTEGER DEFAULT 0,
    
    -- URLs
    absolute_url TEXT,
    
    -- Timestamps
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    
    -- Raw data
    raw_data JSONB,
    
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Docket Entries table (individual filings in a case)
CREATE TABLE IF NOT EXISTS court_data.cl_docket_entries (
    id BIGINT PRIMARY KEY,
    docket_id BIGINT REFERENCES court_data.cl_dockets(id),
    
    -- Entry details
    date_filed DATE,
    entry_number INTEGER,
    recap_sequence_number VARCHAR(50),
    pacer_sequence_number INTEGER,
    
    -- Descriptions
    description TEXT,
    short_description TEXT,
    
    -- Document count
    document_count INTEGER DEFAULT 0,
    
    -- Raw data
    raw_data JSONB,
    
    -- Timestamps
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_cl_dockets_court ON court_data.cl_dockets(court_id);
CREATE INDEX IF NOT EXISTS idx_cl_dockets_date_filed ON court_data.cl_dockets(date_filed DESC);
CREATE INDEX IF NOT EXISTS idx_cl_dockets_docket_number ON court_data.cl_dockets(docket_number);
CREATE INDEX IF NOT EXISTS idx_cl_dockets_patent ON court_data.cl_dockets(is_patent_case) WHERE is_patent_case = true;
CREATE INDEX IF NOT EXISTS idx_cl_dockets_vector ON court_data.cl_dockets(vector_indexed) WHERE vector_indexed = false;

CREATE INDEX IF NOT EXISTS idx_cl_opinions_cluster ON court_data.cl_opinions(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cl_opinions_docket ON court_data.cl_opinions(docket_id);
CREATE INDEX IF NOT EXISTS idx_cl_opinions_author ON court_data.cl_opinions(author_str);
CREATE INDEX IF NOT EXISTS idx_cl_opinions_type ON court_data.cl_opinions(type);
CREATE INDEX IF NOT EXISTS idx_cl_opinions_vector ON court_data.cl_opinions(vector_indexed) WHERE vector_indexed = false;

-- Full text search indexes
CREATE INDEX IF NOT EXISTS idx_cl_dockets_case_name_gin 
ON court_data.cl_dockets 
USING gin(to_tsvector('english', case_name));

CREATE INDEX IF NOT EXISTS idx_cl_opinions_text_gin 
ON court_data.cl_opinions 
USING gin(to_tsvector('english', plain_text))
WHERE plain_text IS NOT NULL;

-- Create update function if it doesn't exist (might already exist from init_db.sql)
CREATE OR REPLACE FUNCTION court_data.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create update triggers
CREATE TRIGGER update_cl_dockets_updated_at BEFORE UPDATE ON court_data.cl_dockets
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

CREATE TRIGGER update_cl_opinions_updated_at BEFORE UPDATE ON court_data.cl_opinions
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

CREATE TRIGGER update_cl_clusters_updated_at BEFORE UPDATE ON court_data.cl_clusters
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

CREATE TRIGGER update_cl_entries_updated_at BEFORE UPDATE ON court_data.cl_docket_entries
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

-- View to combine CourtListener opinions with existing opinions for unified access
CREATE OR REPLACE VIEW court_data.all_opinions AS
SELECT 
    'juriscraper' as source,
    o.id,
    o.judge_id,
    NULL::BIGINT as docket_id,
    o.case_name,
    o.case_date,
    o.docket_number,
    o.court_code,
    o.text_content,
    o.metadata,
    o.vector_indexed,
    o.created_at
FROM court_data.opinions o
UNION ALL
SELECT 
    'courtlistener' as source,
    cl_o.id,
    NULL::INTEGER as judge_id,
    cl_o.docket_id,
    d.case_name,
    cl_o.date_created::date as case_date,
    d.docket_number,
    d.court_id as court_code,
    COALESCE(cl_o.plain_text, cl_o.html) as text_content,
    cl_o.raw_data as metadata,
    cl_o.vector_indexed,
    cl_o.imported_at as created_at
FROM court_data.cl_opinions cl_o
LEFT JOIN court_data.cl_dockets d ON cl_o.docket_id = d.id
WHERE cl_o.plain_text IS NOT NULL OR cl_o.html IS NOT NULL;

-- Statistics view for monitoring
CREATE OR REPLACE VIEW court_data.cl_import_stats AS
SELECT 
    court_id,
    COUNT(DISTINCT d.id) as docket_count,
    COUNT(DISTINCT o.id) as opinion_count,
    COUNT(DISTINCT d.id) FILTER (WHERE d.is_patent_case) as patent_case_count,
    COUNT(DISTINCT o.id) FILTER (WHERE o.vector_indexed = false) as opinions_pending_index,
    MIN(d.date_filed) as earliest_case,
    MAX(d.date_filed) as latest_case,
    MAX(d.imported_at) as last_import
FROM court_data.cl_dockets d
LEFT JOIN court_data.cl_opinions o ON d.id = o.docket_id
GROUP BY court_id;

-- Helper function to detect patent cases
CREATE OR REPLACE FUNCTION court_data.is_patent_case(
    p_nature_of_suit VARCHAR(100),
    p_case_name TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    -- Check nature of suit codes
    IF p_nature_of_suit IN ('830', '835', '840') THEN
        RETURN true;
    END IF;
    
    -- Check case name for patent keywords
    IF p_case_name IS NOT NULL AND 
       p_case_name ~* 'patent|infringement|35 u\.s\.c\.|271|284' THEN
        RETURN true;
    END IF;
    
    RETURN false;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Grant permissions (uncomment and adjust as needed)
-- GRANT USAGE ON SCHEMA court_data TO your_app_user;
-- GRANT ALL ON ALL TABLES IN SCHEMA court_data TO your_app_user;
-- GRANT ALL ON ALL SEQUENCES IN SCHEMA court_data TO your_app_user;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA court_data TO your_app_user;