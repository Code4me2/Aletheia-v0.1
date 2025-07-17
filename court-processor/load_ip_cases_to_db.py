#!/usr/bin/env python3
"""
Load the fetched IP cases into PostgreSQL and process through FLP pipeline
"""
import json
import psycopg2
from psycopg2.extras import Json
from datetime import datetime
import eyecite
from courts_db import courts as COURTS_LIST

# Load the fetched data
with open('test_data/ip_cases/ip_cases_2025-07-16.json', 'r') as f:
    data = json.load(f)

print(f"Loaded data from: {data['fetch_date']}")
print(f"Total cases to process: {data['total_cases']}")

# Connect to database
conn = psycopg2.connect(
    host='db',
    database='aletheia',
    user='aletheia',
    password='aletheia123'
)
cursor = conn.cursor()

# Process each court's cases
total_added = 0
for court_id, cases in data['results'].items():
    court_name = data['courts'][court_id]
    print(f"\n📁 Processing {court_name} ({len(cases)} cases)...")
    
    # Find court in Courts-DB
    court_info = None
    for court in COURTS_LIST:
        if court.get('id') == court_id:
            court_info = court
            break
    
    added = 0
    for case in cases:
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
                    'fetch_date': data['fetch_date']
                }
            else:
                case_number = case.get('docket_number', f"DOCKET-{case['id']}")
                doc_type = 'docket'
                
                # Extract citations from case name
                case_name = case.get('case_name', '')
                citations_found = []
                if case_name:
                    try:
                        citations = eyecite.get_citations(case_name)
                        for cite in citations:
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
                    'fetch_date': data['fetch_date']
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
            
            # Commit every 100 records
            if added % 100 == 0:
                conn.commit()
                print(f"  💾 Saved {added} cases so far...")
                
        except Exception as e:
            print(f"  ✗ Error inserting case {case.get('id')}: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    print(f"  ✅ Added {added} cases from {court_name}")

# Final summary
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
print("SUMMARY - IP CASES IN DATABASE")
print("=" * 70)

for row in cursor.fetchall():
    court_name = data['courts'].get(row[0], row[0])
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
print(f"Successfully loaded {total_added} IP cases with FLP processing!")

cursor.close()
conn.close()