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
                self.db_conn.close()