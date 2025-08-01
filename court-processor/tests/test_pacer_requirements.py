#!/usr/bin/env python3
"""
Test PACER requirements and debug login issues
"""

import os
import json
from dotenv import load_dotenv

load_dotenv()

print("PACER Integration Debugging")
print("="*60)

# Get credentials
pacer_username = os.getenv('PACER_USERNAME')
pacer_password = os.getenv('PACER_PASSWORD')

print(f"Username: {pacer_username}")
print(f"Password length: {len(pacer_password)}")
print(f"Password contains dash: {'-' in pacer_password}")
print(f"Password starts with uppercase: {pacer_password[0].isupper() if pacer_password else 'N/A'}")

print("\n" + "="*60)
print("PACER Login Requirements:")
print("="*60)
print("""
Based on the error 'PacerLoginException: Invalid username/password: Login Failed':

1. **CourtListener is attempting to log into PACER on your behalf**
   - This happens server-side at CourtListener
   - They use your credentials to get PACER session cookies
   - The cookies are then used to fetch documents

2. **The login is failing at PACER's end**
   - PACER is rejecting the username/password combination
   - This happens before any cookies are created

3. **Possible reasons for login failure:**
   
   a) **Incorrect credentials**
      - Double-check username and password
      - Test login at https://pacer.uscourts.gov/
   
   b) **Account issues**
      - Account may be locked or suspended
      - Account may need payment method updated
      - Account may require password reset
   
   c) **PACER API vs Web differences**
      - Some PACER accounts have different access levels
      - API access might require special activation
   
   d) **Two-factor authentication**
      - If enabled, automated login won't work
   
   e) **CAPTCHA or security challenges**
      - PACER might be blocking automated logins

4. **Cookie handling is automatic**
   - CourtListener handles all cookie management
   - We don't need to manage cookies ourselves
   - The issue is happening before cookies are created

NEXT STEPS:
1. Log into PACER manually at https://pacer.uscourts.gov/
2. Verify account is active and can access cases
3. Check if there are any security warnings or required actions
4. Try resetting password if login works on web but not API
5. Contact PACER support about API access requirements
""")

# Check if credentials might have encoding issues
print("\n" + "="*60)
print("Credential Analysis:")
print("="*60)

# Check for potentially problematic characters
special_chars = set(pacer_password) - set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_')
if special_chars:
    print(f"Password contains special characters: {special_chars}")
    print("These might need special handling")
else:
    print("Password contains only alphanumeric characters and dash/underscore")

# Check if the error might be related to the specific PACER environment
print("\n" + "="*60)
print("PACER Environment Check:")
print("="*60)
print("""
PACER has different environments:
1. Production: https://pacer.uscourts.gov/
2. Training: https://dcecf.psc.uscourts.gov/cgi-bin/login.pl

Make sure your credentials are for the production environment.
CourtListener uses the production PACER system.
""")

print("\n" + "="*60)
print("RECOMMENDATION:")
print("="*60)
print("""
Since the RECAP availability checking works perfectly (saving money!),
and most documents are already in RECAP, you can:

1. Use the pipeline with existing RECAP documents (14+ million available)
2. Manually download any missing documents from PACER
3. Upload them to contribute to RECAP

The pipeline improvements (better search, text extraction, etc.) 
work great even without direct PACER access!
""")