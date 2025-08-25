#!/usr/bin/env python3
"""
Verify judge extraction is missing metadata judges
"""
import sys
sys.path.append('/app')

from services.database import get_db_connection
import json

def verify_judge_extraction():
    """Check which dockets have judges in metadata but not in extracted data"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("JUDGE EXTRACTION VERIFICATION")
    print("=" * 80)
    
    # Get recent docket documents
    cursor.execute("""
        SELECT 
            cd.id,
            cd.case_number,
            cd.document_type,
            cd.metadata,
            cd.metadata->>'judge_enhanced' as judge_enhanced,
            cd.metadata->>'judge_name' as extracted_judge
        FROM public.court_documents cd
        WHERE cd.document_type IN ('docket', 'recap_docket')
        AND cd.updated_at > NOW() - INTERVAL '1 hour'
        ORDER BY cd.id DESC
        LIMIT 20
    """)
    
    missing_judges = []
    found_judges = []
    
    for row in cursor.fetchall():
        doc_id, case_num, doc_type, metadata, judge_enhanced, extracted_judge = row
        
        # Check metadata for judge
        judge_in_metadata = None
        if isinstance(metadata, dict):
            judge_in_metadata = (
                metadata.get('assigned_to') or 
                metadata.get('assigned_to_str') or
                metadata.get('judge')
            )
        
        print(f"\nDocument: {case_num} (ID: {doc_id})")
        print(f"  Type: {doc_type}")
        print(f"  Judge in metadata: {judge_in_metadata}")
        print(f"  Judge enhanced: {judge_enhanced}")
        print(f"  Extracted judge: {extracted_judge}")
        
        if judge_in_metadata and not extracted_judge:
            missing_judges.append({
                'id': doc_id,
                'case': case_num,
                'metadata_judge': judge_in_metadata
            })
            print("  ❌ MISSING: Judge in metadata but not extracted!")
        elif extracted_judge:
            found_judges.append({
                'id': doc_id,
                'case': case_num,
                'extracted': extracted_judge
            })
            print("  ✅ FOUND: Judge was extracted")
        else:
            print("  ⚠️  No judge in metadata or extraction")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total dockets checked: {len(missing_judges) + len(found_judges)}")
    print(f"Judges found: {len(found_judges)}")
    print(f"Judges missed: {len(missing_judges)}")
    
    if missing_judges:
        print("\nMISSED JUDGES:")
        for doc in missing_judges:
            print(f"  - {doc['case']}: {doc['metadata_judge']}")
    
    # Check a specific document in detail
    if missing_judges:
        print("\n" + "=" * 80)
        print("DETAILED ANALYSIS OF FIRST MISSED JUDGE")
        print("=" * 80)
        
        doc_id = missing_judges[0]['id']
        cursor.execute("""
            SELECT metadata::text
            FROM public.court_documents
            WHERE id = %s
        """, (doc_id,))
        
        metadata_str = cursor.fetchone()[0]
        print(f"\nFull metadata for document {missing_judges[0]['case']}:")
        
        try:
            metadata = json.loads(metadata_str)
            # Pretty print relevant fields
            relevant_fields = ['assigned_to', 'assigned_to_str', 'judge', 'judges', 
                             'judge_enhanced', 'judge_name', 'cl_id']
            
            for field in relevant_fields:
                if field in metadata:
                    print(f"  {field}: {metadata[field]}")
        except:
            print("  [Could not parse metadata]")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    verify_judge_extraction()