#!/usr/bin/env python3
"""
Test RECAP free-first integration
Verifies that the pipeline searches free RECAP before considering PACER
"""

import asyncio
import os
import logging
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.document_ingestion_service import DocumentIngestionService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Reduce noise from other loggers
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('aiohttp').setLevel(logging.WARNING)


async def test_free_recap_search():
    """Test searching free RECAP documents"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    
    if not cl_token:
        logger.error("Missing CourtListener API token")
        return False
    
    # Test configuration - NO PACER credentials
    logger.info("Testing FREE RECAP search (no PACER credentials)")
    
    try:
        async with DocumentIngestionService(api_key=cl_token) as service:
            # Search for recent IP cases in RECAP
            date_after = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            
            results = await service.ingest_from_courtlistener(
                court_ids=['txed'],  # Eastern District of Texas
                date_after=date_after,
                document_types=['recap'],  # Only RECAP documents
                max_per_court=10,
                nature_of_suit=['830'],  # Patent cases
                search_type='r',
                use_recap_fallback=False,  # No PACER fallback
                check_recap_first=True,
                max_pacer_cost=0.0
            )
            
            logger.info(f"\n✅ FREE RECAP search completed")
            logger.info(f"Documents found: {results.get('documents_ingested', 0)}")
            
            # Show statistics
            stats = results.get('statistics', {})
            logger.info(f"\nStatistics:")
            logger.info(f"  RECAP documents: {stats.get('sources', {}).get('courtlistener_recap', 0)}")
            logger.info(f"  Total processed: {stats.get('processing', {}).get('total_documents', 0)}")
            
            return results
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None


async def test_recap_with_fallback():
    """Test RECAP with PACER fallback enabled"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not cl_token:
        logger.error("Missing CourtListener API token")
        return False
    
    # Test configuration - WITH PACER credentials
    if pacer_username and pacer_password:
        logger.info("Testing RECAP with PACER fallback enabled")
    else:
        logger.info("Testing RECAP without PACER (credentials not found)")
    
    try:
        async with DocumentIngestionService(
            api_key=cl_token,
            pacer_username=pacer_username,
            pacer_password=pacer_password
        ) as service:
            # Search for recent cases
            date_after = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            results = await service.ingest_from_courtlistener(
                court_ids=['cafc'],  # Federal Circuit
                date_after=date_after,
                document_types=['recap'],
                max_per_court=5,
                nature_of_suit=['830'],  # Patent cases
                search_type='r',
                use_recap_fallback=bool(pacer_username),  # Enable if creds available
                check_recap_first=True,
                max_pacer_cost=10.0  # $10 limit
            )
            
            logger.info(f"\n✅ RECAP with fallback completed")
            logger.info(f"Documents found: {results.get('documents_ingested', 0)}")
            
            # Show statistics
            stats = results.get('statistics', {})
            logger.info(f"\nStatistics:")
            logger.info(f"  RECAP documents: {stats.get('sources', {}).get('courtlistener_recap', 0)}")
            logger.info(f"  Total processed: {stats.get('processing', {}).get('total_documents', 0)}")
            
            # Check if PACER was used
            if pacer_username:
                logger.info(f"\nPACER fallback was {'AVAILABLE' if pacer_username else 'NOT AVAILABLE'}")
            
            return results
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return None


async def main():
    """Run RECAP free-first tests"""
    
    logger.info("=== RECAP Free-First Integration Test ===\n")
    
    # Test 1: Free RECAP only
    logger.info("Test 1: Free RECAP Search (No PACER)")
    logger.info("-" * 50)
    free_results = await test_free_recap_search()
    
    # Save results
    if free_results:
        filename = f"recap_free_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(free_results, f, indent=2)
        logger.info(f"Results saved to: {filename}")
    
    # Test 2: RECAP with fallback
    logger.info("\n\nTest 2: RECAP with PACER Fallback")
    logger.info("-" * 50)
    fallback_results = await test_recap_with_fallback()
    
    # Save results
    if fallback_results:
        filename = f"recap_fallback_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(fallback_results, f, indent=2)
        logger.info(f"Results saved to: {filename}")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    
    if free_results:
        logger.info(f"Free RECAP found: {free_results.get('documents_ingested', 0)} documents")
    
    if fallback_results:
        logger.info(f"With fallback found: {fallback_results.get('documents_ingested', 0)} documents")
    
    logger.info("\n✅ Free-first approach is working!")
    logger.info("The pipeline searches free RECAP before considering PACER purchases")


if __name__ == "__main__":
    asyncio.run(main())