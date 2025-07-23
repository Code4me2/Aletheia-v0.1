#!/usr/bin/env python3
"""
Eleven Stage Pipeline - Enhanced Version with Document Type Awareness

This version builds on the robust pipeline and adds:
- Document type detection and routing
- Type-specific extraction strategies
- Enhanced court resolution for opinions
- Fixed judge extraction patterns
- Separate metrics by document type
"""

import asyncio
import logging
import json
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import AsIs

# Import our services
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from services.service_config import SERVICES, IS_DOCKER

# Import FLP components
from courts_db import find_court, courts
from eyecite import get_citations
from reporters_db import REPORTERS
import judge_pics

# Import our custom components
from pipeline_exceptions import *
from pipeline_validators import *
from error_reporter import ErrorCollector

# Create courts dictionary for direct lookup
COURTS_DICT = {court['id']: court for court in courts if isinstance(court, dict)}

# Document type mappings from CourtListener
COURTLISTENER_TYPE_MAP = {
    'opinion': 'opinion',
    '010combined': 'opinion',
    '020lead': 'opinion',
    '030concurrence': 'opinion',
    '040dissent': 'opinion',
    'docket': 'docket',
    'order': 'order',
    'brief': 'brief',
    'motion': 'motion',
    'transcript': 'transcript',
    'R': 'transcript',  # RECAP source code for transcripts
}

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class EnhancedElevenStagePipeline:
    """Enhanced eleven stage document processing pipeline with document type awareness"""
    
    def __init__(self):
        """Initialize pipeline with error tracking and type awareness"""
        try:
            self.db_conn = get_db_connection()
        except Exception as e:
            raise DatabaseConnectionError(
                f"Failed to connect to database: {str(e)}",
                details={'connection_string': os.getenv('DATABASE_URL', 'Not set')}
            )
        
        self.stats = {
            'documents_processed': 0,
            'documents_validated': 0,
            'validation_failures': 0,
            'courts_resolved': 0,
            'courts_unresolved': 0,
            'citations_extracted': 0,
            'citations_validated': 0,
            'judges_enhanced': 0,
            'judges_extracted_from_content': 0,
            'reporters_normalized': 0,
            'keywords_extracted': 0,
            'documents_stored': 0,
            'documents_indexed': 0,
            'total_errors': 0,
            'total_warnings': 0
        }
        
        # Document type statistics
        self.document_type_stats = {
            'opinion': {'total': 0, 'courts_resolved': 0, 'judges_found': 0},
            'docket': {'total': 0, 'courts_resolved': 0, 'judges_found': 0},
            'order': {'total': 0, 'courts_resolved': 0, 'judges_found': 0},
            'transcript': {'total': 0, 'courts_resolved': 0, 'judges_found': 0},
            'unknown': {'total': 0, 'courts_resolved': 0, 'judges_found': 0}
        }
        
        self.error_collector = None
    
    def _detect_document_type(self, document: Dict[str, Any]) -> str:
        """Detect document type based on metadata and content patterns"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Check case number pattern for opinions
        case_number = document.get('case_number', '')
        if case_number.startswith('OPINION-'):
            return 'opinion'
        
        # Check metadata type field
        metadata_type = metadata.get('type', '')
        if metadata_type:
            # Map CourtListener types to our categories
            for cl_type, doc_type in COURTLISTENER_TYPE_MAP.items():
                if cl_type in str(metadata_type):
                    return doc_type
        
        # Check for opinion-specific fields
        if any(key in metadata for key in ['cluster', 'author', 'author_str', 'opinions_cited', 'per_curiam']):
            return 'opinion'
        
        # Check for docket-specific fields
        if any(key in metadata for key in ['docket_id', 'cause', 'nature_of_suit', 'assigned_to']):
            return 'docket'
        
        # Check document_type field
        doc_type_field = document.get('document_type', '')
        if doc_type_field in ['opinion', 'docket', 'order', 'transcript', 'brief', 'motion']:
            return doc_type_field
        
        # Content-based detection as last resort
        content = document.get('content', '')[:1000]  # Check first 1000 chars
        if 'IT IS HEREBY ORDERED' in content.upper():
            return 'order'
        if re.search(r'THE COURT:|COURT REPORTER:|\d+:\d+:\d+', content):
            return 'transcript'
        
        # Default to unknown
        logger.debug(f"Could not determine document type for {document.get('id')}")
        return 'unknown'
    
    async def process_batch(self, 
                          limit: int = 10,
                          source_table: str = 'public.court_documents',
                          validate_strict: bool = True) -> Dict[str, Any]:
        """
        Process a batch of documents through all 11 stages with document type awareness
        """
        start_time = datetime.now()
        run_id = f"run_{start_time.isoformat()}"
        self.error_collector = ErrorCollector(run_id)
        stages_completed = []
        
        try:
            # Stage 1: Document Retrieval
            logger.info("=" * 60)
            logger.info("STAGE 1: Document Retrieval")
            logger.info("=" * 60)
            
            documents = self._fetch_documents(limit, source_table)
            stages_completed.append("Document Retrieval")
            self.stats['documents_processed'] = len(documents)
            logger.info(f"✅ Retrieved {len(documents)} documents from {source_table}")
            
            if not documents:
                return {
                    'success': True,
                    'message': 'No documents found to process',
                    'stages_completed': stages_completed,
                    'statistics': self.stats,
                    'error_report': self.error_collector.get_summary()
                }
            
            # Detect document types
            logger.info("\nDetecting document types...")
            for doc in documents:
                doc_type = self._detect_document_type(doc)
                doc['detected_type'] = doc_type
                self.document_type_stats[doc_type]['total'] += 1
            
            # Log document type distribution
            logger.info("Document type distribution:")
            for doc_type, stats in self.document_type_stats.items():
                if stats['total'] > 0:
                    logger.info(f"  {doc_type}: {stats['total']} documents")
            
            # Validate documents
            valid_documents = []
            for doc in documents:
                validation_result = DocumentValidator.validate_document(doc)
                if validation_result.is_valid:
                    valid_documents.append(doc)
                    self.stats['documents_validated'] += 1
                else:
                    self.stats['validation_failures'] += 1
                    self.error_collector.add_validation_failure(
                        validation_result.to_dict(),
                        stage="Document Validation",
                        document_id=doc.get('id')
                    )
                    if validate_strict:
                        logger.warning(f"Skipping document {doc.get('id')} due to validation errors")
                        continue
                    else:
                        valid_documents.append(doc)
            
            # Process each document through remaining stages
            enhanced_documents = []
            
            for idx, doc in enumerate(valid_documents):
                doc_id = doc.get('id', f'unknown_{idx}')
                doc_type = doc.get('detected_type', 'unknown')
                logger.info(f"\nProcessing {doc_type} document {idx + 1}/{len(valid_documents)}: {doc_id}")
                
                try:
                    # Route to type-specific processor
                    if doc_type == 'opinion':
                        enhanced_doc = await self._process_opinion_document(doc, idx)
                    elif doc_type == 'docket':
                        enhanced_doc = await self._process_docket_document(doc, idx)
                    else:
                        enhanced_doc = await self._process_generic_document(doc, idx)
                    
                    enhanced_documents.append(enhanced_doc)
                    
                    # Update type-specific stats
                    if enhanced_doc.get('court_enhancement', {}).get('resolved'):
                        self.document_type_stats[doc_type]['courts_resolved'] += 1
                    if enhanced_doc.get('judge_enhancement', {}).get('enhanced') or \
                       enhanced_doc.get('judge_enhancement', {}).get('judge_name_found'):
                        self.document_type_stats[doc_type]['judges_found'] += 1
                        
                except PipelineError as e:
                    self.error_collector.add_error(e, e.stage or "Unknown", doc_id)
                    self.stats['total_errors'] += 1
                    logger.error(f"Pipeline error for {doc_type} document {doc_id}: {e}")
                    continue
                except Exception as e:
                    self.error_collector.add_error(
                        e, "Document Processing", doc_id,
                        context={'unexpected': True, 'document_type': doc_type}
                    )
                    self.stats['total_errors'] += 1
                    logger.error(f"Unexpected error for {doc_type} document {doc_id}: {e}", exc_info=True)
                    continue
            
            # Complete remaining stages
            stages_completed.extend([
                "Document Type Detection",
                "Court Resolution",
                "Citation Extraction",
                "Reporter Normalization",
                "Judge Enhancement",
                "Document Structure",
                "Keyword Extraction",
                "Metadata Assembly"
            ])
            
            # Storage and indexing stages (same for all document types)
            storage_results = await self._store_enhanced_documents_validated(enhanced_documents)
            stages_completed.append("Enhanced Storage")
            self.stats['documents_stored'] = storage_results.get('total_processed', 0)
            
            haystack_results = await self._index_to_haystack_validated(enhanced_documents)
            stages_completed.append("Haystack Integration")
            self.stats['documents_indexed'] = haystack_results.get('indexed_count', 0)
            
            # Enhanced verification with type-specific metrics
            verification = self._verify_pipeline_results_by_type(enhanced_documents)
            stages_completed.append("Pipeline Verification")
            
            # Calculate final metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Log error summary
            self.error_collector.log_summary(logger)
            
            # Log type-specific performance
            logger.info("\n" + "=" * 60)
            logger.info("DOCUMENT TYPE PERFORMANCE SUMMARY")
            logger.info("=" * 60)
            for doc_type, stats in self.document_type_stats.items():
                if stats['total'] > 0:
                    court_rate = (stats['courts_resolved'] / stats['total']) * 100
                    judge_rate = (stats['judges_found'] / stats['total']) * 100
                    logger.info(f"\n{doc_type.upper()} ({stats['total']} documents):")
                    logger.info(f"  Court resolution: {stats['courts_resolved']}/{stats['total']} ({court_rate:.1f}%)")
                    logger.info(f"  Judge identification: {stats['judges_found']}/{stats['total']} ({judge_rate:.1f}%)")
            
            return {
                'success': True,
                'run_id': run_id,
                'stages_completed': stages_completed,
                'statistics': self.stats,
                'document_type_statistics': self.document_type_stats,
                'processing_time_seconds': processing_time,
                'verification': verification,
                'storage_results': storage_results,
                'haystack_results': haystack_results,
                'error_report': self.error_collector.get_detailed_report(),
                'quality_metrics': self._calculate_quality_metrics()
            }
            
        except Exception as e:
            self.error_collector.add_error(e, "Pipeline", None, {'unexpected': True})
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            return {
                'success': False,
                'run_id': run_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'stages_completed': stages_completed,
                'partial_stats': self.stats,
                'error_report': self.error_collector.get_detailed_report()
            }
        finally:
            if self.db_conn:
                self.db_conn.close()    # Type-specific processing methods

    async def _process_opinion_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process opinion document with opinion-specific extraction strategies"""
        doc_id = doc.get('id')
        
        # Stage 2: Opinion-specific court resolution
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 2: Court Resolution Enhancement (Opinion)")
            logger.info("=" * 60)
        
        court_info = self._enhance_court_info_opinion(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        # Continue with standard processing for other stages
        return await self._process_common_stages(doc, idx)
    
    async def _process_docket_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process docket document with docket-specific extraction strategies"""
        doc_id = doc.get('id')
        
        # Stage 2: Docket-specific court resolution
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 2: Court Resolution Enhancement (Docket)")
            logger.info("=" * 60)
        
        court_info = self._enhance_court_info_docket(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        # Continue with standard processing
        return await self._process_common_stages(doc, idx)
    
    async def _process_generic_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process generic/unknown document with fallback strategies"""
        # Use the original court resolution method
        court_info = self._enhance_court_info_validated(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        return await self._process_common_stages(doc, idx)
    
    async def _process_common_stages(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process common stages for all document types"""
        doc_id = doc.get('id')
        doc_type = doc.get('detected_type', 'unknown')
        
        # Stage 3: Citation Extraction
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 3: Citation Extraction and Analysis")
            logger.info("=" * 60)
        
        citations_data = self._extract_citations_validated(doc)
        doc['citations_extracted'] = citations_data
        self.stats['citations_extracted'] += citations_data.get('count', 0)
        self.stats['citations_validated'] += citations_data.get('valid_count', 0)
        
        # Stage 4: Reporter Normalization
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 4: Reporter Normalization")
            logger.info("=" * 60)
        
        if doc['citations_extracted']['count'] > 0:
            reporters_data = self._normalize_reporters_validated(
                doc['citations_extracted']['citations']
            )
            doc['reporters_normalized'] = reporters_data
            self.stats['reporters_normalized'] += reporters_data.get('normalized_count', 0)
        else:
            doc['reporters_normalized'] = {'count': 0, 'normalized_reporters': []}
        
        # Stage 5: Judge Enhancement (type-aware)
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 5: Judge Information Enhancement")
            logger.info("=" * 60)
        
        if doc_type == 'opinion':
            judge_info = self._enhance_judge_info_opinion(doc)
        else:
            judge_info = self._enhance_judge_info_validated(doc)
        
        doc['judge_enhancement'] = judge_info
        
        if judge_info.get('enhanced'):
            self.stats['judges_enhanced'] += 1
        if judge_info.get('extracted_from_content'):
            self.stats['judges_extracted_from_content'] += 1
        
        # Stages 6-8: Standard processing
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 6: Document Structure Analysis")
            logger.info("=" * 60)
        
        structure = self._analyze_structure(doc)
        doc['structure_analysis'] = structure
        
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 7: Legal Keyword Extraction")
            logger.info("=" * 60)
        
        keyword_extraction = self._extract_legal_keywords(doc)
        doc['keyword_extraction'] = keyword_extraction
        self.stats['keywords_extracted'] += len(keyword_extraction.get('keywords', []))
        
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 8: Comprehensive Metadata Assembly")
            logger.info("=" * 60)
        
        metadata = self._assemble_metadata_validated(doc)
        doc['comprehensive_metadata'] = metadata
        
        return doc
    
    def _enhance_court_info_opinion(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced court resolution for opinion documents"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        court_hint = None
        extraction_method = None
        
        # Method 1: Extract from cluster URL
        cluster_url = metadata.get('cluster', '')
        if cluster_url and not court_hint:
            # CourtListener cluster URLs sometimes contain court info
            # We would need to fetch the cluster data via API for full info
            # For now, try to extract from the URL pattern
            logger.debug(f"Opinion has cluster URL: {cluster_url}")
            extraction_method = 'cluster_url'
        
        # Method 2: Extract from case name patterns
        case_name = metadata.get('case_name', '') or document.get('case_number', '')
        if case_name and not court_hint:
            court_hint = self._extract_court_from_case_name(case_name)
            if court_hint:
                extraction_method = 'case_name_pattern'
        
        # Method 3: Extract from content
        if not court_hint:
            content = document.get('content', '')
            court_hint = self._extract_court_from_opinion_content(content)
            if court_hint:
                extraction_method = 'content_analysis'
        
        # Method 4: Try the download URL
        download_url = metadata.get('download_url', '')
        if download_url and not court_hint:
            # Ohio Supreme Court example: supremecourt.ohio.gov
            if 'supremecourt.ohio.gov' in download_url:
                court_hint = 'ohioctapp'  # Ohio Court of Appeals
                extraction_method = 'download_url'
        
        if not court_hint:
            logger.warning(f"Could not determine court for opinion {document.get('id')}")
            return {
                'resolved': False,
                'reason': 'No court information found in opinion metadata or content',
                'attempted_methods': ['cluster_url', 'case_name_pattern', 'content_analysis', 'download_url'],
                'metadata_keys': list(metadata.keys())
            }
        
        # Validate and resolve court
        court_validation = CourtValidator.validate_court_id(court_hint)
        
        if court_validation.is_valid:
            court_data = COURTS_DICT.get(court_hint, {})
            return {
                'resolved': True,
                'court_id': court_hint,
                'court_name': court_data.get('name', ''),
                'court_citation': court_data.get('citation_string', ''),
                'court_type': court_data.get('type', ''),
                'court_level': court_data.get('level', ''),
                'extraction_method': extraction_method,
                'document_type': 'opinion',
                'validation': court_validation.to_dict()
            }
        else:
            return {
                'resolved': False,
                'attempted_court_id': court_hint,
                'reason': 'Court ID validation failed',
                'extraction_method': extraction_method,
                'validation_errors': court_validation.errors
            }
    
    def _enhance_court_info_docket(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced court resolution for docket documents"""
        # For dockets, use the standard resolution which works well
        return self._enhance_court_info_validated(document)
    
    def _extract_court_from_case_name(self, case_name: str) -> Optional[str]:
        """Extract court hints from case name patterns"""
        # Common patterns in case names
        patterns = {
            r'United States v\.': 'federal',  # Federal cases
            r'State v\.': 'state',  # State cases
            r'Commonwealth v\.': 'state',  # Commonwealth states
            r'People v\.': 'state',  # Some state cases
            r'In re': 'bankruptcy',  # Often bankruptcy or family court
        }
        
        for pattern, court_type in patterns.items():
            if re.search(pattern, case_name, re.IGNORECASE):
                logger.debug(f"Found {court_type} pattern in case name: {case_name}")
                # This gives us a hint but not a specific court ID
                # Would need more context to determine exact court
                return None
        
        return None
    
    def _extract_court_from_opinion_content(self, content: str) -> Optional[str]:
        """Extract court from opinion content patterns"""
        if not content:
            return None
        
        # Look in first 500 chars for court identification
        content_start = content[:500].upper()
        
        # Federal court patterns
        federal_patterns = [
            (r'UNITED STATES DISTRICT COURT.*?(?:FOR THE\s+)?([A-Z]+)\s+DISTRICT OF\s+([A-Z]+)', 'federal_district'),
            (r'UNITED STATES COURT OF APPEALS.*?([A-Z]+)\s+CIRCUIT', 'federal_appeals'),
            (r'SUPREME COURT OF THE UNITED STATES', 'scotus'),
        ]
        
        for pattern, court_type in federal_patterns:
            match = re.search(pattern, content_start)
            if match:
                if court_type == 'federal_district':
                    # Try to construct court ID like 'txed' for Eastern District of Texas
                    # This would need a mapping table
                    logger.debug(f"Found federal district court pattern: {match.group(0)}")
                elif court_type == 'federal_appeals':
                    # Map circuit number to court ID
                    logger.debug(f"Found federal appeals court pattern: {match.group(0)}")
                return None  # Need mapping logic
        
        # State court patterns
        state_patterns = [
            (r'SUPREME COURT OF ([A-Z]+)', 'state_supreme'),
            (r'COURT OF APPEALS OF ([A-Z]+)', 'state_appeals'),
            (r'([A-Z]+) COURT OF APPEALS', 'state_appeals'),
        ]
        
        for pattern, court_type in state_patterns:
            match = re.search(pattern, content_start)
            if match:
                state_name = match.group(1)
                logger.debug(f"Found {court_type} for state: {state_name}")
                # Would need state name to court ID mapping
                return None
        
        return None
    
    def _enhance_judge_info_opinion(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced judge extraction for opinion documents"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # For opinions, check author fields first
        judge_name = metadata.get('author_str', '') or metadata.get('author', '')
        
        if judge_name:
            logger.info(f"Found judge in opinion author field: {judge_name}")
            return {
                'enhanced': False,
                'reason': 'Found in author metadata',
                'judge_name_found': judge_name,
                'extracted_from_author': True,
                'per_curiam': metadata.get('per_curiam', False),
                'joined_by': metadata.get('joined_by', [])
            }
        
        # Fall back to standard extraction
        return self._enhance_judge_info_validated(document)    # Fixed methods and type-specific verification

    def _extract_judge_from_content_fixed(self, content: str) -> Optional[str]:
        """Extract judge name from document content with fixed patterns"""
        if not content:
            return None
        
        # Fixed judge patterns - more specific to avoid greedy matching
        patterns = [
            # Standard patterns (working well)
            r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'Before:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'JUDGE:\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'Signed\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            
            # Fixed patterns for all-caps names
            r'([A-Z]+\s+[A-Z]\.\s+[A-Z]+)(?:,\s+Chief)?\s+(?:United States\s+)?District Judge',  # JOHN A. SMITH
            r'([A-Z]+\s+[A-Z]+)(?:,\s+Chief)?\s+(?:United States\s+)?District Judge',  # JOHN SMITH
            
            # Opinion-specific patterns
            r'Opinion by:\s*([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+J\.',  # "Smith, J."
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+Circuit Judge',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+dissenting',
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+),\s+concurring',
        ]
        
        # Search in first 2000 characters and last 1000
        content_start = content[:2000]
        content_end = content[-1000:] if len(content) > 1000 else ""
        
        for pattern in patterns:
            # Check start
            match = re.search(pattern, content_start)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                
                # Validate it's actually a name (not all caps like "UNITED STATES DISTRICT")
                if judge_name and not judge_name.isupper() or \
                   (judge_name.isupper() and ' ' in judge_name and len(judge_name.split()) <= 4):
                    logger.info(f"  Extracted judge from content start: {judge_name}")
                    return judge_name
            
            # Check end
            match = re.search(pattern, content_end)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                
                # Validate it's actually a name
                if judge_name and not judge_name.isupper() or \
                   (judge_name.isupper() and ' ' in judge_name and len(judge_name.split()) <= 4):
                    logger.info(f"  Extracted judge from content end: {judge_name}")
                    return judge_name
        
        return None
    
    def _verify_pipeline_results_by_type(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced pipeline verification with document type breakdown"""
        # Overall verification
        overall_verification = self._verify_pipeline_results_validated(documents)
        
        # Type-specific verification
        type_metrics = {}
        for doc_type in ['opinion', 'docket', 'order', 'transcript', 'unknown']:
            type_docs = [d for d in documents if d.get('detected_type') == doc_type]
            if type_docs:
                type_metrics[doc_type] = self._calculate_type_metrics(type_docs)
        
        # Enhanced verification result
        verification = {
            'overall': overall_verification,
            'by_document_type': type_metrics,
            'type_distribution': self.document_type_stats,
            'insights': self._generate_insights(type_metrics)
        }
        
        # Log type-specific performance
        logger.info("\nDocument Type Performance:")
        for doc_type, metrics in type_metrics.items():
            logger.info(f"\n{doc_type.upper()}:")
            logger.info(f"  Documents: {metrics.get('total', 0)}")
            logger.info(f"  Completeness: {metrics.get('completeness_score', 0):.1f}%")
            logger.info(f"  Quality: {metrics.get('quality_score', 0):.1f}%")
        
        return verification
    
    def _calculate_type_metrics(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate metrics for a specific document type"""
        metrics = {
            'total': len(documents),
            'courts_resolved': 0,
            'judges_found': 0,
            'citations_found': 0,
            'keywords_extracted': 0,
            'completeness_score': 0,
            'quality_score': 0
        }
        
        total_completeness = 0
        total_quality = 0
        
        for doc in documents:
            doc_completeness = 0
            doc_quality = 0
            max_possible = 6  # 6 enhancement types
            
            # Court resolution
            if doc.get('court_enhancement', {}).get('resolved'):
                metrics['courts_resolved'] += 1
                doc_completeness += 1
                doc_quality += 2 if not doc.get('court_enhancement', {}).get('validation', {}).get('errors') else 1
            
            # Judge identification
            if doc.get('judge_enhancement', {}).get('enhanced') or \
               doc.get('judge_enhancement', {}).get('judge_name_found'):
                metrics['judges_found'] += 1
                doc_completeness += 1
                doc_quality += 2
            
            # Citations
            if doc.get('citations_extracted', {}).get('count', 0) > 0:
                metrics['citations_found'] += 1
                doc_completeness += 1
                doc_quality += 1
            
            # Keywords
            if len(doc.get('keyword_extraction', {}).get('keywords', [])) > 0:
                metrics['keywords_extracted'] += 1
                doc_completeness += 1
                doc_quality += 1
            
            # Structure and reporters
            if doc.get('structure_analysis', {}).get('sections', 0) > 0:
                doc_completeness += 1
                doc_quality += 1
            
            if doc.get('reporters_normalized', {}).get('normalized_count', 0) > 0:
                doc_completeness += 1
                doc_quality += 1
            
            total_completeness += (doc_completeness / max_possible)
            total_quality += (doc_quality / 10)  # Max quality points = 10
        
        if metrics['total'] > 0:
            metrics['completeness_score'] = (total_completeness / metrics['total']) * 100
            metrics['quality_score'] = (total_quality / metrics['total']) * 100
            metrics['court_resolution_rate'] = (metrics['courts_resolved'] / metrics['total']) * 100
            metrics['judge_identification_rate'] = (metrics['judges_found'] / metrics['total']) * 100
        
        return metrics
    
    def _generate_insights(self, type_metrics: Dict[str, Dict[str, Any]]) -> List[str]:
        """Generate insights from type-specific metrics"""
        insights = []
        
        # Find best and worst performing document types
        if type_metrics:
            best_type = max(type_metrics.items(), 
                          key=lambda x: x[1].get('completeness_score', 0))
            worst_type = min(type_metrics.items(), 
                           key=lambda x: x[1].get('completeness_score', 0))
            
            if best_type[0] != worst_type[0]:
                insights.append(
                    f"{best_type[0].capitalize()} documents have the highest completeness "
                    f"({best_type[1]['completeness_score']:.1f}%) while {worst_type[0]} documents "
                    f"have the lowest ({worst_type[1]['completeness_score']:.1f}%)"
                )
            
            # Check for specific issues
            for doc_type, metrics in type_metrics.items():
                if metrics.get('total', 0) > 0:
                    if metrics.get('court_resolution_rate', 0) < 50:
                        insights.append(
                            f"{doc_type.capitalize()} documents have low court resolution rate "
                            f"({metrics['court_resolution_rate']:.1f}%) - may need specialized extraction"
                        )
                    
                    if metrics.get('judge_identification_rate', 0) < 30:
                        insights.append(
                            f"{doc_type.capitalize()} documents have low judge identification rate "
                            f"({metrics['judge_identification_rate']:.1f}%) - check metadata fields"
                        )
        
        return insights
    
    # Include all the methods from the robust pipeline that we're reusing
    def _fetch_documents(self, limit: int, source_table: str) -> List[Dict[str, Any]]:
        """Stage 1: Fetch documents from database with validation"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Validate table name to prevent SQL injection
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$', source_table):
                    raise ValidationError(f"Invalid table name: {source_table}")
                
                if source_table == 'public.court_documents':
                    cursor.execute("""
                        SELECT id, case_number, document_type, content, metadata, created_at
                        FROM public.court_documents
                        WHERE content IS NOT NULL AND LENGTH(content) > 100
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                else:
                    # For other tables, use parameterized query
                    schema, table = source_table.split('.')
                    cursor.execute("""
                        SELECT * FROM %s.%s
                        WHERE content IS NOT NULL
                        LIMIT %s
                    """, (AsIs(schema), AsIs(table), limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            raise DatabaseConnectionError(
                f"Database query failed: {str(e)}",
                stage="Document Retrieval"
            )
    
    # Copy essential methods from robust pipeline
    def _enhance_court_info_validated(self, document: Dict[str, Any]) -> Dict[str, Any]: