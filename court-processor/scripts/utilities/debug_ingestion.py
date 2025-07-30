#!/usr/bin/env python3
"""
Debug document ingestion to understand why documents aren't being stored
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from services.document_ingestion_service import DocumentIngestionService

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_ingestion():
    """Debug the ingestion process step by step"""
    
    # Simple configuration for testing
    config = {
        'court_ids': ['ded'],  # Just Delaware district
        'date_after': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'document_types': ['opinions'],
        'max_per_court': 5,  # Small number for testing
        'nature_of_suit': ['830'],  # Just patents
        'search_type': 'r'  # RECAP documents
    }
    
    logger.info("Starting debug ingestion with config:")
    logger.info(json.dumps(config, indent=2))
    
    async with DocumentIngestionService() as service:
        # Enable debug logging
        service.cl_service.logger = logger
        
        logger.info("\n=== STEP 1: Searching for documents ===")
        results = await service.ingest_from_courtlistener(
            court_ids=config['court_ids'],
            date_after=config['date_after'],
            document_types=config['document_types'],
            max_per_court=config['max_per_court'],
            nature_of_suit=config['nature_of_suit'],
            search_type=config['search_type']
        )
        
        logger.info(f"\nIngestion results:")
        logger.info(f"  Success: {results.get('success')}")
        logger.info(f"  Documents ingested: {results.get('documents_ingested')}")
        logger.info(f"  Errors: {results.get('errors')}")
        
        if 'storage_details' in results:
            logger.info(f"\nStorage details:")
            logger.info(f"  Stored: {results['storage_details'].get('stored')}")
            logger.info(f"  Updated: {results['storage_details'].get('updated')}")
            logger.info(f"  Failed: {results['storage_details'].get('failed')}")
            logger.info(f"  Errors: {results['storage_details'].get('errors')}")
        
        stats = service.get_statistics()
        logger.info(f"\nIngestion statistics:")
        logger.info(json.dumps(stats, indent=2))
        
        # Check what's in the database
        logger.info("\n=== STEP 2: Checking database ===")
        from services.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN document_type = 'opinion' THEN 1 END) as opinions,
                   COUNT(CASE WHEN document_type = 'recap' THEN 1 END) as recap,
                   COUNT(CASE WHEN processed = true THEN 1 END) as processed
            FROM court_documents
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)
        
        counts = cursor.fetchone()
        logger.info(f"Recent documents in database:")
        logger.info(f"  Total: {counts[0]}")
        logger.info(f"  Opinions: {counts[1]}")
        logger.info(f"  RECAP: {counts[2]}")
        logger.info(f"  Processed: {counts[3]}")
        
        # Show a sample document
        cursor.execute("""
            SELECT case_number, case_name, document_type, 
                   LENGTH(content) as content_length,
                   metadata->>'source' as source,
                   created_at
            FROM court_documents
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        sample = cursor.fetchone()
        if sample:
            logger.info(f"\nMost recent document:")
            logger.info(f"  Case number: {sample[0]}")
            logger.info(f"  Case name: {sample[1]}")
            logger.info(f"  Type: {sample[2]}")
            logger.info(f"  Content length: {sample[3]}")
            logger.info(f"  Source: {sample[4]}")
            logger.info(f"  Created: {sample[5]}")
        
        cursor.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(debug_ingestion())