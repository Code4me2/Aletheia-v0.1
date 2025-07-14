#!/usr/bin/env python3
"""
Enhanced Bulk Download Script for CourtListener Data
Includes RECAP documents, transcripts, and audio recordings
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
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
        logging.FileHandler('/data/logs/bulk_download_enhanced.log'),
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

class EnhancedCourtListenerDownloader:
    """Enhanced downloader with RECAP document support"""
    
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
            'recap_documents_downloaded': 0,
            'transcripts_found': 0,
            'audio_downloaded': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
        # Track downloaded items to avoid duplicates
        self.downloaded_dockets: Set[int] = set()
        self.downloaded_entries: Set[int] = set()
    
    def download_court_data(self, court_id: str, court_info: Dict, 
                          lookback_days: int = 730, include_recap: bool = True,
                          transcripts_only: bool = False):
        """Download all data for a specific court"""
        logger.info(f"Starting enhanced download for {court_info['name']} ({court_id})")
        logger.info(f"Options: include_recap={include_recap}, transcripts_only={transcripts_only}")
        
        # Create output directory
        output_dir = f"/data/courtlistener/{court_id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Download dockets
        self._download_dockets(court_id, output_dir, lookback_days)
        
        if include_recap:
            # Download RECAP documents for each docket
            self._download_recap_documents(court_id, output_dir, transcripts_only)
        
        # Download opinions
        if not transcripts_only:
            self._download_opinions(court_id, output_dir, lookback_days)
        
        # Download audio recordings
        self._download_audio_recordings(court_id, output_dir, lookback_days)
        
        logger.info(f"Completed enhanced download for {court_id}")
    
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
                
                # Track docket IDs for RECAP download
                for docket in dockets:
                    self.downloaded_dockets.add(docket['id'])
                
                # Save dockets to file
                filename = f"{output_dir}/dockets_page_{page}.json"
                with open(filename, 'w') as f:
                    json.dump(dockets, f, indent=2)
                
                self.stats['dockets_downloaded'] += len(dockets)
                logger.info(f"Downloaded {len(dockets)} dockets from {court_id} (page {page})")
                
                # Check if there are more pages
                if not data.get('next'):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error downloading dockets page {page}: {e}")
                self.stats['errors'] += 1
                break
    
    def _download_recap_documents(self, court_id: str, output_dir: str,
                                transcripts_only: bool = False):
        """Download RECAP documents for all dockets"""
        logger.info(f"Downloading RECAP documents for {len(self.downloaded_dockets)} dockets")
        
        recap_dir = f"{output_dir}/recap_documents"
        os.makedirs(recap_dir, exist_ok=True)
        
        for docket_id in self.downloaded_dockets:
            try:
                # Get docket entries
                self._download_docket_entries(docket_id, recap_dir, transcripts_only)
                
            except Exception as e:
                logger.error(f"Error downloading RECAP for docket {docket_id}: {e}")
                self.stats['errors'] += 1
    
    def _download_docket_entries(self, docket_id: int, output_dir: str,
                               transcripts_only: bool = False):
        """Download docket entries and their RECAP documents"""
        page = 1
        entries_for_docket = []
        
        while True:
            self.rate_limiter.wait_if_needed()
            
            try:
                params = {
                    'docket': docket_id,
                    'page': page,
                    'page_size': 100
                }
                
                response = self.session.get(f"{BASE_URL}docket-entries/", params=params)
                response.raise_for_status()
                
                data = response.json()
                entries = data.get('results', [])
                
                if not entries:
                    break
                
                for entry in entries:
                    entry_id = entry['id']
                    if entry_id not in self.downloaded_entries:
                        self.downloaded_entries.add(entry_id)
                        
                        # Check if this might be a transcript
                        if self._is_potential_transcript(entry.get('description', '')):
                            entry['potential_transcript'] = True
                            
                        entries_for_docket.append(entry)
                        
                        # Download RECAP documents for this entry
                        self._download_entry_recap_documents(
                            entry_id, 
                            output_dir, 
                            transcripts_only
                        )
                
                # Check for more pages
                if not data.get('next'):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error downloading entries for docket {docket_id}: {e}")
                break
        
        # Save entries if we found any
        if entries_for_docket:
            filename = f"{output_dir}/docket_{docket_id}_entries.json"
            with open(filename, 'w') as f:
                json.dump(entries_for_docket, f, indent=2)
    
    def _download_entry_recap_documents(self, entry_id: int, output_dir: str,
                                      transcripts_only: bool = False):
        """Download RECAP documents for a specific docket entry"""
        self.rate_limiter.wait_if_needed()
        
        try:
            params = {
                'docket_entry': entry_id,
                'page_size': 100
            }
            
            response = self.session.get(f"{BASE_URL}recap-documents/", params=params)
            response.raise_for_status()
            
            data = response.json()
            documents = data.get('results', [])
            
            if documents:
                for doc in documents:
                    # Detect if this is a transcript
                    is_transcript = self._is_transcript_document(doc)
                    doc['is_transcript'] = is_transcript
                    
                    if is_transcript:
                        self.stats['transcripts_found'] += 1
                        doc['transcript_type'] = self._detect_transcript_type(
                            doc.get('description', '')
                        )
                    
                    # Skip non-transcripts if transcripts_only
                    if transcripts_only and not is_transcript:
                        continue
                    
                    self.stats['recap_documents_downloaded'] += 1
                
                # Save documents
                filename = f"{output_dir}/entry_{entry_id}_recap_docs.json"
                with open(filename, 'w') as f:
                    json.dump(documents, f, indent=2)
                
                logger.debug(f"Downloaded {len(documents)} RECAP documents for entry {entry_id}")
                
        except Exception as e:
            logger.error(f"Error downloading RECAP documents for entry {entry_id}: {e}")
    
    def _download_audio_recordings(self, court_id: str, output_dir: str,
                                 lookback_days: int):
        """Download audio recording metadata"""
        logger.info(f"Downloading audio recordings for {court_id}")
        
        audio_dir = f"{output_dir}/audio"
        os.makedirs(audio_dir, exist_ok=True)
        
        date_from = (datetime.now() - timedelta(days=lookback_days)).isoformat()
        page = 1
        
        while True:
            self.rate_limiter.wait_if_needed()
            
            try:
                params = {
                    'court': court_id,
                    'date_created__gte': date_from,
                    'page': page,
                    'page_size': 100
                }
                
                response = self.session.get(f"{BASE_URL}audio/", params=params)
                
                if response.status_code == 404:
                    logger.info(f"No audio recordings available for {court_id}")
                    break
                    
                response.raise_for_status()
                
                data = response.json()
                recordings = data.get('results', [])
                
                if not recordings:
                    break
                
                # Save audio metadata
                filename = f"{audio_dir}/audio_page_{page}.json"
                with open(filename, 'w') as f:
                    json.dump(recordings, f, indent=2)
                
                self.stats['audio_downloaded'] += len(recordings)
                logger.info(f"Downloaded {len(recordings)} audio recordings metadata")
                
                if not data.get('next'):
                    break
                    
                page += 1
                
            except Exception as e:
                logger.error(f"Error downloading audio: {e}")
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
    
    def _is_potential_transcript(self, description: str) -> bool:
        """Quick check if description might indicate a transcript"""
        if not description:
            return False
            
        desc_lower = description.lower()
        transcript_indicators = [
            'transcript', 'hearing', 'proceeding', 'testimony',
            'deposition', 'oral argument'
        ]
        return any(indicator in desc_lower for indicator in transcript_indicators)
    
    def _is_transcript_document(self, document: Dict) -> bool:
        """Determine if a RECAP document is a transcript"""
        description = document.get('description', '').lower()
        
        # Strong indicators
        if 'transcript' in description:
            return True
        
        # Check document type
        doc_type = document.get('document_type', '').lower()
        if doc_type in ['transcript', 'hearing', 'deposition']:
            return True
        
        # Additional indicators
        transcript_keywords = [
            'hearing', 'proceeding', 'testimony', 'deposition',
            'trial', 'oral argument', 'sentencing', 'conference'
        ]
        
        return any(keyword in description for keyword in transcript_keywords)
    
    def _detect_transcript_type(self, description: str) -> str:
        """Detect specific type of transcript"""
        desc_lower = description.lower()
        
        if 'deposition' in desc_lower:
            return 'deposition'
        elif 'trial' in desc_lower:
            return 'trial'
        elif 'hearing' in desc_lower:
            return 'hearing'
        elif 'oral argument' in desc_lower:
            return 'oral_argument'
        elif 'sentencing' in desc_lower:
            return 'sentencing'
        elif 'status conference' in desc_lower:
            return 'status_conference'
        else:
            return 'other'
    
    def run_enhanced_download(self, courts: Optional[List[str]] = None, 
                            lookback_days: int = 730,
                            include_recap: bool = True,
                            transcripts_only: bool = False):
        """Run enhanced bulk download"""
        if courts is None:
            courts = list(TARGET_COURTS.keys())
        
        logger.info(f"Starting enhanced bulk download for {len(courts)} courts")
        logger.info(f"Lookback period: {lookback_days} days")
        logger.info(f"Include RECAP: {include_recap}")
        logger.info(f"Transcripts only: {transcripts_only}")
        
        for court_id in courts:
            if court_id not in TARGET_COURTS:
                logger.warning(f"Unknown court ID: {court_id}")
                continue
            
            court_info = TARGET_COURTS[court_id]
            
            try:
                self.download_court_data(
                    court_id, 
                    court_info, 
                    lookback_days,
                    include_recap,
                    transcripts_only
                )
            except Exception as e:
                logger.error(f"Failed to download data for {court_id}: {e}")
                self.stats['errors'] += 1
        
        # Print summary
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("=" * 70)
        logger.info("ENHANCED BULK DOWNLOAD COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Dockets downloaded: {self.stats['dockets_downloaded']:,}")
        logger.info(f"Opinions downloaded: {self.stats['opinions_downloaded']:,}")
        logger.info(f"RECAP documents downloaded: {self.stats['recap_documents_downloaded']:,}")
        logger.info(f"Transcripts found: {self.stats['transcripts_found']:,}")
        logger.info(f"Audio recordings: {self.stats['audio_downloaded']:,}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        total_items = (self.stats['dockets_downloaded'] + 
                      self.stats['opinions_downloaded'] + 
                      self.stats['recap_documents_downloaded'])
        if duration > 0:
            logger.info(f"Average rate: {total_items / (duration/3600):.1f} items/hour")

def main():
    """Main entry point"""
    if not API_TOKEN:
        logger.error("COURTLISTENER_API_TOKEN not set in environment")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced bulk download with RECAP support')
    parser.add_argument('--courts', nargs='+', help='Court IDs to download (default: all)')
    parser.add_argument('--days', type=int, default=730, help='Lookback days (default: 730)')
    parser.add_argument('--high-priority-only', action='store_true', 
                       help='Only download high priority courts')
    parser.add_argument('--no-recap', action='store_true',
                       help='Skip RECAP document download')
    parser.add_argument('--transcripts-only', action='store_true',
                       help='Only download transcript documents')
    
    args = parser.parse_args()
    
    # Filter courts if needed
    courts_to_download = args.courts
    if args.high_priority_only:
        courts_to_download = [court_id for court_id, info in TARGET_COURTS.items() 
                            if info['priority'] == 'high']
    
    # Create output directory
    os.makedirs('/data/courtlistener', exist_ok=True)
    os.makedirs('/data/logs', exist_ok=True)
    
    # Run enhanced bulk download
    downloader = EnhancedCourtListenerDownloader(API_TOKEN)
    downloader.run_enhanced_download(
        courts_to_download, 
        args.days,
        include_recap=not args.no_recap,
        transcripts_only=args.transcripts_only
    )

if __name__ == "__main__":
    main()