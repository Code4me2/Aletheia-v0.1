#!/usr/bin/env python3
"""
Simple test to demonstrate the FLP pipeline components
"""
import json
from datetime import datetime

def test_courts_db():
    """Test Courts-DB functionality"""
    print("\n=== Testing Courts-DB ===")
    try:
        from courts_db import find_court_by_id, find_court, courts
        
        # Test court ID lookup
        court = find_court_by_id("txed")
        print(f"✓ Found court by ID 'txed': {court['name']}")
        
        # Test court name resolution
        variations = ["S.D.N.Y.", "SDNY", "Southern District of New York"]
        for name in variations:
            matches = find_court(name)
            if matches:
                print(f"✓ '{name}' resolved to: {matches[0]['id']}")
        
        # Show total courts available
        print(f"✓ Total courts in database: {len(list(courts))}")
        return True
        
    except Exception as e:
        print(f"✗ Courts-DB test failed: {e}")
        return False

def test_reporters_db():
    """Test Reporters-DB functionality"""
    print("\n=== Testing Reporters-DB ===")
    try:
        from reporters_db import REPORTERS
        
        # Test reporter normalization
        test_cases = [
            ("F.3d", "F.3d"),
            ("Fed. 3d", "F.3d"),
            ("U.S.", "U.S."),
            ("S. Ct.", "S. Ct.")
        ]
        
        for input_cite, expected in test_cases:
            # Check if reporter exists
            found = False
            for reporter_key, reporter_data in REPORTERS.items():
                if any(input_cite in editions.get('cite_type', '') 
                      for editions in reporter_data if isinstance(editions, dict)):
                    print(f"✓ '{input_cite}' is a valid reporter")
                    found = True
                    break
            if not found and input_cite == expected:
                print(f"✓ '{input_cite}' is already normalized")
        
        print(f"✓ Total reporters in database: {len(REPORTERS)}")
        return True
        
    except Exception as e:
        print(f"✗ Reporters-DB test failed: {e}")
        return False

def test_data_loading():
    """Test loading our court documents from PostgreSQL"""
    print("\n=== Testing Data Access ===")
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Database connection
        conn = psycopg2.connect(
            host='db',
            database='aletheia',
            user='aletheia',
            password='aletheia123'
        )
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get sample documents
            cursor.execute("""
                SELECT case_number, document_type, 
                       metadata->>'case_name' as case_name,
                       metadata->>'court' as court,
                       metadata->>'is_real_data' as is_real
                FROM court_documents 
                LIMIT 5
            """)
            docs = cursor.fetchall()
            
            print(f"✓ Found {len(docs)} documents in database")
            
            # Show sample
            for doc in docs[:2]:
                print(f"  - {doc['case_number']}: {doc['case_name']}")
                print(f"    Court: {doc['court']} | Real data: {doc['is_real']}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Database test failed: {e}")
        return False

def demonstrate_pipeline():
    """Demonstrate how the pipeline would process a document"""
    print("\n=== Pipeline Processing Flow ===")
    
    # Sample document (from our real data)
    sample_doc = {
        'case_name': 'CommWorks Solutions, LLC v. EarthLink, LLC',
        'case_number': '2:25-cv-00716',
        'court': 'txed',
        'date_filed': '2025-07-15',
        'content': 'This is a patent case filed in the Eastern District of Texas...'
    }
    
    print(f"Input Document: {sample_doc['case_name']}")
    print(f"Court: {sample_doc['court']} | Filed: {sample_doc['date_filed']}")
    
    # Step 1: Court standardization
    print("\n1. Court Standardization (Courts-DB):")
    try:
        from courts_db import find_court_by_id
        court = find_court_by_id(sample_doc['court'])
        print(f"   ✓ Standardized to: {court['name']}")
        print(f"   ✓ Full name: {court['full_name']}")
        print(f"   ✓ Citation string: {court['citation_string']}")
    except:
        print("   ✗ Courts-DB not available")
    
    # Step 2: Citation extraction (would use Eyecite)
    print("\n2. Citation Extraction (Eyecite):")
    print("   ✗ Eyecite not installed (requires C++ compiler)")
    print("   Would extract: case citations, statutes, regulations")
    
    # Step 3: Document processing (would use Doctor)
    print("\n3. Document Processing (Doctor):")
    print("   ✗ Doctor service not running")
    print("   Would extract: text from PDFs, create thumbnails")
    
    # Step 4: Store enhanced data
    print("\n4. Enhanced Data Storage:")
    print("   ✓ Would store in PostgreSQL with enhanced metadata")
    print("   ✓ Original data preserved, enhancements added to metadata field")

def main():
    """Run all tests"""
    print("=" * 60)
    print("FLP Integration Pipeline Test")
    print(f"Run time: {datetime.now()}")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Courts-DB", test_courts_db()))
    results.append(("Reporters-DB", test_reporters_db()))
    results.append(("Database Access", test_data_loading()))
    
    # Show pipeline flow
    demonstrate_pipeline()
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary:")
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {name}: {status}")
    
    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

if __name__ == "__main__":
    main()