#!/usr/bin/env python3
"""
Integration wrapper for PACER authentication with court-processor RECAP client

This validates PACER credentials before using the existing RECAP client
"""

import os
import asyncio
import logging
from typing import Optional, Dict
import sys

# Add path for court-processor modules
sys.path.append('/Users/vel/Desktop/coding/Aletheia-worktrees/flp-integration/court-processor')

from services.recap.recap_fetch_client import RECAPFetchClient
from pacer_integration import PACERAuthenticator

logger = logging.getLogger(__name__)


class AuthenticatedRECAPClient:
    """
    Wrapper that ensures PACER authentication before using RECAP client
    """
    
    def __init__(self, cl_token: str, pacer_username: str, pacer_password: str):
        self.cl_token = cl_token
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self.pacer_auth = PACERAuthenticator(environment='PRODUCTION')
        self.recap_client = None
        self.authenticated = False
        
    async def __aenter__(self):
        # Authenticate with PACER first
        auth_result = self.pacer_auth.authenticate()
        if not auth_result['success']:
            raise Exception(f"PACER authentication failed: {auth_result['error']}")
        
        self.authenticated = True
        logger.info("PACER authentication successful")
        
        # Create RECAP client with validated credentials
        self.recap_client = RECAPFetchClient(
            self.cl_token, 
            self.pacer_username, 
            self.pacer_password
        )
        await self.recap_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.recap_client:
            await self.recap_client.__aexit__(exc_type, exc_val, exc_tb)
        
        # Logout from PACER
        if self.authenticated:
            self.pacer_auth.logout()
    
    def __getattr__(self, name):
        """Proxy all other methods to the RECAP client"""
        if self.recap_client is None:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")
        return getattr(self.recap_client, name)


async def fetch_ip_case_documents():
    """
    Example of fetching IP case documents using authenticated client
    """
    # Load credentials
    cl_token = os.getenv('COURTLISTENER_API_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    # IP case examples
    cases = [
        {'docket': '2:2024cv00162', 'court': 'txed', 'name': 'Byteweavr v. Databricks'},
        {'docket': '2:2024cv00181', 'court': 'txed', 'name': 'Cerence v. Samsung'},
    ]
    
    async with AuthenticatedRECAPClient(cl_token, pacer_username, pacer_password) as client:
        for case in cases:
            try:
                # Check if already in RECAP (free)
                is_available = await client.check_recap_availability_before_purchase(
                    case['docket'], 
                    case['court']
                )
                
                if is_available:
                    logger.info(f"{case['name']} already in RECAP - free access!")
                else:
                    # Fetch from PACER (costs money)
                    logger.info(f"Fetching {case['name']} from PACER...")
                    result = await client.fetch_docket_with_monitoring(
                        docket_identifier=case['docket'],
                        court=case['court'],
                        show_parties_and_counsel=True
                    )
                    logger.info(f"Success! Cost: ${result.get('cost', 0):.2f}")
                    
            except Exception as e:
                logger.error(f"Failed to fetch {case['name']}: {e}")


def integrate_with_document_ingestion_service():
    """
    Show how to modify document_ingestion_service.py to use authenticated RECAP
    """
    integration_code = '''
# In document_ingestion_service.py, modify the PDF fetching section:

# Add import at top
from court_processor_integration import AuthenticatedRECAPClient

# In the fetch_and_extract_pdf method, after the 404/403 error:

if response.status in [403, 404]:
    logger.warning(f"Direct PDF download failed for {pdf_url}")
    
    # Try RECAP fetch if we have PACER credentials
    if self.pacer_username and self.pacer_password:
        try:
            async with AuthenticatedRECAPClient(
                self.cl_api_key, 
                self.pacer_username, 
                self.pacer_password
            ) as recap_client:
                
                # Extract docket info from the document
                docket_number = document.get('docket_number')
                court = document.get('court')
                
                if docket_number and court:
                    # Check if in RECAP first
                    in_recap = await recap_client.check_recap_availability_before_purchase(
                        docket_number, court
                    )
                    
                    if not in_recap:
                        # Purchase from PACER
                        result = await recap_client.fetch_docket_with_monitoring(
                            docket_identifier=docket_number,
                            court=court
                        )
                        logger.info(f"Fetched via PACER. Cost: ${result.get('cost', 0):.2f}")
                        
                        # Now try to get the PDF again
                        # ... existing PDF extraction code ...
                        
        except Exception as e:
            logger.error(f"RECAP fetch failed: {e}")
'''
    
    print("\nIntegration code for document_ingestion_service.py:")
    print(integration_code)


if __name__ == "__main__":
    # Test the authenticated client
    asyncio.run(fetch_ip_case_documents())
    
    # Show integration instructions
    integrate_with_document_ingestion_service()