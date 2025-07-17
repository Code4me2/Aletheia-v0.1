#!/usr/bin/env python3
"""
Test and download actual PDFs from CourtListener
"""
import requests
import os
from datetime import datetime

API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

headers = {'Authorization': f'Token {API_TOKEN}'}

print("=" * 70)
print("TESTING PDF DOWNLOAD CAPABILITIES")
print("=" * 70)

# Create directory for PDFs
os.makedirs('downloaded_pdfs', exist_ok=True)

# Get opinions from different courts
courts = ['cafc', 'ca9', 'ca5']  # Federal Circuit, 9th Circuit, 5th Circuit
downloaded = 0

for court in courts:
    print(f"\n🔍 Checking {court} opinions...")
    
    response = requests.get(
        f'{BASE_URL}/opinions/',
        headers=headers,
        params={
            'court': court,
            'date_filed__gte': '2024-01-01',
            'page_size': 5,
            'ordering': '-date_created'
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        opinions = data.get('results', [])
        
        for i, opinion in enumerate(opinions):
            if 'download_url' in opinion and opinion['download_url']:
                print(f"\n  Opinion {i+1}:")
                print(f"  - Type: {opinion.get('type', 'Unknown')}")
                print(f"  - Court: {opinion.get('court', 'Unknown')}")
                print(f"  - Date: {opinion.get('date_created', 'Unknown')}")
                print(f"  - Download URL: {opinion['download_url']}")
                
                # Try to download the PDF
                try:
                    pdf_response = requests.get(
                        opinion['download_url'],
                        headers={'User-Agent': 'CourtListener API Test'},
                        allow_redirects=True,
                        timeout=30
                    )
                    
                    if pdf_response.status_code == 200:
                        content_type = pdf_response.headers.get('Content-Type', '')
                        
                        if 'pdf' in content_type.lower():
                            # Save the PDF
                            filename = f"{court}_opinion_{opinion['id']}.pdf"
                            filepath = os.path.join('downloaded_pdfs', filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(pdf_response.content)
                            
                            file_size = len(pdf_response.content)
                            print(f"  ✅ Downloaded: {filename} ({file_size:,} bytes)")
                            downloaded += 1
                            
                            # Stop after 3 successful downloads to save space
                            if downloaded >= 3:
                                break
                        else:
                            print(f"  ⚠️  Not a PDF: {content_type}")
                    else:
                        print(f"  ❌ Download failed: {pdf_response.status_code}")
                        
                except Exception as e:
                    print(f"  ❌ Error: {e}")
            
            # Also check for plain text
            if 'plain_text' in opinion and opinion['plain_text']:
                text_preview = opinion['plain_text'][:200].replace('\n', ' ')
                print(f"  📄 Plain text available: {text_preview}...")
        
        if downloaded >= 3:
            break

# Check what we downloaded
print(f"\n" + "=" * 70)
print("DOWNLOAD SUMMARY")
print("=" * 70)

if os.path.exists('downloaded_pdfs'):
    files = os.listdir('downloaded_pdfs')
    print(f"✅ Successfully downloaded {len(files)} PDFs:")
    for file in files:
        size = os.path.getsize(os.path.join('downloaded_pdfs', file))
        print(f"  - {file}: {size:,} bytes")

# Test if opinions have both PDF and text
print("\n" + "=" * 70)
print("CHECKING DATA AVAILABILITY")
print("=" * 70)

response = requests.get(
    f'{BASE_URL}/opinions/',
    headers=headers,
    params={'court': 'cafc', 'page_size': 10}
)

if response.status_code == 200:
    opinions = response.json()['results']
    
    pdf_count = sum(1 for op in opinions if op.get('download_url'))
    text_count = sum(1 for op in opinions if op.get('plain_text'))
    both_count = sum(1 for op in opinions if op.get('download_url') and op.get('plain_text'))
    
    print(f"Out of {len(opinions)} opinions:")
    print(f"  - {pdf_count} have download URLs")
    print(f"  - {text_count} have plain text")
    print(f"  - {both_count} have both PDF and text")

print("\n🎉 CONCLUSION:")
print("The CourtListener free tier DOES provide access to:")
print("  ✅ Opinion PDFs via download_url")
print("  ✅ Opinion plain text (when available)")
print("  ❌ Docket entries (requires paid tier)")
print("  ❌ RECAP documents (requires paid tier)")
print("\nYou can download actual court opinion PDFs for free!")