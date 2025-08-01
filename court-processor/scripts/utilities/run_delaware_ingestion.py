#!/usr/bin/env python3
"""
Run court processor orchestrator specifically for Delaware courts
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


async def run_delaware_ingestion():
    """Run ingestion specifically for Delaware courts"""
    
    # Custom configuration for Delaware
    config = {
        'ingestion': {
            'court_ids': ['ded', 'debankr'],  # Delaware district and bankruptcy courts
            'document_types': ['opinions'],
            'max_per_court': 50,
            'lookback_days': 30,  # Last 30 days
            'nature_of_suit': ['820', '830', '835', '840'],  # IP case types
            'search_type': 'r'  # RECAP documents
        },
        'processing': {
            'batch_size': 20,
            'extract_pdfs': True,
            'validate_strict': True,
            'enable_judge_lookup': True,
            'enable_citation_validation': True
        },
        'scheduling': {
            'run_daily_at': None,  # One-time run
            'retry_failed': True,
            'max_retries': 3
        }
    }
    
    logger.info("Starting Delaware court document ingestion")
    logger.info(f"Target courts: {config['ingestion']['court_ids']}")
    logger.info(f"Looking for IP cases (nature of suit: {config['ingestion']['nature_of_suit']})")
    
    # Create and run orchestrator
    orchestrator = CourtProcessorOrchestrator(config)
    
    try:
        results = await orchestrator.run_complete_workflow()
        
        logger.info("\n" + "="*60)
        logger.info("DELAWARE INGESTION COMPLETE")
        logger.info("="*60)
        
        if results['success']:
            logger.info(f"✓ Workflow completed successfully")
            logger.info(f"✓ Workflow ID: {results['workflow_id']}")
            
            # Show phase summaries
            for phase_name, phase_results in results['phases'].items():
                logger.info(f"\n{phase_name.upper()} Phase:")
                if phase_name == 'ingestion':
                    logger.info(f"  Documents ingested: {phase_results.get('documents_ingested', 0)}")
                elif phase_name == 'processing':
                    logger.info(f"  Documents processed: {phase_results.get('total_processed', 0)}")
                    logger.info(f"  Average completeness: {phase_results.get('average_completeness', 0):.1f}%")
                elif phase_name == 'reporting':
                    logger.info(f"  Report saved to: {phase_results.get('report_path', 'N/A')}")
        else:
            logger.error(f"✗ Workflow failed: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        

if __name__ == "__main__":
    asyncio.run(run_delaware_ingestion())