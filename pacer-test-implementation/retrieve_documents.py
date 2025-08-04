#!/usr/bin/env python3
"""
Retrieve the actual documents from completed RECAP requests
"""

import os
import requests
from dotenv import load_dotenv
import time

load_dotenv()

def retrieve_recap_documents():
    """Retrieve documents from our successful RECAP requests"""
    
    cl_token = os.environ.get('COURTLISTENER_TOKEN')
    
    # Request IDs from our test
    request_ids = {
        1666274: "Byteweavr v. Databricks",
        1666275: "Cerence v. Samsung",
    }
    
    print("📥 Retrieving Documents from RECAP")
    print("=" * 50)
    
    for request_id, case_name in request_ids.items():
        print(f"\n📋 {case_name} (Request ID: {request_id})")
        
        # Check request status
        status_url = f"https://www.courtlistener.com/api/rest/v4/recap-fetch/{request_id}/"
        headers = {'Authorization': f'Token {cl_token}'}
        
        try:
            response = requests.get(status_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                print(f"   Status: {status}")
                print(f"   Court: {data.get('court')}")
                print(f"   Docket Number: {data.get('docket_number')}")
                
                # Check if docket was created
                docket_id = data.get('docket')
                if docket_id:
                    print(f"   ✅ Docket ID: {docket_id}")
                    
                    # Get the docket details
                    docket_url = f"https://www.courtlistener.com/api/rest/v4/dockets/{docket_id}/"
                    docket_response = requests.get(docket_url, headers=headers)
                    
                    if docket_response.status_code == 200:
                        docket_data = docket_response.json()
                        print(f"   📄 Case Name: {docket_data.get('case_name')}")
                        print(f"   📅 Date Filed: {docket_data.get('date_filed')}")
                        print(f"   👨‍⚖️ Judge: {docket_data.get('assigned_to_str', 'N/A')}")
                        print(f"   🔗 CourtListener URL: https://www.courtlistener.com{docket_data.get('absolute_url', '')}")
                        
                        # Check for docket entries (the actual documents)
                        entries_url = f"https://www.courtlistener.com/api/rest/v4/docket-entries/?docket={docket_id}"
                        entries_response = requests.get(entries_url, headers=headers)
                        
                        if entries_response.status_code == 200:
                            entries_data = entries_response.json()
                            entry_count = entries_data.get('count', 0)
                            print(f"   📚 Docket Entries: {entry_count}")
                            
                            if entry_count > 0:
                                # Show first few entries
                                print("   📝 Recent Entries:")
                                for i, entry in enumerate(entries_data.get('results', [])[:3]):
                                    entry_num = entry.get('entry_number', '?')
                                    desc = entry.get('description', 'No description')[:60]
                                    print(f"      #{entry_num}: {desc}...")
                else:
                    print("   ⚠️  No docket created yet")
                    
                # Check for documents
                if data.get('recap_document'):
                    print(f"   📎 Document ID: {data.get('recap_document')}")
                    
            else:
                print(f"   ❌ Could not retrieve status: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error: {e}")
    
    print("\n" + "=" * 50)
    print("\n🔍 How to Access Documents:")
    print("1. Via API: Use the docket ID to fetch docket entries")
    print("2. Via Web: Visit the CourtListener URLs above")
    print("3. Via PDF: Look for recap_document IDs in the docket entries")
    
    # Show how to get PDFs
    print("\n📄 To Download PDFs:")
    print("```python")
    print("# Get docket entries")
    print("entries_url = f'https://www.courtlistener.com/api/rest/v4/docket-entries/?docket={docket_id}'")
    print("# Each entry may have recap_documents with download URLs")
    print("```")


if __name__ == "__main__":
    retrieve_recap_documents()