"""
Test script for RECAP integration
"""
import asyncio
import json
import os
from datetime import datetime, date, timedelta
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.courtlistener_service import CourtListenerService
from services.recap_processor import RECAPProcessor
from services.legal_document_enhancer import enhance_legal_document


async def test_courtlistener_connection():
    """Test basic connection to CourtListener API"""
    print("\n=== Testing CourtListener Connection ===")
    
    # Note: Set COURTLISTENER_API_KEY environment variable or pass it here
    cl_service = CourtListenerService()
    
    try:
        # Test fetching recent opinions
        print("Fetching recent opinions...")
        opinions = await cl_service.fetch_opinions(
            court_id='ca9',
            date_filed_after='2024-01-01',
            max_results=5
        )
        
        print(f"✓ Found {len(opinions)} opinions")
        if opinions:
            print(f"  Sample: {opinions[0].get('case_name', 'No name')[:50]}...")
        
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False
    finally:
        await cl_service.close()


async def test_recap_docket_fetch():
    """Test fetching RECAP docket data"""
    print("\n=== Testing RECAP Docket Fetch ===")
    
    cl_service = CourtListenerService()
    
    try:
        # Fetch recent IP dockets from Eastern District of Texas
        print("Fetching recent patent dockets from EDTX...")
        dockets = await cl_service.fetch_recap_dockets(
            court_ids=['txed'],
            date_filed_after='2024-01-01',
            nature_of_suit=['830'],  # Patent cases
            max_results=3
        )
        
        print(f"✓ Found {len(dockets)} patent dockets")
        
        for i, docket in enumerate(dockets[:2]):
            print(f"\n  Docket {i+1}:")
            print(f"    ID: {docket.get('id')}")
            print(f"    Case: {docket.get('case_name', 'No name')[:60]}...")
            print(f"    Court: {docket.get('court')}")
            print(f"    Nature of Suit: {docket.get('nature_of_suit')}")
            print(f"    Date Filed: {docket.get('date_filed')}")
        
        return dockets
    except Exception as e:
        print(f"✗ RECAP fetch failed: {e}")
        return []
    finally:
        await cl_service.close()


async def test_recap_document_fetch(docket_id: int):
    """Test fetching documents for a specific docket"""
    print(f"\n=== Testing RECAP Document Fetch for Docket {docket_id} ===")
    
    cl_service = CourtListenerService()
    
    try:
        print(f"Fetching documents for docket {docket_id}...")
        documents = await cl_service.fetch_recap_documents(docket_id)
        
        print(f"✓ Found {len(documents)} documents")
        
        # Look for transcripts
        transcripts = []
        for doc in documents:
            desc = doc.get('description', '').lower()
            if any(word in desc for word in ['transcript', 'hearing', 'proceeding']):
                transcripts.append(doc)
        
        print(f"  Including {len(transcripts)} potential transcripts")
        
        # Show sample documents
        for i, doc in enumerate(documents[:3]):
            print(f"\n  Document {i+1}:")
            print(f"    ID: {doc.get('id')}")
            print(f"    Number: {doc.get('document_number')}")
            print(f"    Description: {doc.get('description', 'No description')[:60]}...")
            print(f"    Pages: {doc.get('page_count', 'Unknown')}")
            print(f"    Available: {doc.get('is_available', False)}")
            print(f"    Has Text: {bool(doc.get('plain_text'))}")
        
        return documents
    except Exception as e:
        print(f"✗ Document fetch failed: {e}")
        return []
    finally:
        await cl_service.close()


async def test_recap_search():
    """Test RECAP search functionality"""
    print("\n=== Testing RECAP Search ===")
    
    cl_service = CourtListenerService()
    
    try:
        print("Searching for 'patent infringement' cases...")
        results = await cl_service.search_recap(
            query='patent infringement',
            court_ids=['txed', 'deld'],
            max_results=5
        )
        
        print(f"✓ Found {len(results)} search results")
        
        for i, result in enumerate(results[:3]):
            print(f"\n  Result {i+1}:")
            print(f"    Case: {result.get('caseName', 'No name')[:60]}...")
            print(f"    Court: {result.get('court')}")
            print(f"    Date: {result.get('dateFiled')}")
            print(f"    Snippet: {result.get('snippet', '')[:100]}...")
        
        return results
    except Exception as e:
        print(f"✗ Search failed: {e}")
        return []
    finally:
        await cl_service.close()


async def test_ip_case_detection():
    """Test IP case detection logic"""
    print("\n=== Testing IP Case Detection ===")
    
    processor = RECAPProcessor()
    
    test_cases = [
        {
            'nature_of_suit': '830',
            'case_name': 'Apple Inc. v. Samsung Electronics Co.',
            'expected': True,
            'reason': 'Patent case (830)'
        },
        {
            'nature_of_suit': '840',
            'case_name': 'Nike v. Adidas',
            'expected': True,
            'reason': 'Trademark case (840)'
        },
        {
            'nature_of_suit': '440',
            'case_name': 'Smith v. Jones',
            'expected': False,
            'reason': 'Not IP case'
        },
        {
            'nature_of_suit': '190',
            'case_name': 'Patent Holder LLC v. Tech Corp',
            'expected': True,
            'reason': 'Patent in case name'
        }
    ]
    
    for case in test_cases:
        is_ip = processor._is_ip_case(case)
        status = "✓" if is_ip == case['expected'] else "✗"
        print(f"{status} {case['case_name']}: {is_ip} ({case['reason']})")


