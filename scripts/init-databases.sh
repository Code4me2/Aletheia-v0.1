#!/bin/bash
set -e

# This script is run by PostgreSQL during initialization
echo "Starting database initialization..."

# Create service-specific databases
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create lawyerchat database for the lawyer-chat service
    CREATE DATABASE lawyerchat;
    GRANT ALL PRIVILEGES ON DATABASE lawyerchat TO $POSTGRES_USER;
    
    -- Switch to main database for table creation
    \connect $POSTGRES_DB;
    
    -- Create tables for hierarchical summarization
    CREATE TABLE IF NOT EXISTS hierarchical_summaries (
        id SERIAL PRIMARY KEY,
        workflow_id VARCHAR(255) NOT NULL,
        level INTEGER NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB,
        parent_id INTEGER REFERENCES hierarchical_summaries(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for better performance
    CREATE INDEX idx_workflow_id ON hierarchical_summaries(workflow_id);
    CREATE INDEX idx_level ON hierarchical_summaries(level);
    CREATE INDEX idx_parent_id ON hierarchical_summaries(parent_id);
    CREATE INDEX idx_created_at ON hierarchical_summaries(created_at);
    
    -- Create table for document processing status
    CREATE TABLE IF NOT EXISTS document_processing_status (
        id SERIAL PRIMARY KEY,
        workflow_id VARCHAR(255) NOT NULL UNIQUE,
        status VARCHAR(50) NOT NULL DEFAULT 'pending',
        total_documents INTEGER DEFAULT 0,
        processed_documents INTEGER DEFAULT 0,
        error_message TEXT,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        metadata JSONB
    );
    
    -- Create index for status queries
    CREATE INDEX idx_processing_status ON document_processing_status(status);
    CREATE INDEX idx_processing_workflow ON document_processing_status(workflow_id);
    
    -- Create table for court processor documents
    CREATE TABLE IF NOT EXISTS court_documents (
        id SERIAL PRIMARY KEY,
        case_number VARCHAR(255),
        document_type VARCHAR(100),
        file_path TEXT,
        content TEXT,
        metadata JSONB,
        processed BOOLEAN DEFAULT false,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for court documents
    CREATE INDEX idx_case_number ON court_documents(case_number);
    CREATE INDEX idx_document_type ON court_documents(document_type);
    CREATE INDEX idx_processed ON court_documents(processed);
    
    -- Create update trigger for updated_at columns
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS \$\$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        RETURN NEW;
    END;
    \$\$ language 'plpgsql';
    
    CREATE TRIGGER update_hierarchical_summaries_updated_at
        BEFORE UPDATE ON hierarchical_summaries
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    CREATE TRIGGER update_court_documents_updated_at
        BEFORE UPDATE ON court_documents
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    
    -- Grant permissions to ensure n8n can access tables
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
    
    -- Create a view for hierarchical summary statistics
    CREATE OR REPLACE VIEW workflow_summary_stats AS
    SELECT 
        workflow_id,
        COUNT(*) as total_summaries,
        COUNT(DISTINCT level) as total_levels,
        MAX(level) as max_level,
        MIN(created_at) as first_created,
        MAX(created_at) as last_created,
        SUM(LENGTH(content)) as total_content_size
    FROM hierarchical_summaries
    GROUP BY workflow_id;
    
    -- Switch to lawyerchat database
    \connect lawyerchat;
    
    -- Create tables for lawyer-chat application
    CREATE TABLE IF NOT EXISTS conversations (
        id SERIAL PRIMARY KEY,
        user_id VARCHAR(255),
        title VARCHAR(500),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        conversation_id INTEGER REFERENCES conversations(id) ON DELETE CASCADE,
        role VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Create indexes for lawyer-chat
    CREATE INDEX idx_user_conversations ON conversations(user_id);
    CREATE INDEX idx_conversation_messages ON messages(conversation_id);
    CREATE INDEX idx_message_created ON messages(created_at);
    
    -- Grant permissions
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO $POSTGRES_USER;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO $POSTGRES_USER;
    
EOSQL

echo "Database initialization complete!"