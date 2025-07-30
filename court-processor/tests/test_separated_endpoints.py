#!/usr/bin/env python3
"""
Test script for the separated Opinion and RECAP endpoints
"""

import asyncio
import aiohttp
import json
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API base URL
API_BASE = "http://localhost:8091"


async def test_health_check():
    """Test API health check"""
    print("\n=== Testing Health Check ===")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ API Status: {data['status']}")
                    print(f"   Version: {data['version']}")
                    print(f"   Endpoints: {json.dumps(data['endpoints'], indent=2)}")
                    return True
                else:
                    print(f"❌ Health check failed: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


async def test_opinion_search():
    """Test broad opinion search"""
    print("\n=== Testing Opinion Search (Broad) ===")
    
    # Calculate date 30 days ago
    date_30_days_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    request_data = {
        "query": "intellectual property patent",
        "court_ids": ["cafc", "ded"],
        "date_filed_after": date_30_days_ago,
        "max_results": 10
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/api/opinions/search",
                json=request_data
            ) as response:
                data = await response.json()
                
                if response.status == 200 and data.get('success'):
                    print(f"✅ Opinion search successful")
                    print(f"   Total results: {data['total_results']}")
                    print(f"   Documents processed: {data['documents_processed']}")
                    print(f"   Processing time: {data['processing_time']}")
                    
                    # Show first few results
                    if data.get('results'):
                        print("\n   First 3 results:")
                        for i, doc in enumerate(data['results'][:3]):
                            print(f"\n   {i+1}. {doc.get('case_name', 'Unknown')}")
                            print(f"      Court: {doc.get('metadata', {}).get('court_name', 'Unknown')}")
                            print(f"      Date: {doc.get('metadata', {}).get('date_filed', 'Unknown')}")
                    
                    return True
                else:
                    print(f"❌ Opinion search failed: {data.get('error', 'Unknown error')}")
                    return False
                    
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False


async def test_recap_docket_free():
    """Test RECAP docket retrieval (free from archive)"""
    print("\n=== Testing RECAP Docket (Free Archive) ===")
    
    # Use a known case that might be in RECAP
    request_data = {
        "docket_number": "1:2021cv00001",  # Example docket
        "court": "dcd",  # DC District
        "include_documents": True,
        "max_documents": 5
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/api/recap/docket",
                json=request_data
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    print(f"{'✅' if data['success'] else '❌'} RECAP docket request")
                    print(f"   In RECAP: {data['in_recap']}")
                    print(f"   Purchased from PACER: {data['purchased_from_pacer']}")
                    if data.get('case_name'):
                        print(f"   Case: {data['case_name']}")
                    print(f"   Documents: {data['documents_downloaded']}")
                    
                    if data.get('error'):
                        print(f"   Error: {data['error']}")
                    
                    return data['success']
                else:
                    print(f"❌ RECAP request failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False


async def test_recap_docket_purchase():
    """Test RECAP docket purchase from PACER"""
    print("\n=== Testing RECAP Docket (PACER Purchase) ===")
    
    # Check if PACER credentials are configured
    if not os.getenv('PACER_USERNAME'):
        print("⚠️  PACER credentials not configured - skipping purchase test")
        return None
    
    # Use a specific case for testing
    request_data = {
        "docket_number": "2:2024cv00181",
        "court": "txed",
        "include_documents": True,
        "max_documents": 3,
        "date_start": "2024-01-01",
        "date_end": "2024-12-31",
        "force_purchase": False  # Only purchase if not in RECAP
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    print("⚠️  This may incur PACER charges if the docket is not in RECAP!")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/api/recap/docket",
                json=request_data
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    print(f"{'✅' if data['success'] else '❌'} RECAP/PACER request")
                    print(f"   In RECAP: {data['in_recap']}")
                    print(f"   Purchased from PACER: {data['purchased_from_pacer']}")
                    
                    if data.get('purchase_cost'):
                        print(f"   Cost: ${data['purchase_cost']:.2f}")
                    
                    if data.get('webhook_registered'):
                        print(f"   Webhook registered: Yes")
                        print(f"   Request ID: {data.get('request_id')}")
                        print(f"   Status URL: {data.get('status_url')}")
                    
                    if data.get('error'):
                        print(f"   Error: {data['error']}")
                    
                    return data
                else:
                    print(f"❌ RECAP request failed: HTTP {response.status}")
                    return None
                    
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None


async def test_recap_status(request_id: int):
    """Test RECAP request status check"""
    print(f"\n=== Testing RECAP Status Check (ID: {request_id}) ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{API_BASE}/api/recap/status/{request_id}"
            ) as response:
                data = await response.json()
                
                if response.status == 200:
                    print(f"✅ Status check successful")
                    print(f"   Status: {data['status']}")
                    print(f"   Completed: {data['completed']}")
                    print(f"   Documents processed: {data['documents_processed']}")
                    
                    if data.get('error'):
                        print(f"   Error: {data['error']}")
                    
                    return data
                else:
                    print(f"❌ Status check failed: HTTP {response.status}")
                    return None
                    
    except Exception as e:
        print(f"❌ Request error: {e}")
        return None


async def test_data_flows_documentation():
    """Test documentation endpoint"""
    print("\n=== Testing Data Flows Documentation ===")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{API_BASE}/api/docs/flows") as response:
                if response.status == 200:
                    data = await response.json()
                    print("✅ Documentation retrieved")
                    print("\nOpinion Flow:")
                    print(f"  - {data['opinion_flow']['description']}")
                    print(f"  - Source: {data['opinion_flow']['data_source']}")
                    print(f"  - Cost: {data['opinion_flow']['cost']}")
                    
                    print("\nRECAP Flow:")
                    print(f"  - {data['recap_flow']['description']}")
                    print(f"  - Source: {data['recap_flow']['data_source']}")
                    print(f"  - Cost: {data['recap_flow']['cost']}")
                    
                    return True
                else:
                    print(f"❌ Documentation retrieval failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Request error: {e}")
        return False


async def main():
    """Run all tests"""
    print("Court Processor API Test Suite")
    print("==============================")
    
    # Check if API is running
    api_healthy = await test_health_check()
    if not api_healthy:
        print("\n❌ API is not running. Please start it with:")
        print("   cd court-processor/api")
        print("   python court_processor_api.py")
        return
    
    # Test documentation
    await test_data_flows_documentation()
    
    # Test opinion search
    await test_opinion_search()
    
    # Test RECAP free search
    await test_recap_docket_free()
    
    # Test RECAP purchase (if credentials available)
    purchase_result = await test_recap_docket_purchase()
    
    # If we got a request ID, check its status
    if purchase_result and purchase_result.get('request_id'):
        await asyncio.sleep(2)  # Wait a bit
        await test_recap_status(purchase_result['request_id'])
    
    print("\n✅ Test suite completed")


if __name__ == "__main__":
    asyncio.run(main())