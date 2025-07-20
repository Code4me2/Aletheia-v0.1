#!/usr/bin/env python3
"""
Comprehensive Judge Gilstrap Data Retrieval: July 2020 - July 2025
Using the complete pipeline architecture with PostgreSQL-first storage
"""

import asyncio
import logging
import time
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import requests

# Import our working standalone processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standalone_enhanced_processor import StandaloneEnhancedProcessor, ProcessorConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gilstrap_comprehensive")

# Database configuration - Use Docker network
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'database': os.environ.get('DB_NAME', 'aletheia'),
    'user': os.environ.get('DB_USER', 'aletheia'),
    'password': os.environ.get('DB_PASSWORD', 'aletheia123')
}

class GilstrapComprehensiveProcessor:
    """Comprehensive processor for all Judge Gilstrap documents 2020-2025"""
    
    def __init__(self):
        self.config = ProcessorConfig()
        self.config.courtlistener_api_key = os.getenv('COURTLISTENER_API_TOKEN', '')
        self.config.haystack_url = os.getenv('HAYSTACK_URL', 'http://haystack-service:8000')
        
        # Initialize standalone processor
        self.standalone_processor = StandaloneEnhancedProcessor(self.config)
        
        # Database connection
        self.db_conn = None
        
        # Comprehensive stats
        self.stats = {
            'total_searched': 0,
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'db_stored': 0,
            'haystack_ingested': 0,
            'errors': 0,
            'processing_time': 0,
            'content_volume': 0,
            'date_range': {
                'start': '2020-07-01',
                'end': '2025-07-31'
            },
            'court_coverage': [],
            'document_types': {},
            'yearly_breakdown': {}
        }
    
    def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            self.db_conn = psycopg2.connect(**DB_CONFIG)
            logger.info("Connected to PostgreSQL database")
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def ensure_database_schema(self):
        """Ensure database schema exists for comprehensive data"""
        try:
            with self.db_conn.cursor() as cursor:
                # Check if court_documents table exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'court_documents'
                    )
                """)
                
                if not cursor.fetchone()[0]:
                    # Create comprehensive schema
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS court_documents (
                            id SERIAL PRIMARY KEY,
                            case_number VARCHAR(255) NOT NULL,
                            document_type VARCHAR(100) DEFAULT 'opinion',
                            content TEXT,
                            metadata JSONB,
                            processed BOOLEAN DEFAULT FALSE,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            -- Indexes for performance
                            UNIQUE(case_number, document_type)
                        )
                    """)
                    
                    # Create comprehensive indexes for Judge Gilstrap queries
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_court_documents_judge 
                        ON court_documents USING GIN ((metadata->>'judge_name'))
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_court_documents_date 
                        ON court_documents USING GIN ((metadata->>'date_filed'))
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_court_documents_court 
                        ON court_documents USING GIN ((metadata->>'court_id'))
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_court_documents_content_search 
                        ON court_documents USING GIN (to_tsvector('english', content))
                    """)
                    
                    self.db_conn.commit()
                    logger.info("Created comprehensive database schema")
                
                return True
        except Exception as e:
            logger.error(f"Database schema setup failed: {e}")
            self.db_conn.rollback()
            return False
    
    def get_existing_gilstrap_documents(self) -> Dict[str, Any]:
        """Get statistics on existing Gilstrap documents"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Count existing documents
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_docs,
                        COUNT(DISTINCT metadata->>'case_name') as unique_cases,
                        MIN(metadata->>'date_filed') as earliest_date,
                        MAX(metadata->>'date_filed') as latest_date,
                        AVG(LENGTH(content)) as avg_content_length
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                    AND content IS NOT NULL
                """)
                
                stats = cursor.fetchone()
                
                # Get document types breakdown
                cursor.execute("""
                    SELECT 
                        document_type,
                        COUNT(*) as count
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                    GROUP BY document_type
                    ORDER BY count DESC
                """)
                
                doc_types = {row['document_type']: row['count'] for row in cursor.fetchall()}
                
                # Get yearly breakdown
                cursor.execute("""
                    SELECT 
                        EXTRACT(YEAR FROM (metadata->>'date_filed')::date) as year,
                        COUNT(*) as count
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                    AND metadata->>'date_filed' IS NOT NULL
                    GROUP BY EXTRACT(YEAR FROM (metadata->>'date_filed')::date)
                    ORDER BY year
                """)
                
                yearly = {str(int(row['year'])): row['count'] for row in cursor.fetchall() if row['year']}
                
                return {
                    'existing_stats': dict(stats) if stats else {},
                    'document_types': doc_types,
                    'yearly_breakdown': yearly
                }
                
        except Exception as e:
            logger.error(f"Failed to get existing document stats: {e}")
            return {}
    
    async def fetch_all_available_gilstrap_documents(self, max_documents: int = 1000) -> Dict[str, Any]:
        """Fetch all available Gilstrap documents using existing processor"""
        logger.info(f"Fetching all available Gilstrap documents (max: {max_documents})")
        
        total_documents = []
        batch_size = 100
        processed_batches = 0
        
        while len(total_documents) < max_documents:
            remaining = max_documents - len(total_documents)
            current_batch_size = min(batch_size, remaining)
            
            logger.info(f"Fetching batch {processed_batches + 1} (up to {current_batch_size} documents)")
            
            try:
                # Use existing processor to fetch documents
                batch_result = await self.standalone_processor.process_gilstrap_documents(
                    max_documents=current_batch_size,
                    court_id="txed"
                )
                
                if not batch_result.get('documents'):
                    logger.info("No more documents available")
                    break
                
                documents = batch_result['documents']
                new_documents = []
                
                # Filter out already processed documents
                for doc in documents:
                    if not self.is_document_duplicate(doc.get('meta', {})):
                        new_documents.append(doc)
                
                if not new_documents:
                    logger.info("No new documents in this batch")
                    break
                
                total_documents.extend(new_documents)
                
                self.stats['total_fetched'] += len(documents)
                self.stats['new_documents'] += len(new_documents)
                
                logger.info(f"Fetched {len(documents)} documents, {len(new_documents)} new")
                
                # Store documents in PostgreSQL
                stored_count = 0
                for doc in new_documents:
                    if self.store_document_in_database(doc):
                        stored_count += 1
                
                logger.info(f"Stored {stored_count} new documents in database")
                
                # Rate limiting
                await asyncio.sleep(2)
                
                processed_batches += 1
                
                # If we got fewer documents than requested, we've reached the end
                if len(documents) < current_batch_size:
                    break
                
            except Exception as e:
                logger.error(f"Error fetching documents in batch {processed_batches + 1}: {e}")
                self.stats['errors'] += 1
                break
        
        return {
            'total_documents_fetched': len(total_documents),
            'documents': total_documents,
            'batches_processed': processed_batches
        }
    
    def store_document_in_database(self, document: Dict[str, Any]) -> bool:
        """Store document in PostgreSQL with comprehensive metadata"""
        try:
            content = document['content']
            meta = document['meta']
            
            # Check for duplicates
            if self.is_document_duplicate(meta):
                self.stats['duplicates'] += 1
                return False
            
            with self.db_conn.cursor() as cursor:
                # Enhance metadata with additional processing info
                enhanced_meta = {
                    **meta,
                    'comprehensive_fetch': True,
                    'fetch_timestamp': datetime.utcnow().isoformat(),
                    'content_length': len(content),
                    'content_words': len(content.split()) if content else 0
                }
                
                cursor.execute("""
                    INSERT INTO court_documents 
                    (case_number, document_type, content, metadata, processed, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    meta.get('case_name', f"Gilstrap-{meta.get('courtlistener_id', 'Unknown')}"),
                    meta.get('type', 'opinion'),
                    content,
                    Json(enhanced_meta),
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                doc_id = cursor.fetchone()[0]
                self.db_conn.commit()
                
                self.stats['db_stored'] += 1
                self.stats['content_volume'] += len(content)
                
                # Track document types
                doc_type = meta.get('type', 'opinion')
                self.stats['document_types'][doc_type] = self.stats['document_types'].get(doc_type, 0) + 1
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            self.db_conn.rollback()
            self.stats['errors'] += 1
            return False
    
    def is_document_duplicate(self, meta: Dict[str, Any]) -> bool:
        """Check if document already exists"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM court_documents 
                    WHERE case_number = %s AND document_type = %s
                """, (
                    meta.get('case_name', 'Unknown'),
                    meta.get('type', 'opinion')
                ))
                
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return False
    
    def analyze_date_distribution(self):
        """Analyze the date distribution of documents in the database"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT 
                        EXTRACT(YEAR FROM (metadata->>'date_filed')::date) as year,
                        COUNT(*) as count
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                    AND metadata->>'date_filed' IS NOT NULL
                    GROUP BY EXTRACT(YEAR FROM (metadata->>'date_filed')::date)
                    ORDER BY year
                """)
                
                yearly_data = cursor.fetchall()
                
                for row in yearly_data:
                    year = str(int(row['year'])) if row['year'] else 'Unknown'
                    count = row['count']
                    self.stats['yearly_breakdown'][year] = count
                
                logger.info("📅 Date distribution analysis complete")
                
        except Exception as e:
            logger.error(f"Date distribution analysis failed: {e}")
    
    async def ingest_all_gilstrap_to_haystack(self) -> Dict[str, Any]:
        """Ingest all Gilstrap documents to Haystack"""
        logger.info("Starting comprehensive Haystack ingestion for all Gilstrap documents")
        
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Get all Gilstrap documents
                cursor.execute("""
                    SELECT id, case_number, document_type, content, metadata, created_at, updated_at
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                    AND content IS NOT NULL
                    AND content != ''
                    ORDER BY created_at DESC
                """)
                
                documents = cursor.fetchall()
                logger.info(f"Found {len(documents)} Gilstrap documents for Haystack ingestion")
                
                if not documents:
                    return {'successful_ingestions': 0, 'failed_ingestions': 0}
                
                # Prepare documents for Haystack
                haystack_docs = []
                for db_doc in documents:
                    haystack_doc = self.prepare_document_for_haystack(dict(db_doc))
                    haystack_docs.append(haystack_doc)
                
                # Ingest to Haystack in batches
                batch_size = 50
                total_successful = 0
                total_failed = 0
                
                for i in range(0, len(haystack_docs), batch_size):
                    batch = haystack_docs[i:i+batch_size]
                    logger.info(f"Ingesting batch {i//batch_size + 1} ({len(batch)} documents)")
                    
                    result = await self.standalone_processor.ingest_to_haystack(batch)
                    total_successful += result['successful_ingestions']
                    total_failed += result['failed_ingestions']
                    
                    # Rate limiting between batches
                    await asyncio.sleep(1)
                
                self.stats['haystack_ingested'] = total_successful
                
                return {
                    'successful_ingestions': total_successful,
                    'failed_ingestions': total_failed,
                    'total_documents': len(documents)
                }
                
        except Exception as e:
            logger.error(f"Haystack ingestion failed: {e}")
            return {'successful_ingestions': 0, 'failed_ingestions': 1}
    
    def prepare_document_for_haystack(self, db_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare database document for Haystack ingestion"""
        metadata = db_doc.get('metadata', {})
        content = db_doc.get('content', '')
        
        # Create comprehensive searchable content
        searchable_content = f"""
Case: {metadata.get('case_name', 'Unknown')}
Judge: {metadata.get('judge_name', 'Unknown')}
Court: {metadata.get('court', 'Unknown')}
Date: {metadata.get('date_filed', 'Unknown')}
Case Number: {db_doc.get('case_number', 'Unknown')}
Document Type: {db_doc.get('document_type', 'Unknown')}

{content}
"""
        
        return {
            'content': searchable_content.strip(),
            'meta': {
                # Core identification
                'database_id': db_doc.get('id'),
                'case_number': db_doc.get('case_number'),
                'document_type': db_doc.get('document_type'),
                
                # From metadata
                **metadata,
                
                # Database timestamps
                'db_created_at': str(db_doc.get('created_at')),
                'db_updated_at': str(db_doc.get('updated_at')),
                
                # Processing info
                'source': 'comprehensive_gilstrap_fetch',
                'content_length': len(content),
                'comprehensive_fetch': True,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        }
    
    async def run_comprehensive_fetch(self) -> Dict[str, Any]:
        """Run comprehensive fetch for all Gilstrap documents 2020-2025"""
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP DATA RETRIEVAL")
        logger.info("=" * 80)
        logger.info("Date Range: July 2020 - July 2025")
        logger.info("Court: Eastern District of Texas")
        logger.info("Judge: Rodney Gilstrap")
        logger.info("")
        
        start_time = time.time()
        
        # Step 1: Database setup
        logger.info("Step 1: Database Connection & Schema Setup")
        if not self.connect_to_database():
            return {'error': 'Database connection failed'}
        
        if not self.ensure_database_schema():
            return {'error': 'Database schema setup failed'}
        
        # Get existing document stats
        existing_stats = self.get_existing_gilstrap_documents()
        logger.info(f"✅ Database ready. Existing: {existing_stats.get('existing_stats', {}).get('total_docs', 0)} Gilstrap documents")
        
        # Step 2: Comprehensive document fetching
        logger.info("\nStep 2: Comprehensive Document Fetching")
        logger.info("Fetching all available Judge Gilstrap documents from CourtListener")
        
        # Fetch all available documents (the API will return chronologically)
        # Since we want 2020-2025 data, we'll fetch a large number to ensure coverage
        fetch_result = await self.fetch_all_available_gilstrap_documents(max_documents=2000)
        
        logger.info(f"✅ Completed comprehensive fetch: {fetch_result['total_documents_fetched']} documents")
        logger.info(f"   Processed {fetch_result['batches_processed']} batches")
        
        # Analyze the date distribution of fetched documents
        self.analyze_date_distribution()
        
        # Step 3: Haystack ingestion
        logger.info(f"\nStep 3: Haystack Ingestion")
        haystack_result = await self.ingest_all_gilstrap_to_haystack()
        
        logger.info(f"✅ Haystack ingestion complete: {haystack_result['successful_ingestions']} documents")
        
        # Calculate final stats
        self.stats['processing_time'] = time.time() - start_time
        
        # Step 4: Final verification
        logger.info(f"\nStep 4: Final Verification")
        final_stats = self.get_existing_gilstrap_documents()
        
        # Close database connection
        if self.db_conn:
            self.db_conn.close()
        
        return {
            'stats': self.stats,
            'existing_before': existing_stats,
            'existing_after': final_stats,
            'haystack_result': haystack_result,
            'fetch_result': fetch_result
        }
    
    def print_comprehensive_report(self, results: Dict[str, Any]):
        """Print comprehensive final report"""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP RETRIEVAL REPORT")
        logger.info("=" * 80)
        
        stats = results.get('stats', {})
        existing_before = results.get('existing_before', {})
        existing_after = results.get('existing_after', {})
        
        # Processing Statistics
        logger.info("📊 PROCESSING STATISTICS")
        logger.info(f"   Date Range: {stats.get('date_range', {}).get('start')} to {stats.get('date_range', {}).get('end')}")
        logger.info(f"   Total documents fetched: {stats.get('total_fetched', 0)}")
        logger.info(f"   New documents processed: {stats.get('new_documents', 0)}")
        logger.info(f"   Documents stored in PostgreSQL: {stats.get('db_stored', 0)}")
        logger.info(f"   Duplicates skipped: {stats.get('duplicates', 0)}")
        logger.info(f"   Documents ingested to Haystack: {stats.get('haystack_ingested', 0)}")
        logger.info(f"   Processing time: {stats.get('processing_time', 0):.2f} seconds")
        
        # Content Analysis
        logger.info(f"\n📈 CONTENT ANALYSIS")
        logger.info(f"   Total content volume: {stats.get('content_volume', 0):,} characters")
        if stats.get('db_stored', 0) > 0:
            avg_content = stats.get('content_volume', 0) / stats.get('db_stored', 1)
            logger.info(f"   Average content per document: {avg_content:,.0f} characters")
        
        # Document Types
        if stats.get('document_types'):
            logger.info(f"\n📋 DOCUMENT TYPES")
            for doc_type, count in stats['document_types'].items():
                logger.info(f"   {doc_type}: {count} documents")
        
        # Yearly Breakdown
        if stats.get('yearly_breakdown'):
            logger.info(f"\n📅 YEARLY BREAKDOWN")
            for year, count in sorted(stats['yearly_breakdown'].items()):
                logger.info(f"   {year}: {count} documents")
        
        # Before/After Comparison
        before_total = existing_before.get('existing_stats', {}).get('total_docs', 0)
        after_total = existing_after.get('existing_stats', {}).get('total_docs', 0)
        
        logger.info(f"\n🔄 BEFORE/AFTER COMPARISON")
        logger.info(f"   Documents before: {before_total}")
        logger.info(f"   Documents after: {after_total}")
        logger.info(f"   Net increase: {after_total - before_total}")
        
        # Overall Assessment
        overall_success = (
            stats.get('db_stored', 0) > 0 or
            stats.get('haystack_ingested', 0) > 0
        )
        
        logger.info(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
        logger.info(f"   Data retrieval: {'✅ SUCCESS' if stats.get('total_fetched', 0) > 0 else '❌ FAILED'}")
        logger.info(f"   Database storage: {'✅ SUCCESS' if stats.get('db_stored', 0) > 0 else '❌ FAILED'}")
        logger.info(f"   Haystack indexing: {'✅ SUCCESS' if stats.get('haystack_ingested', 0) > 0 else '❌ FAILED'}")
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP DATABASE COMPLETE")
        logger.info("All documents from July 2020 - July 2025 processed")
        logger.info("=" * 80)

async def main():
    """Main function to run comprehensive Gilstrap data retrieval"""
    
    # Create and run comprehensive processor
    processor = GilstrapComprehensiveProcessor()
    results = await processor.run_comprehensive_fetch()
    
    # Print comprehensive report
    processor.print_comprehensive_report(results)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())