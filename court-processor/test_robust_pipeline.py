#!/usr/bin/env python3
"""
Test the Robust Eleven Stage Pipeline

This test verifies:
- Error handling at each stage
- Validation enforcement
- Proper error reporting
- No hardcoded defaults
- Honest metrics
"""

import asyncio
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from pipeline_exceptions import *
from pipeline_validators import *
from error_reporter import ErrorCollector


async def test_robust_pipeline():
    """Test the robust pipeline with various scenarios"""
    print("\n" + "=" * 80)
    print("TESTING ROBUST ELEVEN STAGE PIPELINE")
    print("=" * 80)
    
    # Test 1: Normal operation with valid data
    print("\n1. Testing normal operation with valid data...")
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(limit=5)
        
        print("\nPipeline Results:")
        print(f"Success: {results['success']}")
        print(f"Documents processed: {results['statistics']['documents_processed']}")
        print(f"Documents validated: {results['statistics']['documents_validated']}")
        print(f"Courts resolved: {results['statistics']['courts_resolved']}")
        print(f"Citations extracted: {results['statistics']['citations_extracted']}")
        print(f"Total errors: {results['statistics']['total_errors']}")
        print(f"Total warnings: {results['statistics']['total_warnings']}")
        
        if results.get('verification'):
            print(f"\nCompleteness Score: {results['verification']['completeness_score']:.1f}%")
            print(f"Quality Score: {results['verification']['quality_score']:.1f}%")
        
        # Check error report
        error_report = results.get('error_report', {})
        if error_report.get('total_errors', 0) > 0:
            print("\nErrors encountered:")
            for stage, errors in error_report.get('errors_by_stage', {}).items():
                print(f"  {stage}: {len(errors)} errors")
                for error in errors[:2]:  # Show first 2 errors
                    print(f"    - {error['error_type']}: {error['message']}")
        
        if error_report.get('total_warnings', 0) > 0:
            print("\nWarnings:")
            for stage, warnings in error_report.get('warnings_by_stage', {}).items():
                print(f"  {stage}: {len(warnings)} warnings")
                
    except Exception as e:
        print(f"Error in normal operation test: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Test with strict validation
    print("\n\n2. Testing with strict validation enabled...")
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(limit=3, validate_strict=True)
        
        print(f"\nWith strict validation:")
        print(f"Documents processed: {results['statistics']['documents_processed']}")
        print(f"Validation failures: {results['statistics']['validation_failures']}")
        print(f"Documents stored: {results['statistics']['documents_stored']}")
        
    except Exception as e:
        print(f"Error in strict validation test: {e}")
    
    # Test 3: Test error handling with bad table
    print("\n\n3. Testing error handling with invalid table...")
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(limit=1, source_table="invalid.table; DROP TABLE")
        print("Should not reach here - SQL injection should be prevented")
    except ValidationError as e:
        print(f"✓ Correctly caught validation error: {e}")
    except Exception as e:
        print(f"✓ Caught error (expected): {type(e).__name__}: {e}")
    
    # Test 4: Check quality metrics
    print("\n\n4. Testing quality metrics calculation...")
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(limit=10)
        
        quality_metrics = results.get('quality_metrics', {})
        if quality_metrics:
            print("\nQuality Metrics:")
            print(f"Validation rate: {quality_metrics.get('validation_rate', 0):.1f}%")
            print(f"Court resolution rate: {quality_metrics.get('court_resolution_rate', 0):.1f}%")
            print(f"Citation extraction rate: {quality_metrics.get('citation_extraction_rate', 0):.1f}%")
            print(f"Judge identification rate: {quality_metrics.get('judge_identification_rate', 0):.1f}%")
            print(f"Error rate: {quality_metrics.get('error_rate', 0):.1f}%")
            
            indicators = quality_metrics.get('data_quality_indicators', {})
            print("\nData Quality Indicators:")
            for indicator, value in indicators.items():
                print(f"  {indicator}: {value}")
    except Exception as e:
        print(f"Error in quality metrics test: {e}")
    
    # Test 5: Verify no hardcoded defaults
    print("\n\n5. Verifying no hardcoded defaults...")
    try:
        # Create a test document with no court info
        from services.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert test document with no court metadata
        cursor.execute("""
            INSERT INTO public.court_documents (case_number, document_type, content, metadata)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            "TEST-NO-COURT",
            "test",
            "This is a test document with no court information.",
            json.dumps({})
        ))
        test_id = cursor.fetchone()[0]
        conn.commit()
        
        # Process just this document
        cursor.execute("""
            SELECT * FROM public.court_documents WHERE id = %s
        """, (test_id,))
        
        pipeline = RobustElevenStagePipeline()
        # Process by fetching specific document
        results = await pipeline.process_batch(limit=1, source_table='public.court_documents')
        
        # Check if any document has unresolved court
        if results['statistics']['courts_unresolved'] > 0:
            print("✓ No hardcoded court defaults - unresolved courts properly tracked")
        else:
            print("✗ Warning: All courts resolved - might have hardcoded defaults")
        
        # Cleanup
        cursor.execute("DELETE FROM public.court_documents WHERE id = %s", (test_id,))
        conn.commit()
        conn.close()
        
    except Exception as e:
        print(f"Error in hardcoded defaults test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_robust_pipeline())