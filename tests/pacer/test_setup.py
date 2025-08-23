#!/usr/bin/env python3
"""
Test script to verify PACER integration setup
"""

import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test environment setup"""
    print("🔍 Testing Environment Setup")
    print("-" * 40)
    
    # Load environment
    load_dotenv()
    
    # Check required variables
    required_vars = {
        'PACER_USERNAME': 'PACER username',
        'PACER_PASSWORD': 'PACER password', 
        'COURTLISTENER_TOKEN': 'CourtListener API token'
    }
    
    optional_vars = {
        'PACER_CLIENT_CODE': 'PACER client code',
        'PACER_MFA_SECRET': 'MFA secret',
        'PACER_USER_TYPE': 'User type (regular/filer)',
        'PACER_ENVIRONMENT': 'Environment (QA/PRODUCTION)'
    }
    
    missing_required = []
    
    # Check required
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * 8} ({description})")
        else:
            print(f"❌ {var}: Missing ({description})")
            missing_required.append(var)
    
    print()
    
    # Check optional
    for var, description in optional_vars.items():
        value = os.environ.get(var)
        if value:
            if var == 'PACER_MFA_SECRET':
                print(f"✅ {var}: {'*' * 8} ({description})")
            else:
                print(f"✅ {var}: {value} ({description})")
        else:
            print(f"⚠️  {var}: Not set ({description})")
    
    print()
    
    if missing_required:
        print("❌ Missing required environment variables:")
        for var in missing_required:
            print(f"   - {var}")
        print("\nPlease copy .env.example to .env and fill in your credentials")
        return False
    
    # Test imports
    print("\n🔍 Testing Python Imports")
    print("-" * 40)
    
    try:
        import requests
        print("✅ requests")
    except ImportError:
        print("❌ requests - run: pip install requests")
        return False
    
    try:
        import pyotp
        print("✅ pyotp")
    except ImportError:
        print("❌ pyotp - run: pip install pyotp")
        return False
    
    try:
        import dotenv
        print("✅ python-dotenv")
    except ImportError:
        print("❌ python-dotenv - run: pip install python-dotenv")
        return False
    
    try:
        import aiohttp
        print("✅ aiohttp")
    except ImportError:
        print("❌ aiohttp - run: pip install aiohttp")
        return False
    
    # Check if main module can be imported
    print("\n🔍 Testing Main Module")
    print("-" * 40)
    
    try:
        from pacer_integration import (
            PACERAuthenticator,
            RECAPIntegrationTester,
            ProductionPACERRECAPClient,
            validate_environment
        )
        print("✅ All classes imported successfully")
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False
    
    # Validate using the module's validator
    print("\n🔍 Running Module Validation")
    print("-" * 40)
    
    try:
        validate_environment()
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        return False
    
    return True


def test_connectivity():
    """Test basic connectivity"""
    print("\n🔍 Testing Connectivity")
    print("-" * 40)
    
    import requests
    
    # Test CourtListener API
    try:
        token = os.environ.get('COURTLISTENER_TOKEN')
        if token:
            headers = {'Authorization': f'Token {token}'}
            response = requests.get(
                'https://www.courtlistener.com/api/rest/v4/',
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                print("✅ CourtListener API accessible")
            else:
                print(f"⚠️  CourtListener API returned {response.status_code}")
        else:
            print("⚠️  Skipping CourtListener test (no token)")
    except Exception as e:
        print(f"❌ CourtListener connectivity error: {e}")
    
    # Test PACER endpoints
    env = os.environ.get('PACER_ENVIRONMENT', 'QA').upper()
    if env == 'QA':
        pacer_url = 'https://qa-login.uscourts.gov'
    else:
        pacer_url = 'https://pacer.login.uscourts.gov'
    
    try:
        response = requests.get(pacer_url, timeout=5)
        if response.status_code in [200, 302, 403]:  # Various expected responses
            print(f"✅ PACER {env} endpoint accessible")
        else:
            print(f"⚠️  PACER {env} returned {response.status_code}")
    except Exception as e:
        print(f"❌ PACER connectivity error: {e}")


def main():
    """Run all tests"""
    print("🧪 PACER Integration Setup Test")
    print("=" * 50)
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment setup incomplete")
        print("Please fix the issues above and try again")
        sys.exit(1)
    
    # Test connectivity
    test_connectivity()
    
    print("\n" + "=" * 50)
    print("✅ Setup test completed!")
    print("\nNext steps:")
    print("1. Review any warnings above")
    print("2. Run the full integration test: python pacer_integration.py")
    print("3. Replace test docket numbers with real QA cases")


if __name__ == "__main__":
    main()