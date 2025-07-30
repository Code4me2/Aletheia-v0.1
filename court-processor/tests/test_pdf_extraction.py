#!/usr/bin/env python3
import asyncio
from integrate_pdf_to_pipeline import PDFContentExtractor
from services.database import get_db_connection
import json
import logging

logging.basicConfig(level=logging.INFO)

async def test_pdf_extraction():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get the test document
    cursor.execute('''
        SELECT id, case_number, content, metadata
        FROM public.court_documents
        WHERE case_number = 'OPINION-11105393'
    ''')
    
    row = cursor.fetchone()
    if not row:
        print('Test document not found')
        return
        
    document = {
        'id': row[0],
        'case_number': row[1], 
        'content': row[2],
        'metadata': row[3]
    }
    
    print(f'Testing document: {document["case_number"]}')
    print(f'Current content: "{document["content"]}"')
    
    cursor.close()
    conn.close()
    
    async with PDFContentExtractor() as extractor:
        enriched = await extractor.enrich_documents_with_pdf_content([document])
        
        stats = extractor.get_statistics()
        print(f'\nExtraction Results:')
        for key, value in stats.items():
            print(f'  {key}: {value}')
        
        if enriched[0].get('content') != document['content']:
            print(f'\nSuccess! Extracted {len(enriched[0]["content"])} characters')
            print(f'Preview: {enriched[0]["content"][:300]}...')
            
            # Update database with extracted content
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE public.court_documents
                SET content = %s,
                    metadata = %s
                WHERE id = %s
            ''', (
                enriched[0]['content'],
                json.dumps(enriched[0]['metadata']),
                enriched[0]['id']
            ))
            conn.commit()
            cursor.close()
            conn.close()
            print('\nDatabase updated with extracted content')

if __name__ == "__main__":
    asyncio.run(test_pdf_extraction())