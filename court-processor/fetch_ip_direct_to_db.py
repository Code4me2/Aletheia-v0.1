#!/usr/bin/env python3
"""
Fetch IP cases and save DIRECTLY to PostgreSQL with FLP pipeline processing
No intermediate JSON files - straight to database
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

def get_db_connection():
    """Get a fresh database connection"""
    return psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )

def process_and_save_case(case, court_id, court_name, court_info=None):
    """Process a single case through FLP pipeline and save to DB"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Determine if it's an opinion or docket
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
                'case_type': 'intellectual_property',
                'fetch_timestamp': datetime.now().isoformat()
            }
        else:
            case_number = case.get('docket_number', f"DOCKET-{case['id']}")
            doc_type = 'docket'
            case_name = case.get('case_name', '')
            
            # Extract citations using Eyecite
            citations_found = []
            if case_name:
                try:
                    citations = eyecite.get_citations(case_name)
                    for cite in citations[:5]:  # Limit to first 5
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

[Full docket requires paid tier access]
"""
            
            metadata = {
                'source': 'courtlistener_ip_dockets',
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
                'case_type': 'intellectual_property',
                'absolute_url': case.get('absolute_url'),
                'fetch_timestamp': datetime.now().isoformat()
            }
            
            # Add FLP enhancements
            if court_info:
                metadata['court_standardized'] = {
                    'id': court_info.get('id'),
                    'name': court_info.get('name'),
                    'full_name': court_info.get('full_name'),
                    'citation_string': court_info.get('citation_string')
                }
            
            if citations_found:
                metadata['citations_extracted'] = citations_found
                metadata['citation_count'] = len(citations_found)
            
            metadata['flp_processed'] = {
                'timestamp': datetime.now().isoformat(),
                'components': ['courts_db', 'eyecite']
            }
        
        # Insert into database
        cursor.execute("""
            INSERT INTO court_documents (
                case_number, document_type, file_path, content, metadata, processed
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            case_number,
            doc_type,
            '',
            content,
            Json(metadata),
            False
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        conn.rollback()
        cursor.close()
        conn.close()
        print(f"    ✗ Error saving {case_number}: {e}")
        return False

async def fetch_court_ip_cases(session, court_id, court_name):
    """Fetch and immediately save IP cases from a court"""
    headers = {'Authorization': f'Token {API_TOKEN}'}
    date_from = (date.today() - timedelta(days=730)).isoformat()
    
    # Get court info from Courts-DB
    court_info = None
    for court in COURTS_LIST:
        if court.get('id') == court_id:
            court_info = court
            break
    
    print(f"\n🔍 Fetching from {court_name} ({court_id})...")
    sys.stdout.flush()
    
    saved_count = 0
    
    # Search for different IP-related keywords
    for keyword in ['patent', 'trademark', 'copyright']:
        page = 1
        keyword_count = 0
        
        while page <= 5:  # Limit pages per keyword
            params = {
                'court': court_id,
                'date_filed__gte': date_from,
                'case_name__icontains': keyword,
                'page_size': 50,
                'page': page,
                'ordering': '-date_filed'
            }
            
            try:
                async with session.get(f'{BASE_URL}/dockets/', headers=headers, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get('results', [])
                        
                        # Process and save each case immediately
                        for case in results:
                            # Filter for actual IP cases
                            case_name_lower = case.get('case_name', '').lower()
                            if any(term in case_name_lower for term in ['patent', 'trademark', 'copyright', 
                                                                         'intellectual property', 'infringement']):
                                if process_and_save_case(case, court_id, court_name, court_info):
                                    saved_count += 1
                                    keyword_count += 1
                        
                        # Check if there are more pages
                        if not data.get('next') or keyword_count >= 100:
                            break
                        
                        page += 1
                        await asyncio.sleep(0.5)  # Rate limiting
                    else:
                        break
                        
            except Exception as e:
                print(f"  ✗ Error fetching {keyword} cases: {e}")
                break
        
        if keyword_count > 0:
            print(f"  ✓ Saved {keyword_count} {keyword} cases")
    
    # For Federal Circuit, also get opinions
    if court_id == 'cafc':
        print(f"  📄 Fetching opinions from {court_name}...")
        params = {
            'court': court_id,
            'date_filed__gte': date_from,
            'page_size': 50,
            'ordering': '-date_filed'
        }
        
        try:
            async with session.get(f'{BASE_URL}/opinions/', headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    opinions = data.get('results', [])
                    
                    opinion_count = 0
                    for op in opinions[:50]:  # Limit opinions
                        op['_type'] = 'opinion'
                        if process_and_save_case(op, court_id, court_name, court_info):
                            saved_count += 1
                            opinion_count += 1
                    
                    if opinion_count > 0:
                        print(f"  ✓ Saved {opinion_count} opinions")
                        
        except Exception as e:
            print(f"  ✗ Opinion error: {e}")
    
    print(f"  📊 Total saved from {court_name}: {saved_count}")
    return saved_count

async def main():
    """Main execution"""
    print("=" * 70)
    print("FETCHING IP CASES DIRECTLY TO POSTGRESQL")
    print("=" * 70)
    print(f"Started: {datetime.now()}")
    print(f"Courts: {', '.join(IP_COURTS.keys())}")
    print("Processing through FLP pipeline (Courts-DB, Eyecite)")
    print("=" * 70)
    sys.stdout.flush()
    
    start_time = datetime.now()
    total_saved = 0
    
    async with aiohttp.ClientSession() as session:
        # Process courts sequentially to avoid overwhelming the API
        for court_id, court_name in IP_COURTS.items():
            count = await fetch_court_ip_cases(session, court_id, court_name)
            total_saved += count
            
            # Show running total
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"\n⏱️  Elapsed: {elapsed:.1f}s | Total saved so far: {total_saved}")
            sys.stdout.flush()
    
    # Final database summary
    conn = get_db_connection()
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
    
    print("\n" + "=" * 70)
    print("FINAL SUMMARY - IP CASES IN DATABASE")
    print("=" * 70)
    
    for row in cursor.fetchall():
        court_name = IP_COURTS.get(row[0], row[0])
        print(f"{court_name}: {row[1]} cases")
    
    cursor.execute("SELECT COUNT(*) FROM court_documents")
    total_all = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM court_documents 
        WHERE metadata->>'case_type' = 'intellectual_property'
    """)
    total_ip = cursor.fetchone()[0]
    
    print(f"\nTotal IP cases: {total_ip}")
    print(f"Total all documents: {total_all}")
    print(f"\n✅ Successfully fetched and processed {total_saved} IP cases!")
    print(f"⏱️  Total time: {(datetime.now() - start_time).total_seconds():.1f} seconds")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    asyncio.run(main())