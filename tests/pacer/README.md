# PACER + RECAP Integration Test Implementation

This directory contains a complete implementation of PACER authentication integrated with CourtListener's RECAP Fetch API, based on the official PACER API documentation (May 2025).

## Features

- ✅ **Official PACER Authentication API** implementation
- ✅ **MFA/TOTP Support** with 30-second window
- ✅ **Filer Requirements** handling (redactFlag)
- ✅ **4 Integration Methods** tested automatically
- ✅ **Production-Ready** error handling and logging
- ✅ **Automatic Method Discovery** finds working approach

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
# Required
PACER_USERNAME=your_username
PACER_PASSWORD=your_password
COURTLISTENER_TOKEN=your_cl_token

# Optional but recommended
PACER_CLIENT_CODE=your_client_code
PACER_MFA_SECRET=your_base32_secret

# User type
PACER_USER_TYPE=regular  # or 'filer'

# Environment
PACER_ENVIRONMENT=QA  # or PRODUCTION
```

### 3. Run Integration Test

```bash
python pacer_integration.py
```

## Architecture

### PACERAuthenticator
- Handles PACER authentication following official API spec
- Supports MFA/TOTP generation
- Manages token lifecycle (23-hour expiry)
- Handles filer requirements automatically

### RECAPIntegrationTester
- Tests 4 different integration methods:
  1. Token field method (experimental)
  2. Token as password method
  3. Cookie header method
  4. Raw credentials method (fallback)
- Automatically discovers working method
- Monitors request completion

### ProductionPACERRECAPClient
- Production-ready client with automatic failover
- Caches working method for efficiency
- Handles token refresh automatically
- Context manager for proper cleanup

## Integration Methods Explained

### Method 1: Token Field
```python
data = {
    'pacer_username': username,
    'pacer_token': token,  # Experimental field
}
```

### Method 2: Token as Password
```python
data = {
    'pacer_username': username,
    'pacer_password': token,  # Token replaces password
}
```

### Method 3: Cookie Headers
```python
headers = {
    'Cookie': 'nextGenCSO=token; PacerClientCode=code'
}
```

### Method 4: Raw Credentials
```python
data = {
    'pacer_username': username,
    'pacer_password': password,
    'client_code': code  # Optional
}
```

## Usage in Production

```python
from pacer_integration import ProductionPACERRECAPClient

# Use as context manager for automatic cleanup
with ProductionPACERRECAPClient('PRODUCTION') as client:
    # Discover working method once
    client.discover_working_method('1:20-cv-12345', 'txed')
    
    # Fetch documents
    result = client.fetch_docket(
        docket_number='1:20-cv-12345',
        court='txed',
        show_parties_and_counsel=True
    )
    
    # Monitor completion
    if result.get('id'):
        status = client.recap_tester.monitor_request(result['id'])
```

## Error Handling

The implementation includes specific handling for:

1. **Authentication Errors**
   - Invalid credentials
   - MFA failures
   - Filer requirements
   - Disabled accounts

2. **Integration Errors**
   - HTTP errors
   - Timeout handling
   - Invalid responses

3. **Token Management**
   - Automatic refresh
   - Expiry tracking
   - Logout on exit

## Troubleshooting

### Common Issues

1. **"All filers must redact"**
   - Set `PACER_USER_TYPE=filer` in `.env`
   - This adds required `redactFlag: "1"`

2. **"Invalid username, password, or one-time passcode"**
   - Verify PACER_USERNAME and PACER_PASSWORD
   - Check MFA setup if using TOTP

3. **"A required Client Code was not entered"**
   - Warning only - login succeeds but no search privileges
   - Add PACER_CLIENT_CODE to enable search

4. **All methods fail**
   - Check CourtListener API token
   - Verify PACER credentials work on website
   - Try with QA environment first

### MFA Setup

To enable MFA:
1. Get your Base32 secret from PACER
2. Add to `.env`: `PACER_MFA_SECRET=YOUR_BASE32_SECRET`
3. The system generates TOTP codes automatically

## Security Notes

- Never commit `.env` files
- Tokens expire after 23 hours
- Always use logout() or context manager
- Store credentials securely in production

## Testing

Replace test docket numbers in `run_integration_test()` with real QA cases:

```python
test_cases = [
    {'docket_number': 'YOUR_QA_DOCKET', 'court': 'YOUR_COURT'},
]
```

## Support

For PACER issues:
- Call: (800) 676-6856
- Email: pacer@psc.uscourts.gov

For CourtListener/RECAP issues:
- See: https://www.courtlistener.com/help/api/