"""
Unified Free Law Project integration that works with existing court_data schema
Integrates with the existing opinions table instead of creating separate tables
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import aiohttp
from datetime import datetime
import asyncio

# Free Law Project imports
from courts_db import find_court, find_court_by_id, courts
from eyecite import get_citations, resolve_citations, clean_text
from reporters_db import EDITIONS, REPORTERS
from xray import detect_bad_redactions
from judge_pics import search_judges, get_judge_photo

logger = logging.getLogger(__name__)

class UnifiedFLPIntegration:
    """
    FLP tools integration that uses existing court_data schema
    """
    
    def __init__(self, db_connection, doctor_url: str = "http://doctor:5050"):
        self.db = db_connection
        self.doctor_url = doctor_url
        self._init_additional_tables()
    
    def _init_additional_tables(self):
        """Initialize only the additional tables needed for FLP-specific data"""
        with self.db.cursor() as cursor:
            # Only create tables that don't exist in the base schema
            
            # Courts reference table for standardization lookups
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.courts_reference (
                    court_id VARCHAR(50) PRIMARY KEY,
                    name TEXT NOT NULL,
                    citation_string TEXT,
                    court_level VARCHAR(20),
                    court_type VARCHAR(20),
                    location TEXT,
                    regex_patterns JSONB,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Reporter normalization cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.normalized_reporters (
                    original TEXT PRIMARY KEY,
                    normalized TEXT NOT NULL,
                    full_name TEXT,
                    metadata JSONB
                );
            """)
            
            # Judge photos cache (extends existing judges table)
            cursor.execute("""
                ALTER TABLE court_data.judges 
                ADD COLUMN IF NOT EXISTS photo_url TEXT,
                ADD COLUMN IF NOT EXISTS judge_pics_id INTEGER,
                ADD COLUMN IF NOT EXISTS metadata JSONB;
            """)
            
            self.db.commit()
    
    async def process_opinion_for_flp(self, opinion_id: int) -> Dict[str, Any]:
        """
        Process an existing opinion with FLP tools
        Enhances the existing record with additional metadata
        """
        results = {
            'opinion_id': opinion_id,
            'enhancements': {},
            'success': False
        }
        
        try:
            # Fetch existing opinion
            with self.db.cursor() as cursor:
                cursor.execute("""
                    SELECT o.*, j.name as judge_name, j.court 
                    FROM court_data.opinions o
                    LEFT JOIN court_data.judges j ON o.judge_id = j.id
                    WHERE o.id = %s
                """, (opinion_id,))
                
                opinion = cursor.fetchone()
                if not opinion:
                    results['error'] = 'Opinion not found'
                    return results
            
            # 1. Standardize court using Courts-DB
            if opinion['court_code']:
                court_info = self.resolve_court(opinion['court_code'], str(opinion['case_date']))
                results['enhancements']['standardized_court'] = court_info
            
            # 2. Extract and normalize citations from text
            if opinion['text_content']:
                citations = get_citations(clean_text(opinion['text_content']))
                resolved_citations = resolve_citations(citations)
                
                normalized_citations = []
                for citation in resolved_citations:
                    if hasattr(citation, 'reporter'):
                        reporter_info = self.normalize_reporter(citation.reporter)
                        normalized_citations.append({
                            'text': str(citation),
                            'normalized_reporter': reporter_info['normalized'],
                            'reporter_full_name': reporter_info['full_name'],
                            'volume': getattr(citation, 'volume', None),
                            'page': getattr(citation, 'page', None)
                        })
                
                results['enhancements']['citations'] = normalized_citations
            
            # 3. Check PDF for bad redactions if available
            if opinion['pdf_path']:
                pdf_full_path = Path('/data/pdfs') / opinion['pdf_path']
                if pdf_full_path.exists():
                    redaction_check = self.check_bad_redactions(pdf_full_path)
                    results['enhancements']['redaction_check'] = redaction_check
            
            # 4. Get judge photo if we have a judge
            if opinion['judge_name']:
                judge_photo = await self.get_judge_photo(
                    opinion['judge_name'], 
                    opinion['court']
                )
                results['enhancements']['judge_photo'] = judge_photo
            
            # 5. Update opinion metadata with enhancements
            await self._update_opinion_metadata(opinion_id, results['enhancements'])
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"FLP processing failed for opinion {opinion_id}: {e}")
            results['error'] = str(e)
        
        return results
    
    async def _update_opinion_metadata(self, opinion_id: int, enhancements: Dict):
        """Update opinion metadata with FLP enhancements"""
        with self.db.cursor() as cursor:
            # Get existing metadata
            cursor.execute("SELECT metadata FROM court_data.opinions WHERE id = %s", (opinion_id,))
            current_metadata = cursor.fetchone()[0] or {}
            
            # Merge enhancements
            current_metadata['flp_enhancements'] = {
                'processed_at': datetime.now().isoformat(),
                'court_standardized': enhancements.get('standardized_court', {}).get('court_id'),
                'citations_found': len(enhancements.get('citations', [])),
                'citations': enhancements.get('citations', []),
                'has_bad_redactions': enhancements.get('redaction_check', {}).get('has_bad_redactions', False),
                'judge_photo_url': enhancements.get('judge_photo', {}).get('photo_url')
            }
            
            # Update the opinion
            cursor.execute("""
                UPDATE court_data.opinions 
                SET metadata = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(current_metadata), opinion_id))
            
            self.db.commit()
    
    async def enhance_new_document(self, pdf_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a new document with FLP tools before inserting into opinions table
        Returns enhanced metadata to be included in the opinion record
        """
        enhancements = {
            'flp_processed': True,
            'flp_processed_at': datetime.now().isoformat()
        }
        
        try:
            # 1. Process PDF with Doctor service
            doctor_results = await self._process_with_doctor(pdf_path)
            enhancements['doctor_results'] = doctor_results
            
            # Extract text if Doctor succeeded
            text_content = doctor_results.get('text', '')
            enhancements['page_count'] = doctor_results.get('page_count', 0)
            
            # 2. Standardize court name
            if metadata.get('court_string'):
                court_info = self.resolve_court(
                    metadata['court_string'], 
                    metadata.get('date_filed')
                )
                enhancements['standardized_court'] = court_info
                # Update metadata with standardized court code
                if court_info.get('court_id'):
                    metadata['court_code'] = court_info['court_id']
            
            # 3. Extract citations
            if text_content:
                citations = get_citations(clean_text(text_content))
                resolved_citations = resolve_citations(citations)
                
                normalized_citations = []
                for citation in resolved_citations:
                    if hasattr(citation, 'reporter'):
                        reporter_info = self.normalize_reporter(citation.reporter)
                        normalized_citations.append({
                            'text': str(citation),
                            'normalized_reporter': reporter_info['normalized'],
                            'reporter_full_name': reporter_info['full_name']
                        })
                
                enhancements['citations'] = normalized_citations
            
            # 4. Check for bad redactions
            redaction_check = self.check_bad_redactions(pdf_path)
            enhancements['has_bad_redactions'] = redaction_check.get('has_bad_redactions', False)
            enhancements['redaction_details'] = redaction_check.get('results', {})
            
            # 5. Extract judge info
            if metadata.get('judge_name'):
                judge_photo = await self.get_judge_photo(
                    metadata['judge_name'],
                    court_info.get('name', '')
                )
                enhancements['judge_photo'] = judge_photo
            
            return {
                'success': True,
                'text_content': text_content,
                'enhancements': enhancements,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"FLP enhancement failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text_content': '',
                'enhancements': enhancements,
                'metadata': metadata
            }
    
    async def _process_with_doctor(self, pdf_path: Path) -> Dict[str, Any]:
        """Process PDF with Doctor service"""
        try:
            async with aiohttp.ClientSession() as session:
                # Create multipart form data
                data = aiohttp.FormData()
                data.add_field('file',
                             open(pdf_path, 'rb'),
                             filename=pdf_path.name,
                             content_type='application/pdf')
                data.add_field('ocr_available', 'true')
                data.add_field('extract_images', 'false')
                
                async with session.post(
                    f"{self.doctor_url}/extract/doc/text/",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'success': True,
                            'text': result.get('extracted_by_ocr') or result.get('content', ''),
                            'page_count': result.get('page_count', 0),
                            'extracted_by_ocr': result.get('extracted_by_ocr', False),
                            'metadata': result.get('metadata', {})
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Doctor service error: {error_text}")
                        return {
                            'success': False,
                            'error': f"Doctor returned {response.status}",
                            'text': ''
                        }
                        
        except Exception as e:
            logger.error(f"Doctor service connection failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    # Include all the existing methods from the original FLP integration
    # (resolve_court, check_bad_redactions, normalize_reporter, get_judge_photo)
    # These remain the same as they're utility functions
    
    def resolve_court(self, court_string: str, date_found: Optional[str] = None) -> Dict[str, Any]:
        """Resolve court name to standardized ID using Courts-DB"""
        court_ids = find_court(court_string, date_found=date_found)
        
        if court_ids:
            court_id = court_ids[0]
            court_data = courts.get(court_id, {})
            
            # Cache in reference table
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.courts_reference 
                    (court_id, name, citation_string, court_level, court_type, location)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (court_id) DO UPDATE SET
                        updated_at = NOW()
                """, (
                    court_id,
                    court_data.get('name', ''),
                    court_data.get('citation_string', ''),
                    court_data.get('level', ''),
                    court_data.get('type', ''),
                    court_data.get('location', '')
                ))
                self.db.commit()
            
            return {
                'court_id': court_id,
                'name': court_data.get('name', ''),
                'citation_string': court_data.get('citation_string', ''),
                'level': court_data.get('level', ''),
                'type': court_data.get('type', ''),
                'location': court_data.get('location', ''),
                'matched_string': court_string,
                'confidence': 'high'
            }
        
        return {
            'court_id': None,
            'matched_string': court_string,
            'confidence': 'none',
            'error': 'Unknown court'
        }
    
    def check_bad_redactions(self, pdf_path: Path) -> Dict[str, Any]:
        """Check for bad redactions using X-Ray"""
        try:
            results = detect_bad_redactions(str(pdf_path))
            has_bad_redactions = bool(results)
            
            return {
                'has_bad_redactions': has_bad_redactions,
                'results': results,
                'success': True
            }
        except Exception as e:
            logger.error(f"X-Ray detection failed: {e}")
            return {
                'has_bad_redactions': False,
                'results': {},
                'success': False,
                'error': str(e)
            }
    
    def normalize_reporter(self, reporter_string: str) -> Dict[str, Any]:
        """Normalize reporter abbreviations using Reporters-DB"""
        
        # Check cache first
        with self.db.cursor() as cursor:
            cursor.execute("""
                SELECT normalized, full_name, metadata 
                FROM court_data.normalized_reporters 
                WHERE original = %s
            """, (reporter_string,))
            
            cached = cursor.fetchone()
            if cached:
                return {
                    'original': reporter_string,
                    'normalized': cached[0],
                    'full_name': cached[1],
                    'metadata': cached[2],
                    'from_cache': True
                }
        
        # Search in REPORTERS database
        normalized = None
        full_name = None
        metadata = {}
        
        # Try exact match first
        for reporter_key, reporter_data in REPORTERS.items():
            if reporter_string.lower() == reporter_key.lower():
                normalized = reporter_key
                full_name = reporter_data.get('name', '')
                metadata = reporter_data
                break
        
        # Try editions if no exact match
        if not normalized:
            for edition in EDITIONS:
                if reporter_string.lower() == edition.get('short_name', '').lower():
                    normalized = edition['short_name']
                    full_name = edition.get('name', '')
                    metadata = edition
                    break
        
        # Cache the result
        if normalized:
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.normalized_reporters 
                    (original, normalized, full_name, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (original) DO NOTHING
                """, (reporter_string, normalized, full_name, json.dumps(metadata)))
                self.db.commit()
        
        return {
            'original': reporter_string,
            'normalized': normalized or reporter_string,
            'full_name': full_name,
            'metadata': metadata,
            'from_cache': False
        }
    
    async def get_judge_photo(self, judge_name: str, court: Optional[str] = None) -> Dict[str, Any]:
        """Get judge photo URL using Judge-pics"""
        try:
            # Search for judge
            results = search_judges(judge_name)
            
            if not results:
                return {
                    'found': False,
                    'judge_name': judge_name,
                    'photo_url': None
                }
            
            # Filter by court if provided
            if court:
                filtered = [j for j in results if court.lower() in j.get('court', '').lower()]
                if filtered:
                    results = filtered
            
            # Get first match
            judge = results[0]
            photo_url = get_judge_photo(judge['id'])
            
            # Update judge record
            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE court_data.judges 
                    SET photo_url = %s,
                        judge_pics_id = %s,
                        metadata = %s,
                        updated_at = NOW()
                    WHERE name = %s
                """, (
                    photo_url,
                    judge['id'],
                    json.dumps(judge),
                    judge_name
                ))
                self.db.commit()
            
            return {
                'found': True,
                'judge_name': judge_name,
                'photo_url': photo_url,
                'judge_id': judge['id'],
                'court': judge.get('court', ''),
                'metadata': judge
            }
            
        except Exception as e:
            logger.error(f"Judge photo lookup failed: {e}")
            return {
                'found': False,
                'judge_name': judge_name,
                'photo_url': None,
                'error': str(e)
            }