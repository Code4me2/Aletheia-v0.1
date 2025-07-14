#!/usr/bin/env python3
"""
Test CourtListener RECAP API endpoints
Verify access to RECAP documents and transcripts
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

class RECAPTester:
    """Test RECAP API endpoints"""
    
    def __init__(self, api_token: str):
        if not api_token:
            raise ValueError("API token required")
            
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
    
    def test_recap_endpoints(self):
        """Test various RECAP endpoints"""
        print("=== Testing RECAP Endpoints ===\n")
        
        # Test RECAP base endpoint
        endpoints = [
            ('recap/', 'RECAP Dockets'),
            ('recap-documents/', 'RECAP Documents'),
            ('audio/', 'Audio Recordings'),
            ('docket-entries/', 'Docket Entries'),
        ]
        
        for endpoint, name in endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                response = self.session.get(url, params={'page_size': 1})
                
                if response.status_code == 200:
                    data = response.json()
                    count = data.get('count', 0)
                    print(f"✓ {name}: {count:,} items available")
                    
                    # Show sample fields if available
                    if data.get('results'):
                        item = data['results'][0]
                        print(f"  Sample fields: {', '.join(sorted(item.keys())[:5])}...")
                else:
                    print(f"✗ {name}: Status {response.status_code}")
                    
            except Exception as e:
                print(f"✗ {name}: Error - {e}")
        
        print()
    
    def test_recap_documents_with_transcripts(self):
        """Search for transcript documents"""
        print("=== Searching for Transcripts ===\n")
        
        try:
            # Search for documents with transcript-related descriptions
            params = {
                'description__icontains': 'transcript',
                'page_size': 5,
                'order_by': '-date_created'
            }
            
            response = self.session.get(f"{BASE_URL}recap-documents/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"Found {count:,} documents with 'transcript' in description\n")
                
                # Display sample transcripts
                for doc in data.get('results', []):
                    print(f"Document ID: {doc.get('id')}")
                    print(f"  Description: {doc.get('description')}")
                    print(f"  Document Type: {doc.get('document_type')}")
                    print(f"  Page Count: {doc.get('page_count')}")
                    print(f"  Has Text: {'plain_text' in doc and bool(doc['plain_text'])}")
                    print(f"  Download URL: {doc.get('filepath_local') or 'Not available'}")
                    print()
            else:
                print(f"Search failed with status {response.status_code}")
                
        except Exception as e:
            print(f"Error searching for transcripts: {e}")
    
    def test_docket_with_documents(self, docket_id: int = None):
        """Test retrieving documents for a specific docket"""
        print("=== Testing Docket Document Retrieval ===\n")
        
        try:
            # First, get a sample docket if none provided
            if not docket_id:
                response = self.session.get(
                    f"{BASE_URL}dockets/",
                    params={'court': 'txed', 'page_size': 1}
                )
                
                if response.status_code == 200 and response.json().get('results'):
                    docket_id = response.json()['results'][0]['id']
                    print(f"Using sample docket ID: {docket_id}")
                else:
                    print("Could not retrieve sample docket")
                    return
            
            # Get docket entries
            entries_response = self.session.get(
                f"{BASE_URL}docket-entries/",
                params={'docket': docket_id, 'page_size': 10}
            )
            
            if entries_response.status_code == 200:
                entries_data = entries_response.json()
                print(f"\nDocket has {entries_data.get('count', 0)} entries")
                
                # Check for RECAP documents in entries
                for entry in entries_data.get('results', [])[:3]:
                    print(f"\nEntry #{entry.get('entry_number')}:")
                    print(f"  Description: {entry.get('description')}")
                    
                    # Check if this entry has RECAP documents
                    recap_docs = entry.get('recap_documents', [])
                    if recap_docs:
                        print(f"  RECAP Documents: {len(recap_docs)}")
                        for doc in recap_docs:
                            print(f"    - {doc.get('description')}")
                    else:
                        print("  No RECAP documents linked")
                        
        except Exception as e:
            print(f"Error testing docket documents: {e}")
    
    def test_audio_recordings(self):
        """Test audio recordings endpoint"""
        print("\n=== Testing Audio Recordings ===\n")
        
        try:
            # Get recent audio recordings
            params = {
                'page_size': 5,
                'order_by': '-date_created'
            }
            
            response = self.session.get(f"{BASE_URL}audio/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                print(f"Found {count:,} audio recordings\n")
                
                for audio in data.get('results', []):
                    print(f"Audio ID: {audio.get('id')}")
                    print(f"  Case Name: {audio.get('case_name')}")
                    print(f"  Duration: {audio.get('duration')} seconds")
                    print(f"  Download URL: {audio.get('download_url')}")
                    print()
            else:
                print(f"Failed with status {response.status_code}")
                
        except Exception as e:
            print(f"Error testing audio: {e}")
    
    def identify_transcript_patterns(self):
        """Identify common patterns in transcript descriptions"""
        print("\n=== Analyzing Transcript Patterns ===\n")
        
        transcript_keywords = [
            'transcript', 'hearing', 'proceeding', 'testimony',
            'deposition', 'trial', 'oral argument', 'sentencing',
            'conference', 'status conference', 'motion hearing'
        ]
        
        pattern_counts = {}
        
        for keyword in transcript_keywords:
            try:
                response = self.session.get(
                    f"{BASE_URL}recap-documents/",
                    params={
                        'description__icontains': keyword,
                        'page_size': 1
                    }
                )
                
                if response.status_code == 200:
                    count = response.json().get('count', 0)
                    if count > 0:
                        pattern_counts[keyword] = count
                        
            except:
                pass
        
        # Display results
        print("Document counts by keyword:")
        for keyword, count in sorted(pattern_counts.items(), 
                                   key=lambda x: x[1], reverse=True):
            print(f"  '{keyword}': {count:,} documents")
    
    def run_all_tests(self):
        """Run all RECAP tests"""
        print("=" * 70)
        print("CourtListener RECAP API Test Report")
        print(f"Timestamp: {datetime.now().isoformat()}")
        print("=" * 70)
        print()
        
        self.test_recap_endpoints()
        self.test_recap_documents_with_transcripts()
        self.test_docket_with_documents()
        self.test_audio_recordings()
        self.identify_transcript_patterns()
        
        print("\n" + "=" * 70)
        print("Test complete!")

def main():
    """Main entry point"""
    if not API_TOKEN:
        print("Error: COURTLISTENER_API_TOKEN not set")
        sys.exit(1)
    
    tester = RECAPTester(API_TOKEN)
    tester.run_all_tests()

if __name__ == "__main__":
    main()