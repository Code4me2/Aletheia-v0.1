#!/usr/bin/env python3
"""
Test RECAP API directly with raw credentials (bypassing PACER auth)
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_recap_direct():
    """Test RECAP API with raw credentials"""
    
    username = os.environ.get('PACER_USERNAME')
    password = os.environ.get('PACER_PASSWORD')
    cl_token = os.environ.get('COURTLISTENER_TOKEN')
    
    print("Testing RECAP API with raw credentials...")
    print(f"Username: {username}")
    print(f"CourtListener token: {cl_token[:8]}...")
    
    # Test case
    docket_number = '1:20-cv-12345'
    court = 'txed'
    
    # RECAP API endpoint
    recap_url = 'https://www.courtlistener.com/api/rest/v4/recap-fetch/'
    
    # Request data
    data = {
        'request_type': 1,  # Docket
        'docket_number': docket_number,
        'court': court,
        'pacer_username': username,
        'pacer_password': password,
    }
    
    headers = {
        'Authorization': f'Token {cl_token}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    print(f"\nTesting RECAP fetch for {docket_number} in {court}...")
    
    try:
        response = requests.post(recap_url, data=data, headers=headers)
        
        print(f"\nResponse Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ RECAP request created!")
            print(f"Request ID: {result.get('id')}")
            print(f"Status: {result.get('status')}")
            print(f"Court: {result.get('court')}")
            print(f"PACER Case ID: {result.get('pacer_case_id')}")
            
            # Monitor the request
            if result.get('id'):
                import time
                request_id = result['id']
                status_url = f"{recap_url}{request_id}/"
                
                print(f"\nMonitoring request {request_id}...")
                for i in range(12):  # Check for 1 minute
                    time.sleep(5)
                    status_response = requests.get(status_url, headers={'Authorization': f'Token {cl_token}'})
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        status = status_data.get('status')
                        print(f"Status check {i+1}: {status}")
                        
                        if status in [2, 5]:  # Success
                            print("✅ Request completed successfully!")
                            break
                        elif status in [3, 6]:  # Failed
                            print(f"❌ Request failed: {status_data.get('error_message')}")
                            break
                    else:
                        print(f"Status check failed: {status_response.status_code}")
                        
        else:
            print(f"❌ RECAP request failed")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"\n💥 Exception: {type(e).__name__}: {e}")


if __name__ == "__main__":
    test_recap_direct()