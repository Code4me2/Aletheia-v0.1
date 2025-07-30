#!/usr/bin/env python3
"""
Export all court documents data to CSV for analysis
Includes all columns and unpacks JSON metadata
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from psycopg2.extras import RealDictCursor
import csv
import json
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def export_all_data_to_csv():
    """Export all court documents data to a comprehensive CSV file"""
    
    conn = get_db_connection(cursor_factory=RealDictCursor)
    cur = conn.cursor()
    
    # Generate filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'court_documents_full_export_{timestamp}.csv'
    
    try:
        # First, get a sample to understand all possible metadata fields
        logger.info("Analyzing metadata structure...")
        cur.execute("""
            SELECT metadata 
            FROM public.court_documents 
            WHERE metadata IS NOT NULL 
            LIMIT 1000
        """)
        
        # Collect all unique metadata keys
        all_metadata_keys = set()
        for row in cur.fetchall():
            if row['metadata']:
                all_metadata_keys.update(row['metadata'].keys())
        
        metadata_keys = sorted(list(all_metadata_keys))
        logger.info(f"Found {len(metadata_keys)} unique metadata fields")
        
        # Get total count
        cur.execute("SELECT COUNT(*) as total FROM public.court_documents")
        total_docs = cur.fetchone()['total']
        logger.info(f"Exporting {total_docs:,} documents...")
        
        # Define all columns for CSV
        basic_columns = [
            'id', 'case_number', 'document_type', 'file_path', 
            'content_length', 'content_preview', 'processed', 
            'created_at', 'updated_at', 'case_name'
        ]
        
        # Add metadata columns with prefix
        metadata_columns = [f'meta_{key}' for key in metadata_keys]
        
        # All columns
        all_columns = basic_columns + metadata_columns
        
        # Open CSV file and write header
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=all_columns, extrasaction='ignore')
            writer.writeheader()
            
            # Fetch data in batches to avoid memory issues
            batch_size = 1000
            offset = 0
            
            while offset < total_docs:
                logger.info(f"Processing batch {offset//batch_size + 1} ({offset:,} - {min(offset + batch_size, total_docs):,})")
                
                cur.execute("""
                    SELECT 
                        id, 
                        case_number, 
                        document_type, 
                        file_path,
                        LENGTH(content) as content_length,
                        LEFT(content, 500) as content_preview,
                        processed,
                        created_at,
                        updated_at,
                        case_name,
                        metadata
                    FROM public.court_documents
                    ORDER BY id
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                
                for row in cur.fetchall():
                    # Create row dictionary with basic fields
                    csv_row = {
                        'id': row['id'],
                        'case_number': row['case_number'],
                        'document_type': row['document_type'],
                        'file_path': row['file_path'],
                        'content_length': row['content_length'],
                        'content_preview': row['content_preview'].replace('\n', ' ').replace('\r', ' ') if row['content_preview'] else '',
                        'processed': row['processed'],
                        'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                        'updated_at': row['updated_at'].isoformat() if row['updated_at'] else '',
                        'case_name': row['case_name']
                    }
                    
                    # Unpack metadata fields
                    if row['metadata']:
                        for key in metadata_keys:
                            value = row['metadata'].get(key, '')
                            # Convert non-string values to string
                            if isinstance(value, (dict, list)):
                                value = json.dumps(value)
                            elif value is None:
                                value = ''
                            csv_row[f'meta_{key}'] = str(value)
                    
                    writer.writerow(csv_row)
                
                offset += batch_size
        
        logger.info(f"Export complete! File saved as: {output_file}")
        
        # Get file size
        file_size = os.path.getsize(output_file) / (1024 * 1024)  # Convert to MB
        logger.info(f"File size: {file_size:.2f} MB")
        
        # Show summary of what was exported
        logger.info("\nExport Summary:")
        logger.info(f"Total documents: {total_docs:,}")
        logger.info(f"Basic columns: {len(basic_columns)}")
        logger.info(f"Metadata columns: {len(metadata_columns)}")
        logger.info(f"Total columns: {len(all_columns)}")
        
        # Sample metadata columns for reference
        logger.info("\nSample metadata columns included:")
        for key in metadata_keys[:20]:  # Show first 20
            logger.info(f"  - meta_{key}")
        if len(metadata_keys) > 20:
            logger.info(f"  ... and {len(metadata_keys) - 20} more")
        
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    export_all_data_to_csv()