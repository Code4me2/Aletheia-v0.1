#!/usr/bin/env python3
"""
Load real CourtListener docket data into PostgreSQL court_documents table
"""

import json
import psycopg2
from psycopg2.extras import Json
import os
from datetime import datetime
from pathlib import Path

# Database configuration
DB_CONFIG = {
    'host': 'db',  # Docker service name
    'port': 5432,
    'database': 'aletheia',
    'user': 'aletheia',
    'password': 'aletheia123'
}

def load_real_dockets():
    """Load real docket data from CourtListener into PostgreSQL"""
    
    # Check both possible data files
    data_files = [
        'test_data/recap_real/recap_real_data.json',
        'test_data/recap_real_paginated/recap_paginated_data.json'
    ]
    
    # Find the most recent file with data
    data = None
    for file_path in data_files:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                temp_data = json.load(f)
                if temp_data.get('dockets'):
                    data = temp_data
                    print(f"Loading data from {file_path}")
                    break
    
    if not data or not data.get('dockets'):
        print("No docket data found to load")
        return
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print(f"Loading {len(data['dockets'])} real dockets from CourtListener...")
    
    documents_added = 0
    
    # Process each docket
    for docket in data['dockets']:
        try:
            # Create a document record for each docket
            # Since we don't have actual document content, we'll create placeholder records
            
            case_number = docket.get('docket_number', f"DOCKET-{docket['id']}")
            case_name = docket.get('case_name', 'Unknown Case')
            court = docket.get('court_id', 'unknown')
            
            # Determine document type based on nature of suit
            nature_of_suit = docket.get('nature_of_suit', '')
            if nature_of_suit in ['830', '835']:
                doc_type = 'patent_case'
            elif nature_of_suit in ['820', '840']:
                doc_type = 'trademark_case'
            elif nature_of_suit in ['440', '441', '442', '443']:
                doc_type = 'civil_rights_case'
            else:
                doc_type = 'civil_case'
            
            # Create document content from available information
            content = f"""Case: {case_name}
Docket Number: {case_number}
Court: {court.upper()}
Filed: {docket.get('date_filed', 'Unknown')}
Judge: {docket.get('assigned_to_str', 'Not assigned')}
Nature of Suit: {nature_of_suit} - {docket.get('cause', 'Not specified')}

[This is a docket entry from CourtListener. Document details require paid API access.]

Case Status: {'Terminated' if docket.get('date_terminated') else 'Active'}
Last Filing: {docket.get('date_last_filing', 'Unknown')}
"""
            
            # Prepare comprehensive metadata
            metadata = {
                'source': 'courtlistener_api',
                'fetch_date': data.get('fetch_date'),
                'docket_id': docket['id'],
                'case_name': case_name,
                'case_name_short': docket.get('case_name_short', ''),
                'court': court,
                'court_id': docket.get('court_id'),
                'docket_number': case_number,
                'docket_number_core': docket.get('docket_number_core'),
                'date_filed': docket.get('date_filed'),
                'date_terminated': docket.get('date_terminated'),
                'date_last_filing': docket.get('date_last_filing'),
                'nature_of_suit': nature_of_suit,
                'cause': docket.get('cause', ''),
                'jury_demand': docket.get('jury_demand', ''),
                'jurisdiction_type': docket.get('jurisdiction_type', ''),
                'assigned_to': docket.get('assigned_to_str', ''),
                'assigned_to_id': docket.get('assigned_to'),
                'referred_to': docket.get('referred_to_str', ''),
                'pacer_case_id': docket.get('pacer_case_id'),
                'absolute_url': f"https://www.courtlistener.com{docket.get('absolute_url', '')}",
                'blocked': docket.get('blocked', False),
                'is_real_data': True
            }
            
            # Insert into court_documents
            cursor.execute("""
                INSERT INTO court_documents (
                    case_number, document_type, file_path, content, metadata, processed
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                case_number,
                doc_type,
                '',  # No file path for API data
                content,
                Json(metadata),
                False
            ))
            
            documents_added += 1
            
        except Exception as e:
            print(f"Error inserting docket {docket.get('id')}: {e}")
            conn.rollback()
            continue
    
    # Commit changes
    conn.commit()
    
    print(f"\nSuccessfully loaded {documents_added} real dockets into court_documents table")
    
    # Show summary by type
    cursor.execute("""
        SELECT document_type, COUNT(*) as count 
        FROM court_documents 
        GROUP BY document_type 
        ORDER BY count DESC
    """)
    results = cursor.fetchall()
    
    print("\nDocument counts by type:")
    for doc_type, count in results:
        print(f"  {doc_type}: {count}")
    
    # Show sample of loaded data
    cursor.execute("""
        SELECT case_number, 
               metadata->>'case_name' as case_name,
               metadata->>'court' as court,
               metadata->>'date_filed' as date_filed
        FROM court_documents 
        WHERE metadata->>'is_real_data' = 'true'
        LIMIT 5
    """)
    samples = cursor.fetchall()
    
    print("\nSample of loaded real cases:")
    for case_num, name, court, filed in samples:
        print(f"  {case_num}: {name[:50]}...")
        print(f"    Court: {court} | Filed: {filed}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    load_real_dockets()