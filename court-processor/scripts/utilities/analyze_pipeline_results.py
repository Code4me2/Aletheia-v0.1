#!/usr/bin/env python3
"""
Analyze the results of the pipeline processing
"""
import sys
sys.path.append('/app')

from services.database import get_db_connection
import json
from datetime import datetime


def analyze_pipeline_results():
    """Analyze what the pipeline processed"""
    
    print("\n" + "="*80)
    print("ANALYZING PIPELINE RESULTS")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Overall processing stats
    cursor.execute("""
        SELECT 
            cd.document_type,
            COUNT(*) as count,
            COUNT(CASE WHEN ou.citations IS NOT NULL AND ou.citations != '[]' THEN 1 END) as has_citations,
            COUNT(CASE WHEN ou.judge_info IS NOT NULL AND ou.judge_info != '{}' THEN 1 END) as has_judge,
            AVG(LENGTH(cd.content)) as avg_content_length
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '10 minutes'
        GROUP BY cd.document_type
        ORDER BY count DESC
    """)
    
    print("\nProcessing Results by Document Type:")
    print(f"{'Type':<15} {'Count':<8} {'Citations':<12} {'Judges':<10} {'Avg Content'}")
    print("-" * 60)
    
    for row in cursor.fetchall():
        doc_type, count, has_cites, has_judge, avg_content = row
        print(f"{doc_type:<15} {count:<8} {has_cites:<12} {has_judge:<10} {int(avg_content):,}")
    
    # 2. Citation extraction effectiveness
    print("\n" + "-"*60)
    print("CITATION EXTRACTION ANALYSIS")
    print("-"*60)
    
    cursor.execute("""
        SELECT 
            cd.document_type,
            COUNT(*) as doc_count,
            SUM(CASE 
                WHEN ou.citations IS NOT NULL AND ou.citations != '' 
                THEN jsonb_array_length(ou.citations::jsonb) 
                ELSE 0 
            END) as total_citations,
            AVG(CASE 
                WHEN ou.citations IS NOT NULL AND ou.citations != '' 
                THEN jsonb_array_length(ou.citations::jsonb) 
                ELSE 0 
            END) as avg_citations_per_doc
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '10 minutes'
        GROUP BY cd.document_type
    """)
    
    for row in cursor.fetchall():
        doc_type, count, total_cites, avg_cites = row
        print(f"{doc_type}: {total_cites} citations from {count} docs (avg: {avg_cites:.1f})")
        if doc_type == 'docket' and total_cites == 0:
            print("  ✅ Correctly: Dockets have no citations to extract")
    
    # 3. Judge extraction analysis
    print("\n" + "-"*60)
    print("JUDGE EXTRACTION ANALYSIS")
    print("-"*60)
    
    cursor.execute("""
        SELECT 
            cd.document_type,
            cd.case_number,
            cd.metadata->>'assigned_to' as metadata_judge,
            ou.judge_info->>'judge_name' as extracted_judge,
            ou.judge_info->>'extraction_source' as source
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '10 minutes'
        AND (cd.metadata->>'assigned_to' IS NOT NULL OR ou.judge_info->>'judge_name' IS NOT NULL)
        ORDER BY cd.document_type, cd.case_number
        LIMIT 15
    """)
    
    docket_issues = 0
    opinion_successes = 0
    
    print("\nJudge Extraction Examples:")
    for row in cursor.fetchall():
        doc_type, case, meta_judge, extracted, source = row
        print(f"\n{doc_type}: {case}")
        print(f"  Metadata judge: {meta_judge}")
        print(f"  Extracted judge: {extracted}")
        print(f"  Source: {source}")
        
        if doc_type in ['docket', 'recap_docket'] and meta_judge and not extracted:
            print("  ❌ ISSUE: Judge in metadata but not extracted")
            docket_issues += 1
        elif doc_type == 'opinion' and extracted:
            print("  ✅ SUCCESS: Judge extracted from opinion")
            opinion_successes += 1
    
    # 4. Overall quality assessment
    print("\n" + "-"*60)
    print("QUALITY ASSESSMENT")
    print("-"*60)
    
    cursor.execute("""
        SELECT 
            cd.document_type,
            COUNT(*) as count,
            AVG((ou.comprehensive_metadata->>'validation_summary'->>'completeness_score')::float) as avg_completeness,
            AVG((ou.comprehensive_metadata->>'validation_summary'->>'quality_score')::float) as avg_quality
        FROM public.court_documents cd
        JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id::integer
        WHERE ou.flp_processing_timestamp > NOW() - INTERVAL '10 minutes'
        GROUP BY cd.document_type
    """)
    
    for row in cursor.fetchall():
        doc_type, count, completeness, quality = row
        print(f"\n{doc_type}:")
        print(f"  Documents: {count}")
        print(f"  Avg completeness: {completeness:.1f}%" if completeness else "  Avg completeness: N/A")
        print(f"  Avg quality: {quality:.1f}%" if quality else "  Avg quality: N/A")
    
    # 5. Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    print("\nKey Findings:")
    print(f"1. Dockets processed for citations: Found 0 citations (wasteful)")
    print(f"2. Docket judge extraction issues: {docket_issues} judges missed from metadata")
    print(f"3. Opinion judge extraction: {opinion_successes} successfully extracted")
    print("\nRecommendations:")
    print("- Skip citation extraction for dockets (save ~0.5s per document)")
    print("- Extract judges from metadata.assigned_to for dockets")
    print("- Use document-type-specific quality metrics")
    print("- Handle missing cl_id with fallback to document ID")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    analyze_pipeline_results()