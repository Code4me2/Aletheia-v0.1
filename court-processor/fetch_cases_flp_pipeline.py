#!/usr/bin/env python3
"""
Generalizable script to fetch cases from CourtListener API v4
and process them through the complete FLP pipeline with Doctor

Usage examples:
    # Fetch by judge name
    python fetch_cases_flp_pipeline.py --judge "Rodney Gilstrap" --years 3
    
    # Fetch by court
    python fetch_cases_flp_pipeline.py --court txed --days 30
    
    # Fetch by docket number pattern
    python fetch_cases_flp_pipeline.py --docket "2:21-cv-*" --court txed
    
    # Fetch by case name search
    python fetch_cases_flp_pipeline.py --case-name "Apple" --court cafc --years 2
    
    # Combine multiple filters
    python fetch_cases_flp_pipeline.py --judge "Gilstrap" --court txed --case-name "patent" --years 1
"""
import os
import sys
import time
import json
import logging
import requests
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, timedelta
import asyncio
from pathlib import Path
import argparse

# Add the court-processor directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flp_document_processor import FLPDocumentProcessor, process_pdf_file

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN', '')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'database': os.environ.get('DB_NAME', 'aletheia'),
    'user': os.environ.get('DB_USER', 'aletheia'),
    'password': os.environ.get('DB_PASSWORD', 'aletheia123')
}

class CourtListenerFetcher:
    def __init__(self, api_token):
        self.api_token = api_token
        self.headers = {'Authorization': f'Token {api_token}'}
        self.stats = {
            'total_cases': 0,
            'processed_cases': 0,
            'failed_cases': 0,
            'skipped_cases': 0
        }
    
    def build_search_params(self, args):
        """Build search parameters from command line arguments"""
        params = {
            'order_by': '-date_filed',
            'page': 1
        }
        
        # Date range
        if args.days:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=args.days)
        elif args.years:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=args.years * 365)
        else:
            # Default to last 30 days
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=30)
        
        params['filed_after'] = start_date.isoformat()
        params['filed_before'] = end_date.isoformat()
        
        # Add filters
        if args.judge:
            params['judge_name'] = args.judge
        if args.court:
            params['court'] = args.court
        if args.case_name:
            params['case_name'] = args.case_name
        if args.docket:
            params['docket_number'] = args.docket
        if args.citation:
            params['citation'] = args.citation
        
        # Opinion type filters
        if args.precedential:
            params['precedential_status'] = 'precedential'
        
        return params, start_date, end_date
    
    def search_cases(self, params):
        """Search for cases with given parameters"""
        try:
            response = requests.get(
                f'{BASE_URL}/opinions/',
                params=params,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None
    
    def download_pdf(self, url, output_path):
        """Download PDF from URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (CourtListener FLP Integration)'
            }
            
            response = requests.get(url, headers=headers, timeout=60, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
            else:
                logger.error(f"PDF download failed {response.status_code}: {url}")
                return False
                
        except Exception as e:
            logger.error(f"PDF download error: {e}")
            return False
    
    async def process_case(self, case_data, pdf_dir, skip_existing=True):
        """Process a single case through the FLP pipeline"""
        
        # Extract case information
        case_id = case_data.get('id')
        case_name = case_data.get('case_name', 'Unknown')
        docket_number = case_data.get('docket_number', f'CASE-{case_id}')
        date_filed = case_data.get('date_filed', '')
        
        # Check if already processed
        if skip_existing and self.case_exists_in_db(docket_number):
            logger.info(f"Skipping existing case: {case_name}")
            self.stats['skipped_cases'] += 1
            return None
        
        logger.info(f"Processing: {case_name} ({docket_number})")
        
        # Check if we have a PDF URL
        pdf_url = case_data.get('download_url', '')
        if not pdf_url:
            logger.warning(f"No PDF URL for case {case_id}")
            self.stats['failed_cases'] += 1
            return None
        
        # Download PDF
        safe_docket = docket_number.replace('/', '_').replace(':', '_')
        pdf_filename = f"{case_id}_{safe_docket}.pdf"
        pdf_path = pdf_dir / pdf_filename
        
        if not self.download_pdf(pdf_url, pdf_path):
            logger.error(f"Failed to download PDF for {case_name}")
            self.stats['failed_cases'] += 1
            return None
        
        # Prepare metadata for FLP processing
        metadata = {
            'case_number': docket_number,
            'case_name': case_name,
            'court': case_data.get('court', ''),
            'court_full': case_data.get('court_full_name', ''),
            'judge_name': case_data.get('author_str', ''),
            'date_filed': date_filed,
            'source': 'courtlistener',
            'courtlistener_id': case_id,
            'docket_url': case_data.get('absolute_url', ''),
            'citation_count': case_data.get('citation_count', 0),
            'precedential_status': case_data.get('precedential_status', ''),
            'opinion_type': case_data.get('type', ''),
            'fetched_date': datetime.now().isoformat()
        }
        
        # Process through FLP pipeline
        try:
            result = await process_pdf_file(str(pdf_path), metadata)
            
            if result['success']:
                logger.info(f"✅ Successfully processed {case_name}")
                logger.info(f"   - Text length: {len(result.get('text', ''))}")
                logger.info(f"   - Citations found: {result.get('citation_count', 0)}")
                self.stats['processed_cases'] += 1
                
                # Clean up PDF after successful processing
                if pdf_path.exists():
                    pdf_path.unlink()
                    
                return result
            else:
                logger.error(f"❌ Failed to process {case_name}: {result.get('error', 'Unknown error')}")
                self.stats['failed_cases'] += 1
                return None
                
        except Exception as e:
            logger.error(f"Processing error for {case_name}: {e}")
            self.stats['failed_cases'] += 1
            return None
    
    def case_exists_in_db(self, case_number):
        """Check if case already exists in database"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM court_documents WHERE case_number = %s LIMIT 1",
                (case_number,)
            )
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Database check error: {e}")
            return False
    
    async def fetch_and_process_all(self, args):
        """Main function to fetch and process all cases matching criteria"""
        
        # Create PDF directory
        pdf_subdir = f"fetch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pdf_dir = Path(f'/data/pdfs/{pdf_subdir}')
        pdf_dir.mkdir(parents=True, exist_ok=True)
        
        # Build search parameters
        params, start_date, end_date = self.build_search_params(args)
        
        logger.info(f"Search parameters: {json.dumps(params, indent=2)}")
        logger.info(f"Date range: {start_date} to {end_date}")
        
        page = 1
        params['page'] = page
        
        while True:
            logger.info(f"Fetching page {page}...")
            
            # Search for cases
            result = self.search_cases(params)
            
            if not result:
                logger.error("Failed to fetch cases")
                break
            
            cases = result.get('results', [])
            if not cases:
                logger.info("No more cases found")
                break
            
            self.stats['total_cases'] += len(cases)
            logger.info(f"Found {len(cases)} cases on page {page}")
            
            # Process each case
            for case_data in cases:
                await self.process_case(case_data, pdf_dir, args.skip_existing)
                
                # Rate limiting
                await asyncio.sleep(args.delay)
            
            # Check if there are more pages
            if not result.get('next') or (args.max_pages and page >= args.max_pages):
                logger.info("Stopping: reached page limit or no more pages")
                break
                
            page += 1
            params['page'] = page
            
            # Additional rate limiting between pages
            await asyncio.sleep(args.delay * 2)
        
        # Print final statistics
        self.print_statistics()
        
        return self.stats
    
    def print_statistics(self):
        """Print final statistics"""
        logger.info("\n" + "="*60)
        logger.info("COURTLISTENER FLP PIPELINE FETCH COMPLETE")
        logger.info("="*60)
        logger.info(f"Total cases found: {self.stats['total_cases']}")
        logger.info(f"Successfully processed: {self.stats['processed_cases']}")
        logger.info(f"Failed: {self.stats['failed_cases']}")
        logger.info(f"Skipped (already exists): {self.stats['skipped_cases']}")
        logger.info("="*60)

