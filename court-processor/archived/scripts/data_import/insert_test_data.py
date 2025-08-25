#!/usr/bin/env python3
"""
Insert test data into database for pipeline testing
"""

import asyncio
import aiohttp
import os
import psycopg2
from psycopg2.extras import Json
from datetime import datetime

API_KEY = os.getenv('COURTLISTENER_API_KEY', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://aletheia:aletheia123@db:5432/aletheia')

async def fetch_courtlistener_data():
    """Fetch real data from CourtListener"""
    
    async with aiohttp.ClientSession() as session:
        # Fetch dockets
        print("Fetching dockets from CourtListener...")
        docket_url = "https://www.courtlistener.com/api/rest/v4/dockets/"
        headers = {"Authorization": f"Token {API_KEY}"}
        params = {
            "court__id": "txed",
            "order_by": "-date_modified",
            "page_size": 5
        }
        
        async with session.get(docket_url, headers=headers, params=params) as response:
            if response.status != 200:
                print(f"Failed to fetch dockets: {response.status}")
                return [], []
            
            data = await response.json()
            dockets = data.get('results', [])
            print(f"Fetched {len(dockets)} dockets")
        
        # Fetch opinions
        print("Fetching opinions from CourtListener...")
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

def insert_into_database(documents, doc_type):
    """Insert documents into the database"""
    
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    
    # Check if table exists and get its schema
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'court_documents' 
        AND table_schema = 'public'
    """)
    columns = [row[0] for row in cursor.fetchall()]
    
    if not columns:
        # Create table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public.court_documents (
                id SERIAL PRIMARY KEY,
                case_number VARCHAR(255) NOT NULL,
                document_type VARCHAR(100) DEFAULT 'opinion',
                content TEXT,
                metadata JSONB,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(case_number, document_type)
            )
        """)
    
    # Insert documents
    inserted = 0
    for doc in documents:
        try:
            # Create case number based on document
            if doc_type == 'docket':
                case_number = doc.get('docket_number', f"DOCKET-{doc.get('id', inserted)}")
            else:
                case_number = f"OPINION-{doc.get('id', inserted)}"
            
            # Prepare content based on type
            if doc_type == 'opinion':
                content = doc.get('plain_text') or doc.get('html_with_citations', str(doc))
            else:
                content = str(doc)
            
            cursor.execute("""
                INSERT INTO public.court_documents (case_number, document_type, content, metadata, processed)
                VALUES (%s, %s, %s, %s, %s)
            """, (case_number, doc_type, content, Json(doc), False))
            
            inserted += 1
        except Exception as e:
            print(f"Error inserting document: {e}")
            conn.rollback()
            continue
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return inserted

async def main():
    print("Inserting Test Data for Pipeline Testing")
    print("=" * 60)
    
    # Fetch data from CourtListener
    dockets, opinions = await fetch_courtlistener_data()
    
    if not dockets and not opinions:
        print("No data fetched from CourtListener")
        return
    
    # Insert into database
    print("\nInserting into database...")
    
    docket_count = insert_into_database(dockets, 'docket')
    print(f"Inserted {docket_count} dockets")
    
    opinion_count = insert_into_database(opinions, 'opinion')
    print(f"Inserted {opinion_count} opinions")
    
    print(f"\nTotal documents inserted: {docket_count + opinion_count}")
    print("Ready to run pipeline test!")

if __name__ == "__main__":
    asyncio.run(main())