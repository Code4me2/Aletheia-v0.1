#!/usr/bin/env python3
"""
Test CourtListener API authentication and access
Based on troubleshooting guide feedback
"""
import requests
import json
from datetime import datetime

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com'

def test_basic_auth():
    """Test basic authentication with correct header format"""
    print("=== Testing Basic Authentication ===")
    
    # Test the CORRECT format: "Authorization: Token YOUR_TOKEN"
    headers = {
        'Authorization': f'Token {API_TOKEN}'  # Note the space after "Token"
    }
    
    # Try the most basic endpoint - courts list
    print("\n1. Testing /api/rest/v3/courts/ endpoint...")
    response = requests.get(
        f'{BASE_URL}/api/rest/v3/courts/',
        headers=headers
    )
    
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print("   ✓ Token is working correctly!")
        data = response.json()
        print(f"   ✓ Found {data.get('count', 0)} courts")
    elif response.status_code == 403:
        print("   ✗ Still getting 403 - check token spelling and format")
        print(f"   Response: {response.text[:200]}")
    else:
        print(f"   ? Unexpected status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
    
    return response.status_code == 200

def test_wrong_formats():
    """Test common wrong authorization formats to confirm they fail"""
    print("\n=== Testing Wrong Authorization Formats ===")
    
    wrong_formats = [
        ('No Token word', {'Authorization': API_TOKEN}),
        ('Bearer instead', {'Authorization': f'Bearer {API_TOKEN}'}),
        ('Bearer Token', {'Authorization': f'Bearer Token {API_TOKEN}'}),
        ('Token without space', {'Authorization': f'Token{API_TOKEN}'}),
    ]
    
    for desc, headers in wrong_formats:
        response = requests.get(
            f'{BASE_URL}/api/rest/v3/courts/',
            headers=headers
        )
        print(f"   {desc}: Status {response.status_code} {'✓ (correctly rejected)' if response.status_code != 200 else '✗ (should fail)'}")

def test_multiple_endpoints():
    """Test different endpoints to check access levels"""
    print("\n=== Testing Multiple Endpoints ===")
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    endpoints = [
        ('/api/rest/v3/courts/', 'Courts list (should work for everyone)'),
        ('/api/rest/v3/search/', 'Search endpoint (should work for everyone)'),
        ('/api/rest/v3/dockets/', 'Dockets list (should work for everyone)'),
        ('/api/rest/v3/docket-entries/', 'Docket entries (might need paid access)'),
        ('/api/rest/v3/recap-documents/', 'RECAP documents (might need paid access)'),
        ('/api/rest/v3/people/', 'People/Judges (should work)'),
        ('/api/rest/v3/opinions/', 'Opinions (should work)'),
    ]
    
    results = []
    for endpoint, description in endpoints:
        response = requests.get(
            f'{BASE_URL}{endpoint}',
            headers=headers,
            params={'page_size': 1}  # Just get one result to test
        )
        status = response.status_code
        results.append((endpoint, status))
        
        if status == 200:
            print(f"   ✓ {endpoint}: {status} - {description}")
        elif status == 403:
            print(f"   ✗ {endpoint}: {status} - {description}")
        else:
            print(f"   ? {endpoint}: {status} - {description}")
    
    return results

def test_rate_limits():
    """Check rate limit headers"""
    print("\n=== Checking Rate Limits ===")
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    response = requests.get(
        f'{BASE_URL}/api/rest/v3/courts/',
        headers=headers
    )
    
    # Check rate limit headers
    rate_headers = {
        'X-RateLimit-Limit': 'Total allowed requests',
        'X-RateLimit-Remaining': 'Requests remaining',
        'X-RateLimit-Reset': 'When limit resets',
    }
    
    for header, desc in rate_headers.items():
        value = response.headers.get(header)
        if value:
            print(f"   {header}: {value} ({desc})")

def test_document_access():
    """Test accessing documents with proper auth"""
    print("\n=== Testing Document Access ===")
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    # First, get a docket
    print("\n1. Fetching a recent docket...")
    docket_response = requests.get(
        f'{BASE_URL}/api/rest/v3/dockets/',
        headers=headers,
        params={
            'court': 'txed',
            'page_size': 1,
            'ordering': '-date_modified'
        }
    )
    
    if docket_response.status_code == 200:
        dockets = docket_response.json().get('results', [])
        if dockets:
            docket = dockets[0]
            docket_id = docket['id']
            print(f"   ✓ Found docket: {docket['case_name']} (ID: {docket_id})")
            
            # Try to get docket entries
            print("\n2. Attempting to fetch docket entries...")
            entries_response = requests.get(
                f'{BASE_URL}/api/rest/v3/docket-entries/',
                headers=headers,
                params={
                    'docket': docket_id,
                    'page_size': 5
                }
            )
            
            print(f"   Docket entries status: {entries_response.status_code}")
            if entries_response.status_code == 200:
                entries = entries_response.json().get('results', [])
                print(f"   ✓ Successfully retrieved {len(entries)} entries")
            elif entries_response.status_code == 403:
                print("   ✗ Access denied - this endpoint may require paid access")

def main():
    """Run all authentication tests"""
    print("=" * 60)
    print("CourtListener API Authentication Test")
    print(f"Testing with token: {API_TOKEN[:10]}...{API_TOKEN[-4:]}")
    print(f"Run time: {datetime.now()}")
    print("=" * 60)
    
    # Run tests
    if test_basic_auth():
        test_wrong_formats()
        endpoint_results = test_multiple_endpoints()
        test_rate_limits()
        test_document_access()
        
        # Summary
        print("\n" + "=" * 60)
        print("Summary:")
        working = sum(1 for _, status in endpoint_results if status == 200)
        forbidden = sum(1 for _, status in endpoint_results if status == 403)
        print(f"✓ Working endpoints: {working}")
        print(f"✗ Forbidden endpoints: {forbidden}")
        print("\nAuthentication is working correctly!")
        print("403 errors on document endpoints indicate tier restrictions, not auth issues.")
    else:
        print("\n" + "=" * 60)
        print("Authentication failed! Please check:")
        print("1. Token is correct and active")
        print("2. Using format: 'Authorization: Token YOUR_TOKEN'")
        print("3. Token has not been regenerated")

if __name__ == "__main__":
    main()