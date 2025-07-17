#!/usr/bin/env python3
"""
Fetch IP/Patent cases with progress tracking
"""
import asyncio
import aiohttp
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, date, timedelta
from pathlib import Path
import sys

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

# IP Courts of Interest
IP_COURTS = {
    'cafc': 'Court of Appeals for the Federal Circuit',
    'txed': 'Eastern District of Texas', 
    'ded': 'District of Delaware',
    'cand': 'Northern District of California',
    'cacd': 'Central District of California',
    'nysd': 'Southern District of New York',
    'ilnd': 'Northern District of Illinois',
}

class ProgressTracker:
    def __init__(self):
        self.start_time = datetime.now()
        self.courts_completed = 0
        self.total_cases = 0
        self.errors = 0
        
    def update(self, court_name, cases_found):
        self.courts_completed += 1
        self.total_cases += cases_found
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"[{elapsed:.1f}s] ✓ {court_name}: {cases_found} cases found")
        print(f"Progress: {self.courts_completed}/{len(IP_COURTS)} courts | Total cases: {self.total_cases}")
        sys.stdout.flush()

async def search_court_with_pagination(session, court_id, court_name, tracker):
    """Search for IP cases with pagination"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    date_from = (date.today() - timedelta(days=730)).isoformat()
    
    all_cases = []
    
    # Search for patent cases
    print(f"\n🔍 Searching {court_name} ({court_id})...")
    sys.stdout.flush()
    
    for keyword in ['patent', 'trademark', 'copyright']:
        page = 1
        while True:
            params = {
                'court': court_id,
                'date_filed__gte': date_from,
                'case_name__icontains': keyword,
                'page_size': 100,  # Max allowed
                'page': page,
                'ordering': '-date_filed'
            }
            
            try:
                async with session.get(f'{BASE_URL}/dockets/', headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get('results', [])
                        
                        # Filter for IP cases
                        ip_cases = [case for case in results 
                                   if any(term in case.get('case_name', '').lower() 
                                         for term in ['patent', 'trademark', 'copyright', 'v.', 'vs.'])]
                        
                        all_cases.extend(ip_cases)
                        
                        # Check if there are more pages
                        if not data.get('next'):
                            break
                        
                        page += 1
                        await asyncio.sleep(1)  # Rate limiting
                        
                        # Limit pages per keyword to avoid huge downloads
                        if page > 3:
                            break
                    else:
                        break
                        
            except Exception as e:
                print(f"  ✗ Error: {e}")
                tracker.errors += 1
                break
    
    # For Federal Circuit, also get opinions
    if court_id == 'cafc' and len(all_cases) < 50:
        try:
            params = {
                'court': court_id,
                'date_filed__gte': date_from,
                'page_size': 50,
                'ordering': '-date_filed'
            }
            
            async with session.get(f'{BASE_URL}/opinions/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    opinions = data.get('results', [])
                    for op in opinions:
                        op['_type'] = 'opinion'
                    all_cases.extend(opinions)
                    
        except Exception as e:
            print(f"  ✗ Opinion error: {e}")
    
    tracker.update(court_name, len(all_cases))
    return court_id, all_cases

async def fetch_with_progress():
    """Fetch IP cases with progress tracking"""
    print("=" * 70)
    print("FETCHING IP CASES FROM LAST 2 YEARS")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Courts: {', '.join(IP_COURTS.keys())}")
    print("This may take 10-30 minutes depending on the number of cases...")
    print("=" * 70)
    sys.stdout.flush()
    
    tracker = ProgressTracker()
    
    async with aiohttp.ClientSession() as session:
        # Process courts one at a time to show progress
        all_results = {}
        
        for court_id, court_name in IP_COURTS.items():
            court_id, cases = await search_court_with_pagination(session, court_id, court_name, tracker)
            if cases:
                all_results[court_id] = cases
                # Save intermediate results
                save_to_database(court_id, cases)
    
    # Final summary
    print("\n" + "=" * 70)
    print("FETCH COMPLETE")
    print("=" * 70)
    print(f"Total time: {(datetime.now() - tracker.start_time).total_seconds():.1f} seconds")
    print(f"Total cases found: {tracker.total_cases}")
    print(f"Errors: {tracker.errors}")
    
    return all_results

def save_to_database(court_id, cases):
    """Save cases to database immediately"""
    if not cases:
        return
        
    conn = psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    cursor = conn.cursor()
    
    court_name = IP_COURTS[court_id]
    added = 0
    
    for case in cases:
        try:
            if case.get('_type') == 'opinion':
                case_number = f"OPINION-{court_id.upper()}-{case['id']}"
                doc_type = 'opinion'
                content = f"""Federal Circuit Opinion
Court: {court_name}
Type: {case.get('type', 'Unknown')}
Author: {case.get('author_str', 'Not specified')}
Date: {case.get('date_created', 'Unknown')}

[Opinion text requires paid tier access]
"""
                metadata = {
                    'source': 'courtlistener_ip_opinions',
                    'court': court_id,
                    'opinion_id': case['id'],
                    'type': case.get('type'),
                    'author': case.get('author_str'),
                    'date_created': case.get('date_created'),
                    'case_type': 'intellectual_property'
                }
            else:
                case_number = case.get('docket_number', f"DOCKET-{case['id']}")
                doc_type = 'docket'
                content = f"""Case: {case.get('case_name', 'Unknown')}
Docket: {case_number}
Court: {court_name}
Filed: {case.get('date_filed', 'Unknown')}
Judge: {case.get('assigned_to_str', 'Not assigned')}

[Full docket requires paid tier access]
"""
                metadata = {
                    'source': 'courtlistener_ip_dockets',
                    'court': court_id,
                    'court_name': court_name,
                    'docket_id': case['id'],
                    'case_name': case.get('case_name'),
                    'date_filed': case.get('date_filed'),
                    'assigned_to': case.get('assigned_to_str'),
                    'nature_of_suit': case.get('nature_of_suit'),
                    'case_type': 'intellectual_property',
                    'absolute_url': case.get('absolute_url')
                }
            
            cursor.execute("""
                INSERT INTO court_documents (
                    case_number, document_type, file_path, content, metadata, processed
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_number) DO UPDATE 
                SET metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (case_number, doc_type, '', content, Json(metadata), False))
            
            added += 1
            
        except Exception as e:
            conn.rollback()
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    if added > 0:
        print(f"  💾 Saved {added} cases to database")
        sys.stdout.flush()

async def main():
    await fetch_with_progress()
    
    # Final database summary
    conn = psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            metadata->>'court' as court,
            COUNT(*) as count
        FROM court_documents 
        WHERE metadata->>'case_type' = 'intellectual_property'
        GROUP BY metadata->>'court'
        ORDER BY count DESC
    """)
    
    print("\n📊 IP CASES IN DATABASE BY COURT:")
    for row in cursor.fetchall():
        court_name = IP_COURTS.get(row[0], row[0])
        print(f"  {court_name}: {row[1]} cases")
    
    cursor.execute("""
        SELECT COUNT(*) FROM court_documents 
        WHERE metadata->>'case_type' = 'intellectual_property'
    """)
    total = cursor.fetchone()[0]
    print(f"\n✓ Total IP cases in database: {total}")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())