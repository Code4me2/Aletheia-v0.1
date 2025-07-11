#!/usr/bin/env python3
"""
List all available courts in CourtListener API
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

def list_courts():
    """Get list of all courts available in CourtListener"""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Aletheia-v0.1/1.0'
    })
    
    print("=== Fetching all courts from CourtListener ===\n")
    
    try:
        # Get courts list with more results per page
        response = session.get(f"{BASE_URL}courts/", params={'page_size': 500})
        response.raise_for_status()
        
        data = response.json()
        courts = data.get('results', [])
        
        print(f"Found {data.get('count', 'unknown')} courts total\n")
        
        # Filter for federal courts we're interested in
        target_names = [
            'delaware', 'eastern district of texas', 
            'northern district of california', 'federal circuit',
            'central district of california', 'southern district of new york'
        ]
        
        print("=== Federal Courts of Interest ===")
        found_courts = []
        
        for court in courts:
            court_name = court.get('full_name', '').lower()
            court_id = court.get('id', '')
            
            # Check if this is one of our target courts
            for target in target_names:
                if target in court_name:
                    found_courts.append(court)
                    print(f"\nCourt ID: {court_id}")
                    print(f"  Full Name: {court.get('full_name')}")
                    print(f"  Short Name: {court.get('short_name')}")
                    print(f"  Jurisdiction: {court.get('jurisdiction')}")
                    print(f"  Citation String: {court.get('citation_string')}")
                    break
        
        # Also show all federal district and appellate courts
        print("\n\n=== All Federal District Courts ===")
        for court in courts:
            if court.get('jurisdiction') == 'FD':  # Federal District
                print(f"{court.get('id'):20} - {court.get('full_name')}")
        
        print("\n\n=== All Federal Appellate Courts ===")
        for court in courts:
            if court.get('jurisdiction') == 'F':  # Federal Appellate
                print(f"{court.get('id'):20} - {court.get('full_name')}")
                
        # Check pagination
        if data.get('next'):
            print(f"\n\nNote: Results are paginated. Showing first {len(courts)} courts.")
            
    except requests.exceptions.RequestException as e:
        print(f"Error fetching courts: {e}")
        if hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    list_courts()