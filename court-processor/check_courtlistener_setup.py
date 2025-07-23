#!/usr/bin/env python3
"""
Quick check for CourtListener API setup
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.service_config import COURTLISTENER_API_TOKEN
from services.courtlistener_service import CourtListenerService
import asyncio


async def check_setup():
    print("\n" + "="*60)
    print("COURTLISTENER API SETUP CHECK")
    print("="*60)
    
    # Check environment variable
    env_token = os.getenv('COURTLISTENER_API_TOKEN')
    config_token = COURTLISTENER_API_TOKEN
    
    print(f"\n1. Environment variable COURTLISTENER_API_TOKEN:")
    print(f"   Set: {'Yes' if env_token else 'No'}")
    if env_token:
        print(f"   Length: {len(env_token)} chars")
        print(f"   First 10 chars: {env_token[:10]}...")
    
    print(f"\n2. Config token (from service_config.py):")
    print(f"   Set: {'Yes' if config_token else 'No'}")
    if config_token:
        print(f"   Length: {len(config_token)} chars")
        print(f"   First 10 chars: {config_token[:10]}...")
    
    # Test actual API connection
    print(f"\n3. Testing API connection...")
    try:
        service = CourtListenerService()
        print(f"   Service initialized with token: {'Yes' if service.api_key else 'No'}")
        
        # Try a simple request
        results = await service.fetch_opinions(max_results=1)
        
        if results:
            print(f"   ✅ API connection successful!")
            print(f"   Retrieved {len(results)} test document(s)")
        else:
            print(f"   ⚠️ API returned no results")
        
        await service.close()
        
    except Exception as e:
        print(f"   ❌ API connection failed: {e}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    
    if not env_token and not config_token:
        print("\n⚠️ No API token found!")
        print("Set the token using one of these methods:")
        print("\n1. Environment variable (recommended):")
        print("   export COURTLISTENER_API_TOKEN='your_token_here'")
        print("\n2. In Docker:")
        print("   Add to docker-compose.yml under court-processor service:")
        print("   environment:")
        print("     - COURTLISTENER_API_TOKEN=your_token_here")
        print("\n3. .env file:")
        print("   COURTLISTENER_API_TOKEN=your_token_here")
    else:
        print("\n✅ API token is configured")
        print("Ready to run the test suite:")
        print("   docker-compose exec court-processor python test_suite.py")


if __name__ == "__main__":
    asyncio.run(check_setup())