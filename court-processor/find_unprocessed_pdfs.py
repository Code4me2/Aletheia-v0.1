#!/usr/bin/env python3
"""
Find CourtListener documents that have PDFs but no extracted text
"""

import asyncio
import os
import logging
from services.courtlistener_service import CourtListenerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'


async def find_unprocessed_pdfs():
    """Search for documents with PDFs but no plain text"""
    
    cl_service = CourtListenerService()
    
    logger.info("\n" + "="*80)
    logger.info("SEARCHING FOR UNPROCESSED PDFS")
    logger.info("="*80)
    
    # Strategy 1: Look for older opinions that might not have plain_text
    logger.info("\n1. Checking older opinions (pre-2020)...")
    
    older_courts = ['scotus', 'ca9', 'ca5']
    for court_id in older_courts:
        logger.info(f"\nChecking {court_id} for older documents...")
        
        # Fetch older opinions
        opinions = await cl_service.fetch_opinions(
            court_id=court_id,
            date_filed_after='2010-01-01',
            max_results=20
        )
        
        for opinion in opinions:
            has_text = bool(opinion.get('plain_text'))
            has_pdf = bool(opinion.get('download_url'))
            
            if has_pdf and not has_text:
                logger.info(f"  ✓ Found PDF without text!")
                logger.info(f"    Opinion ID: {opinion.get('id')}")
                logger.info(f"    Download URL: {opinion.get('download_url')}")
                logger.info(f"    Date: {opinion.get('date_created')}")
                return opinion
            elif has_pdf and has_text:
                text_len = len(opinion.get('plain_text', ''))
                if text_len < 100:  # Very short text might indicate extraction failure
                    logger.info(f"  ⚠ Found PDF with suspiciously short text ({text_len} chars)")
                    logger.info(f"    Opinion ID: {opinion.get('id')}")
    
    # Strategy 2: Check RECAP documents (if accessible)
    logger.info("\n\n2. Checking RECAP documents...")
    try:
        # Try searching for RECAP documents
        recap_results = await cl_service.search_recap(
            query='patent',
            court_ids=['txed'],
            max_results=20
        )
        
        logger.info(f"Found {len(recap_results)} RECAP search results")
        
        # Look for documents with filepath_local but no text
        for result in recap_results:
            if result.get('filepath_local'):
                logger.info(f"  Found RECAP with filepath: {result.get('filepath_local')}")
                # These might need PDF download
                
    except Exception as e:
        logger.info(f"  RECAP search error: {e}")
    
    # Strategy 3: Check specific document types that might lack text
    logger.info("\n\n3. Checking document attachments and exhibits...")
    
    # Try to find court documents that are exhibits or attachments
    params = {
        'type': '020lead',  # Lead opinions
        'per_curiam': 'true',
        'page_size': 10
    }
    
    url = f"{cl_service.BASE_URL}/api/rest/v4/opinions/"
    session = await cl_service._get_session()
    
    async with session.get(url, params=params, headers=cl_service.headers) as response:
        if response.status == 200:
            data = await response.json()
            opinions = data.get('results', [])
            
            for opinion in opinions:
                if opinion.get('download_url') and not opinion.get('plain_text'):
                    logger.info(f"  ✓ Found per curiam opinion without text!")
                    logger.info(f"    Opinion ID: {opinion.get('id')}")
                    logger.info(f"    Download URL: {opinion.get('download_url')}")
                    return opinion
    
    # Strategy 4: Look for specific file types in local_path
    logger.info("\n\n4. Checking for scanned documents...")
    
    # Opinions with local_path ending in _scan.pdf might be scanned
    scan_courts = ['ca1', 'ca2', 'ca3']
    for court_id in scan_courts:
        opinions = await cl_service.fetch_opinions(
            court_id=court_id,
            date_filed_after='2015-01-01',
            max_results=30
        )
        
        for opinion in opinions:
            local_path = opinion.get('local_path', '')
            plain_text = opinion.get('plain_text', '')
            
            if ('scan' in local_path.lower() or 'image' in local_path.lower()) and len(plain_text) < 500:
                logger.info(f"  ✓ Possible scanned document found!")
                logger.info(f"    Court: {court_id}")
                logger.info(f"    Local path: {local_path}")
                logger.info(f"    Text length: {len(plain_text)}")
                logger.info(f"    Download URL: {opinion.get('download_url')}")
                
                if opinion.get('download_url'):
                    return opinion
    
    await cl_service.close()
    
    logger.info("\n\nNo unprocessed PDFs found in sample. Most CourtListener opinions have extracted text.")
    return None


async def test_pdf_extraction_on_found_document():
    """If we find a document without text, test extracting it"""
    
    doc = await find_unprocessed_pdfs()
    
    if doc and doc.get('download_url'):
        logger.info("\n\n" + "="*80)
        logger.info("TESTING PDF EXTRACTION")
        logger.info("="*80)
        
        from courtlistener_pdf_pipeline import CourtListenerPDFPipeline
        
        async with CourtListenerPDFPipeline() as pipeline:
            result = await pipeline._download_and_extract_pdf(doc['download_url'])
            
            if result['success']:
                logger.info(f"\n✅ Successfully extracted text from PDF!")
                logger.info(f"  Method: {result['method']}")
                logger.info(f"  Pages: {result['page_count']}")
                logger.info(f"  Text length: {len(result['text'])}")
                logger.info(f"  First 500 chars: {result['text'][:500]}...")
            else:
                logger.info(f"\n❌ Extraction failed: {result['error']}")


if __name__ == "__main__":
    asyncio.run(test_pdf_extraction_on_found_document())