async def test_transcript_detection():
    """Test transcript detection logic"""
    print("\n=== Testing Transcript Detection ===")
    
    processor = RECAPProcessor()
    
    test_docs = [
        {
            'description': 'Transcript of Jury Trial Proceedings',
            'expected': True
        },
        {
            'description': 'Motion Hearing Transcript',
            'expected': True
        },
        {
            'description': 'Deposition of John Smith',
            'expected': True
        },
        {
            'description': 'Motion to Dismiss',
            'expected': False
        },
        {
            'description': 'Order on Motion',
            'document_type': 'transcript',
            'expected': True
        }
    ]
    
    for doc in test_docs:
        is_transcript = processor._is_transcript(doc)
        status = "✓" if is_transcript == doc['expected'] else "✗"
        print(f"{status} {doc['description']}: {is_transcript}")


async def test_legal_enhancement():
    """Test legal document enhancement on sample text"""
    print("\n=== Testing Legal Enhancement ===")
    
    # Create sample transcript text
    sample_transcript = """
THE COURT: Good morning. We'll hear argument in Apple v. Samsung.

MR. SMITH: Good morning, Your Honor. John Smith for the plaintiff.

MS. JONES: Sarah Jones for the defendant, Your Honor.

THE COURT: Mr. Smith, you may proceed.

MR. SMITH: Thank you, Your Honor. This case involves Patent No. 123,456 
relating to touch screen technology.

MS. JONES: Objection, Your Honor. Relevance.

THE COURT: Overruled. You may continue.

MR. SMITH: The evidence will show clear infringement of claims 1-5.

MS. JONES: Your Honor, I object. This is argumentative.

THE COURT: Sustained. Move on, counsel.
"""
    
    # Create mock elements
    lines = sample_transcript.strip().split('\n')
    elements = []
    
    for line in lines:
        if line.strip():
            class MockElement:
                def __init__(self, text):
                    self.text = text
                    self.category = 'NarrativeText'
                    self.metadata = type('obj', (object,), {'legal': {}})()
            
            elements.append(MockElement(line))
    
    # Enhance
    enhanced = enhance_legal_document(elements, doc_type='transcript')
    
    print("\nEnhanced transcript analysis:")
    
    speakers = set()
    objections = 0
    rulings = 0
    
    for elem in enhanced:
        legal = elem.metadata.legal
        
        if legal.get('speaker'):
            speakers.add(legal['speaker'])
        
        if legal.get('event') == 'objection':
            objections += 1
            print(f"\n  Objection found:")
            print(f"    Speaker: {legal.get('speaker')}")
            print(f"    Type: {legal.get('event_type')}")
            print(f"    Text: {elem.text[:50]}...")
        
        if legal.get('event') == 'ruling':
            rulings += 1
            print(f"\n  Ruling found:")
            print(f"    Ruling: {legal.get('ruling')}")
            print(f"    Text: {elem.text}")
    
    print(f"\nSummary:")
    print(f"  Speakers identified: {len(speakers)} - {speakers}")
    print(f"  Objections: {objections}")
    print(f"  Rulings: {rulings}")


async def test_recap_processor_integration():
    """Test full RECAP processor integration"""
    print("\n=== Testing RECAP Processor Integration ===")
    
    processor = RECAPProcessor()
    
    # Create sample RECAP document
    sample_docket = {
        'id': 12345,
        'court': 'txed',
        'case_name': 'Tech Innovations v. Mobile Corp',
        'nature_of_suit': '830',
        'docket_number': '2:24-cv-00123',
        'date_filed': '2024-01-15'
    }
    
    sample_doc = {
        'id': 67890,
        'document_number': '42',
        'description': 'Transcript of Claim Construction Hearing',
        'date_filed': '2024-03-01',
        'page_count': 125,
        'plain_text': """
THE COURT: We're here for claim construction in Tech Innovations v. Mobile Corp.

MR. WILLIAMS: Your Honor, the term "wireless interface" should be construed...

MS. CHEN: Objection. That's not the agreed construction.

THE COURT: Overruled. Continue.
""",
        'is_available': True
    }
    
    # Test document creation
    unified = processor._create_unified_recap_document(sample_docket, sample_doc)
    
    print("Created unified document:")
    print(f"  ID: {unified['id']}")
    print(f"  Type: {unified['type']}")
    print(f"  Court: {unified['court_id']}")
    print(f"  Is IP Case: {unified['is_ip_case']}")
    print(f"  Description: {unified['description']}")
    
    # Test detection
    print(f"\n  Is transcript: {processor._is_transcript(sample_doc)}")
    print(f"  Is IP case: {processor._is_ip_case(sample_docket)}")


async def main():
    """Run all tests"""
    print("=== RECAP Integration Test Suite ===")
    print(f"Started at: {datetime.now()}")
    
    # Check for API key
    if not os.getenv('COURTLISTENER_API_KEY'):
        print("\n⚠️  WARNING: No COURTLISTENER_API_KEY found in environment")
        print("Some tests may fail or return limited results")
        print("Set with: export COURTLISTENER_API_KEY=your_key_here")
    
    # Run tests
    
    # 1. Test basic connection
    connected = await test_courtlistener_connection()
    
    if connected:
        # 2. Test RECAP docket fetching
        dockets = await test_recap_docket_fetch()
        
        # 3. Test document fetching for first docket
        if dockets and len(dockets) > 0:
            await test_recap_document_fetch(dockets[0]['id'])
        
        # 4. Test search
        await test_recap_search()
    
    # 5. Test detection logic (doesn't need API)
    await test_ip_case_detection()
    await test_transcript_detection()
    
    # 6. Test legal enhancement
    await test_legal_enhancement()
    
    # 7. Test processor integration
    await test_recap_processor_integration()
    
    print(f"\n=== Tests completed at: {datetime.now()} ===")


if __name__ == "__main__":
    asyncio.run(main())