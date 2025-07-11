#!/usr/bin/env python3
"""
Working CourtListener API Verification Script
Tests connectivity and retrieves sample data
"""

import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

# Confirmed court IDs
TARGET_COURTS = {
    'ded': 'District of Delaware',
    'txed': 'Eastern District of Texas',
    'cand': 'Northern District of California',
    'cafc': 'Court of Appeals for the Federal Circuit',
    'cacd': 'Central District of California',
    'nysd': 'Southern District of New York'
}

class CourtListenerAPI:
    """Simple CourtListener API client"""
    
    def __init__(self, api_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
    
    def get_recent_dockets(self, court_id: str, days_back: int = 30):
        """Get recent dockets from a court"""
        # Use a date range that will have results
        date_to = datetime.now().date()
        date_from = date_to - timedelta(days=days_back)
        
        params = {
            'court': court_id,
            'date_filed__gte': date_from.isoformat(),
            'date_filed__lte': date_to.isoformat(),
            'order_by': '-date_filed',
            'page_size': 10
        }
        
        response = self.session.get(f"{BASE_URL}dockets/", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_patent_cases(self, court_id: str):
        """Get patent cases from a court"""
        # Nature of suit codes for patent cases
        params = {
            'court': court_id,
            'nature_of_suit': '830',  # Patent
            'order_by': '-date_filed',
            'page_size': 10
        }
        
        response = self.session.get(f"{BASE_URL}dockets/", params=params)
        response.raise_for_status()
        return response.json()
    
    def get_recent_opinions(self, court_id: str, days_back: int = 30):
        """Get recent opinions from a court"""
        date_from = (datetime.now() - timedelta(days=days_back)).isoformat()
        
        params = {
            'cluster__docket__court': court_id,
            'date_created__gte': date_from,
            'order_by': '-date_created',
            'page_size': 5
        }
        
        response = self.session.get(f"{BASE_URL}opinions/", params=params)
        response.raise_for_status()
        return response.json()

def main():
    """Run verification tests"""
    if not API_TOKEN:
        print("Error: COURTLISTENER_API_TOKEN not set")
        return
    
    api = CourtListenerAPI(API_TOKEN)
    
    print("=" * 70)
    print("CourtListener API Verification")
    print("=" * 70)
    
    # Test District of Delaware
    court_id = 'ded'
    court_name = TARGET_COURTS[court_id]
    
    print(f"\nTesting: {court_name} ({court_id})")
    print("-" * 50)
    
    try:
        # Get recent dockets
        print("\n1. Recent Dockets:")
        dockets_data = api.get_recent_dockets(court_id, days_back=7)
        dockets = dockets_data.get('results', [])
        print(f"   Found {dockets_data.get('count', 0)} total dockets")
        
        if dockets:
            docket = dockets[0]
            print(f"\n   Sample Docket:")
            print(f"   - Case: {docket.get('case_name', 'N/A')}")
            print(f"   - Number: {docket.get('docket_number', 'N/A')}")
            print(f"   - Filed: {docket.get('date_filed', 'N/A')}")
            print(f"   - Nature of Suit: {docket.get('nature_of_suit', 'N/A')}")
            print(f"   - ID: {docket.get('id')}")
        
        # Get patent cases
        print("\n2. Patent Cases:")
        patent_data = api.get_patent_cases(court_id)
        patents = patent_data.get('results', [])
        print(f"   Found {patent_data.get('count', 0)} total patent cases")
        
        if patents:
            patent = patents[0]
            print(f"\n   Sample Patent Case:")
            print(f"   - Case: {patent.get('case_name', 'N/A')}")
            print(f"   - Number: {patent.get('docket_number', 'N/A')}")
            print(f"   - Filed: {patent.get('date_filed', 'N/A')}")
        
        # Get recent opinions
        print("\n3. Recent Opinions:")
        opinions_data = api.get_recent_opinions(court_id, days_back=90)
        opinions = opinions_data.get('results', [])
        print(f"   Found {opinions_data.get('count', 0)} total opinions")
        
        if opinions:
            opinion = opinions[0]
            print(f"\n   Sample Opinion:")
            print(f"   - ID: {opinion.get('id')}")
            print(f"   - Type: {opinion.get('type')}")
            print(f"   - Date Created: {opinion.get('date_created')}")
            has_text = bool(opinion.get('plain_text') or opinion.get('html'))
            print(f"   - Has Text: {'Yes' if has_text else 'No'}")
        
        print("\n✓ All tests passed! API is working correctly.")
        
        # Show summary for all courts
        print("\n" + "=" * 70)
        print("Court Summary")
        print("=" * 70)
        
        for cid, cname in TARGET_COURTS.items():
            try:
                dockets = api.get_recent_dockets(cid, days_back=30)
                count = dockets.get('count', 0)
                print(f"{cid:6} | {cname:40} | {count:,} dockets")
            except:
                print(f"{cid:6} | {cname:40} | Error")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Response: {e.response.text}")

if __name__ == "__main__":
    main()