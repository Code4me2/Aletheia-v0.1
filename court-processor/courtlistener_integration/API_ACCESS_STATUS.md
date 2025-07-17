# CourtListener API Access Status

## Current Access Level: Basic

Your API token provides basic access to CourtListener's public APIs.

### ✅ What Works Now

1. **Search API** - Full functionality
   ```bash
   python3 search_transcripts.py
   ```
   - Search 8.4M+ documents for transcript references
   - Find opinions that quote transcripts
   - No special permissions required

2. **Courts API** - Full access
   - Information about 3,352 jurisdictions
   - Court metadata and identifiers

3. **Test Script**
   ```bash
   python3 test_recap_api.py
   ```
   - Shows which endpoints are accessible
   - Verifies API token is working

### ❌ What Requires RECAP Permissions

1. **RECAP Documents** (`/recap-documents/`)
   - Actual court filing PDFs
   - Transcript documents
   - Requires special permissions

2. **Docket Entries** (`/docket-entries/`)
   - Detailed docket entry information
   - Links to RECAP documents
   - Requires special permissions

3. **Bulk Download Scripts**
   - `bulk_download_enhanced.py`
   - `run_transcript_test.sh`
   - These will fail without RECAP access

### How to Get RECAP Access

1. Visit https://www.courtlistener.com/contact/
2. Or post in https://github.com/freelawproject/courtlistener/discussions
3. Explain your use case (research, analysis, etc.)
4. Reference your existing API token
5. Free Law Project will review and potentially grant access

### Working with Current Access

While waiting for RECAP permissions, you can:
- Use the Search API to find documents mentioning transcripts
- Extract transcript quotes from opinions
- Build systems that work with opinion text rather than full transcripts
- Prepare your infrastructure for when RECAP access is granted

All the code is ready - it just needs the proper API permissions to access RECAP documents.