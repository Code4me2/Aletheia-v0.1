#!/usr/bin/env python3
"""
Test CourtListener API V4
"""
import requests
from datetime import date, timedelta

API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL_V4 = 'https://www.courtlistener.com/api/rest/v4'

headers = {'Authorization': f'Token {API_TOKEN}'}

print("Testing CourtListener API V4")
print("=" * 70)

# Test V4 endpoints
endpoints = [
    '/dockets/',
    '/opinions/',
    '/courts/',
    '/people/',
    '/search/'
]

working_endpoints = []

for endpoint in endpoints:
    print(f"\n🔍 Testing {endpoint}...")
    try:
        params = {'page_size': 2}
        if endpoint == '/search/':
            params['q'] = 'patent'
            params['type'] = 'd'  # dockets
            
        response = requests.get(
            f'{BASE_URL_V4}{endpoint}',
            headers=headers,
            params=params
        )
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                print(f"   ✅ SUCCESS! Total available: {data.get('count', 'unknown')}")
                working_endpoints.append(endpoint)
                
                # Show first result
                if data['results']:
                    first = data['results'][0]
                    if endpoint == '/dockets/':
                        print(f"   Sample: {first.get('case_name', 'Unknown')}")
                        print(f"   Fields available: {list(first.keys())}")
                    elif endpoint == '/opinions/':
                        print(f"   Type: {first.get('type')} | Court: {first.get('court')}")
        else:
            print(f"   ❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")

# Test search capabilities on V4
if working_endpoints:
    print("\n" + "=" * 70)
    print("TESTING V4 SEARCH CAPABILITIES")
    print("=" * 70)
    
    search_tests = [
        {
            'name': 'Search by case name',
            'endpoint': '/dockets/',
            'params': {
                'case_name__icontains': 'Apple',
                'page_size': 5
            }
        },
        {
            'name': 'Search by court',
            'endpoint': '/dockets/', 
            'params': {
                'court': 'txed',
                'date_filed__gte': '2025-01-01',
                'page_size': 5
            }
        },
        {
            'name': 'Search by judge',
            'endpoint': '/dockets/',
            'params': {
                'assigned_to__icontains': 'Albright',
                'page_size': 5
            }
        },
        {
            'name': 'Patent cases by nature of suit',
            'endpoint': '/dockets/',
            'params': {
                'nature_of_suit': '830',
                'page_size': 5
            }
        },
        {
            'name': 'Full text search',
            'endpoint': '/search/',
            'params': {
                'q': 'patent infringement',
                'type': 'd',
                'court': 'txed',
                'page_size': 5
            }
        }
    ]
    
    for test in search_tests:
        print(f"\n🔍 {test['name']}")
        print(f"   Endpoint: {test['endpoint']}")
        print(f"   Params: {test['params']}")
        
        response = requests.get(
            f"{BASE_URL_V4}{test['endpoint']}",
            headers=headers,
            params=test['params']
        )
        
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', []))
            total = data.get('count', 0)
            
            print(f"   ✅ SUCCESS! Found {count} results (total: {total})")
            
            if count > 0:
                first = data['results'][0]
                if 'case_name' in first:
                    print(f"   First result: {first['case_name'][:80]}...")
                    if 'nature_of_suit' in first:
                        print(f"   Nature of suit: {first['nature_of_suit']}")
        else:
            print(f"   ❌ Failed: {response.status_code}")
            if response.status_code == 400:
                print(f"   Error: {response.json()}")

# Test bulk retrieval
print("\n" + "=" * 70)
print("MAXIMUM DATA RETRIEVAL CAPABILITIES")
print("=" * 70)

params = {
    'page_size': 100,
    'ordering': '-date_filed'
}

response = requests.get(f'{BASE_URL_V4}/dockets/', headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Can retrieve up to {len(data['results'])} items per page")
    print(f"✅ Total dockets available: {data.get('count', 'unknown')}")
    
    # Check pagination
    if data.get('next'):
        print("✅ Pagination available - can retrieve ALL data")
        print(f"   Next page URL: {data['next']}")
    
    # Check what fields are available
    if data['results']:
        print("\n📋 Available fields in docket data:")
        for field, value in data['results'][0].items():
            print(f"   - {field}: {type(value).__name__}")

print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)
print("""
With API V4, you can:
1. Search by case name patterns
2. Filter by court
3. Search by judge name
4. Filter by date ranges
5. Retrieve up to 100 items per page
6. Use pagination to get ALL available data
7. Access full docket metadata

The most expansive method is to:
- Use minimal filters (just ordering)
- Set page_size to 100
- Iterate through all pages
- This gives you access to ALL public dockets
""")