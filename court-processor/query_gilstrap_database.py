#!/usr/bin/env python3
"""
Query the database to see what Judge Gilstrap documents we have
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# Database configuration
DB_CONFIG = {
    'host': 'db',
    'database': 'aletheia',
    'user': 'aletheia',
    'password': 'aletheia123'
}

def query_gilstrap_documents():
    """Query Judge Gilstrap documents in database"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Overall stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_docs,
                    MIN(metadata->>'date_filed') as earliest_date,
                    MAX(metadata->>'date_filed') as latest_date,
                    AVG(LENGTH(content)) as avg_content_length,
                    SUM(LENGTH(content)) as total_content_chars
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                AND content IS NOT NULL
            """)
            
            stats = cursor.fetchone()
            print("📊 JUDGE GILSTRAP DATABASE SUMMARY")
            print("=" * 50)
            print(f"Total documents: {stats['total_docs']}")
            print(f"Date range: {stats['earliest_date']} to {stats['latest_date']}")
            print(f"Total content: {stats['total_content_chars']:,} characters")
            print(f"Average content per document: {stats['avg_content_length']:,.0f} characters")
            
            # Yearly breakdown
            cursor.execute("""
                SELECT 
                    EXTRACT(YEAR FROM (metadata->>'date_filed')::date) as year,
                    COUNT(*) as count
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                AND metadata->>'date_filed' IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM (metadata->>'date_filed')::date)
                ORDER BY year
            """)
            
            yearly_data = cursor.fetchall()
            print(f"\n📅 YEARLY BREAKDOWN")
            print("-" * 20)
            for row in yearly_data:
                year = int(row['year']) if row['year'] else 'Unknown'
                count = row['count']
                print(f"{year}: {count} documents")
            
            # Document types
            cursor.execute("""
                SELECT 
                    document_type,
                    COUNT(*) as count
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                GROUP BY document_type
                ORDER BY count DESC
            """)
            
            doc_types = cursor.fetchall()
            print(f"\n📋 DOCUMENT TYPES")
            print("-" * 20)
            for row in doc_types:
                print(f"{row['document_type']}: {row['count']} documents")
            
            # Sample documents
            cursor.execute("""
                SELECT 
                    case_number,
                    metadata->>'case_name' as case_name,
                    metadata->>'date_filed' as date_filed,
                    LENGTH(content) as content_length
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                AND content IS NOT NULL
                ORDER BY (metadata->>'date_filed')::date DESC
                LIMIT 10
            """)
            
            sample_docs = cursor.fetchall()
            print(f"\n📄 SAMPLE DOCUMENTS (Most Recent)")
            print("-" * 50)
            for i, doc in enumerate(sample_docs, 1):
                case_name = doc['case_name'] or doc['case_number']
                date_filed = doc['date_filed'] or 'No date'
                content_length = doc['content_length']
                print(f"{i:2d}. {case_name}")
                print(f"    Date: {date_filed}, Content: {content_length:,} chars")
            
            # Content analysis
            cursor.execute("""
                SELECT 
                    case_number,
                    metadata->>'case_name' as case_name,
                    metadata->>'date_filed' as date_filed,
                    LEFT(content, 200) as content_preview
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                AND content IS NOT NULL
                ORDER BY (metadata->>'date_filed')::date DESC
                LIMIT 3
            """)
            
            content_samples = cursor.fetchall()
            print(f"\n📖 CONTENT SAMPLES")
            print("-" * 50)
            for i, doc in enumerate(content_samples, 1):
                case_name = doc['case_name'] or doc['case_number']
                date_filed = doc['date_filed'] or 'No date'
                preview = doc['content_preview'] or 'No content'
                print(f"{i}. {case_name} ({date_filed})")
                print(f"   Preview: {preview}...")
                print()
        
        conn.close()
        
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    query_gilstrap_documents()