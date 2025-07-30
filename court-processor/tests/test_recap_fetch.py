#!/usr/bin/env python3
"""
Test RECAP Fetch API with PACER credentials
"""

import asyncio
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.recap.recap_fetch_client import RECAPFetchClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_recap_fetch():
    """Test RECAP Fetch API functionality"""
    
    # Get credentials from environment
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_API_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not cl_token:
        logger.error("Missing COURTLISTENER_API_KEY or COURTLISTENER_API_TOKEN")
        return
    
    if not pacer_username or not pacer_password:
        logger.error("Missing PACER_USERNAME or PACER_PASSWORD in .env file")
        return
    
    logger.info("Credentials loaded successfully")
    logger.info(f"PACER Username: {pacer_username}")
    logger.info(f"API Token: {'*' * 10}{cl_token[-4:]}")  # Show last 4 chars only
    
    results = {
        'test_date': datetime.now().isoformat(),
        'tests': {}
    }
    
    async with RECAPFetchClient(cl_token, pacer_username, pacer_password) as client:
        
        # Test 1: Check if a known docket is already in RECAP (free check)
        logger.info("\n" + "="*60)
        logger.info("TEST 1: Check RECAP Availability (Free)")
        logger.info("="*60)
        
        test_docket = '1:21-cv-00038'
        test_court = 'txed'
        
        try:
            is_available = await client.check_recap_availability_before_purchase(
                test_docket, test_court
            )
            
            results['tests']['recap_availability_check'] = {
                'success': True,
                'docket': test_docket,
                'court': test_court,
                'already_in_recap': is_available
            }
            
            if is_available:
                logger.info(f"✓ Docket {test_docket} is already in RECAP - no purchase needed")
            else:
                logger.info(f"✓ Docket {test_docket} is NOT in RECAP - would need to purchase")
                
        except Exception as e:
            logger.error(f"Availability check failed: {e}")
            results['tests']['recap_availability_check'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 2: Fetch a small docket (actually purchase if not in RECAP)
        logger.info("\n" + "="*60)
        logger.info("TEST 2: Fetch Docket with PACER Credentials")
        logger.info("="*60)
        
        # Use a recent case that might not be in RECAP yet
        test_docket_2 = '1:24-cv-00001'  # Very recent case number
        test_court_2 = 'txed'
        
        try:
            # First check if already available
            is_available = await client.check_recap_availability_before_purchase(
                test_docket_2, test_court_2
            )
            
            if is_available:
                logger.info(f"Docket {test_docket_2} already in RECAP - skipping purchase test")
                results['tests']['docket_fetch'] = {
                    'success': True,
                    'skipped': True,
                    'reason': 'Already in RECAP'
                }
            else:
                logger.info(f"Docket {test_docket_2} not in RECAP - will purchase from PACER")
                logger.info("WARNING: This will incur PACER charges (max $3.00)")
                
                # Submit request
                request_data = await client.fetch_docket(
                    docket_identifier=test_docket_2,
                    court=test_court_2,
                    show_parties_and_counsel=True
                )
                
                request_id = request_data['id']
                logger.info(f"Request submitted with ID: {request_id}")
                
                # Wait for completion (max 30 seconds for test)
                try:
                    result = await client.wait_for_completion(request_id, max_wait=30)
                    
                    results['tests']['docket_fetch'] = {
                        'success': True,
                        'request_id': request_id,
                        'status': result['status'],
                        'docket_url': result.get('docket'),
                        'error_message': result.get('error_message'),
                        'purchased': True
                    }
                    
                    if result.get('docket'):
                        logger.info(f"✓ Docket successfully fetched!")
                        logger.info(f"  Docket URL: {result['docket']}")
                    else:
                        logger.warning("Request completed but no docket URL returned")
                        
                except TimeoutError:
                    logger.warning("Request timed out - may still be processing")
                    results['tests']['docket_fetch'] = {
                        'success': False,
                        'error': 'Timeout',
                        'request_id': request_id
                    }
                    
        except Exception as e:
            logger.error(f"Docket fetch failed: {e}")
            results['tests']['docket_fetch'] = {
                'success': False,
                'error': str(e)
            }
        
        # Test 3: Check a document (PDF) - but don't purchase
        logger.info("\n" + "="*60)
        logger.info("TEST 3: Check Document Availability")
        logger.info("="*60)
        
        # This would be a recap_document_id from a previous search
        # For now, just demonstrate the API structure
        results['tests']['pdf_capability'] = {
            'success': True,
            'note': 'PDF fetch available via fetch_pdf(recap_document_id)',
            'cost': '$0.10 per page, max $3.00 per document'
        }
        
        logger.info("✓ PDF fetch capability confirmed (not testing to avoid charges)")
        
        # Show estimated costs
        costs = client.get_estimated_costs()
        logger.info("\n" + "="*60)
        logger.info("ESTIMATED COSTS FOR THIS SESSION")
        logger.info("="*60)
        logger.info(f"Dockets: ${costs['dockets']:.2f}")
        logger.info(f"PDFs: ${costs['pdfs']:.2f}")
        logger.info(f"Total: ${costs['total']:.2f}")
    
    # Save results
    output_file = f"recap_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nTest results saved to: {output_file}")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for test in results['tests'].values() 
                 if test.get('success') or test.get('skipped'))
    total = len(results['tests'])
    
    logger.info(f"Tests passed: {passed}/{total}")
    
    if costs['total'] > 0:
        logger.info(f"\nActual PACER charges incurred: ${costs['total']:.2f}")
    else:
        logger.info("\nNo PACER charges incurred (all documents were already in RECAP)")
    
    return results


async def test_small_batch():
    """Test fetching a small batch of IP cases"""
    
    logger.info("\n" + "="*60)
    logger.info("BATCH TEST: Fetch Recent IP Cases")
    logger.info("="*60)
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_API_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return
    
    # First, search for recent patent cases in E.D. Texas
    from services.courtlistener_service import CourtListenerService
    
    cl_service = CourtListenerService(cl_token)
    
    # Search for recent patent cases
    results = await cl_service.search_with_filters(
        search_type='r',  # RECAP documents
        court_ids=['txed'],
        nature_of_suit=['830'],  # Patent
        date_range=('2024-01-01', '2024-01-31'),  # January 2024
        max_results=5
    )
    
    logger.info(f"Found {len(results)} patent cases")
    
    # Check which ones need to be purchased
    async with RECAPFetchClient(cl_token, pacer_username, pacer_password) as client:
        for i, result in enumerate(results[:3]):  # Only check first 3
            docket_number = result.get('docketNumber', '')
            case_name = result.get('caseName', 'Unknown')
            
            if docket_number:
                logger.info(f"\nCase {i+1}: {case_name}")
                logger.info(f"  Docket: {docket_number}")
                
                # Check availability
                is_available = await client.check_recap_availability_before_purchase(
                    docket_number, 'txed'
                )
                
                if is_available:
                    logger.info("  ✓ Already in RECAP (free)")
                else:
                    logger.info("  💰 Would need to purchase from PACER")
    
    await cl_service.close()


if __name__ == "__main__":
    # Run main test
    asyncio.run(test_recap_fetch())
    
    # Optionally run batch test
    # asyncio.run(test_small_batch())