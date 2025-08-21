#!/usr/bin/env python3
"""
Standalone Enhanced Court Document Processor

A self-contained processor that works directly with CourtListener API
without dependencies on the broken inheritance chain. Once verified,
this will replace the non-functional enhanced processor.
"""

import asyncio
import aiohttp
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import logging

# Simple configuration
@dataclass
class ProcessorConfig:
    """Simplified configuration for standalone processor"""
    courtlistener_api_key: str = ""
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"
    haystack_url: str = "http://localhost:8000"
    timeout: int = 30
    max_retries: int = 3
    rate_limit_delay: float = 0.5

class StandaloneDeduplicationManager:
    """Simple deduplication manager without inheritance issues"""
    
    def __init__(self):
        self.processed_ids: Set[str] = set()
        self.processed_checksums: Set[str] = set()
    
    def is_duplicate(self, document: Dict[str, Any]) -> bool:
        """Check if document is duplicate"""
        doc_id = str(document.get('id', ''))
        if doc_id in self.processed_ids:
            return True
        
        # Check content-based deduplication
        content = document.get('plain_text', '')
        if content:
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

class StandaloneCourtListenerService:
    """Standalone CourtListener API service"""
    
    def __init__(self, config: ProcessorConfig):
        self.config = config
        self.session = None
        self.logger = logging.getLogger("courtlistener_service")
    
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
            "User-Agent": "Standalone Court Processor v1.0",
            "Accept": "application/json"
        }
        
        if self.config.courtlistener_api_key:
            headers["Authorization"] = f"Token {self.config.courtlistener_api_key}"
        
        return headers
    
    async def fetch_gilstrap_documents(self, 
                                     max_documents: int = 50,
                                     court_id: str = "txed") -> List[Dict[str, Any]]:
        """Fetch Judge Gilstrap documents from CourtListener using search API"""
        if not self.session:
            raise RuntimeError("Service not initialized. Use async context manager.")
        
        self.logger.info(f"Fetching Judge Gilstrap documents (max: {max_documents}, court: {court_id})")
        
        # Use search API with correct syntax from API reference
        search_url = f"{self.config.courtlistener_base_url}/search/"
        params = {
            'q': 'judge:gilstrap',  # Correct search syntax
            'type': 'o',  # Case law opinions
            'court': court_id,  # Court filtering
            'page_size': min(max_documents, 100)
        }
        
        try:
            async with self.session.get(search_url, params=params) as response:
                if response.status != 200:
                    self.logger.error(f"Search API failed: {response.status}")
                    error_text = await response.text()
                    self.logger.error(f"Error response: {error_text}")
                    return []
                
                data = await response.json()
                search_results = data.get('results', [])
                self.logger.info(f"Found {len(search_results)} Gilstrap search results")
                
                # Get full opinion data for each result
                documents = []
                for result in search_results:
                    if len(documents) >= max_documents:
                        break
                    
                    # Add rate limiting
                    await asyncio.sleep(self.config.rate_limit_delay)
                    
                    # Get opinion IDs from nested opinions array
                    opinions = result.get('opinions', [])
                    
                    for opinion_data in opinions:
                        opinion_id = opinion_data.get('id')
                        if opinion_id:
                            opinion = await self._fetch_opinion_by_id(opinion_id)
                            if opinion:
                                # Enhance with search result metadata
                                opinion['search_result'] = result
                                opinion['search_opinion_data'] = opinion_data
                                documents.append(opinion)
                                self.logger.info(f"Successfully added opinion {opinion_id}")
                            else:
                                self.logger.warning(f"Failed to fetch opinion {opinion_id}")
                        else:
                            self.logger.warning(f"No opinion ID found in opinion data: {opinion_data}")
                
                self.logger.info(f"Fetched {len(documents)} full opinion documents")
                return documents
                
        except Exception as e:
            self.logger.error(f"Error fetching Gilstrap documents: {str(e)}")
            return []
    
    async def _fetch_opinion_by_id(self, opinion_id: str) -> Optional[Dict[str, Any]]:
        """Fetch full opinion data by ID"""
        opinion_url = f"{self.config.courtlistener_base_url}/opinions/{opinion_id}/"
        
        try:
            async with self.session.get(opinion_url) as response:
                if response.status == 200:
                    opinion = await response.json()
                    self.logger.debug(f"Fetched opinion {opinion_id}")
                    
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

