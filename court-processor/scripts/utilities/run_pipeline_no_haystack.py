#!/usr/bin/env python3
"""
Run pipeline without Haystack integration to avoid timeouts
"""
import asyncio
import sys
sys.path.append('/app')

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_pipeline_no_haystack():
    """Run pipeline but skip Haystack integration"""
    
    print("\n" + "="*80)
    print("RUNNING PIPELINE (WITHOUT HAYSTACK)")
    print("="*80)
    
    # Monkey patch to skip Haystack
    original_process = RobustElevenStagePipeline.process_batch
    
    async def process_batch_no_haystack(self, **kwargs):
        """Process batch but skip Haystack"""
        # Store original method
        original_haystack = self._index_to_haystack_validated
        
        # Replace with no-op
        async def no_haystack(docs):
            logger.info("Skipping Haystack integration")
            return True
        
        self._index_to_haystack_validated = no_haystack
        
        try:
            # Run normal processing
            result = await original_process(self, **kwargs)
            return result
        finally:
            # Restore original
            self._index_to_haystack_validated = original_haystack
    
    # Apply patch
    RobustElevenStagePipeline.process_batch = process_batch_no_haystack
    
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
            print(f"  Documents validated: {stats['documents_validated']}")
            print(f"  Citations extracted: {stats['citations_extracted']}")
            print(f"  Judges enhanced: {stats['judges_enhanced']}")
            print(f"  Courts resolved: {stats['courts_resolved']}")
            print(f"  Documents stored: {stats['documents_stored']}")
            
            # Analyze dockets vs opinions
            analyze_results()
            
        else:
            print(f"\n❌ Pipeline failed: {results.get('error')}")
            
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        import traceback
        traceback.print_exc()


def analyze_results():
    """Analyze the processing results"""
    print("\n" + "-"*60)
    print("ANALYZING RESULTS")
    print("-"*60)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check what was processed
    cursor.execute("""
        SELECT 
            cd.document_type,
            COUNT(*) as count,
            COUNT(CASE WHEN ou.citations IS NOT NULL AND ou.citations != '[]' THEN 1 END) as has_citations,
            COUNT(CASE WHEN ou.judge_info IS NOT NULL AND ou.judge_info != '{}' THEN 1 END) as has_judge,
            AVG(LENGTH(cd.content)) as avg_content_length
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id::text = ou.cl_id
        WHERE cd.updated_at > NOW() - INTERVAL '5 minutes'
        GROUP BY cd.document_type
        ORDER BY count DESC
    """)
    
    print("\nProcessing Results by Document Type:")
    print(f"{'Type':<15} {'Count':<8} {'Citations':<12} {'Judges':<10} {'Avg Content'}")
    print("-" * 60)
    
    for row in cursor.fetchall():
        doc_type, count, has_cites, has_judge, avg_content = row
        print(f"{doc_type:<15} {count:<8} {has_cites:<12} {has_judge:<10} {int(avg_content):,}")
    
    # Check dockets specifically
    cursor.execute("""
        SELECT 
            cd.case_number,
            cd.metadata->>'assigned_to' as metadata_judge,
            ou.judge_info->>'judge_name' as extracted_judge
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id::text = ou.cl_id
        WHERE cd.document_type IN ('docket', 'recap_docket')
        AND cd.updated_at > NOW() - INTERVAL '5 minutes'
        LIMIT 5
    """)
    
    print("\nDocket Judge Extraction Examples:")
    docket_examples = cursor.fetchall()
    for case, meta_judge, extracted in docket_examples:
        print(f"\n{case}:")
        print(f"  Judge in metadata: {meta_judge}")
        print(f"  Judge extracted: {extracted}")
        if meta_judge and not extracted:
            print(f"  ❌ MISSED: Judge was in metadata but not extracted")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    asyncio.run(run_pipeline_no_haystack())