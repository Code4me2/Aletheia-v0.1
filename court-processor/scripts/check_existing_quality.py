#!/usr/bin/env python3
"""
Check the quality of existing unified pipeline data
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database import get_db_connection

def check_existing_quality():
    print("="*80)
    print("EXISTING DATA QUALITY CHECK")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Check E.D. Texas data from 2016-2017
        print("\n1. E.D. Texas opinions (2016-2017):")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(case_name) as has_case_name,
                COUNT(court_id) as has_court_id,
                COUNT(docket_number) as has_docket_number,
                COUNT(author_str) as has_author,
                COUNT(assigned_judge_name) as has_assigned_judge,
                COUNT(CASE WHEN author_str LIKE '%Gilstrap%' 
                    OR assigned_judge_name LIKE '%Gilstrap%' 
                    OR docket_number LIKE '%-JRG' 
                    THEN 1 END) as gilstrap_found
            FROM court_data.opinions_unified
            WHERE court_id = 'txed'
            AND date_filed >= '2016-01-01'
            AND date_filed <= '2017-12-31'
        """)
        
        row = cursor.fetchone()
        stats = {
            'total': row[0],
            'has_case_name': row[1],
            'has_court_id': row[2],
            'has_docket_number': row[3],
            'has_author': row[4],
            'has_assigned_judge': row[5],
            'gilstrap_found': row[6]
        }
        
        print(f"Total documents: {stats['total']}")
        for key in ['has_case_name', 'has_court_id', 'has_docket_number', 'has_author', 'has_assigned_judge', 'gilstrap_found']:
            pct = (stats[key] / stats['total'] * 100) if stats['total'] > 0 else 0
            print(f"{key}: {stats[key]}/{stats['total']} ({pct:.1f}%)")
        
        # 2. Sample some documents to see the data
        print("\n2. Sample documents:")
        cursor.execute("""
            SELECT 
                id,
                case_name,
                court_id,
                docket_number,
                author_str,
                assigned_judge_name,
                judge_info
            FROM court_data.opinions_unified
            WHERE court_id = 'txed'
            AND date_filed >= '2016-01-01'
            AND date_filed <= '2017-12-31'
            LIMIT 5
        """)
        
        for row in cursor.fetchall():
            print(f"\nDoc ID: {row[0]}")
            print(f"  Case: {row[1] or 'MISSING'}")
            print(f"  Court: {row[2] or 'MISSING'}")
            print(f"  Docket: {row[3] or 'MISSING'}")
            print(f"  Author: {row[4] or 'MISSING'}")
            print(f"  Assigned: {row[5] or 'MISSING'}")
            print(f"  Judge Info: {row[6] if row[6] else 'None'}")
        
        # 3. Check for Gilstrap in text
        print("\n3. Checking for Gilstrap in opinion text:")
        cursor.execute("""
            SELECT COUNT(*)
            FROM court_data.opinions_unified
            WHERE court_id = 'txed'
            AND date_filed >= '2016-01-01'
            AND date_filed <= '2017-12-31'
            AND plain_text ILIKE '%gilstrap%'
        """)
        text_matches = cursor.fetchone()[0]
        print(f"Documents with 'Gilstrap' in text: {text_matches}")
        
        # 4. Check overall unified pipeline data quality
        print("\n4. Overall unified pipeline data quality:")
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(case_name) as has_case_name,
                COUNT(court_id) as has_court_id,
                COUNT(docket_number) as has_docket_number,
                COUNT(author_str) + COUNT(assigned_judge_name) as has_any_judge
            FROM court_data.opinions_unified
        """)
        
        overall = cursor.fetchone()
        print(f"\nTotal documents in unified pipeline: {overall[0]}")
        for i, field in enumerate(['case_name', 'court_id', 'docket_number', 'any_judge']):
            pct = (overall[i+1] / overall[0] * 100) if overall[0] > 0 else 0
            print(f"Has {field}: {overall[i+1]}/{overall[0]} ({pct:.1f}%)")
            
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_existing_quality()