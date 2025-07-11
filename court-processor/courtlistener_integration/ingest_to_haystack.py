#!/usr/bin/env python3
"""
Ingest CourtListener data from PostgreSQL to Haystack
Based on existing test patterns in test_enhanced_ingest.py
"""

import os
import sys
import json
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
HAYSTACK_URL = os.environ.get('HAYSTACK_URL', 'http://localhost:8000')
BATCH_SIZE = 10  # Process documents in batches

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CourtListenerHaystackIngester:
    """Ingest CourtListener data into Haystack following existing patterns"""
    
    def __init__(self, database_url: str, haystack_url: str):
        self.db_url = database_url
        self.haystack_url = haystack_url
        self.workflow_id = f"courtlistener_ingest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
    def connect_db(self):
        """Connect to PostgreSQL"""
        return psycopg2.connect(self.db_url)
    
    def get_unindexed_opinions(self, limit: int = BATCH_SIZE) -> List[Dict]:
        """Fetch unindexed CourtListener opinions from PostgreSQL"""
        conn = self.connect_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        
        try:
            # Query for opinions with text that haven't been indexed
            cursor.execute("""
                SELECT 
                    o.id,
                    o.plain_text,
                    o.html,
                    o.author_str,
                    o.date_created,
                    o.type as opinion_type,
                    o.absolute_url,
                    d.case_name,
                    d.docket_number,
                    d.court_id,
                    d.nature_of_suit,
                    d.is_patent_case,
                    d.date_filed,
                    d.assigned_to_str
                FROM court_data.cl_opinions o
                LEFT JOIN court_data.cl_dockets d ON o.docket_id = d.id
                WHERE o.vector_indexed = false 
                AND (o.plain_text IS NOT NULL OR o.html IS NOT NULL)
                ORDER BY o.date_created DESC
                LIMIT %s
            """, (limit,))
            
            opinions = []
            for row in cursor:
                opinions.append(dict(row))
            
            return opinions
            
        finally:
            cursor.close()
            conn.close()
    
    def format_opinion_for_haystack(self, opinion: Dict) -> Dict:
        """Format a CourtListener opinion for Haystack ingestion"""
        # Get text content (prefer plain text over HTML)
        content = opinion['plain_text'] or opinion['html'] or ""
        
        # Build comprehensive metadata
        metadata = {
            "source": "courtlistener",
            "court": opinion['court_id'] or "unknown",
            "case_name": opinion['case_name'] or "Unknown Case",
            "docket_number": opinion['docket_number'] or "",
            "date_created": opinion['date_created'].isoformat() if opinion['date_created'] else "",
            "date_filed": opinion['date_filed'].isoformat() if opinion['date_filed'] else "",
            "author": opinion['author_str'] or "",
            "opinion_type": opinion['opinion_type'] or "",
            "assigned_to": opinion['assigned_to_str'] or "",
            "nature_of_suit": opinion['nature_of_suit'] or "",
            "is_patent_case": opinion['is_patent_case'] or False,
            "url": opinion['absolute_url'] or "",
            "opinion_id": opinion['id']
        }
        
        # Create document in the format expected by Haystack
        # Following the pattern from test_enhanced_ingest.py
        document = {
            "content": content,
            "metadata": metadata,
            "document_type": "court_opinion",
            "document_id": f"cl_opinion_{opinion['id']}",
            "parent_id": None,  # No hierarchy for individual opinions
            "hierarchy_level": 0,  # Top level
            "workflow_id": self.workflow_id,
            "is_final_summary": False,
            "summary_type": None
        }
        
        return document
    
    def ingest_to_haystack(self, documents: List[Dict]) -> bool:
        """Send documents to Haystack /ingest endpoint"""
        try:
            # Following the pattern from test scripts
            response = requests.post(
                f"{self.haystack_url}/ingest",
                json=documents,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Successfully ingested {result.get('documents_processed', len(documents))} documents")
                logger.info(f"Document IDs: {result.get('document_ids', [])}")
                return True
            else:
                logger.error(f"Ingestion failed with status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending documents to Haystack: {e}")
            return False
    
    def mark_opinions_as_indexed(self, opinion_ids: List[int]):
        """Update vector_indexed flag in PostgreSQL"""
        conn = self.connect_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE court_data.cl_opinions 
                SET vector_indexed = true, updated_at = CURRENT_TIMESTAMP
                WHERE id = ANY(%s)
            """, (opinion_ids,))
            
            conn.commit()
            logger.info(f"Marked {cursor.rowcount} opinions as indexed")
            
        finally:
            cursor.close()
            conn.close()
    
    def run_ingestion(self, total_limit: int = None):
        """Run the complete ingestion process"""
        logger.info(f"Starting CourtListener to Haystack ingestion")
        logger.info(f"Workflow ID: {self.workflow_id}")
        logger.info(f"Haystack URL: {self.haystack_url}")
        
        total_processed = 0
        total_errors = 0
        
        while True:
            # Get batch of unindexed opinions
            opinions = self.get_unindexed_opinions(BATCH_SIZE)
            
            if not opinions:
                logger.info("No more unindexed opinions to process")
                break
            
            logger.info(f"Processing batch of {len(opinions)} opinions")
            
            # Format for Haystack
            documents = []
            opinion_ids = []
            
            for opinion in opinions:
                try:
                    doc = self.format_opinion_for_haystack(opinion)
                    documents.append(doc)
                    opinion_ids.append(opinion['id'])
                except Exception as e:
                    logger.error(f"Error formatting opinion {opinion['id']}: {e}")
                    total_errors += 1
            
            if documents:
                # Send to Haystack
                if self.ingest_to_haystack(documents):
                    # Mark as indexed in PostgreSQL
                    self.mark_opinions_as_indexed(opinion_ids)
                    total_processed += len(documents)
                else:
                    total_errors += len(documents)
                    logger.error("Failed to ingest batch, stopping")
                    break
            
            # Check if we've reached the limit
            if total_limit and total_processed >= total_limit:
                logger.info(f"Reached specified limit of {total_limit} documents")
                break
        
        # Summary
        logger.info("=" * 70)
        logger.info("INGESTION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total documents processed: {total_processed}")
        logger.info(f"Total errors: {total_errors}")
        logger.info(f"Workflow ID: {self.workflow_id}")
        
        return total_processed, total_errors
    
    def test_connection(self):
        """Test connections to both PostgreSQL and Haystack"""
        # Test PostgreSQL
        try:
            conn = self.connect_db()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM court_data.cl_opinions WHERE plain_text IS NOT NULL")
            count = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            logger.info(f"✓ PostgreSQL connection OK - Found {count} opinions with text")
        except Exception as e:
            logger.error(f"✗ PostgreSQL connection failed: {e}")
            return False
        
        # Test Haystack
        try:
            response = requests.get(f"{self.haystack_url}/health")
            if response.status_code == 200:
                logger.info("✓ Haystack connection OK")
            else:
                logger.error(f"✗ Haystack health check failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"✗ Haystack connection failed: {e}")
            return False
        
        return True

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Ingest CourtListener data to Haystack')
    parser.add_argument('--limit', type=int, help='Maximum number of documents to ingest')
    parser.add_argument('--test', action='store_true', help='Test connections only')
    parser.add_argument('--haystack-url', default='http://localhost:8000', 
                       help='Haystack service URL (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Override Haystack URL if provided
    haystack_url = args.haystack_url or HAYSTACK_URL
    
    # Create ingester
    ingester = CourtListenerHaystackIngester(DATABASE_URL, haystack_url)
    
    # Test mode
    if args.test:
        logger.info("Running connection tests...")
        if ingester.test_connection():
            logger.info("All connections successful!")
        else:
            logger.error("Connection test failed")
            sys.exit(1)
        return
    
    # Run ingestion
    logger.info("Starting ingestion process...")
    processed, errors = ingester.run_ingestion(args.limit)
    
    # Exit with error code if there were failures
    sys.exit(1 if errors > 0 else 0)

if __name__ == "__main__":
    main()