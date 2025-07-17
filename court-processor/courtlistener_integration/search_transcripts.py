#!/usr/bin/env python3
"""
Search for transcript data using the CourtListener Search API
"""
import os
import json
import requests
from datetime import datetime, timedelta

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

if not API_TOKEN:
    print("Error: COURTLISTENER_API_TOKEN not set")
    exit(1)

headers = {
    'Authorization': f'Token {API_TOKEN}',
    'User-Agent': 'Aletheia-v0.1/1.0'
}

print("=== CourtListener Transcript Search ===\n")

# Search for documents containing transcript-related keywords
search_terms = [
    '"court transcript"',
    '"hearing transcript"',
    '"trial transcript"',
    '"deposition transcript"',
    '"oral argument transcript"'
]

# Courts with high IP case volume
ip_courts = ['txed', 'deld', 'cand', 'cafc']

total_results = 0

for term in search_terms:
    print(f"\nSearching for: {term}")
    print("-" * 50)
    
    try:
        # Search in opinions
        response = requests.get(
            f"{BASE_URL}search/",
            headers=headers,
            params={
                'q': term,
                'type': 'o',  # opinions
                'order_by': 'dateFiled desc',
                'page_size': 10
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            total_results += count
            
            print(f"Found {count:,} results")
            
            # Show first few results
            results = data.get('results', [])
            if results:
                print("\nSample results:")
                for i, result in enumerate(results[:3], 1):
                    print(f"\n{i}. Case: {result.get('caseName', 'Unknown')}")
                    print(f"   Court: {result.get('court', 'Unknown')}")
                    print(f"   Date: {result.get('dateFiled', 'Unknown')}")
                    print(f"   Type: {result.get('type', 'Unknown')}")
                    
                    # Check if snippet contains actual transcript content
                    snippet = result.get('snippet', '')
                    if snippet:
                        # Clean and truncate snippet
                        clean_snippet = snippet.replace('<mark>', '**').replace('</mark>', '**')
                        if len(clean_snippet) > 200:
                            clean_snippet = clean_snippet[:200] + "..."
                        print(f"   Snippet: {clean_snippet}")
                        
        else:
            print(f"Search failed with status {response.status_code}")
            if response.status_code == 429:
                print("Rate limit exceeded - waiting...")
                
    except Exception as e:
        print(f"Error: {e}")

print(f"\n\nTotal results found: {total_results:,}")

# Try to find recent documents from IP courts
print("\n\n=== Recent Documents from IP Courts ===")

for court in ip_courts[:2]:  # Just test first two courts
    print(f"\nCourt: {court}")
    try:
        response = requests.get(
            f"{BASE_URL}search/",
            headers=headers,
            params={
                'q': 'transcript',
                'type': 'o',
                'court': court,
                'filed_after': (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d'),
                'order_by': 'dateFiled desc',
                'page_size': 5
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            count = data.get('count', 0)
            print(f"Found {count:,} recent documents mentioning transcripts")
            
            results = data.get('results', [])
            for result in results[:2]:
                print(f"  - {result.get('caseName', 'Unknown')} ({result.get('dateFiled', 'Unknown')})")
                
    except Exception as e:
        print(f"Error searching {court}: {e}")

print("\n=== Search Complete ===")

# Summary of access
print(f"\n\nNote: This search uses the public Search API.")
print("To download actual transcript PDFs, RECAP permissions are required.")
print("Contact Free Law Project to request access.")