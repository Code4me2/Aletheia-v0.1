#!/usr/bin/env python3
"""
Test the complete pipeline: CourtListener → PDF Download → Text Extraction → Database

This demonstrates the full functionality including:
1. Finding documents that need PDF processing
2. Downloading PDFs
3. Extracting text (with OCR fallback if needed)
4. Storing in database with proper metadata
"""

import asyncio
import os
import logging
from datetime import datetime
import json

os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from courtlistener_pdf_pipeline import CourtListenerPDFPipeline
from services.courtlistener_service import CourtListenerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_complete_pdf_test():
    """Run a complete test of the PDF pipeline"""
    
    logger.info("\n" + "="*80)
    logger.info("COMPLETE PDF PIPELINE TEST")
    logger.info("="*80)
    
    stats = {
        'total_documents': 0,
        'with_plain_text': 0,
        'pdfs_downloaded': 0,
        'text_extracted': 0,
        'extraction_failed': 0,
        'total_chars': 0
    }
    
    async with CourtListenerPDFPipeline() as pipeline:
        # 1. Search for documents across multiple courts
        logger.info("\n1. SEARCHING FOR DOCUMENTS...")
        
        test_courts = [
            ('scotus', '2010-01-01'),  # Older SCOTUS opinions
            ('ca9', '2024-01-01'),     # Recent 9th Circuit
            ('txed', '2024-01-01'),    # Recent E.D. Texas
        ]
        
        all_documents = []
        
        for court_id, date_after in test_courts:
            logger.info(f"\nSearching {court_id} after {date_after}...")
            
            opinions = await pipeline.cl_service.fetch_opinions(
                court_id=court_id,
                date_filed_after=date_after,
                max_results=10
            )
            
            for opinion in opinions:
                stats['total_documents'] += 1
                
                # Analyze what we have
                has_text = bool(opinion.get('plain_text'))
                has_pdf = bool(opinion.get('download_url'))
                
                if has_text:
                    stats['with_plain_text'] += 1
                
                logger.info(f"\n  Opinion {opinion.get('id')}:")
                logger.info(f"    Has plain_text: {has_text} ({len(opinion.get('plain_text', ''))} chars)")
                logger.info(f"    Has PDF URL: {has_pdf}")
                
                # Process the document
                processed_doc = await pipeline._process_opinion(opinion, court_id)
                
                if processed_doc:
                    all_documents.append(processed_doc)
                    
                    # Track extraction stats
                    extraction_method = processed_doc['metadata'].get('extraction_method', '')
                    if extraction_method == 'plain_text_field':
                        logger.info(f"    Used existing text")
                    elif extraction_method in ['pymupdf', 'ocr']:
                        stats['pdfs_downloaded'] += 1
                        stats['text_extracted'] += 1
                        logger.info(f"    ✓ Downloaded and extracted PDF via {extraction_method}")
                    
                    stats['total_chars'] += len(processed_doc['content'])
        
        # 2. Summary of results
        logger.info("\n\n2. EXTRACTION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total documents found: {stats['total_documents']}")
        logger.info(f"Documents with plain_text: {stats['with_plain_text']}")
        logger.info(f"PDFs downloaded: {stats['pdfs_downloaded']}")
        logger.info(f"Text extracted from PDFs: {stats['text_extracted']}")
        logger.info(f"Total characters extracted: {stats['total_chars']:,}")
        
        # 3. Show sample of extracted content
        logger.info("\n\n3. SAMPLE EXTRACTED CONTENT")
        logger.info("="*60)
        
        # Find documents that required PDF download
        pdf_extracted = [d for d in all_documents 
                        if d['metadata'].get('extraction_method') not in ['plain_text_field', None]]
        
        if pdf_extracted:
            logger.info(f"\nShowing {len(pdf_extracted)} documents that required PDF download:")
            for doc in pdf_extracted[:3]:  # Show first 3
                logger.info(f"\n  Case: {doc['case_name']}")
                logger.info(f"  Court: {doc['metadata']['court_id']}")
                logger.info(f"  Pages: {doc['metadata'].get('page_count', 'unknown')}")
                logger.info(f"  Text preview: {doc['content'][:200]}...")
        else:
            logger.info("\nAll documents had pre-extracted text. No PDF downloads were needed.")
        
        # 4. Save results
        output_file = f"pdf_pipeline_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Save summary and sample documents
        test_results = {
            'test_date': datetime.now().isoformat(),
            'statistics': stats,
            'sample_documents': all_documents[:5],  # Save first 5 for inspection
            'pdf_extracted_documents': pdf_extracted
        }
        
        with open(output_file, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        logger.info(f"\n\n4. RESULTS SAVED")
        logger.info(f"Full results saved to: {output_file}")
    
    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)
    
    # Final summary
    if stats['pdfs_downloaded'] > 0:
        logger.info(f"\n✅ Successfully demonstrated PDF download and extraction!")
        logger.info(f"   Downloaded {stats['pdfs_downloaded']} PDFs")
        logger.info(f"   Extracted {stats['text_extracted']} documents")
    else:
        logger.info(f"\n⚠️  All {stats['total_documents']} documents had pre-extracted text.")
        logger.info(f"   No PDF downloads were needed, but the pipeline is ready when needed.")


if __name__ == "__main__":
    asyncio.run(run_complete_pdf_test())