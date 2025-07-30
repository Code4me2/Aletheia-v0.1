#!/usr/bin/env python3
"""
Debug RECAP search to find documents
"""

import asyncio
import os
import logging
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_recap_search():
    """Test different RECAP search parameters"""
    
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    if not cl_token:
        logger.error("Missing CourtListener API token")
        return
    
    headers = {'Authorization': f'Token {cl_token}'}
    search_url = "https://www.courtlistener.com/api/rest/v4/search/"
    
    # Test different search parameters
    test_searches = [
        {
            'name': 'Patent cases in TXED (type=r)',
            'params': {
                'type': 'r',
                'q': 'court:txed AND nature_of_suit:830',
                'order_by': 'score desc',
                'page_size': 5
            }
        },
        {
            'name': 'Recent RECAP documents (type=rd)',
            'params': {
                'type': 'rd',  # Flat document list
                'q': 'court:txed',
                'date_filed__gte': '2024-01-01',
                'order_by': 'score desc',
                'page_size': 5
            }
        },
        {
            'name': 'Any TXED RECAP dockets',
            'params': {
                'type': 'r',
                'q': 'court:txed',
                'order_by': 'score desc',
                'page_size': 5
            }
        },
        {
            'name': 'CAFC Patent cases',
            'params': {
                'type': 'r',
                'q': 'court:cafc AND nature_of_suit:830',
                'order_by': 'score desc',
                'page_size': 5
            }
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for search in test_searches:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {search['name']}")
            logger.info(f"Params: {search['params']}")
            
            try:
                async with session.get(search_url, params=search['params'], headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        count = data.get('count', 0)
                        results = data.get('results', [])
                        
                        logger.info(f"✅ Success! Total count: {count}, Retrieved: {len(results)}")
                        
                        # Show first result structure
                        if results:
                            first = results[0]
                            logger.info(f"\nFirst result preview:")
                            if search['params']['type'] == 'r':
                                # Docket result
                                logger.info(f"  Docket ID: {first.get('docket_id')}")
                                logger.info(f"  Case: {first.get('case_name')}")
                                logger.info(f"  Court: {first.get('court')}")
                                logger.info(f"  Filed: {first.get('date_filed')}")
                                recap_docs = first.get('recap_documents', [])
                                logger.info(f"  Documents shown: {len(recap_docs)}")
                                logger.info(f"  More docs: {first.get('more_docs', False)}")
                                
                                # Show nested documents
                                for i, doc in enumerate(recap_docs[:2]):
                                    logger.info(f"\n  Document {i+1}:")
                                    logger.info(f"    ID: {doc.get('id')}")
                                    logger.info(f"    Description: {doc.get('description')}")
                                    logger.info(f"    Available: {doc.get('is_available')}")
                                    logger.info(f"    Has text: {'plain_text' in doc}")
                            else:
                                # Document result (type=rd)
                                logger.info(f"  Doc ID: {first.get('id')}")
                                logger.info(f"  Description: {first.get('description')}")
                                logger.info(f"  Docket ID: {first.get('docket_id')}")
                                logger.info(f"  Available: {first.get('is_available')}")
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Failed ({response.status}): {error_text}")
                        
            except Exception as e:
                logger.error(f"❌ Error: {e}")
    
    logger.info(f"\n{'='*60}")
    logger.info("Search test complete!")


if __name__ == "__main__":
    asyncio.run(test_recap_search())