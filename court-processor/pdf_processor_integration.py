#!/usr/bin/env python3
"""
PDF Processing Integration for Court Documents

This module handles PDF downloading and text extraction using:
1. CourtListener API for PDF URLs
2. Doctor service for PDF to text conversion
3. Fallback to basic text extraction
"""

import asyncio
import aiohttp
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF downloading and text extraction"""
    
    def __init__(self, doctor_url: str = "http://doctor:5050"):
        self.doctor_url = doctor_url
        self.session = None
        self.headers = {
            'User-Agent': 'Aletheia Legal Processor/1.0'
        }
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def process_document_pdf(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process PDF for a document from CourtListener
        
        Args:
            document: Document dict with potential PDF URL
            
        Returns:
            Dict with extracted text and metadata
        """
        result = {
            'success': False,
            'text': '',
            'page_count': 0,
            'source': 'none',
            'error': None
        }
        
        # Check for PDF URL in various fields
        pdf_url = self._find_pdf_url(document)
        
        if not pdf_url:
            # No PDF available - use existing text fields
            plain_text = document.get('plain_text', '')
            if plain_text:
                result.update({
                    'success': True,
                    'text': plain_text,
                    'source': 'plain_text_field'
                })
            else:
                result['error'] = 'No PDF URL or text content found'
            return result
        
        # Try Doctor service first
        doctor_result = await self._extract_with_doctor(pdf_url)
        if doctor_result['success']:
            return doctor_result
        
        # Fallback to direct download and extraction
        return await self._extract_with_fallback(pdf_url)
    
    def _find_pdf_url(self, document: Dict[str, Any]) -> Optional[str]:
        """Find PDF URL from document fields"""
        
        # Direct download URL (opinions)
        if document.get('download_url'):
            return document['download_url']
        
        # Construct from filepath_local (RECAP documents)
        if document.get('filepath_local'):
            filepath = document['filepath_local']
            # CourtListener serves files from storage subdomain
            return f"https://storage.courtlistener.com/{filepath}"
        
        # Check metadata
        metadata = document.get('metadata', {})
        if isinstance(metadata, dict):
            if metadata.get('pdf_url'):
                return metadata['pdf_url']
            if metadata.get('download_url'):
                return metadata['download_url']
        
        return None
    
    async def _extract_with_doctor(self, pdf_url: str) -> Dict[str, Any]:
        """Extract text using Doctor service"""
        try:
            # Check if Doctor service is available
            async with self.session.get(f"{self.doctor_url}/health") as resp:
                if resp.status != 200:
                    logger.warning("Doctor service not available")
                    return {'success': False, 'error': 'Doctor service unavailable'}
            
            # Send PDF URL to Doctor
            payload = {
                'url': pdf_url,
                'ocr_available': True
            }
            
            async with self.session.post(
                f"{self.doctor_url}/extract/doc/text",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return {
                        'success': True,
                        'text': data.get('content', ''),
                        'page_count': data.get('page_count', 0),
                        'source': 'doctor_service',
                        'metadata': data.get('metadata', {})
                    }
                else:
                    error_text = await response.text()
                    logger.error(f"Doctor extraction failed: {error_text}")
                    return {
                        'success': False,
                        'error': f'Doctor returned {response.status}'
                    }
                    
        except asyncio.TimeoutError:
            logger.error("Doctor service timeout")
            return {'success': False, 'error': 'Doctor timeout'}
        except Exception as e:
            logger.error(f"Doctor service error: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _extract_with_fallback(self, pdf_url: str) -> Dict[str, Any]:
        """Fallback PDF extraction without Doctor"""
        try:
            # Download PDF to temp file
            async with self.session.get(pdf_url, headers=self.headers) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': f'Failed to download PDF: {response.status}'
                    }
                
                # Check if it's actually a PDF
                content = await response.read()
                if not content.startswith(b'%PDF'):
                    return {
                        'success': False,
                        'error': 'Downloaded content is not a PDF'
                    }
                
                # Save to temp file
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(content)
                    tmp_path = tmp.name
                
                try:
                    # Use PyPDF2 for basic extraction
                    import PyPDF2
                    
                    text_parts = []
                    with open(tmp_path, 'rb') as pdf_file:
                        pdf_reader = PyPDF2.PdfReader(pdf_file)
                        page_count = len(pdf_reader.pages)
                        
                        for page_num, page in enumerate(pdf_reader.pages):
                            try:
                                text = page.extract_text()
                                if text:
                                    text_parts.append(text)
                            except Exception as e:
                                logger.warning(f"Failed to extract page {page_num}: {e}")
                    
                    return {
                        'success': True,
                        'text': '\n\n'.join(text_parts),
                        'page_count': page_count,
                        'source': 'pypdf2_fallback'
                    }
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"Fallback extraction failed: {e}")
            return {
                'success': False,
                'error': f'Fallback extraction failed: {str(e)}'
            }


