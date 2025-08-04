#!/usr/bin/env python3
import asyncio
from integrate_pdf_to_pipeline import PDFContentExtractor
import json

async def test():
    async with PDFContentExtractor() as extractor:
        test_doc = {
            'id': 1,
            'case_number': 'TEST',
            'content': 'No content available',
            'metadata': {
                'download_url': 'https://www.supremecourt.ohio.gov/rod/docs/pdf/7/2025/2025-Ohio-2578.pdf'
            }
        }
        
        result = await extractor.enrich_documents_with_pdf_content([test_doc])
        doc = result[0]
        
        print(f"Original content: '{test_doc['content']}'")
        print(f"New content length: {len(doc['content'])}")
        
        if len(doc['content']) > len(test_doc['content']):
            print("\nSuccess! PDF content extracted")
            print(f"First 200 chars: {doc['content'][:200]}...")
            print(f"\nExtraction metadata: {json.dumps(doc.get('metadata', {}).get('pdf_extraction', {}), indent=2)}")
        else:
            print("No new content extracted")

asyncio.run(test())