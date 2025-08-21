#!/usr/bin/env python3
"""
Ingest Judge Rodney Gilstrap cases from E.D. Texas (2022-2023)
Using the proper ingestion service that the pipeline expects
"""

import asyncio
import os
import sys
from datetime import datetime

# Add court-processor to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up environment with API key
os.environ['COURTLISTENER_API_KEY'] = os.getenv('COURTLISTENER_API_KEY', 'f751990518aacab953214f2e56ac6ccbff9e2c14')

from services.document_ingestion_service import DocumentIngestionService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def ingest_gilstrap_cases():
    """
    Ingest Judge Gilstrap cases from E.D. Texas for 2022-2023
    """
    
    logger.info(f"\n{'='*80}")
    logger.info(f"INGESTING JUDGE RODNEY GILSTRAP CASES")
    logger.info(f"{'='*80}")
    logger.info(f"Court: Eastern District of Texas (txed)")
    logger.info(f"Date range: 2022-01-01 to 2023-12-31")
    logger.info(f"Focus: Patent cases and opinions by Judge Gilstrap")
    
    async with DocumentIngestionService() as service:
        # First, ingest opinions from 2022
        logger.info("\n" + "="*60)
        logger.info("INGESTING 2022 OPINIONS")
        logger.info("="*60)
        
        results_2022 = await service.ingest_from_courtlistener(
            court_ids=['txed'],
            date_after='2022-01-01',
            document_types=['opinions'],
            max_per_court=50,  # Get a good sample
            nature_of_suit=['830'],  # Patent cases
            use_recap_fallback=True,
            check_recap_first=True
        )
        
        if results_2022['success']:
            logger.info(f"✓ Ingested {results_2022['documents_ingested']} documents from 2022")
        else:
            logger.error(f"Failed to ingest 2022 documents: {results_2022.get('errors')}")
        
        # Then, ingest opinions from 2023
        logger.info("\n" + "="*60)
        logger.info("INGESTING 2023 OPINIONS")
        logger.info("="*60)
        
        results_2023 = await service.ingest_from_courtlistener(
            court_ids=['txed'],
            date_after='2023-01-01',
            document_types=['opinions'],
            max_per_court=50,  # Get a good sample
            nature_of_suit=['830'],  # Patent cases
            use_recap_fallback=True,
            check_recap_first=True
        )
        
        if results_2023['success']:
            logger.info(f"✓ Ingested {results_2023['documents_ingested']} documents from 2023")
        else:
            logger.error(f"Failed to ingest 2023 documents: {results_2023.get('errors')}")
        
        # Combine statistics
        total_ingested = results_2022.get('documents_ingested', 0) + results_2023.get('documents_ingested', 0)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"INGESTION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total documents ingested: {total_ingested}")
        
        if total_ingested > 0:
            # Show combined statistics
            stats_2022 = results_2022.get('statistics', {}).get('processing', {})
            stats_2023 = results_2023.get('statistics', {}).get('processing', {})
            
            total_pdfs = stats_2022.get('pdfs_downloaded', 0) + stats_2023.get('pdfs_downloaded', 0)
            total_extracted = stats_2022.get('pdfs_extracted', 0) + stats_2023.get('pdfs_extracted', 0)
            
            logger.info(f"\nStatistics:")
            logger.info(f"  PDFs downloaded: {total_pdfs}")
            logger.info(f"  PDFs extracted: {total_extracted}")
            logger.info(f"  2022 documents: {results_2022.get('documents_ingested', 0)}")
            logger.info(f"  2023 documents: {results_2023.get('documents_ingested', 0)}")
            
            logger.info("\nNext steps:")
            logger.info("1. Run the pipeline to process documents: python scripts/run_pipeline.py")
            logger.info("2. Search for Gilstrap cases: python scripts/search_gilstrap_specifically.py")
            logger.info("3. Check Haystack indexing at: http://localhost:8500/docs")
        else:
            logger.warning("\nNo documents were ingested. This might be because:")
            logger.warning("- The documents already exist in the database")
            logger.warning("- No patent cases were found for the date range")
            logger.warning("- API rate limits or connection issues")


async def check_gilstrap_in_database():
    """
    Check if we have any Gilstrap cases in the database
    """
    import psycopg2
    import json
    
    conn = psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    
    cursor = conn.cursor()
    
    # Check for Gilstrap in case names or metadata
    cursor.execute("""
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN case_name ILIKE '%gilstrap%' THEN 1 END) as gilstrap_in_name,
               COUNT(CASE WHEN metadata::text ILIKE '%gilstrap%' THEN 1 END) as gilstrap_in_metadata,
               COUNT(CASE WHEN metadata->>'judge' ILIKE '%gilstrap%' THEN 1 END) as gilstrap_as_judge,
               COUNT(CASE WHEN metadata->>'nature_of_suit' = '830' THEN 1 END) as patent_cases
        FROM public.court_documents
        WHERE document_type = 'opinion'
          AND metadata->>'court_id' = 'txed'
    """)
    
    result = cursor.fetchone()
    
    logger.info(f"\n{'='*60}")
    logger.info("DATABASE CHECK")
    logger.info(f"{'='*60}")
    logger.info(f"Total E.D. Texas opinions: {result[0]}")
    logger.info(f"Gilstrap in case name: {result[1]}")
    logger.info(f"Gilstrap in metadata: {result[2]}")
    logger.info(f"Gilstrap as judge: {result[3]}")
    logger.info(f"Patent cases: {result[4]}")
    
    # Get a sample of Gilstrap cases if any exist
    if result[2] > 0:  # If we have Gilstrap in metadata
        cursor.execute("""
            SELECT case_number, case_name, metadata->>'judge', metadata->>'date_filed'
            FROM public.court_documents
            WHERE metadata::text ILIKE '%gilstrap%'
            LIMIT 5
        """)
        
        samples = cursor.fetchall()
        if samples:
            logger.info("\nSample Gilstrap cases:")
            for sample in samples:
                logger.info(f"  - {sample[1]} ({sample[0]})")
                logger.info(f"    Judge: {sample[2]}, Filed: {sample[3]}")
    
    cursor.close()
    conn.close()


async def main():
    """Main entry point"""
    
    # First check what's already in the database
    await check_gilstrap_in_database()
    
    # Then ingest new cases
    await ingest_gilstrap_cases()
    
    # Check again to see what was added
    logger.info("\n" + "="*60)
    logger.info("CHECKING DATABASE AFTER INGESTION")
    await check_gilstrap_in_database()


if __name__ == "__main__":
    asyncio.run(main())