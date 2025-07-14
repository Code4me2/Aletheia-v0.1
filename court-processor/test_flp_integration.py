#!/usr/bin/env python3
"""
Test script for Free Law Project integration
Tests all components without requiring Docker
"""
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all FLP packages can be imported"""
    print("Testing Free Law Project imports...")
    
    results = []
    
    # Test Courts-DB
    try:
        from courts_db import find_court, courts
        results.append(("Courts-DB", True, f"{len(courts)} courts loaded"))
    except Exception as e:
        results.append(("Courts-DB", False, str(e)))
    
    # Test Eyecite
    try:
        from eyecite import get_citations, clean_text
        test_text = "See Brown v. Board, 347 U.S. 483 (1954)"
        citations = get_citations(clean_text(test_text))
        results.append(("Eyecite", True, f"Found {len(citations)} citations in test"))
    except Exception as e:
        results.append(("Eyecite", False, str(e)))
    
    # Test Reporters-DB
    try:
        from reporters_db import REPORTERS, EDITIONS
        results.append(("Reporters-DB", True, f"{len(REPORTERS)} reporters loaded"))
    except Exception as e:
        results.append(("Reporters-DB", False, str(e)))
    
    # Test Judge-pics
    try:
        from judge_pics import search_judges
        results.append(("Judge-pics", True, "Import successful"))
    except Exception as e:
        results.append(("Judge-pics", False, str(e)))
    
    # Test X-Ray
    try:
        from xray import detect_bad_redactions
        results.append(("X-Ray", True, "Import successful"))
    except Exception as e:
        results.append(("X-Ray", False, str(e)))
    
    # Test Juriscraper
    try:
        import juriscraper
        results.append(("Juriscraper", True, f"Version {juriscraper.__version__}"))
    except Exception as e:
        results.append(("Juriscraper", False, str(e)))
    
    # Print results
    print("\n" + "="*60)
    print("Free Law Project Integration Test Results")
    print("="*60)
    
    for tool, success, message in results:
        status = "✅" if success else "❌"
        print(f"{status} {tool:15} - {message}")
    
    # Summary
    successful = sum(1 for _, success, _ in results if success)
    total = len(results)
    print(f"\n{successful}/{total} components loaded successfully")
    
    return successful == total

def test_court_resolution():
    """Test Courts-DB functionality"""
    print("\n\nTesting Court Resolution...")
    print("-"*40)
    
    try:
        from courts_db import find_court
        
        test_courts = [
            "S.D.N.Y.",
            "Southern District of New York",
            "9th Circuit",
            "Tax Court"
        ]
        
        for court_string in test_courts:
            court_ids = find_court(court_string)
            if court_ids:
                print(f"'{court_string}' → {court_ids[0]}")
            else:
                print(f"'{court_string}' → Not found")
                
    except Exception as e:
        print(f"Error testing court resolution: {e}")

def test_citation_extraction():
    """Test Eyecite functionality"""
    print("\n\nTesting Citation Extraction...")
    print("-"*40)
    
    try:
        from eyecite import get_citations, clean_text
        
        test_text = """
        The court in Brown v. Board of Education, 347 U.S. 483 (1954),
        held that segregation violates the Constitution. Id. at 495.
        See also Plessy v. Ferguson, 163 U.S. 537 (1896).
        """
        
        citations = get_citations(clean_text(test_text))
        print(f"Found {len(citations)} citations:")
        
        for i, citation in enumerate(citations, 1):
            print(f"{i}. {citation} (Type: {citation.__class__.__name__})")
            
    except Exception as e:
        print(f"Error testing citations: {e}")

def test_reporter_normalization():
    """Test Reporters-DB functionality"""
    print("\n\nTesting Reporter Normalization...")
    print("-"*40)
    
    try:
        from reporters_db import REPORTERS
        
        test_reporters = ["U.S.", "F.3d", "F. Supp.", "N.Y."]
        
        for reporter in test_reporters:
            # Simple lookup - in real usage would be more sophisticated
            found = False
            for key, data in REPORTERS.items():
                if reporter.lower() == key.lower():
                    print(f"'{reporter}' → {data.get('name', 'Unknown')}")
                    found = True
                    break
            if not found:
                print(f"'{reporter}' → Not found in exact match")
                
    except Exception as e:
        print(f"Error testing reporters: {e}")

def main():
    """Run all tests"""
    print("Free Law Project Integration Test Suite")
    print("="*60)
    
    # Test imports first
    if not test_imports():
        print("\n⚠️  Some imports failed. Install missing packages:")
        print("pip install courts-db eyecite reporters-db x-ray judge-pics juriscraper")
        return
    
    # Test individual components
    test_court_resolution()
    test_citation_extraction()
    test_reporter_normalization()
    
    print("\n\n✅ All tests completed!")
    print("\nNext steps:")
    print("1. Start Docker services: docker-compose up -d")
    print("2. Run API: python flp_api.py")
    print("3. Test endpoints: curl http://localhost:8090/health")

if __name__ == "__main__":
    main()