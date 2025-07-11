#!/usr/bin/env python3
"""
Test CourtListener data availability for Haystack integration
Shows how the data can be queried from PostgreSQL for RAG indexing
"""

import os
import psycopg2
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL')

def test_courtlistener_data():
    """Test querying CourtListener data from PostgreSQL"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    print("=== Testing CourtListener Data in PostgreSQL ===\n")
    
    # 1. Query unindexed opinions (similar to existing workflow)
    print("1. Querying unindexed CourtListener opinions:")
    cursor.execute("""
        SELECT 
            o.id,
            o.plain_text,
            o.author_str,
            o.date_created,
            d.case_name,
            d.docket_number,
            d.court_id,
            d.nature_of_suit,
            d.is_patent_case
        FROM court_data.cl_opinions o
        LEFT JOIN court_data.cl_dockets d ON o.docket_id = d.id
        WHERE o.vector_indexed = false 
        AND o.plain_text IS NOT NULL
        LIMIT 5
    """)
    
    opinions = cursor.fetchall()
    print(f"   Found {len(opinions)} unindexed opinions with text\n")
    
    if opinions:
        opinion = opinions[0]
        print(f"   Sample Opinion:")
        print(f"   - ID: {opinion[0]}")
        print(f"   - Case: {opinion[4]}")
        print(f"   - Docket: {opinion[5]}")
        print(f"   - Court: {opinion[6]}")
        print(f"   - Patent Case: {opinion[8]}")
        print(f"   - Text Preview: {opinion[1][:200]}...\n")
    
    # 2. Query using the unified view
    print("2. Querying unified opinion view (combines both sources):")
    cursor.execute("""
        SELECT source, COUNT(*) as count 
        FROM court_data.all_opinions 
        GROUP BY source
    """)
    
    sources = cursor.fetchall()
    for source, count in sources:
        print(f"   - {source}: {count} opinions")
    
    # 3. Query patent cases specifically
    print("\n3. Querying patent cases:")
    cursor.execute("""
        SELECT 
            COUNT(DISTINCT d.id) as patent_docket_count,
            COUNT(DISTINCT o.id) as patent_opinion_count
        FROM court_data.cl_dockets d
        LEFT JOIN court_data.cl_opinions o ON d.id = o.docket_id
        WHERE d.is_patent_case = true
    """)
    
    result = cursor.fetchone()
    print(f"   - Patent Dockets: {result[0]}")
    print(f"   - Patent Opinions: {result[1]}")
    
    # 4. Show how to format for Haystack
    print("\n4. Example data formatted for Haystack:")
    
    cursor.execute("""
        SELECT 
            o.id,
            json_build_object(
                'id', 'cl_opinion_' || o.id,
                'content', COALESCE(o.plain_text, o.html),
                'meta', json_build_object(
                    'source', 'courtlistener',
                    'court', d.court_id,
                    'case_name', d.case_name,
                    'docket_number', d.docket_number,
                    'date_created', o.date_created,
                    'author', o.author_str,
                    'is_patent_case', d.is_patent_case,
                    'nature_of_suit', d.nature_of_suit,
                    'url', o.absolute_url
                )
            ) as haystack_document
        FROM court_data.cl_opinions o
        LEFT JOIN court_data.cl_dockets d ON o.docket_id = d.id
        WHERE o.vector_indexed = false 
        AND (o.plain_text IS NOT NULL OR o.html IS NOT NULL)
        LIMIT 1
    """)
    
    result = cursor.fetchone()
    if result:
        print(f"   Opinion ID: {result[0]}")
        print(f"   Haystack Document:")
        print(json.dumps(result[1], indent=2)[:500] + "...")
    
    # 5. Show import statistics
    print("\n5. Import Statistics:")
    cursor.execute("""
        SELECT * FROM court_data.cl_import_stats
    """)
    
    stats = cursor.fetchall()
    for stat in stats:
        print(f"   Court: {stat[0]}")
        print(f"   - Dockets: {stat[1]}")
        print(f"   - Opinions: {stat[2]}")
        print(f"   - Patent Cases: {stat[3]}")
        print(f"   - Pending Index: {stat[4]}")
        print(f"   - Date Range: {stat[5]} to {stat[6]}")
    
    cursor.close()
    conn.close()
    
    print("\n✓ CourtListener data is successfully available in PostgreSQL!")
    print("  Ready for integration with existing court-to-Haystack workflow")

if __name__ == "__main__":
    test_courtlistener_data()