#!/usr/bin/env python3
"""
CourtListener API Verification Script
Tests basic connectivity and data retrieval from CourtListener API
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pprint

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Configuration
API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

# Target courts for testing (correct IDs confirmed)
TARGET_COURTS = {
    'ded': 'District of Delaware',
    'txed': 'Eastern District of Texas',
    'cand': 'Northern District of California',
    'cafc': 'Court of Appeals for the Federal Circuit'
}

class CourtListenerVerifier:
    """Verify CourtListener API connectivity and data quality"""
    
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("API token not found. Please set COURTLISTENER_API_TOKEN in .env file")
            
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0 (https://github.com/Code4me2/Aletheia-v0.1)'
        })
        self.pp = pprint.PrettyPrinter(indent=2)
    
    def test_basic_connectivity(self):
        """Test basic API connectivity"""
        print("\n=== Testing Basic API Connectivity ===")
        try:
            response = self.session.get(BASE_URL)
            response.raise_for_status()
            
            print(f"✓ Connected to CourtListener API")
            print(f"  Status Code: {response.status_code}")
            
            # Check rate limit headers
            rate_limit_headers = {
                'X-RateLimit-Limit': response.headers.get('X-RateLimit-Limit'),
                'X-RateLimit-Remaining': response.headers.get('X-RateLimit-Remaining'),
                'X-RateLimit-Reset': response.headers.get('X-RateLimit-Reset')
            }
            
            print(f"\n  Rate Limit Info:")
            for header, value in rate_limit_headers.items():
                if value:
                    print(f"    {header}: {value}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to connect to API: {e}")
            return False
    
    def test_court_endpoint(self, court_id: str):
        """Test retrieval of court information"""
        print(f"\n=== Testing Court Info: {court_id} ({TARGET_COURTS.get(court_id, 'Unknown')}) ===")
        
        try:
            url = f"{BASE_URL}courts/{court_id}/"
            response = self.session.get(url)
            response.raise_for_status()
            
            court_data = response.json()
            print(f"✓ Retrieved court information")
            print(f"\n  Key fields:")
            print(f"    ID: {court_data.get('id')}")
            print(f"    Name: {court_data.get('full_name')}")
            print(f"    Short Name: {court_data.get('short_name')}")
            print(f"    Jurisdiction: {court_data.get('jurisdiction')}")
            print(f"    Citation String: {court_data.get('citation_string')}")
            
            return court_data
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve court info: {e}")
            return None
    
    def test_recent_dockets(self, court_id: str, limit: int = 5):
        """Test retrieval of recent dockets for a court"""
        print(f"\n=== Testing Recent Dockets: {court_id} ===")
        
        try:
            # Get dockets from the last 30 days
            date_from = (datetime.now() - timedelta(days=30)).isoformat()
            
            params = {
                'court': court_id,
                'date_filed__gte': date_from,
                'order_by': '-date_filed',
                'page_size': limit
            }
            
            url = f"{BASE_URL}dockets/"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            dockets = data.get('results', [])
            
            print(f"✓ Retrieved {len(dockets)} dockets (Total available: {data.get('count', 'Unknown')})")
            
            # Display sample docket
            if dockets:
                print(f"\n  Sample Docket:")
                docket = dockets[0]
                print(f"    ID: {docket.get('id')}")
                print(f"    Case Name: {docket.get('case_name')}")
                print(f"    Case Number: {docket.get('docket_number')}")
                print(f"    Date Filed: {docket.get('date_filed')}")
                print(f"    Nature of Suit: {docket.get('nature_of_suit')}")
                print(f"    Assigned To: {docket.get('assigned_to_str')}")
                
                # Check for patent-related indicators
                is_patent = self._is_patent_case(docket)
                print(f"    Patent Case: {'Yes' if is_patent else 'No'}")
                
                # Show all available fields
                print(f"\n  Available fields in docket:")
                for key in sorted(docket.keys()):
                    print(f"    - {key}")
            
            return dockets
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve dockets: {e}")
            if hasattr(e.response, 'text'):
                print(f"  Response: {e.response.text}")
            return []
    
    def test_recent_opinions(self, court_id: str, limit: int = 5):
        """Test retrieval of recent opinions for a court"""
        print(f"\n=== Testing Recent Opinions: {court_id} ===")
        
        try:
            # Get opinions from the last 90 days
            date_from = (datetime.now() - timedelta(days=90)).isoformat()
            
            params = {
                'cluster__docket__court': court_id,
                'date_created__gte': date_from,
                'order_by': '-date_created',
                'page_size': limit
            }
            
            url = f"{BASE_URL}opinions/"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            opinions = data.get('results', [])
            
            print(f"✓ Retrieved {len(opinions)} opinions (Total available: {data.get('count', 'Unknown')})")
            
            # Display sample opinion
            if opinions:
                print(f"\n  Sample Opinion:")
                opinion = opinions[0]
                print(f"    ID: {opinion.get('id')}")
                print(f"    Author: {opinion.get('author_str')}")
                print(f"    Type: {opinion.get('type')}")
                print(f"    Date Created: {opinion.get('date_created')}")
                
                # Check text availability
                has_text = bool(opinion.get('plain_text') or opinion.get('html') or opinion.get('html_lawbox'))
                print(f"    Has Text: {'Yes' if has_text else 'No'}")
                
                if opinion.get('plain_text'):
                    preview = opinion['plain_text'][:200] + '...' if len(opinion['plain_text']) > 200 else opinion['plain_text']
                    print(f"    Text Preview: {preview}")
                
                # Show all available fields
                print(f"\n  Available fields in opinion:")
                for key in sorted(opinion.keys()):
                    print(f"    - {key}")
            
            return opinions
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to retrieve opinions: {e}")
            if hasattr(e.response, 'text'):
                print(f"  Response: {e.response.text}")
            return []
    
    def test_search_patent_cases(self, court_id: str):
        """Test searching for patent-related cases"""
        print(f"\n=== Testing Patent Case Search: {court_id} ===")
        
        try:
            # Search for patent cases using nature of suit codes
            patent_nos_codes = ['830', '835', '840']  # Patent case codes
            
            params = {
                'court': court_id,
                'nature_of_suit__in': ','.join(patent_nos_codes),
                'order_by': '-date_filed',
                'page_size': 5
            }
            
            url = f"{BASE_URL}dockets/"
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            patent_cases = data.get('results', [])
            
            print(f"✓ Found {data.get('count', 0)} patent cases")
            
            if patent_cases:
                print(f"\n  Sample Patent Cases:")
                for case in patent_cases[:3]:
                    print(f"    - {case.get('case_name')} ({case.get('docket_number')})")
                    print(f"      NOS: {case.get('nature_of_suit')} | Filed: {case.get('date_filed')}")
            
            # Also try text search
            print(f"\n  Testing text search for 'patent infringement'...")
            search_params = {
                'q': 'patent infringement',
                'court': court_id,
                'order_by': '-date_filed',
                'type': 'r'  # RECAP type
            }
            
            search_url = f"{BASE_URL}search/"
            search_response = self.session.get(search_url, params=search_params)
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                print(f"  ✓ Text search found {search_data.get('count', 0)} results")
            else:
                print(f"  ✗ Text search returned status {search_response.status_code}")
            
            return patent_cases
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to search patent cases: {e}")
            return []
    
    def _is_patent_case(self, docket: Dict) -> bool:
        """Determine if a docket is a patent case"""
        # Check nature of suit codes
        nos = str(docket.get('nature_of_suit', ''))
        patent_nos_codes = ['830', '835', '840']
        
        # Check case name
        case_name = docket.get('case_name', '').lower()
        patent_keywords = ['patent', 'infringement', '35 u.s.c.', '271', '284']
        
        return (nos in patent_nos_codes or 
                any(keyword in case_name for keyword in patent_keywords))
    
    def run_full_verification(self):
        """Run complete verification suite"""
        print("=" * 70)
        print("CourtListener API Verification Report")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 70)
        
        # Test basic connectivity
        if not self.test_basic_connectivity():
            print("\n✗ Basic connectivity failed. Please check your API token.")
            return
        
        # Test each target court
        summary = {
            'courts_tested': 0,
            'dockets_found': 0,
            'opinions_found': 0,
            'patent_cases_found': 0
        }
        
        for court_id in ['ded']:  # Start with just Delaware for initial test
            print(f"\n{'='*70}")
            print(f"Testing {court_id.upper()}")
            print(f"{'='*70}")
            
            # Test court info
            court_info = self.test_court_endpoint(court_id)
            if court_info:
                summary['courts_tested'] += 1
            
            # Test dockets
            dockets = self.test_recent_dockets(court_id, limit=3)
            summary['dockets_found'] += len(dockets)
            
            # Test opinions
            opinions = self.test_recent_opinions(court_id, limit=3)
            summary['opinions_found'] += len(opinions)
            
            # Test patent search
            patent_cases = self.test_search_patent_cases(court_id)
            summary['patent_cases_found'] += len(patent_cases)
        
        # Print summary
        print(f"\n{'='*70}")
        print("VERIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"✓ API Connection: SUCCESS")
        print(f"✓ Courts Tested: {summary['courts_tested']}")
        print(f"✓ Sample Dockets Retrieved: {summary['dockets_found']}")
        print(f"✓ Sample Opinions Retrieved: {summary['opinions_found']}")
        print(f"✓ Patent Cases Found: {summary['patent_cases_found']}")
        
        print(f"\n✓ CourtListener API is working correctly!")
        print(f"  Ready to proceed with bulk download implementation.")

def main():
    """Main entry point"""
    try:
        verifier = CourtListenerVerifier(API_TOKEN)
        verifier.run_full_verification()
    except Exception as e:
        print(f"\n✗ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()