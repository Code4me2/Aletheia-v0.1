-- FLP Supplemental Enhancement Tables
-- These tables support the Free Law Project integration without conflicting with existing data
-- Run this after init_db.sql and any CourtListener schemas

-- Court standardization mapping (Courts-DB cache)
CREATE TABLE IF NOT EXISTS court_data.court_standardization (
    original_code VARCHAR(50) PRIMARY KEY,
    flp_court_id VARCHAR(50),
    court_name TEXT,
    confidence VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for lookups
CREATE INDEX IF NOT EXISTS idx_court_std_flp_id ON court_data.court_standardization(flp_court_id);

-- Citation normalization cache (Reporters-DB)
CREATE TABLE IF NOT EXISTS court_data.citation_normalization (
    original TEXT PRIMARY KEY,
    normalized TEXT NOT NULL,
    reporter_full_name TEXT,
    reporter_metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for normalized lookups
CREATE INDEX IF NOT EXISTS idx_citation_norm_normalized ON court_data.citation_normalization(normalized);

-- Bad redaction findings (X-Ray results)
CREATE TABLE IF NOT EXISTS court_data.redaction_issues (
    document_id BIGINT,
    document_type VARCHAR(50), -- 'opinion' or 'recap_document'
    has_bad_redactions BOOLEAN,
    redaction_details JSONB,
    checked_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (document_id, document_type)
);

-- Create indexes for redaction queries
CREATE INDEX IF NOT EXISTS idx_redaction_issues_type ON court_data.redaction_issues(document_type);
CREATE INDEX IF NOT EXISTS idx_redaction_issues_bad ON court_data.redaction_issues(has_bad_redactions) 
    WHERE has_bad_redactions = true;

-- Extend judges table for Judge-pics integration
ALTER TABLE court_data.judges 
ADD COLUMN IF NOT EXISTS photo_url TEXT,
ADD COLUMN IF NOT EXISTS judge_pics_id INTEGER,
ADD COLUMN IF NOT EXISTS flp_metadata JSONB;

-- Create index for judges with photos
CREATE INDEX IF NOT EXISTS idx_judges_photo ON court_data.judges(photo_url) 
    WHERE photo_url IS NOT NULL;

-- Enhancement tracking view
CREATE OR REPLACE VIEW court_data.flp_enhancement_status AS
WITH juriscraper_stats AS (
    SELECT 
        'juriscraper' as source,
        COUNT(*) as total_opinions,
        COUNT(*) FILTER (WHERE metadata->>'flp_supplemental' IS NOT NULL) as enhanced,
        COUNT(*) FILTER (WHERE text_content IS NULL) as missing_text,
        COUNT(*) FILTER (WHERE text_content IS NOT NULL AND metadata->>'flp_supplemental' IS NULL) as ready_to_enhance
    FROM court_data.opinions
),
courtlistener_stats AS (
    SELECT 
        'courtlistener' as source,
        COUNT(*) as total_opinions,
        COUNT(*) FILTER (WHERE metadata->>'flp_supplemental' IS NOT NULL) as enhanced,
        COUNT(*) FILTER (WHERE plain_text IS NULL) as missing_text,
        COUNT(*) FILTER (WHERE plain_text IS NOT NULL AND metadata->>'flp_supplemental' IS NULL) as ready_to_enhance
    FROM court_data.cl_opinions
)
SELECT * FROM juriscraper_stats
UNION ALL
SELECT * FROM courtlistener_stats;

-- Grant permissions (uncomment and adjust as needed)
-- GRANT ALL ON ALL TABLES IN SCHEMA court_data TO your_app_user;
-- GRANT USAGE ON SCHEMA court_data TO your_app_user;