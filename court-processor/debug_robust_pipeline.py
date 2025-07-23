#!/usr/bin/env python3
"""
Debug Robust Pipeline - Gather comprehensive debugging information
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from pipeline_exceptions import *
from services.database import get_db_connection
from courts_db import courts
from reporters_db import REPORTERS
import judge_pics


async def debug_pipeline():
    """Run comprehensive debugging tests"""
    print("\n" + "=" * 80)
    print("DEBUGGING ROBUST PIPELINE")
    print("=" * 80)
    
    # 1. Check database connectivity and schema
    print("\n1. Checking database connectivity and schema...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check court_documents table
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = 'court_documents'
            ORDER BY ordinal_position
        """)
        print("\nCourt documents columns:")
        for col in cursor.fetchall():
            print(f"  - {col[0]}: {col[1]}")
        
        # Check opinions_unified table
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'court_data' AND table_name = 'opinions_unified'
            ORDER BY ordinal_position
        """)
        print("\nOpinions unified columns:")
        for col in cursor.fetchall():
            print(f"  - {col[0]}: {col[1]}")
        
        # Check sample data
        cursor.execute("""
            SELECT id, case_number, document_type, 
                   LENGTH(content) as content_length,
                   metadata::text as metadata_sample
            FROM public.court_documents 
            LIMIT 3
        """)
        print("\nSample documents:")
        for doc in cursor.fetchall():
            print(f"\n  ID: {doc[0]}")
            print(f"  Case: {doc[1]}")
            print(f"  Type: {doc[2]}")
            print(f"  Content Length: {doc[3]}")
            print(f"  Metadata: {doc[4][:100]}..." if doc[4] else "  Metadata: None")
        
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        import traceback
        traceback.print_exc()
    
    # 2. Check FLP tools availability
    print("\n\n2. Checking FLP tools availability...")
    
    # Courts database
    print(f"\nCourts database:")
    print(f"  Total courts: {len(courts)}")
    print(f"  Sample courts:")
    for court in courts[:3]:
        if isinstance(court, dict):
            print(f"    - {court.get('id')}: {court.get('name')}")
    
    # Check for specific courts that should exist
    test_courts = ['txed', 'cacd', 'nysd']
    for court_id in test_courts:
        found = any(c.get('id') == court_id for c in courts if isinstance(c, dict))
        print(f"  Court '{court_id}' found: {found}")
    
    # Reporters database
    print(f"\nReporters database:")
    print(f"  Total reporters: {len(REPORTERS)}")
    print(f"  Sample reporters:")
    for key in list(REPORTERS.keys())[:5]:
        print(f"    - {key}: {type(REPORTERS[key])}")
    
    # Check specific reporters
    test_reporters = ['F.', 'F.2d', 'F.3d', 'F. Supp.', 'U.S.']
    for reporter in test_reporters:
        print(f"  Reporter '{reporter}' exists: {reporter in REPORTERS}")
    
    # Judge pics
    print(f"\nJudge pics:")
    judge_data_path = os.path.join(judge_pics.judge_root, 'people.json')
    print(f"  Judge data path: {judge_data_path}")
    print(f"  Path exists: {os.path.exists(judge_data_path)}")
    if os.path.exists(judge_data_path):
        with open(judge_data_path, 'r') as f:
            judges_data = json.load(f)
            print(f"  Total judges: {len(judges_data)}")
    
    # 3. Test pipeline with detailed error tracking
    print("\n\n3. Testing pipeline with detailed tracking...")
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(limit=2)
        
        print("\nPipeline execution results:")
        print(f"  Success: {results['success']}")
        print(f"  Stages completed: {len(results.get('stages_completed', []))}")
        
        stats = results.get('statistics', {})
        print("\nStatistics:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # Check verification details
        verification = results.get('verification', {})
        if verification:
            print("\nVerification details:")
            print(f"  Completeness: {verification.get('completeness_score', 0):.1f}%")
            print(f"  Quality: {verification.get('quality_score', 0):.1f}%")
            print(f"  Courts resolved: {verification.get('documents_with_court_resolution', 0)}")
            print(f"  Valid courts: {verification.get('documents_with_valid_court', 0)}")
            print(f"  Citations found: {verification.get('documents_with_citations', 0)}")
            print(f"  Valid citations: {verification.get('documents_with_valid_citations', 0)}")
            print(f"  Judges found: {verification.get('documents_with_judge_info', 0)}")
            print(f"  Valid judges: {verification.get('documents_with_valid_judge', 0)}")
            
            # Extraction improvements
            improvements = verification.get('extraction_improvements', {})
            if improvements:
                print("\nExtraction improvements:")
                print(f"  Courts from content: {improvements.get('courts_from_content', 0)}")
                print(f"  Judges from content: {improvements.get('judges_from_content', 0)}")
        
        # Error analysis
        error_report = results.get('error_report', {})
        if error_report:
            print("\nError Analysis:")
            print(f"  Total errors: {error_report.get('total_errors', 0)}")
            print(f"  Total warnings: {error_report.get('total_warnings', 0)}")
            print(f"  Validation failures: {error_report.get('validation_failures', 0)}")
            
            # Errors by stage
            errors_by_stage = error_report.get('errors_by_stage', {})
            if errors_by_stage:
                print("\nErrors by stage:")
                for stage, errors in errors_by_stage.items():
                    print(f"  {stage}: {len(errors)} errors")
                    for error in errors[:1]:  # Show first error
                        print(f"    Type: {error.get('error_type')}")
                        print(f"    Message: {error.get('message')}")
                        if error.get('document_id'):
                            print(f"    Document: {error.get('document_id')}")
        
    except Exception as e:
        print(f"Pipeline error: {e}")
        import traceback
        traceback.print_exc()
    
    # 4. Test specific problem areas
    print("\n\n4. Testing specific problem areas...")
    
    # Test court resolution
    print("\nTesting court resolution:")
    test_cases = [
        {"case_number": "2:20-cv-00123", "metadata": {}},
        {"case_number": "txed:2020-cv-00456", "metadata": {}},
        {"case_number": "1:21-cv-00789", "metadata": {"court": "nysd"}},
    ]
    
    try:
        pipeline = RobustElevenStagePipeline()
        for test_case in test_cases:
            result = pipeline._enhance_court_info_validated(test_case)
            print(f"\n  Case: {test_case['case_number']}")
            print(f"  Resolved: {result.get('resolved')}")
            if result.get('resolved'):
                print(f"  Court ID: {result.get('court_id')}")
                print(f"  Court Name: {result.get('court_name')}")
            else:
                print(f"  Reason: {result.get('reason')}")
    except Exception as e:
        print(f"Court resolution test error: {e}")
    
    # Test judge extraction patterns
    print("\n\nTesting judge extraction patterns:")
    test_contents = [
        "Before Judge John Smith, United States District Judge",
        "Honorable Jane M. Doe, Chief District Judge",
        "WILLIAM JOHNSON, UNITED STATES DISTRICT JUDGE",
        "Signed by Judge Robert Brown",
    ]
    
    try:
        pipeline = RobustElevenStagePipeline()
        for content in test_contents:
            judge = pipeline._extract_judge_from_content_optimized(content)
            print(f"\n  Content: '{content[:50]}...'")
            print(f"  Extracted: {judge}")
    except Exception as e:
        print(f"Judge extraction test error: {e}")
    
    # 5. Check for missing metadata patterns
    print("\n\n5. Analyzing metadata patterns...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN metadata IS NULL THEN 1 END) as null_metadata,
                COUNT(CASE WHEN metadata::text = '{}' THEN 1 END) as empty_metadata,
                COUNT(CASE WHEN metadata::text LIKE '%court%' THEN 1 END) as has_court,
                COUNT(CASE WHEN metadata::text LIKE '%judge%' THEN 1 END) as has_judge
            FROM public.court_documents
        """)
        
        result = cursor.fetchone()
        print("\nMetadata analysis:")
        print(f"  Total documents: {result[0]}")
        print(f"  Null metadata: {result[1]} ({result[1]/result[0]*100:.1f}%)")
        print(f"  Empty metadata: {result[2]} ({result[2]/result[0]*100:.1f}%)")
        print(f"  Has 'court' field: {result[3]} ({result[3]/result[0]*100:.1f}%)")
        print(f"  Has 'judge' field: {result[4]} ({result[4]/result[0]*100:.1f}%)")
        
        conn.close()
    except Exception as e:
        print(f"Metadata analysis error: {e}")
    
    print("\n" + "=" * 80)
    print("Debugging complete")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_pipeline())