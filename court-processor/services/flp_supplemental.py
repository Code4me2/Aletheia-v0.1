"""
Supplemental FLP Integration Service
Enhances existing CourtListener/Juriscraper data without duplication
"""
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import aiohttp
from datetime import datetime
import asyncio
from psycopg2.extras import RealDictCursor

# Free Law Project imports
from courts_db import find_court, courts
from eyecite import get_citations, resolve_citations, clean_text
from reporters_db import EDITIONS, REPORTERS
from xray import detect_bad_redactions
from judge_pics import search_judges, get_judge_photo

logger = logging.getLogger(__name__)

class FLPSupplementalService:
    """
    Supplements existing court data with FLP tools
    Avoids duplication and respects existing data
    """
    
    def __init__(self, db_connection, doctor_url: str = "http://doctor:5050"):
        self.db = db_connection
        self.doctor_url = doctor_url
        self._init_supplemental_tables()
    
    def _init_supplemental_tables(self):
        """Initialize only supplemental tables that don't conflict"""
        with self.db.cursor() as cursor:
            # Courts standardization mapping
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.court_standardization (
                    original_code VARCHAR(50) PRIMARY KEY,
                    flp_court_id VARCHAR(50),
                    court_name TEXT,
                    confidence VARCHAR(20),
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Citation normalization cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.citation_normalization (
                    original TEXT PRIMARY KEY,
                    normalized TEXT NOT NULL,
                    reporter_full_name TEXT,
                    reporter_metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Bad redaction findings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.redaction_issues (
                    document_id BIGINT PRIMARY KEY,
                    document_type VARCHAR(50), -- 'opinion' or 'recap_document'
                    has_bad_redactions BOOLEAN,
                    redaction_details JSONB,
                    checked_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Judge photos (extend existing table)
            cursor.execute("""
                ALTER TABLE court_data.judges 
                ADD COLUMN IF NOT EXISTS photo_url TEXT,
                ADD COLUMN IF NOT EXISTS judge_pics_id INTEGER,
                ADD COLUMN IF NOT EXISTS flp_metadata JSONB;
            """)
            
            self.db.commit()
    
    async def enhance_opinion(self, opinion_id: int, source: str = 'opinions') -> Dict[str, Any]:
        """
        Enhance an existing opinion from either source
        source: 'opinions' (juriscraper) or 'cl_opinions' (courtlistener)
        """
        result = {
            'opinion_id': opinion_id,
            'source': source,
            'enhancements': {},
            'actions_taken': [],
            'success': False
        }
        
        try:
            # Fetch the opinion
            opinion = self._fetch_opinion(opinion_id, source)
            if not opinion:
                result['error'] = f'Opinion {opinion_id} not found in {source}'
                return result
            
            # 1. Text Extraction (only if missing)
            text_content = await self._ensure_text_content(opinion, source)
            if text_content and not opinion.get('text_content'):
                result['enhancements']['text_extracted'] = True
                result['actions_taken'].append('text_extraction')
            
            # 2. Court Standardization (always enhance)
            court_code = opinion.get('court_code') or opinion.get('court_id')
            if court_code:
                court_std = await self._standardize_court(court_code)
                if court_std['standardized']:
                    result['enhancements']['court_standardization'] = court_std
                    result['actions_taken'].append('court_standardization')
            
            # 3. Citation Enhancement
            if text_content:
                citation_data = await self._enhance_citations(opinion, text_content)
                if citation_data['citations_found'] > 0:
                    result['enhancements']['citations'] = citation_data
                    result['actions_taken'].append('citation_extraction')
            
            # 4. Bad Redaction Check (if PDF available)
            pdf_path = self._get_pdf_path(opinion, source)
            if pdf_path and pdf_path.exists():
                redaction_check = await self._check_redactions(opinion_id, source, pdf_path)
                if redaction_check['checked']:
                    result['enhancements']['redaction_check'] = redaction_check
                    result['actions_taken'].append('redaction_check')
            
            # 5. Judge Photo (if judge identified)
            judge_data = await self._enhance_judge_info(opinion)
            if judge_data['enhanced']:
                result['enhancements']['judge'] = judge_data
                result['actions_taken'].append('judge_photo')
            
            # 6. Save enhancements
            if result['actions_taken']:
                await self._save_enhancements(opinion_id, source, result['enhancements'])
                result['success'] = True
            else:
                result['message'] = 'No enhancements needed - data already complete'
                result['success'] = True
            
        except Exception as e:
            logger.error(f"Enhancement failed for {source}:{opinion_id}: {e}")
            result['error'] = str(e)
        
        return result
    
    def _fetch_opinion(self, opinion_id: int, source: str) -> Optional[Dict]:
        """Fetch opinion from appropriate table"""
        table = 'court_data.opinions' if source == 'opinions' else 'court_data.cl_opinions'
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"""
                SELECT * FROM {table} WHERE id = %s
            """, (opinion_id,))
            return cursor.fetchone()
    
    async def _ensure_text_content(self, opinion: Dict, source: str) -> Optional[str]:
        """Extract text only if not already present"""
        # Check existing text fields
        text_fields = ['text_content', 'plain_text', 'html', 'html_lawbox']
        for field in text_fields:
            if opinion.get(field):
                return opinion[field]
        
        # Need to extract text
        pdf_path = self._get_pdf_path(opinion, source)
        if not pdf_path or not pdf_path.exists():
            return None
        
        # Use Doctor for extraction
        doctor_result = await self._extract_with_doctor(pdf_path)
        if doctor_result['success']:
            # Update the opinion with extracted text
            self._update_text_content(opinion['id'], source, doctor_result['text'])
            return doctor_result['text']
        
        return None
    
    def _get_pdf_path(self, opinion: Dict, source: str) -> Optional[Path]:
        """Get PDF path for opinion"""
        if source == 'opinions':
            if opinion.get('pdf_path'):
                return Path('/data/pdfs') / opinion['pdf_path']
        else:  # cl_opinions
            if opinion.get('local_path'):
                return Path(opinion['local_path'])
        return None
    
    async def _extract_with_doctor(self, pdf_path: Path) -> Dict[str, Any]:
        """Extract text using Doctor service"""
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file',
                             open(pdf_path, 'rb'),
                             filename=pdf_path.name,
                             content_type='application/pdf')
                data.add_field('ocr_available', 'true')
                
                async with session.post(
                    f"{self.doctor_url}/extract/doc/text/",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            'success': True,
                            'text': result.get('content', ''),
                            'page_count': result.get('page_count', 0),
                            'method': 'doctor'
                        }
                    else:
                        return {'success': False, 'error': f'Doctor returned {response.status}'}
        except Exception as e:
            logger.error(f"Doctor extraction failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _standardize_court(self, court_code: str) -> Dict[str, Any]:
        """Standardize court using Courts-DB"""
        # Check cache first
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM court_data.court_standardization 
                WHERE original_code = %s
            """, (court_code,))
            cached = cursor.fetchone()
            if cached:
                return {
                    'standardized': True,
                    'original': court_code,
                    'flp_court_id': cached['flp_court_id'],
                    'court_name': cached['court_name'],
                    'from_cache': True
                }
        
        # Resolve using Courts-DB
        court_ids = find_court(court_code)
        if court_ids:
            court_id = court_ids[0]
            court_info = courts.get(court_id, {})
            
            # Cache the result
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.court_standardization
                    (original_code, flp_court_id, court_name, confidence)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (original_code) DO NOTHING
                """, (court_code, court_id, court_info.get('name', ''), 'high'))
                self.db.commit()
            
            return {
                'standardized': True,
                'original': court_code,
                'flp_court_id': court_id,
                'court_name': court_info.get('name', ''),
                'from_cache': False
            }
        
        return {'standardized': False, 'original': court_code}
    
    async def _enhance_citations(self, opinion: Dict, text: str) -> Dict[str, Any]:
        """Extract and enhance citations"""
        # Get existing citations if any
        existing_citations = []
        if opinion.get('opinions_cited'):
            existing_citations = opinion['opinions_cited']
        
        # Extract new citations
        citations = get_citations(clean_text(text))
        resolved = resolve_citations(citations)
        
        enhanced_citations = []
        for citation in resolved:
            cit_data = {
                'text': str(citation),
                'type': citation.__class__.__name__
            }
            
            # Normalize reporter if present
            if hasattr(citation, 'reporter'):
                reporter_info = self._normalize_reporter(citation.reporter)
                cit_data.update({
                    'reporter': citation.reporter,
                    'reporter_normalized': reporter_info['normalized'],
                    'reporter_full_name': reporter_info['full_name']
                })
            
            if hasattr(citation, 'volume'):
                cit_data['volume'] = citation.volume
            if hasattr(citation, 'page'):
                cit_data['page'] = citation.page
            
            enhanced_citations.append(cit_data)
        
        return {
            'citations_found': len(enhanced_citations),
            'citations': enhanced_citations,
            'existing_citations_count': len(existing_citations)
        }
    
    def _normalize_reporter(self, reporter: str) -> Dict[str, Any]:
        """Normalize reporter abbreviation"""
        # Check cache
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM court_data.citation_normalization 
                WHERE original = %s
            """, (reporter,))
            cached = cursor.fetchone()
            if cached:
                return {
                    'original': reporter,
                    'normalized': cached['normalized'],
                    'full_name': cached['reporter_full_name']
                }
        
        # Normalize using Reporters-DB
        normalized = reporter
        full_name = ''
        
        for reporter_key, reporter_data in REPORTERS.items():
            if reporter.lower() == reporter_key.lower():
                normalized = reporter_key
                full_name = reporter_data.get('name', '')
                break
        
        # Cache result
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO court_data.citation_normalization
                (original, normalized, reporter_full_name, reporter_metadata)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (original) DO NOTHING
            """, (reporter, normalized, full_name, json.dumps({})))
            self.db.commit()
        
        return {
            'original': reporter,
            'normalized': normalized,
            'full_name': full_name
        }
    
    async def _check_redactions(self, doc_id: int, doc_type: str, pdf_path: Path) -> Dict[str, Any]:
        """Check for bad redactions"""
        # Check if already analyzed
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT * FROM court_data.redaction_issues 
                WHERE document_id = %s AND document_type = %s
            """, (doc_id, doc_type))
            existing = cursor.fetchone()
            if existing:
                return {
                    'checked': True,
                    'has_bad_redactions': existing['has_bad_redactions'],
                    'from_cache': True
                }
        
        # Check with X-Ray
        try:
            results = detect_bad_redactions(str(pdf_path))
            has_bad = bool(results)
            
            # Save results
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.redaction_issues
                    (document_id, document_type, has_bad_redactions, redaction_details)
                    VALUES (%s, %s, %s, %s)
                """, (doc_id, doc_type, has_bad, json.dumps(results)))
                self.db.commit()
            
            return {
                'checked': True,
                'has_bad_redactions': has_bad,
                'details': results,
                'from_cache': False
            }
        except Exception as e:
            logger.error(f"X-Ray check failed: {e}")
            return {'checked': False, 'error': str(e)}
    
    async def _enhance_judge_info(self, opinion: Dict) -> Dict[str, Any]:
        """Enhance judge information with photo"""
        judge_name = None
        judge_id = None
        
        # Get judge info based on source
        if opinion.get('judge_id'):
            # Juriscraper opinion
            with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT * FROM court_data.judges WHERE id = %s
                """, (opinion['judge_id'],))
                judge = cursor.fetchone()
                if judge:
                    judge_name = judge['name']
                    judge_id = judge['id']
        elif opinion.get('author_str'):
            # CourtListener opinion
            judge_name = opinion['author_str']
        
        if not judge_name:
            return {'enhanced': False, 'reason': 'No judge found'}
        
        # Check if already has photo
        if judge_id:
            with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT photo_url FROM court_data.judges WHERE id = %s
                """, (judge_id,))
                existing = cursor.fetchone()
                if existing and existing['photo_url']:
                    return {'enhanced': False, 'reason': 'Already has photo'}
        
        # Get photo from Judge-pics
        try:
            results = search_judges(judge_name)
            if results:
                judge_match = results[0]
                photo_url = get_judge_photo(judge_match['id'])
                
                # Update or create judge record
                if judge_id:
                    with self.db.cursor() as cursor:
                        cursor.execute("""
                            UPDATE court_data.judges
                            SET photo_url = %s, judge_pics_id = %s, 
                                flp_metadata = %s, updated_at = NOW()
                            WHERE id = %s
                        """, (photo_url, judge_match['id'], 
                              json.dumps(judge_match), judge_id))
                        self.db.commit()
                
                return {
                    'enhanced': True,
                    'judge_name': judge_name,
                    'photo_url': photo_url,
                    'judge_pics_id': judge_match['id']
                }
        except Exception as e:
            logger.error(f"Judge photo lookup failed: {e}")
        
        return {'enhanced': False, 'reason': 'Photo not found'}
    
    def _update_text_content(self, opinion_id: int, source: str, text: str):
        """Update opinion with extracted text"""
        table = 'court_data.opinions' if source == 'opinions' else 'court_data.cl_opinions'
        field = 'text_content' if source == 'opinions' else 'plain_text'
        
        with self.db.cursor() as cursor:
            cursor.execute(f"""
                UPDATE {table} 
                SET {field} = %s, updated_at = NOW()
                WHERE id = %s
            """, (text, opinion_id))
            self.db.commit()
    
    async def _save_enhancements(self, opinion_id: int, source: str, enhancements: Dict):
        """Save enhancement metadata"""
        table = 'court_data.opinions' if source == 'opinions' else 'court_data.cl_opinions'
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get existing metadata
            cursor.execute(f"SELECT metadata FROM {table} WHERE id = %s", (opinion_id,))
            row = cursor.fetchone()
            metadata = row['metadata'] or {}
            
            # Add FLP enhancements
            metadata['flp_supplemental'] = {
                'enhanced_at': datetime.now().isoformat(),
                'enhancements': enhancements
            }
            
            # Update metadata
            cursor.execute(f"""
                UPDATE {table}
                SET metadata = %s, updated_at = NOW()
                WHERE id = %s
            """, (json.dumps(metadata), opinion_id))
            self.db.commit()
    
    async def batch_enhance(self, limit: int = 100, source: str = 'both') -> Dict[str, Any]:
        """Batch enhance opinions that need it"""
        opinions_to_enhance = []
        
        # Find opinions needing enhancement
        if source in ['opinions', 'both']:
            opinions_to_enhance.extend(self._find_unenhanced_opinions('opinions', limit))
        
        if source in ['cl_opinions', 'both']:
            opinions_to_enhance.extend(self._find_unenhanced_opinions('cl_opinions', limit))
        
        # Process in parallel with rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent
        
        async def enhance_with_limit(opinion_data):
            async with semaphore:
                return await self.enhance_opinion(
                    opinion_data['id'], 
                    opinion_data['source']
                )
        
        tasks = [enhance_with_limit(op) for op in opinions_to_enhance[:limit]]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Summarize results
        successful = sum(1 for r in results 
                        if isinstance(r, dict) and r.get('success'))
        
        return {
            'total_processed': len(results),
            'successful': successful,
            'failed': len(results) - successful,
            'opinions_enhanced': opinions_to_enhance[:len(results)]
        }
    
    def _find_unenhanced_opinions(self, source: str, limit: int) -> List[Dict]:
        """Find opinions that haven't been enhanced"""
        table = 'court_data.opinions' if source == 'opinions' else 'court_data.cl_opinions'
        
        with self.db.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(f"""
                SELECT id, case_date 
                FROM {table}
                WHERE metadata->>'flp_supplemental' IS NULL
                ORDER BY case_date DESC
                LIMIT %s
            """, (limit,))
            
            return [{'id': row['id'], 'source': source} for row in cursor.fetchall()]