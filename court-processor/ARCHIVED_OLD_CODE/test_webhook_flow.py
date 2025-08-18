#!/usr/bin/env python3
"""
Test RECAP webhook flow
Demonstrates submitting requests and simulating webhook responses
"""

import asyncio
import os
import logging
import json
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_webhook_registration():
    """Test registering a RECAP request with the webhook handler"""
    
    webhook_url = "http://localhost:5001/webhook/recap-fetch"
    
    # Test registration
    register_data = {
        'request_id': 12345,
        'request_info': {
            'docket_number': '2:2024cv00162',
            'court': 'txed',
            'request_type': 'docket',
            'max_pdfs': 5
        }
    }
    
    async with aiohttp.ClientSession() as session:
        # Register the request
        async with session.post(f"{webhook_url}/register", json=register_data) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"✅ Registration successful: {result}")
            else:
                logger.error(f"Registration failed: {response.status}")
                return False
        
        # Check pending requests
        async with session.get(f"{webhook_url}/pending") as response:
            if response.status == 200:
                pending = await response.json()
                logger.info(f"📋 Pending requests: {pending}")
        
        # Simulate a webhook from CourtListener
        webhook_data = {
            "webhook": {
                "event_type": "recap_fetch.terminated",
                "date_created": datetime.now().isoformat(),
                "idempotency_key": "test-webhook-123"
            },
            "payload": {
                "id": 12345,
                "status": 2,  # Success
                "docket": 16793452,  # This will trigger the mismatch handling
                "request_type": 1,  # Docket
                "court": "txed",
                "docket_number": "2:2024cv00162",
                "error_message": None
            }
        }
        
        logger.info("\n🔔 Simulating webhook delivery...")
        
        headers = {
            'Content-Type': 'application/json',
            'Idempotency-Key': 'test-webhook-123'
        }
        
        async with session.post(webhook_url, json=webhook_data, headers=headers) as response:
            if response.status == 200:
                result = await response.json()
                logger.info(f"✅ Webhook processed: {json.dumps(result, indent=2)}")
            else:
                text = await response.text()
                logger.error(f"Webhook failed ({response.status}): {text}")
    
    return True


async def test_real_webhook_flow():
    """Test with real RECAP submission (requires credentials)"""
    
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from services.recap.authenticated_client import AuthenticatedRECAPClient
    
    # Get credentials
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    pacer_username = os.getenv('PACER_USERNAME')
    pacer_password = os.getenv('PACER_PASSWORD')
    
    if not all([cl_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials")
        return False
    
    webhook_url = "http://localhost:5001/webhook/recap-fetch"
    
    try:
        async with AuthenticatedRECAPClient(
            cl_token, pacer_username, pacer_password, webhook_url
        ) as client:
            logger.info("✅ PACER authentication successful")
            
            # Submit request with webhook registration
            result = await client.fetch_docket_with_webhook(
                docket_number='2:2024cv00162',
                court='txed',
                show_parties_and_counsel=True,
                date_start='2024-01-01',
                date_end='2024-12-31',
                max_pdfs=5  # Include in request info
            )
            
            if result and 'id' in result:
                logger.info(f"📨 RECAP request submitted: ID {result['id']}")
                logger.info("⏳ Webhook will be called when processing completes")
                logger.info(f"   Monitor webhook server logs for completion")
                
                # In production, the webhook would be called automatically
                # For testing, you can manually check the pending requests
                await asyncio.sleep(2)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{webhook_url}/pending") as response:
                        if response.status == 200:
                            pending = await response.json()
                            logger.info(f"\n📋 Current pending requests: {json.dumps(pending, indent=2)}")
            
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False
    
    return True


async def main():
    """Run webhook tests"""
    
    logger.info("=== RECAP Webhook Flow Test ===\n")
    
    # Test 1: Basic webhook registration and processing
    logger.info("Test 1: Webhook Registration and Simulation")
    logger.info("-" * 50)
    await test_webhook_registration()
    
    # Test 2: Real RECAP submission with webhook
    logger.info("\n\nTest 2: Real RECAP Submission with Webhook")
    logger.info("-" * 50)
    await test_real_webhook_flow()
    
    logger.info("\n✅ Webhook flow test completed!")
    logger.info("\nTo receive real webhooks:")
    logger.info("1. Configure webhook URL in CourtListener account")
    logger.info("2. Use ngrok or similar to expose local webhook server")
    logger.info("3. Submit RECAP requests and monitor webhook logs")


if __name__ == "__main__":
    asyncio.run(main())