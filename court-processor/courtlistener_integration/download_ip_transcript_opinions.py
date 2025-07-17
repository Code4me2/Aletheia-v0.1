#!/usr/bin/env python3
"""
Download and process opinions mentioning transcripts from IP courts
Stores results in PostgreSQL database
"""
import os
import sys
import json
import time
import logging
import requests
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Configuration
API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')
BASE_URL = "https://www.courtlistener.com/api/rest/v4/"

# Target IP courts
IP_COURTS = {
    'txed': 'Eastern District of Texas',
    'deld': 'District of Delaware', 
    'cand': 'Northern District of California',
    'cafc': 'Court of Appeals for the Federal Circuit',
    'ilnd': 'Northern District of Illinois',
    'nysd': 'Southern District of New York'
}

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TranscriptOpinionDownloader:
    """Download opinions mentioning transcripts from IP courts"""
    
    def __init__(self, api_token: str, db_url: str):
        self.api_token = api_token
        self.db_url = db_url
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Token {api_token}',
            'User-Agent': 'Aletheia-v0.1/1.0'
        })
        self.stats = {
            'total_downloaded': 0,
            'transcripts_found': 0,
            'errors': 0,
            'start_time': datetime.now()
        }
        
    def setup_database(self):
        """Create database tables if they don't exist"""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Create schema if not exists
            cur.execute("CREATE SCHEMA IF NOT EXISTS court_data")
            
            # Create table for transcript opinions
            cur.execute("""
                CREATE TABLE IF NOT EXISTS court_data.transcript_opinions (
                    id SERIAL PRIMARY KEY,
                    cl_id VARCHAR(50) UNIQUE NOT NULL,
                    case_name TEXT,
                    court VARCHAR(20),
                    court_name TEXT,
                    date_filed DATE,
                    docket_number TEXT,
                    citation TEXT,
                    author_str TEXT,
                    type VARCHAR(50),
                    source VARCHAR(20) DEFAULT 'courtlistener',
                    
                    -- Full text content
                    plain_text TEXT,
                    html_text TEXT,
                    
                    -- Transcript references
                    transcript_mentions INTEGER DEFAULT 0,
                    transcript_quotes JSONB,
                    has_deposition BOOLEAN DEFAULT FALSE,
                    has_trial_transcript BOOLEAN DEFAULT FALSE,
                    has_hearing_transcript BOOLEAN DEFAULT FALSE,
                    
                    -- Metadata
                    nature_of_suit VARCHAR(10),
                    is_ip_case BOOLEAN DEFAULT FALSE,
                    download_url TEXT,
                    api_url TEXT,
                    
                    -- Timestamps
                    date_created TIMESTAMP DEFAULT NOW(),
                    date_modified TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Create indexes
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transcript_opinions_court 
                ON court_data.transcript_opinions(court);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transcript_opinions_date 
                ON court_data.transcript_opinions(date_filed);
            """)
            
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_transcript_opinions_transcript_mentions 
                ON court_data.transcript_opinions(transcript_mentions) 
                WHERE transcript_mentions > 0;
            """)
            
            conn.commit()
            logger.info("Database tables created/verified")
            
        except Exception as e:
            logger.error(f"Database setup error: {e}")
            conn.rollback()
            raise
        finally:
            cur.close()
            conn.close()
    
    def extract_transcript_quotes(self, text: str) -> Dict:
        """Extract transcript quotes and references from opinion text"""
        if not text:
            return {
                'count': 0,
                'quotes': [],
                'has_deposition': False,
                'has_trial': False,
                'has_hearing': False
            }
        
        text_lower = text.lower()
        
        # Count mentions
        transcript_count = len(re.findall(r'\btranscript\b', text_lower))
        
        # Check transcript types
        has_deposition = 'deposition' in text_lower and 'transcript' in text_lower
        has_trial = 'trial transcript' in text_lower
        has_hearing = 'hearing transcript' in text_lower
        
        # Extract quotes around transcript mentions
        quotes = []
        
        # Find sentences containing "transcript"
        sentences = re.split(r'[.!?]\s+', text)
        for sentence in sentences:
            if 'transcript' in sentence.lower():
                # Clean up the sentence
                clean_sentence = ' '.join(sentence.split())
                if len(clean_sentence) > 50:  # Only include substantial quotes
                    quotes.append({
                        'text': clean_sentence[:500],  # Limit length
                        'type': self._classify_transcript_type(clean_sentence)
                    })
        
        # Also look for common transcript citation patterns
        # E.g., "Tr. at 123", "Trial Tr. 45:10-15"
        tr_citations = re.findall(r'(?:Trial\s+)?Tr\.?\s+(?:at\s+)?\d+(?::\d+)?(?:-\d+)?', text)
        for citation in tr_citations[:10]:  # Limit citations
            quotes.append({
                'text': citation,
                'type': 'citation'
            })
        
        return {
            'count': transcript_count,
            'quotes': quotes[:20],  # Limit total quotes
            'has_deposition': has_deposition,
            'has_trial': has_trial,
            'has_hearing': has_hearing
        }
    
    def _classify_transcript_type(self, text: str) -> str:
        """Classify the type of transcript reference"""
        text_lower = text.lower()
        
        if 'deposition' in text_lower:
            return 'deposition'
        elif 'trial' in text_lower:
            return 'trial'
        elif 'hearing' in text_lower:
            return 'hearing'
        elif 'oral argument' in text_lower:
            return 'oral_argument'
        elif 'testimony' in text_lower:
            return 'testimony'
        else:
            return 'general'
    
    def search_court_transcripts(self, court: str, max_results: int = 200) -> List[Dict]:
        """Search for opinions mentioning transcripts in a specific court"""
        results = []
        page = 1
        
        # Search queries to find transcript mentions
        queries = [
            f'transcript AND court:{court}',
            f'"trial transcript" AND court:{court}',
            f'"deposition transcript" AND court:{court}',
            f'"hearing transcript" AND court:{court}'
        ]
        
        for query in queries:
            logger.info(f"Searching: {query}")
            
            while len(results) < max_results:
                try:
                    response = self.session.get(
                        f"{BASE_URL}search/",
                        params={
                            'q': query,
                            'type': 'o',  # opinions
                            'order_by': 'dateFiled desc',
                            'page_size': 20,
                            'page': page
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if not data.get('results'):
                            break
                        
                        # Process each result
                        for result in data['results']:
                            # Skip if we already have this opinion
                            if any(r.get('id') == result.get('id') for r in results):
                                continue
                                
                            # Add court name
                            result['court_name'] = IP_COURTS.get(court, court)
                            results.append(result)
                            
                        page += 1
                        
                        # Rate limiting
                        time.sleep(0.5)
                        
                        # Stop if no more pages
                        if not data.get('next'):
                            break
                            
                    else:
                        logger.error(f"Search error: {response.status_code}")
                        break
                        
                except Exception as e:
                    logger.error(f"Error searching {court}: {e}")
                    self.stats['errors'] += 1
                    break
            
            # Reset page for next query
            page = 1
            
            # Don't overwhelm with one query type
            if len(results) >= max_results:
                break
        
        return results[:max_results]
    
    def fetch_opinion_details(self, opinion_id: str) -> Optional[Dict]:
        """Fetch full opinion details"""
        try:
            # Extract numeric ID from URL if needed
            if '/' in str(opinion_id):
                opinion_id = opinion_id.rstrip('/').split('/')[-1]
            
            url = f"{BASE_URL}opinions/{opinion_id}/"
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch opinion {opinion_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching opinion {opinion_id}: {e}")
            return None
    
    def save_to_database(self, opinion_data: Dict, transcript_info: Dict):
        """Save opinion and transcript information to database"""
        conn = psycopg2.connect(self.db_url)
        cur = conn.cursor()
        
        try:
            # Prepare data
            cl_id = str(opinion_data.get('id', '')).rstrip('/').split('/')[-1]
            
            # Determine if it's an IP case
            case_name = opinion_data.get('caseName', '').lower()
            is_ip_case = any(term in case_name for term in ['patent', 'trademark', 'copyright', 'infringement'])
            
            # Insert or update
            cur.execute("""
                INSERT INTO court_data.transcript_opinions (
                    cl_id, case_name, court, court_name, date_filed,
                    docket_number, citation, author_str, type,
                    plain_text, html_text,
                    transcript_mentions, transcript_quotes,
                    has_deposition, has_trial_transcript, has_hearing_transcript,
                    nature_of_suit, is_ip_case, 
                    download_url, api_url
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s
                )
                ON CONFLICT (cl_id) DO UPDATE SET
                    plain_text = EXCLUDED.plain_text,
                    html_text = EXCLUDED.html_text,
                    transcript_mentions = EXCLUDED.transcript_mentions,
                    transcript_quotes = EXCLUDED.transcript_quotes,
                    has_deposition = EXCLUDED.has_deposition,
                    has_trial_transcript = EXCLUDED.has_trial_transcript,
                    has_hearing_transcript = EXCLUDED.has_hearing_transcript,
                    date_modified = NOW()
            """, (
                cl_id,
                opinion_data.get('caseName'),
                opinion_data.get('court'),
                opinion_data.get('court_name'),
                opinion_data.get('dateFiled'),
                opinion_data.get('docketNumber'),
                opinion_data.get('citation'),
                opinion_data.get('author_str'),
                opinion_data.get('type'),
                opinion_data.get('plain_text'),
                opinion_data.get('html'),
                transcript_info['count'],
                Json(transcript_info['quotes']),
                transcript_info['has_deposition'],
                transcript_info['has_trial'],
                transcript_info['has_hearing'],
                opinion_data.get('suitNature'),
                is_ip_case,
                opinion_data.get('download_url'),
                opinion_data.get('absolute_url')
            ))
            
            conn.commit()
            self.stats['total_downloaded'] += 1
            
            if transcript_info['count'] > 0:
                self.stats['transcripts_found'] += 1
                
        except Exception as e:
            logger.error(f"Database save error: {e}")
            conn.rollback()
            self.stats['errors'] += 1
        finally:
            cur.close()
            conn.close()
    
    def download_all_courts(self, target_count: int = 1000):
        """Download opinions from all IP courts"""
        logger.info(f"Starting download of {target_count} opinions from IP courts")
        
        # Setup database
        self.setup_database()
        
        # Calculate per-court target
        per_court = target_count // len(IP_COURTS) + 1
        
        for court_id, court_name in IP_COURTS.items():
            logger.info(f"\nProcessing {court_name} ({court_id})")
            
            # Search for opinions
            results = self.search_court_transcripts(court_id, per_court)
            logger.info(f"Found {len(results)} results for {court_id}")
            
            # Process each result
            for i, result in enumerate(results):
                if i % 10 == 0:
                    logger.info(f"Processing {court_id} opinion {i+1}/{len(results)}")
                
                # Get opinion ID
                opinion_id = result.get('id')
                if not opinion_id:
                    continue
                
                # Fetch full opinion details
                opinion_details = self.fetch_opinion_details(opinion_id)
                if not opinion_details:
                    continue
                
                # Merge search result with details
                opinion_data = {**result, **opinion_details}
                
                # Extract transcript information
                plain_text = opinion_data.get('plain_text', '')
                transcript_info = self.extract_transcript_quotes(plain_text)
                
                # Save to database
                self.save_to_database(opinion_data, transcript_info)
                
                # Rate limiting
                time.sleep(0.2)
            
            logger.info(f"Completed {court_id}: {self.stats['total_downloaded']} total downloaded")
        
        # Print final stats
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        logger.info("\n" + "="*70)
        logger.info("DOWNLOAD COMPLETE")
        logger.info("="*70)
        logger.info(f"Total opinions downloaded: {self.stats['total_downloaded']}")
        logger.info(f"Opinions with transcripts: {self.stats['transcripts_found']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info(f"Duration: {duration/60:.1f} minutes")
        logger.info(f"Rate: {self.stats['total_downloaded']/(duration/3600):.1f} opinions/hour")

def main():
    """Main entry point"""
    if not API_TOKEN:
        logger.error("COURTLISTENER_API_TOKEN not set")
        sys.exit(1)
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Download transcript opinions from IP courts')
    parser.add_argument('--count', type=int, default=1000, 
                       help='Number of opinions to download (default: 1000)')
    parser.add_argument('--court', help='Specific court to download (default: all IP courts)')
    
    args = parser.parse_args()
    
    # Run downloader
    downloader = TranscriptOpinionDownloader(API_TOKEN, DATABASE_URL)
    
    if args.court:
        # Download from specific court
        logger.info(f"Downloading from {args.court}")
        results = downloader.search_court_transcripts(args.court, args.count)
        # Process results...
    else:
        # Download from all courts
        downloader.download_all_courts(args.count)

if __name__ == "__main__":
    main()