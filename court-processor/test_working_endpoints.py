#!/usr/bin/env python3
"""
Test what ACTUALLY works with our API token
"""
import requests
from datetime import date, timedelta

API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

headers = {'Authorization': f'Token {API_TOKEN}'}

print("Testing CourtListener API Access")
print("=" * 50)

# Test basic endpoints
endpoints = [
    '/dockets/',
    '/opinions/', 
    '/courts/',
    '/people/',
    '/search/'
]

working_endpoints = []

for endpoint in endpoints:
    print(f"\nTesting {endpoint}...")
    try:
        # Try with minimal params
        params = {'page_size': 1}
        if endpoint == '/search/':
            params['q'] = 'test'
            
        response = requests.get(
            f'{BASE_URL}{endpoint}',
            headers=headers,
            params=params
        )
        
        print(f"  Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if 'results' in data:
                print(f"  ✅ Working! Found {data.get('count', 'unknown')} total items")
                working_endpoints.append(endpoint)
                
                # Show available fields from first result
                if data['results']:
                    print("  Available fields:", list(data['results'][0].keys())[:10])
        else:
            print(f"  ❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"  ❌ Exception: {e}")

# Now test what filters work on dockets
if '/dockets/' in working_endpoints:
    print("\n" + "=" * 50)
    print("Testing Docket Filters")
    print("=" * 50)
    
    filters = [
        {'court': 'txed'},
        {'date_filed__gte': '2025-01-01'},
        {'case_name__icontains': 'Apple'},
        {'assigned_to__icontains': 'Albright'},
        {'court': 'txed', 'date_filed__gte': '2025-01-01'},
    ]
    
    for f in filters:
        print(f"\nTesting filter: {f}")
        params = {'page_size': 2}
        params.update(f)
        
        response = requests.get(
            f'{BASE_URL}/dockets/',
            headers=headers,
            params=params
        )
        
        if response.status_code == 200:
            data = response.json()
            count = len(data.get('results', []))
            print(f"  ✅ Works! Found {count} results")
            
            if count > 0:
                first = data['results'][0]
                print(f"  Sample: {first.get('case_name', 'Unknown')}")
                print(f"  Court: {first.get('court')} | Filed: {first.get('date_filed')}")
        else:
            print(f"  ❌ Failed with status {response.status_code}")

# Test pagination
print("\n" + "=" * 50)
print("Testing Maximum Data Retrieval")
print("=" * 50)

params = {
    'page_size': 100,  # Max per page
    'ordering': '-date_filed'
}

response = requests.get(f'{BASE_URL}/dockets/', headers=headers, params=params)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Can retrieve {len(data['results'])} items per page")
    print(f"✅ Total available: {data.get('count', 'unknown')}")
    
    if data.get('next'):
        print("✅ Pagination is available for bulk retrieval")
else:
    print(f"❌ Failed: {response.status_code}")