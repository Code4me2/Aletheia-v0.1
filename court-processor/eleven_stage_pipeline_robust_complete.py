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
    
    def _enhance_court_info_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Court resolution with validation"""
        metadata = document.get('metadata', {})
        
        # Handle metadata that might be a string (JSON) or other type
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                self.error_collector.add_warning(
                    "Failed to parse metadata JSON",
                    stage="Court Resolution",
                    document_id=document.get('id')
                )
                metadata = {}
        elif not isinstance(metadata, dict):
            self.error_collector.add_warning(
                f"Unexpected metadata type: {type(metadata).__name__}",
                stage="Court Resolution",
                document_id=document.get('id')
            )
            metadata = {}
        
        # Try to find court information
        court_hint = None
        extracted_from_content = False
        
        # Check metadata fields
        court_hint = metadata.get('court') or metadata.get('court_id')
        
        # Try to extract from case number
        if not court_hint:
            case_number = document.get('case_number', '')
            if case_number:
                # Extract court from case number patterns
                if ':' in case_number:
                    parts = case_number.split(':')
                    if len(parts[0]) <= 10:  # Reasonable court ID length
                        potential_court = parts[0].split('-')[0].lower()
                        if len(potential_court) >= 2:
                            court_hint = potential_court
                            extracted_from_content = True
        
        if not court_hint:
            # No court found - return unresolved status
            logger.warning(f"Could not determine court for document {document.get('id')}")
            return {
                'resolved': False,
                'reason': 'No court information found in metadata or content',
                'attempted_extraction': True,
                'search_locations': ['metadata.court', 'metadata.court_id', 'case_number pattern']
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
                'extracted_from_content': extracted_from_content,
                'validation': court_validation.to_dict()
            }
        else:
            # Invalid court ID
            for error in court_validation.errors:
                self.error_collector.add_error(
                    ValidationError(error),
                    stage="Court Resolution",
                    document_id=document.get('id')
                )
            
            return {
                'resolved': False,
                'attempted_court_id': court_hint,
                'reason': 'Court ID validation failed',
                'validation_errors': court_validation.errors,
                'validation_warnings': court_validation.warnings
            }
    
    def _extract_citations_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Citation extraction with validation"""
        content = document.get('content', '')
        
        if not content:
            return {
                'count': 0,
                'valid_count': 0,
                'citations': [],
                'validation_summary': {'errors': 0, 'warnings': 0}
            }
        
        # Extract citations using eyecite
        citations = get_citations(content)
        
        citation_data = []
        valid_count = 0
        total_errors = 0
        total_warnings = 0
        
        for cite in citations:
            citation_dict = {
                'text': str(cite),
                'type': type(cite).__name__,
                'groups': cite.groups if hasattr(cite, 'groups') else {}
            }
            
            # Add metadata if available
            if hasattr(cite, 'metadata'):
                citation_dict['metadata'] = {
                    'plaintiff': getattr(cite.metadata, 'plaintiff', None),
                    'defendant': getattr(cite.metadata, 'defendant', None),
                    'year': getattr(cite.metadata, 'year', None),
                    'court': getattr(cite.metadata, 'court', None),
                }
            
            # Extract key citation parts
            if hasattr(cite, 'groups'):
                citation_dict.update({
                    'volume': cite.groups.get('volume'),
                    'reporter': cite.groups.get('reporter'),
                    'page': cite.groups.get('page')
                })
            
            # Validate citation
            validation_result = CitationValidator.validate_citation(citation_dict)
            citation_dict['validation'] = validation_result.to_dict()
            
            if validation_result.is_valid:
                valid_count += 1
            
            total_errors += len(validation_result.errors)
            total_warnings += len(validation_result.warnings)
            
            citation_data.append(citation_dict)
        
        logger.info(f"Extracted {len(citations)} citations, {valid_count} valid")
        
        return {
            'count': len(citations),
            'valid_count': valid_count,
            'citations': citation_data,
            'validation_summary': {
                'errors': total_errors,
                'warnings': total_warnings
            }
        }
    
    def _normalize_reporters_validated(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 4: Reporter normalization with validation"""
        normalized_reporters = []
        unique_reporters = set()
        normalized_count = 0
        
        for citation in citations:
            reporter = citation.get('reporter')
            if not reporter:
                continue
            
            # Get reporter info
            reporter_info = self._get_reporter_info(reporter)
            
            normalization = {
                'original': reporter,
                'edition': reporter_info.get('edition', reporter),
                'found': reporter_info.get('found', False),
                'name': reporter_info.get('name', ''),
                'cite_type': reporter_info.get('cite_type', '')
            }
            
            # Track if this was actually normalized (changed)
            if normalization['edition'] != normalization['original']:
                normalized_count += 1
            
            normalized_reporters.append(normalization)
            unique_reporters.add(normalization['edition'])
        
        # Validate normalization results
        validation_result = ReporterValidator.validate_reporter_normalization({
            'normalized_reporters': normalized_reporters
        })
        
        return {
            'count': len(unique_reporters),
            'normalized_count': normalized_count,
            'unique_reporters': list(unique_reporters),
            'normalized_reporters': normalized_reporters,
            'validation': validation_result.to_dict()
        }
    
    def _get_reporter_info(self, reporter: str) -> Dict[str, Any]:
        """Get reporter information with proper handling of editions"""
        # This is the fixed version from our earlier work
        reporter_clean = reporter.strip()
        
        # Handle Federal Reporter series (F., F.2d, F.3d, etc.)
        if reporter_clean.lower().startswith('f.'):
            base_key = 'F.'
            if base_key in REPORTERS:
                reporter_data = REPORTERS[base_key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    
                    # Determine edition
                    if '3d' in reporter_clean:
                        edition = 'F.3d'
                    elif '2d' in reporter_clean:
                        edition = 'F.2d'
                    elif '4th' in reporter_clean:
                        edition = 'F.4th'
                    else:
                        edition = 'F.'
                    
                    return {
                        'found': True,
                        'base_reporter': base_key,
                        'edition': edition,
                        'name': base_info.get('name', 'Federal Reporter'),
                        'cite_type': base_info.get('cite_type', 'federal')
                    }
        
        # Handle Federal Supplement
        if 'supp' in reporter_clean.lower():
            base_key = 'F. Supp.'
            if '3d' in reporter_clean.lower():
                edition = 'F. Supp. 3d'
            elif '2d' in reporter_clean.lower():
                edition = 'F. Supp. 2d'
            else:
                edition = 'F. Supp.'
            
            if base_key in REPORTERS:
                reporter_data = REPORTERS[base_key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    return {
                        'found': True,
                        'base_reporter': base_key,
                        'edition': edition,
                        'name': base_info.get('name', 'Federal Supplement'),
                        'cite_type': base_info.get('cite_type', 'federal')
                    }
        
        # Direct lookup for other reporters
        if reporter_clean in REPORTERS:
            reporter_data = REPORTERS[reporter_clean]
            if isinstance(reporter_data, list) and reporter_data:
                base_info = reporter_data[0]
                return {
                    'found': True,
                    'base_reporter': reporter_clean,
                    'edition': reporter_clean,
                    'name': base_info.get('name', ''),
                    'cite_type': base_info.get('cite_type', '')
                }
        
        # Case-insensitive lookup
        for key in REPORTERS.keys():
            if reporter_clean.lower() == key.lower():
                reporter_data = REPORTERS[key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    return {
                        'found': True,
                        'base_reporter': key,
                        'edition': key,
                        'name': base_info.get('name', ''),
                        'cite_type': base_info.get('cite_type', '')
                    }
        
        return {
            'found': False,
            'base_reporter': reporter_clean,
            'edition': reporter_clean,
            'name': '',
            'cite_type': ''
        }

    def _enhance_judge_info_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 5: Judge enhancement with validation"""
        metadata = document.get('metadata', {})
        
        # Handle metadata safely
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif not isinstance(metadata, dict):
            metadata = {}
        
        # Try metadata first
        judge_name = metadata.get('judge_name', '') or metadata.get('judge', '') or metadata.get('assigned_to', '')
        judge_initials = metadata.get('federal_dn_judge_initials_assigned', '')
        extracted_from_content = False
        
        # If no judge name but we have initials
        if not judge_name and judge_initials:
            return {
                'enhanced': False,
                'reason': 'Only initials available',
                'judge_initials': judge_initials,
                'judge_name_found': f"Judge {judge_initials}",
                'extracted_from_content': False
            }
        
        # If no judge in metadata, try to extract from content
        if not judge_name:
            judge_name = self._extract_judge_from_content_optimized(document.get('content', ''))
            if judge_name:
                extracted_from_content = True
        
        if not judge_name:
            return {'enhanced': False, 'reason': 'No judge name found'}
        
        # Validate judge name
        name_validation = JudgeValidator.validate_judge_name(judge_name)
        
        if not name_validation.is_valid:
            for error in name_validation.errors:
                self.error_collector.add_error(
                    ValidationError(error),
                    stage="Judge Enhancement",
                    document_id=document.get('id')
                )
            return {
                'enhanced': False,
                'reason': 'Judge name validation failed',
                'attempted_name': judge_name,
                'validation_errors': name_validation.errors
            }
        
        # Use validated/cleaned name
        judge_name = name_validation.cleaned_data
        
        try:
            # Load judge data
            judge_data_path = os.path.join(judge_pics.judge_root, 'people.json')
            
            if os.path.exists(judge_data_path):
                with open(judge_data_path, 'r') as f:
                    judges_data = json.load(f)
                
                # Search for judge
                judge_lower = judge_name.lower()
                for judge_data_item in judges_data:
                    if not isinstance(judge_data_item, dict):
                        continue
                    
                    # Handle person field which might be an ID (int) or dict
                    person_field = judge_data_item.get('person')
                    if isinstance(person_field, dict):
                        person_info = person_field
                        person_name = person_info.get('name_full', '')
                    else:
                        # Person is likely an ID, skip
                        continue
                    
                    if judge_lower in person_name.lower() or person_name.lower() in judge_lower:
                        return {
                            'enhanced': True,
                            'judge_id': person_info.get('id'),
                            'full_name': person_name,
                            'slug': person_info.get('slug'),
                            'photo_path': judge_data_item.get('path'),
                            'photo_available': True,
                            'source': 'judge-pics',
                            'extracted_from_content': extracted_from_content,
                            'validation': name_validation.to_dict()
                        }
                
                # Not found in database but name is valid
                return {
                    'enhanced': False,
                    'reason': 'Judge not found in database',
                    'attempted_name': judge_name,
                    'extracted_from_content': extracted_from_content,
                    'judge_name_found': judge_name,
                    'validation': name_validation.to_dict()
                }
            else:
                return {'enhanced': False, 'reason': 'Judge database not available'}
                
        except Exception as e:
            self.error_collector.add_error(
                e,
                stage="Judge Enhancement",
                document_id=document.get('id')
            )
            return {'enhanced': False, 'error': str(e)}
    
    def _extract_judge_from_content_optimized(self, content: str) -> Optional[str]:
        """Extract judge name from document content"""
        if not content:
            return None
        
        # Extended judge patterns
        patterns = [
            r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'Before:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'JUDGE:\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'Signed\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][A-Z\s]+),?\s+UNITED STATES DISTRICT JUDGE'
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
                logger.info(f"  Extracted judge from content start: {judge_name}")
                return judge_name
            
            # Check end
            match = re.search(pattern, content_end)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                logger.info(f"  Extracted judge from content end: {judge_name}")
                return judge_name
        
        return None
    
    def _analyze_structure(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 6: Document structure analysis"""
        content = document.get('content', '')
        
        structure = {
            'elements': [],
            'sections': 0,
            'paragraphs': 0,
            'has_footnotes': False,
            'has_citations': False
        }
        
        if not content:
            return structure
        
        # Count paragraphs (double newline separated)
        paragraphs = re.split(r'\n\s*\n', content)
        structure['paragraphs'] = len([p for p in paragraphs if p.strip()])
        
        # Look for section markers
        section_patterns = [
            r'^[IVX]+\.\s+[A-Z]',  # Roman numerals
            r'^\d+\.\s+[A-Z]',      # Numbered sections
            r'^[A-Z]\.\s+[A-Z]',    # Letter sections
        ]
        
        for para in paragraphs:
            for pattern in section_patterns:
                if re.match(pattern, para.strip()):
                    structure['sections'] += 1
                    structure['elements'].append('section')
                    break
        
        # Check for footnotes
        if re.search(r'\[\d+\]|\(\d+\)|\*\d+', content):
            structure['has_footnotes'] = True
            structure['elements'].append('footnotes')
        
        # Check for citations
        if re.search(r'\d+\s+[A-Z]\.\s*\d+[a-z]?\s+\d+', content):
            structure['has_citations'] = True
            structure['elements'].append('citations')
        
        return structure
    
    def _extract_legal_keywords(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 7: Extract legal keywords (honest about limitations)"""
        content = document.get('content', '')
        doc_type = document.get('document_type', 'unknown')
        
        extraction_result = {
            'method': 'simple_keyword_matching',
            'document_type': doc_type,
            'keywords': [],
            'legal_terms': [],
            'procedural_terms': [],
            'disclaimer': 'This is basic keyword extraction, not legal analysis'
        }
        
        if not content:
            logger.debug("No content for keyword extraction")
            return extraction_result
        
        content_lower = content.lower()
        
        # Legal keywords
        legal_keywords = [
            'summary judgment', 'motion to dismiss', 'claim construction',
            'patent infringement', 'preliminary injunction', 'class action',
            'jurisdiction', 'standing', 'damages', 'liability', 'negligence',
            'breach of contract', 'due process', 'equal protection'
        ]
        
        for keyword in legal_keywords:
            if keyword in content_lower:
                extraction_result['keywords'].append(keyword)
        
        # Legal standards
        legal_standards = {
            'de novo': 'de novo review',
            'abuse of discretion': 'abuse of discretion',
            'clear error': 'clear error',
            'arbitrary and capricious': 'arbitrary and capricious',
            'rational basis': 'rational basis review',
            'strict scrutiny': 'strict scrutiny'
        }
        
        for search_term, standard_name in legal_standards.items():
            if search_term in content_lower:
                extraction_result['legal_terms'].append(standard_name)
        
        # Procedural terms
        procedural_patterns = {
            'granted': 'motion granted',
            'denied': 'motion denied',
            'reversed': 'reversed',
            'affirmed': 'affirmed',
            'remanded': 'remanded',
            'dismissed': 'dismissed',
            'sustained': 'objection sustained',
            'overruled': 'objection overruled'
        }
        
        for term, description in procedural_patterns.items():
            if term in content_lower:
                extraction_result['procedural_terms'].append(description)
        
        # Remove duplicates
        extraction_result['keywords'] = list(set(extraction_result['keywords']))
        extraction_result['legal_terms'] = list(set(extraction_result['legal_terms']))
        extraction_result['procedural_terms'] = list(set(extraction_result['procedural_terms']))
        
        total_keywords = (
            len(extraction_result['keywords']) + 
            len(extraction_result['legal_terms']) + 
            len(extraction_result['procedural_terms'])
        )
        
        logger.info(f"Extracted {total_keywords} keywords from document")
        
        return extraction_result
    
    def _assemble_metadata_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 8: Assemble comprehensive metadata with validation"""
        
        def clean_for_json(obj):
            """Remove non-serializable objects"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items() if not callable(v)}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        # Start with original metadata
        original_metadata = document.get('metadata', {})
        if isinstance(original_metadata, str):
            try:
                original_metadata = json.loads(original_metadata)
            except:
                original_metadata = {}
        
        # Assemble all enhancements
        comprehensive = {
            'original_metadata': clean_for_json(original_metadata),
            'document_id': document.get('id'),
            'case_number': document.get('case_number'),
            'document_type': document.get('document_type'),
            'processing_timestamp': datetime.now().isoformat(),
            'enhancements': {
                'court': clean_for_json(document.get('court_enhancement', {})),
                'citations': clean_for_json(document.get('citations_extracted', {})),
                'reporters': clean_for_json(document.get('reporters_normalized', {})),
                'judge': clean_for_json(document.get('judge_enhancement', {})),
                'structure': clean_for_json(document.get('structure_analysis', {})),
                'keywords': clean_for_json(document.get('keyword_extraction', {}))
            },
            'quality_indicators': {
                'court_resolved': document.get('court_enhancement', {}).get('resolved', False),
                'citations_found': document.get('citations_extracted', {}).get('count', 0) > 0,
                'judge_identified': bool(
                    document.get('judge_enhancement', {}).get('enhanced') or
                    document.get('judge_enhancement', {}).get('judge_name_found')
                ),
                'keywords_extracted': len(document.get('keyword_extraction', {}).get('keywords', [])) > 0
            }
        }
        
        # Run final validation
        validation_result = PipelineValidator.validate_processing_result(document)
        comprehensive['validation_summary'] = validation_result.to_dict()
        
        return comprehensive
    
    async def _store_enhanced_documents_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 9: Enhanced storage with validation and comprehensive error handling"""
        stored_count = 0
        updated_count = 0
        skipped_count = 0
        validation_failures = 0
        errors = []
        
        try:
            with self.db_conn.cursor() as cursor:
                for doc in documents:
                    doc_id = doc.get('id')
                    
                    try:
                        # Validate document before storage
                        validation_result = PipelineValidator.validate_processing_result(doc)
                        
                        if not validation_result.is_valid and len(validation_result.errors) > 0:
                            validation_failures += 1
                            self.error_collector.add_validation_failure(
                                validation_result.to_dict(),
                                stage="Storage Validation",
                                document_id=doc_id
                            )
                            logger.warning(f"Document {doc_id} has validation errors, storing anyway")
                        
                        # Generate hash based on content
                        content_sample = str(doc.get('content', ''))[:1000]
                        doc_hash = hashlib.sha256(
                            f"{doc_id}_{doc.get('case_number', '')}_{content_sample}".encode()
                        ).hexdigest()
                        
                        # Make data JSON serializable
                        def make_serializable(obj):
                            if isinstance(obj, dict):
                                return {k: make_serializable(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [make_serializable(item) for item in obj]
                            elif hasattr(obj, '__dict__'):
                                return str(obj)
                            elif callable(obj):
                                return None
                            else:
                                return obj
                        
                        # Extract values with validation
                        metadata = doc.get('metadata', {})
                        if not isinstance(metadata, dict):
                            metadata = {}
                        
                        court_enhancement = doc.get('court_enhancement', {})
                        court_id = court_enhancement.get('court_id') if court_enhancement.get('resolved') else None
                        case_name = metadata.get('case_name', doc.get('case_number', f'Document-{doc_id}'))
                        
                        # Check if document exists
                        cursor.execute("""
                            SELECT id, document_hash FROM court_data.opinions_unified 
                            WHERE cl_id = %s
                        """, (doc_id,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            existing_id, existing_hash = existing
                            
                            if existing_hash != doc_hash:
                                # Update existing record
                                cursor.execute("""
                                    UPDATE court_data.opinions_unified SET
                                        court_id = %s,
                                        case_name = %s,
                                        plain_text = %s,
                                        citations = %s,
                                        judge_info = %s,
                                        court_info = %s,
                                        structured_elements = %s,
                                        document_hash = %s,
                                        flp_processing_timestamp = %s,
                                        updated_at = %s
                                    WHERE cl_id = %s
                                """, (
                                    court_id,
                                    case_name,
                                    doc.get('content'),
                                    json.dumps(make_serializable(doc.get('citations_extracted', {}))),
                                    json.dumps(make_serializable(doc.get('judge_enhancement', {}))),
                                    json.dumps(make_serializable(doc.get('court_enhancement', {}))),
                                    json.dumps(make_serializable(doc.get('comprehensive_metadata', {}))),
                                    doc_hash,
                                    datetime.now(),
                                    datetime.now(),
                                    doc_id
                                ))
                                updated_count += 1
                                logger.info(f"Updated existing record for cl_id: {doc_id}")
                            else:
                                skipped_count += 1
                                logger.debug(f"Skipped unchanged document cl_id: {doc_id}")
                        else:
                            # Insert new record
                            cursor.execute("""
                                INSERT INTO court_data.opinions_unified (
                                    cl_id, court_id, case_name, plain_text,
                                    citations, judge_info, court_info,
                                    structured_elements, document_hash,
                                    flp_processing_timestamp, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                doc_id,
                                court_id,
                                case_name,
                                doc.get('content'),
                                json.dumps(make_serializable(doc.get('citations_extracted', {}))),
                                json.dumps(make_serializable(doc.get('judge_enhancement', {}))),
                                json.dumps(make_serializable(doc.get('court_enhancement', {}))),
                                json.dumps(make_serializable(doc.get('comprehensive_metadata', {}))),
                                doc_hash,
                                datetime.now(),
                                datetime.now()
                            ))
                            stored_count += 1
                            logger.info(f"Stored new document cl_id: {doc_id}")
                            
                    except psycopg2.IntegrityError as e:
                        if 'duplicate key value violates unique constraint' in str(e):
                            self.error_collector.add_error(
                                DuplicateDocumentError(
                                    f"Document {doc_id} already exists",
                                    document_id=doc_id
                                ),
                                stage="Storage",
                                document_id=doc_id
                            )
                            skipped_count += 1
                        else:
                            raise
                    except ValidationError as e:
                        self.error_collector.add_error(e, "Storage", doc_id)
                        errors.append(f"Validation error for {doc_id}: {str(e)}")
                    except Exception as e:
                        error_msg = f"Error storing document {doc_id}: {str(e)}"
                        logger.error(error_msg)
                        self.error_collector.add_error(
                            StorageError(error_msg, document_id=doc_id),
                            stage="Storage",
                            document_id=doc_id
                        )
                        errors.append(error_msg)
                        continue
                
                self.db_conn.commit()
                
                total_processed = stored_count + updated_count + skipped_count
                logger.info(f"✅ Storage complete: {stored_count} new, {updated_count} updated, {skipped_count} unchanged")
                
                if validation_failures > 0:
                    logger.warning(f"⚠️  {validation_failures} documents had validation issues")
                
                if errors:
                    logger.warning(f"⚠️  {len(errors)} documents failed to store")
                    
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Storage transaction failed: {e}")
            raise StorageError(
                f"Storage transaction failed: {str(e)}",
                stage="Storage"
            )
        
        return {
            'success': True,
            'stored_count': stored_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'validation_failures': validation_failures,
            'total_processed': stored_count + updated_count + skipped_count,
            'errors': errors
        }
    
    async def _index_to_haystack_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 10: Index to Haystack with validation"""
        try:
            haystack_docs = []
            
            for doc in documents:
                # Validate document has minimum required fields
                if not doc.get('content'):
                    self.error_collector.add_warning(
                        f"Document {doc.get('id')} has no content, skipping Haystack indexing",
                        stage="Haystack Integration",
                        document_id=doc.get('id')
                    )
                    continue
                
                # Create clean metadata
                clean_metadata = {
                    'id': str(doc.get('id')),
                    'case_number': doc.get('case_number'),
                    'document_type': doc.get('document_type'),
                    'court_id': doc.get('court_enhancement', {}).get('court_id'),
                    'court_name': doc.get('court_enhancement', {}).get('court_name'),
                    'court_resolved': doc.get('court_enhancement', {}).get('resolved', False),
                    'judge_name': doc.get('judge_enhancement', {}).get('full_name', 
                                        doc.get('judge_enhancement', {}).get('judge_name_found', '')),
                    'citation_count': doc.get('citations_extracted', {}).get('count', 0),
                    'keywords': doc.get('keyword_extraction', {}).get('keywords', []),
                    'processing_timestamp': datetime.now().isoformat(),
                    'validation_passed': doc.get('comprehensive_metadata', {}).get(
                        'validation_summary', {}
                    ).get('is_valid', False)
                }
                
                haystack_doc = {
                    'content': doc.get('content', ''),
                    'meta': clean_metadata
                }
                haystack_docs.append(haystack_doc)
            
            if not haystack_docs:
                return {
                    'success': True,
                    'indexed_count': 0,
                    'message': 'No documents to index'
                }
            
            # Send to Haystack
            async with aiohttp.ClientSession() as session:
                url = f"{SERVICES['haystack']['url']}/ingest"
                
                try:
                    async with session.post(
                        url,
                        json=haystack_docs,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"✅ Indexed {len(haystack_docs)} documents to Haystack")
                            return {
                                'success': True,
                                'indexed_count': len(haystack_docs),
                                'response': result
                            }
                        else:
                            error_text = await response.text()
                            raise HaystackError(
                                f"Haystack returned {response.status}: {error_text}",
                                stage="Haystack Integration"
                            )
                except asyncio.TimeoutError:
                    raise HaystackError(
                        "Haystack request timed out after 30 seconds",
                        stage="Haystack Integration"
                    )
                except Exception as e:
                    raise HaystackError(
                        f"Haystack integration failed: {str(e)}",
                        stage="Haystack Integration"
                    )
                    
        except HaystackError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                f"Unexpected error in Haystack integration: {str(e)}",
                stage="Haystack Integration"
            )
    
    def _verify_pipeline_results_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 11: Comprehensive pipeline verification"""
        verification = {
            'documents_with_court_resolution': 0,
            'documents_with_valid_court': 0,
            'documents_with_citations': 0,
            'documents_with_valid_citations': 0,
            'documents_with_normalized_reporters': 0,
            'documents_with_judge_info': 0,
            'documents_with_valid_judge': 0,
            'documents_with_structure': 0,
            'documents_with_keywords': 0,
            'documents_fully_valid': 0,
            'average_enhancements_per_doc': 0,
            'completeness_score': 0,
            'quality_score': 0,
            'extraction_improvements': {
                'courts_from_content': 0,
                'judges_from_content': 0
            }
        }
        
        total_enhancements = 0
        total_quality_points = 0
        
        for doc in documents:
            doc_enhancements = 0
            doc_quality_points = 0
            
            # Court resolution
            court_data = doc.get('court_enhancement', {})
            if court_data.get('resolved'):
                verification['documents_with_court_resolution'] += 1
                doc_enhancements += 1
                
                # Check if court is valid
                if not court_data.get('validation', {}).get('errors'):
                    verification['documents_with_valid_court'] += 1
                    doc_quality_points += 2  # Higher points for valid data
                else:
                    doc_quality_points += 1
                
                if court_data.get('extracted_from_content'):
                    verification['extraction_improvements']['courts_from_content'] += 1
            
            # Citations
            citations_data = doc.get('citations_extracted', {})
            if citations_data.get('count', 0) > 0:
                verification['documents_with_citations'] += 1
                doc_enhancements += 1
                
                # Check citation validity
                if citations_data.get('valid_count', 0) > 0:
                    verification['documents_with_valid_citations'] += 1
                    valid_ratio = citations_data['valid_count'] / citations_data['count']
                    doc_quality_points += 2 * valid_ratio
                else:
                    doc_quality_points += 0.5
            
            # Normalized reporters
            if doc.get('reporters_normalized', {}).get('normalized_count', 0) > 0:
                verification['documents_with_normalized_reporters'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Judge info
            judge_data = doc.get('judge_enhancement', {})
            if judge_data.get('enhanced') or judge_data.get('judge_name_found'):
                verification['documents_with_judge_info'] += 1
                doc_enhancements += 1
                
                # Check if judge name is valid
                if not judge_data.get('validation', {}).get('errors'):
                    verification['documents_with_valid_judge'] += 1
                    doc_quality_points += 2
                else:
                    doc_quality_points += 1
                
                if judge_data.get('extracted_from_content'):
                    verification['extraction_improvements']['judges_from_content'] += 1
            
            # Structure
            if len(doc.get('structure_analysis', {}).get('elements', [])) > 0:
                verification['documents_with_structure'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Keywords
            if len(doc.get('keyword_extraction', {}).get('keywords', [])) > 0:
                verification['documents_with_keywords'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Check if document is fully valid
            validation_summary = doc.get('comprehensive_metadata', {}).get('validation_summary', {})
            if validation_summary.get('is_valid', False):
                verification['documents_fully_valid'] += 1
            
            total_enhancements += doc_enhancements
            total_quality_points += doc_quality_points
        
        # Calculate metrics
        num_docs = len(documents)
        if num_docs > 0:
            verification['average_enhancements_per_doc'] = total_enhancements / num_docs
            
            # Completeness: how many enhancements were applied
            max_enhancements = 6  # court, citations, reporters, judge, structure, keywords
            verification['completeness_score'] = (
                (verification['documents_with_court_resolution'] +
                 verification['documents_with_citations'] +
                 verification['documents_with_normalized_reporters'] +
                 verification['documents_with_judge_info'] +
                 verification['documents_with_structure'] +
                 verification['documents_with_keywords']) / 
                (num_docs * max_enhancements) * 100
            )
            
            # Quality: how good are the enhancements
            max_quality_points = 10  # Maximum quality points per document
            verification['quality_score'] = (total_quality_points / (num_docs * max_quality_points)) * 100
        
        logger.info(f"✅ Pipeline verification complete:")
        logger.info(f"   Completeness: {verification['completeness_score']:.1f}%")
        logger.info(f"   Quality: {verification['quality_score']:.1f}%")
        logger.info(f"   Valid documents: {verification['documents_fully_valid']}/{num_docs}")
        
        return verification
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate overall quality metrics for the pipeline run"""
        total_docs = self.stats['documents_processed']
        
        if total_docs == 0:
            return {}
        
        return {
            'validation_rate': (self.stats['documents_validated'] / total_docs) * 100,
            'court_resolution_rate': (self.stats['courts_resolved'] / total_docs) * 100,
            'citation_extraction_rate': (self.stats['citations_extracted'] / total_docs) * 100,
            'judge_identification_rate': (
                (self.stats['judges_enhanced'] + self.stats['judges_extracted_from_content']) / 
                total_docs
            ) * 100,
            'error_rate': (self.stats['total_errors'] / total_docs) * 100,
            'data_quality_indicators': {
                'has_validation_failures': self.stats['validation_failures'] > 0,
                'has_unresolved_courts': self.stats['courts_unresolved'] > 0,
                'has_errors': self.stats['total_errors'] > 0,
                'has_warnings': self.stats['total_warnings'] > 0
            }
        }
    
    def _calculate_complexity_score(self) -> float:
        """Calculate pipeline complexity score"""
        # This is a simple metric - could be enhanced
        return 11.0  # 11 stages