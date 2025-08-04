#!/usr/bin/env python3
"""
PACER Authentication + RECAP Fetch Integration
Based on Official PACER Authentication API Documentation (May 2025)

This implementation includes:
- Complete PACER Authentication API specification
- MFA/TOTP support
- Filer requirements handling
- Multiple RECAP integration methods
- Production-ready error handling
"""

import os
import requests
import pyotp
import time
import json
import asyncio
import aiohttp
from typing import Dict, Optional, List
from datetime import datetime
from dotenv import load_dotenv


class PACERAuthenticator:
    """PACER Authentication client following official API documentation"""
    
    def __init__(self, environment='QA'):
        self.environment = environment
        self.base_url = self._get_base_url(environment)
        self.auth_url = f"{self.base_url}/services/cso-auth"
        self.logout_url = f"{self.base_url}/services/cso-logout"
        
        self.username = os.environ['PACER_USERNAME']
        self.password = os.environ['PACER_PASSWORD']
        self.client_code = os.environ.get('PACER_CLIENT_CODE')
        self.mfa_secret = os.environ.get('PACER_MFA_SECRET')
        
        self.token = None
        self.token_expiry = None
    
    def _get_base_url(self, environment):
        """Get base URL for environment"""
        urls = {
            'QA': 'https://qa-login.uscourts.gov',
            'PRODUCTION': 'https://pacer.login.uscourts.gov'
        }
        return urls.get(environment.upper(), urls['QA'])
    
    def _generate_otp(self) -> Optional[str]:
        """Generate TOTP code for MFA"""
        if not self.mfa_secret:
            return None
        
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.now()
    
    def authenticate(self) -> Dict:
        """Authenticate with PACER (follows official API documentation)"""
        print("🔐 Authenticating with PACER...")
        
        auth_data = {
            'loginId': self.username,
            'password': self.password,
        }
        
        # Client code (may be required for search privileges)
        if self.client_code:
            auth_data['clientCode'] = self.client_code
        
        # MFA one-time passcode (required if MFA enabled)
        otp = self._generate_otp()
        if otp:
            auth_data['otpCode'] = otp
            print(f"📱 Using MFA code: {otp}")
        
        # Redaction flag (REQUIRED for filers per documentation)
        if os.environ.get('PACER_USER_TYPE') == 'filer':
            auth_data['redactFlag'] = '1'
            print("⚖️ Added redaction flag (required for filers)")
        
        try:
            response = requests.post(
                self.auth_url, 
                json=auth_data,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            response.raise_for_status()
            result = response.json()
            
            if result['loginResult'] == '0':
                self.token = result['nextGenCSO']
                self.token_expiry = time.time() + (23 * 60 * 60)  # 23 hours
                
                print(f"✅ PACER authentication successful")
                print(f"🎫 Token length: {len(self.token)} characters")
                
                # Check for warnings in successful response
                if result.get('errorDescription'):
                    self._handle_auth_warning(result['errorDescription'])
                
                return {'success': True, 'token': self.token, 'error': ''}
            else:
                error = result.get('errorDescription', 'Unknown error')
                print(f"❌ PACER authentication failed: {error}")
                self._handle_auth_error(error)
                return {'success': False, 'token': None, 'error': error}
                
        except Exception as e:
            print(f"💥 PACER authentication exception: {e}")
            return {'success': False, 'token': None, 'error': str(e)}
    
    def _handle_auth_warning(self, error_description: str):
        """Handle successful authentication with warnings (from PACER documentation)"""
        if "A required Client Code was not entered" in error_description:
            print("⚠️ CLIENT CODE WARNING: You can log in but won't have search privileges")
            print("💡 Solution: Set PACER_CLIENT_CODE environment variable")
        elif "your current account has been disabled" in error_description:
            print("⚠️ ACCOUNT WARNING: Account disabled but login successful")
            print("📞 Contact PACER Service Center: (800) 676-6856")
    
    def _handle_auth_error(self, error_description: str):
        """Handle authentication errors with specific solutions (from PACER documentation)"""
        error_solutions = {
            "All filers must redact": {
                'solution': 'Add redactFlag: "1" to request',
                'action': 'Set PACER_USER_TYPE=filer in environment'
            },
            "Invalid username, password, or one-time passcode": {
                'solution': 'Verify credentials and MFA code',
                'action': 'Check PACER_USERNAME, PACER_PASSWORD, and MFA setup'
            },
            "your current account has been disabled": {
                'solution': 'Contact PACER Service Center',
                'action': 'Call (800) 676-6856 or email pacer@psc.uscourts.gov'
            }
        }
        
        for error_key, solution in error_solutions.items():
            if error_key in error_description:
                print(f"💡 Solution: {solution['solution']}")
                print(f"🔧 Action: {solution['action']}")
                return
        
        print("❓ Unrecognized error - check PACER documentation")
    
    def get_cookie_header(self) -> str:
        """Generate cookie header for requests"""
        if not self.token:
            raise ValueError("No authentication token available")
        
        cookie = f"nextGenCSO={self.token}"
        if self.client_code:
            cookie += f"; PacerClientCode={self.client_code}"
        
        return cookie
    
    def logout(self) -> bool:
        """Logout and invalidate token"""
        if not self.token:
            return True
        
        try:
            response = requests.post(
                self.logout_url,
                json={'nextGenCSO': self.token},
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
            )
            result = response.json()
            
            if result.get('loginResult') == '0':
                print("✅ PACER logout successful")
                self.token = None
                self.token_expiry = None
                return True
            else:
                print(f"⚠️ PACER logout failed: {result.get('errorDescription')}")
                return False
                
        except Exception as e:
            print(f"💥 PACER logout exception: {e}")
            return False


class RECAPIntegrationTester:
    """Test various RECAP integration methods"""
    
    def __init__(self, pacer_auth: PACERAuthenticator):
        self.pacer_auth = pacer_auth
        self.recap_url = 'https://www.courtlistener.com/api/rest/v4/recap-fetch/'
        self.courtlistener_token = os.environ['COURTLISTENER_TOKEN']
        
        self.test_results = {
            'token_field_method': None,
            'token_as_password_method': None,
            'cookie_header_method': None,
            'raw_credentials_method': None
        }
    
    def _get_base_headers(self):
        """Get base headers for RECAP requests"""
        return {
            'Authorization': f'Token {self.courtlistener_token}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
    
    def test_token_field_method(self, docket_number: str, court: str) -> Dict:
        """Method 1: Test pacer_token field (experimental)"""
        print("\n🧪 Testing Method 1: pacer_token field")
        
        if not self.pacer_auth.token:
            return {'success': False, 'error': 'No PACER token available'}
        
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_token': self.pacer_auth.token,  # Experimental field
        }
        
        try:
            response = requests.post(self.recap_url, data=data, headers=self._get_base_headers())
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Token field method successful!")
                return {'success': True, 'response': result}
            else:
                print(f"❌ Token field method failed: HTTP {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text[:200]}
                
        except Exception as e:
            print(f"💥 Token field method exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_token_as_password_method(self, docket_number: str, court: str) -> Dict:
        """Method 2: Test token in password field"""
        print("\n🧪 Testing Method 2: token as password")
        
        if not self.pacer_auth.token:
            return {'success': False, 'error': 'No PACER token available'}
        
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_password': self.pacer_auth.token,  # Token as password
        }
        
        try:
            response = requests.post(self.recap_url, data=data, headers=self._get_base_headers())
            
            if response.status_code in [200, 201]:  # 201 Created is also success!
                result = response.json()
                print("✅ Token as password method successful!")
                return {'success': True, 'response': result}
            else:
                print(f"❌ Token as password method failed: HTTP {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text[:200]}
                
        except Exception as e:
            print(f"💥 Token as password method exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_cookie_header_method(self, docket_number: str, court: str) -> Dict:
        """Method 3: Test PACER cookies in headers"""
        print("\n🧪 Testing Method 3: PACER cookies")
        
        if not self.pacer_auth.token:
            return {'success': False, 'error': 'No PACER token available'}
        
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            # No password - rely on cookies
        }
        
        headers = self._get_base_headers()
        headers['Cookie'] = self.pacer_auth.get_cookie_header()
        
        try:
            response = requests.post(self.recap_url, data=data, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                print("✅ Cookie header method successful!")
                return {'success': True, 'response': result}
            else:
                print(f"❌ Cookie header method failed: HTTP {response.status_code}")
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text[:200]}
                
        except Exception as e:
            print(f"💥 Cookie header method exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_raw_credentials_method(self, docket_number: str, court: str) -> Dict:
        """Method 4: Test raw credentials (fallback)"""
        print("\n🧪 Testing Method 4: raw credentials")
        
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_password': self.pacer_auth.password,
        }
        
        if self.pacer_auth.client_code:
            data['client_code'] = self.pacer_auth.client_code
        
        try:
            response = requests.post(self.recap_url, data=data, headers=self._get_base_headers())
            
            if response.status_code in [200, 201]:  # 201 Created is also success!
                result = response.json()
                print("✅ Raw credentials method successful!")
                return {'success': True, 'response': result}
            else:
                print(f"❌ Raw credentials method failed: HTTP {response.status_code}")
                print(f"Response preview: {response.text[:300]}")
                return {'success': False, 'error': f'HTTP {response.status_code}', 'response': response.text}
                
        except Exception as e:
            print(f"💥 Raw credentials method exception: {e}")
            return {'success': False, 'error': str(e)}
    
    def run_comprehensive_test(self, docket_number: str, court: str) -> Dict:
        """Run all integration tests"""
        print(f"🚀 Starting comprehensive RECAP integration test")
        print(f"📋 Target: {docket_number} in {court}")
        print("=" * 70)
        
        # Test all methods
        methods = [
            ('token_field_method', self.test_token_field_method),
            ('token_as_password_method', self.test_token_as_password_method),
            ('cookie_header_method', self.test_cookie_header_method),
            ('raw_credentials_method', self.test_raw_credentials_method),
        ]
        
        for method_name, method_func in methods:
            try:
                result = method_func(docket_number, court)
                self.test_results[method_name] = result
                
                # If successful, monitor the request
                if result.get('success') and 'response' in result:
                    request_id = result['response'].get('id')
                    if request_id:
                        print(f"📊 Monitoring request {request_id}...")
                        final_result = self.monitor_request(request_id)
                        self.test_results[method_name]['final_status'] = final_result
                        
                        # If this method works, we can stop testing
                        if final_result.get('status') in [2, 5]:
                            print(f"🎉 {method_name} completed successfully!")
                            break
                
            except Exception as e:
                print(f"💥 {method_name} failed with exception: {e}")
                self.test_results[method_name] = {'success': False, 'error': str(e)}
        
        return self.test_results
    
    def monitor_request(self, request_id: str, timeout: int = 300) -> Dict:
        """Monitor RECAP request status"""
        status_url = f"{self.recap_url}{request_id}/"
        headers = {'Authorization': f'Token {self.courtlistener_token}'}
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(status_url, headers=headers)
                
                if response.status_code == 200:
                    status_data = response.json()
                    status = status_data.get('status')
                    
                    if status in [2, 5]:  # Success
                        print(f"✅ Request completed successfully!")
                        return status_data
                    elif status in [3, 6]:  # Failed
                        print(f"❌ Request failed: {status_data.get('error_message')}")
                        return status_data
                    else:
                        print(f"⏳ Status: {status}")
                        time.sleep(5)
                else:
                    print(f"⚠️ Status check failed: {response.status_code}")
                    time.sleep(5)
            
            except Exception as e:
                print(f"💥 Status check exception: {e}")
                time.sleep(5)
        
        return {'error': 'Timeout waiting for completion', 'status': 'timeout'}


class ProductionPACERRECAPClient:
    """Production-ready PACER/RECAP integration client"""
    
    def __init__(self, environment='QA'):
        self.pacer_auth = PACERAuthenticator(environment)
        self.recap_tester = RECAPIntegrationTester(self.pacer_auth)
        self.preferred_method = None
        self.method_cache = {}
    
    def discover_working_method(self, test_docket: str, test_court: str) -> str:
        """Discover which integration method works"""
        print("🔍 Discovering working authentication method...")
        
        # First, authenticate with PACER
        auth_result = self.pacer_auth.authenticate()
        if not auth_result['success']:
            raise Exception(f"PACER authentication failed: {auth_result['error']}")
        
        # Test all methods
        results = self.recap_tester.run_comprehensive_test(test_docket, test_court)
        
        # Determine preferred method
        method_priority = [
            'token_field_method',
            'token_as_password_method', 
            'cookie_header_method',
            'raw_credentials_method'
        ]
        
        for method in method_priority:
            if results.get(method, {}).get('success'):
                self.preferred_method = method
                print(f"✅ Preferred method: {method}")
                return method
        
        raise Exception("No working authentication method found")
    
    def fetch_docket(self, docket_number: str, court: str, **kwargs) -> Dict:
        """Production docket fetch with optimal method"""
        if not self.preferred_method:
            raise Exception("No authentication method configured. Run discover_working_method() first.")
        
        # Ensure we have a valid PACER token
        if not self.pacer_auth.token or time.time() > (self.pacer_auth.token_expiry or 0):
            auth_result = self.pacer_auth.authenticate()
            if not auth_result['success']:
                raise Exception(f"PACER re-authentication failed: {auth_result['error']}")
        
        # Execute request using preferred method
        if self.preferred_method == 'token_field_method':
            return self._fetch_with_token_field(docket_number, court, **kwargs)
        elif self.preferred_method == 'token_as_password_method':
            return self._fetch_with_token_password(docket_number, court, **kwargs)
        elif self.preferred_method == 'cookie_header_method':
            return self._fetch_with_cookies(docket_number, court, **kwargs)
        else:
            return self._fetch_with_credentials(docket_number, court, **kwargs)
    
    def _fetch_with_token_field(self, docket_number: str, court: str, **kwargs) -> Dict:
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_token': self.pacer_auth.token,
            **kwargs
        }
        return self._execute_request(data)
    
    def _fetch_with_token_password(self, docket_number: str, court: str, **kwargs) -> Dict:
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_password': self.pacer_auth.token,
            **kwargs
        }
        return self._execute_request(data)
    
    def _fetch_with_cookies(self, docket_number: str, court: str, **kwargs) -> Dict:
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            **kwargs
        }
        
        headers = {
            'Authorization': f'Token {os.environ["COURTLISTENER_TOKEN"]}',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Cookie': self.pacer_auth.get_cookie_header()
        }
        
        return self._execute_request(data, headers)
    
    def _fetch_with_credentials(self, docket_number: str, court: str, **kwargs) -> Dict:
        data = {
            'request_type': 1,
            'docket_number': docket_number,
            'court': court,
            'pacer_username': self.pacer_auth.username,
            'pacer_password': self.pacer_auth.password,
            **kwargs
        }
        
        if self.pacer_auth.client_code:
            data['client_code'] = self.pacer_auth.client_code
        
        return self._execute_request(data)
    
    def _execute_request(self, data: Dict, headers: Dict = None) -> Dict:
        if headers is None:
            headers = {
                'Authorization': f'Token {os.environ["COURTLISTENER_TOKEN"]}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        
        response = requests.post(self.recap_tester.recap_url, data=data, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pacer_auth.logout()


def validate_environment():
    """Validate environment setup"""
    load_dotenv()
    
    required = ['PACER_USERNAME', 'PACER_PASSWORD', 'COURTLISTENER_TOKEN']
    missing = [var for var in required if not os.environ.get(var)]
    
    if missing:
        raise EnvironmentError(f"Missing required variables: {', '.join(missing)}")
    
    # Validate filer requirements (from PACER documentation)
    user_type = os.environ.get('PACER_USER_TYPE', 'regular')
    if user_type == 'filer':
        print("⚖️ Filer detected - redaction flag will be required")
        if not os.environ.get('PACER_MFA_SECRET'):
            print("⚠️ WARNING: Filers typically require MFA enrollment")
    
    # Validate MFA setup if secret provided
    if os.environ.get('PACER_MFA_SECRET'):
        secret = os.environ['PACER_MFA_SECRET']
        if len(secret) < 16:
            raise ValueError("PACER_MFA_SECRET appears invalid (too short)")
        print("📱 MFA configured")
    
    print("✅ Environment validation passed")
    return True


def run_integration_test():
    """Complete integration test"""
    print("🧪 PACER + RECAP Integration Test")
    print("=" * 50)
    
    # Validate environment
    try:
        validate_environment()
    except EnvironmentError as e:
        print(f"❌ Environment validation failed: {e}")
        return False
    
    # Test with known case (replace with actual test case)
    test_cases = [
        {'docket_number': '1:20-cv-12345', 'court': 'txed'},
        {'docket_number': '2:21-cv-67890', 'court': 'cand'},
    ]
    
    # Use PRODUCTION (not QA) for regular PACER accounts!
    environment = os.environ.get('PACER_ENVIRONMENT', 'PRODUCTION')
    with ProductionPACERRECAPClient(environment) as client:
        for i, test_case in enumerate(test_cases):
            print(f"\n📋 Test Case {i+1}: {test_case['docket_number']} in {test_case['court']}")
            
            try:
                # Discover working method (only needed once)
                if not client.preferred_method:
                    method = client.discover_working_method(
                        test_case['docket_number'], 
                        test_case['court']
                    )
                    print(f"✅ Discovered working method: {method}")
                
                # Test production fetch
                result = client.fetch_docket(
                    test_case['docket_number'],
                    test_case['court'],
                    show_parties_and_counsel=True
                )
                
                print(f"✅ Fetch successful! Request ID: {result.get('id')}")
                
                # Monitor completion
                if result.get('id'):
                    final_status = client.recap_tester.monitor_request(result['id'])
                    
                    if final_status.get('status') in [2, 5]:
                        print(f"🎉 Complete success for test case {i+1}!")
                        return True
                    else:
                        print(f"⚠️ Request failed: {final_status.get('error_message')}")
                
            except Exception as e:
                print(f"💥 Test case {i+1} failed: {e}")
                continue
    
    return False


if __name__ == "__main__":
    success = run_integration_test()
    if success:
        print("\n🎊 Integration test completed successfully!")
        print("✅ Ready for production implementation")
    else:
        print("\n❌ Integration test failed")
        print("🔧 Check logs and troubleshoot authentication issues")