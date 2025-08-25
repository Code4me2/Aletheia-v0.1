#!/usr/bin/env python3
"""
RECAP Webhook Server
Flask application to receive and process RECAP Fetch webhooks
"""

import os
import logging
import json
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from functools import wraps
import hmac
import hashlib
from typing import Optional

# Add parent directory to path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.recap.webhook_handler import RECAPWebhookHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize webhook handler
webhook_handler: Optional[RECAPWebhookHandler] = None


def init_webhook_handler():
    """Initialize the webhook handler with credentials"""
    global webhook_handler
    
    cl_token = os.getenv('COURTLISTENER_API_TOKEN') or os.getenv('COURTLISTENER_API_KEY')
    if not cl_token:
        logger.error("Missing CourtListener API token")
        return False
    
    download_dir = os.getenv('RECAP_DOWNLOAD_DIR', 'recap_downloads')
    webhook_handler = RECAPWebhookHandler(cl_token, download_dir)
    logger.info(f"Initialized webhook handler with download dir: {download_dir}")
    return True


def async_route(f):
    """Decorator to run async routes"""
    @wraps(f)
    def wrapped(*args, **kwargs):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(f(*args, **kwargs))
        finally:
            loop.close()
    return wrapped


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify webhook signature if configured
    
    Args:
        payload: Raw request body
        signature: Signature from header
        secret: Webhook secret
        
    Returns:
        True if valid or no secret configured
    """
    if not secret:
        return True
    
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'recap-webhook-server',
        'timestamp': datetime.now().isoformat(),
        'handler_initialized': webhook_handler is not None
    })


@app.route('/webhook/recap-fetch', methods=['POST'])
@async_route
async def recap_webhook():
    """
    Receive and process RECAP Fetch webhooks
    
    Expected webhook format:
    {
        "webhook": {
            "event_type": "recap_fetch.terminated",
            "date_created": "2024-07-25T00:00:00Z"
        },
        "payload": {
            "id": 12345,
            "status": 2,
            "docket": 16793452,
            "request_type": 1,
            "court": "txed",
            "docket_number": "2:2024cv00181",
            "error_message": null
        }
    }
    """
    if not webhook_handler:
        return jsonify({'error': 'Webhook handler not initialized'}), 503
    
    try:
        # Get raw payload for signature verification
        raw_payload = request.get_data()
        
        # Verify signature if secret is configured
        webhook_secret = os.getenv('RECAP_WEBHOOK_SECRET')
        if webhook_secret:
            signature = request.headers.get('X-Webhook-Signature', '')
            if not verify_webhook_signature(raw_payload, signature, webhook_secret):
                logger.warning("Invalid webhook signature")
                return jsonify({'error': 'Invalid signature'}), 401
        
        # Parse webhook data
        webhook_data = request.get_json()
        if not webhook_data:
            return jsonify({'error': 'Invalid JSON payload'}), 400
        
        # Add idempotency key from headers if present
        idempotency_key = request.headers.get('Idempotency-Key')
        if idempotency_key and 'webhook' in webhook_data:
            webhook_data['webhook']['idempotency_key'] = idempotency_key
        
        # Log webhook receipt
        logger.info(f"Received RECAP webhook: {json.dumps(webhook_data, indent=2)}")
        
        # Process webhook
        result = await webhook_handler.handle_webhook(webhook_data)
        
        # Return success
        return jsonify({
            'status': 'success',
            'result': result,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Webhook processing error: {e}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/webhook/recap-fetch/register', methods=['POST'])
def register_request():
    """
    Register a RECAP request for tracking
    
    Used to associate request IDs with docket information before webhooks arrive
    """
    if not webhook_handler:
        return jsonify({'error': 'Webhook handler not initialized'}), 503
    
    try:
        data = request.get_json()
        request_id = data.get('request_id')
        request_info = data.get('request_info', {})
        
        if not request_id:
            return jsonify({'error': 'Missing request_id'}), 400
        
        webhook_handler.register_request(request_id, request_info)
        
        return jsonify({
            'status': 'success',
            'request_id': request_id,
            'message': 'Request registered for tracking'
        }), 200
        
    except Exception as e:
        logger.error(f"Error registering request: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/webhook/recap-fetch/pending', methods=['GET'])
def get_pending_requests():
    """Get all pending RECAP requests"""
    if not webhook_handler:
        return jsonify({'error': 'Webhook handler not initialized'}), 503
    
    pending = webhook_handler.get_pending_requests()
    return jsonify({
        'pending_count': len(pending),
        'requests': pending
    })


@app.route('/webhook/recap-fetch/cleanup', methods=['POST'])
def cleanup_old_requests():
    """Clean up old pending requests"""
    if not webhook_handler:
        return jsonify({'error': 'Webhook handler not initialized'}), 503
    
    max_age_hours = request.args.get('max_age_hours', 24, type=int)
    removed = webhook_handler.cleanup_old_requests(max_age_hours)
    
    return jsonify({
        'status': 'success',
        'removed_count': removed,
        'max_age_hours': max_age_hours
    })


if __name__ == '__main__':
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize handler
    if not init_webhook_handler():
        logger.error("Failed to initialize webhook handler")
        sys.exit(1)
    
    # Get configuration
    host = os.getenv('WEBHOOK_HOST', '0.0.0.0')
    port = int(os.getenv('WEBHOOK_PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting RECAP webhook server on {host}:{port}")
    
    # Run Flask app
    app.run(host=host, port=port, debug=debug)