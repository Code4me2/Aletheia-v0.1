#!/usr/bin/env python3
"""
Simple analysis of pipeline results
"""
import sys
sys.path.append('/app')

from services.database import get_db_connection
import json


def analyze_results():
    """Simple analysis of what was processed"""
    
    print("\n" + "="*80)
    print("PIPELINE PROCESSING RESULTS ANALYSIS")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. What was processed
    cursor.execute("""
        SELECT 
            cd.document_type,
            COUNT(*) as count,
            COUNT(CASE WHEN LENGTH(ou.citations) > 2 THEN 1 END) as has_citations,
            COUNT(CASE WHEN LENGTH(ou.judge_info) > 2 THEN 1 END) as has_judge
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '30 minutes'
        GROUP BY cd.document_type
        ORDER BY count DESC
    """)
    
    print("\nDocuments Processed:")
    print(f"{'Type':<15} {'Count':<8} {'Has Citations':<15} {'Has Judge'}")
    print("-" * 50)
    
    total_docs = 0
    docket_count = 0
    opinion_count = 0
    
    for row in cursor.fetchall():
        doc_type, count, has_cites, has_judge = row
        print(f"{doc_type:<15} {count:<8} {has_cites:<15} {has_judge}")
        total_docs += count
        if doc_type == 'docket':
            docket_count = count
        elif doc_type == 'opinion':
            opinion_count = count
    
    # 2. Check specific docket examples
    print("\n" + "-"*50)
    print("DOCKET ANALYSIS")
    print("-"*50)
    
    cursor.execute("""
        SELECT 
            cd.case_number,
            cd.metadata->>'assigned_to' as metadata_judge,
            ou.judge_info
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE cd.document_type = 'docket'
        AND ou.flp_processing_timestamp > NOW() - INTERVAL '30 minutes'
        LIMIT 5
    """)
    
    missed_judges = 0
    print("\nDocket Examples:")
    for case, meta_judge, judge_info in cursor.fetchall():
        print(f"\nCase: {case}")
        print(f"  Judge in metadata: {meta_judge}")
        print(f"  Judge extracted: {'Yes' if judge_info and len(judge_info) > 2 else 'No'}")
        if meta_judge and (not judge_info or len(judge_info) <= 2):
            print("  ❌ MISSED: Judge was in metadata but not extracted")
            missed_judges += 1
    
    # 3. Check citation extraction
    print("\n" + "-"*50)
    print("CITATION EXTRACTION")
    print("-"*50)
    
    cursor.execute("""
        SELECT 
            cd.document_type,
            cd.case_number,
            LENGTH(ou.citations) as citation_length
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '30 minutes'
        ORDER BY cd.document_type, cd.case_number
        LIMIT 10
    """)
    
    print("\nCitation Extraction Examples:")
    for doc_type, case, cite_len in cursor.fetchall():
        has_citations = cite_len > 2  # More than just "[]"
        print(f"{doc_type}: {case} - Citations: {'Yes' if has_citations else 'No'}")
        if doc_type == 'docket' and not has_citations:
            print("  ✅ Correct: Dockets should not have citations")
    
    # 4. Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print(f"\nTotal documents processed: {total_docs}")
    print(f"  Opinions: {opinion_count}")
    print(f"  Dockets: {docket_count}")
    
    print(f"\nIssues Found:")
    print(f"  - Dockets with missed judges: {missed_judges}")
    print(f"  - Dockets processed for citations: {docket_count} (wasteful)")
    
    print(f"\nRecommendations:")
    print(f"  1. Skip citation extraction for dockets (save ~{docket_count * 0.5:.1f} seconds)")
    print(f"  2. Extract judges from metadata for dockets (gain ~{missed_judges} judges)")
    print(f"  3. Use adaptive quality metrics")
    print(f"  4. Fix missing cl_id with fallbacks")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    analyze_results()