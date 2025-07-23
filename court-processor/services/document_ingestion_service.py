#!/usr/bin/env python3
"""
Document Ingestion Service

This service handles all document acquisition and content extraction,
providing a clean separation between data ingestion and processing.
"""

import asyncio
import aiohttp
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import json
import tempfile
import os

from services.courtlistener_service import CourtListenerService
from services.database import get_db_connection
from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Handles document acquisition from various sources and ensures
    all documents have extracted text content before storage.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.cl_service = CourtListenerService(api_key)
        self.pdf_processor = PDFProcessor(ocr_enabled=True)
        self.session = None
        self.stats = {
            'sources': {
                'courtlistener_opinions': 0,
                'courtlistener_recap': 0,
                'direct_upload': 0
            },
            'processing': {
                'total_documents': 0,
                'pdfs_downloaded': 0,
                'pdfs_extracted': 0,
                'ocr_performed': 0,
                'extraction_failed': 0
            },
            'storage': {
                'documents_stored': 0,
                'documents_updated': 0,
                'storage_failed': 0
            },
            'content': {
                'total_characters': 0,
                'total_pages': 0
            }
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        await self.cl_service.close()
    
    async def ingest_from_courtlistener(self,
                                      court_ids: List[str],
                                      date_after: str,
                                      document_types: List[str] = ['opinions'],
                                      max_per_court: int = 100) -> Dict[str, Any]:
        """
        Ingest documents from CourtListener with automatic PDF extraction
        
        Args:
            court_ids: List of court IDs to fetch from
            date_after: Date string (YYYY-MM-DD) for filtering
            document_types: Types to fetch ('opinions', 'recap')
            max_per_court: Maximum documents per court
            
        Returns:
            Ingestion statistics and results
        """
        results = {
            'success': True,
            'documents_ingested': 0,
            'errors': []
        }
        
        try:
            all_documents = []
            
            # Fetch opinions if requested
            if 'opinions' in document_types:
                logger.info("Fetching opinions from CourtListener...")
                opinions = await self._fetch_and_process_opinions(
                    court_ids, date_after, max_per_court
                )
                all_documents.extend(opinions)
                self.stats['sources']['courtlistener_opinions'] += len(opinions)
            
            # Fetch RECAP documents if requested
            if 'recap' in document_types:
                logger.info("Fetching RECAP documents from CourtListener...")
                recap_docs = await self._fetch_and_process_recap(
                    court_ids, date_after, max_per_court
                )
                all_documents.extend(recap_docs)
                self.stats['sources']['courtlistener_recap'] += len(recap_docs)
            
            # Store all documents in database
            if all_documents:
                storage_results = await self._store_documents(all_documents)
                results['documents_ingested'] = storage_results['stored']
                results['storage_details'] = storage_results
            
            logger.info(f"\nIngestion complete: {results['documents_ingested']} documents")
            
        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            results['success'] = False
            results['errors'].append(str(e))
        
        results['statistics'] = self.get_statistics()
        return results
    
    async def _fetch_and_process_opinions(self,
                                        court_ids: List[str],
                                        date_after: str,
                                        max_per_court: int) -> List[Dict[str, Any]]:
        """Fetch opinions and ensure they have text content"""
        processed_documents = []
        
        for court_id in court_ids:
            logger.info(f"\nFetching opinions from {court_id}...")
            
            opinions = await self.cl_service.fetch_opinions(
                court_id=court_id,
                date_filed_after=date_after,
                max_results=max_per_court
            )
            
            for opinion in opinions:
                self.stats['processing']['total_documents'] += 1
                
                # Process each opinion
                doc = await self._process_opinion(opinion, court_id)
                if doc:
                    processed_documents.append(doc)
        
        return processed_documents
    
    async def _process_opinion(self, opinion: Dict[str, Any], court_id: str) -> Optional[Dict[str, Any]]:
        """Process a single opinion, extracting text if needed"""
        
        opinion_id = opinion.get('id')
        logger.debug(f"Processing opinion {opinion_id}")
        
        # Build document structure
        document = {
            'case_number': f"OPINION-{court_id}-{opinion_id}",
            'case_name': self._extract_case_name(opinion),
            'document_type': 'opinion',
            'content': '',
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
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Get text content
        text_content, extraction_method = await self._get_text_content(opinion)
        
        if text_content:
            document['content'] = text_content
            document['metadata']['extraction_method'] = extraction_method
            self.stats['content']['total_characters'] += len(text_content)
            
            # Get cluster data if available
            if opinion.get('cluster'):
                cluster_data = await self._fetch_cluster_data(opinion['cluster'])
                document['metadata']['cluster_data'] = cluster_data
                
                # Update case name and metadata from cluster
                if cluster_data.get('case_name'):
                    document['case_name'] = cluster_data['case_name']
                if cluster_data.get('judges'):
                    document['metadata']['judges'] = cluster_data['judges']
                if cluster_data.get('docket_number'):
                    document['metadata']['docket_number'] = cluster_data['docket_number']
            
            return document
        else:
            logger.warning(f"No text content extracted for opinion {opinion_id}")
            return None
    
    async def _get_text_content(self, document: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get text content from document, extracting from PDF if needed
        
        Returns:
            Tuple of (text_content, extraction_method)
        """
        # First check for existing plain_text
        if document.get('plain_text'):
            return document['plain_text'], 'plain_text_field'
        
        # Try to extract from PDF
        pdf_url = document.get('download_url')
        if pdf_url:
            logger.info(f"  Downloading PDF from: {pdf_url}")
            text_content = await self._download_and_extract_pdf(pdf_url)
            
            if text_content:
                self.stats['processing']['pdfs_extracted'] += 1
                return text_content, 'pdf_extraction'
            else:
                self.stats['processing']['extraction_failed'] += 1
        
        # Check for HTML content as last resort
        if document.get('html'):
            # Simple HTML stripping
            import re
            text = re.sub(r'<[^>]+>', '', document['html'])
            return text.strip(), 'html_stripped'
        
        return '', 'none'
    
    async def _download_and_extract_pdf(self, pdf_url: str) -> Optional[str]:
        """Download PDF and extract text"""
        try:
            async with self.session.get(pdf_url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download PDF: HTTP {response.status}")
                    return None
                
                pdf_content = await response.read()
                self.stats['processing']['pdfs_downloaded'] += 1
                
                # Verify it's a PDF
                if not pdf_content.startswith(b'%PDF'):
                    logger.error("Downloaded content is not a PDF")
                    return None
                
                # Save to temp file and process
                with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
                    tmp.write(pdf_content)
                    tmp_path = tmp.name
                
                try:
                    # Use PDF processor
                    text, metadata = self.pdf_processor.process_pdf(tmp_path)
                    
                    if metadata.get('pages', 0) > 0:
                        self.stats['content']['total_pages'] += metadata['pages']
                    
                    # Check if OCR was used
                    if text and 'OCR' in text:
                        self.stats['processing']['ocr_performed'] += 1
                    
                    return text
                    
                finally:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                        
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return None
    
    async def _store_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Store processed documents in database"""
        results = {
            'stored': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for doc in documents:
            try:
                # Check if document exists
                cursor.execute("""
                    SELECT id FROM public.court_documents 
                    WHERE case_number = %s
                """, (doc['case_number'],))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing document
                    cursor.execute("""
                        UPDATE public.court_documents
                        SET case_name = %s,
                            document_type = %s,
                            content = %s,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE case_number = %s
                    """, (
                        doc['case_name'],
                        doc['document_type'],
                        doc['content'],
                        json.dumps(doc['metadata']),
                        doc['case_number']
                    ))
                    results['updated'] += 1
                    self.stats['storage']['documents_updated'] += 1
                else:
                    # Insert new document
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
                    results['stored'] += 1
                    self.stats['storage']['documents_stored'] += 1
                
                conn.commit()
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Failed to store document {doc['case_number']}: {e}")
                results['failed'] += 1
                results['errors'].append(str(e))
                self.stats['storage']['storage_failed'] += 1
        
        cursor.close()
        conn.close()
        
        return results
    
    async def _fetch_cluster_data(self, cluster_url: str) -> Dict[str, Any]:
        """Fetch additional metadata from cluster endpoint"""
        try:
            async with self.session.get(
                cluster_url,
                headers={'Authorization': f'Token {self.cl_service.api_key}'}
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {}
        except Exception as e:
            logger.error(f"Error fetching cluster data: {e}")
            return {}
    
    def _extract_case_name(self, opinion: Dict[str, Any]) -> str:
        """Extract case name from opinion data"""
        # Implementation depends on opinion structure
        return opinion.get('case_name', f"Opinion {opinion.get('id', 'Unknown')}")
    
    async def _fetch_and_process_recap(self,
                                     court_ids: List[str],
                                     date_after: str,
                                     max_per_court: int) -> List[Dict[str, Any]]:
        """Fetch and process RECAP documents"""
        # TODO: Implement RECAP document processing
        # This would follow similar pattern to opinions
        logger.info("RECAP document processing not yet implemented")
        return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive ingestion statistics"""
        total_docs = self.stats['processing']['total_documents']
        
        return {
            **self.stats,
            'summary': {
                'total_documents_processed': total_docs,
                'pdf_extraction_rate': (
                    (self.stats['processing']['pdfs_extracted'] / 
                     self.stats['processing']['pdfs_downloaded'] * 100)
                    if self.stats['processing']['pdfs_downloaded'] > 0 else 0
                ),
                'storage_success_rate': (
                    ((self.stats['storage']['documents_stored'] + 
                      self.stats['storage']['documents_updated']) /
                     total_docs * 100)
                    if total_docs > 0 else 0
                ),
                'average_document_size': (
                    self.stats['content']['total_characters'] / total_docs
                    if total_docs > 0 else 0
                )
            }
        }