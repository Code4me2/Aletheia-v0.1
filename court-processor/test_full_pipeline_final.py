#!/usr/bin/env python3
"""
Final test of complete pipeline with real CourtListener data
"""

import asyncio
import aiohttp
import os
from datetime import datetime
from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline

API_KEY = os.getenv('COURTLISTENER_API_KEY', 'f751990518aacab953214f2e56ac6ccbff9e2c14')

async def fetch_test_data():
    """Fetch real dockets and opinions from CourtListener"""
    
    async with aiohttp.ClientSession() as session:
        # Fetch some recent dockets
        print("Fetching dockets from CourtListener...")
        docket_url = "https://www.courtlistener.com/api/rest/v4/dockets/"
        headers = {"Authorization": f"Token {API_KEY}"}
        params = {
            "court__id": "txed",  # Eastern District of Texas
            "order_by": "-date_modified",
            "page_size": 5  # Small set for testing
        }
        
        async with session.get(docket_url, headers=headers, params=params) as response:
            if response.status != 200:
                print(f"Failed to fetch dockets: {response.status}")
                return [], []
            
            data = await response.json()
            dockets = data.get('results', [])
            print(f"Fetched {len(dockets)} dockets")
        
        # Fetch some opinions 
        print("\nFetching opinions from CourtListener...")
        opinion_url = "https://www.courtlistener.com/api/rest/v4/opinions/"
        params = {
            "court__id": "txed",
            "order_by": "-date_filed",
            "page_size": 5
        }
        
        async with session.get(opinion_url, headers=headers, params=params) as response:
            if response.status != 200:
                print(f"Failed to fetch opinions: {response.status}")
                opinions = []
            else:
                data = await response.json()
                opinions = data.get('results', [])
                print(f"Fetched {len(opinions)} opinions")
        
        return dockets, opinions

