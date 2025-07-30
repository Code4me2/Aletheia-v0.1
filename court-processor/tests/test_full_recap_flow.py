#!/usr/bin/env python3
"""
Test the complete RECAP flow: purchase → fetch docket → download PDFs
"""

import asyncio
import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
import sys
import aiohttp
from typing import Optional

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


async def search_for_docket(cl_token: str, docket_number: str, court: str) -> Optional[int]:
    """
    Search for a docket by number and court
    
    Returns:
        Docket ID if found, None otherwise
    """
    search_url = "https://www.courtlistener.com/api/rest/v4/search/"
    headers = {'Authorization': f'Token {cl_token}'}
    params = {
        'type': 'r',  # RECAP search
        'q': f'docketNumber:"{docket_number}" AND court_id:{court}'
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.get(search_url, params=params, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('count', 0) > 0 and data.get('results'):
                    # Return the first matching docket ID
                    result = data['results'][0]
                    return result.get('docket_id')
    return None


async def fetch_docket_details(cl_token: str, docket_id: int) -> dict:
    """
    Fetch full docket details from CourtListener API
    
    Args:
        cl_token: CourtListener API token
        docket_id: Docket ID from RECAP fetch response
        
    Returns:
        Full docket data including document URLs
    """
    url = f"https://www.courtlistener.com/api/rest/v4/dockets/{docket_id}/"
    headers = {'Authorization': f'Token {cl_token}'}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                text = await response.text()
                raise Exception(f"Failed to fetch docket details ({response.status}): {text}")


async def download_pdf(session: aiohttp.ClientSession, pdf_url: str, filename: str):
    """Download a PDF file"""
    logger.info(f"Downloading PDF: {filename}")
    
    async with session.get(pdf_url) as response:
        if response.status == 200:
            content = await response.read()
            
            # Save to file
            os.makedirs('test_pdfs', exist_ok=True)
            filepath = os.path.join('test_pdfs', filename)
            
            with open(filepath, 'wb') as f:
                f.write(content)
            
            logger.info(f"✅ Saved PDF: {filepath} ({len(content):,} bytes)")
            return filepath
        else:
            logger.error(f"Failed to download PDF ({response.status})")
            return None


async def test_full_recap_flow():
    """Test the complete RECAP flow"""
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return False
    
    # Test case
    test_case = {
        'docket': '2:2024cv00162',
        'court': 'txed',
        'name': 'Byteweavr, LLC v. Databricks, Inc.'
    }
    
    results = {
        'test_date': datetime.now().isoformat(),
        'case': test_case,
        'steps': []
    }
    
    try:
        async with AuthenticatedRECAPClient(cl_token, pacer_username, pacer_password) as client:
            logger.info("✅ PACER authentication successful")
            
            # Step 1: Check RECAP availability
            logger.info("\n=== Step 1: Check RECAP Availability ===")
            is_available = await client.check_recap_availability_before_purchase(
                test_case['docket'], 
                test_case['court']
            )
            
            results['steps'].append({
                'step': 'check_availability',
                'result': 'already_in_recap' if is_available else 'need_to_purchase'
            })
            
            # Step 2: Fetch from PACER (or skip if available)
            logger.info("\n=== Step 2: Fetch Docket ===")
            
            if is_available:
                logger.info("Already in RECAP - searching for existing docket")
                # Search for existing docket
                # For now, we'll still fetch to demonstrate the flow
            
            result = await client.fetch_docket_with_monitoring(
                docket_identifier=test_case['docket'],
                court=test_case['court'],
                show_parties_and_counsel=True,
                date_start='2024-01-01',
                date_end='2024-12-31'
            )
            
            # Log the full response for debugging
            logger.info(f"Full RECAP response: {json.dumps(result, indent=2)}")
            
            docket_id = result.get('docket')
            if not docket_id:
                raise Exception("No docket ID in response")
            
            # Check if it's a URL or just an ID
            if isinstance(docket_id, str) and docket_id.startswith('http'):
                # Extract ID from URL
                import re
                match = re.search(r'/dockets/(\d+)/', docket_id)
                if match:
                    docket_id = int(match.group(1))
                    logger.info(f"Extracted docket ID from URL: {docket_id}")
            
            logger.info(f"✅ Got docket ID: {docket_id}")
            
            results['steps'].append({
                'step': 'fetch_docket',
                'docket_id': docket_id,
                'request_id': result.get('id'),
                'cost': result.get('cost', 0.0)
            })
            
            # Step 3: Fetch full docket details from CourtListener
            logger.info("\n=== Step 3: Fetch Docket Details ===")
            
            # First try the returned docket ID
            docket_data = await fetch_docket_details(cl_token, docket_id)
            
            # Check if this is the right case
            fetched_docket_number = docket_data.get('docket_number', '')
            if test_case['docket'] not in fetched_docket_number:
                logger.warning(f"Docket mismatch! Expected {test_case['docket']}, got {fetched_docket_number}")
                logger.info("Searching for correct docket...")
                
                # Wait a bit for data to propagate
                await asyncio.sleep(2)
                
                # Search for the correct docket
                correct_docket_id = await search_for_docket(cl_token, test_case['docket'], test_case['court'])
                if correct_docket_id:
                    logger.info(f"Found correct docket ID: {correct_docket_id}")
                    docket_data = await fetch_docket_details(cl_token, correct_docket_id)
                else:
                    logger.error("Could not find correct docket through search")
            
            logger.info(f"Docket: {docket_data.get('case_name')}")
            logger.info(f"Docket Number: {docket_data.get('docket_number')}")
            logger.info(f"Court: {docket_data.get('court')}")
            logger.info(f"Date Filed: {docket_data.get('date_filed')}")
            
            # Extract document information
            entries = docket_data.get('docket_entries', [])
            logger.info(f"Total docket entries: {len(entries)}")
            
            # Count available documents
            total_docs = 0
            docs_with_pdfs = 0
            
            for entry in entries:
                for doc in entry.get('recap_documents', []):
                    total_docs += 1
                    if doc.get('filepath_local'):
                        docs_with_pdfs += 1
            
            logger.info(f"Total documents: {total_docs}")
            logger.info(f"Documents with PDFs: {docs_with_pdfs}")
            
            results['steps'].append({
                'step': 'fetch_details',
                'case_name': docket_data.get('case_name'),
                'total_entries': len(entries),
                'total_documents': total_docs,
                'documents_with_pdfs': docs_with_pdfs
            })
            
            # Step 4: Download first few PDFs as examples
            logger.info("\n=== Step 4: Download Sample PDFs ===")
            
            async with aiohttp.ClientSession() as session:
                downloaded = 0
                max_downloads = 3
                
                for entry in entries[:10]:  # Check first 10 entries
                    if downloaded >= max_downloads:
                        break
                        
                    entry_num = entry.get('entry_number', 'unknown')
                    
                    for doc in entry.get('recap_documents', []):
                        if downloaded >= max_downloads:
                            break
                            
                        # Check if PDF is available
                        filepath = doc.get('filepath_local')
                        if filepath:
                            # Build full URL
                            pdf_url = f"https://www.courtlistener.com{filepath}"
                            
                            # Create filename
                            doc_num = doc.get('document_number', '')
                            desc = doc.get('short_description', 'document')[:50]
                            desc = desc.replace('/', '-').replace(' ', '_')
                            filename = f"entry_{entry_num}_doc_{doc_num}_{desc}.pdf"
                            
                            # Download
                            filepath = await download_pdf(session, pdf_url, filename)
                            if filepath:
                                downloaded += 1
                                
                                results['steps'].append({
                                    'step': 'download_pdf',
                                    'entry_number': entry_num,
                                    'document_number': doc_num,
                                    'description': doc.get('description', ''),
                                    'filepath': filepath,
                                    'page_count': doc.get('page_count')
                                })
            
            logger.info(f"\n✅ Downloaded {downloaded} sample PDFs")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        results['error'] = str(e)
        return False
    
    # Save results
    results_file = f"recap_flow_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n📄 Full results saved to: {results_file}")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    for step in results['steps']:
        logger.info(f"{step['step']}: {step}")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_full_recap_flow())
    if success:
        logger.info("\n🎉 Full RECAP flow test completed successfully!")
    else:
        logger.info("\n❌ Test failed")