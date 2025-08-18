#!/usr/bin/env python3
"""
Enhanced Standalone Court Document Processor

This is an improved version of the standalone processor that:
1. Removes Gilstrap hardcoding - works for any judge/court
2. Integrates ComprehensiveJudgeExtractor for better attribution
3. Adds flexible search parameters
4. Maintains content extraction capabilities
5. Provides comprehensive error handling
"""

import asyncio
import aiohttp
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
import logging

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import judge extractor
from comprehensive_judge_extractor import ComprehensiveJudgeExtractor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ProcessorConfig:
    """Enhanced configuration for flexible document processing"""
    courtlistener_api_key: str = ""
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    haystack_url: str = "http://localhost:8000"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.5
    enable_pdf_extraction: bool = True
    enable_judge_extraction: bool = True
    enable_deduplication: bool = True


class EnhancedDeduplicationManager:
    """Deduplication manager with content and ID checking"""
    
    def __init__(self):
        self.processed_ids: Set[str] = set()
        self.processed_checksums: Set[str] = set()
        self.processed_case_numbers: Set[str] = set()
    
    def is_duplicate(self, document: Dict[str, Any]) -> bool:
        """Check if document is duplicate by ID, content hash, or case number"""
        # Check by ID
        doc_id = str(document.get('id', ''))
        if doc_id and doc_id in self.processed_ids:
            return True
        
        # Check by case number (avoid processing same case multiple times)
        case_number = document.get('case_number') or document.get('search_result', {}).get('caseName', '')
        if case_number and case_number in self.processed_case_numbers:
            return True
        
        # Check by content hash
        content = document.get('plain_text', '') or document.get('html', '')
        if content and len(content) > 100:
            checksum = str(hash(content))
            if checksum in self.processed_checksums:
                return True
            self.processed_checksums.add(checksum)
        
        return False
    
    def mark_processed(self, document: Dict[str, Any]):
        """Mark document as processed"""
        doc_id = str(document.get('id', ''))
        if doc_id:
            self.processed_ids.add(doc_id)
        
        case_number = document.get('case_number') or document.get('search_result', {}).get('caseName', '')
        if case_number:
            self.processed_case_numbers.add(case_number)


