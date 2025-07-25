#!/usr/bin/env python3
"""
Court Processor Orchestrator

This is the main entry point that orchestrates the complete court document
processing workflow with clean separation of concerns.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json
import os

from services.document_ingestion_service import DocumentIngestionService
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection

logger = logging.getLogger(__name__)


class CourtProcessorOrchestrator:
    """
    Orchestrates the complete court document processing workflow
    
    Responsibilities:
    1. Coordinate document ingestion from various sources
    2. Trigger pipeline processing on ingested documents
    3. Monitor progress and handle errors
    4. Generate reports and statistics
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.ingestion_service = None
        self.pipeline = None
        self.stats = {
            'runs': [],
            'total_documents_ingested': 0,
            'total_documents_processed': 0,
            'total_errors': 0
        }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'ingestion': {
                'court_ids': ['txed', 'cafc', 'nysd', 'cand'],  # IP-focused courts
                'document_types': ['opinions'],
                'max_per_court': 100,
                'lookback_days': 7,
                'nature_of_suit': ['820', '830', '835', '840'],  # IP case types
                'search_type': 'r'  # RECAP documents for better coverage
            },
            'processing': {
                'batch_size': 50,
                'extract_pdfs': True,
                'validate_strict': True,
                'enable_judge_lookup': True,
                'enable_citation_validation': True
            },
            'scheduling': {
                'run_daily_at': '02:00',  # 2 AM
                'retry_failed': True,
                'max_retries': 3
            }
        }
    
    async def run_complete_workflow(self) -> Dict[str, Any]:
        """
        Run the complete workflow: ingest → process → report
        
        Returns:
            Workflow execution results
        """
        workflow_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        logger.info(f"\n{'='*80}")
        logger.info(f"STARTING COURT PROCESSOR WORKFLOW: {workflow_id}")
        logger.info(f"{'='*80}")
        
        results = {
            'workflow_id': workflow_id,
            'start_time': datetime.now().isoformat(),
            'phases': {}
        }
        
        try:
            # Phase 1: Document Ingestion
            logger.info("\n[PHASE 1] Document Ingestion")
            logger.info("-" * 60)
            
            ingestion_results = await self._run_ingestion_phase()
            results['phases']['ingestion'] = ingestion_results
            
            if not ingestion_results['success']:
                raise Exception("Ingestion phase failed")
            
            # Phase 2: Document Processing
            logger.info("\n[PHASE 2] Document Processing")
            logger.info("-" * 60)
            
            processing_results = await self._run_processing_phase()
            results['phases']['processing'] = processing_results
            
            # Phase 3: Report Generation
            logger.info("\n[PHASE 3] Report Generation")
            logger.info("-" * 60)
            
            report_results = await self._generate_reports(
                ingestion_results, 
                processing_results
            )
            results['phases']['reporting'] = report_results
            
            # Update statistics
            self._update_statistics(results)
            
            results['success'] = True
            results['end_time'] = datetime.now().isoformat()
            
            logger.info(f"\n{'='*80}")
            logger.info(f"WORKFLOW COMPLETED SUCCESSFULLY")
            logger.info(f"{'='*80}")
            
        except Exception as e:
            logger.error(f"Workflow failed: {e}")
            results['success'] = False
            results['error'] = str(e)
            results['end_time'] = datetime.now().isoformat()
            self.stats['total_errors'] += 1
        
        # Save run results
        self.stats['runs'].append(results)
        self._save_run_history(results)
        
        return results
    
    async def _run_ingestion_phase(self) -> Dict[str, Any]:
        """Run document ingestion phase"""
        
        # Calculate date range
        lookback_days = self.config['ingestion']['lookback_days']
        date_after = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
        
        logger.info(f"Ingesting documents from {date_after} to present")
        logger.info(f"Courts: {', '.join(self.config['ingestion']['court_ids'])}")
        
        async with DocumentIngestionService() as service:
            results = await service.ingest_from_courtlistener(
                court_ids=self.config['ingestion']['court_ids'],
                date_after=date_after,
                document_types=self.config['ingestion']['document_types'],
                max_per_court=self.config['ingestion']['max_per_court'],
                nature_of_suit=self.config['ingestion'].get('nature_of_suit'),
                search_type=self.config['ingestion'].get('search_type')
            )
            
            self.stats['total_documents_ingested'] += results.get('documents_ingested', 0)
            
            # Log summary
            stats = results.get('statistics', {})
            logger.info(f"\nIngestion Summary:")
            logger.info(f"  Documents ingested: {results.get('documents_ingested', 0)}")
            logger.info(f"  PDFs downloaded: {stats.get('processing', {}).get('pdfs_downloaded', 0)}")
            logger.info(f"  PDFs extracted: {stats.get('processing', {}).get('pdfs_extracted', 0)}")
            logger.info(f"  Total characters: {stats.get('content', {}).get('total_characters', 0):,}")
            
            return results
    
    async def _run_processing_phase(self) -> Dict[str, Any]:
        """Run document processing phase through eleven-stage pipeline"""
        
        if not self.pipeline:
            self.pipeline = RobustElevenStagePipeline()
        
        batch_size = self.config['processing']['batch_size']
        total_processed = 0
        all_results = []
        
        # Process in batches
        while True:
            logger.info(f"\nProcessing batch (size: {batch_size})...")
            
            batch_results = await self.pipeline.process_batch(
                limit=batch_size,
                extract_pdfs=self.config['processing']['extract_pdfs'],
                validate_strict=self.config['processing']['validate_strict']
            )
            
            if not batch_results['success']:
                logger.error(f"Batch processing failed: {batch_results.get('error')}")
                break
            
            batch_count = batch_results['statistics']['documents_processed']
            if batch_count == 0:
                logger.info("No more documents to process")
                break
            
            total_processed += batch_count
            all_results.append(batch_results)
            
            # Log batch summary
            logger.info(f"  Processed: {batch_count} documents")
            logger.info(f"  Completeness: {batch_results['verification']['completeness_score']:.1f}%")
            logger.info(f"  Quality: {batch_results['verification']['quality_score']:.1f}%")
            
            # Check if we should continue
            if batch_count < batch_size:
                logger.info("Reached end of available documents")
                break
        
        self.stats['total_documents_processed'] += total_processed
        
        # Aggregate results
        aggregated_results = self._aggregate_processing_results(all_results)
        aggregated_results['total_processed'] = total_processed
        
        return aggregated_results
    
    async def _generate_reports(self, 
                               ingestion_results: Dict[str, Any],
                               processing_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive reports"""
        
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'workflow_summary': {
                'documents_ingested': ingestion_results.get('documents_ingested', 0),
                'documents_processed': processing_results.get('total_processed', 0),
                'overall_completeness': processing_results.get('average_completeness', 0),
                'overall_quality': processing_results.get('average_quality', 0)
            },
            'ingestion_details': ingestion_results.get('statistics', {}),
            'processing_details': processing_results,
            'recommendations': []
        }
        
        # Generate recommendations based on results
        if processing_results.get('average_completeness', 0) < 70:
            report_data['recommendations'].append(
                "Low completeness score - consider reviewing field extraction logic"
            )
        
        if ingestion_results.get('statistics', {}).get('processing', {}).get('extraction_failed', 0) > 0:
            report_data['recommendations'].append(
                f"PDF extraction failed for {ingestion_results['statistics']['processing']['extraction_failed']} documents"
            )
        
        # Save report
        report_file = f"workflow_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path = os.path.join('reports', report_file)
        os.makedirs('reports', exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        logger.info(f"\nReport generated: {report_path}")
        
        # Log summary to console
        logger.info("\nWorkflow Summary:")
        logger.info(f"  Total documents ingested: {report_data['workflow_summary']['documents_ingested']}")
        logger.info(f"  Total documents processed: {report_data['workflow_summary']['documents_processed']}")
        logger.info(f"  Average completeness: {report_data['workflow_summary']['overall_completeness']:.1f}%")
        logger.info(f"  Average quality: {report_data['workflow_summary']['overall_quality']:.1f}%")
        
        if report_data['recommendations']:
            logger.info("\nRecommendations:")
            for rec in report_data['recommendations']:
                logger.info(f"  • {rec}")
        
        return {
            'report_generated': True,
            'report_path': report_path,
            'summary': report_data['workflow_summary']
        }
    
    def _aggregate_processing_results(self, 
                                    batch_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate results from multiple processing batches"""
        
        if not batch_results:
            return {}
        
        total_docs = sum(r['statistics']['documents_processed'] for r in batch_results)
        total_completeness = sum(
            r['verification']['completeness_score'] * r['statistics']['documents_processed'] 
            for r in batch_results
        )
        total_quality = sum(
            r['verification']['quality_score'] * r['statistics']['documents_processed'] 
            for r in batch_results
        )
        
        return {
            'batches_processed': len(batch_results),
            'average_completeness': total_completeness / total_docs if total_docs > 0 else 0,
            'average_quality': total_quality / total_docs if total_docs > 0 else 0,
            'aggregate_statistics': self._merge_statistics([r['statistics'] for r in batch_results])
        }
    
    def _merge_statistics(self, stats_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge statistics from multiple batches"""
        merged = {}
        
        for stats in stats_list:
            for key, value in stats.items():
                if isinstance(value, (int, float)):
                    merged[key] = merged.get(key, 0) + value
                elif isinstance(value, dict):
                    if key not in merged:
                        merged[key] = {}
                    for subkey, subvalue in value.items():
                        if isinstance(subvalue, (int, float)):
                            merged[key][subkey] = merged[key].get(subkey, 0) + subvalue
        
        return merged
    
    def _update_statistics(self, run_results: Dict[str, Any]):
        """Update orchestrator statistics"""
        # Statistics are updated throughout the workflow
        pass
    
    def _save_run_history(self, results: Dict[str, Any]):
        """Save run history for tracking"""
        history_file = 'orchestrator_history.json'
        
        # Load existing history
        history = []
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except:
                pass
        
        # Add current run (keep last 100 runs)
        history.append({
            'workflow_id': results['workflow_id'],
            'start_time': results['start_time'],
            'end_time': results.get('end_time'),
            'success': results.get('success', False),
            'documents_ingested': results.get('phases', {}).get('ingestion', {}).get('documents_ingested', 0),
            'documents_processed': results.get('phases', {}).get('processing', {}).get('total_processed', 0)
        })
        history = history[-100:]  # Keep last 100 runs
        
        # Save updated history
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    
    async def run_daily_batch(self):
        """Run daily batch processing (called by scheduler)"""
        logger.info(f"\nStarting daily batch processing at {datetime.now()}")
        return await self.run_complete_workflow()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get orchestrator statistics"""
        return {
            **self.stats,
            'last_run': self.stats['runs'][-1] if self.stats['runs'] else None,
            'success_rate': sum(1 for r in self.stats['runs'] if r.get('success', False)) / len(self.stats['runs']) * 100 if self.stats['runs'] else 0
        }


async def main():
    """Main entry point for court processor"""
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check for required environment variables
    if not os.getenv('COURTLISTENER_API_KEY'):
        logger.error("COURTLISTENER_API_KEY environment variable not set")
        return
    
    # Create orchestrator with custom config if needed
    config = None
    if os.path.exists('orchestrator_config.json'):
        with open('orchestrator_config.json', 'r') as f:
            config = json.load(f)
            logger.info("Loaded custom configuration")
    
    orchestrator = CourtProcessorOrchestrator(config)
    
    # Run complete workflow
    results = await orchestrator.run_complete_workflow()
    
    # Print final statistics
    stats = orchestrator.get_statistics()
    logger.info(f"\nOrchestrator Statistics:")
    logger.info(f"  Total documents ingested: {stats['total_documents_ingested']}")
    logger.info(f"  Total documents processed: {stats['total_documents_processed']}")
    logger.info(f"  Total errors: {stats['total_errors']}")
    logger.info(f"  Success rate: {stats['success_rate']:.1f}%")


if __name__ == "__main__":
    # Set API key for testing
    os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
    
    asyncio.run(main())