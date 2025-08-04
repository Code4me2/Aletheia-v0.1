#!/usr/bin/env python3
"""
Test Texas court processing specifically
"""
from services.database import get_db_connection
import json

def analyze_texas_courts():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("TEXAS COURT DOCUMENT ANALYSIS")
    print("=" * 80)
    
    # 1. Check document structure for Texas courts
    cursor.execute("""
        SELECT 
            id,
            case_number,
            document_type,
            LENGTH(COALESCE(content, '')) as content_length,
            metadata->>'court' as court,
            metadata->>'court_id' as court_id,
            metadata->>'assigned_to' as assigned_to,
            metadata->>'nature_of_suit' as nature_of_suit
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
        ORDER BY 
            CASE 
                WHEN document_type = 'opinion' THEN 1
                WHEN document_type = 'civil_case' THEN 2
                ELSE 3
            END,
            created_at DESC
        LIMIT 20
    """)
    
    print("\nE.D. Texas Documents Sample:")
    print("-" * 120)
    print(f"{'ID':<6} {'Case Number':<20} {'Type':<12} {'Content':<8} {'Court':<15} {'Court_ID':<10} {'Judge':<20} {'Nature':<10}")
    print("-" * 120)
    
    texas_docs = []
    for row in cursor.fetchall():
        doc_id, case_num, doc_type, content_len, court, court_id, judge, nature = row
        texas_docs.append(row)
        case_num_short = (case_num or 'N/A')[:20]
        judge_short = (judge or 'N/A')[:20]
        print(f"{doc_id:<6} {case_num_short:<20} {doc_type:<12} {content_len:<8} {court or '':<15} {court_id or '':<10} {judge_short:<20} {nature or '':<10}")
    
    # 2. Check for different content structures
    print("\n\nContent Structure Analysis:")
    print("-" * 80)
    
    for doc in texas_docs[:5]:
        doc_id = doc[0]
        cursor.execute("""
            SELECT content, metadata
            FROM public.court_documents
            WHERE id = %s
        """, (doc_id,))
        
        content, metadata = cursor.fetchone()
        print(f"\nDocument ID {doc_id}:")
        
        if content:
            if isinstance(content, str):
                print(f"  Content type: string")
                print(f"  Content preview: {content[:100]}...")
            elif isinstance(content, dict):
                print(f"  Content type: dict")
                print(f"  Content keys: {list(content.keys())}")
            else:
                print(f"  Content type: {type(content)}")
        else:
            print("  No content")
            
        if metadata:
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    pass
            
            if isinstance(metadata, dict):
                print(f"  Metadata keys: {list(metadata.keys())[:10]}...")
                if 'recap_documents' in metadata:
                    print(f"  RECAP documents: {len(metadata['recap_documents'])}")
                if 'download_url' in metadata or 'pdf_url' in metadata:
                    print(f"  Has PDF URL")
    
    # 3. Check cl_id field
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(metadata->>'cl_id') as has_cl_id,
            COUNT(CASE WHEN metadata->>'cl_id' IS NOT NULL THEN 1 END) as valid_cl_id
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
    """)
    
    total, has_cl_id, valid_cl_id = cursor.fetchone()
    print(f"\n\nCL_ID Field Analysis:")
    print(f"  Total Texas docs: {total}")
    print(f"  Has cl_id field: {has_cl_id}")
    print(f"  Valid cl_id: {valid_cl_id}")
    
    # 4. Check nature of suit for IP cases
    cursor.execute("""
        SELECT 
            metadata->>'nature_of_suit' as nos,
            COUNT(*) as count
        FROM public.court_documents
        WHERE metadata::text LIKE '%txed%'
        AND metadata->>'nature_of_suit' IS NOT NULL
        GROUP BY nos
        ORDER BY count DESC
    """)
    
    print(f"\n\nNature of Suit Distribution:")
    print("-" * 40)
    for row in cursor.fetchall():
        nos, count = row
        print(f"  {nos}: {count}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_texas_courts()