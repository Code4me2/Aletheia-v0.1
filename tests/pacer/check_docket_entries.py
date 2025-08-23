#!/usr/bin/env python3
"""
Check what's actually in the docket entries
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_docket_details():
    """Check the actual docket entries"""
    
    cl_token = os.environ.get('COURTLISTENER_TOKEN')
    headers = {'Authorization': f'Token {cl_token}'}
    
    # The docket ID we got
    docket_id = 16793452
    
    print(f"🔍 Checking Docket {docket_id} Details")
    print("=" * 50)
    
    # Get full docket info
    docket_url = f"https://www.courtlistener.com/api/rest/v4/dockets/{docket_id}/"
    
    try:
        response = requests.get(docket_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"Case Name: {data.get('case_name')}")
            print(f"Docket Number: {data.get('docket_number')}")
            print(f"Court: {data.get('court')}")
            print(f"Date Filed: {data.get('date_filed')}")
            print(f"Nature of Suit: {data.get('nature_of_suit', 'N/A')}")
            
            # Get docket entries
            print("\n📚 Docket Entries:")
            entries_url = f"https://www.courtlistener.com/api/rest/v4/docket-entries/?docket={docket_id}"
            entries_response = requests.get(entries_url, headers=headers)
            
            if entries_response.status_code == 200:
                entries_data = entries_response.json()
                print(f"Total Entries: {entries_data.get('count', 0)}")
                
                # Show first 5 entries
                for entry in entries_data.get('results', [])[:5]:
                    print(f"\nEntry #{entry.get('entry_number', '?')}:")
                    print(f"  Date: {entry.get('date_filed', 'N/A')}")
                    print(f"  Description: {entry.get('description', 'N/A')[:80]}")
                    
                    # Check for documents
                    recap_docs = entry.get('recap_documents', [])
                    if recap_docs:
                        print(f"  📎 Documents: {len(recap_docs)}")
                        for doc in recap_docs[:2]:
                            print(f"     - {doc.get('description', 'Document')}")
                            if doc.get('filepath_local'):
                                print(f"       URL: https://www.courtlistener.com{doc.get('filepath_local')}")
    
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 50)
    print("❓ This doesn't look like our patent cases...")
    print("Let me search for the actual patent dockets...")
    
    # Search for our actual cases
    print("\n🔍 Searching for Patent Cases:")
    search_cases = [
        ('2:2024cv00162', 'txed', 'Byteweavr'),
        ('2:2024cv00181', 'txed', 'Cerence'),
    ]
    
    for docket_num, court, name in search_cases:
        print(f"\n📋 Searching: {name} ({docket_num})")
        
        search_url = "https://www.courtlistener.com/api/rest/v4/dockets/"
        params = {
            'docket_number__iexact': docket_num,
            'court': court
        }
        
        try:
            response = requests.get(search_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if data.get('count', 0) > 0:
                    result = data['results'][0]
                    print(f"  ✅ Found! Docket ID: {result.get('id')}")
                    print(f"  Case: {result.get('case_name')}")
                    print(f"  URL: https://www.courtlistener.com{result.get('absolute_url')}")
                else:
                    print(f"  ❌ Not found in CourtListener")
        except Exception as e:
            print(f"  Error: {e}")


if __name__ == "__main__":
    check_docket_details()