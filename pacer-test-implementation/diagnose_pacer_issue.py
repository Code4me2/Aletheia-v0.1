#!/usr/bin/env python3
"""
Comprehensive PACER diagnostic to identify the exact issue
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

def diagnose_pacer():
    """Run comprehensive diagnostics on PACER authentication"""
    
    print("🔍 PACER AUTHENTICATION DIAGNOSTICS")
    print("=" * 50)
    
    # 1. Check environment
    username = os.environ.get('PACER_USERNAME')
    password = os.environ.get('PACER_PASSWORD')
    
    print("\n1️⃣ ENVIRONMENT CHECK")
    print(f"Username: {username}")
    print(f"Password length: {len(password) if password else 0} chars")
    print(f"Password (masked): {'*' * 10}{password[-4:] if password and len(password) > 4 else ''}")
    
    # Check for special characters that might need escaping
    if password:
        special_chars = sum(1 for c in password if not c.isalnum())
        print(f"Special characters in password: {special_chars}")
    
    # 2. Test different endpoints
    print("\n2️⃣ ENDPOINT TESTS")
    
    endpoints = {
        'Production': 'https://pacer.login.uscourts.gov/services/cso-auth',
        'QA': 'https://qa-login.uscourts.gov/services/cso-auth',
        'Production (Alt)': 'https://pacer.uscourts.gov/services/cso-auth',
    }
    
    for name, url in endpoints.items():
        print(f"\nTesting {name}: {url}")
        
        auth_data = {
            'loginId': username,
            'password': password,
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (compatible; PACER-API-Test/1.0)'
        }
        
        try:
            response = requests.post(url, json=auth_data, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"  Login Result: {result.get('loginResult')}")
                    print(f"  Error: {result.get('errorDescription', 'None')}")
                    
                    if result.get('loginResult') == '0':
                        print(f"  ✅ SUCCESS! Token: {result.get('nextGenCSO', '')[:20]}...")
                except:
                    print(f"  Response: {response.text[:100]}")
            else:
                print(f"  Failed: {response.text[:100]}")
                
        except requests.exceptions.Timeout:
            print("  ⏱️  Timeout")
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ Connection error: {str(e)[:50]}")
        except Exception as e:
            print(f"  💥 Error: {type(e).__name__}: {str(e)[:50]}")
    
    # 3. Test RECAP integration
    print("\n3️⃣ RECAP API TEST")
    
    cl_token = os.environ.get('COURTLISTENER_TOKEN')
    if cl_token:
        recap_data = {
            'request_type': 1,
            'docket_number': '1:20-cv-12345',
            'court': 'txed',
            'pacer_username': username,
            'pacer_password': password,
        }
        
        recap_headers = {
            'Authorization': f'Token {cl_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        try:
            response = requests.post(
                'https://www.courtlistener.com/api/rest/v4/recap-fetch/',
                data=recap_data,
                headers=recap_headers
            )
            print(f"RECAP Status: {response.status_code}")
            if response.status_code != 200:
                print(f"RECAP Error: {response.text[:200]}")
            else:
                print("✅ RECAP accepted the request")
        except Exception as e:
            print(f"RECAP Error: {e}")
    
    # 4. Recommendations
    print("\n4️⃣ ANALYSIS & RECOMMENDATIONS")
    print("-" * 40)
    
    print("""
Based on the tests above:

1. If ALL endpoints fail with 'Login Failed':
   - The credentials are incorrect OR
   - The account doesn't have API access enabled
   
2. If production works but QA fails:
   - This is expected (QA needs separate account)
   
3. If PACER auth fails but RECAP works:
   - RECAP might have cached credentials
   
4. Next steps:
   - Verify login at https://pacer.uscourts.gov
   - If web login works, contact PACER support about API access
   - Use RECAP's free archive in the meantime
""")


if __name__ == "__main__":
    diagnose_pacer()