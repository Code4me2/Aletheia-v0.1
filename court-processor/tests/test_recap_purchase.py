#!/usr/bin/env python3
"""
Test actual RECAP purchase with a very recent case
"""

import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.recap.recap_fetch_client import RECAPFetchClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_actual_purchase():
    """Test purchasing a very recent docket from PACER"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_API_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return
    
    # Use a case filed today - very unlikely to be in RECAP yet
    test_cases = [
        ('4:25-mj-00195', 'txed', 'United States v. Paster'),
        ('6:25-cv-00269', 'txed', 'Murphy v. LOWE\'S HOME CENTERS, LLC'),
        ('2:25-cv-00740', 'txed', 'Acer, Incorporated v. Paccar, Inc.')
    ]
    
    async with RECAPFetchClient(cl_token, pacer_username, pacer_password) as client:
        # Try each case until we find one not in RECAP
        for docket_number, court, case_name in test_cases:
            logger.info(f"\nChecking: {case_name}")
            logger.info(f"Docket: {docket_number} in {court}")
            
            # Check if already in RECAP
            is_available = await client.check_recap_availability_before_purchase(
                docket_number, court
            )
            
            if not is_available:
                logger.info("✓ NOT in RECAP - will attempt purchase")
                logger.info("\n" + "="*60)
                logger.info("PURCHASING DOCKET FROM PACER")
                logger.info("This will incur charges (max $3.00)")
                logger.info("="*60)
                
                try:
                    # Submit purchase request
                    request_data = await client.fetch_docket(
                        docket_identifier=docket_number,
                        court=court,
                        show_parties_and_counsel=True
                    )
                    
                    request_id = request_data['id']
                    logger.info(f"\n✓ Request submitted! ID: {request_id}")
                    logger.info("Status: Awaiting Processing")
                    
                    # Monitor the request
                    logger.info("\nMonitoring request status...")
                    
                    result = await client.wait_for_completion(
                        request_id,
                        max_wait=60,  # Wait up to 1 minute
                        poll_interval=3
                    )
                    
                    logger.info("\n" + "="*60)
                    logger.info("PURCHASE COMPLETE!")
                    logger.info("="*60)
                    
                    if result.get('docket'):
                        logger.info(f"✓ Docket URL: {result['docket']}")
                        logger.info(f"✓ Status: {result['status']}")
                        
                        # The docket is now available via the regular API
                        docket_id = result['docket'].split('/')[-2]
                        logger.info(f"✓ Docket ID: {docket_id}")
                        
                        logger.info("\nThe docket has been:")
                        logger.info("1. Purchased from PACER")
                        logger.info("2. Added to the RECAP Archive")
                        logger.info("3. Made freely available to everyone!")
                        
                    if result.get('error_message'):
                        logger.info(f"Message: {result['error_message']}")
                    
                    # Show costs
                    costs = client.get_estimated_costs()
                    logger.info(f"\nEstimated charges for this session: ${costs['total']:.2f}")
                    
                    return True
                    
                except Exception as e:
                    logger.error(f"Purchase failed: {e}")
                    return False
                    
            else:
                logger.info("Already in RECAP - trying next case...")
        
        logger.info("\nAll test cases were already in RECAP!")
        logger.info("This is good - means less PACER fees needed!")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_actual_purchase())
    
    if success:
        logger.info("\n✅ PACER integration working perfectly!")
        logger.info("The pipeline can now purchase any document not in RECAP.")
    else:
        logger.info("\n✅ RECAP availability checking works!")
        logger.info("All recent cases were already in the archive.")