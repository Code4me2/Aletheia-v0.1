#!/usr/bin/env python3
"""
Simple integration to add PDF extraction to the existing pipeline

This module provides a clean way to enhance the existing eleven-stage pipeline
with PDF extraction capabilities without modifying the original code.
"""

import asyncio
import aiohttp
import logging
import tempfile
import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class PDFContentExtractor:
    """
    Standalone PDF content extractor that can be integrated into any pipeline
    """
    
    def __init__(self, ocr_enabled: bool = True):
        self.pdf_processor = PDFProcessor(ocr_enabled=ocr_enabled)
        self.session = None
        self.stats = {
            'documents_checked': 0,
            'documents_missing_content': 0,
            'pdfs_found': 0,
            'pdfs_downloaded': 0,
            'pdfs_extracted': 0,
            'extraction_failed': 0,
            'total_chars_extracted': 0
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def enrich_documents_with_pdf_content(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Check documents and extract PDF content for those missing text
        
        Args:
            documents: List of document dictionaries
            
        Returns:
            Enhanced documents with PDF content extracted where needed
        """
        enriched_documents = []
        
        for doc in documents:
            self.stats['documents_checked'] += 1
            
            # Check if document needs content extraction
            content = doc.get('content', '')
            needs_extraction = (
                not content or 
                len(str(content).strip()) < 50 or
                content == 'No content available'
            )
            
            if needs_extraction:
                self.stats['documents_missing_content'] += 1
                logger.info(f"\nDocument {doc.get('case_number', doc.get('id', 'unknown'))} is missing content")
                
                # Try to extract from PDF
                enhanced_doc = await self._extract_pdf_for_document(doc)
                enriched_documents.append(enhanced_doc)
            else:
                enriched_documents.append(doc)
        
        return enriched_documents
    
    async def _extract_pdf_for_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract PDF content for a single document"""
        
        # Parse metadata if it's a string
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Find PDF URL
        pdf_url = self._find_pdf_url(document, metadata)
        
        if pdf_url:
            self.stats['pdfs_found'] += 1
            logger.info(f"  Found PDF URL: {pdf_url}")
            
            # Download and extract
            extraction_result = await self._download_and_extract(pdf_url)
            
            if extraction_result['success']:
                # Update document with extracted content
                document['content'] = extraction_result['text']
                
                # Add extraction metadata
                if not isinstance(document.get('metadata'), dict):
                    document['metadata'] = {}
                
                document['metadata']['pdf_extraction'] = {
                    'extracted': True,
                    'extraction_date': datetime.now().isoformat(),
                    'extraction_method': extraction_result['method'],
                    'page_count': extraction_result.get('page_count', 0),
                    'content_length': len(extraction_result['text']),
                    'pdf_url': pdf_url
                }
                
                self.stats['pdfs_extracted'] += 1
                self.stats['total_chars_extracted'] += len(extraction_result['text'])
                
                logger.info(f"  ✓ Extracted {len(extraction_result['text'])} characters")
            else:
                self.stats['extraction_failed'] += 1
                logger.warning(f"  ✗ Extraction failed: {extraction_result.get('error', 'Unknown error')}")
                
                # Add failure metadata
                if not isinstance(document.get('metadata'), dict):
                    document['metadata'] = {}
                    
                document['metadata']['pdf_extraction'] = {
                    'extracted': False,
                    'extraction_date': datetime.now().isoformat(),
                    'error': extraction_result.get('error', 'Unknown error'),
                    'pdf_url': pdf_url
                }
        else:
            logger.info(f"  No PDF URL found")
        
        return document
    
    def _find_pdf_url(self, document: Dict[str, Any], metadata: Dict[str, Any]) -> Optional[str]:
        """Find PDF URL from various possible locations"""
        
        # Direct URL fields
        pdf_url = (
            document.get('download_url') or
            document.get('pdf_url') or
            metadata.get('download_url') or
            metadata.get('pdf_url') or
            metadata.get('absolute_url')
        )
        
        # RECAP documents use filepath_local
        if not pdf_url and metadata.get('filepath_local'):
            pdf_url = f"https://storage.courtlistener.com/{metadata['filepath_local']}"
        
        # CourtListener cluster data
        if not pdf_url and metadata.get('cluster_data', {}).get('filepath_local'):
            pdf_url = f"https://storage.courtlistener.com/{metadata['cluster_data']['filepath_local']}"
        
        return pdf_url
    
    async def _download_and_extract(self, pdf_url: str) -> Dict[str, Any]:
        """Download PDF and extract text"""
        
        try:
            # Download PDF
            async with self.session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status} downloading PDF'
                    }
                
                pdf_content = await response.read()
                self.stats['pdfs_downloaded'] += 1
                
                # Verify it's a PDF
                if not pdf_content.startswith(b'%PDF'):
                    return {
                        'success': False,
                        'error': 'Downloaded content is not a PDF'
                    }
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_content)
                    tmp_path = tmp.name
                
                try:
                    # Extract text using PDF processor
                    text, metadata = self.pdf_processor.process_pdf(tmp_path)
                    
                    if text and len(text.strip()) > 0:
                        return {
                            'success': True,
                            'text': text,
                            'method': 'ocr' if 'OCR' in text else 'pymupdf',
                            'page_count': metadata.get('pages', 0),
                            'metadata': metadata
                        }
                    else:
                        return {
                            'success': False,
                            'error': 'No text extracted from PDF'
                        }
                        
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                        
        except asyncio.TimeoutError:
            return {
                'success': False,
                'error': 'Timeout downloading PDF'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get extraction statistics"""
        return {
            **self.stats,
            'extraction_success_rate': (
                (self.stats['pdfs_extracted'] / self.stats['pdfs_found'] * 100)
                if self.stats['pdfs_found'] > 0 else 0
            ),
            'content_enrichment_rate': (
                (self.stats['pdfs_extracted'] / self.stats['documents_missing_content'] * 100)
                if self.stats['documents_missing_content'] > 0 else 0
            )
        }


async def integrate_pdf_extraction_with_pipeline():
    """
    Example of how to integrate PDF extraction with the existing pipeline
    """
    
    from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
    from services.database import get_db_connection
    
    logging.basicConfig(level=logging.INFO)
    
    logger.info("\n" + "="*80)
    logger.info("INTEGRATING PDF EXTRACTION WITH EXISTING PIPELINE")
    logger.info("="*80)
    
    # Step 1: Fetch documents that might need PDF extraction
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Find documents with no content or very short content
    cursor.execute("""
        SELECT id, case_number, document_type, content, metadata
        FROM public.court_documents
        WHERE content IS NULL 
           OR LENGTH(content) < 50
           OR content = 'No content available'
        ORDER BY created_at DESC
        LIMIT 20
    """)
    
    documents = []
    for row in cursor.fetchall():
        documents.append({
            'id': row[0],
            'case_number': row[1],
            'document_type': row[2],
            'content': row[3],
            'metadata': row[4]
        })
    
    cursor.close()
    conn.close()
    
    logger.info(f"\nFound {len(documents)} documents needing content extraction")
    
    # Step 2: Extract PDF content
    async with PDFContentExtractor() as extractor:
        enriched_docs = await extractor.enrich_documents_with_pdf_content(documents)
        
        # Show statistics
        stats = extractor.get_statistics()
        logger.info(f"\nPDF Extraction Statistics:")
        logger.info(f"  Documents checked: {stats['documents_checked']}")
        logger.info(f"  Missing content: {stats['documents_missing_content']}")
        logger.info(f"  PDFs found: {stats['pdfs_found']}")
        logger.info(f"  PDFs extracted: {stats['pdfs_extracted']}")
        logger.info(f"  Total chars extracted: {stats['total_chars_extracted']:,}")
        logger.info(f"  Success rate: {stats['extraction_success_rate']:.1f}%")
    
    # Step 3: Update database with extracted content
    if enriched_docs:
        logger.info(f"\nUpdating database with extracted content...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        updated_count = 0
        for doc in enriched_docs:
            if doc.get('content') and doc.get('metadata', {}).get('pdf_extraction', {}).get('extracted'):
                cursor.execute("""
                    UPDATE public.court_documents
                    SET content = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    doc['content'],
                    json.dumps(doc.get('metadata', {})),
                    doc['id']
                ))
                updated_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"Updated {updated_count} documents with PDF content")
    
    # Step 4: Now run the regular pipeline on the enriched documents
    logger.info(f"\nRunning eleven-stage pipeline on enriched documents...")
    
    pipeline = RobustElevenStagePipeline()
    results = await pipeline.process_batch(limit=20)
    
    logger.info(f"\nPipeline Results:")
    logger.info(f"  Success: {results['success']}")
    logger.info(f"  Documents processed: {results['statistics']['documents_processed']}")
    logger.info(f"  Completeness: {results['verification']['completeness_score']:.1f}%")


if __name__ == "__main__":
    # For testing outside Docker
    if not os.getenv('DATABASE_URL'):
        logger.info("Running standalone PDF extraction test...")
        
        # Test with sample document
        test_doc = {
            'id': 1,
            'case_number': 'TEST-001',
            'content': '',  # Empty content
            'metadata': {
                'download_url': 'https://www.supremecourt.gov/opinions/19pdf/18-1334_8m58.pdf'
            }
        }
        
        async def test():
            async with PDFContentExtractor() as extractor:
                enriched = await extractor.enrich_documents_with_pdf_content([test_doc])
                
                if enriched[0].get('content'):
                    logger.info(f"\n✓ Successfully extracted {len(enriched[0]['content'])} characters")
                    logger.info(f"Preview: {enriched[0]['content'][:200]}...")
                    
        asyncio.run(test())
    else:
        # Run full integration
        asyncio.run(integrate_pdf_extraction_with_pipeline())