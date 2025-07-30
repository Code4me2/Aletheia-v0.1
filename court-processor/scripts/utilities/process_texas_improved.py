#!/usr/bin/env python3
"""
Process Texas courts with improved handling for missing cl_id
"""
import asyncio
import sys
sys.path.append('/app')

from services.database import get_db_connection
import json
from datetime import datetime

async def process_texas_documents():
    """Process Texas documents with special handling"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First, fix the cl_id issue for Texas documents
    print("Fixing cl_id for Texas documents...")
    cursor.execute("""
        UPDATE public.court_documents
        SET metadata = jsonb_set(
            metadata, 
            '{cl_id}', 
            to_jsonb(id::text)
        )
        WHERE metadata::text LIKE '%txed%'
        AND (metadata->>'cl_id' IS NULL OR metadata->>'cl_id' = '')
    """)
    
    updated_count = cursor.rowcount
    conn.commit()
    print(f"Updated {updated_count} Texas documents with cl_id")
    
    # Check IP cases specifically
    cursor.execute("""
        SELECT 
            id,
            case_number,
            document_type,
            metadata->>'assigned_to' as judge,
            metadata->>'nature_of_suit' as nos,
            LENGTH(COALESCE(content, '')) as content_length
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
        AND metadata->>'nature_of_suit' = '830 Patent'
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    print("\n\nE.D. Texas Patent Cases:")
    print("-" * 80)
    print(f"{'ID':<6} {'Case':<20} {'Type':<12} {'Judge':<25} {'Content':<10}")
    print("-" * 80)
    
    for row in cursor.fetchall():
        doc_id, case_num, doc_type, judge, nos, content_len = row
        print(f"{doc_id:<6} {case_num[:20]:<20} {doc_type:<12} {(judge or 'N/A')[:25]:<25} {content_len:<10}")
    
    cursor.close()
    conn.close()
    
    # Now run the pipeline
    print("\n\nRunning pipeline on Texas documents...")
    print("=" * 80)
    
    # Import and run pipeline
    from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
    
    pipeline = RobustElevenStagePipeline()
    
    # Process Texas documents
    results = await pipeline.process_batch(
        limit=30,
        validate_strict=False,
        force_reprocess=True
    )
    
    if results['success']:
        print("\n\nPipeline Results for Recent Documents:")
        print("=" * 80)
        
        # Check if any Texas documents were processed
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                metadata->>'court_id' as court,
                COUNT(*) as count,
                COUNT(CASE WHEN metadata->>'judge_name' IS NOT NULL THEN 1 END) as has_judge,
                COUNT(CASE WHEN metadata->>'citations_extracted' IS NOT NULL THEN 1 END) as has_citations
            FROM public.court_documents
            WHERE updated_at > NOW() - INTERVAL '5 minutes'
            GROUP BY court
            ORDER BY count DESC
        """)
        
        print("\nProcessed Documents by Court:")
        print("-" * 60)
        print(f"{'Court':<10} {'Count':<10} {'Has Judge':<12} {'Has Citations':<15}")
        print("-" * 60)
        
        for row in cursor.fetchall():
            court, count, has_judge, has_citations = row
            print(f"{court or 'N/A':<10} {count:<10} {has_judge:<12} {has_citations:<15}")
        
        cursor.close()
        conn.close()
    
    return results

if __name__ == "__main__":
    asyncio.run(process_texas_documents())