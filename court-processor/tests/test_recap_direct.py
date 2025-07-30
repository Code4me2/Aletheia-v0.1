#!/usr/bin/env python3
"""
Test RECAP Fetch API using direct curl-like approach
Following the exact documentation format
"""

import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Get credentials
cl_token = os.getenv('COURTLISTENER_API_KEY') or os.getenv('COURTLISTENER_API_TOKEN')
pacer_username = os.getenv('PACER_USERNAME')
pacer_password = os.getenv('PACER_PASSWORD')

print("Testing RECAP Fetch API with documentation format...")
print(f"CourtListener Token: ...{cl_token[-4:]}")
print(f"PACER Username: {pacer_username}")
print(f"PACER Password: {'*' * (len(pacer_password) - 4)}{pacer_password[-4:]}")

# Test 1: Exact format from documentation
print("\n" + "="*60)
print("TEST 1: Using requests library with form data")
print("="*60)

url = "https://www.courtlistener.com/api/rest/v4/recap-fetch/"
headers = {
    'Authorization': f'Token {cl_token}'
}

# Use a very simple test case
data = {
    'request_type': '1',  # Try as string like in docs
    'docket_number': '1:21-cv-00038',
    'court': 'txed',
    'pacer_username': pacer_username,
    'pacer_password': pacer_password,
    'show_parties_and_counsel': 'true'  # String instead of boolean
}

try:
    response = requests.post(url, data=data, headers=headers)
    print(f"Response Status: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✓ Success! Request ID: {result.get('id')}")
    else:
        print(f"\n✗ Failed with status {response.status_code}")
        
except Exception as e:
    print(f"Error: {e}")

# Test 2: Try with minimal data
print("\n" + "="*60)
print("TEST 2: Minimal request")
print("="*60)

minimal_data = {
    'request_type': '1',
    'docket': '123456',  # Try with docket ID instead
    'pacer_username': pacer_username,
    'pacer_password': pacer_password
}

try:
    response = requests.post(url, data=minimal_data, headers=headers)
    print(f"Response Status: {response.status_code}")
    print(f"Response Body: {response.text[:200]}...")
    
except Exception as e:
    print(f"Error: {e}")

# Test 3: Check if it's a credential encoding issue
print("\n" + "="*60)
print("TEST 3: Credential debugging")
print("="*60)

# Check for special characters
print(f"Username has special chars: {any(c in pacer_username for c in '@#$%^&*()+={}[]|\\:;<>?,/')}")
print(f"Password has special chars: {any(c in pacer_password for c in '@#$%^&*()+={}[]|\\:;<>?,/')}")

# Try URL encoding
from urllib.parse import quote
encoded_user = quote(pacer_username, safe='')
encoded_pass = quote(pacer_password, safe='')

if encoded_user != pacer_username or encoded_pass != pacer_password:
    print("\nTrying with URL-encoded credentials...")
    
    data_encoded = {
        'request_type': '1',
        'docket_number': '1:21-cv-00038',
        'court': 'txed',
        'pacer_username': encoded_user,
        'pacer_password': encoded_pass,
        'show_parties_and_counsel': 'true'
    }
    
    try:
        response = requests.post(url, data=data_encoded, headers=headers)
        print(f"Response Status: {response.status_code}")
        print(f"Response Body: {response.text[:200]}...")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("No special encoding needed for credentials")

print("\n" + "="*60)
print("DEBUGGING COMPLETE")
print("="*60)