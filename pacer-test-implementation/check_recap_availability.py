#!/usr/bin/env python3
"""
Check if patent cases are already available in RECAP's free archive
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

def check_recap_availability():
    """Check if documents are already in RECAP"""
    
    cl_token = os.environ.get('COURTLISTENER_TOKEN')
    
    cases = [
        {'docket': '2:2024cv00162', 'court': 'txed', 'name': 'Byteweavr v. Databricks'},
        {'docket': '2:2024cv00181', 'court': 'txed', 'name': 'Cerence v. Samsung'},
        {'docket': '3:2024cv00217', 'court': 'cand', 'name': 'DoDots v. Apple'},
    ]
    
    print("🔍 Checking RECAP Free Archive")
    print("=" * 50)
    
    for case in cases:
        print(f"\n📋 {case['name']}")
        print(f"   Docket: {case['docket']} ({case['court'].upper()})")
        
        # Search CourtListener for the docket
        search_url = 'https://www.courtlistener.com/api/rest/v4/dockets/'
        params = {
            'docket_number': case['docket'],
            'court': case['court']
        }
        headers = {'Authorization': f'Token {cl_token}'}
        
        try:
            response = requests.get(search_url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                if isinstance(count, str):
                    count = int(count) if count.isdigit() else 0
                if count > 0:
                    print("   ✅ Found in RECAP! (FREE ACCESS)")
                    docket = data['results'][0]
                    print(f"   - Case name: {docket.get('case_name', 'N/A')}")
                    print(f"   - Date filed: {docket.get('date_filed', 'N/A')}")
                    print(f"   - RECAP URL: https://www.courtlistener.com{docket.get('absolute_url', '')}")
                else:
                    print("   ❌ Not in RECAP free archive")
            else:
                print(f"   ⚠️  Search error: {response.status_code}")
        except Exception as e:
            print(f"   💥 Error: {e}")
    
    print("\n" + "=" * 50)
    print("💡 TIP: Documents in RECAP are FREE to access!")
    print("   No PACER fees required for these documents")


if __name__ == "__main__":
    check_recap_availability()