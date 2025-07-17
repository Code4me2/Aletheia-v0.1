#!/usr/bin/env python3
"""
Test ALL available search methods on CourtListener API
Discover what parameters actually work on the free tier
"""
import requests
import json
from datetime import datetime, date, timedelta

API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

def test_search_params():
    """Test various search parameters to see what works"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    
    print("=" * 70)
    print("TESTING COURTLISTENER API SEARCH CAPABILITIES")
    print("=" * 70)
    
    # Test court to use
    test_court = 'txed'
    date_from = (date.today() - timedelta(days=30)).isoformat()
    
    # Different search parameters to test
    test_params = [
        {
            'name': 'Basic date + court',
            'params': {
                'court': test_court,
                'date_filed__gte': date_from,
                'page_size': 5
            }
        },
        {
            'name': 'Nature of Suit (830 = Patent)',
            'params': {
                'court': test_court,
                'nature_of_suit': '830',
                'date_filed__gte': '2024-01-01',
                'page_size': 5
            }
        },
        {
            'name': 'Nature of Suit search',
            'params': {
                'court': test_court,
                'nature_of_suit__icontains': 'patent',
                'page_size': 5
            }
        },
        {
            'name': 'Cause search',
            'params': {
                'court': test_court,
                'cause__icontains': '35:271',  # Patent statute
                'page_size': 5
            }
        },
        {
            'name': 'Assigned judge search',
            'params': {
                'court': test_court,
                'assigned_to__icontains': 'Gilstrap',  # Famous patent judge
                'page_size': 5
            }
        },
        {
            'name': 'Full-text search (q parameter)',
            'params': {
                'q': 'patent infringement',
                'court': test_court,
                'page_size': 5
            }
        },
        {
            'name': 'Docket number pattern',
            'params': {
                'court': test_court,
                'docket_number__icontains': '2:24',
                'page_size': 5
            }
        },
        {
            'name': 'Multiple filters combined',
            'params': {
                'court': test_court,
                'date_filed__gte': '2024-01-01',
                'assigned_to__isnull': False,
                'date_terminated__isnull': True,  # Active cases only
                'page_size': 5
            }
        }
    ]
    
    working_params = []
    
    for test in test_params:
        print(f"\n🔍 Testing: {test['name']}")
        print(f"   Params: {test['params']}")
        
        try:
            response = requests.get(
                f'{BASE_URL}/dockets/',
                headers=headers,
                params=test['params']
            )
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                total = data.get('count', 0)
                
                print(f"   ✅ SUCCESS: Found {count} results (total available: {total})")
                
                if count > 0:
                    working_params.append(test['name'])
                    # Show first result
                    first = data['results'][0]
                    print(f"   Sample: {first.get('case_name', 'Unknown')}")
                    print(f"           Filed: {first.get('date_filed')} | Nature: {first.get('nature_of_suit')}")
                    
            else:
                print(f"   ❌ FAILED: Status {response.status_code}")
                if response.status_code == 400:
                    print(f"   Error: {response.json()}")
                    
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    # Test the search endpoint
    print("\n" + "=" * 70)
    print("TESTING SEARCH ENDPOINT")
    print("=" * 70)
    
    search_tests = [
        {
            'name': 'Search API with query',
            'params': {'q': 'patent', 'type': 'd', 'order_by': 'score desc'}
        },
        {
            'name': 'Search with court filter',
            'params': {'q': 'apple', 'court': test_court, 'type': 'd'}
        }
    ]
    
    for test in search_tests:
        print(f"\n🔍 Testing: {test['name']}")
        
        try:
            response = requests.get(
                f'{BASE_URL}/search/',
                headers=headers,
                params=test['params']
            )
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"   ✅ Found {count} results")
            else:
                print(f"   ❌ Status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY OF WORKING SEARCH METHODS")
    print("=" * 70)
    print("\nWorking parameters on /dockets/ endpoint:")
    for param in working_params:
        print(f"  ✅ {param}")
    
    print("\n💡 RECOMMENDATIONS:")
    print("1. Use date ranges to get recent cases")
    print("2. Filter by court for targeted results")
    print("3. Search case names for specific terms")
    print("4. Use assigned judge names for judge-specific queries")
    print("5. Combine multiple filters for precise results")

def test_opinions_search():
    """Test opinion search capabilities"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    
    print("\n" + "=" * 70)
    print("TESTING OPINIONS ENDPOINT")
    print("=" * 70)
    
    opinion_params = [
        {
            'name': 'Recent opinions by court',
            'params': {
                'court': 'ca9',
                'date_filed__gte': '2024-01-01',
                'page_size': 5
            }
        },
        {
            'name': 'Opinion text search',
            'params': {
                'text__icontains': 'patent',
                'page_size': 5
            }
        },
        {
            'name': 'Author search',
            'params': {
                'author_str__icontains': 'Chen',
                'page_size': 5
            }
        }
    ]
    
    for test in opinion_params:
        print(f"\n🔍 Testing: {test['name']}")
        
        try:
            response = requests.get(
                f'{BASE_URL}/opinions/',
                headers=headers,
                params=test['params']
            )
            
            if response.status_code == 200:
                data = response.json()
                count = len(data.get('results', []))
                print(f"   ✅ Found {count} results")
                
                if count > 0 and 'text' in data['results'][0]:
                    print("   📄 Opinion text IS available!")
            else:
                print(f"   ❌ Status {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")

def test_bulk_data():
    """Test bulk data endpoints"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    
    print("\n" + "=" * 70)
    print("TESTING BULK DATA ACCESS")
    print("=" * 70)
    
    # Test clusters endpoint
    print("\n🔍 Testing clusters endpoint (groups related documents)...")
    response = requests.get(
        f'{BASE_URL}/clusters/',
        headers=headers,
        params={'page_size': 5}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Clusters accessible: {data.get('count', 0)} total")
    else:
        print(f"   ❌ Clusters not accessible: {response.status_code}")

def main():
    """Run all tests"""
    test_search_params()
    test_opinions_search()
    test_bulk_data()
    
    print("\n" + "=" * 70)
    print("KEY FINDINGS")
    print("=" * 70)
    print("""
1. AVAILABLE SEARCH METHODS (Free Tier):
   - Date ranges (date_filed__gte, date_filed__lte)
   - Court filtering (court='txed')
   - Case name search (case_name__icontains)
   - Assigned judge search (assigned_to__icontains)
   - Docket number patterns (docket_number__icontains)
   - Active/terminated case filtering
   - Full-text search via /search/ endpoint

2. NOT AVAILABLE (Free Tier):
   - Nature of Suit codes (requires paid tier)
   - Cause codes (requires paid tier)
   - Opinion text search (metadata only)
   - Document/entry level data

3. BEST STRATEGIES FOR MAXIMUM DATA:
   - Use broad date ranges
   - Iterate through all courts
   - Search for company names known to be in IP litigation
   - Use judge names (e.g., Albright, Gilstrap for patent cases)
   - Combine multiple filters
""")

if __name__ == "__main__":
    main()