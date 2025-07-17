#!/usr/bin/env python3
"""
Fetch court opinions using CourtListener free tier endpoints
Works with basic API access - no paid tier required
"""
import asyncio
import aiohttp
import json
from datetime import datetime, date, timedelta
from pathlib import Path

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

async def fetch_opinions_data():
    """Fetch opinions and related data using free tier endpoints"""
    print("=== Fetching Court Data with Free Tier Access ===")
    print(f"Started at: {datetime.now()}\n")
    
    # Create data directory
    data_dir = Path("test_data/courtlistener_free")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Correct authorization header format
    headers = {
        'Authorization': f'Token {API_TOKEN}'  # Note the space after "Token"
    }
    
    all_data = {
        'fetch_date': datetime.now().isoformat(),
        'dockets': [],
        'opinions': [],
        'judges': [],
        'courts': [],
        'statistics': {
            'total_dockets': 0,
            'total_opinions': 0,
            'total_judges': 0,
            'dockets_with_opinions': 0
        }
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. Fetch some courts first
        print("1. Fetching court information...")
        async with session.get(f'{BASE_URL}/courts/', headers=headers, params={'page_size': 10}) as resp:
            if resp.status == 200:
                data = await resp.json()
                courts = data.get('results', [])
                all_data['courts'] = courts
                print(f"   ✓ Found {len(courts)} courts")
                
                # Show some example courts
                for court in courts[:3]:
                    print(f"     - {court['id']}: {court['full_name']}")
        
        # 2. Fetch recent opinions from specific courts
        print("\n2. Fetching recent opinions...")
        
        # Use courts that typically have opinions
        target_courts = ['ca9', 'ca5', 'scotus', 'txed']
        
        for court_id in target_courts:
            print(f"\n   Fetching opinions from {court_id}...")
            
            params = {
                'court': court_id,
                'date_filed__gte': (date.today() - timedelta(days=30)).isoformat(),
                'page_size': 5,
                'ordering': '-date_filed'
            }
            
            try:
                async with session.get(f'{BASE_URL}/opinions/', headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        opinions = data.get('results', [])
                        
                        if opinions:
                            print(f"     ✓ Found {len(opinions)} recent opinions")
                            all_data['opinions'].extend(opinions)
                            all_data['statistics']['total_opinions'] += len(opinions)
                            
                            # Show sample
                            for op in opinions[:2]:
                                # Extract case name from cluster URL or use type
                                print(f"       - {op.get('type', 'Opinion')} filed {op.get('date_created', 'Unknown')[:10]}")
                        else:
                            print(f"     - No recent opinions found")
                            
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                print(f"     ✗ Error: {e}")
        
        # 3. Fetch recent dockets (we can get metadata even if not documents)
        print("\n3. Fetching recent docket metadata...")
        
        for court_id in ['txed', 'nysd']:
            params = {
                'court': court_id,
                'date_filed__gte': (date.today() - timedelta(days=7)).isoformat(),
                'page_size': 5,
                'ordering': '-date_filed'
            }
            
            try:
                async with session.get(f'{BASE_URL}/dockets/', headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        dockets = data.get('results', [])
                        
                        if dockets:
                            print(f"\n   ✓ Found {len(dockets)} recent dockets from {court_id}")
                            all_data['dockets'].extend(dockets)
                            all_data['statistics']['total_dockets'] += len(dockets)
                            
                            for docket in dockets[:2]:
                                print(f"     - {docket['case_name']}")
                                print(f"       Filed: {docket['date_filed']} | Number: {docket['docket_number']}")
                        
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"   ✗ Error fetching dockets: {e}")
        
        # 4. Fetch some judge information
        print("\n4. Fetching judge information...")
        
        params = {
            'page_size': 10,
            'ordering': '-date_modified'
        }
        
        try:
            async with session.get(f'{BASE_URL}/people/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    judges = data.get('results', [])
                    all_data['judges'] = judges
                    all_data['statistics']['total_judges'] = len(judges)
                    
                    print(f"   ✓ Found {len(judges)} judges")
                    for judge in judges[:3]:
                        print(f"     - {judge.get('name_first', '')} {judge.get('name_last', '')}")
                        
        except Exception as e:
            print(f"   ✗ Error fetching judges: {e}")
    
    # Save all data
    output_file = data_dir / 'courtlistener_free_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_data, f, indent=2)
    
    print(f"\n✓ Data saved to: {output_file}")
    print(f"\nSummary:")
    print(f"- Courts: {len(all_data['courts'])}")
    print(f"- Opinions: {all_data['statistics']['total_opinions']}")
    print(f"- Dockets: {all_data['statistics']['total_dockets']}")
    print(f"- Judges: {all_data['statistics']['total_judges']}")
    
    return all_data

def process_to_postgres(data):
    """Process fetched data and save to PostgreSQL"""
    import psycopg2
    from psycopg2.extras import Json
    
    print("\n=== Saving to PostgreSQL ===")
    
    # Database configuration
    conn = psycopg2.connect(
        host='db',
        port=5432,
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    cursor = conn.cursor()
    
    documents_added = 0
    
    # Process opinions
    for opinion in data.get('opinions', []):
        try:
            # Create a document from opinion data
            case_number = f"OPINION-{opinion['id']}"
            doc_type = opinion.get('type', 'opinion')
            
            # Create content from available fields
            content = f"""Opinion Type: {opinion.get('type', 'Unknown')}
Author: {opinion.get('author_str', 'Not specified')}
Filed: {opinion.get('date_created', 'Unknown')}

[Opinion text would be here if available in free tier]

This is metadata from CourtListener free tier API.
"""
            
            metadata = {
                'source': 'courtlistener_api_free',
                'opinion_id': opinion['id'],
                'type': opinion.get('type'),
                'author': opinion.get('author_str'),
                'author_id': opinion.get('author_id'),
                'per_curiam': opinion.get('per_curiam', False),
                'joined_by': opinion.get('joined_by_str'),
                'date_created': opinion.get('date_created'),
                'date_modified': opinion.get('date_modified'),
                'sha1': opinion.get('sha1'),
                'download_url': opinion.get('download_url'),
                'local_path': opinion.get('local_path'),
                'extracted_by_ocr': opinion.get('extracted_by_ocr', False)
            }
            
            cursor.execute("""
                INSERT INTO court_documents (
                    case_number, document_type, file_path, content, metadata, processed
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                case_number,
                doc_type,
                opinion.get('local_path', ''),
                content,
                Json(metadata),
                False
            ))
            
            documents_added += 1
            
        except Exception as e:
            print(f"Error inserting opinion {opinion.get('id')}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    print(f"✓ Added {documents_added} opinion documents to database")
    
    cursor.close()
    conn.close()

async def main():
    """Run the complete fetch and process pipeline"""
    data = await fetch_opinions_data()
    
    # Process to PostgreSQL if we got data
    if data['opinions'] or data['dockets']:
        process_to_postgres(data)

if __name__ == "__main__":
    asyncio.run(main())