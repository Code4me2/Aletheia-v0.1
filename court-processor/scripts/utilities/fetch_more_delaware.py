
import asyncio
import logging
from datetime import datetime
from court_processor_orchestrator import CourtProcessorOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_delaware_expanded():
    config = {
        "ingestion": {
            "court_ids": ["ded"],  
            "document_types": ["opinions"],  
            "max_per_court": 50,  # Increase from 20 to 50
            "lookback_days": 730,  # Look back 2 years instead of 1
            "nature_of_suit": None,
            "search_type": "o"
        },
        "processing": {
            "batch_size": 10,
            "extract_pdfs": True,
            "validate_strict": True,
            "enable_judge_lookup": True,
            "enable_citation_validation": True
        }
    }
    
    logger.info(f"Fetching up to {config['ingestion']['max_per_court']} Delaware opinions from last {config['ingestion']['lookback_days']} days")
    
    orchestrator = CourtProcessorOrchestrator(config)
    results = await orchestrator.run_complete_workflow()
    
    if results["success"]:
        logger.info(f"✓ Successfully processed {results['phases']['processing']['total_processed']} documents")
    else:
        logger.error(f"✗ Failed: {results.get('error')}")

asyncio.run(run_delaware_expanded())
