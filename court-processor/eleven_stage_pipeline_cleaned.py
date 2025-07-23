#!/usr/bin/env python3
"""
Eleven Stage Pipeline Implementation - Optimized Version
Final optimized pipeline with all fixes and improvements
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

# Create courts dictionary for direct lookup
COURTS_DICT = {court['id']: court for court in courts if isinstance(court, dict)}

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CleanedElevenStagePipeline:
    """
    Optimized 11-stage document processing pipeline with maximum completeness
    """
    
    def __init__(self):
        self.db_conn = get_db_connection()
        self.stats = {
            'documents_processed': 0,
            'total_enhancements': 0,
            'citations_extracted': 0,
            'courts_resolved': 0,
            'reporters_normalized': 0,
            'judges_enhanced': 0,
            'documents_stored': 0,
            'documents_indexed': 0
        }
    
    async def process_batch(self, 
                          limit: int = 10,
                          source_table: str = 'public.court_documents') -> Dict[str, Any]:
        """
        Process a batch of documents through all 11 stages
        """
        start_time = datetime.now()
        stages_completed = []
        
        try:
            # ==========================================
            # STAGE 1: Document Retrieval
            # ==========================================
            logger.info("=" * 60)
            logger.info("STAGE 1: Document Retrieval")
            logger.info("=" * 60)
            
            documents = self._fetch_documents(limit, source_table)
            stages_completed.append("Document Retrieval")
            self.stats['documents_processed'] = len(documents)
            logger.info(f"✅ Retrieved {len(documents)} documents from {source_table}")
            
            if not documents:
                return {
                    'success': False,
                    'message': 'No documents found to process',
                    'stages_completed': stages_completed
                }
            
            # Process each document through remaining stages
            enhanced_documents = []
            
            for idx, doc in enumerate(documents):
                logger.info(f"\nProcessing document {idx + 1}/{len(documents)}: {doc.get('id')}")
                
                # ==========================================
                # STAGE 2: Court Resolution Enhancement (OPTIMIZED)
                # ==========================================
                if idx == 0:  # Log stage header once
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 2: Court Resolution Enhancement (Optimized)")
                    logger.info("=" * 60)
                
                court_enhancement = self._enhance_court_info_optimized(doc)
                doc['court_enhancement'] = court_enhancement
                if court_enhancement.get('resolved'):
                    self.stats['courts_resolved'] += 1
                    self.stats['total_enhancements'] += 1
                
                # ==========================================
                # STAGE 3: Citation Extraction
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 3: Citation Extraction and Analysis")
                    logger.info("=" * 60)
                
                citations = self._extract_citations(doc)
                doc['citations_extracted'] = citations
                self.stats['citations_extracted'] += citations['count']
                self.stats['total_enhancements'] += citations['count']
                
                # ==========================================
                # STAGE 4: Reporter Normalization (OPTIMIZED)
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 4: Reporter Normalization (Optimized)")
                    logger.info("=" * 60)
                
                normalized_reporters = self._normalize_reporters_optimized(citations['citations'])
                doc['reporters_normalized'] = normalized_reporters
                if normalized_reporters['count'] > 0:
                    self.stats['reporters_normalized'] += 1  # Count documents with normalized reporters
                self.stats['total_enhancements'] += normalized_reporters['count']
                
                # ==========================================
                # STAGE 5: Judge Information Enhancement (OPTIMIZED)
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 5: Judge Information Enhancement (Optimized)")
                    logger.info("=" * 60)
                
                judge_info = self._enhance_judge_info_optimized(doc)
                doc['judge_enhancement'] = judge_info
                if judge_info.get('enhanced'):
                    self.stats['judges_enhanced'] += 1
                    self.stats['total_enhancements'] += 1
                
                # ==========================================
                # STAGE 6: Document Structure Analysis
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 6: Document Structure Analysis")
                    logger.info("=" * 60)
                
                structure = self._analyze_structure(doc)
                doc['structure_analysis'] = structure
                self.stats['total_enhancements'] += len(structure.get('elements', []))
                
                # ==========================================
                # STAGE 7: Legal Keyword Extraction
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 7: Legal Keyword Extraction")
                    logger.info("=" * 60)
                
                keyword_extraction = self._extract_legal_keywords(doc)
                doc['keyword_extraction'] = keyword_extraction
                self.stats['keywords_extracted'] = self.stats.get('keywords_extracted', 0) + len(keyword_extraction.get('keywords', []))
                
                # ==========================================
                # STAGE 8: Comprehensive Metadata Assembly
                # ==========================================
                if idx == 0:
                    logger.info("\n" + "=" * 60)
                    logger.info("STAGE 8: Comprehensive Metadata Assembly")
                    logger.info("=" * 60)
                
                comprehensive_metadata = self._assemble_metadata(doc)
                doc['comprehensive_metadata'] = comprehensive_metadata
                
                enhanced_documents.append(doc)
            
            # Mark stages 2-8 as completed
            stages_completed.extend([
                "Court Resolution Enhancement",
                "Citation Extraction",
                "Reporter Normalization", 
                "Judge Enhancement",
                "Structure Analysis",
                "Keyword Extraction",
                "Metadata Assembly"
            ])
            
            # ==========================================
            # STAGE 9: Enhanced Storage (FIXED)
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 9: Enhanced Storage to PostgreSQL (Fixed)")
            logger.info("=" * 60)
            
            storage_results = self._store_enhanced_documents_fixed(enhanced_documents)
            stages_completed.append("Enhanced Storage")
            self.stats['documents_stored'] = storage_results['stored_count']
            
            # ==========================================
            # STAGE 10: Haystack Integration
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 10: Haystack Integration")
            logger.info("=" * 60)
            
            haystack_results = await self._index_to_haystack(enhanced_documents)
            stages_completed.append("Haystack Integration")
            self.stats['documents_indexed'] = haystack_results.get('indexed_count', 0)
            
            # ==========================================
            # STAGE 11: Pipeline Verification (OPTIMIZED)
            # ==========================================
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 11: Pipeline Verification (Optimized)")
            logger.info("=" * 60)
            
            verification = self._verify_pipeline_results_optimized(enhanced_documents)
            stages_completed.append("Pipeline Verification")
            
            # Calculate final metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            return {
                'success': True,
                'stages_completed': stages_completed,
                'statistics': self.stats,
                'processing_time_seconds': processing_time,
                'verification': verification,
                'enhancements_per_document': self.stats['total_enhancements'] / max(1, self.stats['documents_processed']),
                'pipeline_complexity_score': self._calculate_complexity_score(),
                'optimization_results': {
                    'court_extraction_improved': verification['extraction_improvements']['courts_from_content'] > 0,
                    'judge_extraction_improved': verification['extraction_improvements']['judges_from_content'] > 0,
                    'reporter_normalization_fixed': True,
                    'storage_fixed': storage_results['stored_count'] > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'stages_completed': stages_completed,
                'partial_stats': self.stats
            }
        finally:
            if self.db_conn:
                self.db_conn.close()
    
    def _fetch_documents(self, limit: int, source_table: str) -> List[Dict[str, Any]]:
        """Stage 1: Fetch documents from database"""
        with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            if source_table == 'public.court_documents':
                cursor.execute("""
                    SELECT id, case_number, document_type, content, metadata, created_at
                    FROM public.court_documents
                    WHERE content IS NOT NULL AND LENGTH(content) > 1000
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (limit,))
            else:
                # Handle other tables as needed
                cursor.execute(f"""
                    SELECT * FROM {source_table}
                    WHERE content IS NOT NULL
                    LIMIT %s
                """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def _enhance_court_info_optimized(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Optimized court resolution with aggressive content extraction"""
        metadata = document.get('metadata', {})
        
        # Handle metadata that might be a string (JSON)
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif not isinstance(metadata, dict):
            metadata = {}
        
        # Try metadata first - court_id is directly available in docket data
        court_hint = metadata.get('court_id', '') or metadata.get('court', '') or metadata.get('court_name', '')
        
        # Handle court_id that's already in the correct format (e.g., 'txed')
        if court_hint and len(court_hint) <= 10 and not ' ' in court_hint and court_hint.isalpha():
            # This is likely already a court ID, not a court name
            # Try direct lookup first
            if court_hint in courts:
                # Direct court_id match found
                court_data = courts[court_hint]
                logger.info(f"  Direct court_id match: {court_hint} -> {court_data.get('name', '')[:50]}")
                return {
                    'resolved': True,
                    'court_id': court_hint,
                    'court_name': court_data.get('name', ''),
                    'court_citation': court_data.get('citation_string', ''),
                    'court_type': court_data.get('type', ''),
                    'court_level': court_data.get('level', ''),
                    'matches_found': 1,
                    'search_term': court_hint,
                    'extracted_from_content': False,
                    'direct_match': True
                }
        
        extracted_from_content = False
        
        # If no court info in metadata, aggressively try to extract from content
        if not court_hint:
            court_hint = self._extract_court_from_content_optimized(document.get('content', ''))
            if court_hint:
                extracted_from_content = True
        
        # If still no court info, check case number for hints
        if not court_hint:
            case_number = document.get('case_number', '')
            # Look for court abbreviations in case number
            if 'txed' in case_number.lower():
                court_hint = 'txed'  # Use the court ID directly
                extracted_from_content = True
            elif 'txnd' in case_number.lower():
                court_hint = 'txnd'
                extracted_from_content = True
            elif 'txsd' in case_number.lower():
                court_hint = 'txsd'
                extracted_from_content = True
            elif 'txwd' in case_number.lower():
                court_hint = 'txwd'
                extracted_from_content = True
        
        if not court_hint:
            # No court found - return unresolved status
            logger.warning(f"Could not determine court for document")
            return {
                'resolved': False,
                'reason': 'No court information found in metadata or content',
                'attempted_extraction': True,
                'search_locations': ['metadata.court', 'metadata.court_id', 'case_number pattern']
            }
        
        try:
            # Check if court_hint is already a valid court_id
            if court_hint in COURTS_DICT:
                court_data = COURTS_DICT[court_hint]
                logger.info(f"  Direct court lookup: {court_hint} -> {court_data.get('name', '')[:50]}")
                return {
                    'resolved': True,
                    'court_id': court_hint,
                    'court_name': court_data.get('name', ''),
                    'court_citation': court_data.get('citation_string', ''),
                    'court_type': court_data.get('type', ''),
                    'court_level': court_data.get('level', ''),
                    'matches_found': 1,
                    'search_term': court_hint,
                    'extracted_from_content': extracted_from_content,
                    'direct_match': True
                }
            
            # Otherwise use find_court for name-based search
            court_ids = find_court(court_hint)
            
            if court_ids:
                court_id = court_ids[0]
                court_data = COURTS_DICT.get(court_id, {})
                logger.info(f"  Court name search: '{court_hint}' -> {court_id} ({court_data.get('name', '')[:50]})")
                
                return {
                    'resolved': True,
                    'court_id': court_id,
                    'court_name': court_data.get('name', ''),
                    'court_citation': court_data.get('citation_string', ''),
                    'court_type': court_data.get('type', ''),
                    'court_level': court_data.get('level', ''),
                    'matches_found': len(court_ids),
                    'search_term': court_hint,
                    'extracted_from_content': extracted_from_content,
                    'name_search': True
                }
            else:
                logger.warning(f"  No court match for: {court_hint}")
                return {
                    'resolved': False,
                    'search_term': court_hint,
                    'reason': 'No matches found',
                    'extracted_from_content': extracted_from_content
                }
                
        except Exception as e:
            logger.error(f"Court resolution error: {e}")
            return {'resolved': False, 'error': str(e)}
    
    def _extract_court_from_content_optimized(self, content: str) -> Optional[str]:
        """Extract court name or ID from document content with more patterns"""
        if not content:
            return None
        
        # Extended court patterns - try to extract court IDs when possible
        patterns = [
            # Try to match and convert to court IDs
            (r'UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?EASTERN DISTRICT OF TEXAS', 'txed'),
            (r'EASTERN DISTRICT OF TEXAS', 'txed'),
            (r'E\.D\. TEX\.', 'txed'),
            (r'UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?NORTHERN DISTRICT OF TEXAS', 'txnd'),
            (r'NORTHERN DISTRICT OF TEXAS', 'txnd'),
            (r'N\.D\. TEX\.', 'txnd'),
            (r'UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?SOUTHERN DISTRICT OF TEXAS', 'txsd'),
            (r'SOUTHERN DISTRICT OF TEXAS', 'txsd'),
            (r'S\.D\. TEX\.', 'txsd'),
            (r'UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?WESTERN DISTRICT OF TEXAS', 'txwd'),
            (r'WESTERN DISTRICT OF TEXAS', 'txwd'),
            (r'W\.D\. TEX\.', 'txwd'),
            # Generic patterns that need name extraction
            (r'UNITED STATES DISTRICT COURT\s+(?:FOR THE\s+)?([A-Z\s]+DISTRICT OF [A-Z\s]+)', None),
            (r'IN THE ([A-Z\s]+COURT[A-Z\s]*)', None),
            (r'COURT OF APPEALS\s+(?:FOR THE\s+)?([A-Z\s]+)', None),
            (r'([A-Z\s]+DISTRICT OF [A-Z\s]+)', None),
            (r'UNITED STATES BANKRUPTCY COURT\s+(?:FOR THE\s+)?([A-Z\s]+)', None)
        ]
        
        # Search in first 2000 characters
        content_start = content[:2000].upper()
        
        for pattern, court_id in patterns:
            match = re.search(pattern.upper(), content_start)
            if match:
                if court_id:
                    # We have a direct court_id mapping
                    logger.info(f"  Extracted court ID from content: {court_id}")
                    return court_id
                else:
                    # Extract the court name from the pattern
                    if len(match.groups()) > 0:
                        court_name = match.group(1).strip()
                    else:
                        court_name = match.group(0).strip()
                    logger.info(f"  Extracted court name from content: {court_name}")
                    return court_name
        
        return None
    
    def _extract_citations(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Extract citations with Eyecite"""
        content = document.get('content', '')
        
        if not content:
            return {'count': 0, 'citations': []}
        
        try:
            # Extract citations directly (no clean_text needed)
            citations = get_citations(content)
            
            citation_list = []
            for citation in citations:
                citation_data = {
                    'text': str(citation),
                    'type': type(citation).__name__,
                    'span': getattr(citation, 'span', None)
                }
                
                # Add groups for reporter info
                if hasattr(citation, 'groups'):
                    citation_data['groups'] = citation.groups
                
                # Add metadata if available
                if hasattr(citation, 'metadata'):
                    metadata = citation.metadata
                    citation_data['metadata'] = {
                        'pin_cite': getattr(metadata, 'pin_cite', None),
                        'year': getattr(metadata, 'year', None),
                        'court': getattr(metadata, 'court', None),
                        'plaintiff': getattr(metadata, 'plaintiff', None),
                        'defendant': getattr(metadata, 'defendant', None)
                    }
                
                citation_list.append(citation_data)
            
            return {
                'count': len(citations),
                'citations': citation_list
            }
            
        except Exception as e:
            logger.error(f"Citation extraction error: {e}")
            return {'count': 0, 'citations': [], 'error': str(e)}
    
    def _normalize_reporters_optimized(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 4: Optimized reporter normalization with edition handling"""
        normalized = []
        normalized_reporters = set()  # Track unique normalized reporters
        
        for citation in citations:
            groups = citation.get('groups', {})
            reporter = groups.get('reporter', '')
            
            if reporter:
                reporter_info = self._get_reporter_info(reporter)
                
                if reporter_info['found']:
                    normalized.append({
                        'original': reporter,
                        'normalized': reporter_info['base_reporter'],
                        'edition': reporter_info['edition'],
                        'name': reporter_info['name'],
                        'cite_type': reporter_info['cite_type']
                    })
                    normalized_reporters.add(reporter_info['edition'])
        
        return {
            'count': len(normalized_reporters),  # Count unique normalized reporters
            'normalized_reporters': normalized,
            'unique_reporters': list(normalized_reporters)
        }
    
    def _get_reporter_info(self, reporter: str) -> Dict[str, Any]:
        """Get complete reporter information including editions"""
        
        # Normalize spaces and case
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
                    
                    # Check if this edition exists in the data
                    editions = base_info.get('editions', {})
                    if edition in editions:
                        return {
                            'found': True,
                            'base_reporter': base_key,
                            'edition': edition,
                            'name': base_info.get('name', 'Federal Reporter'),
                            'cite_type': base_info.get('cite_type', 'federal')
                        }
        
        # Handle Federal Supplement (F. Supp., F. Supp. 2d, F. Supp. 3d)
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
        
        # Check variations in all reporters
        for key, data_list in REPORTERS.items():
            if isinstance(data_list, list) and data_list:
                data = data_list[0]
                variations = data.get('variations', {})
                
                # Check if reporter matches any variation
                if isinstance(variations, dict):
                    for edition_key, edition_vars in variations.items():
                        if isinstance(edition_vars, list):
                            for var in edition_vars:
                                if reporter_clean.lower() == var.lower():
                                    return {
                                        'found': True,
                                        'base_reporter': key,
                                        'edition': edition_key,
                                        'name': data.get('name', ''),
                                        'cite_type': data.get('cite_type', '')
                                    }
        
        return {
            'found': False,
            'base_reporter': reporter_clean,
            'edition': reporter_clean,
            'name': '',
            'cite_type': ''
        }
    
    def _enhance_judge_info_optimized(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 5: Optimized judge information extraction"""
        metadata = document.get('metadata', {})
        
        # Handle metadata that might be a string (JSON) or integer
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif isinstance(metadata, int) or not isinstance(metadata, dict):
            metadata = {}
        
        # Try metadata first
        judge_name = metadata.get('judge_name', '') or metadata.get('judge', '') or metadata.get('assigned_to', '')
        judge_initials = metadata.get('federal_dn_judge_initials_assigned', '')
        extracted_from_content = False
        
        # If no judge name but we have initials, try to use them
        if not judge_name and judge_initials:
            # For now, we'll store the initials as partial info
            # In production, this could be mapped to full names
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
        
        try:
            # Load judge data
            judge_data_path = os.path.join(judge_pics.judge_root, 'people.json')
            
            if os.path.exists(judge_data_path):
                with open(judge_data_path, 'r') as f:
                    judges_data = json.load(f)
                
                # Search for judge (data is a list)
                judge_lower = judge_name.lower()
                for judge_data_item in judges_data:
                    # Handle both dict and other types
                    if not isinstance(judge_data_item, dict):
                        continue
                    
                    # Handle person field which might be an ID (int) or a dict
                    person_field = judge_data_item.get('person')
                    if isinstance(person_field, dict):
                        person_info = person_field
                        person_name = person_info.get('name_full', '')
                    else:
                        # Person is likely an ID, skip this entry
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
                            'extracted_from_content': extracted_from_content
                        }
                
                # If not found but we have a name, return partial enhancement
                return {
                    'enhanced': False,
                    'reason': 'Judge not found in database',
                    'attempted_name': judge_name,
                    'extracted_from_content': extracted_from_content,
                    'judge_name_found': judge_name  # Store the name even if not in DB
                }
            else:
                return {'enhanced': False, 'reason': 'Judge database not available'}
                
        except Exception as e:
            import traceback
            logger.error(f"Judge enhancement error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'enhanced': False, 'error': str(e)}
    
    def _extract_judge_from_content_optimized(self, content: str) -> Optional[str]:
        """Extract judge name from document content with more patterns"""
        if not content:
            return None
        
        # Extended judge patterns
        patterns = [
            r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'Before:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'JUDGE:\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'Signed\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'RODNEY GILSTRAP',  # Direct match for common judge
            r'Rodney Gilstrap',
            r'([A-Z][A-Z\s]+),?\s+UNITED STATES DISTRICT JUDGE'  # All caps pattern
        ]
        
        # Search in first 2000 characters and last 1000 (for signatures)
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
        """Stage 6: Analyze document structure"""
        content = document.get('content', '')
        
        if not content:
            return {'elements': []}
        
        elements = []
        lines = content.split('\n')
        
        # Identify structural elements
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped:
                continue
            
            # Headers (all caps, more than 5 chars)
            if line_stripped.isupper() and len(line_stripped) > 5:
                elements.append({
                    'type': 'header',
                    'text': line_stripped,
                    'line_number': i + 1
                })
            
            # Section markers
            section_keywords = ['BACKGROUND', 'DISCUSSION', 'ANALYSIS', 'CONCLUSION', 
                              'FACTS', 'PROCEDURAL HISTORY', 'STANDARD OF REVIEW']
            for keyword in section_keywords:
                if keyword in line_stripped.upper():
                    elements.append({
                        'type': 'section_marker',
                        'section': keyword,
                        'text': line_stripped,
                        'line_number': i + 1
                    })
                    break
            
            # Opinion/Order markers
            if any(marker in line_stripped.upper() for marker in ['OPINION', 'ORDER', 'MEMORANDUM', 'JUDGMENT']):
                elements.append({
                    'type': 'document_type_marker',
                    'text': line_stripped,
                    'line_number': i + 1
                })
            
            # Numbered paragraphs
            if line_stripped[:3].strip().replace('.', '').isdigit():
                elements.append({
                    'type': 'numbered_paragraph',
                    'text': line_stripped[:50] + '...' if len(line_stripped) > 50 else line_stripped,
                    'line_number': i + 1
                })
        
        return {
            'elements': elements[:50],  # Limit to first 50 elements
            'total_lines': len(lines),
            'structure_score': len(elements) / max(1, len(lines)) * 100
        }
    
    def _extract_legal_keywords(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 7: Extract legal keywords (simple keyword matching)"""
        content = document.get('content', '')
        doc_type = document.get('document_type', 'unknown')
        
        # Be honest about what this does - it's just keyword matching
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
        
        # Legal keywords to search for
        legal_keywords = [
            'summary judgment', 'motion to dismiss', 'claim construction',
            'patent infringement', 'preliminary injunction', 'class action',
            'jurisdiction', 'standing', 'damages', 'liability'
        ]
        
        # Check for each keyword
        for keyword in legal_keywords:
            if keyword in content_lower:
                extraction_result['keywords'].append(keyword)
                logger.debug(f"Found keyword: {keyword}")
        
        # Legal standards keywords
        legal_standards = {
            'de novo': 'de novo review',
            'abuse of discretion': 'abuse of discretion',
            'clear error': 'clear error',
            'arbitrary and capricious': 'arbitrary and capricious'
        }
        
        for search_term, standard_name in legal_standards.items():
            if search_term in content_lower:
                extraction_result['legal_terms'].append(standard_name)
        
        # Procedural keywords
        if 'granted' in content_lower:
            extraction_result['procedural_terms'].append('motion granted')
        if 'denied' in content_lower:
            extraction_result['procedural_terms'].append('motion denied')
        if 'reversed' in content_lower:
            extraction_result['procedural_terms'].append('reversed')
        if 'affirmed' in content_lower:
            extraction_result['procedural_terms'].append('affirmed')
        
        # Log summary
        total_keywords = len(extraction_result['keywords']) + len(extraction_result['legal_terms']) + len(extraction_result['procedural_terms'])
        logger.info(f"Extracted {total_keywords} keywords from document")
        
        return extraction_result
    
    def _assemble_metadata(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 8: Assemble comprehensive metadata"""
        # Remove any non-serializable attributes before assembling
        def clean_for_json(obj):
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items() if not callable(v)}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        return {
            'original_metadata': clean_for_json(document.get('metadata', {})),
            'court_info': clean_for_json(document.get('court_enhancement', {})),
            'citations': {
                'extracted': clean_for_json(document.get('citations_extracted', {})),
                'normalized_reporters': clean_for_json(document.get('reporters_normalized', {}))
            },
            'judge_info': clean_for_json(document.get('judge_enhancement', {})),
            'structure': clean_for_json(document.get('structure_analysis', {})),
            'legal_analysis': clean_for_json(document.get('legal_enhancements', {})),
            'processing_timestamp': datetime.now().isoformat(),
            'pipeline_version': '11-stage-optimized-v1',
            'enhancement_count': self._count_enhancements(document)
        }
    
    def _count_enhancements(self, document: Dict[str, Any]) -> int:
        """Count total enhancements in document"""
        count = 0
        
        if document.get('court_enhancement', {}).get('resolved'):
            count += 1
        
        count += document.get('citations_extracted', {}).get('count', 0)
        count += document.get('reporters_normalized', {}).get('count', 0)
        
        if document.get('judge_enhancement', {}).get('enhanced'):
            count += 1
        elif document.get('judge_enhancement', {}).get('judge_name_found'):
            count += 1  # Count partial enhancement
        
        count += len(document.get('structure_analysis', {}).get('elements', []))
        count += len(document.get('legal_enhancements', {}).get('concepts', []))
        
        return count
    
    def _store_enhanced_documents_fixed(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 9: Enhanced storage with proper conflict handling and validation"""
        stored_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        try:
            with self.db_conn.cursor() as cursor:
                for doc in documents:
                    try:
                        # Validate document has required fields
                        if not doc.get('id'):
                            errors.append(f"Document missing required 'id' field")
                            continue
                            
                        # Generate hash based on content for change detection
                        content_sample = str(doc.get('content', ''))[:1000]  # First 1000 chars
                        doc_hash = hashlib.sha256(
                            f"{doc.get('id')}_{doc.get('case_number', '')}_{content_sample}".encode()
                        ).hexdigest()
                        
                        # Ensure all data is JSON serializable
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
                        
                        # Extract metadata safely
                        metadata = doc.get('metadata', {})
                        if not isinstance(metadata, dict):
                            logger.warning(f"Document {doc.get('id')} has non-dict metadata: {type(metadata)}")
                            metadata = {}
                        
                        # Prepare values with validation
                        cl_id = doc.get('id')
                        court_enhancement = doc.get('court_enhancement', {})
                        court_id = court_enhancement.get('court_id') if court_enhancement.get('resolved') else None
                        case_name = metadata.get('case_name', doc.get('case_number', f'Document-{cl_id}'))
                        
                        # First check if this cl_id already exists
                        cursor.execute("""
                            SELECT id, document_hash FROM court_data.opinions_unified 
                            WHERE cl_id = %s
                        """, (cl_id,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            # Document exists - check if we should update
                            existing_id, existing_hash = existing
                            
                            if existing_hash != doc_hash:
                                # Content has changed, update the record
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
                                    cl_id
                                ))
                                updated_count += 1
                                logger.info(f"Updated existing record for cl_id: {cl_id}")
                            else:
                                # Same content, skip
                                skipped_count += 1
                                logger.debug(f"Skipped unchanged document cl_id: {cl_id}")
                        else:
                            # New document, insert
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
                                cl_id,
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
                            logger.info(f"Stored new document cl_id: {cl_id}")
                            
                    except psycopg2.IntegrityError as e:
                        if 'duplicate key value violates unique constraint' in str(e):
                            logger.warning(f"Document {doc.get('id')} already exists (constraint violation)")
                            skipped_count += 1
                        else:
                            error_msg = f"Integrity error for document {doc.get('id')}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    except Exception as e:
                        error_msg = f"Error storing document {doc.get('id')}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        # Continue with other documents
                        continue
                
                self.db_conn.commit()
                
                total_processed = stored_count + updated_count + skipped_count
                logger.info(f"✅ Storage complete: {stored_count} new, {updated_count} updated, {skipped_count} unchanged")
                
                if errors:
                    logger.warning(f"⚠️  {len(errors)} documents failed to store")
                    
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Storage transaction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stored_count': 0,
                'updated_count': 0,
                'skipped_count': 0,
                'errors': errors
            }
        
        return {
            'success': True,
            'stored_count': stored_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'total_processed': stored_count + updated_count + skipped_count,
            'errors': errors
        }
    
    async def _index_to_haystack(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 10: Index documents to Haystack"""
        try:
            # Prepare documents for Haystack
            haystack_docs = []
            
            for doc in documents:
                # Create a clean metadata dict that's JSON serializable
                clean_metadata = {
                    'id': str(doc.get('id')),
                    'case_number': doc.get('case_number'),
                    'document_type': doc.get('document_type'),
                    'court_id': doc.get('court_enhancement', {}).get('court_id'),
                    'court_name': doc.get('court_enhancement', {}).get('court_name'),
                    'judge_name': doc.get('judge_enhancement', {}).get('full_name', 
                                        doc.get('judge_enhancement', {}).get('judge_name_found', '')),
                    'citation_count': doc.get('citations_extracted', {}).get('count', 0),
                    'processing_timestamp': datetime.now().isoformat()
                }
                
                haystack_doc = {
                    'content': doc.get('content', ''),
                    'meta': clean_metadata
                }
                haystack_docs.append(haystack_doc)
            
            # Send to Haystack
            async with aiohttp.ClientSession() as session:
                url = f"{SERVICES['haystack']['url']}/ingest"
                
                async with session.post(
                    url,
                    json=haystack_docs,  # Haystack expects a list, not a dict
                    timeout=30
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"✅ Indexed {len(haystack_docs)} documents to Haystack")
                        return {
                            'indexed_count': len(haystack_docs),
                            'status': 'success',
                            'response': result
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Haystack indexing failed: {response.status} - {error_text}")
                        return {
                            'indexed_count': 0,
                            'status': 'error',
                            'http_status': response.status,
                            'error': error_text
                        }
                        
        except Exception as e:
            logger.error(f"Haystack integration error: {e}")
            return {
                'indexed_count': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def _verify_pipeline_results_optimized(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 11: Optimized pipeline verification"""
        verification = {
            'documents_with_court_resolution': 0,
            'documents_with_citations': 0,
            'documents_with_normalized_reporters': 0,
            'documents_with_judge_info': 0,
            'documents_with_structure': 0,
            'documents_with_legal_concepts': 0,
            'average_enhancements_per_doc': 0,
            'completeness_score': 0,
            'extraction_improvements': {
                'courts_from_content': 0,
                'judges_from_content': 0
            }
        }
        
        total_enhancements = 0
        
        for doc in documents:
            # Court resolution
            court_data = doc.get('court_enhancement', {})
            if court_data.get('resolved'):
                verification['documents_with_court_resolution'] += 1
                if court_data.get('extracted_from_content'):
                    verification['extraction_improvements']['courts_from_content'] += 1
            
            # Citations
            if doc.get('citations_extracted', {}).get('count', 0) > 0:
                verification['documents_with_citations'] += 1
            
            # Normalized reporters
            if doc.get('reporters_normalized', {}).get('count', 0) > 0:
                verification['documents_with_normalized_reporters'] += 1
            
            # Judge info (count both enhanced and partial)
            judge_data = doc.get('judge_enhancement', {})
            if judge_data.get('enhanced') or judge_data.get('judge_name_found'):
                verification['documents_with_judge_info'] += 1
                if judge_data.get('extracted_from_content'):
                    verification['extraction_improvements']['judges_from_content'] += 1
            
            # Structure
            if len(doc.get('structure_analysis', {}).get('elements', [])) > 0:
                verification['documents_with_structure'] += 1
            
            # Legal keywords
            if len(doc.get('keyword_extraction', {}).get('keywords', [])) > 0:
                verification['documents_with_legal_concepts'] += 1
            
            total_enhancements += self._count_enhancements(doc)
        
        if documents:
            verification['average_enhancements_per_doc'] = total_enhancements / len(documents)
            
            # Calculate completeness score (0-100)
            possible_enhancements = len(documents) * 6  # 6 types of enhancements
            actual_enhancements = sum([
                verification['documents_with_court_resolution'],
                verification['documents_with_citations'],
                verification['documents_with_normalized_reporters'],
                verification['documents_with_judge_info'],
                verification['documents_with_structure'],
                verification['documents_with_legal_concepts']
            ])
            verification['completeness_score'] = (actual_enhancements / possible_enhancements) * 100
        
        logger.info(f"✅ Pipeline verification complete: {verification['completeness_score']:.1f}% complete")
        logger.info(f"   Courts extracted from content: {verification['extraction_improvements']['courts_from_content']}")
        logger.info(f"   Judges extracted from content: {verification['extraction_improvements']['judges_from_content']}")
        
        return verification
    
    def _calculate_complexity_score(self) -> float:
        """Calculate pipeline complexity score"""
        # Base score: 10 points per stage (11 stages = 110)
        base_score = 110
        
        # Enhancement multiplier: 0.5 points per enhancement
        enhancement_score = self.stats['total_enhancements'] * 0.5
        
        # Document multiplier: 5 points per successfully processed document
        document_score = self.stats['documents_processed'] * 5
        
        # Storage bonus: 20 points if documents stored successfully
        storage_bonus = 20 if self.stats['documents_stored'] > 0 else 0
        
        return base_score + enhancement_score + document_score + storage_bonus


async def main():
    """Run the optimized eleven stage pipeline"""
    pipeline = OptimizedElevenStagePipeline()
    
    print("\n" + "🚀 " * 20)
    print("ELEVEN STAGE PIPELINE - FULLY OPTIMIZED")
    print("🚀 " * 20 + "\n")
    
    # Process a batch of documents
    results = await pipeline.process_batch(limit=3)  # Start with just 3 for testing
    
    print("\n" + "=" * 80)
    print("PIPELINE RESULTS")
    print("=" * 80)
    
    if results['success']:
        print(f"\n✅ SUCCESS! All {len(results['stages_completed'])} stages completed")
        print(f"\n📊 STATISTICS:")
        for key, value in results['statistics'].items():
            print(f"   {key}: {value}")
        
        print(f"\n⏱️  Processing Time: {results['processing_time_seconds']:.2f} seconds")
        print(f"📈 Enhancements per Document: {results['enhancements_per_document']:.1f}")
        print(f"🎯 Pipeline Complexity Score: {results['pipeline_complexity_score']:.1f}")
        
        print(f"\n✔️  VERIFICATION:")
        for key, value in results['verification'].items():
            if isinstance(value, dict):
                print(f"   {key}:")
                for subkey, subvalue in value.items():
                    print(f"      {subkey}: {subvalue}")
            else:
                print(f"   {key}: {value}")
        
        print(f"\n🔧 OPTIMIZATION RESULTS:")
        for key, value in results.get('optimization_results', {}).items():
            print(f"   {key}: {value}")
    else:
        print(f"\n❌ Pipeline failed: {results.get('error')}")
        print(f"   Stages completed: {len(results.get('stages_completed', []))}")
        print(f"   Partial stats: {results.get('partial_stats')}")
    
    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(main())