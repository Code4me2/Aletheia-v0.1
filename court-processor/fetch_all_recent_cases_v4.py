#!/usr/bin/env python3
"""
Fetch ALL recent cases using CourtListener API V4
Most expansive data retrieval method
"""
import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import Json
from datetime import datetime, date, timedelta
import sys
import eyecite
from courts_db import courts as COURTS_LIST

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

# Focus on IP-heavy courts
IP_COURTS = {
    'cafc': 'Court of Appeals for the Federal Circuit',
    'txed': 'Eastern District of Texas',
    'ded': 'District of Delaware',
    'cand': 'Northern District of California',
    'cacd': 'Central District of California',
    'nysd': 'Southern District of New York',
    'ilnd': 'Northern District of Illinois',
    'txwd': 'Western District of Texas',  # Judge Albright
}

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )

def identify_ip_case(case_data):
    """Identify if a case is likely IP-related"""
    case_name = (case_data.get('case_name') or '').lower()
    nature = case_data.get('nature_of_suit') or ''
    cause = (case_data.get('cause') or '').lower()
    
    # IP nature of suit codes
    if nature in ['830', '840', '820', '835']:  # Patent, Trademark, Copyright, Patent (Abbreviated)
        return True
    
    # IP keywords in case name
    ip_keywords = [
        'patent', 'trademark', 'copyright', 'trade secret',
        'infringement', 'intellectual property', 'licensing',
        'royalty', 'technology', 'software'
    ]
    
    if any(keyword in case_name for keyword in ip_keywords):
        return True
    
    # Patent statute references in cause
    if '35:' in cause or '15:1051' in cause or '17:' in cause:  # Patent, Trademark, Copyright
        return True
    
    # Known IP entities
    ip_entities = [
        'llc v.', 'inc. v.', 'corporation v.', 'technologies',
        'systems', 'solutions', 'innovations', 'holdings'
    ]
    
    if any(entity in case_name for entity in ip_entities):
        # Additional check for tech-sounding names
        if 'v.' in case_name and not any(skip in case_name for skip in ['united states', 'commissioner', 'warden']):
            return True
    
    return False

async def fetch_all_from_court(session, court_id, court_name):
    """Fetch ALL recent cases from a court"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    
    # Get court info
    court_info = None
    for court in COURTS_LIST:
        if court.get('id') == court_id:
            court_info = court
            break
    
    print(f"\n📂 Fetching ALL cases from {court_name} ({court_id})...")
    sys.stdout.flush()
    
    # Start with cases from last 2 years
    date_from = (date.today() - timedelta(days=730)).isoformat()
    
    page = 1
    total_fetched = 0
    total_saved = 0
    ip_cases_found = 0
    
    while True:
        params = {
            'court': court_id,
            'date_filed__gte': date_from,
            'page_size': 100,  # Maximum allowed
            'page': page,
            'ordering': '-date_filed'
        }
        
        try:
            async with session.get(f'{BASE_URL}/dockets/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    results = data.get('results', [])
                    
                    if not results:
                        break
                    
                    total_fetched += len(results)
                    
                    # Process each case
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    for case in results:
                        try:
                            is_ip = identify_ip_case(case)
                            if is_ip:
                                ip_cases_found += 1
                            
                            case_number = case.get('docket_number', f"DOCKET-{case['id']}")
                            case_name = case.get('case_name', '')
                            
                            # Extract citations
                            citations_found = []
                            if case_name and is_ip:
                                try:
                                    citations = eyecite.get_citations(case_name)
                                    for cite in citations[:5]:
                                        citations_found.append({
                                            'text': str(cite),
                                            'type': type(cite).__name__
                                        })
                                except:
                                    pass
                            
                            content = f"""Case: {case_name}
Docket: {case_number}
Court: {court_name}
Filed: {case.get('date_filed', 'Unknown')}
Judge: {case.get('assigned_to_str', 'Not assigned')}
Nature of Suit: {case.get('nature_of_suit', 'Not specified')}
Cause: {case.get('cause', 'Not specified')}

[Full docket requires paid tier access]
"""
                            
                            metadata = {
                                'source': 'courtlistener_v4_bulk',
                                'court': court_id,
                                'court_name': court_name,
                                'docket_id': case['id'],
                                'case_name': case_name,
                                'date_filed': case.get('date_filed'),
                                'date_terminated': case.get('date_terminated'),
                                'assigned_to': case.get('assigned_to_str'),
                                'referred_to': case.get('referred_to_str'),
                                'nature_of_suit': case.get('nature_of_suit'),
                                'cause': case.get('cause'),
                                'jury_demand': case.get('jury_demand'),
                                'jurisdiction_type': case.get('jurisdiction_type'),
                                'fetch_timestamp': datetime.now().isoformat(),
                                'absolute_url': case.get('absolute_url')
                            }
                            
                            if is_ip:
                                metadata['case_type'] = 'intellectual_property'
                            
                            # Add FLP enhancements
                            if court_info:
                                metadata['court_standardized'] = {
                                    'id': court_info.get('id'),
                                    'name': court_info.get('name'),
                                    'full_name': court_info.get('full_name')
                                }
                            
                            if citations_found:
                                metadata['citations_extracted'] = citations_found
                            
                            # Save to database
                            cursor.execute("""
                                INSERT INTO court_documents (
                                    case_number, document_type, file_path, content, metadata, processed
                                ) VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                case_number,
                                'docket',
                                '',
                                content,
                                Json(metadata),
                                False
                            ))
                            
                            if cursor.rowcount > 0:
                                total_saved += 1
                            
                        except Exception as e:
                            print(f"    ✗ Error processing case: {e}")
                            conn.rollback()
                            continue
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    # Progress update
                    print(f"  Page {page}: Fetched {len(results)}, Saved {total_saved}, IP cases: {ip_cases_found}")
                    sys.stdout.flush()
                    
                    # Check if there are more pages
                    if not data.get('next'):
                        break
                    
                    page += 1
                    
                    # Limit pages to avoid excessive runtime
                    if page > 10:  # Max 1000 cases per court
                        print("  ⚠️  Page limit reached")
                        break
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                else:
                    print(f"  ❌ Error: Status {resp.status}")
                    break
                    
        except Exception as e:
            print(f"  ❌ Error fetching page {page}: {e}")
            break
    
    print(f"  📊 Summary: {total_fetched} fetched, {total_saved} saved, {ip_cases_found} IP cases")
    return total_saved, ip_cases_found

async def main():
    """Fetch all recent cases"""
    print("=" * 70)
    print("FETCHING ALL RECENT CASES WITH V4 API")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print("This will fetch up to 1000 cases per court")
    print("=" * 70)
    sys.stdout.flush()
    
    start_time = datetime.now()
    grand_total_saved = 0
    grand_total_ip = 0
    
    async with aiohttp.ClientSession() as session:
        for court_id, court_name in IP_COURTS.items():
            saved, ip_found = await fetch_all_from_court(session, court_id, court_name)
            grand_total_saved += saved
            grand_total_ip += ip_found
    
    # Final summary
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM court_documents")
    total_docs = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM court_documents 
        WHERE metadata->>'case_type' = 'intellectual_property'
    """)
    total_ip_db = cursor.fetchone()[0]
    
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"✅ Total cases saved in this run: {grand_total_saved}")
    print(f"✅ IP cases identified: {grand_total_ip}")
    print(f"📊 Total documents in database: {total_docs}")
    print(f"📊 Total IP cases in database: {total_ip_db}")
    print(f"⏱️  Total time: {(datetime.now() - start_time).total_seconds():.1f} seconds")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())