-- RECAP Document Support Schema
-- Extends CourtListener integration with RECAP documents and transcripts
-- Run this after init_courtlistener_schema.sql

-- RECAP Documents table (actual filed documents)
CREATE TABLE IF NOT EXISTS court_data.cl_recap_documents (
    id BIGINT PRIMARY KEY,  -- CourtListener document ID
    docket_entry_id BIGINT REFERENCES court_data.cl_docket_entries(id),
    docket_id BIGINT REFERENCES court_data.cl_dockets(id),
    
    -- Document identifiers
    document_number VARCHAR(50),
    attachment_number INTEGER,
    pacer_doc_id VARCHAR(100),
    
    -- Document metadata
    description TEXT,
    short_description TEXT,
    document_type VARCHAR(100),  -- e.g., 'motion', 'brief', 'transcript', 'order'
    
    -- File information
    page_count INTEGER,
    file_size BIGINT,
    filepath_local TEXT,
    filepath_ia TEXT,  -- Internet Archive path
    sha1 VARCHAR(40),
    
    -- Content
    plain_text TEXT,
    ocr_status VARCHAR(50),  -- 'complete', 'partial', 'failed', 'unnecessary'
    extracted_by_ocr BOOLEAN DEFAULT false,
    
    -- Transcript detection
    is_transcript BOOLEAN DEFAULT false,
    transcript_type VARCHAR(50),  -- 'hearing', 'deposition', 'trial', 'oral_argument'
    
    -- URLs
    download_url TEXT,
    absolute_url TEXT,
    thumbnail TEXT,
    
    -- Dates
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    date_upload TIMESTAMP,
    
    -- Processing flags
    vector_indexed BOOLEAN DEFAULT false,
    text_extracted BOOLEAN DEFAULT false,
    
    -- Raw data
    raw_data JSONB,
    
    -- Timestamps
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audio recordings table (oral arguments, hearings)
CREATE TABLE IF NOT EXISTS court_data.cl_audio (
    id BIGINT PRIMARY KEY,
    docket_id BIGINT REFERENCES court_data.cl_dockets(id),
    
    -- Audio metadata
    case_name TEXT,
    case_name_short TEXT,
    case_name_full TEXT,
    
    -- Court information
    court_id VARCHAR(50),
    
    -- Audio details
    duration INTEGER,  -- in seconds
    judges TEXT,
    sha1 VARCHAR(40),
    
    -- File information
    download_url TEXT,
    local_path_mp3 TEXT,
    local_path_original TEXT,
    filepath_ia TEXT,
    
    -- Processing
    processing_complete BOOLEAN DEFAULT false,
    date_blocked DATE,
    blocked BOOLEAN DEFAULT false,
    
    -- Dates
    date_created TIMESTAMP,
    date_modified TIMESTAMP,
    
    -- Transcript reference
    has_transcript BOOLEAN DEFAULT false,
    transcript_document_id BIGINT REFERENCES court_data.cl_recap_documents(id),
    
    -- Raw data
    raw_data JSONB,
    
    -- Timestamps
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Enhanced docket entries to link with RECAP documents
ALTER TABLE court_data.cl_docket_entries 
ADD COLUMN IF NOT EXISTS has_recap_documents BOOLEAN DEFAULT false,
ADD COLUMN IF NOT EXISTS recap_document_count INTEGER DEFAULT 0;

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_docket ON court_data.cl_recap_documents(docket_id);
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_entry ON court_data.cl_recap_documents(docket_entry_id);
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_type ON court_data.cl_recap_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_transcript ON court_data.cl_recap_documents(is_transcript) 
    WHERE is_transcript = true;
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_vector ON court_data.cl_recap_documents(vector_indexed) 
    WHERE vector_indexed = false;
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_date ON court_data.cl_recap_documents(date_created DESC);

CREATE INDEX IF NOT EXISTS idx_cl_audio_docket ON court_data.cl_audio(docket_id);
CREATE INDEX IF NOT EXISTS idx_cl_audio_court ON court_data.cl_audio(court_id);
CREATE INDEX IF NOT EXISTS idx_cl_audio_transcript ON court_data.cl_audio(has_transcript);

-- Full text search on RECAP documents
CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_description_gin 
ON court_data.cl_recap_documents 
USING gin(to_tsvector('english', description));

CREATE INDEX IF NOT EXISTS idx_cl_recap_docs_text_gin 
ON court_data.cl_recap_documents 
USING gin(to_tsvector('english', plain_text))
WHERE plain_text IS NOT NULL;

-- Update triggers for new tables
CREATE TRIGGER update_cl_recap_docs_updated_at BEFORE UPDATE ON court_data.cl_recap_documents
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

CREATE TRIGGER update_cl_audio_updated_at BEFORE UPDATE ON court_data.cl_audio
    FOR EACH ROW EXECUTE FUNCTION court_data.update_updated_at_column();

-- View for transcript documents
CREATE OR REPLACE VIEW court_data.transcript_documents AS
SELECT 
    d.id,
    d.docket_id,
    d.description,
    d.document_type,
    d.transcript_type,
    d.page_count,
    d.plain_text,
    d.date_created,
    dk.case_name,
    dk.court_id,
    dk.docket_number,
    LENGTH(d.plain_text) as text_length,
    d.vector_indexed
FROM court_data.cl_recap_documents d
JOIN court_data.cl_dockets dk ON d.docket_id = dk.id
WHERE d.is_transcript = true
AND d.plain_text IS NOT NULL;

-- Statistics view for RECAP data
CREATE OR REPLACE VIEW court_data.recap_stats AS
SELECT 
    COUNT(DISTINCT d.id) as total_documents,
    COUNT(DISTINCT d.id) FILTER (WHERE d.is_transcript) as transcript_count,
    COUNT(DISTINCT d.id) FILTER (WHERE d.plain_text IS NOT NULL) as documents_with_text,
    COUNT(DISTINCT d.id) FILTER (WHERE d.vector_indexed = false AND d.plain_text IS NOT NULL) as pending_index,
    COUNT(DISTINCT a.id) as audio_recordings,
    COUNT(DISTINCT a.id) FILTER (WHERE a.has_transcript) as audio_with_transcript,
    SUM(d.page_count) as total_pages,
    pg_size_pretty(SUM(d.file_size)::bigint) as total_file_size
FROM court_data.cl_recap_documents d
FULL OUTER JOIN court_data.cl_audio a ON true;

-- Function to detect transcript documents
CREATE OR REPLACE FUNCTION court_data.detect_transcript_type(
    p_description TEXT,
    p_document_type TEXT
) RETURNS VARCHAR AS $$
DECLARE
    v_description_lower TEXT;
    v_transcript_type VARCHAR(50);
BEGIN
    v_description_lower := LOWER(COALESCE(p_description, ''));
    
    -- Detect specific transcript types
    IF v_description_lower ~ 'deposition' THEN
        v_transcript_type := 'deposition';
    ELSIF v_description_lower ~ 'trial\s+transcript' THEN
        v_transcript_type := 'trial';
    ELSIF v_description_lower ~ 'hearing\s+transcript' OR v_description_lower ~ 'motion\s+hearing' THEN
        v_transcript_type := 'hearing';
    ELSIF v_description_lower ~ 'oral\s+argument' THEN
        v_transcript_type := 'oral_argument';
    ELSIF v_description_lower ~ 'sentencing' THEN
        v_transcript_type := 'sentencing';
    ELSIF v_description_lower ~ 'status\s+conference' THEN
        v_transcript_type := 'status_conference';
    ELSIF v_description_lower ~ 'transcript' THEN
        v_transcript_type := 'other';
    ELSE
        v_transcript_type := NULL;
    END IF;
    
    RETURN v_transcript_type;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Function to check if document is transcript
CREATE OR REPLACE FUNCTION court_data.is_transcript_document(
    p_description TEXT,
    p_document_type TEXT
) RETURNS BOOLEAN AS $$
BEGIN
    RETURN court_data.detect_transcript_type(p_description, p_document_type) IS NOT NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Grant permissions (uncomment and adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA court_data TO your_app_user;
-- GRANT ALL ON ALL FUNCTIONS IN SCHEMA court_data TO your_app_user;