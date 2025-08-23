#!/usr/bin/env python3
"""
Test PACER with PRODUCTION endpoints (correct approach)
Based on pacer_corrections.md insights
"""

import os
import requests
import pyotp
from dotenv import load_dotenv

load_dotenv()

class CorrectedPACERTest:
    """Test PACER using production endpoints with regular credentials"""
    
    def __init__(self):
        # ALWAYS use production for regular PACER accounts
        self.auth_url = 'https://pacer.login.uscourts.gov/services/cso-auth'
        self.username = os.environ.get('PACER_USERNAME')
        self.password = os.environ.get('PACER_PASSWORD')
        
        print("🏭 Using PRODUCTION endpoints (correct for regular PACER accounts)")
        print(f"👤 Username: {self.username}")
    
    def test_authentication(self):
        """Test authentication with production endpoint"""
        print("\n🔐 Testing PACER authentication...")
        
        auth_data = {
            'loginId': self.username,
            'password': self.password,
        }
        
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            print(f"🌐 Calling: {self.auth_url}")
            response = requests.post(self.auth_url, json=auth_data, headers=headers)
            
            print(f"📡 HTTP Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                login_result = result.get('loginResult')
                
                if login_result == '0':
                    token = result.get('nextGenCSO')
                    print(f"✅ SUCCESS! Authentication worked!")
                    print(f"🎫 Token: {token[:20]}... ({len(token)} chars)")
                    return True
                else:
                    print(f"❌ Login failed: {result.get('errorDescription')}")
                    return False
            else:
                print(f"❌ HTTP error: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"💥 Error: {e}")
            return False


def main():
    print("🚀 CORRECTED PACER TEST")
    print("=" * 50)
    print("ℹ️  Key insight: QA endpoints need QA account, not regular PACER account")
    print("ℹ️  Using PRODUCTION endpoints with your regular credentials")
    
    tester = CorrectedPACERTest()
    success = tester.test_authentication()
    
    if success:
        print("\n🎊 Your PACER credentials work with production endpoints!")
        print("✅ The issue was using QA endpoints with production credentials")
    else:
        print("\n❌ Authentication still failing")
        print("🔧 Next steps:")
        print("1. Verify credentials work on https://pacer.uscourts.gov")
        print("2. Check if API access is enabled for your account")
        print("3. Contact PACER support: (800) 676-6856")


if __name__ == "__main__":
    main()