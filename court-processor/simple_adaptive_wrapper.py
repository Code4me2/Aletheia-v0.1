#!/usr/bin/env python3
"""
Simple wrapper to add adaptive behavior to existing pipeline
Minimal changes, maximum compatibility
"""
import asyncio
import sys
import json
import logging
from typing import Dict, Any, List

sys.path.append('/app')

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from document_type_detector import DocumentTypeDetector
from services.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fix_missing_cl_ids():
    """Ensure all documents have cl_id before processing"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # First, check how many need fixing
        cursor.execute("""
            SELECT COUNT(*) 
            FROM public.court_documents 
            WHERE metadata->>'cl_id' IS NULL 
               OR metadata->>'cl_id' = ''
        """)
        
        need_fixing = cursor.fetchone()[0]
        
        if need_fixing > 0:
            # Fix them
            cursor.execute("""
                UPDATE public.court_documents
                SET metadata = 
                    CASE 
                        WHEN metadata IS NULL THEN jsonb_build_object('cl_id', id::text)
                        ELSE metadata || jsonb_build_object('cl_id', id::text)
                    END
                WHERE metadata->>'cl_id' IS NULL 
                   OR metadata->>'cl_id' = ''
                RETURNING id
            """)
            
            fixed_ids = cursor.fetchall()
            conn.commit()
            logger.info(f"✅ Fixed {len(fixed_ids)} documents with missing cl_id")
            return len(fixed_ids)
    
    except Exception as e:
        logger.error(f"Error fixing cl_ids: {e}")
        conn.rollback()
        return 0
    finally:
        cursor.close()
        conn.close()
    
    return 0


async def run_adaptive_pipeline(limit: int = 30):
    """Run pipeline with document-type awareness"""
    
    print("\n" + "="*80)
    print("ADAPTIVE PIPELINE PROCESSING")
    print("="*80)
    
    # Step 1: Fix missing cl_ids
    fixed_count = fix_missing_cl_ids()
    
    # Step 2: Analyze what we're about to process
    detector = DocumentTypeDetector()
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            COALESCE(metadata->>'cl_id', id::text) as cl_id,
            document_type,
            LENGTH(COALESCE(content, '')) as content_length,
            metadata
        FROM public.court_documents
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    
    # Analyze document mix
    doc_types = {
        'opinion': {'count': 0, 'should_have_citations': 0},
        'docket': {'count': 0, 'has_judge_metadata': 0},
        'order': {'count': 0},
        'other': {'count': 0}
    }
    
    documents_to_process = []
    
    for row in cursor.fetchall():
        cl_id, doc_type, content_len, metadata = row
        
        # Detect actual type
        doc = {
            'cl_id': cl_id,
            'document_type': doc_type,
            'content_length': content_len,
            'metadata': metadata
        }
        
        detected_type, confidence, _ = detector.detect_type({
            'content': 'x' * content_len,  # Simulate content length
            'document_type': doc_type,
            'metadata': metadata
        })
        
        # Categorize
        if detected_type == 'opinion' and content_len > 5000:
            doc_types['opinion']['count'] += 1
            doc_types['opinion']['should_have_citations'] += 1
        elif detected_type == 'docket':
            doc_types['docket']['count'] += 1
            # Check for judge in metadata
            if isinstance(metadata, dict) and metadata.get('assigned_to'):
                doc_types['docket']['has_judge_metadata'] += 1
        elif detected_type == 'order':
            doc_types['order']['count'] += 1
        else:
            doc_types['other']['count'] += 1
        
        documents_to_process.append(doc)
    
    cursor.close()
    conn.close()
    
    # Step 3: Show pre-processing analysis
    print(f"\nPre-processing Analysis:")
    print(f"  Fixed {fixed_count} documents with missing cl_id")
    print(f"\nDocument Mix (top {limit}):")
    for doc_type, info in doc_types.items():
        if info['count'] > 0:
            print(f"  {doc_type}: {info['count']} documents")
            if doc_type == 'opinion':
                print(f"    - Should have citations: {info['should_have_citations']}")
            elif doc_type == 'docket':
                print(f"    - Have judge in metadata: {info['has_judge_metadata']}")
    
    # Step 4: Run standard pipeline
    print(f"\nRunning standard pipeline...")
    pipeline = RobustElevenStagePipeline()
    results = await pipeline.process_batch(limit=limit, force_reprocess=True)
    
    # Step 5: Post-processing analysis
    if results['success']:
        print("\n" + "="*80)
        print("POST-PROCESSING ANALYSIS")
        print("="*80)
        
        stats = results['statistics']
        
        # Check for issues
        issues = []
        
        # Issue 1: Dockets with citations (shouldn't happen)
        if doc_types['docket']['count'] > 0 and stats.get('citations_extracted', 0) > 0:
            avg_citations = stats['citations_extracted'] / stats['documents_processed']
            if avg_citations < 5:  # Low citation count suggests dockets were processed
                issues.append("⚠️  Low citation count suggests dockets were processed for citations")
        
        # Issue 2: Missing judges in dockets
        if doc_types['docket']['has_judge_metadata'] > 0:
            judge_rate = stats.get('judges_enhanced', 0) / stats['documents_processed']
            if judge_rate < 0.3:
                issues.append("⚠️  Low judge extraction rate despite metadata availability")
        
        # Issue 3: Empty results
        if stats['documents_processed'] > 0 and stats.get('citations_extracted', 0) == 0:
            if doc_types['opinion']['count'] > 0:
                issues.append("❌ No citations found despite having opinion documents")
        
        # Display results
        print(f"\nStandard Pipeline Results:")
        print(f"  Documents processed: {stats['documents_processed']}")
        print(f"  Citations extracted: {stats.get('citations_extracted', 0)}")
        print(f"  Judges identified: {stats.get('judges_enhanced', 0)}")
        
        if issues:
            print(f"\nIssues Detected:")
            for issue in issues:
                print(f"  {issue}")
        
        # Recommendations
        print(f"\nRecommendations for Adaptive Processing:")
        if doc_types['docket']['count'] > 0:
            print(f"  • Skip citation extraction for {doc_types['docket']['count']} dockets")
            print(f"  • Extract judges from metadata for {doc_types['docket']['has_judge_metadata']} dockets")
        if doc_types['opinion']['count'] > 0:
            print(f"  • Full processing for {doc_types['opinion']['count']} opinions")
        
        # Calculate what metrics SHOULD be
        print(f"\nExpected vs Actual Performance:")
        
        # Expected citations (only from opinions)
        expected_citations = doc_types['opinion']['count'] * 30  # ~30 per opinion
        actual_citations = stats.get('citations_extracted', 0)
        print(f"  Citations: expected ~{expected_citations}, got {actual_citations}")
        
        # Expected judges
        expected_judges = (
            doc_types['opinion']['count'] * 0.3 +  # 30% from opinion text
            doc_types['docket']['has_judge_metadata']  # 100% from metadata
        )
        actual_judges = stats.get('judges_enhanced', 0)
        print(f"  Judges: expected ~{int(expected_judges)}, got {actual_judges}")
        
    else:
        print(f"\nPipeline failed: {results.get('error')}")
    
    return results


async def demonstrate_adaptive_strategies():
    """Show how different document types should be processed"""
    
    print("\n" + "="*80)
    print("ADAPTIVE PROCESSING STRATEGIES")
    print("="*80)
    
    detector = DocumentTypeDetector()
    
    # Get sample documents of each type
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get one of each type
    samples = {
        'opinion': None,
        'docket': None,
        'recap_docket': None,
        'civil_case': None
    }
    
    for doc_type in samples.keys():
        cursor.execute("""
            SELECT id, case_number, content, metadata
            FROM public.court_documents
            WHERE document_type = %s
            AND LENGTH(COALESCE(content, '')) > 0
            LIMIT 1
        """, (doc_type,))
        
        row = cursor.fetchone()
        if row:
            samples[doc_type] = {
                'id': row[0],
                'case_number': row[1],
                'content': row[2],
                'metadata': row[3]
            }
    
    cursor.close()
    conn.close()
    
    # Demonstrate processing for each
    for doc_type, doc in samples.items():
        if doc:
            print(f"\n{doc_type.upper()} Processing Strategy:")
            print("-" * 40)
            
            detected, confidence, chars = detector.detect_type({
                'content': doc['content'],
                'document_type': doc_type,
                'metadata': doc['metadata']
            })
            
            strategy = detector.get_processing_strategy(detected)
            
            print(f"Document: {doc['case_number']}")
            print(f"Detected type: {detected} ({confidence:.1%} confidence)")
            print(f"Content length: {len(doc['content'])} chars")
            print(f"Has citations: {chars['has_citations']} ({chars['citation_count']} found)")
            
            print(f"\nRecommended stages: {strategy['stages']}")
            print(f"Judge extraction: {strategy['judge_extraction']}")
            
            # Check metadata for judge
            if isinstance(doc['metadata'], dict) and doc['metadata'].get('assigned_to'):
                print(f"✅ Judge in metadata: {doc['metadata']['assigned_to']}")


if __name__ == "__main__":
    # Run the main analysis
    asyncio.run(run_adaptive_pipeline(30))
    
    # Show adaptive strategies
    asyncio.run(demonstrate_adaptive_strategies())