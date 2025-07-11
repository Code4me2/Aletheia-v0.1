#!/usr/bin/env python3
"""
Bulk Download Script for CourtListener Data
Downloads court data for specified courts with rate limiting
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

# Target courts for bulk download
TARGET_COURTS = {
    'ded': {'name': 'District of Delaware', 'priority': 'high'},
    'txed': {'name': 'Eastern District of Texas', 'priority': 'high'},
    'cand': {'name': 'Northern District of California', 'priority': 'high'},
    'cafc': {'name': 'Court of Appeals for the Federal Circuit', 'priority': 'high'},
    'cacd': {'name': 'Central District of California', 'priority': 'medium'},
    'nysd': {'name': 'Southern District of New York', 'priority': 'medium'}
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/data/logs/bulk_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter to stay within API limits"""
    
    def __init__(self, requests_per_hour: int = 4500):
        self.requests_per_hour = requests_per_hour
        self.request_times = []
        
    def wait_if_needed(self):
        """Wait if we're approaching rate limit"""
        now = time.time()
        # Remove requests older than 1 hour
        self.request_times = [t for t in self.request_times if now - t < 3600]
        
        if len(self.request_times) >= self.requests_per_hour:
            # Wait until the oldest request is 1 hour old
            sleep_time = 3600 - (now - self.request_times[0]) + 1
            logger.info(f"Rate limit reached. Sleeping for {sleep_time:.1f} seconds...")
            time.sleep(sleep_time)
            self.request_times = []
        
        self.request_times.append(now)

