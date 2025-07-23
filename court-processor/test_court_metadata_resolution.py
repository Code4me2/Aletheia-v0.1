#!/usr/bin/env python3
"""
Test court metadata resolution issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection
import json


def test_court_resolution():
    """Test why courts aren't being resolved from metadata"""
    
    # Get a real document from database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, case_number, metadata
        FROM public.court_documents
        WHERE metadata::text LIKE '%"court":%'
        LIMIT 5
    """)
    
    documents = cursor.fetchall()
    conn.close()
    
    pipeline = RobustElevenStagePipeline()
    
    print("Testing court resolution on real documents:\n")
    
    for doc_id, case_number, metadata in documents:
        print(f"\nDocument ID: {doc_id}")
        print(f"Case Number: {case_number}")
        print(f"Metadata: {json.dumps(metadata, indent=2)[:200]}...")
        
        # Create document dict
        document = {
            'id': doc_id,
            'case_number': case_number,
            'metadata': metadata
        }
        
        # Test court resolution
        result = pipeline._enhance_court_info_validated(document)
        
        print(f"\nResolution result:")
        print(f"  Resolved: {result.get('resolved')}")
        if result.get('resolved'):
            print(f"  Court ID: {result.get('court_id')}")
            print(f"  Court Name: {result.get('court_name')}")
        else:
            print(f"  Reason: {result.get('reason')}")
            print(f"  Attempted court: {result.get('attempted_court_id')}")
        
        # Check if the court exists in our database
        if metadata and isinstance(metadata, dict):
            court_from_meta = metadata.get('court')
            if court_from_meta:
                from courts_db import courts
                found = any(c.get('id') == court_from_meta for c in courts if isinstance(c, dict))
                print(f"  Court '{court_from_meta}' exists in courts_db: {found}")
    

if __name__ == "__main__":
    test_court_resolution()