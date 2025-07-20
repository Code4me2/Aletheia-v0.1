"""
Extracted database optimizations from scripts/init_db.sql
Provides optimized database schema and performance enhancements for court document processing
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)


class DatabaseOptimizer:
    """
    Database optimization utilities for court document processing
    
    Extracted from scripts/init_db.sql with enhancements for production use
    """
    
    def __init__(self, connection_config: Optional[Dict[str, str]] = None):
        """
        Initialize database optimizer
        
        Args:
            connection_config: Database connection parameters (optional, uses defaults)
        """
        self.connection_config = connection_config or {
            'host': 'db',
            'port': '5432',
            'user': 'aletheia',
            'password': 'aletheia123',
            'database': 'aletheia'
        }
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.connection_config)
    
    def create_optimized_schema(self, schema_name: str = 'court_data') -> bool:
        """
        Create optimized database schema for court documents
        
        Args:
            schema_name: Name of the schema to create
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                # Create schema
                logger.info(f"Creating schema: {schema_name}")
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
                
                # Create tables with optimizations
                self._create_judges_table(cursor, schema_name)
                self._create_opinions_table(cursor, schema_name)
                self._create_processing_log_table(cursor, schema_name)
                
                # Create indexes
                self._create_performance_indexes(cursor, schema_name)
                
                # Create functions and triggers
                self._create_helper_functions(cursor, schema_name)
                self._create_triggers(cursor, schema_name)
                
                # Create views
                self._create_statistics_views(cursor, schema_name)
                
            conn.close()
            logger.info("Optimized schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create optimized schema: {e}")
            return False
    
    def _create_judges_table(self, cursor, schema_name: str):
        """Create optimized judges table"""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.judges (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL UNIQUE,
                court VARCHAR(100),
                photo_url TEXT,
                judge_pics_id INTEGER,
                metadata JSONB DEFAULT '{{}}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Judges table indexes
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_judges_name 
            ON {schema_name}.judges(name)
        """)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_judges_court 
            ON {schema_name}.judges(court)
        """)
        
        # GIN index for metadata JSONB
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_judges_metadata_gin 
            ON {schema_name}.judges USING gin(metadata)
        """)
        
        logger.debug("Judges table created with optimizations")
    
    def _create_opinions_table(self, cursor, schema_name: str):
        """Create optimized opinions table"""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.opinions (
                id SERIAL PRIMARY KEY,
                judge_id INTEGER REFERENCES {schema_name}.judges(id),
                case_name TEXT,
                case_date DATE NOT NULL,
                docket_number VARCHAR(100),
                court_code VARCHAR(50),
                
                -- Content storage
                pdf_url TEXT,
                pdf_path VARCHAR(500),
                text_content TEXT NOT NULL,
                
                -- Metadata storage
                metadata JSONB DEFAULT '{{}}',
                pdf_metadata JSONB DEFAULT '{{}}',
                
                -- Processing status
                processing_status VARCHAR(50) DEFAULT 'completed',
                processing_error TEXT,
                
                -- Integration flags
                vector_indexed BOOLEAN DEFAULT false,
                haystack_ingested BOOLEAN DEFAULT false,
                flp_enhanced BOOLEAN DEFAULT false,
                hierarchical_doc_id INTEGER,
                
                -- Timestamps
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Deduplication
                document_hash VARCHAR(64),
                
                -- Constraints
                CONSTRAINT unique_opinion UNIQUE (court_code, docket_number, case_date),
                CONSTRAINT unique_document_hash UNIQUE (document_hash)
            )
        """)
        
        logger.debug("Opinions table created with optimizations")
    
    def _create_processing_log_table(self, cursor, schema_name: str):
        """Create processing log table for monitoring"""
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {schema_name}.processing_log (
                id SERIAL PRIMARY KEY,
                court_code VARCHAR(50),
                run_date DATE,
                process_type VARCHAR(50),
                opinions_found INTEGER DEFAULT 0,
                opinions_processed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                error_details JSONB DEFAULT '{{}}',
                performance_metrics JSONB DEFAULT '{{}}',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                status VARCHAR(50) DEFAULT 'running'
            )
        """)
        
        # Processing log indexes
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_processing_log_date 
            ON {schema_name}.processing_log(run_date DESC)
        """)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_processing_log_court_date 
            ON {schema_name}.processing_log(court_code, run_date DESC)
        """)
        
        logger.debug("Processing log table created")
    
    def _create_performance_indexes(self, cursor, schema_name: str):
        """Create performance-optimized indexes"""
        
        # Composite index for judge-based date queries (most common pattern)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_judge_date 
            ON {schema_name}.opinions(judge_id, case_date DESC)
        """)
        
        # Date-based queries
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_date 
            ON {schema_name}.opinions(case_date DESC)
        """)
        
        # Court-based queries
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_court 
            ON {schema_name}.opinions(court_code)
        """)
        
        # Docket number queries
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_docket 
            ON {schema_name}.opinions(docket_number)
        """)
        
        # Partial index for unprocessed documents (very efficient for batch processing)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_vector_unprocessed 
            ON {schema_name}.opinions(id) 
            WHERE vector_indexed = false
        """)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_haystack_unprocessed 
            ON {schema_name}.opinions(id) 
            WHERE haystack_ingested = false
        """)
        
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_flp_unprocessed 
            ON {schema_name}.opinions(id) 
            WHERE flp_enhanced = false
        """)
        
        # Full-text search index on content
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_text_search 
            ON {schema_name}.opinions 
            USING gin(to_tsvector('english', text_content))
        """)
        
        # GIN indexes for JSONB metadata queries
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_metadata_gin 
            ON {schema_name}.opinions USING gin(metadata)
        """)
        
        # Hash index for deduplication
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_document_hash 
            ON {schema_name}.opinions(document_hash)
        """)
        
        # Composite index for judge name queries (through metadata)
        cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_opinions_judge_name_performance 
            ON {schema_name}.opinions USING gin((metadata->>'judge_name')) 
            WHERE metadata->>'judge_name' IS NOT NULL
        """)
        
        logger.info("Performance indexes created")
    
    def _create_helper_functions(self, cursor, schema_name: str):
        """Create helper functions for database operations"""
        
        # Update timestamp function
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {schema_name}.update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        # Get or create judge function
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {schema_name}.get_or_create_judge(
                p_judge_name VARCHAR(255),
                p_court VARCHAR(100)
            ) RETURNS INTEGER AS $$
            DECLARE
                v_judge_id INTEGER;
            BEGIN
                -- Try to find existing judge
                SELECT id INTO v_judge_id
                FROM {schema_name}.judges
                WHERE name = p_judge_name;
                
                -- If not found, create new judge
                IF v_judge_id IS NULL THEN
                    INSERT INTO {schema_name}.judges (name, court)
                    VALUES (p_judge_name, p_court)
                    ON CONFLICT (name) DO UPDATE SET 
                        court = EXCLUDED.court,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id INTO v_judge_id;
                END IF;
                
                RETURN v_judge_id;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Batch update processing status function
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {schema_name}.update_processing_status(
                p_ids INTEGER[],
                p_status_field VARCHAR(50),
                p_status_value BOOLEAN
            ) RETURNS INTEGER AS $$
            DECLARE
                v_updated_count INTEGER;
            BEGIN
                EXECUTE format('UPDATE {schema_name}.opinions SET %I = $1, updated_at = CURRENT_TIMESTAMP WHERE id = ANY($2)', p_status_field)
                USING p_status_value, p_ids;
                
                GET DIAGNOSTICS v_updated_count = ROW_COUNT;
                RETURN v_updated_count;
            END;
            $$ LANGUAGE plpgsql
        """)
        
        # Document hash generation function
        cursor.execute(f"""
            CREATE OR REPLACE FUNCTION {schema_name}.generate_document_hash(
                p_case_name TEXT,
                p_court_code VARCHAR(50),
                p_case_date DATE
            ) RETURNS VARCHAR(64) AS $$
            BEGIN
                RETURN encode(sha256((p_case_name || p_court_code || p_case_date::text)::bytea), 'hex');
            END;
            $$ LANGUAGE plpgsql
        """)
        
        logger.debug("Helper functions created")
    
    def _create_triggers(self, cursor, schema_name: str):
        """Create triggers for automatic timestamp updates"""
        
        cursor.execute(f"""
            CREATE TRIGGER update_judges_updated_at 
            BEFORE UPDATE ON {schema_name}.judges
            FOR EACH ROW EXECUTE FUNCTION {schema_name}.update_updated_at_column()
        """)
        
        cursor.execute(f"""
            CREATE TRIGGER update_opinions_updated_at 
            BEFORE UPDATE ON {schema_name}.opinions
            FOR EACH ROW EXECUTE FUNCTION {schema_name}.update_updated_at_column()
        """)
        
        logger.debug("Triggers created")
    
    def _create_statistics_views(self, cursor, schema_name: str):
        """Create views for statistics and monitoring"""
        
        # Judge statistics view
        cursor.execute(f"""
            CREATE OR REPLACE VIEW {schema_name}.judge_stats AS
            SELECT 
                j.id,
                j.name,
                j.court,
                COUNT(o.id) as opinion_count,
                MIN(o.case_date) as earliest_opinion,
                MAX(o.case_date) as latest_opinion,
                COUNT(o.id) FILTER (WHERE o.vector_indexed = false) as pending_vector_indexing,
                COUNT(o.id) FILTER (WHERE o.haystack_ingested = false) as pending_haystack_ingestion,
                COUNT(o.id) FILTER (WHERE o.flp_enhanced = false) as pending_flp_enhancement,
                AVG(LENGTH(o.text_content)) as avg_content_length,
                SUM(LENGTH(o.text_content)) as total_content_length
            FROM {schema_name}.judges j
            LEFT JOIN {schema_name}.opinions o ON j.id = o.judge_id
            GROUP BY j.id, j.name, j.court
        """)
        
        # Processing status view
        cursor.execute(f"""
            CREATE OR REPLACE VIEW {schema_name}.processing_status AS
            SELECT 
                court_code,
                COUNT(*) as total_opinions,
                COUNT(*) FILTER (WHERE vector_indexed = true) as vector_indexed_count,
                COUNT(*) FILTER (WHERE haystack_ingested = true) as haystack_ingested_count,
                COUNT(*) FILTER (WHERE flp_enhanced = true) as flp_enhanced_count,
                MIN(case_date) as earliest_case_date,
                MAX(case_date) as latest_case_date,
                MAX(updated_at) as last_updated
            FROM {schema_name}.opinions
            GROUP BY court_code
        """)
        
        # System performance view
        cursor.execute(f"""
            CREATE OR REPLACE VIEW {schema_name}.system_performance AS
            SELECT 
                'opinions' as table_name,
                COUNT(*) as total_records,
                pg_size_pretty(pg_total_relation_size('{schema_name}.opinions')) as table_size,
                pg_size_pretty(pg_indexes_size('{schema_name}.opinions')) as indexes_size,
                (SELECT COUNT(*) FROM {schema_name}.opinions WHERE updated_at > CURRENT_DATE - INTERVAL '1 day') as records_updated_today
            UNION ALL
            SELECT 
                'judges' as table_name,
                COUNT(*) as total_records,
                pg_size_pretty(pg_total_relation_size('{schema_name}.judges')) as table_size,
                pg_size_pretty(pg_indexes_size('{schema_name}.judges')) as indexes_size,
                (SELECT COUNT(*) FROM {schema_name}.judges WHERE updated_at > CURRENT_DATE - INTERVAL '1 day') as records_updated_today
        """)
        
        logger.debug("Statistics views created")
    
    def analyze_performance(self, schema_name: str = 'court_data') -> Dict[str, Any]:
        """
        Analyze database performance and suggest optimizations
        
        Args:
            schema_name: Schema to analyze
            
        Returns:
            Performance analysis results
        """
        try:
            conn = self.get_connection()
            
            with conn.cursor() as cursor:
                # Get table statistics
                cursor.execute(f"""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes,
                        n_live_tup as live_tuples,
                        n_dead_tup as dead_tuples,
                        last_vacuum,
                        last_autovacuum,
                        last_analyze,
                        last_autoanalyze
                    FROM pg_stat_user_tables 
                    WHERE schemaname = %s
                """, (schema_name,))
                
                table_stats = cursor.fetchall()
                
                # Get index usage
                cursor.execute(f"""
                    SELECT 
                        indexrelname as index_name,
                        idx_tup_read as tuples_read,
                        idx_tup_fetch as tuples_fetched,
                        idx_scan as scans
                    FROM pg_stat_user_indexes 
                    WHERE schemaname = %s
                    ORDER BY idx_scan DESC
                """, (schema_name,))
                
                index_stats = cursor.fetchall()
                
                # Get slow queries (if pg_stat_statements is available)
                try:
                    cursor.execute("""
                        SELECT query, mean_exec_time, calls, total_exec_time
                        FROM pg_stat_statements 
                        WHERE query LIKE %s
                        ORDER BY mean_exec_time DESC 
                        LIMIT 10
                    """, (f'%{schema_name}%',))
                    
                    slow_queries = cursor.fetchall()
                except:
                    slow_queries = []
                
            conn.close()
            
            return {
                'table_statistics': table_stats,
                'index_usage': index_stats,
                'slow_queries': slow_queries,
                'recommendations': self._generate_performance_recommendations(table_stats, index_stats)
            }
            
        except Exception as e:
            logger.error(f"Performance analysis failed: {e}")
            return {'error': str(e)}
    
    def _generate_performance_recommendations(self, table_stats, index_stats) -> List[str]:
        """Generate performance recommendations based on statistics"""
        recommendations = []
        
        # Check for tables that need vacuuming
        for stat in table_stats:
            dead_tuples = stat[5] or 0
            live_tuples = stat[4] or 0
            
            if live_tuples > 0 and dead_tuples / live_tuples > 0.1:
                recommendations.append(f"Table {stat[1]} has high dead tuple ratio ({dead_tuples}/{live_tuples}). Consider VACUUM.")
        
        # Check for unused indexes
        for stat in index_stats:
            scans = stat[3] or 0
            if scans < 10:
                recommendations.append(f"Index {stat[0]} has low usage ({scans} scans). Consider dropping if not needed.")
        
        return recommendations
    
    def optimize_queries(self, schema_name: str = 'court_data') -> bool:
        """
        Apply query optimizations and update statistics
        
        Args:
            schema_name: Schema to optimize
            
        Returns:
            True if successful
        """
        try:
            conn = self.get_connection()
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            with conn.cursor() as cursor:
                # Update table statistics
                cursor.execute(f"ANALYZE {schema_name}.judges")
                cursor.execute(f"ANALYZE {schema_name}.opinions")
                cursor.execute(f"ANALYZE {schema_name}.processing_log")
                
                logger.info("Table statistics updated")
                
                # Create materialized view for frequently accessed judge stats
                cursor.execute(f"""
                    CREATE MATERIALIZED VIEW IF NOT EXISTS {schema_name}.judge_stats_materialized AS
                    SELECT * FROM {schema_name}.judge_stats
                """)
                
                # Refresh materialized view
                cursor.execute(f"REFRESH MATERIALIZED VIEW {schema_name}.judge_stats_materialized")
                
                logger.info("Materialized views optimized")
            
            conn.close()
            return True
            
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return False


def create_optimized_database(connection_config: Dict[str, str], schema_name: str = 'court_data') -> bool:
    """
    Convenience function to create fully optimized database schema
    
    Args:
        connection_config: Database connection parameters
        schema_name: Schema name to create
        
    Returns:
        True if successful
    """
    optimizer = DatabaseOptimizer(connection_config)
    return optimizer.create_optimized_schema(schema_name)


def get_performance_report(connection_config: Dict[str, str], schema_name: str = 'court_data') -> Dict[str, Any]:
    """
    Convenience function to get performance analysis report
    
    Args:
        connection_config: Database connection parameters
        schema_name: Schema to analyze
        
    Returns:
        Performance analysis results
    """
    optimizer = DatabaseOptimizer(connection_config)
    return optimizer.analyze_performance(schema_name)


# SQL templates for common optimization patterns

JUDGE_PERFORMANCE_QUERY = """
-- Optimized query for judge-based document retrieval
SELECT 
    o.id,
    o.case_name,
    o.case_date,
    o.text_content,
    j.name as judge_name,
    j.court
