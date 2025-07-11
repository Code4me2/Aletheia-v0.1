#!/usr/bin/env python3
"""
Find specific district courts in CourtListener API
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

def find_district_courts():
    """Search for district courts"""
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Aletheia-v0.1/1.0'
    })
    
    print("=== Searching for District Courts ===\n")
    
    # Courts we're looking for
    search_terms = [
        'Delaware',
        'Eastern District of Texas', 
        'Northern District of California',
        'Central District of California',
        'Southern District of New York',
        'District of New Jersey'
    ]
    
    page = 1
    found_courts = {}
    
    while True:
        try:
            response = session.get(f"{BASE_URL}courts/", params={'page': page, 'page_size': 100})
            response.raise_for_status()
            
            data = response.json()
            courts = data.get('results', [])
            
            if not courts:
                break
                
            for court in courts:
                full_name = court.get('full_name', '')
                court_id = court.get('id', '')
                
                # Check if this matches any of our search terms
                for term in search_terms:
                    if term.lower() in full_name.lower():
                        found_courts[term] = {
                            'id': court_id,
                            'full_name': full_name,
                            'short_name': court.get('short_name'),
                            'jurisdiction': court.get('jurisdiction'),
                            'citation_string': court.get('citation_string')
                        }
                        print(f"Found: {term}")
                        print(f"  ID: {court_id}")
                        print(f"  Full Name: {full_name}")
                        print(f"  Jurisdiction Type: {court.get('jurisdiction')}")
                        print(f"  Position: {court.get('position')}")
                        print()
            
            # Check if we have more pages
            if not data.get('next'):
                break
                
            page += 1
            if page > 50:  # Safety limit
                break
                
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            break
    
    print(f"\n=== Summary ===")
    print(f"Found {len(found_courts)} out of {len(search_terms)} courts")
    
    # Show what we didn't find
    for term in search_terms:
        if term not in found_courts:
            print(f"NOT FOUND: {term}")
    
    # Let's also check what jurisdiction codes exist
    print("\n=== Checking jurisdiction codes in first 200 courts ===")
    jurisdictions = set()
    
    try:
        response = session.get(f"{BASE_URL}courts/", params={'page_size': 200})
        response.raise_for_status()
        data = response.json()
        
        for court in data.get('results', []):
            jurisdictions.add(court.get('jurisdiction', 'None'))
        
        print(f"Unique jurisdiction codes found: {sorted(jurisdictions)}")
        
        # Show some examples of each jurisdiction type
        for jur in sorted(jurisdictions):
            if jur:
                print(f"\nExamples of jurisdiction '{jur}':")
                count = 0
                for court in data.get('results', []):
                    if court.get('jurisdiction') == jur and count < 3:
                        print(f"  - {court.get('id')}: {court.get('full_name')}")
                        count += 1
        
    except:
        pass

if __name__ == "__main__":
    find_district_courts()