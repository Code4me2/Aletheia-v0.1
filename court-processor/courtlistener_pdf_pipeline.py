#!/usr/bin/env python3
"""
CourtListener PDF Pipeline Integration

This module integrates PDF downloading and text extraction into the document
ingestion flow, ensuring text is extracted BEFORE documents are stored in the database.
"""

import asyncio
import aiohttp
import logging
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

from services.courtlistener_service import CourtListenerService
from services.database import get_db_connection
from pdf_processor import PDFProcessor
import tempfile

logger = logging.getLogger(__name__)


class CourtListenerPDFPipeline:
    """Pipeline for fetching documents from CourtListener and extracting text from PDFs"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.cl_service = CourtListenerService(api_key)
        self.pdf_processor = PDFProcessor(ocr_enabled=True)
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self.cl_service.close()
    
    async def fetch_and_process_opinions(self, 
                                       court_ids: List[str], 
                                       date_after: str,
                                       max_documents: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch opinions from CourtListener and extract text from PDFs
        
        Args:
            court_ids: List of court IDs to fetch from
            date_after: Date string (YYYY-MM-DD) for filtering
            max_documents: Maximum number of documents to process
            
        Returns:
            List of processed documents with extracted text
        """
        processed_documents = []
        
        for court_id in court_ids:
            logger.info(f"\nFetching opinions from court: {court_id}")
            
            opinions = await self.cl_service.fetch_opinions(
                court_id=court_id,
                date_filed_after=date_after,
                max_results=max_documents // len(court_ids)
            )
            
            logger.info(f"Found {len(opinions)} opinions from {court_id}")
            
            for opinion in opinions:
                try:
                    processed_doc = await self._process_opinion(opinion, court_id)
                    if processed_doc:
                        processed_documents.append(processed_doc)
                except Exception as e:
                    logger.error(f"Failed to process opinion {opinion.get('id')}: {e}")
                    continue
        
        return processed_documents
    
    async def _process_opinion(self, opinion: Dict[str, Any], court_id: str) -> Optional[Dict[str, Any]]:
        """Process a single opinion document"""
        
        # Extract basic metadata
        opinion_id = opinion.get('id')
        case_name = self._extract_case_name(opinion)
        
        logger.info(f"\nProcessing opinion {opinion_id}: {case_name}")
        
        # Get text content
        text_content = ""
        extraction_method = "none"
        page_count = 0
        
        # First check if plain_text is already available
        if opinion.get('plain_text'):
            text_content = opinion['plain_text']
            extraction_method = "plain_text_field"
            logger.info(f"  Using existing plain_text field ({len(text_content)} chars)")
        
        # If no text, try to download and extract from PDF
        elif opinion.get('download_url'):
            logger.info(f"  Downloading PDF from: {opinion['download_url']}")
            pdf_result = await self._download_and_extract_pdf(opinion['download_url'])
            
            if pdf_result['success']:
                text_content = pdf_result['text']
                extraction_method = pdf_result['method']
                page_count = pdf_result['page_count']
                logger.info(f"  Extracted {len(text_content)} chars via {extraction_method}")
            else:
                logger.warning(f"  PDF extraction failed: {pdf_result['error']}")
        
        # Skip if no text extracted
        if not text_content:
            logger.warning(f"  No text content extracted, skipping")
            return None
        
        # Get cluster metadata if available
        cluster_data = {}
        if opinion.get('cluster'):
            cluster_data = await self._fetch_cluster_data(opinion['cluster'])
        
        # Prepare document for database storage
        document = {
            'case_number': f"OPINION-{court_id}-{opinion_id}",
            'case_name': case_name,
            'document_type': 'opinion',
            'content': text_content,
            'metadata': {
                'source': 'courtlistener',
                'opinion_id': opinion_id,
                'court_id': court_id,
                'type': opinion.get('type', ''),
                'author_str': opinion.get('author_str', ''),
                'per_curiam': opinion.get('per_curiam', False),
                'date_created': opinion.get('date_created', ''),
                'download_url': opinion.get('download_url', ''),
                'absolute_url': opinion.get('absolute_url', ''),
                'cluster_data': cluster_data,
                'extraction_method': extraction_method,
                'page_count': page_count,
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Add judge info from cluster if available
        if cluster_data:
            if cluster_data.get('judges'):
                document['metadata']['judges'] = cluster_data['judges']
            if cluster_data.get('case_name'):
                document['case_name'] = cluster_data['case_name']
            if cluster_data.get('docket_number'):
                document['metadata']['docket_number'] = cluster_data['docket_number']
            if cluster_data.get('date_filed'):
                document['metadata']['date_filed'] = cluster_data['date_filed']
        
        return document
    
    def _extract_case_name(self, opinion: Dict[str, Any]) -> str:
        """Extract case name from opinion data"""
        # Try cluster first
        cluster_url = opinion.get('cluster', '')
        if cluster_url and hasattr(self, '_cluster_cache'):
            cluster_data = self._cluster_cache.get(cluster_url, {})
            if cluster_data.get('case_name'):
                return cluster_data['case_name']
        
        # Fall back to constructing from metadata
        if opinion.get('case_name'):
            return opinion['case_name']
        
        # Use opinion type as last resort
        return f"Opinion {opinion.get('id', 'Unknown')}"
    
    async def _download_and_extract_pdf(self, pdf_url: str) -> Dict[str, Any]:
        """Download PDF and extract text"""
        try:
            # Download PDF
            async with self.session.get(pdf_url) as response:
                if response.status != 200:
                    return {
                        'success': False,
                        'error': f'HTTP {response.status} downloading PDF'
                    }
                
                pdf_content = await response.read()
                
                # Verify it's a PDF
                if not pdf_content.startswith(b'%PDF'):
                    return {
                        'success': False,
                        'error': 'Downloaded content is not a PDF'
                    }
                
                # Save to temp file and process
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_content)
                    tmp_path = tmp.name
                
                try:
                    # Use existing PDF processor
                    text, metadata = self.pdf_processor.process_pdf(tmp_path)
                    
                    return {
                        'success': True,
                        'text': text,
                        'page_count': metadata.get('pages', 0),
                        'method': 'pymupdf' if text else 'ocr',
                        'metadata': metadata
                    }
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"PDF download/extraction error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _fetch_cluster_data(self, cluster_url: str) -> Dict[str, Any]:
        """Fetch additional metadata from cluster endpoint"""
        try:
            # Extract cluster ID from URL
            # Example: https://www.courtlistener.com/api/rest/v4/clusters/123/
            parts = cluster_url.rstrip('/').split('/')
            cluster_id = parts[-1]
            
            async with self.session.get(
                cluster_url,
                headers={'Authorization': f'Token {self.cl_service.api_key}'}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.warning(f"Failed to fetch cluster {cluster_id}: HTTP {response.status}")
                    return {}
                    
        except Exception as e:
            logger.error(f"Error fetching cluster data: {e}")
            return {}
    
    async def store_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store processed documents in the database"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        stats = {
            'total': len(documents),
            'stored': 0,
            'skipped': 0,
            'errors': 0
        }
        
        for doc in documents:
            try:
                # Check if document already exists
                cursor.execute("""
                    SELECT id FROM public.court_documents 
                    WHERE case_number = %s
                """, (doc['case_number'],))
                
                if cursor.fetchone():
                    logger.info(f"Document {doc['case_number']} already exists, updating")
                    cursor.execute("""
                        UPDATE public.court_documents
                        SET content = %s,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE case_number = %s
                    """, (
                        doc['content'],
                        json.dumps(doc['metadata']),
                        doc['case_number']
                    ))
                else:
                    cursor.execute("""
                        INSERT INTO public.court_documents 
                        (case_number, case_name, document_type, content, metadata)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        doc['case_number'],
                        doc['case_name'],
                        doc['document_type'],
                        doc['content'],
                        json.dumps(doc['metadata'])
                    ))
                
                conn.commit()
                stats['stored'] += 1
                
            except Exception as e:
                logger.error(f"Error storing document {doc.get('case_number')}: {e}")
                conn.rollback()
                stats['errors'] += 1
        
        cursor.close()
        conn.close()
        
        return stats


async def run_pdf_pipeline():
    """Run the complete PDF pipeline"""
    
    # Configuration
    os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'
    
    logging.basicConfig(level=logging.INFO)
    
    logger.info("\n" + "="*80)
    logger.info("COURTLISTENER PDF PIPELINE")
    logger.info("="*80)
    
    # Target IP courts - try some that might have PDFs
    court_ids = ['ca5', 'ca9']  # Circuit courts often have PDFs
    date_after = '2024-06-01'
    max_documents = 10  # Start small for testing
    
    async with CourtListenerPDFPipeline() as pipeline:
        # Fetch and process documents
        logger.info(f"\nFetching opinions from courts: {court_ids}")
        logger.info(f"Date filter: after {date_after}")
        
        documents = await pipeline.fetch_and_process_opinions(
            court_ids=court_ids,
            date_after=date_after,
            max_documents=max_documents
        )
        
        logger.info(f"\n\nProcessed {len(documents)} documents with text content")
        
        # Show summary
        total_chars = sum(len(doc['content']) for doc in documents)
        logger.info(f"Total text extracted: {total_chars:,} characters")
        
        # Store in database (or files if DB not available)
        logger.info("\nStoring documents...")
        try:
            storage_stats = await pipeline.store_documents(documents)
        except Exception as e:
            logger.warning(f"Database storage failed: {e}")
            logger.info("Saving to JSON file instead...")
            
            # Save to file as fallback
            output_file = f"extracted_opinions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(output_file, 'w') as f:
                json.dump(documents, f, indent=2, default=str)
            
            logger.info(f"Saved {len(documents)} documents to {output_file}")
            storage_stats = {
                'total': len(documents),
                'stored': len(documents),
                'errors': 0
            }
        
        logger.info(f"\nStorage Results:")
        logger.info(f"  Total: {storage_stats['total']}")
        logger.info(f"  Stored: {storage_stats['stored']}")
        logger.info(f"  Errors: {storage_stats['errors']}")
    
    logger.info("\n" + "="*80)
    logger.info("PIPELINE COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(run_pdf_pipeline())