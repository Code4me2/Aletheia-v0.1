#!/usr/bin/env python3
"""
Ingest processed court documents from PostgreSQL into Haystack
"""
import os
import sys
import json
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'db'),
    'database': os.environ.get('DB_NAME', 'aletheia'),
    'user': os.environ.get('DB_USER', 'aletheia'),
    'password': os.environ.get('DB_PASSWORD', 'aletheia123')
}

HAYSTACK_URL = os.environ.get('HAYSTACK_URL', 'http://haystack-judicial:8000')

class HaystackIngester:
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.haystack_url = HAYSTACK_URL
        self.stats = {
            'total': 0,
            'ingested': 0,
            'failed': 0,
            'skipped': 0
        }
    
    def check_haystack_health(self):
        """Check if Haystack service is available"""
        try:
            response = requests.get(f"{self.haystack_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Haystack health check failed: {e}")
            return False
    
    def fetch_documents_for_ingestion(self, judge_name=None, limit=None):
        """Fetch documents from PostgreSQL that need to be ingested"""
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                id,
                case_number,
                document_type,
                content,
                metadata,
                created_at,
                updated_at
            FROM court_documents
            WHERE 
                content IS NOT NULL 
                AND content != ''
                AND processed = true
        """
        
        params = []
        
        # Add judge filter if specified
        if judge_name:
            query += " AND metadata->>'judge_name' ILIKE %s"
            params.append(f"%{judge_name}%")
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        documents = cursor.fetchall()
        cursor.close()
        
        return documents
    
    def prepare_document_for_haystack(self, doc):
        """Prepare document in Haystack format"""
        metadata = doc['metadata'] or {}
        
        # Extract key fields from metadata
        case_name = metadata.get('case_name', doc['case_number'])
        court = metadata.get('court_full', metadata.get('court', 'Unknown Court'))
        judge = metadata.get('judge_name', 'Unknown Judge')
        date_filed = metadata.get('date_filed', str(doc['created_at']))
        
        # Extract FLP enhancements
        flp_data = metadata.get('flp_enhancements', {})
        citations = flp_data.get('citations', metadata.get('citations', []))
        citation_count = len(citations) if isinstance(citations, list) else 0
        
        # Build searchable content
        searchable_content = f"""
Case: {case_name}
Court: {court}
Judge: {judge}
Date: {date_filed}
Case Number: {doc['case_number']}

{doc['content']}
"""
        
        # Prepare Haystack document
        haystack_doc = {
            "content": searchable_content,
            "meta": {
                "id": str(doc['id']),
                "case_number": doc['case_number'],
                "case_name": case_name,
                "court": court,
                "judge": judge,
                "date_filed": date_filed,
                "document_type": doc['document_type'],
                "citation_count": citation_count,
                "citations": citations[:10] if citations else [],  # First 10 citations
                "created_at": str(doc['created_at']),
                "updated_at": str(doc['updated_at']),
                "source": "courtlistener",
                "flp_processed": True,
                "doctor_extracted": flp_data.get('doctor_results', {}).get('success', False)
            }
        }
        
        # Add any custom metadata fields
        if metadata.get('precedential_status'):
            haystack_doc['meta']['precedential_status'] = metadata['precedential_status']
        
        if metadata.get('docket_url'):
            haystack_doc['meta']['docket_url'] = metadata['docket_url']
        
        return haystack_doc
    
    def ingest_batch(self, documents):
        """Ingest a batch of documents into Haystack"""
        try:
            # Prepare documents
            haystack_docs = []
            for doc in documents:
                try:
                    haystack_doc = self.prepare_document_for_haystack(doc)
                    haystack_docs.append(haystack_doc)
                except Exception as e:
                    logger.error(f"Failed to prepare document {doc['id']}: {e}")
                    self.stats['failed'] += 1
            
            if not haystack_docs:
                return False
            
            # Send to Haystack ingest endpoint
            payload = {
                "documents": haystack_docs
            }
            
            response = requests.post(
                f"{self.haystack_url}/ingest",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                ingested_count = result.get('documents_written', len(haystack_docs))
                self.stats['ingested'] += ingested_count
                logger.info(f"✅ Ingested batch of {ingested_count} documents")
                return True
            else:
                logger.error(f"Ingest failed with status {response.status_code}: {response.text}")
                self.stats['failed'] += len(haystack_docs)
                return False
                
        except Exception as e:
            logger.error(f"Batch ingest error: {e}")
            self.stats['failed'] += len(documents)
            return False
    
    def ingest_all_documents(self, judge_name=None, batch_size=10):
        """Ingest all documents in batches"""
        logger.info(f"Starting document ingestion to Haystack...")
        
        # Check Haystack health
        if not self.check_haystack_health():
            logger.error("Haystack service is not available!")
            return False
        
        # Fetch documents
        documents = self.fetch_documents_for_ingestion(judge_name)
        self.stats['total'] = len(documents)
        
        logger.info(f"Found {len(documents)} documents to ingest")
        
        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} documents)...")
            
            self.ingest_batch(batch)
            
            # Rate limiting
            time.sleep(0.5)
        
        # Print statistics
        self.print_statistics()
        
        return self.stats['ingested'] > 0
    
    def search_test(self, query):
        """Test search functionality after ingestion"""
        try:
            response = requests.post(
                f"{self.haystack_url}/search",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"\nSearch results for '{query}':")
                for i, doc in enumerate(results.get('documents', [])):
                    logger.info(f"{i+1}. {doc['meta']['case_name']} ({doc['meta']['case_number']})")
                    logger.info(f"   Judge: {doc['meta']['judge']}")
                    logger.info(f"   Score: {doc.get('score', 'N/A')}")
                return True
            else:
                logger.error(f"Search failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Search test error: {e}")
            return False
    
    def print_statistics(self):
        """Print ingestion statistics"""
        logger.info("\n" + "="*60)
        logger.info("HAYSTACK INGESTION COMPLETE")
        logger.info("="*60)
        logger.info(f"Total documents found: {self.stats['total']}")
        logger.info(f"Successfully ingested: {self.stats['ingested']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        success_rate = (self.stats['ingested'] / self.stats['total'] * 100) if self.stats['total'] > 0 else 0
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info("="*60)

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest court documents into Haystack')
    parser.add_argument('--judge', help='Filter by judge name (e.g., "Gilstrap")')
    parser.add_argument('--batch-size', type=int, default=10, help='Batch size for ingestion')
    parser.add_argument('--test-search', help='Test search query after ingestion')
    parser.add_argument('--limit', type=int, help='Limit number of documents to ingest')
    
    args = parser.parse_args()
    
    # Create ingester
    ingester = HaystackIngester()
    
    # Ingest documents
    success = ingester.ingest_all_documents(
        judge_name=args.judge,
        batch_size=args.batch_size
    )
    
    if success and args.test_search:
        logger.info(f"\nTesting search with query: '{args.test_search}'")
        ingester.search_test(args.test_search)
    
    # Close connection
    ingester.conn.close()

if __name__ == "__main__":
    main()