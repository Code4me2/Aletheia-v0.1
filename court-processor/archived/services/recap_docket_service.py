"""
RECAP Docket Service
Handles specific docket retrieval from RECAP/PACER
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import aiohttp

from .courtlistener_service import CourtListenerService
from .recap.authenticated_client import AuthenticatedRECAPClient
from .recap.recap_pdf_handler import RECAPPDFHandler
from .database import get_db_connection

logger = logging.getLogger(__name__)


class RECAPDocketService:
    """
    Service for retrieving specific dockets from RECAP/PACER
    
    This service handles:
    1. Checking RECAP availability (free)
    2. Purchasing from PACER if needed
    3. Managing webhook notifications
    4. Downloading associated PDFs
    """
    
    def __init__(self, cl_token: str, pacer_username: Optional[str] = None, 
                 pacer_password: Optional[str] = None):
        self.cl_token = cl_token
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self.cl_service = CourtListenerService(cl_token)
        self.pending_requests = {}  # Track pending PACER requests
        
    async def check_recap_availability(self, docket_number: str, court: str) -> bool:
        """
        Check if a specific docket is available in RECAP (free)
        
        Args:
            docket_number: Exact docket number
            court: Court ID
            
        Returns:
            True if available in RECAP, False otherwise
        """
        try:
            # Search RECAP for the specific docket
            search_params = {
                'type': 'r',  # RECAP type
                'q': f'docketNumber:"{docket_number}"',
                'court': court
            }
            
            results = await self.cl_service.search(search_params)
            
            if results and results.get('results'):
                # Check if we have any results for this docket
                for result in results['results']:
                    # Verify it's the exact docket we're looking for
                    if result.get('docketNumber') == docket_number:
                        logger.info(f"Docket {docket_number} found in RECAP")
                        return True
            
            logger.info(f"Docket {docket_number} not found in RECAP")
            return False
            
        except Exception as e:
            logger.error(f"Error checking RECAP availability: {e}")
            return False
    
    async def fetch_from_recap(self, docket_number: str, court: str,
                              include_documents: bool = True,
                              max_documents: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch docket from RECAP (free archive)
        
        Args:
            docket_number: Exact docket number
            court: Court ID
            include_documents: Whether to download PDFs
            max_documents: Maximum PDFs to download
            
        Returns:
            Dict with docket info and documents
        """
        result = {
            'success': False,
            'docket_number': docket_number,
            'court': court,
            'case_name': None,
            'docket_id': None,
            'documents': [],
            'error': None
        }
        
        try:
            # Search for the docket
            search_params = {
                'type': 'r',
                'q': f'docketNumber:"{docket_number}"',
                'court': court
            }
            
            search_results = await self.cl_service.search(search_params)
            
            if not search_results or not search_results.get('results'):
                result['error'] = "Docket not found in RECAP"
                return result
            
            # Get the first matching result
            docket_data = None
            for res in search_results['results']:
                if res.get('docketNumber') == docket_number:
                    docket_data = res
                    break
            
            if not docket_data:
                result['error'] = "Exact docket match not found"
                return result
            
            # Extract docket info
            result['case_name'] = docket_data.get('caseName')
            result['docket_id'] = docket_data.get('docket_id') or docket_data.get('id')
            
            # Get docket details if we have an ID
            if result['docket_id'] and include_documents:
                # Fetch docket entries
                docket_url = f"https://www.courtlistener.com/api/rest/v4/dockets/{result['docket_id']}/"
                
                async with aiohttp.ClientSession() as session:
                    headers = {'Authorization': f'Token {self.cl_token}'}
                    async with session.get(docket_url, headers=headers) as response:
                        if response.status == 200:
                            docket_detail = await response.json()
                            
                            # Get docket entries
                            entries = docket_detail.get('docket_entries', [])
                            
                            # Download associated documents
                            if entries:
                                pdf_handler = RECAPPDFHandler(self.cl_token)
                                documents = await pdf_handler.download_docket_pdfs(
                                    result['docket_id'],
                                    max_documents=max_documents
                                )
                                result['documents'] = documents
            
            result['success'] = True
            
        except Exception as e:
            logger.error(f"Error fetching from RECAP: {e}")
            result['error'] = str(e)
        
        return result
    
    async def purchase_from_pacer(self, docket_number: str, court: str,
                                 include_documents: bool = True,
                                 max_documents: Optional[int] = None,
                                 date_start: Optional[str] = None,
                                 date_end: Optional[str] = None) -> Dict[str, Any]:
        """
        Purchase docket from PACER using RECAP Fetch API
        
        Args:
            docket_number: Exact docket number
            court: Court ID
            include_documents: Whether to request PDFs
            max_documents: Maximum PDFs to purchase
            date_start: Start date for entries (YYYY-MM-DD)
            date_end: End date for entries (YYYY-MM-DD)
            
        Returns:
            Dict with purchase status and request ID
        """
        result = {
            'submitted': False,
            'request_id': None,
            'estimated_cost': 0.0,
            'webhook_registered': False,
            'error': None
        }
        
        if not self.pacer_username or not self.pacer_password:
            result['error'] = "PACER credentials not configured"
            return result
        
        try:
            async with AuthenticatedRECAPClient(
                self.cl_token,
                self.pacer_username,
                self.pacer_password
            ) as client:
                # Submit RECAP fetch request
                fetch_result = await client.fetch_docket(
                    docket_identifier=docket_number,
                    court=court,
                    show_parties_and_counsel=True,
                    date_start=date_start,
                    date_end=date_end
                )
                
                if fetch_result and 'id' in fetch_result:
                    result['submitted'] = True
                    result['request_id'] = fetch_result['id']
                    result['estimated_cost'] = self._estimate_cost(fetch_result)
                    
                    # Register for webhook notification
                    self.pending_requests[fetch_result['id']] = {
                        'docket_number': docket_number,
                        'court': court,
                        'requested_at': datetime.now().isoformat(),
                        'include_documents': include_documents,
                        'max_documents': max_documents
                    }
                    result['webhook_registered'] = True
                else:
                    result['error'] = "Failed to submit RECAP request"
                    
        except Exception as e:
            logger.error(f"Error purchasing from PACER: {e}")
            result['error'] = str(e)
        
        return result
    
    async def check_request_status(self, request_id: int) -> Dict[str, Any]:
        """
        Check status of a RECAP fetch request
        
        Args:
            request_id: RECAP request ID
            
        Returns:
            Dict with status information
        """
        status_result = {
            'status': 'unknown',
            'completed': False,
            'docket_id': None,
            'documents_processed': 0,
            'error': None
        }
        
        try:
            # Check status via RECAP API
            status_url = f"https://www.courtlistener.com/api/rest/v4/recap-fetch/{request_id}/"
            
            async with aiohttp.ClientSession() as session:
                headers = {'Authorization': f'Token {self.cl_token}'}
                async with session.get(status_url, headers=headers) as response:
                    if response.status == 200:
                        status_data = await response.json()
                        
                        # Map status codes
                        status_map = {
                            1: 'awaiting',
                            2: 'success',
                            3: 'failed',
                            4: 'queued_retry',
                            5: 'success_retry',
                            6: 'failed_retries'
                        }
                        
                        status_code = status_data.get('status')
                        status_result['status'] = status_map.get(status_code, 'unknown')
                        status_result['completed'] = status_code in [2, 3, 5, 6]
                        
                        if status_code in [2, 5]:  # Success
                            status_result['docket_id'] = status_data.get('docket')
                            
                            # Check if we have pending document downloads
                            if request_id in self.pending_requests:
                                req_info = self.pending_requests[request_id]
                                if req_info.get('include_documents') and status_result['docket_id']:
                                    # Download documents
                                    pdf_handler = RECAPPDFHandler(self.cl_token)
                                    documents = await pdf_handler.download_docket_pdfs(
                                        status_result['docket_id'],
                                        max_documents=req_info.get('max_documents')
                                    )
                                    status_result['documents_processed'] = len(documents)
                        
                        elif status_code in [3, 6]:  # Failed
                            status_result['error'] = status_data.get('error_message', 'Request failed')
                    else:
                        status_result['error'] = f"Failed to check status: HTTP {response.status}"
                        
        except Exception as e:
            logger.error(f"Error checking request status: {e}")
            status_result['error'] = str(e)
        
        return status_result
    
    def _estimate_cost(self, fetch_result: Dict) -> float:
        """Estimate cost based on RECAP fetch response"""
        # Base docket cost
        cost = 3.00  # Max $3 per docket
        
        # Add estimated document costs if applicable
        # This is a rough estimate - actual cost depends on page count
        if 'estimated_pages' in fetch_result:
            page_cost = fetch_result['estimated_pages'] * 0.10
            cost += min(page_cost, 30.00)  # Max $30 per document
        
        return cost
    
    async def process_webhook_notification(self, webhook_data: Dict) -> Dict[str, Any]:
        """
        Process a webhook notification from CourtListener
        
        Args:
            webhook_data: Webhook payload
            
        Returns:
            Processing result
        """
        result = {
            'processed': False,
            'request_id': None,
            'docket_id': None,
            'documents_downloaded': 0,
            'error': None
        }
        
        try:
            payload = webhook_data.get('payload', {})
            request_id = payload.get('id')
            
            if request_id and request_id in self.pending_requests:
                # Get request info
                req_info = self.pending_requests[request_id]
                
                # Check if successful
                if payload.get('status') in [2, 5]:  # Success codes
                    result['request_id'] = request_id
                    result['docket_id'] = payload.get('docket')
                    
                    # Download documents if requested
                    if req_info.get('include_documents') and result['docket_id']:
                        pdf_handler = RECAPPDFHandler(self.cl_token)
                        documents = await pdf_handler.download_docket_pdfs(
                            result['docket_id'],
                            max_documents=req_info.get('max_documents')
                        )
                        result['documents_downloaded'] = len(documents)
                        
                        # Store in database
                        await self._store_recap_documents(
                            documents,
                            req_info['docket_number'],
                            req_info['court']
                        )
                    
                    result['processed'] = True
                    
                    # Clean up pending request
                    del self.pending_requests[request_id]
                else:
                    result['error'] = f"Request failed with status: {payload.get('status')}"
            else:
                result['error'] = f"Unknown request ID: {request_id}"
                
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            result['error'] = str(e)
        
        return result
    
    async def _store_recap_documents(self, documents: List[Dict], 
                                    docket_number: str, court: str):
        """Store RECAP documents in database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for doc in documents:
                # Insert or update document
                cursor.execute("""
                    INSERT INTO public.court_documents 
                    (case_number, case_name, document_type, content, metadata, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_number) 
                    DO UPDATE SET 
                        content = EXCLUDED.content,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """, (
                    f"RECAP-{court}-{doc.get('id')}",
                    doc.get('description', ''),
                    'recap_document',
                    doc.get('content', ''),
                    json.dumps({
                        'docket_number': docket_number,
                        'court': court,
                        'pacer_doc_id': doc.get('pacer_doc_id'),
                        'page_count': doc.get('page_count'),
                        'file_path': doc.get('file_path')
                    }),
                    datetime.now()
                ))
            
            conn.commit()
            logger.info(f"Stored {len(documents)} RECAP documents")
            
        except Exception as e:
            logger.error(f"Error storing RECAP documents: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    async def close(self):
        """Clean up resources"""
        await self.cl_service.close()