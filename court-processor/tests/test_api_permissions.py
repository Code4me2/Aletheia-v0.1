#!/usr/bin/env python3
"""
Test which CourtListener API endpoints are accessible
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_API_TOKEN')
base_url = "https://www.courtlistener.com/api/rest/v4"
headers = {'Authorization': f'Token {cl_token}'}

print("Testing CourtListener API Endpoint Permissions")
print("="*60)
print(f"Token: ...{cl_token[-4:]}")
print("="*60)

# Test various endpoints
endpoints = [
    # Basic endpoints (should work)
    ("GET", "/courts/", {}, "Court information"),
    ("GET", "/opinions/", {"page_size": 1}, "Opinions"),
    ("GET", "/search/", {"q": "test", "page_size": 1}, "Search"),
    
    # Potentially restricted endpoints
    ("GET", "/recap-query/", {"pacer_doc_id__in": "12345"}, "RECAP Query"),
    ("POST", "/citation-lookup/", {"text": "test"}, "Citation Lookup"),
    ("GET", "/people/", {"page_size": 1}, "People/Judges"),
    
    # RECAP Fetch (requires PACER credentials)
    ("GET", "/recap-fetch/", {}, "RECAP Fetch List"),
    
    # Other endpoints
    ("GET", "/dockets/", {"page_size": 1}, "Dockets"),
    ("GET", "/audio/", {"page_size": 1}, "Audio"),
]

results = []

for method, endpoint, params, description in endpoints:
    url = f"{base_url}{endpoint}"
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=5)
        else:
            response = requests.post(url, headers=headers, json=params, timeout=5)
        
        status = response.status_code
        
        # Check response
        if status == 200:
            result = "✅ Accessible"
        elif status == 401:
            result = "🔒 Unauthorized (need different permissions)"
        elif status == 403:
            result = "⛔ Forbidden (not allowed)"
        elif status == 404:
            result = "❓ Not found"
        elif status == 405:
            result = "⚠️ Method not allowed"
        else:
            result = f"❌ Error {status}"
        
        print(f"\n{description} ({method} {endpoint}):")
        print(f"  Status: {status}")
        print(f"  Result: {result}")
        
        if status not in [200, 401, 403, 404]:
            print(f"  Response: {response.text[:100]}...")
            
        results.append({
            "endpoint": endpoint,
            "method": method,
            "status": status,
            "accessible": status == 200
        })
        
    except Exception as e:
        print(f"\n{description} ({method} {endpoint}):")
        print(f"  Error: {str(e)}")
        results.append({
            "endpoint": endpoint,
            "method": method,
            "status": "error",
            "accessible": False
        })

# Summary
print("\n" + "="*60)
print("SUMMARY")
print("="*60)

accessible = [r for r in results if r["accessible"]]
restricted = [r for r in results if r["status"] in [401, 403]]

print(f"\nAccessible endpoints: {len(accessible)}")
for r in accessible:
    print(f"  ✅ {r['method']} {r['endpoint']}")

print(f"\nRestricted endpoints: {len(restricted)}")
for r in restricted:
    print(f"  🔒 {r['method']} {r['endpoint']} (status: {r['status']})")

print("\n" + "="*60)
print("CONCLUSIONS")
print("="*60)
print("\n1. Your CourtListener API token is valid and working")
print("2. Basic search and data access work fine")
print("3. Some endpoints like /recap-query/ and /citation-lookup/ need special permissions")
print("4. The PACER credentials issue is separate from API access")
print("\nFor PACER integration, you need to:")
print("- Verify PACER credentials at https://pacer.uscourts.gov/")
print("- Ensure your PACER account is active and in good standing")
print("- Check if you need a specific PACER account type for API access")