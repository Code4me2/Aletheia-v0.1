#!/usr/bin/env python3
"""
Load sample court data into PostgreSQL court_documents table
"""

import json
import psycopg2
from psycopg2.extras import Json
import os
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'db',  # Docker service name
    'port': 5432,
    'database': 'aletheia',
    'user': 'aletheia',
    'password': 'aletheia123'
}

def load_sample_data():
    """Load sample court data from JSON file"""
    
    # Load the sample data
    sample_file = 'test_data/recap/sample_fetched_data.json'
    with open(sample_file, 'r') as f:
        data = json.load(f)
    
    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print(f"Loading data from {sample_file}...")
    
    # Process each docket
    documents_added = 0
    for docket in data.get('dockets', []):
        docket_id = docket['id']
        case_name = docket['case_name']
        case_number = docket.get('docket_number', f"DOCKET-{docket_id}")
        court = docket.get('court', 'unknown')
        
        # Process documents for this docket
        for doc in data.get('documents', []):
            # Create document record
            try:
                # Prepare document data
                doc_type = 'transcript' if 'transcript' in doc.get('description', '').lower() else 'document'
                
                # Create a mock content if not available
                content = doc.get('plain_text') or f"[Document content not available. Description: {doc.get('description', 'No description')}]"
                
                # Prepare metadata
                metadata = {
                    'docket_id': docket_id,
                    'case_name': case_name,
                    'court': court,
                    'document_id': doc['id'],
                    'docket_entry': doc.get('docket_entry'),
                    'document_number': doc.get('document_number'),
                    'description': doc.get('description'),
                    'page_count': doc.get('page_count', 0),
                    'date_filed': doc.get('date_filed'),
                    'is_available': doc.get('is_available', False),
                    'nature_of_suit': docket.get('nature_of_suit')
                }
                
                # Insert into court_documents
                cursor.execute("""
                    INSERT INTO court_documents (
                        case_number, document_type, file_path, content, metadata, processed
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_number,
                    doc_type,
                    doc.get('filepath_local', ''),
                    content,
                    Json(metadata),
                    False
                ))
                
                documents_added += 1
                
            except Exception as e:
                print(f"Error inserting document {doc.get('id')}: {e}")
                conn.rollback()
                continue
    
    # Also add some more diverse documents from the sample data
    if 'transcripts' in data:
        for transcript in data.get('transcripts', [])[:5]:  # Add first 5 transcripts
            try:
                case_number = f"TRANSCRIPT-{transcript.get('docket_id', 'unknown')}"
                content = f"[Transcript: {transcript.get('description', 'Court transcript')}. Case: {transcript.get('case_name', 'Unknown case')}]"
                
                metadata = {
                    'docket_id': transcript.get('docket_id'),
                    'case_name': transcript.get('case_name'),
                    'court': transcript.get('court'),
                    'document_id': transcript.get('document_id'),
                    'description': transcript.get('description'),
                    'date_filed': transcript.get('date_filed'),
                    'page_count': transcript.get('page_count', 0),
                    'is_transcript': True
                }
                
                cursor.execute("""
                    INSERT INTO court_documents (
                        case_number, document_type, file_path, content, metadata, processed
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    case_number,
                    'transcript',
                    '',
                    content,
                    Json(metadata),
                    False
                ))
                
                documents_added += 1
                
            except Exception as e:
                print(f"Error inserting transcript: {e}")
                conn.rollback()
                continue
    
    # Commit changes
    conn.commit()
    
    print(f"\nSuccessfully loaded {documents_added} documents into court_documents table")
    
    # Show summary
    cursor.execute("SELECT COUNT(*), document_type FROM court_documents GROUP BY document_type")
    results = cursor.fetchall()
    
    print("\nDocument counts by type:")
    for count, doc_type in results:
        print(f"  {doc_type}: {count}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    load_sample_data()