class StandaloneEnhancedProcessor:
    """Standalone enhanced processor without inheritance dependencies"""
    
    def __init__(self, config: Optional[ProcessorConfig] = None):
        # Initialize configuration
        if config is None:
            config = ProcessorConfig()
            # Load from environment
            config.courtlistener_api_key = os.getenv('COURTLISTENER_API_TOKEN', '')
            config.haystack_url = os.getenv('HAYSTACK_URL', 'http://localhost:8000')
        
        self.config = config
        self.dedup_manager = StandaloneDeduplicationManager()
        self.logger = logging.getLogger("standalone_processor")
        
        # Validate configuration
        if not self.config.courtlistener_api_key:
            self.logger.warning("No CourtListener API key configured")
    
    async def process_gilstrap_documents(self, 
                                       max_documents: int = 50,
                                       court_id: str = "txed") -> Dict[str, Any]:
        """Process Judge Gilstrap documents end-to-end"""
        
        stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'errors': 0,
            'processing_time': 0,
            'documents': []
        }
        
        start_time = time.time()
        
        try:
            self.logger.info(f"Starting Gilstrap document processing (max: {max_documents})")
            
            # Fetch documents from CourtListener
            async with StandaloneCourtListenerService(self.config) as cl_service:
                documents = await cl_service.fetch_gilstrap_documents(max_documents, court_id)
            
            stats['total_fetched'] = len(documents)
            self.logger.info(f"Fetched {len(documents)} documents from CourtListener")
            
            # Process each document
            for i, doc in enumerate(documents):
                try:
                    # Check for duplicates
                    if self.dedup_manager.is_duplicate(doc):
                        stats['duplicates'] += 1
                        self.logger.debug(f"Skipping duplicate document {doc.get('id')}")
                        continue
                    
                    # Process document
                    processed_doc = await self._process_single_document(doc)
                    
                    if processed_doc['success']:
                        stats['new_documents'] += 1
                        stats['documents'].append(processed_doc['document'])
                        self.dedup_manager.mark_processed(doc)
                        self.logger.info(f"Processed document {i+1}/{len(documents)}: {processed_doc['document'].get('case_name', 'Unknown')}")
                    else:
                        stats['errors'] += 1
                        self.logger.error(f"Failed to process document {doc.get('id')}: {processed_doc.get('error')}")
                
                except Exception as e:
                    stats['errors'] += 1
                    self.logger.error(f"Error processing document {i}: {str(e)}")
            
            stats['processing_time'] = time.time() - start_time
            
            self.logger.info(f"Processing complete: {stats['new_documents']} new, {stats['duplicates']} duplicates, {stats['errors']} errors")
            return stats
            
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            stats['error'] = str(e)
            stats['processing_time'] = time.time() - start_time
            return stats
    
    async def _process_single_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single document with enhancement"""
        try:
            # Extract document content using API reference priority order
            content = (doc.get('plain_text') or 
                      doc.get('html') or 
                      doc.get('xml_harvard') or 
                      '')
            
            if not content and doc.get('download_url'):
                # Could implement PDF download and extraction here
                content = f"Document available at: {doc['download_url']}"
            
            # Get search result metadata if available
            search_result = doc.get('search_result', {})
            
            # Create enhanced document with rich metadata
            enhanced_doc = {
                'id': doc.get('id'),
                'cluster_id': doc.get('cluster_id'),
                'content': content,
                'meta': {
                    # Core identification
                    'source': 'courtlistener_standalone',
                    'courtlistener_id': doc.get('id'),
                    'cluster_id': doc.get('cluster_id'),
                    
                    # Search result metadata (richer than direct API)
                    'case_name': search_result.get('caseName', ''),
                    'date_filed': search_result.get('dateFiled', ''),
                    'court': search_result.get('court', 'Eastern District of Texas'),
                    'court_id': search_result.get('court_id', 'txed'),
                    'judge_name': search_result.get('judge', 'Rodney Gilstrap'),
                    'status': search_result.get('status', ''),
                    'snippet': search_result.get('snippet', ''),
                    
                    # Opinion-specific metadata
                    'author_str': doc.get('author_str', ''),
                    'type': doc.get('type', 'opinion'),
                    'page_count': doc.get('page_count', 0),
                    'per_curiam': doc.get('per_curiam', False),
                    'sha1': doc.get('sha1', ''),
                    
                    # URLs and resources
                    'download_url': doc.get('download_url'),
                    'absolute_url': doc.get('absolute_url'),
                    'local_path': doc.get('local_path'),
                    
                    # Processing metadata
                    'processing_timestamp': datetime.utcnow().isoformat(),
                    'fetched_at': doc.get('fetched_at'),
                    'api_version': 'v4',
                    
                    # Legal classification
                    'is_gilstrap_case': True,  # Since we're filtering for Gilstrap
                    'is_patent_case': self._detect_patent_case(content),
                    
                    # Content analysis
                    'content_length': len(content),
                    'has_content': bool(content.strip()),
                    'legal_issues': self._extract_legal_issues(content),
                    'citations': self._extract_basic_citations(content)
                }
            }
            
            # Try to extract case name from content
            case_name = self._extract_case_name(content)
            if case_name:
                enhanced_doc['meta']['case_name'] = case_name
            
            return {
                'success': True,
                'document': enhanced_doc
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_patent_case(self, content: str) -> bool:
        """Detect if this is a patent case"""
        if not content:
            return False
        
        content_lower = content.lower()
        patent_terms = ['patent', 'infringement', 'claim construction', 'obviousness', 'anticipation']
        return any(term in content_lower for term in patent_terms)
    
    def _extract_legal_issues(self, content: str) -> List[str]:
        """Extract legal issues from content"""
        if not content:
            return []
        
        content_lower = content.lower()
        legal_terms = [
            'patent infringement', 'summary judgment', 'preliminary injunction',
            'claim construction', 'markman', 'obviousness', 'anticipation',
            'damages', 'licensing', 'validity', 'enablement'
        ]
        
        found_issues = []
        for term in legal_terms:
            if term in content_lower:
                found_issues.append(term)
        
        return found_issues[:10]  # Limit to 10
    
    def _extract_basic_citations(self, content: str) -> List[str]:
        """Extract basic legal citations from content"""
        if not content:
            return []
        
        import re
        
        citation_patterns = [
            r'\d+\s+U\.S\.\s+\d+',  # US Reports
            r'\d+\s+F\.\d*d?\s+\d+',  # Federal Reporter
            r'\d+\s+F\.\s*Supp\.\s*\d*d?\s+\d+',  # Federal Supplement
            r'Fed\.\s*R\.\s*Civ\.\s*P\.\s*\d+',  # Federal Rules
        ]
        
        citations = set()
        for pattern in citation_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                citations.add(match.group().strip())
        
        return list(citations)[:20]  # Limit to 20
    
    def _extract_case_name(self, content: str) -> Optional[str]:
        """Extract case name from content"""
        if not content:
            return None
        
        # Look for typical case name patterns
        lines = content.split('\n')[:20]  # Check first 20 lines
        
        for line in lines:
            line = line.strip()
            if 'v.' in line and len(line) < 200:
                # Clean up the line
                line = line.replace('\t', ' ')
                while '  ' in line:
                    line = line.replace('  ', ' ')
                
                if line and not line.startswith('Civil Action'):
                    return line
        
        return None
    
    async def ingest_to_haystack(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ingest processed documents to Haystack"""
        
        self.logger.info(f"Ingesting {len(documents)} documents to Haystack")
        
        stats = {
            'total_documents': len(documents),
            'successful_ingestions': 0,
            'failed_ingestions': 0,
            'errors': []
        }
        
        try:
            import requests
            
            # Prepare documents for Haystack
            haystack_docs = []
            for doc in documents:
                haystack_doc = {
                    'content': doc['content'],
                    'meta': doc['meta']
                }
                haystack_docs.append(haystack_doc)
            
            # Send to Haystack
            response = requests.post(
                f"{self.config.haystack_url}/ingest",
                json=haystack_docs,
                timeout=60,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 201]:
                result = response.json()
                stats['successful_ingestions'] = len(haystack_docs)
                self.logger.info(f"Successfully ingested {len(haystack_docs)} documents to Haystack")
            else:
                stats['failed_ingestions'] = len(haystack_docs)
                error_msg = f"Haystack ingestion failed: {response.status_code} - {response.text}"
                stats['errors'].append(error_msg)
                self.logger.error(error_msg)
                
        except Exception as e:
            stats['failed_ingestions'] = len(documents)
            error_msg = f"Haystack ingestion error: {str(e)}"
            stats['errors'].append(error_msg)
            self.logger.error(error_msg)
        
        return stats
    
    async def process_and_ingest_gilstrap_documents(self, 
                                                  max_documents: int = 50,
                                                  court_id: str = "txed") -> Dict[str, Any]:
        """Complete end-to-end processing and ingestion"""
        
        self.logger.info(f"Starting end-to-end Gilstrap processing and ingestion")
        
        # Process documents
        processing_result = await self.process_gilstrap_documents(max_documents, court_id)
        
        # Ingest to Haystack if we have documents
        if processing_result['documents']:
            ingestion_result = await self.ingest_to_haystack(processing_result['documents'])
            
            # Combine results
            combined_result = {
                **processing_result,
                'haystack_ingestion': ingestion_result
            }
        else:
            combined_result = processing_result
            combined_result['haystack_ingestion'] = {
                'total_documents': 0,
                'successful_ingestions': 0,
                'failed_ingestions': 0,
                'message': 'No documents to ingest'
            }
        
        return combined_result

