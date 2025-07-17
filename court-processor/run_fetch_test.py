#!/usr/bin/env python3
"""
Minimal test to fetch RECAP data
"""
import os
import json
import asyncio
from datetime import date, timedelta
from pathlib import Path

# Set API key
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

# Import after setting env var
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.courtlistener_service import CourtListenerService
from services.recap_processor import RECAPProcessor

async def fetch_minimal_test():
    """Fetch minimal test data to verify functionality"""
    print("=== Fetching Minimal RECAP Test Data ===\n")
    
    cl_service = CourtListenerService()
    processor = RECAPProcessor()
    
    # Create data directory
    data_dir = Path("test_data/recap")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'fetch_time': str(date.today()),
        'dockets': [],
        'documents': [],
        'transcripts': [],
        'errors': []
    }
    
    try:
        # 1. Test basic connection
        print("1. Testing connection...")
        opinions = await cl_service.fetch_opinions(
            court_id='ca9',
            max_results=1
        )
        if opinions:
            print(f"✓ Connected! Found {len(opinions)} opinion")
        
        # 2. Fetch recent patent cases from EDTX
        print("\n2. Fetching recent patent cases from E.D. Texas...")
        start_date = (date.today() - timedelta(days=30)).isoformat()
        
        dockets = await cl_service.fetch_recap_dockets(
            court_ids=['txed'],
            date_filed_after=start_date,
            nature_of_suit=['830'],  # Patent only
            max_results=5  # Just 5 for testing
        )
        
        print(f"✓ Found {len(dockets)} patent dockets")
        results['dockets'] = dockets
        
        # 3. Process first 2 dockets
        for i, docket in enumerate(dockets[:2]):
            print(f"\n3.{i+1} Processing docket: {docket['case_name'][:50]}...")
            
            # Fetch documents
            try:
                documents = await cl_service.fetch_recap_documents(docket['id'])
                print(f"  Found {len(documents)} documents")
                
                # Check for transcripts
                for doc in documents[:10]:  # First 10 docs only
                    if processor._is_transcript(doc):
                        results['transcripts'].append({
                            'docket_id': docket['id'],
                            'case_name': docket['case_name'],
                            'doc_id': doc['id'],
                            'description': doc['description'],
                            'pages': doc.get('page_count', 0)
                        })
                        print(f"  ✓ Found transcript: {doc['description'][:60]}...")
                
                results['documents'].extend(documents[:5])  # Save first 5
                
            except Exception as e:
                print(f"  ✗ Error fetching documents: {e}")
                results['errors'].append(str(e))
        
        # 4. Search for transcripts
        print("\n4. Searching for transcripts...")
        search_results = await cl_service.search_recap(
            query='transcript markman',
            court_ids=['txed'],
            max_results=3
        )
        
        print(f"✓ Found {len(search_results)} search results")
        
        # Save results
        with open(data_dir / 'minimal_test_data.json', 'w') as f:
            json.dump(results, f, indent=2)
        
        # Print summary
        print("\n=== Summary ===")
        print(f"Dockets fetched: {len(results['dockets'])}")
        print(f"Documents found: {len(results['documents'])}")
        print(f"Transcripts identified: {len(results['transcripts'])}")
        print(f"Errors: {len(results['errors'])}")
        
        # Show transcripts
        if results['transcripts']:
            print("\nSample transcripts found:")
            for t in results['transcripts'][:3]:
                print(f"- {t['description'][:60]}...")
                print(f"  Pages: {t['pages']}")
        
        print(f"\n✓ Data saved to: {data_dir.absolute()}/minimal_test_data.json")
        
        # Rate limit check
        print(f"\nRate limit remaining: {cl_service.rate_limit_remaining}/5000")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await cl_service.close()
        del os.environ['COURTLISTENER_API_KEY']
        print("\n✓ API key cleared")

# Run the test
if __name__ == "__main__":
    asyncio.run(fetch_minimal_test())
    print("\n✓ Test complete! You can now revoke the API key.")