#!/usr/bin/env python3
"""Quick verification of CourtListener API"""

import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

def quick_test():
    """Quick API test"""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Aletheia-v0.1/1.0'
    })
    
    print("Testing CourtListener API...")
    
    # Test 1: Basic connectivity
    try:
        resp = session.get(BASE_URL)
        print(f"✓ API Connected (Status: {resp.status_code})")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return
    
    # Test 2: Get Delaware court info
    try:
        resp = session.get(f"{BASE_URL}courts/ded/")
        court = resp.json()
        print(f"✓ Court found: {court.get('full_name')}")
    except Exception as e:
        print(f"✗ Court lookup failed: {e}")
    
    # Test 3: Get recent dockets (last 7 days)
    try:
        date_from = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        params = {
            'court': 'ded',
            'date_filed__gte': date_from,
            'page_size': 5
        }
        resp = session.get(f"{BASE_URL}dockets/", params=params)
        data = resp.json()
        count = data.get('count', 0)
        print(f"✓ Found {count} dockets in Delaware (last 7 days)")
        
        # Show first case
        if data.get('results'):
            case = data['results'][0]
            print(f"  Example: {case.get('case_name', 'N/A')} ({case.get('docket_number', 'N/A')})")
    except Exception as e:
        print(f"✗ Docket retrieval failed: {e}")
    
    print("\nAPI verification complete!")

if __name__ == "__main__":
    quick_test()