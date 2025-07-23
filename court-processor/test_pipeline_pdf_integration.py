#!/usr/bin/env python3
"""
Test the integrated pipeline with automatic PDF extraction

This demonstrates how the central pipeline now optionally extracts
PDFs when documents are missing content.
"""

import asyncio
import logging
import os
import json
from datetime import datetime

# Set API key for testing
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_pipeline_with_pdf_extraction():
    """Test the pipeline with PDF extraction enabled"""
    
    logger.info("\n" + "="*80)
    logger.info("TESTING PIPELINE WITH AUTOMATIC PDF EXTRACTION")
    logger.info("="*80)
    
    # Create pipeline instance
    pipeline = RobustElevenStagePipeline()
    
    # First, let's insert some test documents without content
    # to simulate documents that need PDF extraction
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert test documents with PDF URLs but no content
        test_docs = [
            {
                'case_number': 'PDF-TEST-001',
                'case_name': 'Test Supreme Court Opinion',
                'document_type': 'opinion',
                'content': '',  # Empty content
                'metadata': json.dumps({
                    'download_url': 'https://www.supremecourt.gov/opinions/19pdf/18-1334_8m58.pdf',
                    'court_id': 'scotus',
                    'source': 'test'
                })
            },
            {
                'case_number': 'PDF-TEST-002', 
                'case_name': 'Test Circuit Opinion',
                'document_type': 'opinion',
                'content': 'Short text',  # Minimal content
                'metadata': json.dumps({
                    'download_url': 'http://www.ca5.uscourts.gov/opinions/pub/24/24-10519-CR1.pdf',
                    'court_id': 'ca5',
                    'source': 'test'
                })
            }
        ]
        
        for doc in test_docs:
            cursor.execute("""
                INSERT INTO public.court_documents 
                (case_number, case_name, document_type, content, metadata)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (case_number) DO UPDATE
                SET content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, (
                doc['case_number'],
                doc['case_name'],
                doc['document_type'],
                doc['content'],
                doc['metadata']
            ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✓ Inserted test documents with empty/minimal content")
        
    except Exception as e:
        logger.warning(f"Database setup skipped: {e}")
        logger.info("Will test with mock documents instead")
    
    # Test 1: Run pipeline WITHOUT PDF extraction
    logger.info("\n\n1. Running pipeline WITHOUT PDF extraction...")
    
    results_without_pdf = await pipeline.process_batch(
        limit=10,
        extract_pdfs=False  # PDF extraction disabled
    )
    
    if results_without_pdf['success']:
        logger.info(f"  Documents processed: {results_without_pdf['statistics']['documents_processed']}")
        logger.info(f"  Completeness score: {results_without_pdf['verification']['completeness_score']:.1f}%")
        
        # Check how many documents have minimal content
        docs_with_content = sum(1 for doc in results_without_pdf.get('processed_documents', [])
                               if doc.get('content') and len(doc.get('content', '')) > 100)
        logger.info(f"  Documents with substantial content: {docs_with_content}")
    
    # Test 2: Run pipeline WITH PDF extraction
    logger.info("\n\n2. Running pipeline WITH PDF extraction enabled...")
    
    results_with_pdf = await pipeline.process_batch(
        limit=10,
        extract_pdfs=True  # PDF extraction enabled!
    )
    
    if results_with_pdf['success']:
        logger.info(f"  Documents processed: {results_with_pdf['statistics']['documents_processed']}")
        logger.info(f"  Completeness score: {results_with_pdf['verification']['completeness_score']:.1f}%")
        
        # Check improvement
        docs_with_content_after = sum(1 for doc in results_with_pdf.get('processed_documents', [])
                                     if doc.get('content') and len(doc.get('content', '')) > 100)
        logger.info(f"  Documents with substantial content: {docs_with_content_after}")
        
        # Show which documents got PDF content
        for doc in results_with_pdf.get('processed_documents', []):
            metadata = doc.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            if metadata.get('pdf_extraction', {}).get('extracted'):
                logger.info(f"\n  ✓ PDF extracted for: {doc.get('case_number')}")
                logger.info(f"    Content length: {metadata['pdf_extraction']['content_length']:,} chars")
                logger.info(f"    Page count: {metadata['pdf_extraction'].get('page_count', 'unknown')}")
    
    # Compare results
    logger.info("\n\n3. COMPARISON")
    logger.info("="*60)
    
    if results_without_pdf['success'] and results_with_pdf['success']:
        score_without = results_without_pdf['verification']['completeness_score']
        score_with = results_with_pdf['verification']['completeness_score']
        
        logger.info(f"Completeness without PDF extraction: {score_without:.1f}%")
        logger.info(f"Completeness with PDF extraction: {score_with:.1f}%")
        logger.info(f"Improvement: +{score_with - score_without:.1f}%")
    
    # Save results
    output_file = f"pipeline_pdf_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'results_without_pdf': results_without_pdf['statistics'] if results_without_pdf['success'] else None,
            'results_with_pdf': results_with_pdf['statistics'] if results_with_pdf['success'] else None,
            'improvement': {
                'completeness_gain': score_with - score_without if results_with_pdf['success'] else 0
            }
        }, f, indent=2, default=str)
    
    logger.info(f"\nResults saved to: {output_file}")
    
    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETE")
    logger.info("="*80)


async def test_without_database():
    """Test PDF extraction without database dependency"""
    
    logger.info("\n" + "="*80)
    logger.info("TESTING PDF EXTRACTION (NO DATABASE)")
    logger.info("="*80)
    
    from integrate_pdf_to_pipeline import PDFContentExtractor
    
    # Create test documents
    test_documents = [
        {
            'id': 1,
            'case_number': 'TEST-SCOTUS-001',
            'content': '',  # No content
            'metadata': {
                'download_url': 'https://www.supremecourt.gov/opinions/19pdf/18-1334_8m58.pdf',
                'court_id': 'scotus'
            }
        },
        {
            'id': 2,
            'case_number': 'TEST-CA5-001',
            'content': 'Too short',  # Minimal content
            'metadata': {
                'download_url': 'http://www.ca5.uscourts.gov/opinions/pub/24/24-10519-CR1.pdf',
                'court_id': 'ca5'
            }
        },
        {
            'id': 3,
            'case_number': 'TEST-GOOD-001',
            'content': 'This document already has sufficient content for processing. ' * 20,
            'metadata': {
                'court_id': 'txed'
            }
        }
    ]
    
    # Test PDF extraction
    async with PDFContentExtractor() as extractor:
        enriched_docs = await extractor.enrich_documents_with_pdf_content(test_documents)
        
        # Show results
        stats = extractor.get_statistics()
        logger.info(f"\nExtraction Statistics:")
        logger.info(f"  Documents checked: {stats['documents_checked']}")
        logger.info(f"  Missing content: {stats['documents_missing_content']}")
        logger.info(f"  PDFs found: {stats['pdfs_found']}")
        logger.info(f"  PDFs extracted: {stats['pdfs_extracted']}")
        logger.info(f"  Success rate: {stats['extraction_success_rate']:.1f}%")
        
        # Show enriched documents
        for doc in enriched_docs:
            logger.info(f"\nDocument: {doc['case_number']}")
            logger.info(f"  Original content length: {len(test_documents[doc['id']-1].get('content', ''))}")
            logger.info(f"  Enriched content length: {len(doc.get('content', ''))}")
            
            if doc.get('metadata', {}).get('pdf_extraction', {}).get('extracted'):
                logger.info(f"  ✓ PDF extracted successfully!")


if __name__ == "__main__":
    # Check if we have database access
    if os.getenv('DATABASE_URL'):
        asyncio.run(test_pipeline_with_pdf_extraction())
    else:
        # Run simpler test without database
        asyncio.run(test_without_database())