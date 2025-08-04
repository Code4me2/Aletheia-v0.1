#!/usr/bin/env python3
"""
Debug API field structure to understand what fields are actually returned
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from services.courtlistener_service import CourtListenerService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def debug_api_fields():
    """Debug what fields are actually returned by the API"""
    
    cl_service = CourtListenerService()
    
    # Test 1: RECAP search results
    logger.info("\n=== RECAP Search Results ===")
    results = await cl_service.search_with_filters(
        search_type='r',  # RECAP
        court_ids=['ded'],
        nature_of_suit=['830'],  # Patent
        date_range=((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                   datetime.now().strftime('%Y-%m-%d')),
        max_results=2
    )
    
    if results:
        logger.info(f"Found {len(results)} RECAP results")
        for i, result in enumerate(results):
            logger.info(f"\nRECAP Result {i+1} fields:")
            # Show all fields
            for key in sorted(result.keys()):
                value = result[key]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                logger.info(f"  {key}: {value}")
            
            # Check specific text fields
            logger.info("\nText content fields:")
            text_fields = ['snippet', 'text', 'short_description', 'description', 
                          'plain_text', 'html', 'content']
            for field in text_fields:
                if field in result and result[field]:
                    logger.info(f"  ✓ {field}: {len(result[field])} chars")
    
    # Test 2: Opinion results 
    logger.info("\n\n=== Opinion Search Results ===")
    opinion_results = await cl_service.search_with_filters(
        search_type='o',  # Opinions
        court_ids=['ded'],
        date_range=((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                   datetime.now().strftime('%Y-%m-%d')),
        max_results=2
    )
    
    if opinion_results:
        logger.info(f"Found {len(opinion_results)} opinion results")
        for i, result in enumerate(opinion_results):
            logger.info(f"\nOpinion Result {i+1} fields:")
            for key in sorted(result.keys()):
                value = result[key]
                if isinstance(value, str) and len(value) > 100:
                    value = value[:100] + "..."
                logger.info(f"  {key}: {value}")
    
    await cl_service.close()


if __name__ == "__main__":
    asyncio.run(debug_api_fields())