def verify_doctor_service():
    """Verify Doctor service is running"""
    try:
        response = requests.get('http://doctor-judicial:5050/', timeout=2)
        return response.status_code == 200
    except:
        return False

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Fetch cases from CourtListener and process through FLP pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch Judge Gilstrap's cases from last 3 years
  %(prog)s --judge "Rodney Gilstrap" --court txed --years 3
  
  # Fetch recent patent cases from CAFC
  %(prog)s --court cafc --case-name "patent" --days 30
  
  # Fetch all cases from a specific court in last month
  %(prog)s --court txed --days 30
  
  # Fetch with specific docket pattern
  %(prog)s --docket "2:21-cv-*" --court txed --years 1
        """
    )
    
    # Search filters
    parser.add_argument('--judge', help='Judge name to search for')
    parser.add_argument('--court', help='Court ID (e.g., txed, cafc, scotus)')
    parser.add_argument('--case-name', help='Case name search term')
    parser.add_argument('--docket', help='Docket number pattern')
    parser.add_argument('--citation', help='Citation to search for')
    parser.add_argument('--precedential', action='store_true', 
                       help='Only precedential opinions')
    
    # Date range
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument('--days', type=int, help='Number of days back to search')
    date_group.add_argument('--years', type=int, help='Number of years back to search')
    
    # Processing options
    parser.add_argument('--max-pages', type=int, help='Maximum number of pages to fetch')
    parser.add_argument('--delay', type=float, default=1.0, 
                       help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--skip-existing', action='store_true', default=True,
                       help='Skip cases that already exist in database (default: True)')
    parser.add_argument('--no-skip-existing', dest='skip_existing', action='store_false',
                       help='Re-process existing cases')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_arguments()
    
    # Check for API token
    if not API_TOKEN:
        logger.error("COURTLISTENER_API_TOKEN environment variable not set!")
        logger.info("Please set: export COURTLISTENER_API_TOKEN='your-token-here'")
        sys.exit(1)
    
    # Verify Doctor service
    if not verify_doctor_service():
        logger.warning("Doctor service not available - will use fallback PDF processing")
        logger.info("For best results, start Doctor: docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d doctor")
    else:
        logger.info("✅ Doctor service is running")
    
    # Create fetcher and run
    fetcher = CourtListenerFetcher(API_TOKEN)
    asyncio.run(fetcher.fetch_and_process_all(args))

if __name__ == "__main__":
    main()