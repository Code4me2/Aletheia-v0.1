#!/usr/bin/env python3
"""
Run the robust pipeline to process court documents
"""
import asyncio
import sys
sys.path.append('/app')

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_robust_pipeline():
    """Run the robust pipeline on court documents"""
    
    print("\n" + "="*80)
    print("RUNNING ROBUST PIPELINE ON COURT DOCUMENTS")
    print("="*80)
    
    pipeline = RobustElevenStagePipeline()
    
    try:
        # Process documents
        results = await pipeline.process_batch(
            limit=30,
            source_table='public.court_documents',
            only_unprocessed=False,
            extract_pdfs=False,
            force_reprocess=True,
            validate_strict=False
        )
        
        if results['success']:
            print("\n✅ PIPELINE COMPLETED SUCCESSFULLY")
            
            # Show results
            stats = results['statistics']
            print("\nProcessing Statistics:")
            print(f"  Documents processed: {stats['documents_processed']}")
            print(f"  Citations extracted: {stats['citations_extracted']}")
            print(f"  Judges enhanced: {stats['judges_enhanced']}")
            print(f"  Courts resolved: {stats['courts_resolved']}")
            print(f"  Keywords extracted: {stats['keywords_extracted']}")
            print(f"  Documents stored: {stats['documents_stored']}")
            
            # Show quality metrics
            quality = results.get('quality_metrics', {})
            if quality:
                print("\nQuality Metrics:")
                print(f"  Average completeness: {quality.get('average_completeness', 0):.1f}%")
                print(f"  Average quality: {quality.get('average_quality', 0):.1f}%")
                print(f"  Documents above 80% quality: {quality.get('documents_above_80_percent', 0)}")
            
            # Show error summary
            error_report = results.get('error_report', {})
            if error_report:
                print(f"\nErrors: {error_report.get('total_errors', 0)}")
                print(f"Warnings: {error_report.get('total_warnings', 0)}")
                
        else:
            print(f"\n❌ Pipeline failed: {results.get('error')}")
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_robust_pipeline())