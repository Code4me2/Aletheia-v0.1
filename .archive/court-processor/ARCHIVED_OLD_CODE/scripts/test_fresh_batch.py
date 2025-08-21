#!/usr/bin/env python3
"""
Test unified pipeline with fresh data to see current behavior
"""
import asyncio
import sys
import os
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import UnifiedDocumentProcessor
from services.database import get_db_connection

async def test_fresh_batch():
    print("="*80)
    print("UNIFIED PIPELINE FRESH DATA TEST")
    print("="*80)
    
    processor = UnifiedDocumentProcessor()
    
    # Use more recent data that might not be processed yet
    params = {
        'court_id': 'txed',
        'date_filed_after': '2023-01-01',
        'max_documents': 5  # Small batch to analyze
    }
    
    print(f"\nTest parameters: {json.dumps(params, indent=2)}")
    
    try:
        # Force fresh data by clearing duplicates for this test
        print("\n1. Clearing test batch from deduplication...")
        processor.dedup_manager.processed_hashes.clear()
        
        print("\n2. Running unified processor...")
        results = await processor.process_courtlistener_batch(
            court_id=params['court_id'],
            date_filed_after=params['date_filed_after'],
            max_documents=params['max_documents']
        )
        
        print(f"\nProcessing results: {json.dumps(results, indent=2)}")
        
        # Check what was saved
        if results.get('new_documents', 0) > 0:
            print("\n3. Checking newly processed documents...")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    cl_id,
                    case_name,
                    court_id,
                    docket_number,
                    author_str,
                    assigned_judge_name,
                    cl_cluster_id,
                    cl_docket_id
                FROM court_data.opinions_unified
                WHERE created_at >= NOW() - INTERVAL '2 minutes'
                ORDER BY created_at DESC
                LIMIT 5
            """)
            
            for row in cursor.fetchall():
                print(f"\nDocument ID: {row[0]}")
                print(f"  CL Opinion ID: {row[1]}")
                print(f"  Case Name: {row[2] or 'MISSING'}")
                print(f"  Court ID: {row[3] or 'MISSING'}")
                print(f"  Docket Number: {row[4] or 'MISSING'}")
                print(f"  Author: {row[5] or 'MISSING'}")
                print(f"  Assigned Judge: {row[6] or 'MISSING'}")
                print(f"  CL Cluster ID: {row[7] or 'MISSING'}")
                print(f"  CL Docket ID: {row[8] or 'MISSING'}")
            
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await processor.cl_service.close()

if __name__ == "__main__":
    asyncio.run(test_fresh_batch())