class EnhancedPipelineWithPDF:
    """Enhancement for the main pipeline to add PDF processing"""
    
    @staticmethod
    def enhance_pipeline_with_pdf(pipeline_instance):
        """
        Monkey-patch the existing pipeline to add PDF processing
        
        Args:
            pipeline_instance: Instance of RobustElevenStagePipeline
        """
        
        # Save original text extraction method
        original_extract = pipeline_instance._extract_text_validated
        
        async def _extract_text_validated_with_pdf(self, document: Dict[str, Any]) -> Dict[str, Any]:
            """Enhanced text extraction with PDF support"""
            
            # First try PDF extraction
            async with PDFProcessor() as pdf_processor:
                pdf_result = await pdf_processor.process_document_pdf(document)
                
                if pdf_result['success']:
                    # Update document with PDF-extracted text
                    document['content'] = pdf_result['text']
                    document['pdf_extraction'] = {
                        'source': pdf_result['source'],
                        'page_count': pdf_result['page_count']
                    }
                    
                    logger.info(f"Successfully extracted {len(pdf_result['text'])} chars from PDF via {pdf_result['source']}")
                    
                    return {
                        'extracted': True,
                        'text': pdf_result['text'],
                        'length': len(pdf_result['text']),
                        'source': pdf_result['source'],
                        'page_count': pdf_result['page_count']
                    }
            
            # Fall back to original extraction method
            return await original_extract(document)
        
        # Apply the patch
        pipeline_instance._extract_text_validated = _extract_text_validated_with_pdf.__get__(
            pipeline_instance, pipeline_instance.__class__
        )
        
        logger.info("Pipeline enhanced with PDF processing capability")
        
        return pipeline_instance


async def test_pdf_processing():
    """Test PDF processing with real documents"""
    
    import sys
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from services.courtlistener_service import CourtListenerService
    
    # Set API key
    os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
    
    logging.basicConfig(level=logging.INFO)
    
    logger.info("\n" + "="*80)
    logger.info("TESTING PDF PROCESSING INTEGRATION")
    logger.info("="*80)
    
    # Get some opinions with PDFs
    cl_service = CourtListenerService()
    opinions = await cl_service.fetch_opinions(
        court_id='ca5',
        date_filed_after='2024-01-01',
        max_results=3
    )
    
    async with PDFProcessor() as processor:
        for i, opinion in enumerate(opinions):
            logger.info(f"\n\nTesting Opinion {i+1}:")
            logger.info(f"  ID: {opinion.get('id')}")
            logger.info(f"  Download URL: {opinion.get('download_url')}")
            
            result = await processor.process_document_pdf(opinion)
            
            logger.info(f"  Extraction Result:")
            logger.info(f"    Success: {result['success']}")
            logger.info(f"    Source: {result.get('source', 'none')}")
            logger.info(f"    Text length: {len(result.get('text', ''))}")
            logger.info(f"    Page count: {result.get('page_count', 0)}")
            
            if result.get('error'):
                logger.info(f"    Error: {result['error']}")
            
            if result['success'] and result['text']:
                # Show first 200 chars
                preview = result['text'][:200].replace('\n', ' ')
                logger.info(f"    Text preview: {preview}...")
    
    await cl_service.close()


if __name__ == "__main__":
    asyncio.run(test_pdf_processing())