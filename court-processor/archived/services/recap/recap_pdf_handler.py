#!/usr/bin/env python3
"""
RECAP PDF Handler
Handles fetching docket details and downloading PDFs after RECAP purchase
"""

import asyncio
import aiohttp
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# API Endpoints
COURTLISTENER_BASE_URL = "https://www.courtlistener.com"
DOCKET_API = f"{COURTLISTENER_BASE_URL}/api/rest/v4/dockets/"
DOCKET_ENTRY_API = f"{COURTLISTENER_BASE_URL}/api/rest/v4/docket-entries/"
RECAP_DOCUMENT_API = f"{COURTLISTENER_BASE_URL}/api/rest/v4/recap-documents/"
SEARCH_API = f"{COURTLISTENER_BASE_URL}/api/rest/v4/search/"


class RECAPPDFHandler:
    """
    Handles fetching docket details and downloading PDFs after RECAP purchase
    """
    
    def __init__(self, cl_token: str, download_dir: str = "recap_pdfs"):
        self.cl_token = cl_token
        self.headers = {'Authorization': f'Token {cl_token}'}
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_and_verify_docket(self, docket_id: int, expected_docket_number: str, 
                                     court: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """
        Fetch docket and verify it matches expected case
        Handles the docket mismatch issue by searching if needed
        """
        for attempt in range(max_retries):
            # Fetch docket by ID
            docket_url = f"{DOCKET_API}{docket_id}/"
            try:
                async with self.session.get(docket_url, headers=self.headers) as response:
                    if response.status == 200:
                        docket_data = await response.json()
                        
                        # Check if this is the right docket
                        if expected_docket_number in docket_data.get('docket_number', ''):
                            logger.info(f"✅ Found correct docket: {docket_data.get('case_name')}")
                            return docket_data
                        else:
                            logger.warning(
                                f"Docket mismatch! Expected {expected_docket_number}, "
                                f"got {docket_data.get('docket_number')}"
                            )
            except Exception as e:
                logger.error(f"Error fetching docket: {e}")
            
            # If mismatch or error, search for correct docket
            logger.info(f"Searching for correct docket (attempt {attempt + 1}/{max_retries})...")
            
            # Wait before searching (data propagation delay)
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
            
            # Search for the correct docket
            correct_docket_id = await self.search_for_docket(expected_docket_number, court)
            if correct_docket_id and correct_docket_id != docket_id:
                docket_id = correct_docket_id
                # Try fetching the correct docket
                docket_url = f"{DOCKET_API}{correct_docket_id}/"
                async with self.session.get(docket_url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.json()
            
            # Wait before retry
            if attempt < max_retries - 1:
                await asyncio.sleep(5)
        
        return None
    
    async def search_for_docket(self, docket_number: str, court: str) -> Optional[int]:
        """Search for a docket by number and court"""
        search_params = {
            'type': 'r',  # RECAP search
            'q': f'docketNumber:"{docket_number}" AND court_id:{court}',
            'order_by': '-date_modified'
        }
        
        try:
            async with self.session.get(SEARCH_API, params=search_params, headers=self.headers) as response:
                if response.status == 200:
                    search_data = await response.json()
                    if search_data.get('results'):
                        # Get the most recent matching docket
                        for result in search_data['results']:
                            if docket_number in result.get('docketNumber', ''):
                                return result.get('docket_id')
        except Exception as e:
            logger.error(f"Error searching for docket: {e}")
        
        return None
    
    async def download_docket_pdfs(self, docket_id: int, max_pdfs: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Download PDFs from a docket
        
        Args:
            docket_id: CourtListener docket ID
            max_pdfs: Maximum number of PDFs to download (None for all)
            
        Returns:
            List of downloaded PDF information
        """
        downloaded_pdfs = []
        
        # Fetch docket entries with nested documents (v4 API)
        params = {
            'docket': docket_id,
            'order_by': 'date_filed,-entry_number',  # v4 default ordering
            'page_size': 100
        }
        
        entries_url = DOCKET_ENTRY_API
        pdf_count = 0
        
        while entries_url:
            async with self.session.get(entries_url, params=params, headers=self.headers) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch docket entries: {response.status}")
                    break
                
                data = await response.json()
                
                # Process each entry
                for entry in data.get('results', []):
                    if max_pdfs and pdf_count >= max_pdfs:
                        return downloaded_pdfs
                    
                    entry_pdfs = await self._process_docket_entry(entry)
                    for pdf_info in entry_pdfs:
                        downloaded_pdfs.append(pdf_info)
                        pdf_count += 1
                        if max_pdfs and pdf_count >= max_pdfs:
                            return downloaded_pdfs
                
                # Get next page
                entries_url = data.get('next')
                params = {}  # Clear params for next page
        
        logger.info(f"Downloaded {len(downloaded_pdfs)} PDFs from docket {docket_id}")
        return downloaded_pdfs
    
    async def _process_docket_entry(self, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process a single docket entry and download its documents"""
        downloaded = []
        
        # Get recap documents for this entry
        if 'recap_documents' in entry:
            # Documents are already nested in the response
            documents = entry['recap_documents']
        else:
            # Need to fetch documents separately
            doc_params = {'docket_entry': entry['id']}
            async with self.session.get(RECAP_DOCUMENT_API, params=doc_params, headers=self.headers) as response:
                if response.status == 200:
                    doc_data = await response.json()
                    documents = doc_data.get('results', [])
                else:
                    documents = []
        
        # Download each available document
        for doc in documents:
            if doc.get('is_available') and doc.get('filepath_local'):
                pdf_info = await self._download_pdf(doc, entry)
                if pdf_info:
                    downloaded.append(pdf_info)
        
        return downloaded
    
    async def _download_pdf(self, recap_doc: Dict[str, Any], 
                           docket_entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Download a specific PDF"""
        doc_id = recap_doc.get('id')
        filepath = recap_doc.get('filepath_local')
        
        if not filepath:
            logger.warning(f"No filepath for document {doc_id}")
            return None
        
        # Construct download URL
        download_url = f"{COURTLISTENER_BASE_URL}{filepath}"
        
        try:
            async with self.session.get(download_url) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Verify PDF content
                    if not content.startswith(b'%PDF'):
                        logger.warning(f"Downloaded content is not a PDF for document {doc_id}")
                        return None
                    
                    # Create filename with metadata
                    date_filed = docket_entry.get('date_filed', 'unknown')
                    entry_num = docket_entry.get('entry_number', 'unknown')
                    doc_num = recap_doc.get('document_number', '')
                    description = recap_doc.get('short_description', 'document')
                    
                    # Clean description for filename
                    description = description.replace('/', '-').replace(' ', '_')[:50]
                    
                    # Create subdirectory by date
                    date_dir = self.download_dir / date_filed.replace('-', '')
                    date_dir.mkdir(exist_ok=True)
                    
                    filename = f"entry_{entry_num}_doc_{doc_num}_{description}.pdf"
                    filepath = date_dir / filename
                    
                    # Save the PDF
                    with open(filepath, 'wb') as f:
                        f.write(content)
                    
                    logger.info(f"✅ Downloaded: {filename} ({len(content):,} bytes)")
                    
                    return {
                        "id": doc_id,
                        "filepath": str(filepath),
                        "filename": filename,
                        "description": recap_doc.get('description'),
                        "short_description": recap_doc.get('short_description'),
                        "page_count": recap_doc.get('page_count'),
                        "date_filed": date_filed,
                        "entry_number": entry_num,
                        "document_number": doc_num,
                        "size": len(content),
                        "pacer_doc_id": recap_doc.get('pacer_doc_id'),
                        "download_url": download_url,
                        "downloaded_at": datetime.now().isoformat()
                    }
                else:
                    logger.error(f"Failed to download PDF {doc_id}: HTTP {response.status}")
        except Exception as e:
            logger.error(f"Error downloading PDF {doc_id}: {e}")
        
        return None
    
    async def process_recap_purchase(self, docket_id: int, docket_number: str, 
                                    court: str, max_pdfs: Optional[int] = None) -> Dict[str, Any]:
        """
        Complete process after RECAP purchase: verify docket and download PDFs
        
        Args:
            docket_id: Docket ID from RECAP response
            docket_number: Expected docket number
            court: Court ID
            max_pdfs: Maximum PDFs to download
            
        Returns:
            Processing results including downloaded PDFs
        """
        result = {
            'success': False,
            'docket_id': docket_id,
            'docket_number': docket_number,
            'court': court,
            'pdfs': [],
            'error': None
        }
        
        try:
            # Verify and get correct docket
            docket_data = await self.fetch_and_verify_docket(docket_id, docket_number, court)
            
            if not docket_data:
                result['error'] = "Could not find or verify docket"
                return result
            
            # Update with correct docket info
            result['docket_id'] = docket_data['id']
            result['case_name'] = docket_data.get('case_name')
            result['date_filed'] = docket_data.get('date_filed')
            
            # Download PDFs
            pdfs = await self.download_docket_pdfs(docket_data['id'], max_pdfs)
            result['pdfs'] = pdfs
            result['success'] = True
            result['pdf_count'] = len(pdfs)
            
            logger.info(f"Successfully processed docket {docket_number}: {len(pdfs)} PDFs")
            
        except Exception as e:
            logger.error(f"Error processing RECAP purchase: {e}")
            result['error'] = str(e)
        
        return result