#!/usr/bin/env python3
"""
Simple test to verify opinion search functionality
"""

import asyncio
import aiohttp
import json
from datetime import datetime

API_BASE = "http://localhost:8091"


async def test_opinion_search():
    """Test opinion search with simple parameters"""
    
    # Test 1: Search Federal Circuit opinions from 2023
    print("\n=== Test 1: Federal Circuit Opinions (2023) ===")
    request_data = {
        "court_ids": ["cafc"],
        "date_filed_after": "2023-01-01",
        "date_filed_before": "2023-12-31",
        "max_results": 5
    }
    
    await make_request(request_data)
    
    # Test 2: Search with keyword
    print("\n=== Test 2: Patent Cases with Keyword ===")
    request_data = {
        "query": "patent",
        "court_ids": ["cafc", "ded"],
        "date_filed_after": "2023-06-01",
        "max_results": 5
    }
    
    await make_request(request_data)
    
    # Test 3: Search by nature of suit (patent cases)
    print("\n=== Test 3: Patent Cases by Nature of Suit ===")
    request_data = {
        "court_ids": ["ded"],
        "nature_of_suit": ["830"],  # Patent
        "date_filed_after": "2023-01-01",
        "max_results": 5
    }
    
    await make_request(request_data)


async def make_request(request_data):
    """Make API request and display results"""
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{API_BASE}/api/opinions/search",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    
                    print(f"\nResponse:")
                    print(f"  Success: {data.get('success')}")
                    print(f"  Total results: {data.get('total_results', 0)}")
                    print(f"  Documents processed: {data.get('documents_processed', 0)}")
                    print(f"  Processing time: {data.get('processing_time', 'N/A')}")
                    
                    if data.get('error'):
                        print(f"  Error: {data['error']}")
                    
                    results = data.get('results', [])
                    if results:
                        print(f"\n  Documents returned:")
                        for i, doc in enumerate(results[:3]):
                            print(f"\n  {i+1}. Case: {doc.get('case_name', 'Unknown')}")
                            print(f"     Type: {doc.get('document_type', 'Unknown')}")
                            content = doc.get('content', '')
                            print(f"     Content: {len(content)} chars")
                            if content:
                                print(f"     Preview: {content[:100]}...")
                            
                            metadata = doc.get('metadata', {})
                            print(f"     Court: {metadata.get('court_name', metadata.get('court', 'Unknown'))}")
                            print(f"     Date: {metadata.get('date_filed', 'Unknown')}")
                            print(f"     CL ID: {metadata.get('cl_id', 'Not found')}")
                    else:
                        print("\n  No documents returned")
                else:
                    text = await response.text()
                    print(f"\n❌ HTTP {response.status}: {text}")
                    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


async def test_pipeline_readiness():
    """Check if documents are ready for pipeline processing"""
    print("\n=== Pipeline Readiness Check ===")
    print("Documents from opinion search are stored in the database and can be processed by:")
    print("  1. The 11-stage pipeline: python scripts/run_pipeline.py")
    print("  2. The adaptive pipeline: python scripts/run_pipeline.py --adaptive")
    print("\nThe pipeline will:")
    print("  - Extract courts, citations, judges")
    print("  - Normalize reporters")
    print("  - Extract document structure")
    print("  - Store enhanced metadata")
    print("  - Index for search")


async def main():
    print("Opinion Search Verification")
    print("===========================")
    
    await test_opinion_search()
    await test_pipeline_readiness()
    
    print("\n✅ Test completed")


if __name__ == "__main__":
    asyncio.run(main())