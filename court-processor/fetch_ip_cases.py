#!/usr/bin/env python3
"""
Fetch IP/Patent cases from CourtListener for the last 2 years
"""
import asyncio
import aiohttp
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, date, timedelta
from pathlib import Path

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

# IP Courts of Interest
IP_COURTS = {
    'cafc': 'Court of Appeals for the Federal Circuit',  # Main patent appeals court
    'txed': 'Eastern District of Texas',  # Major patent litigation venue
    'ded': 'District of Delaware',  # Corporate HQ venue, many patent cases
    'cand': 'Northern District of California',  # Tech companies
    'cacd': 'Central District of California',  # LA tech scene
    'nysd': 'Southern District of New York',  # Financial/pharma patents
    'ilnd': 'Northern District of Illinois',  # Chicago business hub
}

# Search terms for IP cases
IP_KEYWORDS = [
    'patent', 'trademark', 'copyright', 'intellectual property',
    'infringement', 'trade secret', '35 U.S.C', 'Lanham Act',
    'DMCA', 'royalty', 'licensing'
]

async def search_ip_cases(session, court_id, court_name):
    """Search for IP cases in a specific court"""
    print(f"\n🔍 Searching {court_name} ({court_id})...")
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    # Date range: last 2 years
    date_from = (date.today() - timedelta(days=730)).isoformat()
    
    all_cases = []
    
    # Try searching for patent-related cases
    for keyword in ['patent', 'trademark', 'copyright']:
        params = {
            'court': court_id,
            'date_filed__gte': date_from,
            'case_name__icontains': keyword,
            'page_size': 20,
            'ordering': '-date_filed'
        }
        
        try:
            async with session.get(f'{BASE_URL}/dockets/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get('results', [])
                    
                    # Filter for actual IP cases
                    ip_cases = []
                    for case in results:
                        case_name_lower = case.get('case_name', '').lower()
                        # Check if it's actually an IP case
                        if any(term in case_name_lower for term in ['patent', 'trademark', 'copyright', 
                                                                     'trade secret', 'intellectual property']):
                            ip_cases.append(case)
                    
                    if ip_cases:
                        print(f"  ✓ Found {len(ip_cases)} {keyword} cases")
                        all_cases.extend(ip_cases)
                    
                    await asyncio.sleep(0.5)  # Rate limiting
                    
        except Exception as e:
            print(f"  ✗ Error searching {keyword}: {e}")
    
    # Also try opinions endpoint for Federal Circuit
    if court_id == 'cafc':
        print(f"  📄 Fetching recent opinions from {court_name}...")
        params = {
            'court': court_id,
            'date_filed__gte': date_from,
            'page_size': 30,
            'ordering': '-date_filed'
        }
        
        try:
            async with session.get(f'{BASE_URL}/opinions/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    opinions = data.get('results', [])
                    if opinions:
                        print(f"  ✓ Found {len(opinions)} recent opinions")
                        # Add opinions as a different type
                        for op in opinions:
                            op['_type'] = 'opinion'
                        all_cases.extend(opinions)
                        
        except Exception as e:
            print(f"  ✗ Error fetching opinions: {e}")
    
    return court_id, all_cases

async def fetch_all_ip_cases():
    """Fetch IP cases from all courts of interest"""
    print("=" * 60)
    print("Fetching IP Cases from Last 2 Years")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    # Create data directory
    data_dir = Path("test_data/ip_cases")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    all_results = {}
    
    async with aiohttp.ClientSession() as session:
        # Fetch from all courts concurrently
        tasks = []
        for court_id, court_name in IP_COURTS.items():
            task = search_ip_cases(session, court_id, court_name)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        for court_id, cases in results:
            if cases:
                all_results[court_id] = cases
    
    # Save results
    output_file = data_dir / f'ip_cases_{date.today().isoformat()}.json'
    with open(output_file, 'w') as f:
        json.dump({
            'fetch_date': datetime.now().isoformat(),
            'courts': IP_COURTS,
            'results': all_results,
            'total_cases': sum(len(cases) for cases in all_results.values())
        }, f, indent=2)
    
    print(f"\n✓ Saved results to: {output_file}")
    
    return all_results

def process_to_postgres(results):
    """Save IP cases to PostgreSQL"""
    print("\n" + "=" * 60)
    print("Saving IP Cases to Database")
    print("=" * 60)
    
    conn = psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    cursor = conn.cursor()
    
    total_added = 0
    
    for court_id, cases in results.items():
        court_name = IP_COURTS[court_id]
        print(f"\n📁 Processing {court_name} ({len(cases)} cases)...")
        
        added = 0
        for case in cases:
            try:
                # Check if it's an opinion or docket
                if case.get('_type') == 'opinion':
                    # Process as opinion
                    case_number = f"OPINION-{court_id.upper()}-{case['id']}"
                    doc_type = 'opinion'
                    
                    content = f"""Federal Circuit Opinion
Court: {court_name}
Type: {case.get('type', 'Unknown')}
Author: {case.get('author_str', 'Not specified')}
Date: {case.get('date_created', 'Unknown')}

[Opinion text would be available with paid tier access]
"""
                    
                    metadata = {
                        'source': 'courtlistener_ip_opinions',
                        'court': court_id,
                        'opinion_id': case['id'],
                        'type': case.get('type'),
                        'author': case.get('author_str'),
                        'date_created': case.get('date_created'),
                        'fetch_date': datetime.now().isoformat(),
                        'case_type': 'intellectual_property'
                    }
                    
                else:
                    # Process as docket
                    case_number = case.get('docket_number', f"DOCKET-{case['id']}")
                    doc_type = 'docket'
                    
                    content = f"""Case: {case.get('case_name', 'Unknown')}
Docket Number: {case_number}
Court: {court_name} ({court_id})
Filed: {case.get('date_filed', 'Unknown')}
Judge: {case.get('assigned_to_str', 'Not assigned')}
Nature of Suit: {case.get('nature_of_suit', 'Not specified')}
Cause: {case.get('cause', 'Not specified')}

[Full docket entries would be available with paid tier access]
"""
                    
                    metadata = {
                        'source': 'courtlistener_ip_dockets',
                        'court': court_id,
                        'court_name': court_name,
                        'docket_id': case['id'],
                        'case_name': case.get('case_name'),
                        'date_filed': case.get('date_filed'),
                        'date_terminated': case.get('date_terminated'),
                        'assigned_to': case.get('assigned_to_str'),
                        'referred_to': case.get('referred_to_str'),
                        'nature_of_suit': case.get('nature_of_suit'),
                        'cause': case.get('cause'),
                        'jury_demand': case.get('jury_demand'),
                        'jurisdiction_type': case.get('jurisdiction_type'),
                        'fetch_date': datetime.now().isoformat(),
                        'case_type': 'intellectual_property',
                        'absolute_url': case.get('absolute_url')
                    }
                
                # Insert into database
                cursor.execute("""
                    INSERT INTO court_documents (
                        case_number, document_type, file_path, content, metadata, processed
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (case_number) DO UPDATE 
                    SET metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    case_number,
                    doc_type,
                    '',
                    content,
                    Json(metadata),
                    False
                ))
                
                added += 1
                total_added += 1
                
            except Exception as e:
                print(f"  ✗ Error inserting case {case.get('id')}: {e}")
                conn.rollback()
                continue
        
        conn.commit()
        print(f"  ✓ Added {added} cases from {court_name}")
    
    # Summary
    cursor.execute("""
        SELECT COUNT(*) 
        FROM court_documents 
        WHERE metadata->>'case_type' = 'intellectual_property'
    """)
    total_ip_cases = cursor.fetchone()[0]
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"✓ Total IP cases added in this run: {total_added}")
    print(f"✓ Total IP cases in database: {total_ip_cases}")
    
    cursor.close()
    conn.close()

async def main():
    """Run the complete IP case fetch pipeline"""
    results = await fetch_all_ip_cases()
    
    if results:
        process_to_postgres(results)
    else:
        print("\n⚠️  No IP cases found")

if __name__ == "__main__":
    asyncio.run(main())