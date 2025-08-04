#!/usr/bin/env python3
"""
RECAP Fetch API Client

Implements the CourtListener RECAP Fetch API for purchasing PACER documents
and contributing them to the public RECAP Archive.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Optional, Union, List
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class RECAPFetchClient:
    """
    Client for CourtListener RECAP Fetch API.
    
    This client handles asynchronous document purchases from PACER,
    including dockets, PDFs, and attachment pages.
    """
    
    # Status codes from documentation
    STATUS_AWAITING = 1
    STATUS_SUCCESS = 2
    STATUS_FAILED = 3
    STATUS_QUEUED_RETRY = 4
    STATUS_SUCCESS_RETRY = 5
    STATUS_FAILED_RETRIES = 6
    
    def __init__(self, 
                 cl_token: str,
                 pacer_username: str,
                 pacer_password: str):
        """
        Initialize RECAP Fetch client.
        
        Args:
            cl_token: CourtListener API token
            pacer_username: PACER username
            pacer_password: PACER password
        """
        self.cl_token = cl_token
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self.base_url = 'https://www.courtlistener.com/api/rest/v4/recap-fetch/'
        self.headers = {'Authorization': f'Token {cl_token}'}
        self.session = None
        
        # Track costs
        self.estimated_costs = {
            'dockets': 0.0,
            'pdfs': 0.0,
            'total': 0.0
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_docket(self,
                          docket_identifier: Union[int, str],
                          court: Optional[str] = None,
                          show_parties_and_counsel: bool = True,
                          date_start: Optional[str] = None,
                          date_end: Optional[str] = None,
                          client_code: Optional[str] = None) -> Dict:
        """
        Purchase and fetch a docket from PACER.
        
        Args:
            docket_identifier: CourtListener docket ID (int) or docket number (str)
            court: Court ID (required if using docket number)
            show_parties_and_counsel: Include party/attorney information
            date_start: Start date for entries (MM/DD/YYYY)
            date_end: End date for entries (MM/DD/YYYY)
            client_code: Optional PACER client code
            
        Returns:
            Dict with request ID and initial status
        """
        data = {
            'request_type': 1,
            'pacer_username': self.pacer_username,
            'pacer_password': self.pacer_password,
            'show_parties_and_counsel': show_parties_and_counsel
        }
        
        # Handle docket identification
        if isinstance(docket_identifier, int):
            data['docket'] = docket_identifier
            logger.info(f"Requesting docket by ID: {docket_identifier}")
        else:
            if not court:
                raise ValueError("Court ID required when using docket number")
            data['docket_number'] = docket_identifier
            data['court'] = court
            logger.info(f"Requesting docket by number: {docket_identifier} in {court}")
        
        # Optional parameters
        if date_start:
            data['de_date_start'] = date_start
        if date_end:
            data['de_date_end'] = date_end
        if client_code:
            data['client_code'] = client_code
        
        # Estimate cost (max $3 per docket)
        self.estimated_costs['dockets'] += 3.0
        self.estimated_costs['total'] += 3.0
        
        return await self._submit_request(data)
    
    async def fetch_pdf(self,
                       recap_document_id: int,
                       client_code: Optional[str] = None) -> Dict:
        """
        Purchase and fetch a PDF document from PACER.
        
        Args:
            recap_document_id: CourtListener document ID
            client_code: Optional PACER client code
            
        Returns:
            Dict with request ID and initial status
        """
        data = {
            'request_type': 2,
            'recap_document': recap_document_id,
            'pacer_username': self.pacer_username,
            'pacer_password': self.pacer_password
        }
        
        if client_code:
            data['client_code'] = client_code
        
        logger.info(f"Requesting PDF for document ID: {recap_document_id}")
        
        # Estimate cost (max $3 per document)
        self.estimated_costs['pdfs'] += 3.0
        self.estimated_costs['total'] += 3.0
        
        return await self._submit_request(data)
    
    async def fetch_attachment_page(self,
                                   recap_document_id: int) -> Dict:
        """
        Fetch attachment page (FREE in PACER).
        
        Args:
            recap_document_id: CourtListener document ID
            
        Returns:
            Dict with request ID and initial status
        """
        data = {
            'request_type': 3,
            'recap_document': recap_document_id,
            'pacer_username': self.pacer_username,
            'pacer_password': self.pacer_password
        }
        
        logger.info(f"Requesting attachment page for document ID: {recap_document_id}")
        
        # No cost for attachment pages
        return await self._submit_request(data)
    
    async def _submit_request(self, data: Dict) -> Dict:
        """Submit request to RECAP Fetch API."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        async with self.session.post(
            self.base_url,
            data=data,
            headers=self.headers
        ) as response:
            if response.status not in [200, 201]:  # 201 Created is also success
                text = await response.text()
                raise Exception(f"Request failed ({response.status}): {text}")
            
            result = await response.json()
            logger.info(f"Request submitted with ID: {result['id']}")
            return result
    
    async def check_status(self, request_id: int) -> Dict:
        """Check status of a submitted request."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        url = f"{self.base_url}{request_id}/"
        async with self.session.get(url, headers=self.headers) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Status check failed ({response.status}): {text}")
            
            return await response.json()
    
    async def wait_for_completion(self,
                                 request_id: int,
                                 max_wait: int = 300,
                                 poll_interval: int = 2) -> Dict:
        """
        Wait for request completion with polling.
        
        Args:
            request_id: RECAP Fetch request ID
            max_wait: Maximum seconds to wait
            poll_interval: Seconds between status checks
            
        Returns:
            Final status dict
            
        Raises:
            TimeoutError: If request doesn't complete in time
            Exception: If request fails
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_data = await self.check_status(request_id)
            status = status_data['status']
            
            # Success states
            if status in [self.STATUS_SUCCESS, self.STATUS_SUCCESS_RETRY]:
                logger.info(f"Request {request_id} completed successfully")
                return status_data
            
            # Failure states
            if status in [self.STATUS_FAILED, self.STATUS_FAILED_RETRIES]:
                error_msg = status_data.get('error_message', 'Unknown error')
                raise Exception(f"Request {request_id} failed: {error_msg}")
            
            # Still processing
            logger.debug(f"Request {request_id} status: {status} - Waiting...")
            await asyncio.sleep(poll_interval)
        
        raise TimeoutError(f"Request {request_id} timed out after {max_wait} seconds")
    
    async def fetch_docket_with_monitoring(self, **kwargs) -> Dict:
        """
        Fetch docket and wait for completion.
        
        Convenience method that submits request and monitors until complete.
        """
        # Submit request
        request_data = await self.fetch_docket(**kwargs)
        request_id = request_data['id']
        
        # Wait for completion
        try:
            result = await self.wait_for_completion(request_id)
            
            # Extract URLs from successful result
            if result.get('docket'):
                logger.info(f"Docket available at: {result['docket']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Docket fetch failed: {e}")
            raise
    
    async def check_recap_availability_before_purchase(self,
                                                      docket_number: str,
                                                      court: str) -> bool:
        """
        Check if content already exists in RECAP before purchasing.
        
        Args:
            docket_number: Docket number to check
            court: Court ID
            
        Returns:
            True if already available, False if need to purchase
        """
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        search_url = "https://www.courtlistener.com/api/rest/v4/search/"
        params = {
            'type': 'r',  # RECAP search
            'q': f'docketNumber:"{docket_number}" AND court_id:{court}'
        }
        
        async with self.session.get(
            search_url,
            params=params,
            headers=self.headers
        ) as response:
            if response.status == 200:
                data = await response.json()
                available = data.get('count', 0) > 0
                
                if available:
                    logger.info(f"Docket {docket_number} already in RECAP - no purchase needed")
                else:
                    logger.info(f"Docket {docket_number} not in RECAP - purchase required")
                
                return available
            
            return False
    
    def get_estimated_costs(self) -> Dict[str, float]:
        """Get estimated costs for this session."""
        return self.estimated_costs.copy()
    
    def reset_cost_tracking(self):
        """Reset cost tracking."""
        self.estimated_costs = {
            'dockets': 0.0,
            'pdfs': 0.0,
            'total': 0.0
        }


