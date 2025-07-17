#!/usr/bin/env python3
"""
Live test of RECAP integration with API key
"""
import asyncio
import os
import sys
from datetime import date, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the API key temporarily
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from services.courtlistener_service import CourtListenerService
from services.recap_processor import RECAPProcessor


async def test_live_api():
    """Test with real API calls"""
    print("=== Live RECAP API Test ===\n")
    
    cl_service = CourtListenerService()
    processor = RECAPProcessor()
    
    try:
        # Test 1: Basic connection with opinions
        print("1. Testing basic API connection...")
        opinions = await cl_service.fetch_opinions(
            court_id='ca9',
            date_filed_after='2024-11-01',
            max_results=2
        )
        print(f"✓ Connected! Found {len(opinions)} recent Ninth Circuit opinions")
        if opinions:
            print(f"  Example: {opinions[0].get('case_name', 'No name')[:60]}...")
        
        # Test 2: Fetch recent patent dockets from EDTX
        print("\n2. Fetching recent patent cases from E.D. Texas...")
        dockets = await cl_service.fetch_recap_dockets(
            court_ids=['txed'],
            date_filed_after='2024-11-01',
            nature_of_suit=['830'],  # Patent cases
            max_results=3
        )
        
        print(f"✓ Found {len(dockets)} patent dockets")
        
        if dockets:
            # Show first docket details
            docket = dockets[0]
            print(f"\n  Sample Docket:")
            print(f"    ID: {docket.get('id')}")
            print(f"    Case: {docket.get('case_name', 'No name')[:60]}...")
            print(f"    Court: {docket.get('court')}")
            print(f"    Nature of Suit: {docket.get('nature_of_suit')}")
            print(f"    Date Filed: {docket.get('date_filed')}")
            print(f"    Docket Number: {docket.get('docket_number')}")
            
            # Test 3: Fetch documents for this docket
            print(f"\n3. Fetching documents for docket {docket.get('id')}...")
            documents = await cl_service.fetch_recap_documents(docket.get('id'))
            
            print(f"✓ Found {len(documents)} documents")
            
            # Look for transcripts
            transcripts = []
            for doc in documents:
                if processor._is_transcript(doc):
                    transcripts.append(doc)
            
            print(f"  Including {len(transcripts)} potential transcripts")
            
            # Show first few documents
            for i, doc in enumerate(documents[:3]):
                print(f"\n  Document {i+1}:")
                print(f"    Doc ID: {doc.get('id')}")
                print(f"    Number: {doc.get('document_number')}")
                print(f"    Description: {doc.get('description', 'No description')[:60]}...")
                print(f"    Pages: {doc.get('page_count', 'Unknown')}")
                print(f"    Has PDF: {bool(doc.get('filepath_local'))}")
                print(f"    Is Transcript: {processor._is_transcript(doc)}")
        
        # Test 4: Search for recent trademark cases
        print("\n4. Searching for recent trademark cases...")
        search_results = await cl_service.search_recap(
            query='trademark infringement',
            court_ids=['txed', 'deld'],
            date_range=('2024-10-01', date.today().isoformat()),
            max_results=3
        )
        
        print(f"✓ Found {len(search_results)} search results")
        for i, result in enumerate(search_results):
            print(f"\n  Result {i+1}:")
            print(f"    Case: {result.get('caseName', 'No name')[:60]}...")
            print(f"    Court: {result.get('court')}")
            print(f"    Date: {result.get('dateFiled')}")
        
        # Test 5: Test IP case detection
        print("\n5. Testing IP case detection on real data...")
        ip_count = 0
        for docket in dockets[:5]:
            if processor._is_ip_case(docket):
                ip_count += 1
                print(f"  ✓ IP Case: {docket.get('case_name', '')[:50]}...")
        
        print(f"\nSummary: {ip_count}/{len(dockets[:5])} detected as IP cases")
        
        # Show rate limit status
        print(f"\n6. Rate Limit Status:")
        print(f"  Remaining: {cl_service.rate_limit_remaining}/5000")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await cl_service.close()
        # Clear the API key from environment
        del os.environ['COURTLISTENER_API_KEY']
        print("\n✓ API key cleared from environment")


async def test_minimal():
    """Minimal test with just one API call"""
    print("\n=== Minimal API Test ===")
    
    cl_service = CourtListenerService()
    
    try:
        # Single API call to verify key works
        print("Making single API call to verify key...")
        opinions = await cl_service.fetch_opinions(
            court_id='scotus',
            max_results=1
        )
        
        if opinions:
            print("✓ API key is valid!")
            print(f"  Sample case: {opinions[0].get('case_name', 'No name')}")
        else:
            print("✗ No results returned")
            
    except Exception as e:
        print(f"✗ API Error: {e}")
    
    finally:
        await cl_service.close()


# Run the tests
if __name__ == "__main__":
    print("Starting RECAP API tests...\n")
    
    # Run minimal test first
    asyncio.run(test_minimal())
    
    # Then run full test
    asyncio.run(test_live_api())
    
    print("\n=== Testing complete ===")
    print("You can now revoke the API key")