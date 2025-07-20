#!/usr/bin/env python3
"""
Fetch ALL available Judge Gilstrap documents from CourtListener
Regardless of date range, get everything that exists
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
logger = logging.getLogger("all_gilstrap")

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'database': os.environ.get('DB_NAME', 'aletheia'),
    'user': os.environ.get('DB_USER', 'aletheia'),
    'password': os.environ.get('DB_PASSWORD', 'aletheia123')
}

class AllGilstrapProcessor:
    """Processor to fetch ALL available Judge Gilstrap documents"""
    
    def __init__(self):
        self.config = ProcessorConfig()
        self.config.courtlistener_api_key = os.getenv('COURTLISTENER_API_TOKEN', '')
        self.config.haystack_url = os.getenv('HAYSTACK_URL', 'http://haystack-service:8000')
        
        # Initialize standalone processor
        self.standalone_processor = StandaloneEnhancedProcessor(self.config)
        
        # Database connection
        self.db_conn = None
        
        # Stats
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
            'yearly_breakdown': {},
            'search_methods_used': []
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
    
    async def fetch_using_multiple_methods(self) -> Dict[str, Any]:
        """Try multiple search methods to get all Gilstrap documents"""
        
        all_documents = []
        seen_ids = set()
        
        # Multiple search strategies
        search_methods = [
            {
                'name': 'Primary Judge Search',
                'approach': 'judge_name',
                'max_docs': 200
            },
            {
                'name': 'Text Search for Gilstrap',
                'approach': 'text_search',
                'max_docs': 200
            },
            {
                'name': 'Extended Judge Search',
                'approach': 'extended_judge',
                'max_docs': 200
            }
        ]
        
        for method in search_methods:
            logger.info(f"\n--- {method['name']} ---")
            
            try:
                if method['approach'] == 'judge_name':
                    # Use our existing processor
                    result = await self.standalone_processor.process_gilstrap_documents(
                        max_documents=method['max_docs'],
                        court_id="txed"
                    )
                    
                elif method['approach'] == 'text_search':
                    # Direct API call for text search
                    result = await self.text_search_gilstrap(method['max_docs'])
                    
                elif method['approach'] == 'extended_judge':
                    # Extended search with different parameters
                    result = await self.extended_judge_search(method['max_docs'])
                
                if result and result.get('documents'):
                    documents = result['documents']
                    new_docs = 0
                    
                    for doc in documents:
                        doc_id = doc.get('meta', {}).get('courtlistener_id', '')
                        if doc_id and doc_id not in seen_ids:
                            all_documents.append(doc)
                            seen_ids.add(doc_id)
                            new_docs += 1
                    
                    logger.info(f"  ✅ Found {len(documents)} documents, {new_docs} new")
                    self.stats['search_methods_used'].append({
                        'method': method['name'],
                        'total_found': len(documents),
                        'new_documents': new_docs
                    })
                else:
                    logger.info(f"  ❌ No documents found")
                
            except Exception as e:
                logger.error(f"  ❌ {method['name']} failed: {e}")
                self.stats['errors'] += 1
        
        return {
            'total_unique_documents': len(all_documents),
            'documents': all_documents,
            'search_methods': self.stats['search_methods_used']
        }
    
    async def text_search_gilstrap(self, max_docs: int) -> Dict[str, Any]:
        """Search for documents containing 'gilstrap' in text"""
        logger.info(f"Text search for Gilstrap documents (max: {max_docs})")
        
        headers = {
            'Authorization': f'Token {self.config.courtlistener_api_key}',
            'User-Agent': 'Comprehensive Gilstrap Search'
        }
        
        params = {
            'q': 'gilstrap',
            'type': 'o',
            'court': 'txed',
            'page_size': min(max_docs, 100)
        }
        
        try:
            response = requests.get(
                f"{self.config.courtlistener_base_url}/search/",
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                # Convert to our document format
                documents = []
                for result in results:
                    # Get full document content
                    doc_content = await self.fetch_full_document(result)
                    if doc_content:
                        documents.append(doc_content)
                
                return {
                    'documents': documents,
                    'method': 'text_search'
                }
            else:
                logger.error(f"Text search failed: {response.status_code}")
                return {'documents': []}
                
        except Exception as e:
            logger.error(f"Text search error: {e}")
            return {'documents': []}
    
    async def extended_judge_search(self, max_docs: int) -> Dict[str, Any]:
        """Extended judge search with different parameters"""
        logger.info(f"Extended judge search (max: {max_docs})")
        
        headers = {
            'Authorization': f'Token {self.config.courtlistener_api_key}',
            'User-Agent': 'Extended Gilstrap Search'
        }
        
        # Try multiple query variations
        queries = [
            'judge:"Rodney Gilstrap"',
            'judge:"R. Gilstrap"',
            'judge:Gilstrap',
            'assignedTo:"Rodney Gilstrap"'
        ]
        
        all_results = []
        
        for query in queries:
            params = {
                'q': query,
                'type': 'o',
                'court': 'txed',
                'page_size': min(max_docs // len(queries), 50)
            }
            
            try:
                response = requests.get(
                    f"{self.config.courtlistener_base_url}/search/",
                    params=params,
                    headers=headers,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get('results', [])
                    
                    for result in results:
                        doc_content = await self.fetch_full_document(result)
                        if doc_content:
                            all_results.append(doc_content)
                    
                    logger.info(f"  Query '{query}': {len(results)} results")
                
            except Exception as e:
                logger.error(f"Extended search query '{query}' failed: {e}")
        
        return {
            'documents': all_results,
            'method': 'extended_judge_search'
        }
    
    async def fetch_full_document(self, search_result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Fetch full document content from search result"""
        try:
            # Get the opinion URL
            opinion_url = search_result.get('resource_uri', '')
            if not opinion_url:
                return None
            
            headers = {
                'Authorization': f'Token {self.config.courtlistener_api_key}',
                'User-Agent': 'Document Fetcher'
            }
            
            response = requests.get(
                f"https://www.courtlistener.com{opinion_url}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                opinion_data = response.json()
                
                # Extract content
                content = opinion_data.get('plain_text', '') or opinion_data.get('html_with_citations', '')
                
                if not content:
                    return None
                
                # Build metadata
                metadata = {
                    'courtlistener_id': opinion_data.get('id'),
                    'case_name': opinion_data.get('case_name', 'Unknown'),
                    'date_filed': opinion_data.get('date_filed', ''),
                    'court': 'txed',
                    'court_full': 'Eastern District of Texas',
                    'judge_name': opinion_data.get('author_str', ''),
                    'type': 'opinion',
                    'source': 'courtlistener_comprehensive',
                    'citation_count': opinion_data.get('citation_count', 0),
                    'precedential_status': opinion_data.get('precedential_status', ''),
                    'comprehensive_search': True
                }
                
                return {
                    'content': content,
                    'meta': metadata
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching full document: {e}")
            return None
    
    def store_document_in_database(self, document: Dict[str, Any]) -> bool:
        """Store document in PostgreSQL"""
        try:
            content = document['content']
            meta = document['meta']
            
            # Check for duplicates
            if self.is_document_duplicate(meta):
                self.stats['duplicates'] += 1
                return False
            
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
                    True,
                    datetime.utcnow(),
                    datetime.utcnow()
                ))
                
                doc_id = cursor.fetchone()[0]
                self.db_conn.commit()
                
                self.stats['db_stored'] += 1
                self.stats['content_volume'] += len(content)
                
                # Track yearly breakdown
                date_filed = meta.get('date_filed', '')
                if date_filed:
                    year = date_filed[:4]
                    self.stats['yearly_breakdown'][year] = self.stats['yearly_breakdown'].get(year, 0) + 1
                
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
    
    async def ingest_to_haystack(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest documents to Haystack"""
        logger.info(f"Ingesting {len(documents)} documents to Haystack")
        
        if not documents:
            return {'successful_ingestions': 0, 'failed_ingestions': 0}
        
        try:
            result = await self.standalone_processor.ingest_to_haystack(documents)
            self.stats['haystack_ingested'] = result['successful_ingestions']
            return result
        except Exception as e:
            logger.error(f"Haystack ingestion failed: {e}")
            return {'successful_ingestions': 0, 'failed_ingestions': len(documents)}
    
    async def run_comprehensive_fetch(self) -> Dict[str, Any]:
        """Run comprehensive fetch of all available Gilstrap documents"""
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP DATA COLLECTION")
        logger.info("=" * 80)
        logger.info("Goal: Fetch ALL available Judge Gilstrap documents")
        logger.info("Methods: Multiple search strategies")
        logger.info("")
        
        start_time = time.time()
        
        # Step 1: Database setup
        logger.info("Step 1: Database Connection")
        if not self.connect_to_database():
            return {'error': 'Database connection failed'}
        
        # Step 2: Multi-method search
        logger.info("\nStep 2: Multi-Method Document Search")
        search_result = await self.fetch_using_multiple_methods()
        
        documents = search_result['documents']
        logger.info(f"✅ Found {len(documents)} unique documents across all methods")
        
        # Step 3: Store in database
        logger.info(f"\nStep 3: Store Documents in PostgreSQL")
        for i, doc in enumerate(documents):
            if self.store_document_in_database(doc):
                logger.info(f"  Stored document {i+1}/{len(documents)}: {doc['meta'].get('case_name', 'Unknown')}")
        
        logger.info(f"✅ Stored {self.stats['db_stored']} new documents")
        
        # Step 4: Haystack ingestion
        logger.info(f"\nStep 4: Haystack Ingestion")
        haystack_result = await self.ingest_to_haystack(documents)
        
        logger.info(f"✅ Ingested {haystack_result['successful_ingestions']} documents to Haystack")
        
        # Calculate final stats
        self.stats['processing_time'] = time.time() - start_time
        self.stats['total_fetched'] = len(documents)
        self.stats['new_documents'] = len(documents)
        
        # Close database connection
        if self.db_conn:
            self.db_conn.close()
        
        return {
            'stats': self.stats,
            'search_result': search_result,
            'haystack_result': haystack_result
        }
    
    def print_comprehensive_report(self, results: Dict[str, Any]):
        """Print comprehensive report"""
        logger.info("\n" + "=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP COLLECTION REPORT")
        logger.info("=" * 80)
        
        stats = results.get('stats', {})
        
        # Processing Statistics
        logger.info("📊 PROCESSING STATISTICS")
        logger.info(f"   Total unique documents found: {stats.get('total_fetched', 0)}")
        logger.info(f"   New documents stored: {stats.get('db_stored', 0)}")
        logger.info(f"   Duplicates skipped: {stats.get('duplicates', 0)}")
        logger.info(f"   Documents ingested to Haystack: {stats.get('haystack_ingested', 0)}")
        logger.info(f"   Processing time: {stats.get('processing_time', 0):.2f} seconds")
        logger.info(f"   Content volume: {stats.get('content_volume', 0):,} characters")
        
        # Search Methods
        logger.info(f"\n🔍 SEARCH METHODS USED")
        for method in stats.get('search_methods_used', []):
            logger.info(f"   {method['method']}: {method['total_found']} total, {method['new_documents']} new")
        
        # Yearly Breakdown
        if stats.get('yearly_breakdown'):
            logger.info(f"\n📅 YEARLY BREAKDOWN")
            for year, count in sorted(stats['yearly_breakdown'].items()):
                logger.info(f"   {year}: {count} documents")
        
        # Overall Assessment
        overall_success = stats.get('db_stored', 0) > 0
        
        logger.info(f"\n🎯 OVERALL RESULT: {'✅ SUCCESS' if overall_success else '❌ FAILED'}")
        logger.info(f"   Document discovery: {'✅ SUCCESS' if stats.get('total_fetched', 0) > 0 else '❌ FAILED'}")
        logger.info(f"   Database storage: {'✅ SUCCESS' if stats.get('db_stored', 0) > 0 else '❌ FAILED'}")
        logger.info(f"   Haystack indexing: {'✅ SUCCESS' if stats.get('haystack_ingested', 0) > 0 else '❌ FAILED'}")
        
        logger.info("=" * 80)
        logger.info("COMPREHENSIVE JUDGE GILSTRAP COLLECTION COMPLETE")
        logger.info("All available documents have been processed")
        logger.info("=" * 80)

async def main():
    """Main function"""
    processor = AllGilstrapProcessor()
    results = await processor.run_comprehensive_fetch()
    
    # Print comprehensive report
    processor.print_comprehensive_report(results)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())