class EnhancedCourtListenerService:
    """Flexible CourtListener API service for any court/judge/date"""
    
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.session = None
        self.logger = logging.getLogger("enhanced_courtlistener_service")
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.config.timeout),
            headers=self._get_headers()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "User-Agent": "Enhanced Court Processor v2.0",
            "Accept": "application/json"
        }
        
        if self.config.courtlistener_api_key:
            headers["Authorization"] = f"Token {self.config.courtlistener_api_key}"
        
        return headers
    
    def _build_search_query(self, 
                          judge_name: Optional[str] = None,
                          date_after: Optional[str] = None,
                          date_before: Optional[str] = None,
                          docket_number: Optional[str] = None,
                          case_name: Optional[str] = None,
                          custom_query: Optional[str] = None) -> str:
        """
        Build flexible search query for CourtListener API
        
        Examples:
            judge_name="Gilstrap" -> 'judge:"Gilstrap"'
            date_after="2024-01-01" -> 'filed_after:2024-01-01'
            custom_query="patent infringement" -> adds custom text
        """
        query_parts = []
        
        if judge_name:
            # Handle multi-word judge names
            if ' ' in judge_name:
                query_parts.append(f'judge:"{judge_name}"')
            else:
                query_parts.append(f'judge:{judge_name}')
        
        if date_after:
            query_parts.append(f'filed_after:{date_after}')
        
        if date_before:
            query_parts.append(f'filed_before:{date_before}')
        
        if docket_number:
            # Handle various docket number formats
            query_parts.append(f'docketNumber:"{docket_number}"')
        
        if case_name:
            query_parts.append(f'caseName:"{case_name}"')
        
        if custom_query:
            query_parts.append(custom_query)
        
        # Join with AND operator for all conditions
        return ' AND '.join(query_parts) if query_parts else ''
    
    async def search_court_documents(self,
                                    court_id: Optional[str] = None,
                                    judge_name: Optional[str] = None,
                                    date_after: Optional[str] = None,
                                    date_before: Optional[str] = None,
                                    max_documents: int = 50,
                                    custom_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for court documents with flexible parameters
        
        This replaces the hardcoded fetch_gilstrap_documents method
        """
        if not self.session:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        self.logger.info(f"Searching court documents - Court: {court_id}, Judge: {judge_name}, Max: {max_documents}")
        
        # Build flexible query
        query = self._build_search_query(
            judge_name=judge_name,
            date_after=date_after,
            date_before=date_before,
            custom_query=custom_query
        )
        
        # Build search parameters
        params = {
            'type': 'o',  # Opinions
            'page_size': min(max_documents, 100)
        }
        
        if query:
            params['q'] = query
        
        if court_id:
            params['court'] = court_id
        
        self.logger.info(f"Search query: {query if query else 'No query filters'}")
        
        search_url = f"{self.config.courtlistener_base_url}/search/"
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Search API failed: {response.status}")
                    error_text = await response.text()
                    self.logger.error(f"Error response: {error_text}")
                    return []
                
                data = await response.json()
                search_results = data.get('results', [])
                self.logger.info(f"Found {len(search_results)} search results")
                
                # Fetch full opinion data for each result
                documents = []
                for result in search_results:
                    if len(documents) >= max_documents:
                        break
                    
                    # Rate limiting
                    await asyncio.sleep(self.config.rate_limit_delay)
                    
                    # Process each opinion in the result
                    opinions = result.get('opinions', [])
                    
                    for opinion_data in opinions:
                        opinion_id = opinion_data.get('id')
                        if opinion_id:
                            full_opinion = await self._fetch_opinion_by_id(opinion_id)
                            if full_opinion:
                                # Preserve search result metadata
                                full_opinion['search_result'] = result
                                full_opinion['search_opinion_data'] = opinion_data
                                documents.append(full_opinion)
                                self.logger.info(f"Added opinion {opinion_id} - {result.get('caseName', 'Unknown')}")
                            else:
                                self.logger.warning(f"Failed to fetch opinion {opinion_id}")
                        
                        if len(documents) >= max_documents:
                            break
                
                self.logger.info(f"Successfully fetched {len(documents)} full opinion documents")
                return documents
                
        except Exception as e:
            self.logger.error(f"Error searching documents: {str(e)}")
            return []
    
    async def _fetch_opinion_by_id(self, opinion_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full opinion data by ID with all content fields"""
        opinion_url = f"{self.config.courtlistener_base_url}/opinions/{opinion_id}/"
        
        try:
            async with self.session.get(opinion_url) as response:
                if response.status == 200:
                    opinion = await response.json()
                    
                    # Add processing metadata
                    opinion['source'] = 'courtlistener_api'
                    opinion['fetched_at'] = datetime.utcnow().isoformat()
                    
                    return opinion
                else:
                    self.logger.warning(f"Opinion API failed for {opinion_id}: {response.status}")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error fetching opinion {opinion_id}: {str(e)}")
            return None


class EnhancedStandaloneProcessor:
    """Enhanced processor with flexible search and comprehensive judge extraction"""
    
    def __init__(self, config: Optional[ProcessorConfig] = None):
        if config is None:
            config = ProcessorConfig()
            # Load from environment
            config.courtlistener_api_key = os.getenv('COURTLISTENER_API_KEY', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
            config.haystack_url = os.getenv('HAYSTACK_URL', 'http://localhost:8000')
        
        self.config = config
        self.dedup_manager = EnhancedDeduplicationManager() if config.enable_deduplication else None
        self.logger = logging.getLogger("enhanced_standalone_processor")
        
        # Validate configuration
        if not self.config.courtlistener_api_key:
            self.logger.warning("No CourtListener API key configured - some features may be limited")
    
    async def process_court_documents(self,
                                     court_id: Optional[str] = None,
                                     judge_name: Optional[str] = None,
                                     date_after: Optional[str] = None,
                                     date_before: Optional[str] = None,
                                     max_documents: int = 50,
                                     custom_query: Optional[str] = None,
                                     extract_judges: bool = True) -> Dict[str, Any]:
        """
        Process court documents with flexible parameters
        
        Args:
            court_id: Court identifier (e.g., 'txed', 'ded')
            judge_name: Judge name to filter by
            date_after: Start date (YYYY-MM-DD)
            date_before: End date (YYYY-MM-DD)
            max_documents: Maximum documents to process
            custom_query: Additional search query
            extract_judges: Whether to run comprehensive judge extraction
            
        Returns:
            Processing statistics and documents
        """
        stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'errors': 0,
            'processing_time': 0,
            'judge_attribution': 0,
            'content_extracted': 0,
            'documents': []
        }
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting document processing - Court: {court_id}, Judge: {judge_name}")
            
            # Fetch documents from CourtListener
            async with EnhancedCourtListenerService(self.config) as cl_service:
                documents = await cl_service.search_court_documents(
                    court_id=court_id,
                    judge_name=judge_name,
                    date_after=date_after,
                    date_before=date_before,
                    max_documents=max_documents,
                    custom_query=custom_query
                )
            
            stats['total_fetched'] = len(documents)
            self.logger.info(f"Fetched {len(documents)} documents from CourtListener")
            
            # Process each document
            for i, doc in enumerate(documents):
                try:
                    # Check for duplicates if enabled
                    if self.dedup_manager and self.dedup_manager.is_duplicate(doc):
                        stats['duplicates'] += 1
                        self.logger.debug(f"Skipping duplicate document {doc.get('id')}")
                        continue
                    
                    # Process document with enhancements
                    processed_doc = await self._process_single_document(doc, extract_judges)
                    
                    if processed_doc['success']:
                        stats['new_documents'] += 1
                        stats['documents'].append(processed_doc['document'])
                        
                        # Update statistics
                        if processed_doc['document'].get('meta', {}).get('judge_name'):
                            stats['judge_attribution'] += 1
                        if processed_doc['document'].get('content'):
                            stats['content_extracted'] += 1
                        
                        # Mark as processed
                        if self.dedup_manager:
                            self.dedup_manager.mark_processed(doc)
                        
                        self.logger.info(f"Processed {i+1}/{len(documents)}: {processed_doc['document'].get('meta', {}).get('case_name', 'Unknown')}")
                    else:
                        stats['errors'] += 1
                        self.logger.error(f"Failed to process document {doc.get('id')}: {processed_doc.get('error')}")
                
                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(f"Error processing document {i}: {str(e)}")
            
            stats['processing_time'] = time.time() - start_time
            
            # Calculate rates
            if stats['new_documents'] > 0:
                stats['judge_attribution_rate'] = (stats['judge_attribution'] / stats['new_documents']) * 100
                stats['content_extraction_rate'] = (stats['content_extracted'] / stats['new_documents']) * 100
            else:
                stats['judge_attribution_rate'] = 0
                stats['content_extraction_rate'] = 0
            
            self.logger.info(f"Processing complete: {stats['new_documents']} new, {stats['duplicates']} duplicates, {stats['errors']} errors")
            self.logger.info(f"Judge attribution: {stats['judge_attribution_rate']:.1f}%, Content extraction: {stats['content_extraction_rate']:.1f}%")
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            stats['error'] = str(e)
            stats['processing_time'] = time.time() - start_time
            return stats
    
    async def _process_single_document(self, doc: Dict[str, Any], extract_judges: bool = True) -> Dict[str, Any]:
        """
        Process a single document with comprehensive enhancements
        
        Includes:
        1. Content extraction from multiple fields
        2. Judge extraction using ComprehensiveJudgeExtractor
        3. Metadata assembly
        4. Document classification
        """
        try:
            # Extract content from available fields (priority order)
            content = (
                doc.get('plain_text') or 
                doc.get('html') or 
                doc.get('html_lawbox') or
                doc.get('html_columbia') or
                doc.get('xml_harvard') or 
                ''
            )
            
            # Check for PDF URL if no content
            if not content and doc.get('download_url'):
                # Mark for future PDF extraction
                content = f"[PDF available: {doc['download_url']}]"
            
            # Get search result metadata
            search_result = doc.get('search_result', {})
            search_opinion = doc.get('search_opinion_data', {})
            
            # Extract judge information using ComprehensiveJudgeExtractor
            judge_name = None
            judge_source = None
            judge_confidence = 0.0
            
            if extract_judges and self.config.enable_judge_extraction:
                try:
                    judge_info = ComprehensiveJudgeExtractor.extract_comprehensive_judge_info(
                        search_result=search_result,
                        opinion_data=doc,
                        docket_number=search_result.get('docketNumber')
                    )
                    
                    if judge_info:
                        judge_name = judge_info.name
                        judge_source = judge_info.source
                        judge_confidence = judge_info.confidence
                        self.logger.debug(f"Extracted judge: {judge_name} (source: {judge_source}, confidence: {judge_confidence})")
                except Exception as e:
                    self.logger.warning(f"Judge extraction failed: {str(e)}")
                    # Fall back to search result judge
                    judge_name = search_result.get('judge')
                    judge_source = 'search_result'
                    judge_confidence = 0.5
            
            # Create enhanced document
            enhanced_doc = {
                'id': doc.get('id'),
                'cluster_id': doc.get('cluster_id'),
                'content': content,
                'meta': {
                    # Core identification
                    'source': 'courtlistener_standalone',  # Maintain compatibility with 020lead
                    'courtlistener_id': doc.get('id'),
                    'cluster_id': doc.get('cluster_id'),
                    
                    # Case information
                    'case_name': search_result.get('caseName', ''),
                    'case_number': search_result.get('docketNumber', ''),
                    'date_filed': search_result.get('dateFiled', ''),
                    'date_argued': doc.get('date_argued'),
                    
                    # Court information
                    'court': search_result.get('court', ''),
                    'court_id': search_result.get('court_id', ''),
                    'court_citation': search_result.get('court_citation', ''),
                    
                    # Judge information (comprehensive)
                    'judge_name': judge_name,
                    'judge_source': judge_source,
                    'judge_confidence': judge_confidence,
                    'all_judge_sources': {
                        'search': search_result.get('judge'),
                        'opinion': doc.get('author_str'),
                        'panel': doc.get('panel_names')
                    },
                    
                    # Opinion metadata
                    'author_str': doc.get('author_str', ''),
                    'per_curiam': doc.get('per_curiam', False),
                    'type': doc.get('type', ''),
                    'status': search_result.get('status', ''),
                    'snippet': search_result.get('snippet', ''),
                    
                    # Citations
                    'citation': search_result.get('citation', []),
                    'citation_count': search_result.get('citation_count', 0),
                    'cited_by': doc.get('opinions_cited', []),
                    
                    # URLs and resources
                    'download_url': doc.get('download_url'),
                    'absolute_url': doc.get('absolute_url') or search_result.get('absolute_url'),
                    'local_path': doc.get('local_path'),
                    
                    # Processing metadata
                    'processing_timestamp': datetime.utcnow().isoformat(),
                    'fetched_at': doc.get('fetched_at'),
                    'content_length': len(content),
                    'has_content': bool(content and not content.startswith('[PDF available:')),
                    
                    # Classification
                    'is_patent_case': self._detect_patent_case(content),
                    'document_type': self._classify_document_type(doc, search_result),
                    'legal_issues': self._extract_legal_issues(content)
                }
            }
            
            return {
                'success': True,
                'document': enhanced_doc
            }
            
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_patent_case(self, content: str) -> bool:
        """Detect if this is a patent case"""
        if not content or len(content) < 100:
            return False
        
        content_lower = content.lower()
        patent_terms = ['patent', 'infringement', 'claim construction', 'obviousness', 
                       'anticipation', '35 u.s.c', 'patent owner', 'inter partes']
        
        # Count occurrences
        patent_count = sum(1 for term in patent_terms if term in content_lower)
        return patent_count >= 3
    
    def _classify_document_type(self, doc: Dict, search_result: Dict) -> str:
        """Classify document type based on metadata"""
        # Check for specific opinion types
        opinion_type = doc.get('type', '').lower()
        if '020lead' in opinion_type or 'lead' in opinion_type:
            return '020lead'
        elif '010combined' in opinion_type:
            return '010combined'
        elif '030concurrence' in opinion_type:
            return '030concurrence'
        elif '040dissent' in opinion_type:
            return '040dissent'
        
        # Default to opinion
        return 'opinion'
    
    def _extract_legal_issues(self, content: str) -> List[str]:
        """Extract legal issues from content"""
        if not content or len(content) < 100:
            return []
        
        content_lower = content.lower()
        legal_issues = []
        
        # Common legal issues
        issue_patterns = {
            'summary judgment': 'summary judgment',
            'preliminary injunction': 'preliminary injunction',
            'motion to dismiss': 'motion to dismiss',
            'claim construction': 'claim construction',
            'markman': 'markman hearing',
            'daubert': 'daubert motion',
            'class certification': 'class certification',
            'jurisdiction': 'jurisdiction',
            'standing': 'standing',
            'damages': 'damages'
        }
        
        for pattern, issue in issue_patterns.items():
            if pattern in content_lower:
                legal_issues.append(issue)
        
        return legal_issues[:5]  # Limit to top 5 issues


# Testing and validation
async def test_enhanced_processor():
    """Test the enhanced processor with various parameters"""
    
    processor = EnhancedStandaloneProcessor()
    
    # Test 1: General court search (not Gilstrap specific)
    print("\n" + "="*60)
    print("Test 1: Eastern District of Texas - Recent Cases")
    print("="*60)
    
    result = await processor.process_court_documents(
        court_id='txed',
        date_after='2024-01-01',
        max_documents=3,
        extract_judges=True
    )
    
    print(f"Fetched: {result['total_fetched']}")
    print(f"Processed: {result['new_documents']}")
    print(f"Judge attribution rate: {result.get('judge_attribution_rate', 0):.1f}%")
    print(f"Content extraction rate: {result.get('content_extraction_rate', 0):.1f}%")
    
    # Test 2: Specific judge search
    print("\n" + "="*60)
    print("Test 2: Search for specific judge")
    print("="*60)
    
    result = await processor.process_court_documents(
        court_id='txed',
        judge_name='Payne',  # Roy S. Payne
        max_documents=2,
        extract_judges=True
    )
    
    print(f"Fetched: {result['total_fetched']}")
    if result['documents']:
        doc = result['documents'][0]
        meta = doc['meta']
        print(f"Sample case: {meta['case_name']}")
        print(f"Judge: {meta['judge_name']} (confidence: {meta['judge_confidence']})")
    
    return result


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_enhanced_processor())