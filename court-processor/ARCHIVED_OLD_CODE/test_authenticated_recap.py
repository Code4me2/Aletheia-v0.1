#!/usr/bin/env python3
"""
Test authenticated RECAP client with real patent cases
"""

import asyncio
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.recap.authenticated_client import AuthenticatedRECAPClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_authenticated_recap():
    """Test authenticated RECAP client with real cases"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return False
    
    logger.info("Starting authenticated RECAP test")
    logger.info(f"PACER Username: {pacer_username}")
    
    # Real patent cases
    test_cases = [
        {
            'docket': '2:2024cv00162',
            'court': 'txed',
            'name': 'Byteweavr, LLC v. Databricks, Inc.',
            'filed': 'March 8, 2024'
        },
        {
            'docket': '2:2024cv00181',
            'court': 'txed',
            'name': 'Cerence Operating Company v. Samsung Electronics',
            'filed': 'March 15, 2024'
        }
    ]
    
    results = {
        'test_date': datetime.now().isoformat(),
        'successful': 0,
        'failed': 0,
        'cases': []
    }
    
    try:
        async with AuthenticatedRECAPClient(cl_token, pacer_username, pacer_password) as client:
            logger.info("✅ Authentication successful - client ready")
            
            for case in test_cases:
                logger.info(f"\n{'='*60}")
                logger.info(f"Testing: {case['name']}")
                logger.info(f"Docket: {case['docket']} in {case['court'].upper()}")
                
                case_result = {
                    'case': case['name'],
                    'docket': case['docket'],
                    'court': case['court']
                }
                
                try:
                    # Step 1: Check if already in RECAP (free)
                    logger.info("Checking RECAP availability...")
                    is_available = await client.check_recap_availability_before_purchase(
                        case['docket'], 
                        case['court']
                    )
                    
                    case_result['in_recap'] = is_available
                    
                    if is_available:
                        logger.info("✅ Already in RECAP - free access!")
                        case_result['status'] = 'already_in_recap'
                        case_result['cost'] = 0.0
                    else:
                        logger.info("📋 Not in RECAP - fetching from PACER...")
                        
                        # Step 2: Fetch from PACER
                        result = await client.fetch_docket_with_monitoring(
                            docket_identifier=case['docket'],
                            court=case['court'],
                            show_parties_and_counsel=True,
                            date_start='2024-01-01',  # Limit to 2024 entries (YYYY-MM-DD format)
                            date_end='2024-12-31'
                        )
                        
                        case_result['status'] = 'fetched_from_pacer'
                        case_result['cost'] = result.get('cost', 0.0)
                        case_result['request_id'] = result.get('id')
                        case_result['docket_id'] = result.get('docket')
                        
                        logger.info(f"✅ Successfully fetched! Cost: ${case_result['cost']:.2f}")
                        
                        # Log some details
                        if result.get('docket'):
                            logger.info(f"   Docket ID: {result['docket']}")
                        if result.get('pacer_case_id'):
                            logger.info(f"   PACER Case ID: {result['pacer_case_id']}")
                    
                    results['successful'] += 1
                    case_result['success'] = True
                    
                except Exception as e:
                    logger.error(f"❌ Failed: {e}")
                    case_result['success'] = False
                    case_result['error'] = str(e)
                    results['failed'] += 1
                
                results['cases'].append(case_result)
            
            # Show estimated costs
            logger.info(f"\n{'='*60}")
            logger.info("Cost Summary:")
            logger.info(f"  Estimated total: ${client.estimated_costs['total']:.2f}")
            logger.info(f"  - Dockets: ${client.estimated_costs['dockets']:.2f}")
            logger.info(f"  - PDFs: ${client.estimated_costs['pdfs']:.2f}")
            
    except Exception as e:
        logger.error(f"Client initialization failed: {e}")
        return False
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"Total cases tested: {len(test_cases)}")
    logger.info(f"✅ Successful: {results['successful']}")
    logger.info(f"❌ Failed: {results['failed']}")
    
    # Show individual results
    logger.info("\nDetailed Results:")
    for case_result in results['cases']:
        logger.info(f"\n{case_result['case']}:")
        logger.info(f"  Status: {case_result.get('status', 'failed')}")
        logger.info(f"  Cost: ${case_result.get('cost', 0):.2f}")
        if case_result.get('error'):
            logger.info(f"  Error: {case_result['error']}")
    
    return results['successful'] > 0


async def test_simple_check():
    """Simple test to just check authentication"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return
    
    logger.info("Testing simple authentication...")
    
    try:
        async with AuthenticatedRECAPClient(cl_token, pacer_username, pacer_password) as client:
            logger.info("✅ Authentication successful!")
            
            # Just check one case availability
            is_available = await client.check_recap_availability_before_purchase(
                '2:2024cv00162', 'txed'
            )
            
            logger.info(f"Byteweavr case in RECAP: {is_available}")
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")


if __name__ == "__main__":
    # Run simple test first
    logger.info("=== SIMPLE AUTHENTICATION TEST ===")
    asyncio.run(test_simple_check())
    
    # Then run full test
    logger.info("\n\n=== FULL INTEGRATION TEST ===")
    success = asyncio.run(test_authenticated_recap())
    
    if success:
        logger.info("\n🎉 Authenticated RECAP integration working!")
    else:
        logger.info("\n❌ Integration test failed")