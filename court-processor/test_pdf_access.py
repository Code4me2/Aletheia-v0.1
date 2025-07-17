#!/usr/bin/env python3
"""
Test PDF access on CourtListener API
Check what document access is available on free tier
"""
import requests
import json
from datetime import datetime

API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

headers = {'Authorization': f'Token {API_TOKEN}'}

print("=" * 70)
print("TESTING PDF/DOCUMENT ACCESS ON COURTLISTENER")
print("=" * 70)

# First, let's check what fields are available in our fetched data
print("\n1. Checking available fields in docket data...")

response = requests.get(
    f'{BASE_URL}/dockets/',
    headers=headers,
    params={'page_size': 1, 'court': 'cafc'}
)

if response.status_code == 200:
    data = response.json()
    if data['results']:
        docket = data['results'][0]
        print(f"✓ Docket fields available:")
        for key in docket.keys():
            if 'pdf' in key.lower() or 'download' in key.lower() or 'file' in key.lower() or 'document' in key.lower():
                print(f"  - {key}: {docket[key]}")
        
        # Check absolute_url
        if 'absolute_url' in docket:
            print(f"\n  - absolute_url: {docket['absolute_url']}")

# Check opinions endpoint for PDF URLs
print("\n2. Checking opinion data for PDF access...")

response = requests.get(
    f'{BASE_URL}/opinions/',
    headers=headers,
    params={'page_size': 2, 'court': 'cafc'}
)

if response.status_code == 200:
    data = response.json()
    if data['results']:
        print(f"✓ Opinion fields available:")
        opinion = data['results'][0]
        
        # Look for any URL or file-related fields
        pdf_related_fields = []
        for key, value in opinion.items():
            if any(term in key.lower() for term in ['url', 'pdf', 'download', 'file', 'path', 'text']):
                pdf_related_fields.append((key, value))
                print(f"  - {key}: {str(value)[:100]}...")
        
        # Check if we can access the download URL
        if 'download_url' in opinion and opinion['download_url']:
            print(f"\n3. Testing download_url access...")
            print(f"   URL: {opinion['download_url']}")
            
            try:
                # Try to access with our auth token
                pdf_response = requests.get(
                    opinion['download_url'],
                    headers=headers,
                    allow_redirects=True,
                    stream=True
                )
                
                print(f"   Status: {pdf_response.status_code}")
                print(f"   Content-Type: {pdf_response.headers.get('Content-Type', 'Not specified')}")
                
                if pdf_response.status_code == 200:
                    # Check if it's actually a PDF
                    content_type = pdf_response.headers.get('Content-Type', '')
                    if 'pdf' in content_type:
                        print("   ✅ PDF IS ACCESSIBLE!")
                        # Check file size
                        content_length = pdf_response.headers.get('Content-Length', 'Unknown')
                        print(f"   File size: {content_length} bytes")
                    else:
                        # Read first 500 chars to see what we got
                        content = pdf_response.text[:500]
                        print(f"   Content preview: {content[:200]}...")
                else:
                    print(f"   ❌ Access denied: {pdf_response.text[:200]}")
                    
            except Exception as e:
                print(f"   ❌ Error accessing URL: {e}")

# Check for opinion text
print("\n4. Checking for opinion text content...")
if data['results']:
    for i, opinion in enumerate(data['results'][:2]):
        text_fields = ['plain_text', 'html', 'html_lawbox', 'html_columbia', 'html_with_citations', 'xml_harvard']
        print(f"\n   Opinion {i+1}:")
        for field in text_fields:
            if field in opinion and opinion[field]:
                print(f"   ✅ {field}: Available ({len(str(opinion[field]))} chars)")
                print(f"      Preview: {str(opinion[field])[:100]}...")

# Test docket entries endpoint
print("\n5. Testing docket entries endpoint...")

# Get a docket ID first
response = requests.get(
    f'{BASE_URL}/dockets/',
    headers=headers,
    params={'page_size': 1, 'court': 'txed'}
)

if response.status_code == 200 and response.json()['results']:
    docket_id = response.json()['results'][0]['id']
    
    # Try to get entries for this docket
    entries_response = requests.get(
        f'{BASE_URL}/docket-entries/',
        headers=headers,
        params={'docket': docket_id, 'page_size': 5}
    )
    
    print(f"   Docket entries status: {entries_response.status_code}")
    
    if entries_response.status_code == 200:
        entries_data = entries_response.json()
        if entries_data['results']:
            print(f"   ✅ Docket entries accessible! Found {len(entries_data['results'])} entries")
            
            # Check for document URLs in entries
            entry = entries_data['results'][0]
            print(f"\n   First entry fields:")
            for key in ['description', 'filing_date', 'document_number', 'pacer_doc_id']:
                if key in entry:
                    print(f"   - {key}: {entry[key]}")
            
            # Check for recap_documents
            if 'recap_documents' in entry:
                print(f"   - recap_documents: {entry['recap_documents']}")

# Test RECAP documents endpoint
print("\n6. Testing RECAP documents endpoint...")

recap_response = requests.get(
    f'{BASE_URL}/recap/',
    headers=headers,
    params={'page_size': 5}
)

print(f"   RECAP endpoint status: {recap_response.status_code}")

# Summary
print("\n" + "=" * 70)
print("SUMMARY OF DOCUMENT ACCESS")
print("=" * 70)
print("""
Based on the tests above, we can determine:
1. Whether download_url fields lead to actual PDFs
2. Whether opinion text is available in various formats
3. Whether docket entries are accessible
4. Whether RECAP documents are available

This will show what document access is truly available on the free tier.
""")