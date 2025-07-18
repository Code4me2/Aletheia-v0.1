#!/usr/bin/env python3
"""
Debug Search Results Structure

Analyzes the structure of search results to understand how to extract opinion IDs.
"""
import asyncio
import sys
import os
import json

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

async def debug_search_results():
    """Debug search results structure"""
    
    print("=== DEBUG SEARCH RESULTS STRUCTURE ===\n")
    
    cl_service = CourtListenerService()
    
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{cl_service.base_url}/search/",
            headers=cl_service._get_headers(),
            params={
                "q": "Gilstrap",
                "type": "o",  # Opinions
                "court": "txed",
                "page_size": 3
            },
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                
                print(f"📊 Found {len(results)} search results")
                
                for i, result in enumerate(results):
                    print(f"\n📄 Result {i+1}:")
                    print(f"   Available fields: {list(result.keys())}")
                    print(f"   Case name: {result.get('caseName', 'Unknown')}")
                    print(f"   Court: {result.get('court', 'Unknown')}")
                    print(f"   Date: {result.get('dateFiled', 'Unknown')}")
                    print(f"   Absolute URL: {result.get('absolute_url', 'None')}")
                    
                    # Check for different ID fields
                    id_fields = ['id', 'opinion_id', 'pk', 'uuid']
                    for field in id_fields:
                        if field in result:
                            print(f"   {field}: {result[field]}")
                    
                    # Show full structure for first result
                    if i == 0:
                        print(f"\n   📋 Full structure:")
                        for key, value in result.items():
                            if isinstance(value, str) and len(value) > 100:
                                print(f"      {key}: {value[:100]}...")
                            else:
                                print(f"      {key}: {value}")
                    
                    # Try to extract opinion ID from absolute_url
                    abs_url = result.get('absolute_url', '')
                    if abs_url and '/opinion/' in abs_url:
                        # Extract ID from URL like /opinion/123456/case-name/
                        parts = abs_url.split('/')
                        if len(parts) > 2 and parts[1] == 'opinion':
                            opinion_id = parts[2]
                            print(f"   🎯 Extracted opinion ID from URL: {opinion_id}")
                            
                            # Test fetching this opinion
                            async with session.get(
                                f"{cl_service.base_url}/opinions/{opinion_id}/",
                                headers=cl_service._get_headers(),
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as opinion_response:
                                
                                if opinion_response.status == 200:
                                    opinion_data = await opinion_response.json()
                                    text_length = len(opinion_data.get('plain_text', ''))
                                    print(f"      ✅ Successfully fetched opinion: {text_length:,} chars")
                                    return opinion_id, opinion_data
                                else:
                                    print(f"      ❌ Failed to fetch opinion: HTTP {opinion_response.status}")
                
    return None, None

if __name__ == "__main__":
    try:
        opinion_id, opinion_data = asyncio.run(debug_search_results())
        if opinion_id:
            print(f"\n✅ Successfully identified working opinion ID: {opinion_id}")
        else:
            print(f"\n❌ Could not find working opinion ID")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()