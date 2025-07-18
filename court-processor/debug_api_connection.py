#!/usr/bin/env python3
"""
Debug API Connection Issue

Tests CourtListener API connection to diagnose timeout issues.
"""
import asyncio
import sys
import os

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

async def debug_api_connection():
    """Debug API connection issues"""
    
    print("=== DEBUG API CONNECTION ===\n")
    
    cl_service = CourtListenerService()
    
    print(f"🔧 Configuration:")
    print(f"   • Base URL: {cl_service.base_url}")
    print(f"   • API Key configured: {'Yes' if cl_service.api_key else 'No'}")
    print(f"   • Timeout: {cl_service.timeout}s")
    
    if cl_service.api_key:
        print(f"   • API Key prefix: {cl_service.api_key[:10]}...")
    
    print(f"\n🔍 Testing simple connection...")
    
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            print("   📡 Making test request...")
            
            async with session.get(
                f"{cl_service.base_url}/opinions/",
                headers=cl_service._get_headers(),
                params={"page_size": 1},
                timeout=aiohttp.ClientTimeout(total=30)  # Longer timeout for debugging
            ) as response:
                
                print(f"   ✅ Response received: HTTP {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    print(f"   📊 Data received: {len(data.get('results', []))} results")
                    print(f"   🎉 API connection is working!")
                    return True
                else:
                    text = await response.text()
                    print(f"   ❌ HTTP {response.status}: {text[:200]}")
                    return False
                    
    except asyncio.TimeoutError:
        print(f"   ❌ Request timed out after 30 seconds")
        return False
    except Exception as e:
        print(f"   ❌ Connection error: {str(e)}")
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(debug_api_connection())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)