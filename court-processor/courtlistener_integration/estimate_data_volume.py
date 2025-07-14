#!/usr/bin/env python3
"""
Estimate data volume for CourtListener download
Checks document counts and sizes before bulk download
"""

import os
import sys
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

# Target courts
TARGET_COURTS = {
    'ded': 'District of Delaware',
    'txed': 'Eastern District of Texas',
    'cand': 'Northern District of California',
    'cafc': 'Court of Appeals for the Federal Circuit',
    'cacd': 'Central District of California',
    'nysd': 'Southern District of New York'
}

class DataVolumeEstimator:
    """Estimate data volume before downloading"""
    
    def __init__(self, api_token: str):
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
        self.estimates = {}
    
    def estimate_court_data(self, court_id: str, court_name: str, days: int = 90):
        """Estimate data volume for a single court"""
        print(f"\nAnalyzing {court_name} ({court_id})...")
        
        date_from = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        court_data = {
            'dockets': {'count': 0, 'size_mb': 0},
            'opinions': {'count': 0, 'size_mb': 0},
            'recap_documents': {'count': 0, 'size_mb': 0, 'transcripts': 0},
            'audio': {'count': 0, 'size_mb': 0},
            'total_api_calls': 0
        }
        
        # Estimate dockets
        try:
            response = self.session.get(f"{BASE_URL}dockets/", params={
                'court': court_id,
                'date_filed__gte': date_from,
                'page_size': 1
            })
            if response.status_code == 200:
                court_data['dockets']['count'] = response.json().get('count', 0)
                # Estimate ~5KB per docket JSON
                court_data['dockets']['size_mb'] = (court_data['dockets']['count'] * 5) / 1024
                # API calls needed (100 per page)
                court_data['total_api_calls'] += (court_data['dockets']['count'] // 100) + 1
        except Exception as e:
            print(f"  Error checking dockets: {e}")
        
        # Estimate opinions
        try:
            response = self.session.get(f"{BASE_URL}opinions/", params={
                'cluster__docket__court': court_id,
                'date_created__gte': date_from + 'T00:00:00Z',
                'page_size': 1
            })
            if response.status_code == 200:
                court_data['opinions']['count'] = response.json().get('count', 0)
                # Estimate ~50KB per opinion (includes text)
                court_data['opinions']['size_mb'] = (court_data['opinions']['count'] * 50) / 1024
                court_data['total_api_calls'] += (court_data['opinions']['count'] // 100) + 1
        except Exception as e:
            print(f"  Error checking opinions: {e}")
        
        # Estimate RECAP documents (this is the big one)
        # We'll sample a few dockets to estimate
        try:
            # Get sample of recent dockets
            response = self.session.get(f"{BASE_URL}dockets/", params={
                'court': court_id,
                'date_filed__gte': date_from,
                'page_size': 10,
                'order_by': '-date_filed'
            })
            
            if response.status_code == 200:
                sample_dockets = response.json().get('results', [])
                
                if sample_dockets:
                    # Sample docket entries from first few dockets
                    total_entries = 0
                    total_docs = 0
                    transcript_count = 0
                    
                    for docket in sample_dockets[:3]:  # Sample first 3
                        # Get entries for this docket
                        entries_resp = self.session.get(f"{BASE_URL}docket-entries/", params={
                            'docket': docket['id'],
                            'page_size': 100
                        })
                        
                        if entries_resp.status_code == 200:
                            entries_data = entries_resp.json()
                            entries_count = entries_data.get('count', 0)
                            total_entries += entries_count
                            
                            # Sample RECAP documents from first few entries
                            for entry in entries_data.get('results', [])[:5]:
                                docs_resp = self.session.get(f"{BASE_URL}recap-documents/", params={
                                    'docket_entry': entry['id'],
                                    'page_size': 10
                                })
                                
                                if docs_resp.status_code == 200:
                                    docs = docs_resp.json().get('results', [])
                                    total_docs += len(docs)
                                    
                                    # Check for transcripts
                                    for doc in docs:
                                        desc = doc.get('description', '').lower()
                                        if 'transcript' in desc:
                                            transcript_count += 1
                    
                    # Extrapolate based on sample
                    if len(sample_dockets) > 0:
                        avg_entries_per_docket = total_entries / min(3, len(sample_dockets))
                        avg_docs_per_docket = total_docs / min(3, len(sample_dockets))
                        
                        estimated_total_entries = int(court_data['dockets']['count'] * avg_entries_per_docket)
                        estimated_total_docs = int(court_data['dockets']['count'] * avg_docs_per_docket)
                        estimated_transcripts = int(transcript_count * court_data['dockets']['count'] / min(3, len(sample_dockets)))
                        
                        court_data['recap_documents']['count'] = estimated_total_docs
                        court_data['recap_documents']['transcripts'] = estimated_transcripts
                        # Estimate ~10KB per document metadata, ~100KB if has text
                        court_data['recap_documents']['size_mb'] = (estimated_total_docs * 30) / 1024
                        
                        # API calls for entries and documents
                        court_data['total_api_calls'] += estimated_total_entries // 100
                        court_data['total_api_calls'] += estimated_total_docs // 100
                        
        except Exception as e:
            print(f"  Error estimating RECAP documents: {e}")
        
        # Estimate audio
        try:
            response = self.session.get(f"{BASE_URL}audio/", params={
                'court': court_id,
                'date_created__gte': date_from + 'T00:00:00Z',
                'page_size': 1
            })
            if response.status_code == 200:
                court_data['audio']['count'] = response.json().get('count', 0)
                # Audio metadata only, ~2KB each
                court_data['audio']['size_mb'] = (court_data['audio']['count'] * 2) / 1024
                court_data['total_api_calls'] += (court_data['audio']['count'] // 100) + 1
        except Exception as e:
            # Audio might not be available for all courts
            pass
        
        self.estimates[court_id] = court_data
        return court_data
    
    def print_summary(self, days: int):
        """Print summary of estimates"""
        print("\n" + "=" * 80)
        print(f"DATA VOLUME ESTIMATE - Last {days} Days")
        print("=" * 80)
        
        total_size = 0
        total_docs = 0
        total_api_calls = 0
        total_transcripts = 0
        
        for court_id, data in self.estimates.items():
            court_name = TARGET_COURTS[court_id]
            court_total_mb = (data['dockets']['size_mb'] + 
                            data['opinions']['size_mb'] + 
                            data['recap_documents']['size_mb'] + 
                            data['audio']['size_mb'])
            
            print(f"\n{court_name} ({court_id}):")
            print(f"  Dockets: {data['dockets']['count']:,}")
            print(f"  Opinions: {data['opinions']['count']:,}")
            print(f"  RECAP Documents: {data['recap_documents']['count']:,}")
            print(f"  - Estimated Transcripts: {data['recap_documents']['transcripts']:,}")
            print(f"  Audio Recordings: {data['audio']['count']:,}")
            print(f"  Estimated JSON Size: {court_total_mb:.1f} MB")
            print(f"  API Calls Required: ~{data['total_api_calls']:,}")
            
            total_size += court_total_mb
            total_docs += (data['dockets']['count'] + 
                         data['opinions']['count'] + 
                         data['recap_documents']['count'])
            total_api_calls += data['total_api_calls']
            total_transcripts += data['recap_documents']['transcripts']
        
        print("\n" + "-" * 80)
        print("TOTALS:")
        print(f"  Total Documents: {total_docs:,}")
        print(f"  Estimated Transcripts: {total_transcripts:,}")
        print(f"  Total JSON Size: {total_size:.1f} MB")
        print(f"  Total API Calls: ~{total_api_calls:,}")
        print(f"  Time at Rate Limit: ~{total_api_calls / 4500:.1f} hours")
        
        print("\n" + "=" * 80)
        print("IMPORTANT NOTES:")
        print("=" * 80)
        print("1. This estimates JSON metadata size only")
        print("2. Actual PDFs/documents are NOT included (would be 100-1000x larger)")
        print("3. Only documents with existing text extraction are useful without PDFs")
        print("4. Transcript detection is based on small sample - actual count may vary")
        print("5. Rate limit: 4,500 requests/hour with authentication")
        
        # Storage recommendations
        print("\n" + "-" * 80)
        print("STORAGE RECOMMENDATIONS:")
        print(f"- JSON metadata: ~{total_size * 1.5:.0f} MB (with overhead)")
        print(f"- PostgreSQL storage: ~{total_size * 2:.0f} MB (with indexes)")
        print(f"- If downloading PDFs: 50-500 GB (not recommended initially)")
        
        # Time estimate
        hours_needed = total_api_calls / 4500
        if hours_needed < 1:
            print(f"\nDownload time: ~{hours_needed * 60:.0f} minutes")
        else:
            print(f"\nDownload time: ~{hours_needed:.1f} hours")
            if hours_needed > 24:
                print(f"  ({hours_needed / 24:.1f} days with continuous running)")
    
    def save_estimate(self, filename: str = "data_estimate.json"):
        """Save detailed estimates to file"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'courts': self.estimates,
            'summary': {
                'total_documents': sum(
                    d['dockets']['count'] + d['opinions']['count'] + d['recap_documents']['count']
                    for d in self.estimates.values()
                ),
                'total_size_mb': sum(
                    d['dockets']['size_mb'] + d['opinions']['size_mb'] + 
                    d['recap_documents']['size_mb'] + d['audio']['size_mb']
                    for d in self.estimates.values()
                ),
                'total_api_calls': sum(d['total_api_calls'] for d in self.estimates.values()),
                'estimated_transcripts': sum(d['recap_documents']['transcripts'] for d in self.estimates.values())
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\nDetailed estimate saved to: {filename}")

def main():
    """Main entry point"""
    if not API_TOKEN:
        print("Error: COURTLISTENER_API_TOKEN not set")
        sys.exit(1)
    
    import argparse
    parser = argparse.ArgumentParser(description='Estimate CourtListener data volume')
    parser.add_argument('--days', type=int, default=90, help='Number of days to analyze (default: 90)')
    parser.add_argument('--courts', nargs='+', help='Specific courts to analyze (default: all)')
    parser.add_argument('--save', action='store_true', help='Save detailed estimate to file')
    
    args = parser.parse_args()
    
    estimator = DataVolumeEstimator(API_TOKEN)
    
    # Determine which courts to analyze
    courts_to_analyze = args.courts if args.courts else list(TARGET_COURTS.keys())
    
    print(f"Estimating data volume for the last {args.days} days...")
    print(f"Courts: {', '.join(courts_to_analyze)}")
    print("\nThis may take a few minutes due to API sampling...")
    
    # Analyze each court
    for court_id in courts_to_analyze:
        if court_id in TARGET_COURTS:
            estimator.estimate_court_data(court_id, TARGET_COURTS[court_id], args.days)
        else:
            print(f"Warning: Unknown court ID: {court_id}")
    
    # Print summary
    estimator.print_summary(args.days)
    
    # Save if requested
    if args.save:
        estimator.save_estimate()

if __name__ == "__main__":
    main()