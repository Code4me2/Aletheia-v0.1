-- Active Court Processor Database Schema
-- This is the ONLY schema currently in use by the court-processor service
-- Table: public.court_documents
-- Last verified: August 2025

-- Main documents table used by both API and CLI
CREATE TABLE IF NOT EXISTS public.court_documents (
    id SERIAL PRIMARY KEY,
    case_number VARCHAR(255),           -- Case identifier (e.g., "2:17-CV-00141-JRG")
    document_type VARCHAR(100),          -- Type: 'opinion', '020lead', 'opinion_doctor', 'docket'
    file_path TEXT,                      -- Path to original file (if applicable)
    content TEXT,                        -- Full document content (HTML/XML format)
    metadata JSONB,                      -- Flexible metadata storage
    processed BOOLEAN DEFAULT FALSE,     -- Processing status flag
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    case_name VARCHAR(500)               -- Human-readable case name
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_case_number ON public.court_documents(case_number);
CREATE INDEX IF NOT EXISTS idx_document_type ON public.court_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_processed ON public.court_documents(processed);
CREATE INDEX IF NOT EXISTS idx_court_docs_metadata ON public.court_documents USING gin(metadata);

-- Update trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_court_documents_updated_at 
    BEFORE UPDATE ON public.court_documents 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Document Types Reference
-- 'opinion'        - Generic court opinion
-- '020lead'        - CourtListener lead opinion (main opinion of the court)
-- 'opinion_doctor' - Enhanced/processed opinion
-- 'docket'         - Docket entry
-- '010combined'    - (archived) Combined opinion
-- '030concurrence' - (archived) Concurring opinion  
-- '040dissent'     - (archived) Dissenting opinion

-- Metadata JSON Structure (typical fields)
-- {
--   "judge_name": "Rodney Gilstrap",
--   "court_id": "txed",
--   "date_filed": "2019-06-14",
--   "cl_opinion_id": "1967",
--   "cl_cluster_id": 7336453,
--   "citations": ["767 F.3d 1308", "664 F.3d 467"],
--   "source": "courtlistener_standalone",
--   "type": "020lead"
-- }

-- Current Statistics (as of August 2025)
-- Total documents: 485
-- Document types: opinion (273), 020lead (210), opinion_doctor (2)
-- Top courts: txed (72), ded (44), mdd (16)
-- Date range: 1996-05-02 to 2025-07-22