"""
RECAP Document Processor

Specialized processor for RECAP data including:
- Docket processing
- Document metadata enrichment
- IP case identification
- Transcript handling
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

from .unified_document_processor import UnifiedDocumentProcessor
from .courtlistener_service import CourtListenerService
from .legal_document_enhancer import DocumentType

logger = logging.getLogger(__name__)


class RECAPProcessor(UnifiedDocumentProcessor):
    """
    Extended processor for RECAP-specific documents
    """
    
    def __init__(self):
        super().__init__()
        self.recap_stats = {
            'dockets_processed': 0,
            'documents_found': 0,
            'documents_available': 0,
            'transcripts_found': 0,
            'ip_cases_found': 0
        }
    
    async def process_recap_docket(self, docket_data: Dict) -> Dict:
        """
        Process a complete RECAP docket with all associated documents
        
        Args:
            docket_data: Docket metadata from CourtListener
            
        Returns:
            Processing results with statistics
        """
        results = {
            'docket_id': docket_data.get('id'),
            'case_name': docket_data.get('case_name'),
            'court': docket_data.get('court'),
            'nature_of_suit': docket_data.get('nature_of_suit'),
            'documents_processed': 0,
            'errors': []
        }
        
        try:
            # Check if it's an IP case
            if self._is_ip_case(docket_data):
                self.recap_stats['ip_cases_found'] += 1
                results['is_ip_case'] = True
            
            # Get all documents for this docket
            documents = await self.cl_service.fetch_recap_documents(
                docket_data['id']
            )
            
            results['total_documents'] = len(documents)
            self.recap_stats['documents_found'] += len(documents)
            
            # Process each document
            for doc in documents:
                try:
                    # Check if it's a transcript
                    if self._is_transcript(doc):
                        self.recap_stats['transcripts_found'] += 1
                        doc['detected_type'] = 'transcript'
                    
                    # Check document availability
                    if doc.get('filepath_local'):
                        is_available = await self.cl_service.check_document_availability(
                            doc['filepath_local']
                        )
                        if is_available:
                            self.recap_stats['documents_available'] += 1
                            doc['pdf_available'] = True
                    
                    # Create unified document structure
                    unified_doc = self._create_unified_recap_document(
                        docket_data, doc
                    )
                    
                    # Process through main pipeline
                    processed = await self.process_single_document(unified_doc)
                    
                    if processed.get('saved_id'):
                        results['documents_processed'] += 1
                    else:
                        results['errors'].append({
                            'doc_id': doc.get('id'),
                            'error': processed.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing RECAP document {doc.get('id')}: {e}")
                    results['errors'].append({
                        'doc_id': doc.get('id'),
                        'error': str(e)
                    })
            
            self.recap_stats['dockets_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing docket {docket_data.get('id')}: {e}")
            results['error'] = str(e)
        
        return results
    
    def _is_ip_case(self, docket_data: Dict) -> bool:
        """Check if docket is an IP-related case"""
        nature_of_suit = docket_data.get('nature_of_suit')
        
        # Check nature of suit codes
        ip_codes = ['820', '830', '835', '840']
        if nature_of_suit in ip_codes:
            return True
        
        # Check case name patterns
        case_name = docket_data.get('case_name', '').lower()
        ip_keywords = ['patent', 'trademark', 'copyright', 'infringement', 
                      'intellectual property', '(ptab)', 'inter partes']
        
        return any(keyword in case_name for keyword in ip_keywords)
    
    def _is_transcript(self, document: Dict) -> bool:
        """Check if document is a transcript"""
        # Check description
        description = document.get('description', '').lower()
        transcript_keywords = ['transcript', 'hearing', 'trial', 'deposition',
                             'oral argument', 'proceedings']
        
        if any(keyword in description for keyword in transcript_keywords):
            return True
        
        # Check document type
        if document.get('document_type') == 'transcript':
            return True
        
        # Check page count (transcripts tend to be longer)
        page_count = document.get('page_count', 0)
        if page_count > 50 and 'minute' not in description:
            # Might be a transcript if it's long and not a minute entry
            return 'hearing' in description or 'trial' in description
        
        return False
    
    def _create_unified_recap_document(self, 
                                     docket_data: Dict, 
                                     doc_data: Dict) -> Dict:
        """
        Create a unified document structure from RECAP data
        
        Combines docket and document metadata into format expected by pipeline
        """
        # Determine document type for legal enhancer
        if self._is_transcript(doc_data):
            doc_type = 'transcript'
        elif 'order' in doc_data.get('description', '').lower():
            doc_type = 'order'
        elif 'motion' in doc_data.get('description', '').lower():
            doc_type = 'motion'
        elif 'brief' in doc_data.get('description', '').lower():
            doc_type = 'brief'
        else:
            doc_type = 'docket_entry'
        
        unified = {
            # Standard identifiers
            'id': f"recap_{doc_data.get('id')}",
            'source': 'recap',
            'type': doc_type,
            
            # Docket information
            'court_id': docket_data.get('court'),
            'docket_id': docket_data.get('id'),
            'docket_number': docket_data.get('docket_number'),
            'case_name': docket_data.get('case_name'),
            'nature_of_suit': docket_data.get('nature_of_suit'),
            
            # Document information
            'document_number': doc_data.get('document_number'),
            'attachment_number': doc_data.get('attachment_number'),
            'description': doc_data.get('description'),
            'document_type': doc_data.get('document_type'),
            
            # Dates
            'date_filed': doc_data.get('date_filed') or docket_data.get('date_filed'),
            'date_created': doc_data.get('date_created'),
            'date_modified': doc_data.get('date_modified'),
            
            # Content
            'plain_text': doc_data.get('plain_text'),
            'ocr_status': doc_data.get('ocr_status'),
            'page_count': doc_data.get('page_count'),
            
            # File information
            'filepath_local': doc_data.get('filepath_local'),
            'pacer_doc_id': doc_data.get('pacer_doc_id'),
            
            # Additional metadata
            'is_available': doc_data.get('is_available', False),
            'is_free_on_pacer': doc_data.get('is_free_on_pacer', False),
            'is_sealed': doc_data.get('is_sealed', False),
            
            # IP case indicator
            'is_ip_case': self._is_ip_case(docket_data),
            
            # For deduplication - combine docket and doc info
            'recap_metadata': {
                'docket_id': docket_data.get('id'),
                'document_id': doc_data.get('id'),
                'pacer_doc_id': doc_data.get('pacer_doc_id')
            }
        }
        
        # Add judge information if available
        if docket_data.get('assigned_to'):
            unified['author_str'] = docket_data['assigned_to']
            unified['author_id'] = docket_data.get('assigned_to_id')
        
        # Add party information
        if docket_data.get('parties'):
            unified['parties'] = docket_data['parties']
        
        return unified
    
    async def process_ip_cases_batch(self,
                                   start_date: str,
                                   end_date: Optional[str] = None,
                                   courts: Optional[List[str]] = None,
                                   include_transcripts_only: bool = False) -> Dict:
        """
        Process a batch of IP cases from RECAP
        
        Args:
            start_date: Start date for filtering
            end_date: End date (defaults to today)
            courts: List of court IDs (defaults to IP-heavy courts)
            include_transcripts_only: Only process transcript documents
            
        Returns:
            Processing statistics
        """
        if not courts:
            courts = self.cl_service.IP_COURTS['district_heavy_ip']
        
        stats = {
            'start_time': datetime.utcnow().isoformat(),
            'dockets_found': 0,
            'dockets_processed': 0,
            'documents_processed': 0,
            'transcripts_processed': 0,
            'errors': []
        }
        
        try:
            # Fetch IP-related dockets
            dockets = await self.cl_service.fetch_recap_dockets(
                court_ids=courts,
                date_filed_after=start_date,
                nature_of_suit=['820', '830', '835', '840'],
                max_results=1000
            )
            
            stats['dockets_found'] = len(dockets)
            logger.info(f"Found {len(dockets)} IP dockets to process")
            
            # Process each docket
            for docket in dockets:
                try:
                    result = await self.process_recap_docket(docket)
                    
                    if not result.get('error'):
                        stats['dockets_processed'] += 1
                        stats['documents_processed'] += result['documents_processed']
                    else:
                        stats['errors'].append({
                            'docket_id': docket['id'],
                            'error': result['error']
                        })
                        
                except Exception as e:
                    logger.error(f"Failed to process docket {docket['id']}: {e}")
                    stats['errors'].append({
                        'docket_id': docket['id'],
                        'error': str(e)
                    })
            
            stats['end_time'] = datetime.utcnow().isoformat()
            stats['recap_stats'] = self.recap_stats
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            stats['error'] = str(e)
        
        return stats
    
    async def search_and_process_recap(self,
                                     search_query: str,
                                     court_ids: Optional[List[str]] = None,
                                     max_results: int = 100) -> Dict:
        """
        Search RECAP and process results
        
        Args:
            search_query: Search terms
            court_ids: Courts to search
            max_results: Maximum results to process
            
        Returns:
            Search and processing results
        """
        results = {
            'query': search_query,
            'documents_found': 0,
            'documents_processed': 0,
            'errors': []
        }
        
        try:
            # Search RECAP
            search_results = await self.cl_service.search_recap(
                query=search_query,
                court_ids=court_ids,
                max_results=max_results
            )
            
            results['documents_found'] = len(search_results)
            
            # Process each result
            for result in search_results:
                try:
                    # Convert search result to unified format
                    unified_doc = {
                        'id': f"recap_search_{result.get('id')}",
                        'source': 'recap_search',
                        'court_id': result.get('court'),
                        'case_name': result.get('caseName'),
                        'docket_number': result.get('docketNumber'),
                        'plain_text': result.get('snippet', ''),
                        'date_filed': result.get('dateFiled'),
                        'type': 'search_result'
                    }
                    
                    # Process through pipeline
                    processed = await self.process_single_document(unified_doc)
                    
                    if processed.get('saved_id'):
                        results['documents_processed'] += 1
                    else:
                        results['errors'].append({
                            'doc_id': result.get('id'),
                            'error': processed.get('error', 'Unknown error')
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing search result: {e}")
                    results['errors'].append({
                        'doc_id': result.get('id'),
                        'error': str(e)
                    })
                    
        except Exception as e:
            logger.error(f"Search failed: {e}")
            results['error'] = str(e)
        
        return results


# Utility functions for RECAP data
def get_recap_document_url(filepath_local: str) -> str:
    """Get the URL for a RECAP document"""
    if not filepath_local:
        return ""
    
    # RECAP documents are served from storage.courtlistener.com
    base_url = "https://storage.courtlistener.com"
    return f"{base_url}/{filepath_local}"


def parse_pacer_case_id(pacer_case_id: str) -> Dict:
    """Parse PACER case ID into components"""
    # PACER case IDs follow pattern: 1:21-cv-00123
    parts = pacer_case_id.split(':')
    if len(parts) == 2:
        office, case = parts
        case_parts = case.split('-')
        if len(case_parts) >= 3:
            return {
                'office': office,
                'year': case_parts[0],
                'type': case_parts[1],
                'number': case_parts[2]
            }
    return {}