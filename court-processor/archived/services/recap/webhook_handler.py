#!/usr/bin/env python3
"""
RECAP Webhook Handler
Processes webhooks from CourtListener for RECAP Fetch completions
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Set
from enum import IntEnum
import hashlib
from pathlib import Path

from .recap_pdf_handler import RECAPPDFHandler

logger = logging.getLogger(__name__)


class RecapStatus(IntEnum):
    """RECAP Fetch status codes"""
    AWAITING = 1
    SUCCESS = 2
    FAILED = 3
    QUEUED_RETRY = 4
    SUCCESS_RETRY = 5
    FAILED_RETRIES = 6


class RequestType(IntEnum):
    """RECAP request types"""
    DOCKET = 1
    PDF = 2
    ATTACHMENT = 3


class RECAPWebhookHandler:
    """
    Handles RECAP Fetch webhooks and triggers PDF downloads
    """
    
    def __init__(self, cl_token: str, download_dir: str = "recap_downloads"):
        self.cl_token = cl_token
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self._processed_webhooks: Set[str] = set()  # Track processed webhook IDs
        self._pending_requests: Dict[int, Dict] = {}  # Track pending RECAP requests
    
    def register_request(self, request_id: int, request_info: Dict[str, Any]):
        """
        Register a RECAP request that we're expecting a webhook for
        
        Args:
            request_id: RECAP Fetch request ID
            request_info: Information about the request (docket_number, court, etc.)
        """
        self._pending_requests[request_id] = {
            **request_info,
            'registered_at': datetime.now().isoformat()
        }
        logger.info(f"Registered RECAP request {request_id} for tracking")
    
    async def handle_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process incoming RECAP Fetch webhook
        
        Args:
            webhook_data: Webhook payload from CourtListener
            
        Returns:
            Processing result including downloaded PDFs
        """
        # Extract webhook info
        webhook_info = webhook_data.get('webhook', {})
        payload = webhook_data.get('payload', {})
        
        # Use Idempotency-Key to prevent duplicate processing
        idempotency_key = webhook_info.get('idempotency_key', '')
        if idempotency_key and idempotency_key in self._processed_webhooks:
            logger.info(f"Webhook {idempotency_key} already processed, skipping")
            return {"status": "duplicate", "message": "Already processed"}
        
        if idempotency_key:
            self._processed_webhooks.add(idempotency_key)
        
        # Parse the webhook
        request_id = payload.get('id')
        status = RecapStatus(payload.get('status'))
        request_type = RequestType(payload.get('request_type', 1))
        
        logger.info(f"Processing webhook for RECAP Fetch {request_id} with status {status.name}")
        
        # Get request info if we have it
        request_info = self._pending_requests.get(request_id, {})
        
        result = {
            'webhook_id': idempotency_key,
            'request_id': request_id,
            'status': status.name,
            'request_type': request_type.name,
            'timestamp': datetime.now().isoformat(),
            'request_info': request_info
        }
        
        # Handle based on status
        if status in [RecapStatus.SUCCESS, RecapStatus.SUCCESS_RETRY]:
            if request_type == RequestType.DOCKET:
                result.update(await self._process_docket_completion(payload, request_info))
            elif request_type == RequestType.PDF:
                result.update(await self._process_pdf_completion(payload, request_info))
            elif request_type == RequestType.ATTACHMENT:
                result.update(await self._process_attachment_completion(payload, request_info))
        
        elif status in [RecapStatus.FAILED, RecapStatus.FAILED_RETRIES]:
            error_msg = payload.get('error_message', 'Unknown error')
            logger.error(f"RECAP Fetch failed: {error_msg}")
            result.update({
                'success': False,
                'error': error_msg
            })
        
        elif status in [RecapStatus.AWAITING, RecapStatus.QUEUED_RETRY]:
            logger.info(f"RECAP Fetch {request_id} still processing")
            result.update({
                'success': False,
                'message': 'Still processing'
            })
        
        # Clean up if completed
        if status in [RecapStatus.SUCCESS, RecapStatus.SUCCESS_RETRY, 
                     RecapStatus.FAILED, RecapStatus.FAILED_RETRIES]:
            self._pending_requests.pop(request_id, None)
        
        return result
    
    async def _process_docket_completion(self, payload: Dict[str, Any], 
                                       request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process completed docket fetch"""
        docket_id = payload.get('docket')
        docket_number = payload.get('docket_number') or request_info.get('docket_number')
        court = payload.get('court') or request_info.get('court')
        
        logger.info(f"Processing docket completion for {docket_number} (ID: {docket_id})")
        
        if not all([docket_id, docket_number, court]):
            return {
                'success': False,
                'error': 'Missing required docket information'
            }
        
        # Download PDFs using our PDF handler
        async with RECAPPDFHandler(self.cl_token, str(self.download_dir)) as pdf_handler:
            result = await pdf_handler.process_recap_purchase(
                docket_id=docket_id,
                docket_number=docket_number,
                court=court,
                max_pdfs=request_info.get('max_pdfs')
            )
        
        return result
    
    async def _process_pdf_completion(self, payload: Dict[str, Any], 
                                    request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process completed PDF fetch"""
        recap_document_id = payload.get('recap_document')
        
        logger.info(f"Processing PDF completion for document {recap_document_id}")
        
        # For individual PDFs, we'd download directly
        # This is less common as we usually fetch entire dockets
        return {
            'success': True,
            'recap_document_id': recap_document_id,
            'message': 'Individual PDF fetch completed'
        }
    
    async def _process_attachment_completion(self, payload: Dict[str, Any], 
                                           request_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process completed attachment page fetch"""
        recap_document_id = payload.get('recap_document')
        
        logger.info(f"Processing attachment page completion for document {recap_document_id}")
        
        return {
            'success': True,
            'recap_document_id': recap_document_id,
            'message': 'Attachment page fetch completed'
        }
    
    def get_pending_requests(self) -> Dict[int, Dict]:
        """Get all pending RECAP requests"""
        return self._pending_requests.copy()
    
    def cleanup_old_requests(self, max_age_hours: int = 24):
        """Remove old pending requests that likely won't complete"""
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        old_requests = []
        for request_id, info in self._pending_requests.items():
            registered_at = datetime.fromisoformat(info['registered_at']).timestamp()
            if registered_at < cutoff:
                old_requests.append(request_id)
        
        for request_id in old_requests:
            logger.info(f"Removing old pending request {request_id}")
            self._pending_requests.pop(request_id, None)
        
        return len(old_requests)