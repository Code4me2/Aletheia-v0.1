#!/usr/bin/env python3
"""
Debug script to see what fields are returned by search_with_filters
"""

import asyncio
import json
import os
from dotenv import load_dotenv
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.courtlistener_service import CourtListenerService

load_dotenv()


async def debug_search():
    """Debug what search_with_filters returns"""
    
    cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_TOKEN')
    cl_service = CourtListenerService(cl_token)
    
    print("Testing search_with_filters...")
    
    try:
        # Simple search for recent opinions
        results = await cl_service.search_with_filters(
            search_type='o',  # Opinions
            court_ids=['cafc'],
            date_range=('2023-01-01', '2023-12-31'),
            max_results=2
        )
        
        print(f"\nFound {len(results)} results")
        
        if results:
            print("\nFirst result structure:")
            first_result = results[0]
            
            # Print all keys
            print("\nTop-level keys:")
            for key in sorted(first_result.keys()):
                value = first_result[key]
                if isinstance(value, str) and len(value) > 100:
                    print(f"  {key}: <string with {len(value)} chars>")
                elif isinstance(value, dict):
                    print(f"  {key}: <dict with {len(value)} keys>")
                elif isinstance(value, list):
                    print(f"  {key}: <list with {len(value)} items>")
                else:
                    print(f"  {key}: {value}")
            
            # Check for text fields
            print("\nText fields:")
            text_fields = ['plain_text', 'html', 'html_lawbox', 'html_columbia', 
                          'xml_harvard', 'text', 'snippet']
            for field in text_fields:
                if field in first_result:
                    content = first_result[field]
                    if content:
                        print(f"  {field}: {len(content)} chars")
                    else:
                        print(f"  {field}: empty")
            
            # Check download URL
            if 'download_url' in first_result:
                print(f"\nDownload URL: {first_result['download_url']}")
            
            # Pretty print full result
            print("\nFull first result:")
            print(json.dumps(first_result, indent=2, default=str))
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await cl_service.close()


if __name__ == "__main__":
    asyncio.run(debug_search())