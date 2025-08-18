#!/usr/bin/env python3
"""
Test script for court processor
Run this to verify everything is working correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from processor import CourtProcessor
from pdf_processor import PDFProcessor

logging.basicConfig(level=logging.INFO)

def test_pdf_processor():
    """Test PDF processing functionality"""
    print("\n=== Testing PDF Processor ===")
    processor = PDFProcessor()
    
    # Test with a sample PDF if available
    test_pdf = "/data/pdfs/test.pdf"
    if os.path.exists(test_pdf):
        text, metadata = processor.process_pdf(test_pdf)
        print(f"Extracted {len(text)} characters")
        print(f"Metadata: {metadata}")
    else:
        print("No test PDF found at /data/pdfs/test.pdf")

def test_database_connection():
    """Test database connectivity"""
    print("\n=== Testing Database Connection ===")
    processor = CourtProcessor()
    
    try:
        conn = processor.get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            result = cur.fetchone()
            print(f"Database connection successful: {result}")
            
            # Check if schema exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.schemata 
                    WHERE schema_name = 'court_data'
                )
            """)
            schema_exists = cur.fetchone()[0]
            print(f"court_data schema exists: {schema_exists}")
            
            if schema_exists:
                # Get table info
                cur.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'court_data'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cur.fetchall()]
                print(f"Tables in court_data: {tables}")
                
                # Get judge count
                cur.execute("SELECT COUNT(*) FROM court_data.judges")
                judge_count = cur.fetchone()[0]
                print(f"Number of judges: {judge_count}")
                
                # Get opinion count
                cur.execute("SELECT COUNT(*) FROM court_data.opinions")
                opinion_count = cur.fetchone()[0]
                print(f"Number of opinions: {opinion_count}")
            
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")

def test_judge_normalization():
    """Test judge name normalization"""
    print("\n=== Testing Judge Name Normalization ===")
    processor = CourtProcessor()
    
    test_names = [
        "Smith",
        "Judge Smith",
        "JUDGE SMITH",
        "  Judge   Smith  ",
        "",
        None
    ]
    
    for name in test_names:
        normalized = processor.normalize_judge_name(name)
        print(f"'{name}' -> '{normalized}'")

def test_court_config():
    """Test court configuration loading"""
    print("\n=== Testing Court Configuration ===")
    processor = CourtProcessor()
    
    courts = processor.config.get('courts', {})
    print(f"Configured courts: {list(courts.keys())}")
    
    for court_code, config in courts.items():
        active = config.get('active', False)
        print(f"  {court_code}: {config.get('name')} (active: {active})")

if __name__ == "__main__":
    print("Court Processor Test Suite")
    print("=" * 50)
    
    test_court_config()
    test_database_connection()
    test_judge_normalization()
    test_pdf_processor()
    
    print("\n" + "=" * 50)
    print("Tests completed!")
    print("\nTo run a test scrape:")
    print("  python processor.py --court tax")
    print("\nTo initialize the database:")
    print("  python processor.py --init-db")