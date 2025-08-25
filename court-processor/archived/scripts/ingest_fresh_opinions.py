#!/usr/bin/env python3
"""
Simple script to ingest fresh court opinions from CourtListener
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta

# Add court-processor to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from services.document_ingestion_service import DocumentIngestionService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_recent_opinions(court_id: str = 'txed', days_back: int = 30):
    """
    Ingest recent opinions from a specific court
    
    Args:
        court_id: Court identifier (default: txed - Eastern District of Texas)
        days_back: Number of days to look back (default: 30)
    """
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_back)
    date_after = start_date.strftime('%Y-%m-%d')
    
    logger.info(f"\n{'='*60}")
    logger.info(f"INGESTING FRESH OPINIONS FROM {court_id.upper()}")
    logger.info(f"{'='*60}")
    logger.info(f"Date range: {date_after} to today")
    logger.info(f"Court: {court_id}")
    
    async with DocumentIngestionService() as service:
        # Directly ingest opinions
        logger.info("\nIngesting opinions from CourtListener...")
        results = await service.ingest_from_courtlistener(
            court_ids=[court_id],
            date_after=date_after,
            document_types=['opinions'],
            max_per_court=20,  # Limit for testing
            # Remove nature_of_suit filter to get all cases
            use_recap_fallback=False,
            check_recap_first=False
        )
        
        if results['success']:
            logger.info(f"\n✓ Successfully ingested {results['documents_ingested']} documents")
            
            # Show statistics
            stats = results['statistics']
            logger.info("\nIngestion Statistics:")
            logger.info(f"  Total documents processed: {stats['processing']['total_documents']}")
            logger.info(f"  PDFs downloaded: {stats['processing']['pdfs_downloaded']}")
            logger.info(f"  PDFs extracted: {stats['processing']['pdfs_extracted']}")
            logger.info(f"  Documents stored: {stats['storage']['documents_stored']}")
            logger.info(f"  Documents updated: {stats['storage']['documents_updated']}")
            logger.info(f"  Total text characters: {stats['content']['total_characters']:,}")
            
            # Show summary
            if 'summary' in stats:
                logger.info("\nSummary:")
                logger.info(f"  PDF extraction rate: {stats['summary']['pdf_extraction_rate']:.1f}%")
                logger.info(f"  Storage success rate: {stats['summary']['storage_success_rate']:.1f}%")
                logger.info(f"  Average document size: {stats['summary']['average_document_size']:.0f} chars")
        else:
            logger.error(f"Ingestion failed: {results.get('errors', 'Unknown error')}")


async def main():
    """Main entry point"""
    
    # Parse command line arguments
    court_id = 'txed'  # Default to Eastern District of Texas
    days_back = 30     # Default to last 30 days
    
    if len(sys.argv) > 1:
        court_id = sys.argv[1]
    if len(sys.argv) > 2:
        days_back = int(sys.argv[2])
    
    # Run ingestion
    await ingest_recent_opinions(court_id, days_back)
    
    logger.info("\nIngestion complete!")
    logger.info("Documents are now available in PostgreSQL and ready for processing.")
    logger.info("To process them through the pipeline, run: python run_pipeline.py")


if __name__ == "__main__":
    asyncio.run(main())