class CourtListenerBulkDownloader:
    """Bulk downloader for CourtListener data"""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
        self.rate_limiter = RateLimiter()
        self.stats = {
            'dockets_downloaded': 0,
            'opinions_downloaded': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
    
    def download_court_data(self, court_id: str, court_info: Dict, 
                          lookback_days: int = 730):
        """Download all data for a specific court"""
        logger.info(f"Starting download for {court_info['name']} ({court_id})")
        
        # Create output directory
        output_dir = f"/data/courtlistener/{court_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Download dockets
        self._download_dockets(court_id, output_dir, lookback_days)
        
        # Download opinions
        self._download_opinions(court_id, output_dir, lookback_days)
        
        logger.info(f"Completed download for {court_id}")
    
    def _download_dockets(self, court_id: str, output_dir: str, 
                         lookback_days: int):
        """Download dockets for a court"""
        date_from = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        page = 1
        while True:
            self.rate_limiter.wait_if_needed()
            
            try:
                params = {
                    'court': court_id,
                    'date_filed__gte': date_from,
                    'order_by': '-date_filed',
                    'page': page,
                    'page_size': 100
                }
                
                response = self.session.get(f"{BASE_URL}dockets/", params=params)
                response.raise_for_status()
                
                data = response.json()
                dockets = data.get('results', [])
                
                if not dockets:
                    break
                
                # Save dockets to file
                filename = f"{output_dir}/dockets_page_{page}.json"
                with open(filename, 'w') as f:
                    json.dump(dockets, f, indent=2)
                
                self.stats['dockets_downloaded'] += len(dockets)
                logger.info(f"Downloaded {len(dockets)} dockets from {court_id} (page {page})")
                
                # Check for patent cases and download details
                for docket in dockets:
                    if self._is_patent_case(docket):
                        self._download_docket_details(docket['id'], output_dir)
                
                # Check if there are more pages
                if not data.get('next'):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error downloading dockets page {page}: {e}")
                self.stats['errors'] += 1
                break
    
    def _download_opinions(self, court_id: str, output_dir: str, 
                          lookback_days: int):
        """Download opinions for a court"""
        date_from = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        
        page = 1
        while True:
            self.rate_limiter.wait_if_needed()
            
            try:
                params = {
                    'cluster__docket__court': court_id,
                    'date_created__gte': date_from,
                    'order_by': '-date_created',
                    'page': page,
                    'page_size': 100
                }
                
                response = self.session.get(f"{BASE_URL}opinions/", params=params)
                response.raise_for_status()
                
                data = response.json()
                opinions = data.get('results', [])
                
                if not opinions:
                    break
                
                # Save opinions to file
                filename = f"{output_dir}/opinions_page_{page}.json"
                with open(filename, 'w') as f:
                    json.dump(opinions, f, indent=2)
                
                self.stats['opinions_downloaded'] += len(opinions)
                logger.info(f"Downloaded {len(opinions)} opinions from {court_id} (page {page})")
                
                # Check if there are more pages
                if not data.get('next'):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error downloading opinions page {page}: {e}")
                self.stats['errors'] += 1
                break
    
    def _download_docket_details(self, docket_id: int, output_dir: str):
        """Download detailed information for a specific docket"""
        self.rate_limiter.wait_if_needed()
        
        try:
            # Get docket entries
            response = self.session.get(f"{BASE_URL}docket-entries/", 
                                      params={'docket': docket_id})
            
            if response.status_code == 200:
                entries = response.json().get('results', [])
                
                # Save docket details
                details_dir = f"{output_dir}/docket_details"
                os.makedirs(details_dir, exist_ok=True)
                
                filename = f"{details_dir}/docket_{docket_id}_entries.json"
                with open(filename, 'w') as f:
                    json.dump(entries, f, indent=2)
                
                logger.debug(f"Downloaded {len(entries)} entries for docket {docket_id}")
                
        except Exception as e:
            logger.error(f"Error downloading docket details {docket_id}: {e}")
    
    def _is_patent_case(self, docket: Dict) -> bool:
        """Check if a docket is a patent case"""
        # Nature of suit codes for patent cases
        patent_nos_codes = ['830', '835', '840']
        nos = str(docket.get('nature_of_suit', ''))
        
        # Also check case name
        case_name = docket.get('case_name', '').lower()
        patent_keywords = ['patent', 'infringement', '35 u.s.c.']
        
        return (nos in patent_nos_codes or 
                any(keyword in case_name for keyword in patent_keywords))
    
    def run_bulk_download(self, courts: Optional[List[str]] = None, 
                         lookback_days: int = 730):
        """Run bulk download for specified courts"""
        if courts is None:
            courts = list(TARGET_COURTS.keys())
        
        logger.info(f"Starting bulk download for {len(courts)} courts")
        logger.info(f"Lookback period: {lookback_days} days")
        
        for court_id in courts:
            if court_id not in TARGET_COURTS:
                logger.warning(f"Unknown court ID: {court_id}")
                continue
            
            court_info = TARGET_COURTS[court_id]
            
            try:
                self.download_court_data(court_id, court_info, lookback_days)
            except Exception as e:
                logger.error(f"Failed to download data for {court_id}: {e}")
                self.stats['errors'] += 1
        
        # Print summary
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("=" * 70)
        logger.info("BULK DOWNLOAD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Dockets downloaded: {self.stats['dockets_downloaded']:,}")
        logger.info(f"Opinions downloaded: {self.stats['opinions_downloaded']:,}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Average rate: {(self.stats['dockets_downloaded'] + self.stats['opinions_downloaded']) / (duration/3600):.1f} items/hour")

def main():
    """Main entry point"""
    if not API_TOKEN:
        logger.error("COURTLISTENER_API_TOKEN not set in environment")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Bulk download CourtListener data')
    parser.add_argument('--courts', nargs='+', help='Court IDs to download (default: all)')
    parser.add_argument('--days', type=int, default=730, help='Lookback days (default: 730)')
    parser.add_argument('--high-priority-only', action='store_true', 
                       help='Only download high priority courts')
    
    args = parser.parse_args()
    
    # Filter courts if needed
    courts_to_download = args.courts
    if args.high_priority_only:
        courts_to_download = [court_id for court_id, info in TARGET_COURTS.items() 
                            if info['priority'] == 'high']
    
    # Create output directory
    os.makedirs('/data/courtlistener', exist_ok=True)
    
    # Run bulk download
    downloader = CourtListenerBulkDownloader(API_TOKEN)
    downloader.run_bulk_download(courts_to_download, args.days)

if __name__ == "__main__":
    main()