#!/usr/bin/env python3
"""
Search all pages to find specific courts
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

def search_all_courts():
    """Search all courts for our targets"""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Aletheia-v0.1/1.0'
    })
    
    # What we're looking for
    targets = {
        'Eastern District of Texas': None,
        'Northern District of California': None,
        'Central District of California': None,
        'Southern District of New York': None,
        'District of Delaware': 'ded',  # Already found
        'Federal Circuit': 'cafc'  # Already found
    }
    
    print("=== Searching all courts for targets ===\n")
    
    page = 1
    total_searched = 0
    
    while page <= 20:  # Search up to 20 pages
        try:
            response = session.get(f"{BASE_URL}courts/", params={
                'page': page, 
                'page_size': 200,
                'jurisdiction': 'FD'  # Try filtering by Federal District
            })
            
            if response.status_code != 200:
                # Try without filter
                response = session.get(f"{BASE_URL}courts/", params={
                    'page': page, 
                    'page_size': 200
                })
            
            response.raise_for_status()
            data = response.json()
            courts = data.get('results', [])
            
            if not courts:
                break
            
            for court in courts:
                total_searched += 1
                full_name = court.get('full_name', '')
                
                # Check each target
                for target, found_id in targets.items():
                    if found_id is None:  # Not found yet
                        if any(word in full_name.lower() for word in target.lower().split()):
                            if 'district' in target.lower() and 'district' in full_name.lower():
                                # Found a match!
                                targets[target] = court.get('id')
                                print(f"FOUND: {target}")
                                print(f"  ID: {court.get('id')}")
                                print(f"  Full Name: {full_name}")
                                print(f"  Jurisdiction: {court.get('jurisdiction')}")
                                print()
            
            if not data.get('next'):
                break
                
            page += 1
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break
    
    print(f"\n=== Search Complete ===")
    print(f"Searched {total_searched} courts across {page} pages\n")
    
    print("=== Final Results ===")
    for target, court_id in targets.items():
        if court_id:
            print(f"✓ {target}: {court_id}")
        else:
            print(f"✗ {target}: NOT FOUND")
    
    # Let's try a different approach - search by short name
    print("\n=== Trying search by keywords ===")
    
    keywords = ['texas', 'california', 'york']
    
    for keyword in keywords:
        try:
            response = session.get(f"{BASE_URL}courts/", params={
                'page_size': 100,
                'search': keyword  # Try search parameter
            })
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nResults for '{keyword}':")
                for court in data.get('results', [])[:5]:
                    if 'district' in court.get('full_name', '').lower():
                        print(f"  - {court.get('id')}: {court.get('full_name')}")
        except:
            pass

if __name__ == "__main__":
    search_all_courts()