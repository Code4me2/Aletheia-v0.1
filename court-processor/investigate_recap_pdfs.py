#!/usr/bin/env python3
"""
Investigate RECAP Document PDF Access

This script specifically explores RECAP documents and their PDF fields
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the API key
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from services.courtlistener_service import CourtListenerService
import logging
import json
import aiohttp

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def investigate_recap_pdfs():
    """Deep dive into RECAP document structure and PDF access"""
    
    service = CourtListenerService()
    
    logger.info("\n" + "="*80)
    logger.info("INVESTIGATING RECAP DOCUMENT PDF ACCESS")
    logger.info("="*80)
    
    # 1. Try direct RECAP document search
    logger.info("\n1. Direct RECAP Document API Call...")
    
    session = await service._get_session()
    
    # Try to get some RECAP documents directly
    url = f"{service.BASE_URL}{service.RECAP_DOCS_ENDPOINT}"
    params = {
        'page_size': 10,
        'is_available': 'true',  # Only available documents
        'document_type': '1'  # Main document type
    }
    
    logger.info(f"URL: {url}")
    logger.info(f"Params: {params}")
    
    # Add API key to headers
    headers = {**service.headers, 'Authorization': f'Token {os.getenv("COURTLISTENER_API_KEY")}'}
    
    async with session.get(url, params=params, headers=headers) as response:
        logger.info(f"Response status: {response.status}")
        
        if response.status == 200:
            data = await response.json()
            logger.info(f"Found {data.get('count', 0)} total documents")
            
            results = data.get('results', [])
            logger.info(f"Got {len(results)} documents in this page")
            
            for i, doc in enumerate(results[:5]):
                logger.info(f"\nRECAP Document {i+1}:")
                logger.info(f"  ID: {doc.get('id')}")
                logger.info(f"  Description: {doc.get('description')}")
                logger.info(f"  Document Type: {doc.get('document_type')}")
                logger.info(f"  Is Available: {doc.get('is_available')}")
                logger.info(f"  Page Count: {doc.get('page_count')}")
                logger.info(f"  File Size: {doc.get('file_size')}")
                
                # PDF access fields
                logger.info("  PDF Access Fields:")
                logger.info(f"    filepath_local: {doc.get('filepath_local')}")
                logger.info(f"    absolute_url: {doc.get('absolute_url')}")
                logger.info(f"    download_url: {doc.get('download_url')}")
                logger.info(f"    pacer_doc_id: {doc.get('pacer_doc_id')}")
                
                # Check for docket entry info
                docket_entry = doc.get('docket_entry')
                if docket_entry:
                    logger.info(f"  Docket Entry ID: {docket_entry}")
        else:
            text = await response.text()
            logger.error(f"Failed to get documents: {text[:500]}")
    
    # 2. Try to find specific IP case documents
    logger.info("\n\n2. Searching for Patent Case Documents...")
    
    # Search for patent-related RECAP documents
    search_results = await service.search_recap(
        query='patent infringement',
        court_ids=['txed', 'cafc', 'nysd'],
        max_results=10
    )
    
    logger.info(f"Found {len(search_results)} search results")
    
    for j, result in enumerate(search_results[:5]):
        logger.info(f"\nSearch Result {j+1}:")
        logger.info(f"  Case: {result.get('caseName')}")
        logger.info(f"  Docket Number: {result.get('docketNumber')}")
        logger.info(f"  Court: {result.get('court')}")
        logger.info(f"  Type: {result.get('type')}")
        
        # Check for PDF fields in search results
        logger.info("  PDF Fields in Search:")
        logger.info(f"    filepath_local: {result.get('filepath_local')}")
        logger.info(f"    absolute_url: {result.get('absolute_url')}")
        logger.info(f"    download_url: {result.get('download_url')}")
        logger.info(f"    recap_document_id: {result.get('recap_document_id')}")
        logger.info(f"    docket_id: {result.get('docket_id')}")
    
    # 3. If we have a docket_id, try to get its documents
    if search_results and search_results[0].get('docket_id'):
        docket_id = search_results[0]['docket_id']
        logger.info(f"\n\n3. Getting documents for docket ID: {docket_id}")
        
        # Try the original method
        docs = await service.fetch_recap_documents(docket_id)
        logger.info(f"Found {len(docs)} documents using fetch_recap_documents")
        
        # Also try a direct query with just docket_id
        params2 = {
            'docket': docket_id,
            'page_size': 10,
            'is_available': 'true'
        }
        
        async with session.get(url, params=params2, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                results2 = data.get('results', [])
                logger.info(f"Found {len(results2)} documents with docket param")
                
                for doc in results2[:3]:
                    logger.info(f"\n  Document: {doc.get('description')}")
                    logger.info(f"    filepath_local: {doc.get('filepath_local')}")
                    logger.info(f"    is_available: {doc.get('is_available')}")
    
    await service.close()


async def test_recap_pdf_download():
    """Test downloading a RECAP PDF if we find one"""
    
    logger.info("\n\n" + "="*80)
    logger.info("TESTING RECAP PDF DOWNLOAD")
    logger.info("="*80)
    
    service = CourtListenerService()
    session = await service._get_session()
    
    # Get some RECAP documents that should have PDFs
    url = f"{service.BASE_URL}{service.RECAP_DOCS_ENDPOINT}"
    params = {
        'page_size': 20,
        'is_available': 'true',
        'page_count__gt': '0',  # Has pages
        'filepath_local__isnull': 'false'  # Has a file path
    }
    
    # Add API key to headers
    headers = {**service.headers, 'Authorization': f'Token {os.getenv("COURTLISTENER_API_KEY")}'}
    
    async with session.get(url, params=params, headers=headers) as response:
        if response.status == 200:
            data = await response.json()
            docs = data.get('results', [])
            
            # Find a document with filepath_local
            pdf_found = False
            for doc in docs:
                filepath = doc.get('filepath_local')
                if filepath:
                    logger.info(f"\nFound document with filepath: {filepath}")
                    logger.info(f"Description: {doc.get('description')}")
                    logger.info(f"Page count: {doc.get('page_count')}")
                    
                    # Construct download URL
                    # CourtListener serves files from storage.courtlistener.com
                    pdf_url = f"https://storage.courtlistener.com/{filepath}"
                    logger.info(f"Constructed URL: {pdf_url}")
                    
                    # Try to download
                    try:
                        async with session.get(pdf_url) as pdf_response:
                            logger.info(f"PDF Response status: {pdf_response.status}")
                            logger.info(f"Content type: {pdf_response.headers.get('Content-Type')}")
                            
                            if pdf_response.status == 200:
                                content = await pdf_response.read(1000)  # Read first 1KB
                                if content[:4] == b'%PDF':
                                    logger.info("✅ Successfully accessed RECAP PDF!")
                                    pdf_found = True
                                    break
                                else:
                                    logger.info("❌ Content is not a PDF")
                            else:
                                logger.info(f"Failed to download: HTTP {pdf_response.status}")
                    except Exception as e:
                        logger.error(f"Download error: {e}")
            
            if not pdf_found:
                logger.info("\nNo accessible PDFs found in RECAP documents")
    
    await service.close()


if __name__ == "__main__":
    asyncio.run(investigate_recap_pdfs())
    asyncio.run(test_recap_pdf_download())