# Convenience functions
async def fetch_docket_safe(cl_token: str,
                           pacer_username: str,
                           pacer_password: str,
                           docket_number: str,
                           court: str,
                           check_existing: bool = True) -> Optional[Dict]:
    """
    Safely fetch a docket with availability check.
    
    Args:
        cl_token: CourtListener API token
        pacer_username: PACER username
        pacer_password: PACER password
        docket_number: Docket number
        court: Court ID
        check_existing: Check if already in RECAP first
        
    Returns:
        Result dict or None if already available
    """
    async with RECAPFetchClient(cl_token, pacer_username, pacer_password) as client:
        # Check if already available
        if check_existing:
            available = await client.check_recap_availability_before_purchase(
                docket_number, court
            )
            if available:
                return None  # Already in RECAP
        
        # Purchase from PACER
        return await client.fetch_docket_with_monitoring(
            docket_identifier=docket_number,
            court=court
        )


# Example usage
if __name__ == "__main__":
    import os
    
    async def main():
        # Get credentials from environment
        cl_token = os.getenv('COURTLISTENER_API_KEY')
        pacer_user = os.getenv('PACER_USERNAME')
        pacer_pass = os.getenv('PACER_PASSWORD')
        
        if not all([cl_token, pacer_user, pacer_pass]):
            print("Missing required credentials in environment")
            return
        
        async with RECAPFetchClient(cl_token, pacer_user, pacer_pass) as client:
            # Example: Fetch a docket
            try:
                result = await client.fetch_docket_with_monitoring(
                    docket_identifier='1:20-cv-00001',
                    court='txed',
                    show_parties_and_counsel=True
                )
                
                print(f"Success! Result: {result}")
                print(f"Estimated costs: {client.get_estimated_costs()}")
                
            except Exception as e:
                print(f"Error: {e}")
    
    asyncio.run(main())