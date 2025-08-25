#!/usr/bin/env python3
"""
Authenticated RECAP Client
Ensures PACER authentication before using RECAP Fetch API
"""

import os
import logging
import requests
from typing import Optional, Dict
import aiohttp

from .recap_fetch_client import RECAPFetchClient
from .recap_pdf_handler import RECAPPDFHandler

logger = logging.getLogger(__name__)


class PACERAuthenticator:
    """Simple PACER authenticator for production use"""
    
    def __init__(self):
        self.auth_url = 'https://pacer.login.uscourts.gov/services/cso-auth'
        self.logout_url = 'https://pacer.login.uscourts.gov/services/cso-logout'
        self.token = None
        
    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate with PACER"""
        logger.info("Authenticating with PACER...")
        
        auth_data = {
            'loginId': username,
            'password': password,
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(self.auth_url, json=auth_data, headers=headers)
            response.raise_for_status()
            result = response.json()
            
            if result.get('loginResult') == '0':
                self.token = result.get('nextGenCSO')
                logger.info("PACER authentication successful")
                return {'success': True, 'token': self.token}
            else:
                error = result.get('errorDescription', 'Unknown error')
                logger.error(f"PACER authentication failed: {error}")
                return {'success': False, 'error': error}
                
        except Exception as e:
            logger.error(f"PACER authentication exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def logout(self) -> bool:
        """Logout from PACER"""
        if not self.token:
            return True
            
        try:
            response = requests.post(
                self.logout_url,
                json={'nextGenCSO': self.token},
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            result = response.json()
            
            if result.get('loginResult') == '0':
                logger.info("PACER logout successful")
                self.token = None
                return True
            else:
                logger.warning(f"PACER logout failed: {result.get('errorDescription')}")
                return False
                
        except Exception as e:
            logger.error(f"PACER logout exception: {e}")
            return False


class AuthenticatedRECAPClient(RECAPFetchClient):
    """
    RECAP client that ensures PACER authentication before operations
    """
    
    def __init__(self, cl_token: str, pacer_username: str, pacer_password: str,
                 webhook_url: Optional[str] = None):
        super().__init__(cl_token, pacer_username, pacer_password)
        self.pacer_auth = PACERAuthenticator()
        self.authenticated = False
        self.webhook_url = webhook_url or os.getenv('RECAP_WEBHOOK_URL')
        
    async def __aenter__(self):
        # Authenticate with PACER first
        auth_result = self.pacer_auth.authenticate(self.pacer_username, self.pacer_password)
        if not auth_result['success']:
            raise Exception(f"PACER authentication failed: {auth_result.get('error')}")
        
        self.authenticated = True
        logger.info("PACER pre-authentication successful - RECAP requests should now work")
        
        # Call parent's aenter
        await super().__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Call parent's aexit first
        await super().__aexit__(exc_type, exc_val, exc_tb)
        
        # Then logout from PACER
        if self.authenticated:
            self.pacer_auth.logout()
            self.authenticated = False
    
    async def fetch_docket(self, *args, **kwargs):
        """Override to ensure authentication"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with PACER. Use 'async with' context manager.")
        return await super().fetch_docket(*args, **kwargs)
    
    async def fetch_pdf(self, *args, **kwargs):
        """Override to ensure authentication"""
        if not self.authenticated:
            raise RuntimeError("Not authenticated with PACER. Use 'async with' context manager.")
        return await super().fetch_pdf(*args, **kwargs)
    
    async def fetch_docket_and_pdfs(self, docket_number: str, court: str,
                                   max_pdfs: Optional[int] = None,
                                   date_start: Optional[str] = None,
                                   date_end: Optional[str] = None) -> Dict:
        """
        Complete workflow: Check RECAP, purchase if needed, download PDFs
        
        Args:
            docket_number: Docket number to fetch
            court: Court ID
            max_pdfs: Maximum PDFs to download (None for all)
            date_start: Start date for docket entries (YYYY-MM-DD)
            date_end: End date for docket entries (YYYY-MM-DD)
            
        Returns:
            Dict with docket info and downloaded PDFs
        """
        result = {
            'docket_number': docket_number,
            'court': court,
            'in_recap': False,
            'purchased': False,
            'docket_id': None,
            'case_name': None,
            'pdfs': [],
            'error': None
        }
        
        try:
            # Check if already in RECAP
            is_available = await self.check_recap_availability_before_purchase(docket_number, court)
            result['in_recap'] = is_available
            
            if is_available:
                logger.info(f"Docket {docket_number} already in RECAP - free access")
                # Search for existing docket
                async with RECAPPDFHandler(self.cl_token) as pdf_handler:
                    docket_id = await pdf_handler.search_for_docket(docket_number, court)
                    if docket_id:
                        result['docket_id'] = docket_id
                        # Download PDFs from existing docket
                        pdf_result = await pdf_handler.process_recap_purchase(
                            docket_id, docket_number, court, max_pdfs
                        )
                        result.update(pdf_result)
            else:
                logger.info(f"Purchasing docket {docket_number} from PACER...")
                # Purchase from PACER
                fetch_result = await self.fetch_docket_with_monitoring(
                    docket_identifier=docket_number,
                    court=court,
                    show_parties_and_counsel=True,
                    date_start=date_start,
                    date_end=date_end
                )
                
                result['purchased'] = True
                result['purchase_cost'] = fetch_result.get('cost', 0.0)
                
                # Get docket ID from response
                docket_id = fetch_result.get('docket')
                if docket_id:
                    result['docket_id'] = docket_id
                    
                    # Download PDFs
                    async with RECAPPDFHandler(self.cl_token) as pdf_handler:
                        pdf_result = await pdf_handler.process_recap_purchase(
                            docket_id, docket_number, court, max_pdfs
                        )
                        result.update(pdf_result)
                else:
                    result['error'] = "No docket ID in RECAP response"
                    
        except Exception as e:
            logger.error(f"Error in fetch_docket_and_pdfs: {e}")
            result['error'] = str(e)
            result['success'] = False
        
        return result
    
    async def _register_webhook_request(self, request_id: int, request_info: Dict):
        """Register a RECAP request with the webhook handler"""
        if not self.webhook_url:
            return
        
        try:
            register_url = f"{self.webhook_url}/register"
            async with aiohttp.ClientSession() as session:
                async with session.post(register_url, json={
                    'request_id': request_id,
                    'request_info': request_info
                }) as response:
                    if response.status == 200:
                        logger.info(f"Registered RECAP request {request_id} with webhook handler")
                    else:
                        logger.warning(f"Failed to register webhook request: {response.status}")
        except Exception as e:
            logger.error(f"Error registering webhook request: {e}")
    
    async def fetch_docket_with_webhook(self, docket_number: str, court: str,
                                       **kwargs) -> Dict:
        """
        Fetch docket using RECAP and register for webhook notification
        
        This method submits the request and returns immediately.
        The webhook handler will process the completion.
        """
        # Submit the RECAP request
        result = await self.fetch_docket(
            docket_identifier=docket_number,
            court=court,
            **kwargs
        )
        
        # Register with webhook handler
        if result and 'id' in result:
            await self._register_webhook_request(result['id'], {
                'docket_number': docket_number,
                'court': court,
                'request_type': 'docket',
                **kwargs
            })
        
        return result