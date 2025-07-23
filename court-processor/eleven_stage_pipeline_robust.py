#!/usr/bin/env python3
"""
Eleven Stage Pipeline - Robust Version with Full Error Handling and Validation

This version includes:
- Custom exception hierarchy
- Comprehensive validation
- Detailed error reporting
- No hardcoded defaults
- Honest functionality
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

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RobustElevenStagePipeline:
    """Eleven stage document processing pipeline with robust error handling"""
    
    def __init__(self):
        """Initialize pipeline with error tracking"""
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
        
        self.error_collector = None
    
    async def process_batch(self, 
                          limit: int = 10,
                          source_table: str = 'public.court_documents',
                          validate_strict: bool = True) -> Dict[str, Any]:
        """
        Process a batch of documents through all 11 stages with full error handling
        
        Args:
            limit: Number of documents to process
            source_table: Table to fetch documents from
            validate_strict: If True, skip documents with validation errors
        
        Returns:
            Comprehensive results including errors and validation reports
        """
        start_time = datetime.now()
        run_id = f"run_{start_time.isoformat()}"
        self.error_collector = ErrorCollector(run_id)
        stages_completed = []
        
        try:
            # ==========================================
            # STAGE 1: Document Retrieval with Validation
            # ==========================================
            logger.info("=" * 60)
            logger.info("STAGE 1: Document Retrieval")
            logger.info("=" * 60)
            
            try:
                documents = self._fetch_documents(limit, source_table)
                stages_completed.append("Document Retrieval")
                self.stats['documents_processed'] = len(documents)
                logger.info(f"✅ Retrieved {len(documents)} documents from {source_table}")
            except Exception as e:
                raise DocumentRetrievalError(
                    f"Failed to retrieve documents: {str(e)}",
                    stage="Document Retrieval",
                    details={'source_table': source_table, 'limit': limit}
                )
            
            if not documents:
                return {
                    'success': True,
                    'message': 'No documents found to process',
                    'stages_completed': stages_completed,
                    'statistics': self.stats,
                    'error_report': self.error_collector.get_summary()
                }
            
            # Validate retrieved documents
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
                        
                # Log warnings
                for warning in validation_result.warnings:
                    self.error_collector.add_warning(
                        warning,
                        stage="Document Validation",
                        document_id=doc.get('id')
                    )
            
            # Process each document through remaining stages
            enhanced_documents = []
            
            for idx, doc in enumerate(valid_documents):
                doc_id = doc.get('id', f'unknown_{idx}')
                logger.info(f"\nProcessing document {idx + 1}/{len(valid_documents)}: {doc_id}")
                
                try:
                    # Process through each enhancement stage
                    enhanced_doc = await self._process_single_document(doc, idx)
                    enhanced_documents.append(enhanced_doc)
                except PipelineError as e:
                    # Pipeline errors are expected and handled
                    self.error_collector.add_error(e, e.stage or "Unknown", doc_id)
                    self.stats['total_errors'] += 1
                    logger.error(f"Pipeline error for document {doc_id}: {e}")
                    # Continue with next document
                    continue
                except Exception as e:
                    # Unexpected errors
                    self.error_collector.add_error(
                        e, "Document Processing", doc_id,
                        context={'unexpected': True}
                    )
                    self.stats['total_errors'] += 1
                    logger.error(f"Unexpected error for document {doc_id}: {e}", exc_info=True)
                    continue
            
            # Complete remaining stages with enhanced documents
            stages_completed.extend([
                "Court Resolution",
                "Citation Extraction",
                "Reporter Normalization",
                "Judge Enhancement",
                "Document Structure",
                "Keyword Extraction",
                "Metadata Assembly"
            ])
            
            # ==========================================
            # STAGE 9: Enhanced Storage with Validation
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 9: Enhanced Storage to PostgreSQL")
            logger.info("=" * 60)
            
            storage_results = await self._store_enhanced_documents_validated(enhanced_documents)
            stages_completed.append("Enhanced Storage")
            self.stats['documents_stored'] = storage_results.get('total_processed', 0)
            
            # ==========================================
            # STAGE 10: Haystack Integration
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 10: Haystack Integration")
            logger.info("=" * 60)
            
            haystack_results = await self._index_to_haystack_validated(enhanced_documents)
            stages_completed.append("Haystack Integration")
            self.stats['documents_indexed'] = haystack_results.get('indexed_count', 0)
            
            # ==========================================
            # STAGE 11: Pipeline Verification
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 11: Pipeline Verification")
            logger.info("=" * 60)
            
            verification = self._verify_pipeline_results_validated(enhanced_documents)
            stages_completed.append("Pipeline Verification")
            
            # Calculate final metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            # Log error summary
            self.error_collector.log_summary(logger)
            
            return {
                'success': True,
                'run_id': run_id,
                'stages_completed': stages_completed,
                'statistics': self.stats,
                'processing_time_seconds': processing_time,
                'verification': verification,
                'storage_results': storage_results,
                'haystack_results': haystack_results,
                'error_report': self.error_collector.get_detailed_report(),
                'quality_metrics': self._calculate_quality_metrics()
            }
            
        except PipelineError as e:
            # Known pipeline errors
            self.error_collector.add_error(e, e.stage or "Pipeline", None)
            logger.error(f"Pipeline failed: {e}")
            return {
                'success': False,
                'run_id': run_id,
                'error': str(e),
                'error_type': type(e).__name__,
                'stages_completed': stages_completed,
                'partial_stats': self.stats,
                'error_report': self.error_collector.get_detailed_report()
            }
        except Exception as e:
            # Unexpected errors
            self.error_collector.add_error(e, "Pipeline", None, {'unexpected': True})
            logger.error(f"Unexpected pipeline error: {e}", exc_info=True)
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
    
    async def _process_single_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process a single document through enhancement stages"""
        doc_id = doc.get('id')
        
        # ==========================================
        # STAGE 2: Court Resolution Enhancement
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 2: Court Resolution Enhancement")
            logger.info("=" * 60)
        
        try:
            court_info = self._enhance_court_info_validated(doc)
            doc['court_enhancement'] = court_info
            
            if court_info.get('resolved'):
                self.stats['courts_resolved'] += 1
            else:
                self.stats['courts_unresolved'] += 1
                
        except Exception as e:
            raise CourtResolutionError(
                f"Court resolution failed: {str(e)}",
                stage="Court Resolution",
                document_id=doc_id
            )
        
        # ==========================================
        # STAGE 3: Citation Extraction and Analysis
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 3: Citation Extraction and Analysis")
            logger.info("=" * 60)
        
        try:
            citations_data = self._extract_citations_validated(doc)
            doc['citations_extracted'] = citations_data
            self.stats['citations_extracted'] += citations_data.get('count', 0)
            self.stats['citations_validated'] += citations_data.get('valid_count', 0)
        except Exception as e:
            raise CitationExtractionError(
                f"Citation extraction failed: {str(e)}",
                stage="Citation Extraction",
                document_id=doc_id
            )
        
        # ==========================================
        # STAGE 4: Reporter Normalization
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 4: Reporter Normalization")
            logger.info("=" * 60)
        
        try:
            if doc['citations_extracted']['count'] > 0:
                reporters_data = self._normalize_reporters_validated(
                    doc['citations_extracted']['citations']
                )
                doc['reporters_normalized'] = reporters_data
                self.stats['reporters_normalized'] += reporters_data.get('normalized_count', 0)
            else:
                doc['reporters_normalized'] = {'count': 0, 'normalized_reporters': []}
        except Exception as e:
            raise ReporterNormalizationError(
                f"Reporter normalization failed: {str(e)}",
                stage="Reporter Normalization",
                document_id=doc_id
            )
        
        # ==========================================
        # STAGE 5: Judge Information Enhancement
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 5: Judge Information Enhancement")
            logger.info("=" * 60)
        
        try:
            judge_info = self._enhance_judge_info_validated(doc)
            doc['judge_enhancement'] = judge_info
            
            if judge_info.get('enhanced'):
                self.stats['judges_enhanced'] += 1
            if judge_info.get('extracted_from_content'):
                self.stats['judges_extracted_from_content'] += 1
        except Exception as e:
            raise JudgeEnhancementError(
                f"Judge enhancement failed: {str(e)}",
                stage="Judge Enhancement",
                document_id=doc_id
            )
        
        # ==========================================
        # STAGE 6: Document Structure Analysis
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 6: Document Structure Analysis")
            logger.info("=" * 60)
        
        structure = self._analyze_structure(doc)
        doc['structure_analysis'] = structure
        
        # ==========================================
        # STAGE 7: Legal Keyword Extraction
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 7: Legal Keyword Extraction")
            logger.info("=" * 60)
        
        keyword_extraction = self._extract_legal_keywords(doc)
        doc['keyword_extraction'] = keyword_extraction
        self.stats['keywords_extracted'] += len(keyword_extraction.get('keywords', []))
        
        # ==========================================
        # STAGE 8: Comprehensive Metadata Assembly
        # ==========================================
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 8: Comprehensive Metadata Assembly")
            logger.info("=" * 60)
        
        metadata = self._assemble_metadata_validated(doc)
        doc['comprehensive_metadata'] = metadata
        
        return doc

# Continue in next part...