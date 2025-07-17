#!/usr/bin/env python3
"""
Simple fetch of opinions from CourtListener free tier
"""
import requests
import json
from datetime import datetime

# API Configuration
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
BASE_URL = 'https://www.courtlistener.com/api/rest/v3'

def fetch_recent_opinions():
    """Fetch recent opinions using free tier access"""
    print("=== Fetching Recent Opinions ===")
    
    headers = {
        'Authorization': f'Token {API_TOKEN}'
    }
    
    # Fetch recent opinions from Court of Appeals
    params = {
        'court': 'ca9',  # Ninth Circuit
        'date_filed__gte': '2024-01-01',
        'page_size': 10,
        'ordering': '-date_filed'
    }
    
    print("\nFetching opinions from Ninth Circuit...")
    response = requests.get(f'{BASE_URL}/opinions/', headers=headers, params=params)
    
    if response.status_code == 200:
        data = response.json()
        opinions = data.get('results', [])
        print(f"✓ Found {len(opinions)} opinions")
        
        # Save to file
        with open('test_data/opinions_sample.json', 'w') as f:
            json.dump(opinions, f, indent=2)
        
        # Process to database
        if opinions:
            process_opinions(opinions)
        
        return opinions
    else:
        print(f"✗ Error: {response.status_code}")
        return []

def process_opinions(opinions):
    """Save opinions to PostgreSQL"""
    import psycopg2
    from psycopg2.extras import Json
    
    print("\nSaving to database...")
    
    conn = psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )
    cursor = conn.cursor()
    
    added = 0
    for op in opinions[:5]:  # Just process first 5
        try:
            case_number = f"CA9-OPINION-{op['id']}"
            
            metadata = {
                'source': 'courtlistener_opinions',
                'opinion_id': op['id'],
                'type': op.get('type'),
                'author': op.get('author_str'),
                'date_created': op.get('date_created'),
                'court': 'ca9'
            }
            
            content = f"""Ninth Circuit Opinion
Type: {op.get('type', 'Unknown')}
Author: {op.get('author_str', 'Not specified')}
Date: {op.get('date_created', 'Unknown')}

[Full opinion text not available in free tier]
"""
            
            cursor.execute("""
                INSERT INTO court_documents (
                    case_number, document_type, file_path, content, metadata, processed
                ) VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (
                case_number,
                'opinion',
                '',
                content,
                Json(metadata),
                False
            ))
            added += 1
            
        except Exception as e:
            print(f"Error: {e}")
            conn.rollback()
    
    conn.commit()
    print(f"✓ Added {added} opinions to database")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    fetch_recent_opinions()