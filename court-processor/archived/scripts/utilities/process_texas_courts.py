#!/usr/bin/env python3
"""
Process East Texas court documents specifically
"""
import asyncio
import sys
sys.path.append('/app')

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection

async def process_texas_courts():
    """Process E.D. Texas documents with the pipeline"""
    
    # First, let's analyze what we have
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get E.D. Texas documents that need processing
    cursor.execute("""
        SELECT 
            id,
            metadata->>'court' as court,
            metadata->>'court_id' as court_id,
            metadata->>'cl_id' as cl_id
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
        LIMIT 5
    """)
    
    print("Sample E.D. Texas document metadata:")
    print("-" * 80)
    for row in cursor.fetchall():
        doc_id, court, court_id, cl_id = row
        print(f"ID: {doc_id}, Court: {court}, Court_ID: {court_id}, CL_ID: {cl_id}")
    
    cursor.close()
    conn.close()
    
    # Now run the pipeline
    print("\n" + "="*80)
    print("Running pipeline on E.D. Texas documents...")
    print("="*80 + "\n")
    
    pipeline = RobustElevenStagePipeline()
    
    # Modify the pipeline query to focus on E.D. Texas
    original_query = pipeline.retrieval_query
    pipeline.retrieval_query = """
        SELECT 
            COALESCE(metadata->>'cl_id', id::text) as cl_id,
            case_number,
            case_name,
            document_type,
            content,
            metadata,
            id,
            created_at,
            updated_at
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
        ORDER BY created_at DESC
        LIMIT %s
    """
    
    # Process documents
    results = await pipeline.process_batch(limit=20, validate_strict=False)
    
    # Restore original query
    pipeline.retrieval_query = original_query
    
    # Analyze results
    if results['success']:
        print("\n" + "="*80)
        print("E.D. TEXAS PROCESSING RESULTS")
        print("="*80)
        
        stats = results['statistics']
        print(f"\nDocuments processed: {stats['documents_processed']}")
        print(f"Courts resolved: {stats['courts_resolved']}")
        print(f"Citations extracted: {stats['citations_extracted']}")
        print(f"Judges identified: {stats['judges_enhanced'] + stats['judges_extracted_from_content']}")
        
        # Document type breakdown
        if 'document_type_statistics' in results:
            print("\nDocument Type Distribution:")
            for doc_type, info in results['document_type_statistics'].items():
                print(f"  {doc_type}: {info['count']} ({info['percentage']:.1f}%)")
        
        # Quality metrics
        quality = results['quality_metrics']
        print(f"\nQuality Metrics:")
        print(f"  Court resolution rate: {quality['court_resolution_rate']:.1f}%")
        print(f"  Total citations extracted: {quality.get('total_citations_extracted', 0)}")
        print(f"  Judge identification rate: {quality['judge_identification_rate']:.1f}%")
        
        # Errors and warnings
        if 'errors' in results and results['errors']:
            print(f"\nErrors encountered: {len(results['errors'])}")
            for i, error in enumerate(results['errors'][:5]):
                print(f"  {i+1}. {error}")
                
        if 'warnings' in results and results['warnings']:
            print(f"\nWarnings: {len(results['warnings'])}")
            for i, warning in enumerate(results['warnings'][:5]):
                print(f"  {i+1}. {warning}")
    
    return results

if __name__ == "__main__":
    asyncio.run(process_texas_courts())