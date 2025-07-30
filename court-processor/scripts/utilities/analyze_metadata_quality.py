#!/usr/bin/env python3
"""
Analyze metadata quality in court documents
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from psycopg2.extras import RealDictCursor
import json

def analyze_metadata_quality():
    """Analyze the quality and intelligibility of metadata"""
    
    conn = get_db_connection(cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    try:
        # Overall statistics
        cur.execute("""
            SELECT 
                COUNT(*) as total_docs,
                COUNT(metadata) as has_metadata
            FROM public.court_documents
        """)
        
        result = cur.fetchone()
        print("METADATA QUALITY ANALYSIS")
        print("="*60)
        print(f"Total documents: {result['total_docs']:,}")
        print(f"Have metadata: {result['has_metadata']:,} ({result['has_metadata']/result['total_docs']*100:.1f}%)")
        
        # Check key fields
        print("\nKey Field Coverage:")
        print("-"*40)
        
        fields = ['case_name', 'court', 'judge_name', 'assigned_to', 'date_filed', 'docket_number']
        
        for field in fields:
            cur.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(metadata->>%s) as not_null,
                    COUNT(CASE WHEN LENGTH(metadata->>%s) > 0 THEN 1 END) as not_empty,
                    COUNT(CASE WHEN metadata->>%s = '' THEN 1 END) as empty_string
                FROM public.court_documents
                WHERE metadata IS NOT NULL
            """, (field, field, field))
            
            res = cur.fetchone()
            coverage = res['not_empty']/res['total']*100 if res['total'] > 0 else 0
            empty_pct = res['empty_string']/res['total']*100 if res['total'] > 0 else 0
            
            print(f"{field:15}: {res['not_empty']:,}/{res['total']:,} ({coverage:5.1f}% filled, {empty_pct:5.1f}% empty)")
        
        # Check for common issues
        print("\n\nData Quality Issues:")
        print("-"*40)
        
        # Check case name quality
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN metadata->>'case_name' LIKE '%?%' THEN 1 END) as with_questions,
                COUNT(CASE WHEN LENGTH(metadata->>'case_name') > 150 THEN 1 END) as very_long,
                COUNT(CASE WHEN metadata->>'case_name' ~ '[^[:ascii:]]' THEN 1 END) as non_ascii
            FROM public.court_documents
            WHERE metadata->>'case_name' IS NOT NULL
        """)
        
        case_quality = cur.fetchone()
        
        print(f"Case names with issues (out of {case_quality['total']:,}):")
        print(f"  With '?' marks: {case_quality['with_questions']:,} ({case_quality['with_questions']/case_quality['total']*100:.1f}%)")
        print(f"  Very long (>150 chars): {case_quality['very_long']:,} ({case_quality['very_long']/case_quality['total']*100:.1f}%)")
        print(f"  Non-ASCII characters: {case_quality['non_ascii']:,} ({case_quality['non_ascii']/case_quality['total']*100:.1f}%)")
        
        # Check assigned_to values
        cur.execute("""
            SELECT 
                metadata->>'assigned_to' as value,
                COUNT(*) as count
            FROM public.court_documents
            WHERE metadata->>'assigned_to' IS NOT NULL
            AND metadata->>'assigned_to' != ''
            GROUP BY metadata->>'assigned_to'
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\nTop 10 'assigned_to' values:")
        for row in cur.fetchall():
            print(f"  '{row['value']}': {row['count']:,} documents")
        
        # Sample some documents to see typical metadata
        print("\n\nSample Document Metadata:")
        print("-"*60)
        
        cur.execute("""
            SELECT 
                id,
                document_type,
                metadata,
                LENGTH(content) as content_length
            FROM public.court_documents
            WHERE metadata IS NOT NULL
            ORDER BY id DESC
            LIMIT 5
        """)
        
        for doc in cur.fetchall():
            metadata = doc['metadata'] or {}
            print(f"\nDoc {doc['id']} (Type: {doc['document_type'] or 'unknown'}, {doc['content_length']:,} chars):")
            print(f"  Case: '{metadata.get('case_name', 'NULL')}'")
            print(f"  Court: '{metadata.get('court', 'NULL')}'")
            print(f"  Judge: '{metadata.get('judge_name', 'NULL')}'")
            print(f"  Assigned: '{metadata.get('assigned_to', 'NULL')}'")
            print(f"  Filed: '{metadata.get('date_filed', 'NULL')}'")
        
        # Overall intelligibility estimate
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN 
                    metadata->>'case_name' IS NOT NULL AND 
                    LENGTH(metadata->>'case_name') BETWEEN 5 AND 150 AND
                    metadata->>'case_name' NOT LIKE '%?%'
                THEN 1 END) as clean_cases,
                COUNT(CASE WHEN 
                    metadata->>'court' IS NOT NULL AND 
                    LENGTH(metadata->>'court') BETWEEN 2 AND 10
                THEN 1 END) as valid_courts
            FROM public.court_documents
            WHERE metadata IS NOT NULL
        """)
        
        quality = cur.fetchone()
        
        print("\n\nOVERALL METADATA INTELLIGIBILITY:")
        print("="*60)
        print(f"Documents with clean case names: {quality['clean_cases']:,}/{quality['total']:,} ({quality['clean_cases']/quality['total']*100:.1f}%)")
        print(f"Documents with valid court codes: {quality['valid_courts']:,}/{quality['total']:,} ({quality['valid_courts']/quality['total']*100:.1f}%)")
        
        intelligibility = min(quality['clean_cases']/quality['total']*100, quality['valid_courts']/quality['total']*100)
        print(f"\nEstimated metadata intelligibility: {intelligibility:.1f}%")
        
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    analyze_metadata_quality()