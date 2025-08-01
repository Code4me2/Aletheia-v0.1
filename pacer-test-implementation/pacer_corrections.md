#!/usr/bin/env python3
"""
CORRECTED PACER API Implementation
Uses PRODUCTION endpoints with regular PACER credentials
(QA endpoints require separate QA account registration)
"""

import requests
import pyotp
import os

class CorrectedPACERAPI:
    """PACER API using correct endpoint/credential combinations"""
    
    def __init__(self, use_production=True):
        """
        Initialize with correct endpoints
        
        Args:
            use_production (bool): True for production, False for QA
                                 Note: QA requires separate QA account!
        """
        if use_production:
            # PRODUCTION endpoints - use with regular PACER credentials
            self.auth_url = 'https://pacer.login.uscourts.gov/services/cso-auth'
            self.logout_url = 'https://pacer.login.uscourts.gov/services/cso-logout'
            self.env_name = "PRODUCTION"
            print("🏭 Using PRODUCTION endpoints with regular PACER credentials")
        else:
            # QA endpoints - requires SEPARATE QA account from qa-pacer.uscourts.gov
            self.auth_url = 'https://qa-login.uscourts.gov/services/cso-auth'
            self.logout_url = 'https://qa-login.uscourts.gov/services/cso-logout'
            self.env_name = "QA"
            print("🧪 Using QA endpoints - REQUIRES SEPARATE QA ACCOUNT!")
            print("ℹ️  Register QA account at: https://qa-pacer.uscourts.gov")
        
        # Get credentials from environment
        self.username = os.environ.get('PACER_USERNAME')
        self.password = os.environ.get('PACER_PASSWORD')
        self.client_code = os.environ.get('PACER_CLIENT_CODE')
        self.mfa_secret = os.environ.get('PACER_MFA_SECRET')
        self.is_filer = os.environ.get('PACER_IS_FILER') == 'true'
        
        # Validate credentials
        if not self.username or not self.password:
            raise ValueError("PACER_USERNAME and PACER_PASSWORD environment variables required")
        
        self.token = None
        
        print(f"📊 Environment: {self.env_name}")
        print(f"👤 Username: {self.username}")
        print(f"🔐 MFA Enabled: {'Yes' if self.mfa_secret else 'No'}")
        print(f"⚖️  Filer Account: {'Yes' if self.is_filer else 'No'}")
    
    def get_mfa_code(self):
        """Generate MFA code if secret is configured"""
        if not self.mfa_secret:
            return None
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.now()
    
    def authenticate(self):
        """
        Authenticate with PACER using correct endpoint/credential combination
        """
        print(f"\n🔐 Authenticating with {self.env_name} PACER...")
        
        # Build authentication request
        auth_data = {
            'loginId': self.username,
            'password': self.password,
        }
        
        # Add optional fields
        if self.client_code:
            auth_data['clientCode'] = self.client_code
            print(f"🏢 Using client code: {self.client_code}")
        
        # Add MFA if configured
        mfa_code = self.get_mfa_code()
        if mfa_code:
            auth_data['otpCode'] = mfa_code
            print(f"📱 Using MFA code: {mfa_code}")
        
        # Add redaction flag for filers
        if self.is_filer:
            auth_data['redactFlag'] = '1'
            print("⚖️ Added redaction flag (filer account)")
        
        # Make authentication request
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            print(f"🌐 Calling: {self.auth_url}")
            response = requests.post(self.auth_url, json=auth_data, headers=headers)
            
            print(f"📡 HTTP Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"❌ HTTP Error: {response.status_code}")
                print(f"Response: {response.text[:500]}")
                raise Exception(f"HTTP {response.status_code}: {response.text}")
            
            result = response.json()
            print(f"📋 PACER Response: {result}")
            
            # Parse result
            login_result = result.get('loginResult')
            error_description = result.get('errorDescription', '')
            
            if login_result == '0':
                # Success!
                self.token = result['nextGenCSO']
                print(f"✅ Authentication successful!")
                print(f"🎫 Token: {self.token[:20]}... ({len(self.token)} chars)")
                
                # Print any warnings
                if error_description:
                    print(f"⚠️ Warning: {error_description}")
                    self._handle_warning(error_description)
                
                return self.token
            else:
                # Authentication failed
                print(f"❌ Authentication failed!")
                print(f"🔍 Login Result: {login_result}")
                print(f"📝 Error: {error_description}")
                
                self._handle_error(error_description)
                raise Exception(f"PACER authentication failed: {error_description}")
        
        except requests.RequestException as e:
            print(f"💥 Network error: {e}")
            raise Exception(f"Network error connecting to PACER: {e}")
        except Exception as e:
            print(f"💥 Unexpected error: {e}")
            raise
    
    def _handle_warning(self, error_description):
        """Handle warnings in successful authentication"""
        if "A required Client Code was not entered" in error_description:
            print("💡 SOLUTION: Set PACER_CLIENT_CODE environment variable")
            print("📞 Contact PACER Service Center to get a client code: (800) 676-6856")
    
    def _handle_error(self, error_description):
        """Handle authentication errors with specific solutions"""
        
        solutions = {
            "All filers must redact": {
                'fix': "Set PACER_IS_FILER=true environment variable",
                'explanation': "Filers must include redactFlag in authentication"
            },
            "Invalid username, password, or one-time passcode": {
                'fix': "Check credentials and MFA setup",
                'explanation': "Verify PACER_USERNAME, PACER_PASSWORD, and MFA secret"
            },
            "your current account has been disabled": {
                'fix': "Contact PACER Service Center: (800) 676-6856",
                'explanation': "Account needs reactivation"
            },
            "Access denied": {
                'fix': "Contact PACER Service Center to enable API access",
                'explanation': "Your account may not have API permissions enabled"
            }
        }
        
        for error_key, solution in solutions.items():
            if error_key.lower() in error_description.lower():
                print(f"🔧 FIX: {solution['fix']}")
                print(f"📖 INFO: {solution['explanation']}")
                return
        
        print("❓ Unknown error - contact PACER Service Center for assistance")
        print("📞 Phone: (800) 676-6856")
        print("📧 Email: pacer@psc.uscourts.gov")
    
    def get_request_headers(self):
        """Get headers for subsequent PACER requests"""
        if not self.token:
            raise Exception("No authentication token. Call authenticate() first.")
        
        cookie = f"nextGenCSO={self.token}"
        if self.client_code:
            cookie += f"; PacerClientCode={self.client_code}"
        
        return {
            'Cookie': cookie,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def logout(self):
        """Logout and invalidate token"""
        if not self.token:
            print("ℹ️  No active token to logout")
            return True
        
        print(f"\n🚪 Logging out from {self.env_name}...")
        
        logout_data = {'nextGenCSO': self.token}
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        try:
            response = requests.post(self.logout_url, json=logout_data, headers=headers)
            result = response.json()
            
            if result.get('loginResult') == '0':
                print("✅ Logout successful")
                self.token = None
                return True
            else:
                print(f"⚠️ Logout failed: {result.get('errorDescription')}")
                return False
        
        except Exception as e:
            print(f"💥 Logout error: {e}")
            return False


def test_both_approaches():
    """Test both production and QA to demonstrate the difference"""
    
    print("🔬 TESTING BOTH APPROACHES")
    print("=" * 60)
    
    # Test 1: Production endpoints (should work with regular credentials)
    print("\n1️⃣ TESTING PRODUCTION ENDPOINTS")
    print("-" * 40)
    
    try:
        pacer_prod = CorrectedPACERAPI(use_production=True)
        token = pacer_prod.authenticate()
        
        if token:
            print("🎉 PRODUCTION SUCCESS!")
            headers = pacer_prod.get_request_headers()
            print(f"📋 Headers for PACER API calls: {headers}")
            pacer_prod.logout()
        
    except Exception as e:
        print(f"❌ Production test failed: {e}")
    
    # Test 2: QA endpoints (likely to fail unless you have QA account)
    print("\n2️⃣ TESTING QA ENDPOINTS")
    print("-" * 40)
    
    try:
        pacer_qa = CorrectedPACERAPI(use_production=False)
        token = pacer_qa.authenticate()
        
        if token:
            print("🎉 QA SUCCESS!")
            pacer_qa.logout()
        
    except Exception as e:
        print(f"❌ QA test failed (expected if no QA account): {e}")
        print("💡 To use QA: Register separate account at https://qa-pacer.uscourts.gov")


def quick_production_test():
    """Quick test of production endpoints"""
    print("🚀 QUICK PRODUCTION TEST")
    print("=" * 30)
    
    try:
        pacer = CorrectedPACERAPI(use_production=True)
        token = pacer.authenticate()
        
        if token:
            print("\n🎊 SUCCESS! Your PACER credentials work!")
            print("✅ You can now use PACER API with production endpoints")
            
            # Show how to use the token
            headers = pacer.get_request_headers()
            print(f"\n📋 Use these headers for PACER API calls:")
            print(f"    {headers}")
            
            pacer.logout()
            return True
        
    except Exception as e:
        print(f"\n❌ Still having issues: {e}")
        print("\n🔧 NEXT STEPS:")
        print("1. Verify your PACER credentials work on pacer.uscourts.gov")
        print("2. Contact PACER Service Center: (800) 676-6856")
        print("3. Ask about enabling API access for your account")
        return False


if __name__ == "__main__":
    # Set up your environment variables first:
    # export PACER_USERNAME="your_username"
    # export PACER_PASSWORD="your_password"
    # export PACER_CLIENT_CODE="your_client_code"  # if you have one
    # export PACER_MFA_SECRET="your_mfa_secret"    # if MFA enabled
    # export PACER_IS_FILER="true"                 # if you're a filer
    
    # Then run one of these tests:
    
    quick_production_test()        # Recommended: test production only
    # test_both_approaches()       # Compare production vs QA
