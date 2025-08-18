#!/usr/bin/env python3
"""
Search specifically for Gilstrap cases using the CourtListener search API
"""
import asyncio
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.courtlistener_service import CourtListenerService

async def search_for_gilstrap():
    print("="*80)
    print("SEARCHING FOR GILSTRAP CASES")
    print("="*80)
    
    cl_service = CourtListenerService()
    
    try:
        # Search using the search API with Gilstrap keyword
        session = await cl_service._get_session()
        search_url = f"{cl_service.BASE_URL}/api/rest/v4/search/"
        
        params = {
            'q': 'Gilstrap',
            'type': 'o',  # opinions
            'court': 'txed',
            'filed_after': '2016-01-01',
            'filed_before': '2017-12-31',
            'page_size': 10
        }
        
        print(f"Search params: {json.dumps(params, indent=2)}")
        
        async with session.get(search_url, params=params, headers=cl_service.headers) as response:
            if response.status == 200:
                results = await response.json()
                print(f"\nFound {results.get('count', 0)} total results")
                
                if results.get('results'):
                    print("\nGilstrap cases found:")
                    for i, result in enumerate(results['results'][:10]):
                        print(f"\n{i+1}. {result.get('caseName', 'Unknown')}")
                        print(f"   Docket: {result.get('docketNumber', 'N/A')}")
                        print(f"   Filed: {result.get('dateFiled', 'N/A')}")
                        print(f"   Judge: {result.get('judge', 'N/A')}")
                        print(f"   Opinion ID: {result.get('id', 'N/A')}")
                        
                        # Extract the opinion ID for fetching
                        if result.get('id'):
                            print(f"   URL: {cl_service.BASE_URL}/api/rest/v4/opinions/{result['id']}/")
                else:
                    print("\nNo Gilstrap cases found with search API")
            else:
                print(f"Search failed: {response.status}")
                text = await response.text()
                print(f"Error: {text}")
                
    finally:
        await cl_service.close()

if __name__ == "__main__":
    asyncio.run(search_for_gilstrap())