#!/usr/bin/env python3
"""
Simple verification of RECAP API functionality
"""
import json
import urllib.request
import urllib.parse

# API configuration
API_KEY = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def test_api_connection():
    """Test basic API connection"""
    print("=== Testing CourtListener API Connection ===\n")
    
    # Test 1: Fetch recent Supreme Court opinion
    print("1. Testing basic opinions endpoint...")
    url = f"{BASE_URL}/opinions/?court=scotus&page_size=1"
    
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Token {API_KEY}')
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        
        if 'results' in data and data['results']:
            opinion = data['results'][0]
            print("✓ API connection successful!")
            print(f"  Case: {opinion.get('case_name', 'Unknown')}")
            print(f"  Date: {opinion.get('date_filed')}")
        else:
            print("✗ No results returned")
    except Exception as e:
        print(f"✗ API Error: {e}")
    
    # Test 2: Check RECAP dockets endpoint
    print("\n2. Testing RECAP dockets endpoint...")
    params = {
        'court': 'txed',
        'nature_of_suit': '830',  # Patent
        'date_filed__gte': '2024-10-01',
        'page_size': '2'
    }
    
    query_string = urllib.parse.urlencode(params)
    url = f"{BASE_URL}/dockets/?{query_string}"
    
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Token {API_KEY}')
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        
        if 'results' in data:
            print(f"✓ RECAP endpoint working! Found {len(data['results'])} dockets")
            
            for i, docket in enumerate(data['results']):
                print(f"\n  Docket {i+1}:")
                print(f"    ID: {docket.get('id')}")
                print(f"    Case: {docket.get('case_name', 'Unknown')[:60]}...")
                print(f"    Court: {docket.get('court')}")
                print(f"    NOS: {docket.get('nature_of_suit')}")
                print(f"    Filed: {docket.get('date_filed')}")
                
                # If we have a docket ID, test document fetch
                if docket.get('id'):
                    print(f"\n3. Testing document fetch for docket {docket['id']}...")
                    doc_url = f"{BASE_URL}/recap-documents/?docket_entry__docket__id={docket['id']}&page_size=3"
                    
                    req = urllib.request.Request(doc_url)
                    req.add_header('Authorization', f'Token {API_KEY}')
                    
                    try:
                        doc_response = urllib.request.urlopen(req)
                        doc_data = json.loads(doc_response.read())
                        
                        if 'results' in doc_data:
                            print(f"  ✓ Found {len(doc_data['results'])} documents")
                            
                            for j, doc in enumerate(doc_data['results'][:2]):
                                print(f"    Doc {j+1}: {doc.get('description', 'No description')[:50]}...")
                                
                    except Exception as e:
                        print(f"  ✗ Document fetch error: {e}")
                    
                    break  # Only test first docket
    except Exception as e:
        print(f"✗ RECAP Error: {e}")
    
    # Test 3: Search functionality
    print("\n4. Testing RECAP search...")
    search_params = {
        'q': 'patent infringement',
        'type': 'r',  # RECAP
        'court': 'txed',
        'page_size': '2'
    }
    
    query_string = urllib.parse.urlencode(search_params)
    url = f"{BASE_URL}/search/?{query_string}"
    
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'Token {API_KEY}')
    
    try:
        response = urllib.request.urlopen(req)
        data = json.loads(response.read())
        
        if 'results' in data:
            print(f"✓ Search working! Found {len(data['results'])} results")
            
            for i, result in enumerate(data['results']):
                print(f"  Result {i+1}: {result.get('caseName', 'Unknown')[:50]}...")
    except Exception as e:
        print(f"✗ Search Error: {e}")
    
    print("\n=== API verification complete ===")
    print("✓ You can now revoke the API key")

if __name__ == "__main__":
    test_api_connection()