#!/usr/bin/env python3
"""
Search for RECAP documents (dockets) across multiple IP courts
These should have more results than opinions
"""

import asyncio
import logging
from datetime import datetime
from court_processor_orchestrator import CourtProcessorOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_recap_broad_search():
    """Search for RECAP dockets across major IP courts"""
    
    # Focus on district courts that handle lots of IP cases
    ip_courts = {
        'txed': 'E.D. Texas',
        'txwd': 'W.D. Texas', 
        'ded': 'D. Delaware',
        'cand': 'N.D. California',
        'nysd': 'S.D. New York',
        'ilnd': 'N.D. Illinois'
    }
    
    config = {
        'ingestion': {
            'court_ids': list(ip_courts.keys()),
            'document_types': ['opinions'],  # Keep as opinions but search type 'r'
            'max_per_court': 20,  # More per court
            'lookback_days': 30,  # Last month
            'nature_of_suit': ['830'],  # Just patents for focused results
            'search_type': 'r'  # RECAP documents
        },
        'processing': {
            'batch_size': 30,
            'extract_pdfs': False,  # No PDFs for dockets
            'validate_strict': False,  # Less strict for metadata
            'enable_judge_lookup': True,
            'enable_citation_validation': True
        }
    }
    
    logger.info("=" * 80)
    logger.info("RECAP BROAD SEARCH - IP DOCKETS")
    logger.info("=" * 80)
    logger.info(f"Searching for patent cases (nature of suit 830)")
    logger.info(f"Courts: {', '.join(ip_courts.keys())}")
    logger.info(f"Document type: RECAP dockets")
    logger.info(f"Time range: Last 30 days")
    
    orchestrator = CourtProcessorOrchestrator(config)
    
    try:
        results = await orchestrator.run_complete_workflow()
        
        if results['success']:
            logger.info("\n✓ Search completed successfully")
            
            # Extract court distribution if available
            ingestion = results['phases'].get('ingestion', {})
            if ingestion.get('documents_ingested', 0) > 0:
                logger.info(f"\nDocuments found: {ingestion['documents_ingested']}")
                
                # Try to get court breakdown from processing
                processing = results['phases'].get('processing', {})
                if processing.get('aggregate_statistics'):
                    stats = processing['aggregate_statistics']
                    logger.info(f"Courts resolved: {stats.get('courts_resolved', 0)}")
                    logger.info(f"Judges identified: {stats.get('judges_enhanced', 0)}")
                    
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    asyncio.run(run_recap_broad_search())