async def test_complete_pipeline():
    """Test the complete pipeline with real data"""
    
    print("Final Pipeline Test with Real CourtListener Data")
    print("=" * 60)
    
    # Initialize pipeline
    pipeline = OptimizedElevenStagePipeline()
    
    # Fetch real data
    dockets, opinions = await fetch_test_data()
    
    if not dockets and not opinions:
        print("No data fetched, using test data...")
        # Use a test docket
        dockets = [{
            'id': 123456,
            'date_created': '2024-01-15T10:00:00Z',
            'date_modified': '2024-01-15T10:00:00Z',
            'court_id': 'txed',
            'docket_number': '2:24-cv-00123',
            'case_name': 'Apple Inc. v. Samsung Electronics Co.',
            'judge': 'Rodney Gilstrap',
            'source': 0,
            'appeal_from_id': None,
            'referred_to_id': None,
            'panel': [],
            'originating_court_information_id': None
        }]
        
        opinions = [{
            'id': 789012,
            'absolute_url': '/opinion/789012/apple-v-samsung/',
            'case_name': 'Apple Inc. v. Samsung Electronics Co.',
            'case_name_full': 'Apple Inc. v. Samsung Electronics Co., Ltd.',
            'case_name_short': 'Apple v. Samsung',
            'court_id': 'txed',
            'date_filed': '2024-01-10',
            'type': 'Combined Opinion',
            'source': 'R',
            'procedural_history': '',
            'attorneys': '',
            'nature_of_suit': 'Patent',
            'citation_count': 0,
            'cluster_id': 987654,
            'html': '',
            'html_lawbox': '',
            'html_columbia': '',
            'html_anon_2020': '',
            'xml_harvard': '',
            'html_with_citations': '''<p>This case cites several important precedents including 
            <cite>123 F.3d 456</cite> (5th Cir. 2023), <cite>456 F.2d 789</cite> (9th Cir. 1972),
            <cite>789 F. Supp. 2d 123</cite> (E.D. Tex. 2020), and <cite>654 U.S. 321</cite> (2019).
            The Federal Circuit in <cite>234 Fed. Cir. 567</cite> held that...</p>''',
            'plain_text': '''This case cites several important precedents including 
            123 F.3d 456 (5th Cir. 2023), 456 F.2d 789 (9th Cir. 1972),
            789 F. Supp. 2d 123 (E.D. Tex. 2020), and 654 U.S. 321 (2019).
            The Federal Circuit in 234 Fed. Cir. 567 held that...''',
            'sha1': 'abc123def456',
            'download_url': '/api/rest/v4/opinions/789012/download/',
            'local_path': '',
            'cites': []
        }]
    
    # Process dockets
    print("\n" + "="*60)
    print("PROCESSING DOCKETS")
    print("="*60)
    
    for i, docket in enumerate(dockets):
        print(f"\nDocket {i+1}/{len(dockets)}: {docket.get('case_name', 'Unknown')}")
        
        # Process single document
        results = await pipeline.process_batch([{
            'content': str(docket),
            'metadata': docket,
            'type': 'docket'
        }])
        result = results[0] if results else {'success': False, 'error': 'No result'}
        
        if result['success']:
            print(f"✅ Successfully processed")
            print(f"   Completeness: {result['completeness_score']:.1f}%")
            print(f"   Enhancements applied: {result['enhancements_applied']}")
            
            # Show details of enhancements
            metadata = result['processed_data']['metadata']
            
            if metadata.get('court_enhanced'):
                print(f"   Court: {metadata.get('court_full_name', 'Unknown')}")
            
            if metadata.get('judge_enhanced'):
                print(f"   Judge: {metadata.get('judge_full_name', 'Unknown')}")
            
            if metadata.get('citations'):
                print(f"   Citations found: {len(metadata['citations'])}")
                
            if metadata.get('normalized_reporters'):
                print(f"   Reporters normalized: {metadata['normalized_reporters']['count']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Process opinions
    print("\n" + "="*60)
    print("PROCESSING OPINIONS")
    print("="*60)
    
    for i, opinion in enumerate(opinions):
        print(f"\nOpinion {i+1}/{len(opinions)}: {opinion.get('case_name', 'Unknown')}")
        
        # Use plain text if available, otherwise html_with_citations
        content = opinion.get('plain_text') or opinion.get('html_with_citations', '')
        
        # Process single document
        results = await pipeline.process_batch([{
            'content': content,
            'metadata': opinion,
            'type': 'opinion'
        }])
        result = results[0] if results else {'success': False, 'error': 'No result'}
        
        if result['success']:
            print(f"✅ Successfully processed")
            print(f"   Completeness: {result['completeness_score']:.1f}%")
            print(f"   Enhancements applied: {result['enhancements_applied']}")
            
            # Show details of enhancements
            metadata = result['processed_data']['metadata']
            
            if metadata.get('court_enhanced'):
                print(f"   Court: {metadata.get('court_full_name', 'Unknown')}")
            
            if metadata.get('citations'):
                print(f"   Citations found: {len(metadata['citations'])}")
                # Show some citations
                for j, cite in enumerate(metadata['citations'][:3]):
                    print(f"     - {cite['text']}")
                if len(metadata['citations']) > 3:
                    print(f"     ... and {len(metadata['citations']) - 3} more")
            
            if metadata.get('normalized_reporters'):
                reporters = metadata['normalized_reporters']
                print(f"   Reporters normalized: {reporters['count']}")
                if reporters.get('normalized_reporters'):
                    # Show successful normalizations
                    success_count = len([r for r in reporters['normalized_reporters'] 
                                       if r.get('found', False)])
                    print(f"   Successfully normalized: {success_count}/{len(reporters['normalized_reporters'])}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Test Haystack integration
    print("\n" + "="*60)
    print("TESTING HAYSTACK INTEGRATION")
    print("="*60)
    
    # Process all documents for Haystack
    all_docs = []
    
    for docket in dockets:
        # Process single document
        results = await pipeline.process_batch([{
            'content': str(docket),
            'metadata': docket,
            'type': 'docket'
        }])
        result = results[0] if results else {'success': False, 'error': 'No result'}
        if result['success']:
            all_docs.append(result['processed_data'])
    
    for opinion in opinions:
        content = opinion.get('plain_text') or opinion.get('html_with_citations', '')
        # Process single document
        results = await pipeline.process_batch([{
            'content': content,
            'metadata': opinion,
            'type': 'opinion'
        }])
        result = results[0] if results else {'success': False, 'error': 'No result'}
        if result['success']:
            all_docs.append(result['processed_data'])
    
    if all_docs:
        print(f"\nSending {len(all_docs)} documents to Haystack...")
        haystack_result = await pipeline.send_to_haystack(all_docs)
        
        if haystack_result['success']:
            print(f"✅ Successfully sent to Haystack")
            print(f"   Documents indexed: {haystack_result.get('document_count', 0)}")
        else:
            print(f"❌ Failed to send to Haystack: {haystack_result.get('error', 'Unknown error')}")
    else:
        print("No documents to send to Haystack")
    
    print("\n" + "="*60)
    print("PIPELINE TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_complete_pipeline())