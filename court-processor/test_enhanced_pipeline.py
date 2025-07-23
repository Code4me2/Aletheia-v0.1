#!/usr/bin/env python3
"""
Test Enhanced Pipeline with Document Type Awareness
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline as EnhancedElevenStagePipeline
from services.database import get_db_connection
import json


async def test_enhanced_pipeline():
    """Test the enhanced pipeline with document type awareness"""
    print("\n" + "=" * 80)
    print("TESTING ENHANCED PIPELINE WITH DOCUMENT TYPE AWARENESS")
    print("=" * 80)
    
    # Test 1: Process a mix of document types
    print("\n1. Testing with mixed document types...")
    try:
        pipeline = EnhancedElevenStagePipeline()
        results = await pipeline.process_batch(limit=10)
        
        print("\nPipeline Results:")
        print(f"Success: {results['success']}")
        print(f"Documents processed: {results['statistics']['documents_processed']}")
        
        # Show document type distribution
        print("\nDocument Type Distribution:")
        type_stats = results.get('document_type_statistics', {})
        for doc_type, stats in type_stats.items():
            count = stats.get('count', 0)
            percentage = stats.get('percentage', 0)
            print(f"  {doc_type}: {count} documents ({percentage:.1f}%)")
        
        # Show overall verification
        verification = results.get('verification', {})
        if verification:
            overall = verification.get('overall', {})
            print(f"\nOverall Performance:")
            print(f"  Completeness: {overall.get('completeness_score', 0):.1f}%")
            print(f"  Quality: {overall.get('quality_score', 0):.1f}%")
            
            # Show type-specific metrics
            by_type = verification.get('by_document_type', {})
            if by_type:
                print("\nPerformance by Document Type:")
                for doc_type, metrics in by_type.items():
                    print(f"\n  {doc_type.upper()}:")
                    print(f"    Completeness: {metrics.get('completeness_score', 0):.1f}%")
                    print(f"    Quality: {metrics.get('quality_score', 0):.1f}%")
                    print(f"    Court resolution: {metrics.get('court_resolution_rate', 0):.1f}%")
                    print(f"    Judge identification: {metrics.get('judge_identification_rate', 0):.1f}%")
            
            # Show insights
            insights = verification.get('insights', [])
            if insights:
                print("\nInsights:")
                for insight in insights:
                    print(f"  - {insight}")
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Check specific document types
    print("\n\n2. Checking document type detection accuracy...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get specific document types
        cursor.execute("""
            SELECT id, case_number, metadata::text as metadata_text
            FROM public.court_documents
            WHERE 
                (case_number LIKE 'OPINION-%' OR 
                 metadata::text LIKE '%"type":%' OR
                 metadata::text LIKE '%"docket_id":%')
            LIMIT 5
        """)
        
        print("\nDocument Type Detection Results:")
        for doc_id, case_number, metadata_text in cursor.fetchall():
            # Parse metadata
            try:
                metadata = json.loads(metadata_text) if metadata_text else {}
            except:
                metadata = {}
            
            # Create minimal document for type detection
            doc = {
                'id': doc_id,
                'case_number': case_number,
                'metadata': metadata
            }
            
            pipeline = EnhancedElevenStagePipeline()
            detected_type = pipeline._detect_document_type(doc)
            
            print(f"\n  ID: {doc_id}")
            print(f"  Case: {case_number}")
            print(f"  Metadata type field: {metadata.get('type', 'None')}")
            print(f"  Has cluster: {'cluster' in metadata}")
            print(f"  Has docket_id: {'docket_id' in metadata}")
            print(f"  Detected type: {detected_type}")
        
        conn.close()
    except Exception as e:
        print(f"Error checking document types: {e}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_pipeline())