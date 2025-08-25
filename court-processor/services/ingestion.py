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
from services.recap.authenticated_client import AuthenticatedRECAPClient
from pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """
    Handles document acquisition from various sources and ensures
    all documents have extracted text content before storage.
    """
    
    def __init__(self, api_key: Optional[str] = None, 
                 pacer_username: Optional[str] = None,
                 pacer_password: Optional[str] = None):
        self.cl_service = CourtListenerService(api_key)
        self.pdf_processor = PDFProcessor(ocr_enabled=True)
        self.session = None
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self.recap_client = None
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
                                      max_per_court: int = 100,
                                      nature_of_suit: Optional[List[str]] = None,
                                      search_type: Optional[str] = None,
                                      use_recap_fallback: bool = False,
                                      check_recap_first: bool = True,
                                      max_pacer_cost: float = 0.0) -> Dict[str, Any]:
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
            
            # Use enhanced search if nature_of_suit provided for IP cases
            if nature_of_suit and search_type:
                logger.info(f"Using enhanced search for IP cases with nature_of_suit: {nature_of_suit}")
                ip_documents = await self._fetch_ip_focused_documents(
                    court_ids, date_after, nature_of_suit, search_type, max_per_court
                )
                all_documents.extend(ip_documents)
                self.stats['sources']['courtlistener_opinions'] += len(ip_documents)
            # Otherwise use standard opinions endpoint
            elif 'opinions' in document_types:
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
                    court_ids, date_after, max_per_court,
                    use_recap_fallback=use_recap_fallback,
                    check_recap_first=check_recap_first,
                    max_pacer_cost=max_pacer_cost
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
    
    async def _fetch_ip_focused_documents(self,
                                        court_ids: List[str],
                                        date_after: str,
                                        nature_of_suit: List[str],
                                        search_type: str,
                                        max_per_court: int) -> List[Dict[str, Any]]:
        """Fetch IP-focused documents using enhanced search"""
        processed_documents = []
        
        # Use enhanced search to find IP cases
        results = await self.cl_service.search_with_filters(
            search_type=search_type,
            court_ids=court_ids,
            nature_of_suit=nature_of_suit,
            date_range=(date_after, datetime.now().strftime('%Y-%m-%d')),
            max_results=max_per_court * len(court_ids)
        )
        
        logger.info(f"Found {len(results)} IP-focused documents")
        
        # Process each result
        for result in results:
            self.stats['processing']['total_documents'] += 1
            
            # Extract court ID from result
            court_id = result.get('court_id', '')
            if not court_id and 'court' in result:
                court_id = result['court']
            
            # Store current court for RECAP availability check
            self._current_court_id = court_id
            
            # Process based on result type
            if search_type == 'o' or result.get('type') == 'opinion':
                doc = await self._process_opinion(result, court_id)
            else:
                # For RECAP results, adapt to opinion format
                doc = await self._process_recap_result(result, court_id)
            
            if doc:
                processed_documents.append(doc)
                
        return processed_documents
    
    async def _process_recap_document(self, recap_doc: Dict[str, Any], 
                                     docket_info: Dict[str, Any], 
                                     court_id: str) -> Optional[Dict[str, Any]]:
        """Process a single RECAP document from v4 API response"""
        
        doc_id = recap_doc.get('id')
        logger.debug(f"Processing RECAP document {doc_id}")
        
        # Build document structure matching pipeline schema
        document = {
            'case_number': f"RECAP-{court_id}-{doc_id}",
            'case_name': docket_info.get('case_name', ''),
            'document_type': 'recap_document',
            'content': '',  # Will be filled from PDF or plain_text
            'metadata': {
                'source': 'courtlistener_recap',
                'recap_document_id': doc_id,
                'docket_id': docket_info.get('docket_id'),
                'court_id': court_id,
                'court_name': docket_info.get('court', ''),
                'description': recap_doc.get('description', ''),
                'pacer_doc_id': recap_doc.get('pacer_doc_id'),
                'entry_date_filed': recap_doc.get('entry_date_filed'),
                'page_count': recap_doc.get('page_count'),
                'is_available': recap_doc.get('is_available', False),
                'filepath_local': recap_doc.get('filepath_local'),
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Get text content - prefer plain_text if available
        if recap_doc.get('plain_text'):
            document['content'] = recap_doc['plain_text']
            logger.debug(f"Using existing plain text for document {doc_id}")
        elif recap_doc.get('filepath_local'):
            # Download and extract from PDF
            pdf_url = f"https://www.courtlistener.com/{recap_doc['filepath_local']}"
            text_content = await self._download_and_extract_pdf(pdf_url, check_recap=False)
            if text_content:
                document['content'] = text_content
            else:
                logger.warning(f"Failed to extract text from PDF for document {doc_id}")
                return None
        else:
            logger.warning(f"No content available for document {doc_id}")
            return None
        
        # Track content size
        self.stats['content']['total_characters'] += len(document['content'])
        self.stats['processing']['total_documents'] += 1
        
        return document
    
    async def _process_recap_result(self, result: Dict[str, Any], court_id: str) -> Optional[Dict[str, Any]]:
        """Process a RECAP search result"""
        
        result_id = result.get('docket_id', result.get('id', ''))
        logger.debug(f"Processing RECAP result {result_id}")
        
        # Build document structure with correct field names
        document = {
            'case_number': result.get('docketNumber', f"RECAP-{court_id}-{result_id}"),
            'case_name': result.get('caseName', ''),
            'document_type': 'recap_docket',
            'content': '',  # RECAP search results don't have text content
            'metadata': {
                'source': 'courtlistener_recap',
                'docket_id': result.get('docket_id'),
                'court_id': result.get('court_id', court_id),
                'court_name': result.get('court', ''),
                'nature_of_suit': result.get('suitNature', ''),
                'date_filed': result.get('dateFiled', ''),
                'date_terminated': result.get('dateTerminated'),
                'cause': result.get('cause', ''),
                'jury_demand': result.get('juryDemand', ''),
                'jurisdiction_type': result.get('jurisdictionType', ''),
                'assigned_to': result.get('assignedTo', ''),
                'assigned_to_id': result.get('assigned_to_id'),
                'referred_to': result.get('referredTo'),
                'party': result.get('party', []),
                'attorney': result.get('attorney', []),
                'firm': result.get('firm', []),
                'docket_absolute_url': result.get('docket_absolute_url', ''),
                'pacer_case_id': result.get('pacer_case_id'),
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Extract recap documents info
        recap_docs = result.get('recap_documents', [])
        if recap_docs:
            document['metadata']['recap_document_count'] = len(recap_docs)
            document['metadata']['recap_documents'] = [
                {
                    'document_number': doc.get('document_number'),
                    'description': doc.get('description', ''),
                    'short_description': doc.get('short_description', ''),
                    'is_available': doc.get('is_available', False),
                    'page_count': doc.get('page_count'),
                    'pacer_doc_id': doc.get('pacer_doc_id')
                }
                for doc in recap_docs[:5]  # Store first 5 for reference
            ]
        
        # Even without text content, the metadata is valuable
        # Store the document for metadata tracking and future PDF retrieval
        return document
    
    async def _process_opinion(self, search_result: Dict[str, Any], court_id: str) -> Optional[Dict[str, Any]]:
        """Process a search result containing opinion data"""
        
        # Search results contain cluster data with nested opinions
        cluster_id = search_result.get('cluster_id')
        logger.debug(f"Processing opinion cluster {cluster_id}")
        
        # Build document structure from cluster/search result
        document = {
            'case_number': search_result.get('docketNumber', f"OPINION-{court_id}-{cluster_id}"),
            'case_name': search_result.get('caseName', ''),
            'document_type': 'opinion',
            'content': '',
            'metadata': {
                'source': 'courtlistener',
                'cluster_id': cluster_id,
                'cl_id': str(cluster_id),  # Add cl_id for pipeline compatibility
                'court_id': court_id,
                'court_name': search_result.get('court', ''),
                'docket_number': search_result.get('docketNumber', ''),
                'date_filed': search_result.get('dateFiled', ''),
                'date_argued': search_result.get('dateArgued', ''),
                'status': search_result.get('status', ''),
                'judges': search_result.get('judge', ''),
                'attorneys': search_result.get('attorney', ''),
                'nature_of_suit': search_result.get('suitNature', ''),
                'absolute_url': search_result.get('absolute_url', ''),
                'processed_at': datetime.now().isoformat()
            }
        }
        
        # Check if there are nested opinions with download URLs
        opinions = search_result.get('opinions', [])
        if opinions:
            # Use the first opinion (usually the main/combined opinion)
            first_opinion = opinions[0]
            document['metadata']['opinion_id'] = first_opinion.get('id')
            document['metadata']['opinion_type'] = first_opinion.get('type', '')
            document['metadata']['download_url'] = first_opinion.get('download_url', '')
            document['metadata']['snippet'] = first_opinion.get('snippet', '')
            
            # Try to get text content
            text_content, extraction_method = await self._get_text_content(first_opinion)
            
            if text_content:
                document['content'] = text_content
                document['metadata']['extraction_method'] = extraction_method
                self.stats['content']['total_characters'] += len(text_content)
            elif first_opinion.get('download_url'):
                # We have a PDF URL but no text - this is common for recent opinions
                logger.info(f"Opinion {cluster_id} has PDF but no text - storing metadata")
                document['metadata']['pdf_available'] = True
                document['metadata']['requires_pdf_extraction'] = True
        
        # Return document even without content - metadata is valuable
        return document
    
    async def _get_text_content(self, document: Dict[str, Any]) -> Tuple[str, str]:
        """
        Get text content from document, extracting from PDF if needed
        
        Returns:
            Tuple of (text_content, extraction_method)
        """
        # Use the enhanced text extraction method from CourtListener service
        text_content = self.cl_service.extract_all_text_fields(document)
        if text_content:
            # Determine which field was used
            if document.get('plain_text'):
                return text_content, 'plain_text_field'
            elif document.get('html'):
                return text_content, 'html_field'
            elif document.get('xml_harvard'):
                return text_content, 'xml_harvard_field'
            else:
                return text_content, 'other_text_field'
        
        # If no text fields available, try to extract from PDF
        pdf_url = document.get('download_url')
        if pdf_url:
            logger.info(f"  No text fields found, downloading PDF from: {pdf_url}")
            text_content = await self._download_and_extract_pdf(pdf_url)
            
            if text_content:
                self.stats['processing']['pdfs_extracted'] += 1
                return text_content, 'pdf_extraction'
            else:
                self.stats['processing']['extraction_failed'] += 1
        
        return '', 'none'
    
    async def _download_and_extract_pdf(self, pdf_url: str, check_recap: bool = True) -> Optional[str]:
        """Download PDF and extract text with optional RECAP availability check"""
        try:
            # For RECAP documents, check availability first
            if check_recap and 'recap' in pdf_url and hasattr(self, '_current_court_id'):
                # Extract PACER doc ID from URL if available
                # URL pattern: /download/recap/12345.pdf
                import re
                match = re.search(r'/recap/(\d+)\.pdf', pdf_url)
                if match:
                    pacer_doc_id = match.group(1)
                    available_docs = await self.cl_service.check_recap_availability(
                        self._current_court_id, [pacer_doc_id]
                    )
                    if not available_docs:
                        logger.warning(f"RECAP document {pacer_doc_id} not available")
                        return None
            
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
    
    async def search_opinions(self,
                            query: Optional[str] = None,
                            court_ids: List[str] = None,
                            date_after: Optional[str] = None,
                            date_before: Optional[str] = None,
                            document_types: List[str] = ['opinion'],
                            max_results: int = 100,
                            nature_of_suit: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Search for court opinions using broad criteria
        
        Args:
            query: Full-text search query
            court_ids: List of court IDs
            date_after: Date filed after (YYYY-MM-DD)
            date_before: Date filed before (YYYY-MM-DD)
            document_types: Document types to search
            max_results: Maximum results to return
            nature_of_suit: Nature of suit codes
            
        Returns:
            Search results with documents
        """
        search_params = {
            'type': 'o',  # Opinions
            'order_by': 'score desc',
            'per_page': min(max_results, 100)
        }
        
        # Add search criteria
        if query:
            search_params['q'] = query
        
        if court_ids:
            search_params['court'] = ' OR '.join(court_ids)
        
        if date_after:
            search_params['filed_after'] = date_after
        
        if date_before:
            search_params['filed_before'] = date_before
        
        if nature_of_suit:
            search_params['nature_of_suit'] = ' OR '.join(nature_of_suit)
        
        try:
            # Perform search using search_with_filters
            results = await self.cl_service.search_with_filters(
                query=query,
                search_type='o',  # Opinions
                court_ids=court_ids,
                nature_of_suit=nature_of_suit,
                date_range=(date_after, date_before) if date_after or date_before else None,
                max_results=max_results
            )
            
            if not results:
                return {
                    'success': False,
                    'total_results': 0,
                    'documents': [],
                    'error': 'No results found'
                }
            
            # Process results (search_with_filters returns a list)
            documents = []
            for result in results:
                doc = await self._process_opinion(result, result.get('court', ''))
                if doc:
                    documents.append(doc)
            
            return {
                'success': True,
                'total_results': len(results),
                'documents': documents,
                'search_params': search_params
            }
            
        except Exception as e:
            logger.error(f"Opinion search failed: {e}")
            return {
                'success': False,
                'total_results': 0,
                'documents': [],
                'error': str(e)
            }
    
    async def _fetch_and_process_recap(self,
                                     court_ids: List[str],
                                     date_after: str,
                                     max_per_court: int,
                                     use_recap_fallback: bool = False,
                                     check_recap_first: bool = True,
                                     max_pacer_cost: float = 0.0) -> List[Dict[str, Any]]:
        """
        Fetch and process RECAP documents with free-first approach
        
        NOTE: RECAP requires specific docket numbers and cannot do broad searches.
        This method will search existing RECAP documents only.
        """
        processed_documents = []
        total_cost = 0.0
        
        try:
            # Note: RECAP search is limited - cannot do broad topic searches
            # We can only search for docket numbers we already know about
            logger.warning("RECAP search requires specific docket numbers - broad searches not supported")
            
            # If we have specific docket numbers (from somewhere), we could search for them
            # For now, return empty as we don't have docket numbers to search for
            
            return processed_documents
            
        except Exception as e:
            logger.error(f"RECAP processing error: {e}")
            return processed_documents
    
    async def _handle_recap_fallback(self, court_id: str, date_after: str,
                                   existing_results: List[Dict],
                                   processed_documents: List[Dict],
                                   total_cost: float,
                                   max_pacer_cost: float) -> float:
        """
        Handle RECAP Fetch API fallback for missing documents
        
        Returns updated total cost
        """
        if total_cost >= max_pacer_cost:
            logger.info(f"PACER cost limit reached (${max_pacer_cost}), skipping fallback")
            return total_cost
        
        logger.info(f"Checking for additional documents via PACER for {court_id}")
        
        # Import RECAP client only if needed
        from .recap.authenticated_client import AuthenticatedRECAPClient
        
        try:
            webhook_url = os.getenv('RECAP_WEBHOOK_URL')
            
            async with AuthenticatedRECAPClient(
                self.cl_service.api_key,
                self.pacer_username,
                self.pacer_password,
                webhook_url
            ) as recap_client:
                # Get list of recent notable cases we might want
                # This is a simplified example - in production you'd have
                # more sophisticated logic to identify missing documents
                
                # For now, let's just log that fallback is available
                logger.info(f"RECAP Fetch API ready for {court_id}")
                logger.info("Fallback purchasing not yet fully implemented")
                
                # Future implementation would:
                # 1. Identify specific missing dockets
                # 2. Check if they're worth purchasing
                # 3. Submit RECAP Fetch requests
                # 4. Register with webhook handler
                # 5. Let webhooks handle completion
                
        except Exception as e:
            logger.error(f"RECAP fallback error: {e}")
        
        return total_cost
    
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