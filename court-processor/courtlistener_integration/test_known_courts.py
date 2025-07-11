#!/usr/bin/env python3
"""
Test with known court IDs based on CourtListener patterns
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

def test_court_ids():
    """Test various court ID patterns"""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Aletheia-v0.1/1.0'
    })
    
    # Based on the pattern we found (ded = District of Delaware)
    # Let's try these patterns
    test_ids = [
        'ded',    # District of Delaware (confirmed)
        'txed',   # Eastern District of Texas
        'cand',   # Northern District of California  
        'cacd',   # Central District of California
        'nysd',   # Southern District of New York
        'njd',    # District of New Jersey
        'cafc',   # Federal Circuit (confirmed)
    ]
    
    print("=== Testing Court IDs ===\n")
    
    found_courts = {}
    
    for court_id in test_ids:
        try:
            # Try to get court info
            response = session.get(f"{BASE_URL}courts/{court_id}/")
            
            if response.status_code == 200:
                court_data = response.json()
                found_courts[court_id] = court_data
                print(f"✓ {court_id}: {court_data.get('full_name')}")
                print(f"    Jurisdiction: {court_data.get('jurisdiction')}")
                print(f"    Short Name: {court_data.get('short_name')}")
            else:
                print(f"✗ {court_id}: Not found (Status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ {court_id}: Error - {e}")
    
    # Now test if we can get dockets from these courts
    print("\n\n=== Testing Docket Retrieval ===")
    
    for court_id, court_data in found_courts.items():
        try:
            response = session.get(f"{BASE_URL}dockets/", params={
                'court': court_id,
                'page_size': 1
            })
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"✓ {court_id}: {count} dockets available")
            else:
                print(f"✗ {court_id}: Cannot retrieve dockets (Status: {response.status_code})")
                
        except Exception as e:
            print(f"✗ {court_id}: Error retrieving dockets - {e}")

if __name__ == "__main__":
    test_court_ids()