#!/usr/bin/env python3
"""
Simple script to fetch real data from CourtListener API
"""
import os
import json
import asyncio
import aiohttp
from datetime import datetime, date, timedelta
from pathlib import Path

# API Configuration
API_KEY = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
API_BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

async def fetch_recap_data():
    """Fetch recent RECAP documents from CourtListener"""
    print("=== Fetching Real RECAP Data ===")
    print(f"Started at: {datetime.now()}\n")
    
    # Create data directory
    data_dir = Path("test_data/recap_real")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'Authorization': f'Token {API_KEY}'
    }
    
    all_data = {
        'fetch_date': datetime.now().isoformat(),
        'dockets': [],
        'documents': []
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. Fetch recent dockets from Eastern District of Texas
        print("Fetching recent patent dockets from TXED...")
        
        params = {
            'court': 'txed',
            'date_filed__gte': '2024-01-01',  # From start of 2024
            'ordering': '-date_filed',
            'page_size': 5  # Just get 5 recent dockets
        }
        
        try:
            async with session.get(f'{API_BASE_URL}/dockets/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    dockets = data.get('results', [])
                    print(f"Found {len(dockets)} dockets")
                    
                    for docket in dockets:
                        print(f"\nProcessing: {docket['case_name']}")
                        all_data['dockets'].append(docket)
                        
                        # Fetch documents for this docket
                        docket_id = docket['id']
                        doc_params = {
                            'docket': docket_id,
                            'page_size': 10  # Get first 10 documents
                        }
                        
                        async with session.get(f'{API_BASE_URL}/recap-documents/', headers=headers, params=doc_params) as doc_resp:
                            if doc_resp.status == 200:
                                doc_data = await doc_resp.json()
                                documents = doc_data.get('results', [])
                                print(f"  Found {len(documents)} documents")
                                
                                for doc in documents:
                                    doc['docket_id'] = docket_id
                                    doc['case_name'] = docket['case_name']
                                    doc['court'] = docket['court']
                                    all_data['documents'].append(doc)
                            else:
                                print(f"  Error fetching documents: {doc_resp.status}")
                        
                        # Small delay to respect rate limits
                        await asyncio.sleep(0.5)
                else:
                    print(f"Error fetching dockets: {resp.status}")
                    error_text = await resp.text()
                    print(f"Error details: {error_text}")
        
        except Exception as e:
            print(f"Error during fetch: {e}")
            import traceback
            traceback.print_exc()
    
    # Save the data
    output_file = data_dir / 'recap_real_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✓ Data saved to: {output_file}")
    print(f"✓ Fetched {len(all_data['dockets'])} dockets with {len(all_data['documents'])} documents")
    
    # Show summary
    if all_data['dockets']:
        print("\n=== Sample Dockets ===")
        for docket in all_data['dockets'][:3]:
            print(f"- {docket['case_name']}")
            print(f"  Filed: {docket['date_filed']} | Number: {docket['docket_number']}")
    
    return all_data

if __name__ == "__main__":
    asyncio.run(fetch_recap_data())