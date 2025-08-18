#!/usr/bin/env python3
"""
Fetch Delaware court documents using the enhanced pipeline
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
import os
import sys
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.courtlistener_service import CourtListenerService
from services.document_ingestion_service import DocumentIngestionService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def fetch_delaware_documents():
    """Fetch documents from Delaware courts"""
    
    # Delaware courts in the system
    delaware_courts = {
        'ded': 'District of Delaware',  # Main federal district court
        'debankr': 'Bankruptcy Court for the District of Delaware'
    }
    
    # IP-related nature of suit codes
    ip_nature_codes = ['820', '830', '835', '840']  # Patent, Trademark, etc.
    
    results = {
        'search_date': datetime.now().isoformat(),
        'courts': {},
        'total_documents': 0,
        'ip_documents': 0
    }
    
    # Initialize services
    cl_service = CourtListenerService()
    ingestion_service = DocumentIngestionService()
    
    for court_id, court_name in delaware_courts.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Searching {court_name} ({court_id})")
        logger.info(f"{'='*60}")
        
        court_results = {
            'court_name': court_name,
            'documents': [],
            'total': 0,
            'ip_related': 0
        }
        
        try:
            # Search for recent opinions from this court
            search_params = {
                'court': court_id,
                'type': 'r',  # RECAP documents (better coverage)
                'order_by': '-date_filed',
                'filed_after': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            }
            
            logger.info(f"Searching with params: {search_params}")
            
            opinions = await cl_service.search_opinions(**search_params)
            
            if opinions and 'results' in opinions:
                logger.info(f"Found {opinions['count']} total documents")
                
                # Process first 10 documents
                for i, doc in enumerate(opinions['results'][:10]):
                    doc_info = {
                        'id': doc.get('id'),
                        'case_name': doc.get('case_name'),
                        'docket_number': doc.get('docket_number'),
                        'date_filed': doc.get('date_filed'),
                        'court': doc.get('court'),
                        'nature_of_suit': doc.get('nature_of_suit', ''),
                        'judge': doc.get('judge_full_name', ''),
                        'has_pdf': bool(doc.get('filepath_local')),
                        'text_length': len(doc.get('text', '') or ''),
                        'citation': doc.get('citation', [])
                    }
                    
                    # Check if IP-related
                    if doc_info['nature_of_suit'] in ip_nature_codes:
                        doc_info['is_ip_case'] = True
                        court_results['ip_related'] += 1
                    else:
                        doc_info['is_ip_case'] = False
                    
                    court_results['documents'].append(doc_info)
                    court_results['total'] += 1
                    
                    # Log document details
                    logger.info(f"\nDocument {i+1}:")
                    logger.info(f"  Case: {doc_info['case_name']}")
                    logger.info(f"  Docket: {doc_info['docket_number']}")
                    logger.info(f"  Date: {doc_info['date_filed']}")
                    logger.info(f"  Judge: {doc_info['judge']}")
                    logger.info(f"  Nature of Suit: {doc_info['nature_of_suit']}")
                    logger.info(f"  Has PDF: {doc_info['has_pdf']}")
                    logger.info(f"  Text Length: {doc_info['text_length']} chars")
                    if doc_info['is_ip_case']:
                        logger.info(f"  ** IP-RELATED CASE **")
                
                # Now search specifically for IP cases
                logger.info(f"\nSearching specifically for IP cases...")
                ip_search_params = {
                    **search_params,
                    'nature_of_suit': ip_nature_codes
                }
                
                ip_opinions = await cl_service.search_opinions(**ip_search_params)
                
                if ip_opinions and 'results' in ip_opinions:
                    logger.info(f"Found {ip_opinions['count']} IP-related documents")
                    court_results['ip_search_count'] = ip_opinions['count']
                
            else:
                logger.warning(f"No documents found for {court_name}")
            
        except Exception as e:
            logger.error(f"Error searching {court_name}: {e}")
            court_results['error'] = str(e)
        
        results['courts'][court_id] = court_results
        results['total_documents'] += court_results['total']
        results['ip_documents'] += court_results['ip_related']
    
    # Save results
    output_file = f"delaware_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info("SUMMARY")
    logger.info(f"{'='*60}")
    logger.info(f"Total courts searched: {len(delaware_courts)}")
    logger.info(f"Total documents found: {results['total_documents']}")
    logger.info(f"IP-related documents: {results['ip_documents']}")
    logger.info(f"Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    asyncio.run(fetch_delaware_documents())