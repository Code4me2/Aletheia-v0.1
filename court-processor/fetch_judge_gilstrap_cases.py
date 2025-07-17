#!/usr/bin/env python3
"""
Fetch Judge Gilstrap's cases from the last 3 years using CourtListener API v4
Process them through the complete FLP pipeline with Doctor
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

# Judge Gilstrap info
JUDGE_NAME = "Rodney Gilstrap"
COURT_ID = "txed"  # Eastern District of Texas

def search_judge_gilstrap_cases(start_date, end_date, page=1):
    """Search for Judge Gilstrap's cases in the specified date range"""
    
    # Search for opinions by Judge Gilstrap
    params = {
        'filed_after': start_date,
        'filed_before': end_date,
        'court': COURT_ID,
        'judge_name': JUDGE_NAME,
        'order_by': '-date_filed',
        'page': page
    }
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    try:
        response = requests.get(
            f'{BASE_URL}/opinions/',
            params=params,
            headers=headers,
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

def download_pdf(url, output_path):
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

async def process_gilstrap_case(case_data, pdf_dir):
    """Process a single Judge Gilstrap case through the FLP pipeline"""
    
    # Extract case information
    case_id = case_data.get('id')
    case_name = case_data.get('case_name', 'Unknown')
    docket_number = case_data.get('docket_number', f'GILSTRAP-{case_id}')
    date_filed = case_data.get('date_filed', '')
    
    logger.info(f"Processing: {case_name} ({docket_number})")
    
    # Check if we have a PDF URL
    pdf_url = case_data.get('download_url', '')
    if not pdf_url:
        logger.warning(f"No PDF URL for case {case_id}")
        return None
    
    # Download PDF
    pdf_filename = f"gilstrap_{case_id}_{docket_number.replace('/', '_')}.pdf"
    pdf_path = pdf_dir / pdf_filename
    
    if not download_pdf(pdf_url, pdf_path):
        logger.error(f"Failed to download PDF for {case_name}")
        return None
    
    # Prepare metadata for FLP processing
    metadata = {
        'case_number': docket_number,
        'case_name': case_name,
        'court': COURT_ID,
        'court_full': 'United States District Court for the Eastern District of Texas',
        'judge_name': JUDGE_NAME,
        'date_filed': date_filed,
        'source': 'courtlistener',
        'courtlistener_id': case_id,
        'docket_url': case_data.get('absolute_url', ''),
        'citation_count': case_data.get('citation_count', 0),
        'precedential_status': case_data.get('precedential_status', ''),
        'opinion_type': case_data.get('type', ''),
        'fetched_date': datetime.now().isoformat()
    }
    
    # Process through FLP pipeline (Doctor + Eyecite + Courts-DB + Reporters-DB)
    try:
        result = await process_pdf_file(str(pdf_path), metadata)
        
        if result['success']:
            logger.info(f"✅ Successfully processed {case_name}")
            logger.info(f"   - Text length: {len(result.get('text', ''))}")
            logger.info(f"   - Citations found: {result.get('citation_count', 0)}")
            
            # Clean up PDF after successful processing
            if pdf_path.exists():
                pdf_path.unlink()
                
            return result
        else:
            logger.error(f"❌ Failed to process {case_name}: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        logger.error(f"Processing error for {case_name}: {e}")
        return None

async def fetch_and_process_all_gilstrap_cases():
    """Main function to fetch and process all Judge Gilstrap cases from last 3 years"""
    
    # Create PDF directory
    pdf_dir = Path('/data/pdfs/gilstrap')
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    # Date range: last 3 years
    end_date = datetime.now().date()
    start_date = (datetime.now() - timedelta(days=3*365)).date()
    
    logger.info(f"Fetching Judge Gilstrap cases from {start_date} to {end_date}")
    
    # Statistics
    total_cases = 0
    processed_cases = 0
    failed_cases = 0
    page = 1
    
    while True:
        logger.info(f"Fetching page {page}...")
        
        # Search for cases
        result = search_judge_gilstrap_cases(start_date.isoformat(), end_date.isoformat(), page)
        
        if not result:
            logger.error("Failed to fetch cases")
            break
        
        cases = result.get('results', [])
        if not cases:
            logger.info("No more cases found")
            break
        
        total_cases += len(cases)
        logger.info(f"Found {len(cases)} cases on page {page}")
        
        # Process each case
        for case_data in cases:
            result = await process_gilstrap_case(case_data, pdf_dir)
            
            if result:
                processed_cases += 1
            else:
                failed_cases += 1
            
            # Rate limiting
            await asyncio.sleep(1)
        
        # Check if there are more pages
        if not result.get('next'):
            logger.info("No more pages")
            break
            
        page += 1
        
        # Additional rate limiting between pages
        await asyncio.sleep(2)
    
    # Final statistics
    logger.info("\n" + "="*50)
    logger.info("JUDGE GILSTRAP DATA FETCH COMPLETE")
    logger.info("="*50)
    logger.info(f"Total cases found: {total_cases}")
    logger.info(f"Successfully processed: {processed_cases}")
    logger.info(f"Failed: {failed_cases}")
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info("="*50)
    
    return {
        'total': total_cases,
        'processed': processed_cases,
        'failed': failed_cases
    }

def verify_doctor_service():
    """Verify Doctor service is running"""
    try:
        response = requests.get('http://doctor-judicial:5050/', timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    """Main entry point"""
    
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
    
    # Run the async fetch and process
    asyncio.run(fetch_and_process_all_gilstrap_cases())

if __name__ == "__main__":
    main()