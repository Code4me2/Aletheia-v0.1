#!/usr/bin/env python3
"""
Debug the broad search to see what's being returned
"""

import asyncio
import logging
from datetime import datetime, timedelta
from services.courtlistener_service import CourtListenerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def debug_broad_search():
    """Check what the search actually returns"""
    
    cl_service = CourtListenerService()
    
    # Try searching for opinions from specific courts
    test_courts = ['txed', 'cafc', 'nysd', 'ilnd']
    
    for court in test_courts:
        logger.info(f"\n{'='*60}")
        logger.info(f"Searching {court} for opinions...")
        logger.info(f"{'='*60}")
        
        try:
            # Search for recent opinions
            results = await cl_service.search_with_filters(
                search_type='o',  # Opinions
                court_ids=[court],
                date_range=((datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'), 
                           datetime.now().strftime('%Y-%m-%d')),
                max_results=5
            )
            
            logger.info(f"Found {len(results)} results from {court}")
            
            if results:
                # Check first result
                first = results[0]
                logger.info(f"\nFirst result fields:")
                for key in sorted(first.keys()):
                    value = first[key]
                    if isinstance(value, str) and len(value) > 100:
                        value = value[:100] + "..."
                    logger.info(f"  {key}: {value}")
                
                # Check for text fields
                text_fields = ['text', 'plain_text', 'html', 'snippet', 'content']
                logger.info(f"\nText content check:")
                for field in text_fields:
                    if field in first and first[field]:
                        logger.info(f"  ✓ {field}: {len(first[field])} chars")
                    else:
                        logger.info(f"  ✗ {field}: not found or empty")
                        
        except Exception as e:
            logger.error(f"Error searching {court}: {e}")
    
    # Also try a nature of suit search
    logger.info(f"\n{'='*60}")
    logger.info(f"Searching for patent cases (830) across all courts...")
    logger.info(f"{'='*60}")
    
    patent_results = await cl_service.search_with_filters(
        search_type='o',
        nature_of_suit=['830'],
        date_range=((datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'), 
                   datetime.now().strftime('%Y-%m-%d')),
        max_results=10
    )
    
    if patent_results:
        courts_found = {}
        for result in patent_results:
            court = result.get('court', result.get('court_id', 'unknown'))
            courts_found[court] = courts_found.get(court, 0) + 1
        
        logger.info(f"Found {len(patent_results)} patent opinions from these courts:")
        for court, count in sorted(courts_found.items()):
            logger.info(f"  {court}: {count} opinions")
    
    await cl_service.close()


if __name__ == "__main__":
    asyncio.run(debug_broad_search())