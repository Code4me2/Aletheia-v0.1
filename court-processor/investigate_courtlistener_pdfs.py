#!/usr/bin/env python3
"""
Investigate CourtListener PDF Access

This script explores how to get actual PDF documents from CourtListener API
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.courtlistener_service import CourtListenerService
import logging
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def investigate_pdfs():
    """Investigate PDF access methods in CourtListener"""
    
    service = CourtListenerService()
    
    logger.info("\n" + "="*80)
    logger.info("INVESTIGATING COURTLISTENER PDF ACCESS")
    logger.info("="*80)
    
    # 1. Check Opinion PDFs
    logger.info("\n1. Checking Opinion Documents...")
    opinions = await service.fetch_opinions(
        court_id='ca9',  # 9th Circuit has good data
        date_filed_after='2024-01-01',
        max_results=5
    )
    
    logger.info(f"Found {len(opinions)} opinions")
    
    for i, opinion in enumerate(opinions):
        logger.info(f"\nOpinion {i+1}:")
        logger.info(f"  ID: {opinion.get('id')}")
        logger.info(f"  Type: {opinion.get('type')}")
        
        # Check for PDF-related fields
        logger.info("  PDF-related fields:")
        logger.info(f"    download_url: {opinion.get('download_url')}")
        logger.info(f"    local_path: {opinion.get('local_path')}")
        logger.info(f"    filepath_local: {opinion.get('filepath_local')}")
        logger.info(f"    absolute_url: {opinion.get('absolute_url')}")
        
        # Check text content
        plain_text = opinion.get('plain_text', '')
        html_text = opinion.get('html', '')
        logger.info(f"    plain_text length: {len(plain_text)}")
        logger.info(f"    html length: {len(html_text)}")
        
        # Check cluster for more info
        cluster_url = opinion.get('cluster')
        if cluster_url:
            logger.info(f"    cluster: {cluster_url}")
    
    # 2. Check RECAP Documents (these are more likely to have PDFs)
    logger.info("\n\n2. Checking RECAP Documents...")
    
    # First get a docket
    dockets = await service.fetch_recap_dockets(
        court_ids=['nysd'],  # Southern District of NY
        nature_of_suit=['830'],  # Patent cases
        date_filed_after='2024-01-01',
        max_results=2
    )
    
    if dockets:
        docket = dockets[0]
        logger.info(f"\nChecking docket: {docket.get('case_name')}")
        logger.info(f"  Docket ID: {docket.get('id')}")
        
        # Get documents for this docket
        recap_docs = await service.fetch_recap_documents(docket['id'])
        logger.info(f"  Found {len(recap_docs)} RECAP documents")
        
        for j, doc in enumerate(recap_docs[:5]):  # First 5 docs
            logger.info(f"\n  RECAP Document {j+1}:")
            logger.info(f"    ID: {doc.get('id')}")
            logger.info(f"    Description: {doc.get('description')}")
            logger.info(f"    Document type: {doc.get('document_type')}")
            
            # PDF access fields
            logger.info("    PDF Access:")
            logger.info(f"      filepath_local: {doc.get('filepath_local')}")
            logger.info(f"      absolute_url: {doc.get('absolute_url')}")
            logger.info(f"      is_available: {doc.get('is_available')}")
            logger.info(f"      page_count: {doc.get('page_count')}")
            logger.info(f"      file_size: {doc.get('file_size')}")
            logger.info(f"      pacer_doc_id: {doc.get('pacer_doc_id')}")
            
            # Text content
            logger.info(f"      plain_text length: {len(doc.get('plain_text', ''))}")
            logger.info(f"      ocr_status: {doc.get('ocr_status')}")
    
    # 3. Check Search Results for PDF info
    logger.info("\n\n3. Checking Search Results...")
    search_results = await service.search_recap(
        query='patent opinion',
        court_ids=['cafc'],  # Federal Circuit
        max_results=3
    )
    
    for k, result in enumerate(search_results):
        logger.info(f"\nSearch Result {k+1}:")
        logger.info(f"  Case: {result.get('caseName')}")
        logger.info(f"  Type: {result.get('type')}")
        logger.info(f"  filepath_local: {result.get('filepath_local')}")
        logger.info(f"  absolute_url: {result.get('absolute_url')}")
        logger.info(f"  download_url: {result.get('download_url')}")
    
    # 4. Test actual download URL construction
    logger.info("\n\n4. Understanding URL Patterns...")
    
    # Check if we can construct download URLs
    base_url = "https://www.courtlistener.com"
    storage_url = "https://storage.courtlistener.com"
    
    logger.info(f"\nBase URL: {base_url}")
    logger.info(f"Storage URL: {storage_url}")
    
    # Example paths from above
    if opinions and opinions[0].get('download_url'):
        logger.info(f"\nExample opinion download URL: {opinions[0]['download_url']}")
    
    if recap_docs and recap_docs[0].get('filepath_local'):
        filepath = recap_docs[0]['filepath_local']
        logger.info(f"\nExample RECAP filepath_local: {filepath}")
        logger.info(f"Constructed URL: {storage_url}/{filepath}")
    
    await service.close()


async def test_pdf_download():
    """Test downloading an actual PDF"""
    
    logger.info("\n\n" + "="*80)
    logger.info("TESTING PDF DOWNLOAD")
    logger.info("="*80)
    
    import aiohttp
    
    # Get a document with PDF
    service = CourtListenerService()
    
    # Try to find an opinion with download_url
    opinions = await service.fetch_opinions(
        court_id='scotus',  # Supreme Court opinions are public
        date_filed_after='2023-01-01',
        max_results=10
    )
    
    pdf_url = None
    for opinion in opinions:
        if opinion.get('download_url'):
            pdf_url = opinion['download_url']
            logger.info(f"\nFound opinion with download URL: {pdf_url}")
            break
    
    if pdf_url:
        # Try to download
        async with aiohttp.ClientSession() as session:
            headers = service.headers
            
            logger.info(f"Attempting to download PDF...")
            logger.info(f"Headers: {headers}")
            
            try:
                async with session.get(pdf_url, headers=headers) as response:
                    logger.info(f"Response status: {response.status}")
                    logger.info(f"Content type: {response.headers.get('Content-Type')}")
                    logger.info(f"Content length: {response.headers.get('Content-Length')}")
                    
                    if response.status == 200:
                        content = await response.read()
                        logger.info(f"Downloaded {len(content)} bytes")
                        
                        # Check if it's a PDF
                        if content[:4] == b'%PDF':
                            logger.info("✅ Successfully downloaded PDF!")
                        else:
                            logger.info("❌ Content is not a PDF")
                            logger.info(f"First 100 bytes: {content[:100]}")
                    else:
                        text = await response.text()
                        logger.info(f"Download failed: {text[:500]}")
                        
            except Exception as e:
                logger.error(f"Download error: {e}")
    else:
        logger.info("No opinions found with download URLs")
    
    await service.close()


if __name__ == "__main__":
    asyncio.run(investigate_pdfs())
    asyncio.run(test_pdf_download())