#!/usr/bin/env python3
"""
Run court processor orchestrator for Delaware OPINIONS (not dockets)
This should provide documents with actual text content for better pipeline testing
"""

import asyncio
import logging
from datetime import datetime
from court_processor_orchestrator import CourtProcessorOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def run_delaware_opinions():
    """Run ingestion specifically for Delaware court opinions"""
    
    # Configuration for opinions (not RECAP)
    config = {
        'ingestion': {
            'court_ids': ['ded'],  # Delaware district court
            'document_types': ['opinions'],  # Opinions only
            'max_per_court': 20,  # Get 20 opinions
            'lookback_days': 365,  # Look back 1 year for more results
            'nature_of_suit': None,  # Don't filter by nature for opinions
            'search_type': 'o'  # 'o' for opinions (not 'r' for RECAP)
        },
        'processing': {
            'batch_size': 10,
            'extract_pdfs': True,
            'validate_strict': True,
            'enable_judge_lookup': True,
            'enable_citation_validation': True
        },
        'scheduling': {
            'run_daily_at': None,
            'retry_failed': True,
            'max_retries': 3
        }
    }
    
    logger.info("Starting Delaware OPINIONS ingestion")
    logger.info(f"Target court: {config['ingestion']['court_ids']}")
    logger.info(f"Document type: OPINIONS (should have text content)")
    logger.info(f"Looking back: {config['ingestion']['lookback_days']} days")
    
    # Create and run orchestrator
    orchestrator = CourtProcessorOrchestrator(config)
    
    try:
        results = await orchestrator.run_complete_workflow()
        
        logger.info("\n" + "="*60)
        logger.info("DELAWARE OPINIONS INGESTION COMPLETE")
        logger.info("="*60)
        
        if results['success']:
            logger.info(f"✓ Workflow completed successfully")
            logger.info(f"✓ Workflow ID: {results['workflow_id']}")
            
            # Show phase summaries
            for phase_name, phase_results in results['phases'].items():
                logger.info(f"\n{phase_name.upper()} Phase:")
                if phase_name == 'ingestion':
                    logger.info(f"  Documents ingested: {phase_results.get('documents_ingested', 0)}")
                    stats = phase_results.get('statistics', {})
                    if stats:
                        logger.info(f"  Total characters: {stats.get('content', {}).get('total_characters', 0):,}")
                        logger.info(f"  PDFs extracted: {stats.get('processing', {}).get('pdfs_extracted', 0)}")
                elif phase_name == 'processing':
                    logger.info(f"  Documents processed: {phase_results.get('total_processed', 0)}")
                    logger.info(f"  Average completeness: {phase_results.get('average_completeness', 0):.1f}%")
                    logger.info(f"  Average quality: {phase_results.get('average_quality', 0):.1f}%")
                elif phase_name == 'reporting':
                    logger.info(f"  Report saved to: {phase_results.get('report_path', 'N/A')}")
        else:
            logger.error(f"✗ Workflow failed: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        

if __name__ == "__main__":
    asyncio.run(run_delaware_opinions())