#!/usr/bin/env python3
"""
Broad IP court ingestion - test pipeline with multiple courts
Targets the top IP venues in the US
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


async def run_broad_ip_ingestion():
    """Run ingestion across major IP courts"""
    
    # Top IP courts in order of case volume
    ip_courts = {
        'txed': 'Eastern District of Texas (patent hotspot)',
        'ded': 'District of Delaware (corporate/patent hub)',
        'cafc': 'Court of Appeals Federal Circuit (patent appeals)',
        'cand': 'Northern District of California (tech sector)',
        'nysd': 'Southern District of New York (trademark/copyright)',
        'ilnd': 'Northern District of Illinois (diverse IP)',
        'njd': 'District of New Jersey (pharma patents)',
        'vaed': 'Eastern District of Virginia (rocket docket)',
        'txwd': 'Western District of Texas (new patent venue)',
        'flsd': 'Southern District of Florida (trademark disputes)'
    }
    
    # Configuration for broad search
    config = {
        'ingestion': {
            'court_ids': list(ip_courts.keys()),  # All courts
            'document_types': ['opinions'],  # Focus on opinions for best results
            'max_per_court': 10,  # 10 per court = up to 100 documents
            'lookback_days': 180,  # Last 6 months for broader coverage
            'nature_of_suit': ['820', '830', '835', '840'],  # All IP types
            'search_type': 'o'  # Opinions
        },
        'processing': {
            'batch_size': 20,
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
    
    logger.info("=" * 80)
    logger.info("BROAD IP COURT INGESTION TEST")
    logger.info("=" * 80)
    logger.info(f"Target courts: {len(ip_courts)} major IP venues")
    logger.info(f"Document types: Opinions (full text)")
    logger.info(f"Time range: Last {config['ingestion']['lookback_days']} days")
    logger.info(f"Max documents: {len(ip_courts) * config['ingestion']['max_per_court']}")
    logger.info(f"Nature of suit codes: {', '.join(config['ingestion']['nature_of_suit'])}")
    logger.info("  820: Copyright")
    logger.info("  830: Patent")
    logger.info("  835: Patent (Drug)")
    logger.info("  840: Trademark")
    logger.info("")
    logger.info("Courts being searched:")
    for court_id, description in ip_courts.items():
        logger.info(f"  {court_id}: {description}")
    
    # Create and run orchestrator
    orchestrator = CourtProcessorOrchestrator(config)
    
    try:
        results = await orchestrator.run_complete_workflow()
        
        logger.info("\n" + "="*60)
        logger.info("BROAD INGESTION COMPLETE")
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
                    
                    # Check if we have court breakdown
                    if 'aggregate_statistics' in phase_results:
                        agg_stats = phase_results['aggregate_statistics']
                        logger.info(f"  Courts resolved: {agg_stats.get('courts_resolved', 0)}")
                        logger.info(f"  Citations extracted: {agg_stats.get('citations_extracted', 0)}")
                        logger.info(f"  Keywords found: {agg_stats.get('keywords_extracted', 0)}")
                        
                elif phase_name == 'reporting':
                    logger.info(f"  Report saved to: {phase_results.get('report_path', 'N/A')}")
                    
            # Summary analysis
            logger.info("\n" + "="*60)
            logger.info("ANALYSIS SUMMARY")
            logger.info("="*60)
            
            if results['phases'].get('ingestion', {}).get('documents_ingested', 0) > 0:
                docs_per_court = results['phases']['ingestion']['documents_ingested'] / len(ip_courts)
                logger.info(f"Average documents per court: {docs_per_court:.1f}")
                
                # Calculate success metrics
                if results['phases'].get('processing'):
                    completeness = results['phases']['processing'].get('average_completeness', 0)
                    quality = results['phases']['processing'].get('average_quality', 0)
                    
                    logger.info(f"\nPipeline Performance:")
                    logger.info(f"  Overall completeness: {completeness:.1f}%")
                    logger.info(f"  Overall quality: {quality:.1f}%")
                    
                    if completeness > 70:
                        logger.info("  ✅ Excellent completeness - pipeline working well across courts")
                    elif completeness > 50:
                        logger.info("  ⚠️ Good completeness - some courts may have limited data")
                    else:
                        logger.info("  ❌ Low completeness - check document types")
                        
        else:
            logger.error(f"✗ Workflow failed: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        

if __name__ == "__main__":
    asyncio.run(run_broad_ip_ingestion())