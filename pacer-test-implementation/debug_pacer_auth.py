#!/usr/bin/env python3
"""
Debug PACER authentication to see detailed error information
"""

import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

def test_pacer_auth_detailed():
    """Test PACER authentication with detailed debugging"""
    
    username = os.environ.get('PACER_USERNAME')
    password = os.environ.get('PACER_PASSWORD')
    environment = os.environ.get('PACER_ENVIRONMENT', 'QA')
    
    print(f"Testing PACER authentication...")
    print(f"Username: {username}")
    print(f"Password: {'*' * len(password) if password else 'NOT SET'}")
    print(f"Environment: {environment}")
    
    # Get URL
    if environment.upper() == 'QA':
        base_url = 'https://qa-login.uscourts.gov'
    else:
        base_url = 'https://pacer.login.uscourts.gov'
    
    auth_url = f"{base_url}/services/cso-auth"
    print(f"Auth URL: {auth_url}")
    
    # Prepare request
    auth_data = {
        'loginId': username,
        'password': password,
    }
    
    print(f"\nRequest data: {json.dumps({k: v if k != 'password' else '***' for k, v in auth_data.items()}, indent=2)}")
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    print(f"\nMaking authentication request...")
    
    try:
        response = requests.post(auth_url, json=auth_data, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        try:
            response_json = response.json()
            print(f"\nResponse JSON:")
            print(json.dumps(response_json, indent=2))
        except:
            print(f"\nResponse Text: {response.text}")
        
        # Check if we need special handling
        if response.status_code == 200:
            result = response.json()
            if result.get('loginResult') == '0':
                print("\n✅ Authentication successful!")
                print(f"Token length: {len(result.get('nextGenCSO', ''))}")
            else:
                print(f"\n❌ Authentication failed with loginResult: {result.get('loginResult')}")
                print(f"Error: {result.get('errorDescription', 'Unknown')}")
    
    except Exception as e:
        print(f"\n💥 Exception occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_pacer_auth_detailed()