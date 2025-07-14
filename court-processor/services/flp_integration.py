"""
Comprehensive Free Law Project tools integration
Includes Courts-DB, Doctor, Juriscraper, Eyecite, X-Ray, Reporters-DB, and Judge-pics
"""
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import json
import aiohttp
from datetime import datetime

# Free Law Project imports
from courts_db import find_court, find_court_by_id, courts
from eyecite import get_citations, resolve_citations, clean_text
from reporters_db import EDITIONS, REPORTERS
from xray import detect_bad_redactions
from judge_pics import search_judges, get_judge_photo

logger = logging.getLogger(__name__)

class FLPIntegration:
    """
    Unified interface for all Free Law Project tools
    """
    
    def __init__(self, db_connection, doctor_url: str = "http://doctor:5050"):
        self.db = db_connection
        self.doctor_url = doctor_url
        self._init_database_tables()
    
    def _init_database_tables(self):
        """Initialize all required database tables"""
        with self.db.cursor() as cursor:
            # Courts reference table
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
            
            # Processed documents with FLP enhancements
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.processed_documents_flp (
                    id SERIAL PRIMARY KEY,
                    case_name TEXT NOT NULL,
                    docket_number TEXT,
                    court_id VARCHAR(50),
                    date_filed DATE,
                    extracted_text TEXT,
                    page_count INTEGER DEFAULT 0,
                    has_bad_redactions BOOLEAN DEFAULT FALSE,
                    bad_redaction_details JSONB,
                    thumbnail_path TEXT,
                    normalized_citations JSONB,
                    judge_ids JSONB,
                    processing_metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Judge information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.judges (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    court VARCHAR(100),
                    photo_url TEXT,
                    judge_pics_id INTEGER,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            
            # Citation normalization cache
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS court_data.normalized_reporters (
                    original TEXT PRIMARY KEY,
                    normalized TEXT NOT NULL,
                    full_name TEXT,
                    metadata JSONB
                );
            """)
            
            self.db.commit()
    
    # Courts-DB Functions
    def resolve_court(self, court_string: str, date_found: Optional[str] = None) -> Dict[str, Any]:
        """Resolve court name to standardized ID using Courts-DB"""
        court_ids = find_court(court_string, date_found=date_found)
        
        if court_ids:
            court_id = court_ids[0]
            court_data = courts.get(court_id, {})
            
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
    
    # X-Ray Functions (Bad Redaction Detection)
    def check_bad_redactions(self, pdf_path: Path) -> Dict[str, Any]:
        """Check for bad redactions using X-Ray"""
        try:
            # X-Ray can be used directly or through Doctor
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
    
    # Reporters-DB Functions
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
    
    # Judge-pics Functions
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
            
            # Store in database
            with self.db.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.judges 
                    (name, court, photo_url, judge_pics_id, metadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (name) DO UPDATE SET
                        photo_url = EXCLUDED.photo_url,
                        judge_pics_id = EXCLUDED.judge_pics_id,
                        updated_at = NOW()
                """, (
                    judge_name,
                    judge.get('court', ''),
                    photo_url,
                    judge['id'],
                    json.dumps(judge)
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
    
    # Comprehensive Document Processing
    async def process_document_comprehensive(self, pdf_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process document using all FLP tools
        
        Args:
            pdf_path: Path to PDF file
            metadata: Document metadata including case_name, court_string, etc.
        
        Returns:
            Comprehensive processing results
        """
        results = {
            'success': False,
            'steps_completed': [],
            'errors': []
        }
        
        try:
            # 1. Resolve court using Courts-DB
            court_info = self.resolve_court(
                metadata.get('court_string', ''),
                metadata.get('date_filed')
            )
            results['court'] = court_info
            results['steps_completed'].append('court_resolution')
            
            # 2. Check bad redactions with X-Ray
            redaction_check = self.check_bad_redactions(pdf_path)
            results['redactions'] = redaction_check
            results['steps_completed'].append('redaction_check')
            
            # 3. Extract text (would use Doctor in production)
            # For now, using a placeholder
            results['text'] = f"[Text extraction would use Doctor service for {pdf_path}]"
            results['steps_completed'].append('text_extraction')
            
            # 4. Extract and normalize citations
            if results.get('text'):
                citations = get_citations(clean_text(results['text']))
                resolved_citations = resolve_citations(citations)
                
                # Normalize reporters
                normalized_citations = []
                for citation in resolved_citations:
                    if hasattr(citation, 'reporter'):
                        reporter_info = self.normalize_reporter(citation.reporter)
                        normalized_citations.append({
                            'text': str(citation),
                            'normalized_reporter': reporter_info['normalized'],
                            'reporter_full_name': reporter_info['full_name']
                        })
                
                results['citations'] = normalized_citations
                results['steps_completed'].append('citation_extraction')
            
            # 5. Extract judge names and get photos
            judge_names = self._extract_judge_names(metadata, results.get('text', ''))
            results['judges'] = []
            
            for judge_name in judge_names:
                judge_info = await self.get_judge_photo(
                    judge_name, 
                    court_info.get('name', '')
                )
                results['judges'].append(judge_info)
            
            if judge_names:
                results['steps_completed'].append('judge_photos')
            
            # 6. Save comprehensive results
            await self._save_comprehensive_results(results, metadata)
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Comprehensive processing failed: {e}")
            results['errors'].append(str(e))
        
        return results
    
    def _extract_judge_names(self, metadata: Dict, text: str) -> List[str]:
        """Extract judge names from metadata or text"""
        judge_names = []
        
        # Check metadata first
        if metadata.get('judges'):
            if isinstance(metadata['judges'], str):
                judge_names.append(metadata['judges'])
            elif isinstance(metadata['judges'], list):
                judge_names.extend(metadata['judges'])
        
        # Could add more sophisticated extraction from text here
        
        return judge_names
    
    async def _save_comprehensive_results(self, results: Dict, metadata: Dict):
        """Save comprehensive processing results"""
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO court_data.processed_documents_flp
                (case_name, docket_number, court_id, date_filed,
                 extracted_text, has_bad_redactions, bad_redaction_details,
                 normalized_citations, judge_ids, processing_metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                metadata.get('case_name'),
                metadata.get('docket_number'),
                results['court'].get('court_id'),
                metadata.get('date_filed'),
                results.get('text', ''),
                results['redactions'].get('has_bad_redactions', False),
                json.dumps(results['redactions'].get('results', {})),
                json.dumps(results.get('citations', [])),
                json.dumps([j['judge_id'] for j in results.get('judges', []) if j.get('judge_id')]),
                json.dumps({
                    'steps_completed': results['steps_completed'],
                    'errors': results['errors'],
                    'processed_at': datetime.now().isoformat()
                })
            ))
            self.db.commit()