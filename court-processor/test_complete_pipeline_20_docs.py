#!/usr/bin/env python3
"""
Test Complete Pipeline with 20 Real Gilstrap Documents
CourtListener → Processing → PostgreSQL → Haystack

Uses existing database schema and infrastructure.
"""

import asyncio
import logging
import time
import json
import os
import sys
from datetime import datetime
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
logger = logging.getLogger("complete_pipeline_test")

# Database configuration - Use Docker network when running in container
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),  # Docker service name
    'database': os.environ.get('DB_NAME', 'aletheia'),
    'user': os.environ.get('DB_USER', 'aletheia'),
    'password': os.environ.get('DB_PASSWORD', 'aletheia123')
}

class CompletePipelineProcessor:
    """Complete pipeline processor with database integration"""
    
    def __init__(self):
        self.config = ProcessorConfig()
        self.config.courtlistener_api_key = os.getenv('COURTLISTENER_API_TOKEN', '')
        
        # Use Docker service name for Haystack when running in container
        self.config.haystack_url = os.getenv('HAYSTACK_URL', 'http://haystack-service:8000')
        
        # Initialize standalone processor
        self.standalone_processor = StandaloneEnhancedProcessor(self.config)
        
        # Database connection
        self.db_conn = None
        
        # Stats tracking
        self.stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'db_stored': 0,
            'haystack_ingested': 0,
            'errors': 0,
            'processing_time': 0
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
    
    def check_database_schema(self):
        """Check if required tables exist"""
        try:
            with self.db_conn.cursor() as cursor:
                # Check for court_documents table
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_name = 'court_documents'
                    )
                """)
                
                table_exists = cursor.fetchone()[0]
                if not table_exists:
                    logger.warning("court_documents table doesn't exist, creating it")
                    self.create_court_documents_table()
                
                return True
        except Exception as e:
            logger.error(f"Database schema check failed: {e}")
            return False
    
    def create_court_documents_table(self):
        """Create court_documents table if it doesn't exist"""
        try:
            with self.db_conn.cursor() as cursor:
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
                
                # Create indexes
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_court_documents_judge 
                    ON court_documents USING GIN ((metadata->>'judge_name'))
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_court_documents_court 
                    ON court_documents USING GIN ((metadata->>'court_id'))
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_court_documents_processed 
                    ON court_documents (processed)
                """)
                
                self.db_conn.commit()
                logger.info("Created court_documents table with indexes")
                
        except Exception as e:
            logger.error(f"Failed to create court_documents table: {e}")
            self.db_conn.rollback()
    
    def is_document_duplicate(self, doc_meta: Dict[str, Any]) -> bool:
        """Check if document already exists in database"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM court_documents 
                    WHERE case_number = %s AND document_type = %s
                """, (
                    doc_meta.get('case_name', 'Unknown'),
                    doc_meta.get('type', 'opinion')
                ))
                
                existing = cursor.fetchone()
                return existing is not None
                
        except Exception as e:
            logger.error(f"Duplicate check failed: {e}")
            return False
    
    def store_document_in_database(self, document: Dict[str, Any]) -> Optional[int]:
        """Store processed document in PostgreSQL database"""
        try:
            content = document['content']
            meta = document['meta']
            
            # Check for duplicates
            if self.is_document_duplicate(meta):
                logger.info(f"Skipping duplicate: {meta.get('case_name', 'Unknown')}")
                self.stats['duplicates'] += 1
                return None
            
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_documents 
                    (case_number, document_type, content, metadata, processed, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    meta.get('case_name', f"Gilstrap-{meta.get('courtlistener_id', 'Unknown')}"),
                    meta.get('type', 'opinion'),
                    content,
                    Json(meta),
                    True,  # Mark as processed
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                doc_id = cursor.fetchone()[0]
                self.db_conn.commit()
                
                logger.info(f"Stored document in database with ID: {doc_id}")
                self.stats['db_stored'] += 1
                return doc_id
                
        except Exception as e:
            logger.error(f"Failed to store document in database: {e}")
            self.db_conn.rollback()
            self.stats['errors'] += 1
            return None
    
    def get_documents_from_database(self, judge_name: str = "Gilstrap", limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve documents from database for Haystack ingestion"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, case_number, document_type, content, metadata, created_at, updated_at
                    FROM court_documents
                    WHERE metadata->>'judge_name' ILIKE %s
                    AND content IS NOT NULL
                    AND content != ''
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (f"%{judge_name}%", limit))
                
                documents = cursor.fetchall()
                logger.info(f"Retrieved {len(documents)} documents from database")
                return [dict(doc) for doc in documents]
                
        except Exception as e:
            logger.error(f"Failed to retrieve documents from database: {e}")
            return []
    
    def prepare_document_for_haystack(self, db_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare database document for Haystack ingestion"""
        metadata = db_doc.get('metadata', {})
        content = db_doc.get('content', '')
        
        # Create searchable content
        searchable_content = f"""
Case: {metadata.get('case_name', 'Unknown')}
Judge: {metadata.get('judge_name', 'Unknown')}
Court: {metadata.get('court', 'Unknown')}
Date: {metadata.get('date_filed', 'Unknown')}
Case Number: {db_doc.get('case_number', 'Unknown')}

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
                'source': 'complete_pipeline',
                'content_length': len(content),
                'pipeline_timestamp': datetime.utcnow().isoformat()
            }
        }
    
    async def ingest_database_documents_to_haystack(self, judge_name: str = "Gilstrap") -> Dict[str, Any]:
        """Ingest documents from database to Haystack"""
        logger.info(f"Starting Haystack ingestion for {judge_name} documents")
        
        # Get documents from database
        db_documents = self.get_documents_from_database(judge_name)
        
        if not db_documents:
            logger.warning("No documents found in database for Haystack ingestion")
            return {'successful_ingestions': 0, 'failed_ingestions': 0}
        
        # Prepare documents for Haystack
        haystack_docs = []
        for db_doc in db_documents:
            haystack_doc = self.prepare_document_for_haystack(db_doc)
            haystack_docs.append(haystack_doc)
        
        # Ingest to Haystack
        ingestion_result = await self.standalone_processor.ingest_to_haystack(haystack_docs)
        
        self.stats['haystack_ingested'] = ingestion_result['successful_ingestions']
        
        return ingestion_result
    
    async def run_complete_pipeline_test(self, max_documents: int = 20) -> Dict[str, Any]:
        """Run the complete pipeline test with 20 documents"""
        
        logger.info("="*80)
        logger.info("COMPLETE PIPELINE TEST: 20 REAL GILSTRAP DOCUMENTS")
        logger.info("="*80)
        logger.info(f"Target: {max_documents} documents")
        logger.info(f"Pipeline: CourtListener → Processing → PostgreSQL → Haystack")
        logger.info("")
        
        start_time = time.time()
        
        # Step 1: Connect to database
        logger.info("Step 1: Database Connection")
        if not self.connect_to_database():
            return {'error': 'Database connection failed'}
        
        if not self.check_database_schema():
            return {'error': 'Database schema check failed'}
        
        logger.info("✅ Database ready")
        
        # Step 2: Fetch and process documents from CourtListener
        logger.info(f"\nStep 2: Fetch {max_documents} documents from CourtListener")
        processing_result = await self.standalone_processor.process_gilstrap_documents(
            max_documents=max_documents
        )
        
        self.stats['total_fetched'] = processing_result['total_fetched']
        self.stats['new_documents'] = processing_result['new_documents']
        
        logger.info(f"✅ Fetched and processed {processing_result['new_documents']} documents")
        
        # Step 3: Store documents in PostgreSQL
        logger.info(f"\nStep 3: Store documents in PostgreSQL")
        if processing_result['documents']:
            for doc in processing_result['documents']:
                doc_id = self.store_document_in_database(doc)
                if doc_id:
                    logger.debug(f"Stored document with DB ID: {doc_id}")
        
        logger.info(f"✅ Stored {self.stats['db_stored']} documents in database")
        
        # Step 4: Ingest to Haystack
        logger.info(f"\nStep 4: Ingest documents to Haystack")
        haystack_result = await self.ingest_database_documents_to_haystack()
        
        logger.info(f"✅ Ingested {haystack_result['successful_ingestions']} documents to Haystack")
        
        # Calculate final stats
        self.stats['processing_time'] = time.time() - start_time
        
        # Step 5: Test retrieval
        logger.info(f"\nStep 5: Test Haystack retrieval")
        retrieval_test = await self.test_haystack_retrieval()
        
        # Close database connection
        if self.db_conn:
            self.db_conn.close()
        
        return {
            **self.stats,
            'haystack_result': haystack_result,
            'retrieval_test': retrieval_test
        }
    
    async def test_haystack_retrieval(self) -> Dict[str, Any]:
        """Test Haystack retrieval of ingested documents"""
        test_queries = [
            "Judge Gilstrap patent infringement",
            "Eastern District of Texas",
            "summary judgment",
            "claim construction"
        ]
        
        retrieval_results = {}
        
        for query in test_queries:
            try:
                haystack_url = os.getenv('HAYSTACK_URL', 'http://haystack-service:8000')
                response = requests.post(
                    f"{haystack_url}/search",
                    json={"query": query, "top_k": 5},
                    timeout=10
                )
                
                if response.status_code == 200:
                    results = response.json()
                    retrieval_results[query] = {
                        'total_results': results.get('total_results', 0),
                        'found_results': len(results.get('results', [])),
                        'top_scores': [
                            doc.get('score', 0) for doc in results.get('results', [])[:3]
                        ]
                    }
                    logger.info(f"Query '{query}': {retrieval_results[query]['found_results']} results")
                else:
                    retrieval_results[query] = {'error': f"HTTP {response.status_code}"}
                    
            except Exception as e:
                retrieval_results[query] = {'error': str(e)}
        
        return retrieval_results
    
    def print_final_report(self, results: Dict[str, Any]):
        """Print comprehensive final report"""
        logger.info("\n" + "="*80)
        logger.info("COMPLETE PIPELINE TEST RESULTS")
        logger.info("="*80)
        
        # Processing stats
        logger.info(f"📊 PROCESSING STATISTICS")
        logger.info(f"   Documents fetched from CourtListener: {results['total_fetched']}")
        logger.info(f"   Documents processed: {results['new_documents']}")
        logger.info(f"   Duplicates skipped: {results['duplicates']}")
        logger.info(f"   Documents stored in PostgreSQL: {results['db_stored']}")
        logger.info(f"   Documents ingested to Haystack: {results['haystack_ingested']}")
        logger.info(f"   Processing errors: {results['errors']}")
        logger.info(f"   Total processing time: {results['processing_time']:.2f}s")
        
        # Success rates
        if results['total_fetched'] > 0:
            processing_rate = (results['new_documents'] / results['total_fetched']) * 100
            db_rate = (results['db_stored'] / results['new_documents']) * 100 if results['new_documents'] > 0 else 0
            haystack_rate = (results['haystack_ingested'] / results['db_stored']) * 100 if results['db_stored'] > 0 else 0
            
            logger.info(f"\n📈 SUCCESS RATES")
            logger.info(f"   Processing success rate: {processing_rate:.1f}%")
            logger.info(f"   Database storage rate: {db_rate:.1f}%")
            logger.info(f"   Haystack ingestion rate: {haystack_rate:.1f}%")
        
        # Retrieval test results
        if 'retrieval_test' in results:
            logger.info(f"\n🔍 HAYSTACK RETRIEVAL TEST")
            for query, result in results['retrieval_test'].items():
                if 'error' in result:
                    logger.info(f"   '{query}': ❌ {result['error']}")
                else:
                    logger.info(f"   '{query}': ✅ {result['found_results']} results")
        
        # Overall assessment
        overall_success = (
            results['total_fetched'] > 0 and
            results['db_stored'] > 0 and
            results['haystack_ingested'] > 0 and
            results['errors'] == 0
        )
        
        logger.info(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '⚠️ PARTIAL SUCCESS'}")
        logger.info("="*80)

async def main():
    """Main function to run the complete pipeline test"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test complete pipeline with real Gilstrap documents')
    parser.add_argument('--max-docs', type=int, default=20, help='Maximum documents to process')
    
    args = parser.parse_args()
    
    # Create and run the complete pipeline test
    processor = CompletePipelineProcessor()
    results = await processor.run_complete_pipeline_test(args.max_docs)
    
    # Print final report
    processor.print_final_report(results)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())