async def main():
    """Test the standalone processor"""
    import argparse
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Standalone Enhanced Court Processor')
    parser.add_argument('--max-docs', type=int, default=20, help='Maximum documents to process')
    parser.add_argument('--court', default='txed', help='Court ID')
    parser.add_argument('--ingest', action='store_true', help='Also ingest to Haystack')
    
    args = parser.parse_args()
    
    # Create processor
    processor = StandaloneEnhancedProcessor()
    
    if args.ingest:
        # Full end-to-end processing
        result = await processor.process_and_ingest_gilstrap_documents(
            max_documents=args.max_docs,
            court_id=args.court
        )
        
        print("\n" + "="*80)
        print("END-TO-END PROCESSING COMPLETE")
        print("="*80)
        print(f"Documents fetched: {result['total_fetched']}")
        print(f"Documents processed: {result['new_documents']}")
        print(f"Duplicates skipped: {result['duplicates']}")
        print(f"Processing errors: {result['errors']}")
        print(f"Processing time: {result['processing_time']:.2f}s")
        
        if 'haystack_ingestion' in result:
            ing = result['haystack_ingestion']
            print(f"Haystack ingestions: {ing['successful_ingestions']}")
            print(f"Haystack failures: {ing['failed_ingestions']}")
        
        print("="*80)
        
    else:
        # Processing only
        result = await processor.process_gilstrap_documents(
            max_documents=args.max_docs,
            court_id=args.court
        )
        
        print("\n" + "="*80)
        print("PROCESSING COMPLETE")
        print("="*80)
        print(f"Documents fetched: {result['total_fetched']}")
        print(f"Documents processed: {result['new_documents']}")
        print(f"Duplicates skipped: {result['duplicates']}")
        print(f"Processing errors: {result['errors']}")
        print(f"Processing time: {result['processing_time']:.2f}s")
        print("="*80)
        
        # Show sample documents
        if result['documents']:
            print(f"\nSample documents ({min(3, len(result['documents']))}):")
            for i, doc in enumerate(result['documents'][:3]):
                meta = doc['meta']
                print(f"  {i+1}. {meta.get('case_name', 'Unknown Case')}")
                print(f"     Judge: {meta.get('judge_name', 'Unknown')}")
                print(f"     Content: {len(doc['content'])} chars")
                print(f"     Issues: {', '.join(meta.get('legal_issues', [])[:3])}")

if __name__ == "__main__":
    asyncio.run(main())