FROM {schema}.opinions o
JOIN {schema}.judges j ON o.judge_id = j.id
WHERE j.name ILIKE %s
ORDER BY o.case_date DESC
LIMIT %s
"""

BATCH_PROCESSING_QUERY = """
-- Optimized query for batch processing unprocessed documents
SELECT id, case_name, text_content, metadata
FROM {schema}.opinions
WHERE {status_field} = false
ORDER BY case_date DESC
LIMIT %s
"""

CONTENT_SEARCH_QUERY = """
-- Optimized full-text search query
SELECT 
    o.id,
    o.case_name,
    o.case_date,
    ts_headline('english', o.text_content, plainto_tsquery('english', %s)) as highlighted_content,
    ts_rank(to_tsvector('english', o.text_content), plainto_tsquery('english', %s)) as relevance_score
FROM {schema}.opinions o
WHERE to_tsvector('english', o.text_content) @@ plainto_tsquery('english', %s)
ORDER BY relevance_score DESC
LIMIT %s
"""

STATISTICS_QUERY = """
-- Get comprehensive statistics for monitoring
SELECT 
    (SELECT COUNT(*) FROM {schema}.opinions) as total_opinions,
    (SELECT COUNT(*) FROM {schema}.judges) as total_judges,
    (SELECT COUNT(*) FROM {schema}.opinions WHERE vector_indexed = false) as pending_vector_indexing,
    (SELECT COUNT(*) FROM {schema}.opinions WHERE haystack_ingested = false) as pending_haystack_ingestion,
    (SELECT COUNT(*) FROM {schema}.opinions WHERE flp_enhanced = false) as pending_flp_enhancement,
    (SELECT MAX(case_date) FROM {schema}.opinions) as latest_case_date,
    (SELECT AVG(LENGTH(text_content)) FROM {schema}.opinions) as avg_content_length
"""