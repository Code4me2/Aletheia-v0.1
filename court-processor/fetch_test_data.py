#!/usr/bin/env python3
"""
Fetch non-trivial test data from RECAP: IP cases and transcripts
"""
import asyncio
import json
import os
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set the API key
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from services.courtlistener_service import CourtListenerService
from services.recap_processor import RECAPProcessor


async def fetch_test_dataset():
    """Fetch a comprehensive test dataset of IP cases and transcripts"""
    print("=== Fetching RECAP Test Dataset ===")
    print(f"Started at: {datetime.now()}\n")
    
    cl_service = CourtListenerService()
    processor = RECAPProcessor()
    
    # Create data directory
    data_dir = Path("test_data/recap")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Statistics
    stats = {
        'total_dockets': 0,
        'ip_dockets': 0,
        'total_documents': 0,
        'transcripts': 0,
        'available_pdfs': 0,
        'cases_with_transcripts': []
    }
    
    # Store all fetched data
    all_data = {
        'fetch_date': datetime.now().isoformat(),
        'dockets': [],
        'documents_by_docket': {},
        'transcripts': [],
        'ip_cases': []
    }
    
    try:
        # 1. Fetch IP cases from multiple courts
        print("1. Fetching IP cases from key venues...")
        
        # Target courts and date range
        target_courts = ['txed', 'deld', 'cand', 'ilnd', 'cafc']
        start_date = (date.today() - timedelta(days=90)).isoformat()  # Last 3 months
        
        for court in target_courts:
            print(f"\n  Fetching from {court.upper()}...")
            
            # Fetch patent cases
            patent_dockets = await cl_service.fetch_recap_dockets(
                court_ids=[court],
                date_filed_after=start_date,
                nature_of_suit=['830', '835'],  # Patent and ANDA
                max_results=10  # 10 per court to be conservative with API
            )
            
            # Fetch trademark/copyright cases
            tm_dockets = await cl_service.fetch_recap_dockets(
                court_ids=[court],
                date_filed_after=start_date,
                nature_of_suit=['820', '840'],  # Copyright and Trademark
                max_results=5  # 5 per court to be conservative
            )
            
            court_dockets = patent_dockets + tm_dockets
            print(f"    Found {len(court_dockets)} IP dockets")
            
            # Process each docket
            for docket in court_dockets:
                stats['total_dockets'] += 1
                
                if processor._is_ip_case(docket):
                    stats['ip_dockets'] += 1
                    all_data['ip_cases'].append({
                        'docket_id': docket['id'],
                        'case_name': docket['case_name'],
                        'court': docket['court'],
                        'nature_of_suit': docket['nature_of_suit'],
                        'date_filed': docket['date_filed']
                    })
                
                # Store docket
                all_data['dockets'].append(docket)
                
                # Fetch documents for this docket
                print(f"    Fetching documents for: {docket['case_name'][:50]}...")
                documents = await cl_service.fetch_recap_documents(docket['id'])
                
                stats['total_documents'] += len(documents)
                all_data['documents_by_docket'][str(docket['id'])] = documents
                
                # Look for transcripts
                docket_transcripts = []
                for doc in documents:
                    if processor._is_transcript(doc):
                        stats['transcripts'] += 1
                        docket_transcripts.append(doc)
                        
                        # Store transcript info
                        all_data['transcripts'].append({
                            'docket_id': docket['id'],
                            'case_name': docket['case_name'],
                            'court': docket['court'],
                            'document_id': doc['id'],
                            'description': doc['description'],
                            'date_filed': doc['date_filed'],
                            'page_count': doc.get('page_count', 0),
                            'is_available': doc.get('is_available', False)
                        })
                    
                    # Count available PDFs
                    if doc.get('is_available') or doc.get('filepath_local'):
                        stats['available_pdfs'] += 1
                
                if docket_transcripts:
                    stats['cases_with_transcripts'].append({
                        'case_name': docket['case_name'],
                        'docket_id': docket['id'],
                        'transcript_count': len(docket_transcripts)
                    })
                
                # Rate limit consideration
                await asyncio.sleep(0.1)
        
        # 2. Search specifically for transcripts
        print("\n2. Searching specifically for transcript documents...")
        
        transcript_searches = [
            'transcript hearing',
            'oral argument transcript',
            'trial transcript',
            'deposition transcript',
            'markman hearing transcript'
        ]
        
        for search_term in transcript_searches:
            print(f"\n  Searching: '{search_term}'")
            
            results = await cl_service.search_recap(
                query=search_term,
                court_ids=target_courts,
                date_range=(start_date, date.today().isoformat()),
                max_results=10
            )
            
            print(f"    Found {len(results)} results")
            
            # Store search results
            for result in results:
                if 'transcript' in result.get('snippet', '').lower():
                    all_data['transcripts'].append({
                        'search_result': True,
                        'case_name': result.get('caseName'),
                        'court': result.get('court'),
                        'date_filed': result.get('dateFiled'),
                        'snippet': result.get('snippet')
                    })
        
        # 3. Save all data
        print("\n3. Saving fetched data...")
        
        # Save main dataset
        with open(data_dir / 'recap_test_dataset.json', 'w') as f:
            json.dump(all_data, f, indent=2)
        
        # Save statistics
        stats['rate_limit_remaining'] = cl_service.rate_limit_remaining
        with open(data_dir / 'fetch_statistics.json', 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Save sample documents for testing
        sample_docs = []
        
        # Get diverse sample of documents
        for docket_id, docs in all_data['documents_by_docket'].items():
            # Get one transcript if available
            transcript = next((d for d in docs if processor._is_transcript(d)), None)
            if transcript:
                sample_docs.append({
                    'type': 'transcript',
                    'docket_id': docket_id,
                    'document': transcript
                })
            
            # Get one regular document
            regular_doc = next((d for d in docs if not processor._is_transcript(d)), None)
            if regular_doc:
                sample_docs.append({
                    'type': 'document',
                    'docket_id': docket_id,
                    'document': regular_doc
                })
        
        with open(data_dir / 'sample_documents.json', 'w') as f:
            json.dump(sample_docs[:50], f, indent=2)  # Save up to 50 samples
        
        # Print summary
        print("\n=== Fetch Summary ===")
        print(f"Total Dockets: {stats['total_dockets']}")
        print(f"IP Dockets: {stats['ip_dockets']}")
        print(f"Total Documents: {stats['total_documents']}")
        print(f"Transcripts Found: {stats['transcripts']}")
        print(f"Available PDFs: {stats['available_pdfs']}")
        print(f"Cases with Transcripts: {len(stats['cases_with_transcripts'])}")
        print(f"\nRate Limit Remaining: {stats['rate_limit_remaining']}/5000")
        
        # Show some transcript examples
        print("\n=== Sample Transcripts Found ===")
        for case in stats['cases_with_transcripts'][:5]:
            print(f"- {case['case_name'][:60]}...")
            print(f"  Docket ID: {case['docket_id']} | Transcripts: {case['transcript_count']}")
        
        # Create a focused test set
        print("\n4. Creating focused test set...")
        
        test_set = {
            'patent_cases': [],
            'trademark_cases': [],
            'transcript_cases': [],
            'mixed_ip_cases': []
        }
        
        # Categorize cases
        for docket in all_data['dockets']:
            nos = docket.get('nature_of_suit')
            docket_id = str(docket['id'])
            
            # Get document count
            doc_count = len(all_data['documents_by_docket'].get(docket_id, []))
            transcript_count = len([d for d in all_data['documents_by_docket'].get(docket_id, []) 
                                  if processor._is_transcript(d)])
            
            case_info = {
                'docket_id': docket['id'],
                'case_name': docket['case_name'],
                'court': docket['court'],
                'nature_of_suit': nos,
                'date_filed': docket['date_filed'],
                'document_count': doc_count,
                'transcript_count': transcript_count
            }
            
            if nos in ['830', '835']:
                test_set['patent_cases'].append(case_info)
            elif nos in ['820', '840']:
                test_set['trademark_cases'].append(case_info)
            
            if transcript_count > 0:
                test_set['transcript_cases'].append(case_info)
            
            if processor._is_ip_case(docket) and doc_count > 10:
                test_set['mixed_ip_cases'].append(case_info)
        
        # Save test set
        with open(data_dir / 'test_set.json', 'w') as f:
            json.dump(test_set, f, indent=2)
        
        print(f"\nTest Set Created:")
        print(f"- Patent Cases: {len(test_set['patent_cases'])}")
        print(f"- Trademark Cases: {len(test_set['trademark_cases'])}")
        print(f"- Cases with Transcripts: {len(test_set['transcript_cases'])}")
        print(f"- Complex IP Cases (>10 docs): {len(test_set['mixed_ip_cases'])}")
        
        print(f"\n✓ Data saved to: {data_dir.absolute()}")
        
    except Exception as e:
        print(f"\n✗ Error during fetch: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await cl_service.close()
        # Clear API key
        del os.environ['COURTLISTENER_API_KEY']
        print(f"\n✓ Completed at: {datetime.now()}")
        print("✓ API key cleared")


async def create_test_cases():
    """Create specific test cases from fetched data"""
    print("\n=== Creating Specific Test Cases ===")
    
    data_dir = Path("test_data/recap")
    
    # Load fetched data
    with open(data_dir / 'recap_test_dataset.json', 'r') as f:
        data = json.load(f)
    
    # Create test cases for different scenarios
    test_cases = {
        'simple_patent_case': None,
        'complex_trademark_case': None,
        'case_with_multiple_transcripts': None,
        'recent_markman_hearing': None,
        'high_document_count_case': None
    }
    
    # Find cases matching each scenario
    for docket in data['dockets']:
        docket_id = str(docket['id'])
        docs = data['documents_by_docket'].get(docket_id, [])
        
        # Simple patent case
        if not test_cases['simple_patent_case'] and docket.get('nature_of_suit') == '830' and len(docs) < 50:
            test_cases['simple_patent_case'] = {
                'docket': docket,
                'documents': docs[:10]  # First 10 docs
            }
        
        # Complex trademark case
        if not test_cases['complex_trademark_case'] and docket.get('nature_of_suit') == '840' and len(docs) > 30:
            test_cases['complex_trademark_case'] = {
                'docket': docket,
                'documents': docs[:20]
            }
        
        # Case with multiple transcripts
        transcript_count = len([d for d in docs if 'transcript' in d.get('description', '').lower()])
        if not test_cases['case_with_multiple_transcripts'] and transcript_count >= 2:
            test_cases['case_with_multiple_transcripts'] = {
                'docket': docket,
                'documents': [d for d in docs if 'transcript' in d.get('description', '').lower()]
            }
        
        # Recent Markman hearing
        for doc in docs:
            if 'markman' in doc.get('description', '').lower() and 'transcript' in doc.get('description', '').lower():
                test_cases['recent_markman_hearing'] = {
                    'docket': docket,
                    'documents': [doc]
                }
                break
        
        # High document count
        if not test_cases['high_document_count_case'] and len(docs) > 100:
            test_cases['high_document_count_case'] = {
                'docket': docket,
                'documents': docs[:50]  # First 50 for testing
            }
    
    # Save test cases
    with open(data_dir / 'specific_test_cases.json', 'w') as f:
        json.dump(test_cases, f, indent=2)
    
    print("\nTest cases created:")
    for case_type, case_data in test_cases.items():
        if case_data:
            print(f"✓ {case_type}: {case_data['docket']['case_name'][:50]}...")
        else:
            print(f"✗ {case_type}: Not found")


if __name__ == "__main__":
    # Run the fetch
    asyncio.run(fetch_test_dataset())
    
    # Create test cases
    asyncio.run(create_test_cases())
    
    print("\n=== Data Fetch Complete ===")
    print("You can now revoke the API key.")
    print("\nTo process this data, run:")
    print("  python process_test_data.py")