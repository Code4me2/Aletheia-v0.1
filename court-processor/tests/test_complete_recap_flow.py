#!/usr/bin/env python3
"""
Test the complete RECAP flow with PDF downloads
"""

import asyncio
import os
import logging
import json
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


async def test_complete_recap_flow():
    """Test the complete RECAP flow with PDF downloads"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return False
    
    # Test cases
    test_cases = [
        {
            'docket': '2:2024cv00162',
            'court': 'txed',
            'name': 'Byteweavr, LLC v. Databricks, Inc.',
            'max_pdfs': 5  # Limit PDFs for testing
        },
        {
            'docket': '2:2024cv00181',
            'court': 'txed',
            'name': 'Cerence Operating Company v. Samsung Electronics',
            'max_pdfs': 5
        }
    ]
    
    all_results = {
        'test_date': datetime.now().isoformat(),
        'cases': []
    }
    
    try:
        async with AuthenticatedRECAPClient(cl_token, pacer_username, pacer_password) as client:
            logger.info("✅ PACER authentication successful")
            
            for case in test_cases:
                logger.info(f"\n{'='*60}")
                logger.info(f"Testing: {case['name']}")
                logger.info(f"Docket: {case['docket']} in {case['court'].upper()}")
                logger.info(f"{'='*60}")
                
                # Run the complete flow
                result = await client.fetch_docket_and_pdfs(
                    docket_number=case['docket'],
                    court=case['court'],
                    max_pdfs=case['max_pdfs'],
                    date_start='2024-01-01',
                    date_end='2024-12-31'
                )
                
                # Log results
                if result.get('success'):
                    logger.info(f"✅ Success!")
                    logger.info(f"  Case Name: {result.get('case_name')}")
                    logger.info(f"  Docket ID: {result.get('docket_id')}")
                    logger.info(f"  Already in RECAP: {result.get('in_recap')}")
                    logger.info(f"  Purchased: {result.get('purchased')}")
                    if result.get('purchased'):
                        logger.info(f"  Cost: ${result.get('purchase_cost', 0):.2f}")
                    logger.info(f"  PDFs Downloaded: {len(result.get('pdfs', []))}")
                    
                    # Show first few PDFs
                    for i, pdf in enumerate(result.get('pdfs', [])[:3]):
                        logger.info(f"\n  PDF {i+1}:")
                        logger.info(f"    File: {pdf.get('filename')}")
                        logger.info(f"    Description: {pdf.get('short_description')}")
                        logger.info(f"    Pages: {pdf.get('page_count')}")
                        logger.info(f"    Size: {pdf.get('size', 0):,} bytes")
                else:
                    logger.error(f"❌ Failed: {result.get('error')}")
                
                # Add to results
                all_results['cases'].append({
                    'case': case['name'],
                    'docket': case['docket'],
                    'result': result
                })
                
                # Brief pause between cases
                await asyncio.sleep(2)
            
            # Show cost summary
            total_cost = sum(
                case['result'].get('purchase_cost', 0) 
                for case in all_results['cases'] 
                if case['result'].get('purchased')
            )
            total_pdfs = sum(
                len(case['result'].get('pdfs', []))
                for case in all_results['cases']
            )
            
            logger.info(f"\n{'='*60}")
            logger.info("SUMMARY")
            logger.info(f"{'='*60}")
            logger.info(f"Total cases processed: {len(test_cases)}")
            logger.info(f"Total PDFs downloaded: {total_pdfs}")
            logger.info(f"Total PACER costs: ${total_cost:.2f}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    # Save detailed results
    results_file = f"complete_recap_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"\n📄 Detailed results saved to: {results_file}")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_complete_recap_flow())
    if success:
        logger.info("\n🎉 Complete RECAP flow test successful!")
    else:
        logger.info("\n❌ Test failed")