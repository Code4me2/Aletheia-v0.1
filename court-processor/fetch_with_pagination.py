#!/usr/bin/env python3
"""
Fetch real data from CourtListener API with proper pagination
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

async def fetch_paginated_documents(session, headers, docket_id, max_pages=3):
    """Fetch documents for a docket with pagination"""
    documents = []
    page = 1
    
    while page <= max_pages:
        try:
            params = {
                'docket': docket_id,
                'page': page,
                'page_size': 5  # Small page size to be respectful
            }
            
            print(f"    Fetching page {page} of documents...")
            async with session.get(f'{API_BASE_URL}/docket-entries/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    entries = data.get('results', [])
                    
                    if not entries:
                        break  # No more results
                    
                    # Process each entry
                    for entry in entries:
                        # Each docket entry can have multiple RECAP documents
                        if 'recap_documents' in entry and entry['recap_documents']:
                            # Fetch RECAP documents for this entry
                            for doc_url in entry['recap_documents']:
                                # Extract document ID from URL if needed
                                if isinstance(doc_url, str):
                                    # Fetch individual document
                                    async with session.get(doc_url, headers=headers) as doc_resp:
                                        if doc_resp.status == 200:
                                            doc_data = await doc_resp.json()
                                            doc_data['docket_id'] = docket_id
                                            doc_data['entry_id'] = entry['id']
                                            documents.append(doc_data)
                                        await asyncio.sleep(0.2)  # Rate limiting
                        
                        # Also store the entry itself
                        entry_doc = {
                            'id': f"entry_{entry['id']}",
                            'docket_id': docket_id,
                            'entry_number': entry.get('entry_number'),
                            'date_filed': entry.get('date_filed'),
                            'description': entry.get('description'),
                            'pacer_doc_id': entry.get('pacer_doc_id'),
                            'document_type': 'docket_entry'
                        }
                        documents.append(entry_doc)
                    
                    # Check if there's a next page
                    if not data.get('next'):
                        break
                        
                    page += 1
                    await asyncio.sleep(0.5)  # Rate limiting between pages
                    
                elif resp.status == 403:
                    print(f"    Access forbidden for page {page}")
                    break
                else:
                    print(f"    Error {resp.status} on page {page}")
                    break
                    
        except Exception as e:
            print(f"    Error fetching page {page}: {e}")
            break
    
    return documents

async def fetch_recap_data_paginated():
    """Fetch recent RECAP data with proper pagination"""
    print("=== Fetching Real RECAP Data with Pagination ===")
    print(f"Started at: {datetime.now()}\n")
    
    # Create data directory
    data_dir = Path("test_data/recap_real_paginated")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    headers = {
        'Authorization': f'Token {API_KEY}'
    }
    
    all_data = {
        'fetch_date': datetime.now().isoformat(),
        'dockets': [],
        'documents': [],
        'statistics': {
            'total_dockets': 0,
            'total_documents': 0,
            'dockets_with_documents': 0
        }
    }
    
    async with aiohttp.ClientSession() as session:
        # First, fetch a few recent dockets
        print("Fetching recent dockets from TXED...")
        
        params = {
            'court': 'txed',
            'date_filed__gte': '2024-01-01',
            'ordering': '-date_filed',
            'page_size': 3  # Just get 3 dockets to test
        }
        
        try:
            async with session.get(f'{API_BASE_URL}/dockets/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    dockets = data.get('results', [])
                    print(f"Found {len(dockets)} dockets")
                    all_data['statistics']['total_dockets'] = len(dockets)
                    
                    # Process each docket
                    for i, docket in enumerate(dockets):
                        print(f"\n[{i+1}/{len(dockets)}] Processing: {docket['case_name']}")
                        print(f"  Docket ID: {docket['id']}")
                        all_data['dockets'].append(docket)
                        
                        # Fetch documents with pagination
                        documents = await fetch_paginated_documents(session, headers, docket['id'])
                        
                        if documents:
                            print(f"  Retrieved {len(documents)} documents/entries")
                            all_data['statistics']['dockets_with_documents'] += 1
                            
                            # Add case info to each document
                            for doc in documents:
                                doc['case_name'] = docket['case_name']
                                doc['court'] = docket['court_id']
                                doc['docket_number'] = docket['docket_number']
                                all_data['documents'].append(doc)
                        else:
                            print(f"  No documents retrieved")
                        
                        # Rate limiting between dockets
                        await asyncio.sleep(1)
                        
                else:
                    print(f"Error fetching dockets: {resp.status}")
                    error_text = await resp.text()
                    print(f"Error details: {error_text}")
        
        except Exception as e:
            print(f"Error during fetch: {e}")
            import traceback
            traceback.print_exc()
    
    # Update statistics
    all_data['statistics']['total_documents'] = len(all_data['documents'])
    
    # Save the data
    output_file = data_dir / 'recap_paginated_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✓ Data saved to: {output_file}")
    print(f"\nSummary:")
    print(f"- Dockets fetched: {all_data['statistics']['total_dockets']}")
    print(f"- Documents retrieved: {all_data['statistics']['total_documents']}")
    print(f"- Dockets with documents: {all_data['statistics']['dockets_with_documents']}")
    
    # Show sample of what we got
    if all_data['documents']:
        print("\n=== Sample Documents ===")
        for doc in all_data['documents'][:5]:
            print(f"- {doc.get('description', doc.get('document_type', 'Unknown'))}")
            print(f"  Case: {doc.get('case_name', 'Unknown')}")
            print(f"  Filed: {doc.get('date_filed', 'Unknown')}")
    
    return all_data

if __name__ == "__main__":
    asyncio.run(fetch_recap_data_paginated())