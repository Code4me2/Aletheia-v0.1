#!/usr/bin/env python3
"""
Test the unified pipeline as-is to establish baseline data quality
"""
import asyncio
import sys
import os
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import UnifiedDocumentProcessor
from services.database import get_db_connection

async def test_baseline_quality():
    print("="*80)
    print("UNIFIED PIPELINE BASELINE TEST")
    print("="*80)
    print(f"Start time: {datetime.now()}")
    
    processor = UnifiedDocumentProcessor()
    
    # Test with E.D. Texas opinions from 2016-2017 (Gilstrap's peak period)
    params = {
        'court_id': 'txed',
        'date_filed_after': '2016-01-01',
        'date_filed_before': '2017-12-31',
        'max_results': 10  # Start small
    }
    
    print(f"\nTest parameters: {json.dumps(params, indent=2)}")
    
    try:
        # Run the processor
        print("\n1. Running unified processor...")
        results = await processor.process_courtlistener_batch(
            court_id=params['court_id'],
            date_filed_after=params['date_filed_after'],
            max_documents=params['max_results']
        )
        
        print(f"\nProcessing complete. Results: {results}")
        
        # Check what was actually saved
        print("\n2. Checking database for saved documents...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent documents
        cursor.execute("""
            SELECT 
                id,
                case_name,
                court_id,
                docket_number,
                author_str,
                created_at,
                judge_info,
                assigned_judge_name
            FROM court_data.opinions_unified
            WHERE created_at >= NOW() - INTERVAL '5 minutes'
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        rows = cursor.fetchall()
        print(f"\nFound {len(rows)} recently processed documents")
        
        # Analyze metadata completeness
        metadata_stats = {
            'total': len(rows),
            'has_case_name': 0,
            'has_court_id': 0,
            'has_docket_number': 0,
            'has_judge': 0,
            'gilstrap_found': 0
        }
        
        for row in rows:
            id_, case_name, court_id, docket_number, author_str, created_at, judge_info, assigned_judge = row
            
            if case_name:
                metadata_stats['has_case_name'] += 1
            if court_id:
                metadata_stats['has_court_id'] += 1
            if docket_number:
                metadata_stats['has_docket_number'] += 1
            if author_str or assigned_judge:
                metadata_stats['has_judge'] += 1
                judge_text = f"{author_str or ''} {assigned_judge or ''}"
                if 'Gilstrap' in judge_text or 'JRG' in (docket_number or ''):
                    metadata_stats['gilstrap_found'] += 1
            
            print(f"\nDocument {id_}:")
            print(f"  Case: {case_name or 'MISSING'}")
            print(f"  Court: {court_id or 'MISSING'}")
            print(f"  Docket: {docket_number or 'MISSING'}")
            print(f"  Judge (author): {author_str or 'MISSING'}")
            print(f"  Judge (assigned): {assigned_judge or 'MISSING'}")
            print(f"  Judge info: {judge_info if judge_info else 'None'}")
        
        # Summary statistics
        print("\n" + "="*80)
        print("METADATA COMPLETENESS ANALYSIS")
        print("="*80)
        for key, value in metadata_stats.items():
            if key != 'total':
                pct = (value / metadata_stats['total'] * 100) if metadata_stats['total'] > 0 else 0
                print(f"{key}: {value}/{metadata_stats['total']} ({pct:.1f}%)")
        
        # Check for Gilstrap in text content
        print("\n3. Checking for Gilstrap in opinion text...")
        cursor.execute("""
            SELECT COUNT(*) 
            FROM court_data.opinions_unified
            WHERE created_at >= NOW() - INTERVAL '5 minutes'
            AND plain_text ILIKE '%gilstrap%'
        """)
        text_matches = cursor.fetchone()[0]
        print(f"Documents with 'Gilstrap' in text: {text_matches}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # No close method on processor, but close the service
        await processor.cl_service.close()

if __name__ == "__main__":
    asyncio.run(test_baseline_quality())