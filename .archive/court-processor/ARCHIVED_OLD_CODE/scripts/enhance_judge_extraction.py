#!/usr/bin/env python3
"""
Simple enhancement to extract judges from metadata for dockets
Demonstrates the fix needed in the pipeline
"""
import sys
sys.path.append('/app')

from services.database import get_db_connection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def enhance_judge_extraction():
    """Add judge extraction from metadata where missing"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("ENHANCING JUDGE EXTRACTION FROM METADATA")
    print("=" * 80)
    
    # Find dockets with judges in metadata but not extracted
    cursor.execute("""
        SELECT 
            id,
            case_number,
            document_type,
            metadata,
            metadata->>'assigned_to' as assigned_judge
        FROM public.court_documents
        WHERE document_type IN ('docket', 'recap_docket', 'civil_case')
        AND metadata->>'assigned_to' IS NOT NULL
        AND (
            metadata->>'judge_enhanced' IS NULL 
            OR metadata->>'judge_enhanced' = 'false'
        )
        LIMIT 20
    """)
    
    documents_to_update = []
    
    for row in cursor.fetchall():
        doc_id, case_num, doc_type, metadata, assigned_judge = row
        
        print(f"\nDocument: {case_num} ({doc_type})")
        print(f"  Judge in metadata: {assigned_judge}")
        
        # Clean up judge name if needed
        clean_judge = assigned_judge
        if 'courtlistener.com' in str(assigned_judge):
            # Extract from URL
            parts = assigned_judge.strip('/').split('/')
            if parts:
                clean_judge = parts[-1].replace('-', ' ').title()
        
        # Prepare update
        documents_to_update.append({
            'id': doc_id,
            'case': case_num,
            'original': assigned_judge,
            'cleaned': clean_judge
        })
        
        print(f"  Will extract as: {clean_judge}")
    
    # Apply updates
    if documents_to_update:
        print(f"\n\nUpdating {len(documents_to_update)} documents...")
        
        for doc in documents_to_update:
            # Add judge extraction to metadata
            cursor.execute("""
                UPDATE public.court_documents
                SET metadata = metadata || jsonb_build_object(
                    'judge_enhanced', true,
                    'judge_name', %s,
                    'judge_source', 'metadata.assigned_to',
                    'judge_extraction_method', 'metadata'
                )
                WHERE id = %s
            """, (doc['cleaned'], doc['id']))
        
        conn.commit()
        print(f"✅ Updated {len(documents_to_update)} documents with judge information")
        
        # Show results
        print("\nUPDATED DOCUMENTS:")
        for doc in documents_to_update[:5]:
            print(f"  - {doc['case']}: {doc['cleaned']}")
            if doc['original'] != doc['cleaned']:
                print(f"    (cleaned from: {doc['original']})")
    else:
        print("\nNo documents need judge extraction enhancement")
    
    cursor.close()
    conn.close()
    
    return len(documents_to_update)


def demonstrate_proper_extraction():
    """Show how the pipeline should handle different document types"""
    
    print("\n" + "="*80)
    print("PROPER EXTRACTION STRATEGY BY DOCUMENT TYPE")
    print("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get examples of each type
    examples = {}
    
    for doc_type in ['opinion', 'docket', 'recap_docket', 'civil_case']:
        cursor.execute("""
            SELECT 
                case_number,
                LENGTH(COALESCE(content, '')) as content_len,
                metadata->>'assigned_to' as metadata_judge,
                metadata->>'judge_enhanced' as is_enhanced,
                metadata->>'judge_name' as extracted_judge
            FROM public.court_documents
            WHERE document_type = %s
            LIMIT 1
        """, (doc_type,))
        
        row = cursor.fetchone()
        if row:
            examples[doc_type] = {
                'case': row[0],
                'content_len': row[1],
                'metadata_judge': row[2],
                'is_enhanced': row[3],
                'extracted_judge': row[4]
            }
    
    # Show proper strategy for each
    for doc_type, data in examples.items():
        print(f"\n{doc_type.upper()}:")
        print(f"  Case: {data['case']}")
        print(f"  Content length: {data['content_len']:,} chars")
        print(f"  Judge in metadata: {data['metadata_judge'] or 'None'}")
        print(f"  Currently extracted: {data['extracted_judge'] or 'None'}")
        
        # Recommend strategy
        if doc_type == 'opinion' and data['content_len'] > 5000:
            print("  ✅ Strategy: Extract from content (look for signature, 'Before:', etc.)")
            print("  ✅ Run citation extraction (expect 20-50 citations)")
        elif doc_type in ['docket', 'recap_docket', 'civil_case']:
            print("  ✅ Strategy: Extract from metadata.assigned_to")
            print("  ❌ Skip citation extraction (no legal text)")
            if data['metadata_judge'] and not data['extracted_judge']:
                print("  ⚠️  MISSING: Should extract judge from metadata!")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    # First enhance existing documents
    updated_count = enhance_judge_extraction()
    
    # Then demonstrate proper strategies
    demonstrate_proper_extraction()
    
    print(f"\n\nSUMMARY: Enhanced {updated_count} documents with judge extraction from metadata")