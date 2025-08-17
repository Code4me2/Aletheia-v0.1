-- Database schema for Citation Generation node
-- This schema supports a fixed 3-level hierarchical structure:
-- Level 0: Source documents (original content)
-- Level 1: First level summaries (batches/chunks)
-- Level 2: Final summary with citations

-- Create the main hierarchical documents table
CREATE TABLE IF NOT EXISTS hierarchical_documents (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    summary TEXT,
    batch_id VARCHAR(255) NOT NULL,
    hierarchy_level INTEGER NOT NULL CHECK (hierarchy_level >= 0 AND hierarchy_level <= 2), -- Enforces 3-level structure (0, 1, 2)
    parent_id INTEGER REFERENCES hierarchical_documents(id),
    child_ids INTEGER[] DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    -- New fields for better traceability
    document_type VARCHAR(20) DEFAULT 'source', -- 'source', 'chunk', 'batch', 'summary'
    chunk_index INTEGER,
    source_document_ids INTEGER[] DEFAULT '{}',
    token_count INTEGER DEFAULT 0
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_hierarchical_docs_batch_id ON hierarchical_documents(batch_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_docs_level ON hierarchical_documents(hierarchy_level);
CREATE INDEX IF NOT EXISTS idx_hierarchical_docs_parent ON hierarchical_documents(parent_id);
CREATE INDEX IF NOT EXISTS idx_hierarchical_docs_type ON hierarchical_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_hierarchical_docs_batch_level ON hierarchical_documents(batch_id, hierarchy_level);

-- Create processing status table
CREATE TABLE IF NOT EXISTS processing_status (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(255) UNIQUE NOT NULL,
    total_documents INTEGER NOT NULL,
    current_level INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'processing',
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index on batch_id for status lookups
CREATE INDEX IF NOT EXISTS idx_processing_status_batch ON processing_status(batch_id);

-- Add new columns if they don't exist (for existing databases)
DO $$ 
BEGIN
    -- Add document_type column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'hierarchical_documents' 
                   AND column_name = 'document_type') THEN
        ALTER TABLE hierarchical_documents 
        ADD COLUMN document_type VARCHAR(20) DEFAULT 'source';
    END IF;
    
    -- Add chunk_index column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'hierarchical_documents' 
                   AND column_name = 'chunk_index') THEN
        ALTER TABLE hierarchical_documents 
        ADD COLUMN chunk_index INTEGER;
    END IF;
    
    -- Add source_document_ids column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'hierarchical_documents' 
                   AND column_name = 'source_document_ids') THEN
        ALTER TABLE hierarchical_documents 
        ADD COLUMN source_document_ids INTEGER[] DEFAULT '{}';
    END IF;
    
    -- Add token_count column if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'hierarchical_documents' 
                   AND column_name = 'token_count') THEN
        ALTER TABLE hierarchical_documents 
        ADD COLUMN token_count INTEGER DEFAULT 0;
    END IF;
END $$;

-- Example queries to understand the hierarchy:

-- Get all documents for a batch organized by level
-- SELECT hierarchy_level, document_type, COUNT(*) as doc_count, 
--        SUM(token_count) as total_tokens
-- FROM hierarchical_documents 
-- WHERE batch_id = 'your-batch-id'
-- GROUP BY hierarchy_level, document_type
-- ORDER BY hierarchy_level;

-- Get the document tree for a batch
-- WITH RECURSIVE doc_tree AS (
--     -- Start with the final summary (highest level)
--     SELECT * FROM hierarchical_documents 
--     WHERE batch_id = 'your-batch-id' 
--     AND hierarchy_level = (
--         SELECT MAX(hierarchy_level) FROM hierarchical_documents 
--         WHERE batch_id = 'your-batch-id'
--     )
--     
--     UNION ALL
--     
--     -- Recursively get all parent documents
--     SELECT hd.* FROM hierarchical_documents hd
--     INNER JOIN doc_tree dt ON hd.id = ANY(dt.source_document_ids) OR hd.id = dt.parent_id
-- )
-- SELECT * FROM doc_tree ORDER BY hierarchy_level DESC, id;