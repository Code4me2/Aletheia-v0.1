#!/usr/bin/env python3
"""
Test FLP tools with correct API usage
"""
import json
from datetime import datetime

def test_eyecite_proper():
    """Test Eyecite with correct API"""
    print("\n=== Testing Eyecite (Fixed) ===")
    try:
        import eyecite
        
        test_text = """
        This case follows Brown v. Board of Education, 347 U.S. 483 (1954) and 
        cites to Marbury v. Madison, 5 U.S. 137 (1803). See also Smith v. Jones, 
        123 F.3d 456 (9th Cir. 1999) and 42 U.S.C. § 1983.
        """
        
        # Get citations
        citations = eyecite.get_citations(test_text)
        
        print(f"✓ Found {len(citations)} citations:")
        for cite in citations:
            # Different citation types have different attributes
            if hasattr(cite, 'reporter_found'):
                print(f"  - {cite}: {cite.reporter_found} vol. {cite.reporter.volume} p. {cite.reporter.page}")
            else:
                print(f"  - {cite}: {type(cite).__name__}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_xray_proper():
    """Test X-Ray with correct API"""
    print("\n=== Testing X-Ray (Fixed) ===")
    try:
        import x_ray
        
        print("✓ X-Ray module loaded")
        print(f"  - Module location: {x_ray.__file__}")
        
        # List available functions
        available = [attr for attr in dir(x_ray) if not attr.startswith('_')]
        print(f"  - Available functions: {', '.join(available[:5])}")
        
        # X-Ray is primarily for PDF analysis
        print("  - Primary use: PDF quality analysis")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_judge_pics_proper():
    """Test Judge Pics with correct API"""
    print("\n=== Testing Judge Pics (Fixed) ===")
    try:
        import judge_pics
        
        print("✓ Judge Pics module loaded")
        
        # The correct way to search
        results = judge_pics.search("Roberts", "Supreme Court")
        
        if results:
            print(f"  - Found {len(results)} matches for 'Roberts'")
            judge = results[0]
            print(f"  - First match: {judge['name']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_courts_db_proper():
    """Test Courts-DB with correct API"""
    print("\n=== Testing Courts-DB (Fixed) ===")
    try:
        import courts_db
        
        # Find court by ID
        court = courts_db.find_court_by_id("scotus")
        if court:
            print(f"✓ Found SCOTUS: {court['name']}")
        
        # Search for courts
        results = courts_db.find_court("Southern District")
        print(f"✓ Found {len(results)} courts matching 'Southern District'")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_reporters_db_proper():
    """Test Reporters-DB with correct API"""
    print("\n=== Testing Reporters-DB (Fixed) ===")
    try:
        from reporters_db import REPORTERS
        
        # Check some common reporters
        test_reporters = ["U.S.", "F.3d", "F. Supp.", "S. Ct."]
        
        found = 0
        for test_rep in test_reporters:
            for reporter_key, editions in REPORTERS.items():
                for edition in editions:
                    if isinstance(edition, dict) and test_rep in str(edition.get('cite_type', '')):
                        print(f"✓ Found '{test_rep}' → {edition.get('name', reporter_key)}")
                        found += 1
                        break
        
        print(f"✓ Total reporters in database: {len(REPORTERS)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def main():
    """Run all corrected tests"""
    print("=" * 60)
    print("FLP Tools API Test (Corrected)")
    print(f"Time: {datetime.now()}")
    print("=" * 60)
    
    # Run tests
    results = []
    results.append(("Courts-DB", test_courts_db_proper()))
    results.append(("Reporters-DB", test_reporters_db_proper()))
    results.append(("Eyecite", test_eyecite_proper()))
    results.append(("X-Ray", test_xray_proper()))
    results.append(("Judge Pics", test_judge_pics_proper()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")
    
    print(f"\nTotal: {passed}/{total} components working")

if __name__ == "__main__":
    main()