#!/usr/bin/env python3
"""
FLP Document Processing with Doctor Service
Handles PDF processing through Doctor + FLP pipeline
"""
import asyncio
import aiohttp
import psycopg2
from psycopg2.extras import Json
from pathlib import Path
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import eyecite
from courts_db import courts as COURTS_LIST
from reporters_db import REPORTERS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FLPDocumentProcessor:
    def __init__(self, doctor_url: str = "http://doctor-judicial:5050"):
        self.doctor_url = doctor_url
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def check_doctor_health(self) -> bool:
        """Check if Doctor service is available"""
        try:
            async with self.session.get(f"{self.doctor_url}/", timeout=2) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Doctor health check failed: {e}")
            return False
    
    async def process_pdf_with_doctor(self, pdf_path: Path) -> Dict[str, Any]:
        """
        Process PDF through Doctor service
        Returns extracted text, thumbnails, and metadata
        """
        try:
            # Prepare the file for upload
            with open(pdf_path, 'rb') as pdf_file:
                data = aiohttp.FormData()
                data.add_field('file', pdf_file, 
                             filename=pdf_path.name,
                             content_type='application/pdf')
                data.add_field('strip_margin', 'true')
                
                # Extract text
                async with self.session.post(
                    f"{self.doctor_url}/extract/doc/text/",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        # Doctor returns 'content' not 'text'
                        extracted_text = result.get('content', result.get('text', ''))
                        
                        # Log the response structure for debugging
                        logger.info(f"Doctor response keys: {list(result.keys())}")
                        
                        # Get metadata
                        metadata = {
                            'doctor_extracted': True,
                            'extraction_method': result.get('extraction_method', 'unknown'),
                            'page_count': result.get('page_count', 0),
                            'file_size': pdf_path.stat().st_size,
                            'extracted_length': len(extracted_text)
                        }
                        
                        # Extract document number if available
                        if 'document_number' in result:
                            metadata['document_number'] = result['document_number']
                        
                        return {
                            'success': True,
                            'text': extracted_text,
                            'metadata': metadata
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Doctor extraction failed: {error_text}")
                        return {
                            'success': False,
                            'error': f"Doctor returned {response.status}",
                            'text': ''
                        }
                        
        except Exception as e:
            logger.error(f"Error processing with Doctor: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': ''
            }
    
    async def generate_thumbnail(self, pdf_path: Path, size: str = "small") -> Optional[bytes]:
        """Generate thumbnail for PDF"""
        try:
            with open(pdf_path, 'rb') as pdf_file:
                data = aiohttp.FormData()
                data.add_field('file', pdf_file,
                             filename=pdf_path.name,
                             content_type='application/pdf')
                data.add_field('size', size)
                
                async with self.session.post(
                    f"{self.doctor_url}/convert/pdf/thumbnails/",
                    data=data
                ) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Thumbnail generation failed: {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error generating thumbnail: {e}")
            return None
    
    def extract_citations(self, text: str) -> list:
        """Extract citations using Eyecite"""
        citations = []
        try:
            found_citations = eyecite.get_citations(text)
            
            for cite in found_citations[:50]:  # Limit to 50 citations
                cite_dict = {
                    'text': str(cite),
                    'type': type(cite).__name__,
                    'index': cite.index
                }
                
                # Add citation-specific attributes
                if hasattr(cite, 'reporter'):
                    cite_dict['reporter'] = cite.reporter
                if hasattr(cite, 'volume'):
                    cite_dict['volume'] = cite.volume
                if hasattr(cite, 'page'):
                    cite_dict['page'] = cite.page
                if hasattr(cite, 'metadata') and cite.metadata:
                    if hasattr(cite.metadata, 'year'):
                        cite_dict['year'] = cite.metadata.year
                    if hasattr(cite.metadata, 'court'):
                        cite_dict['court'] = cite.metadata.court
                        
                citations.append(cite_dict)
                
        except Exception as e:
            logger.error(f"Citation extraction failed: {e}")
            
        return citations
    
    def standardize_court(self, court_id: str) -> Dict[str, Any]:
        """Standardize court using Courts-DB"""
        for court in COURTS_LIST:
            if court.get('id') == court_id:
                return {
                    'id': court.get('id'),
                    'name': court.get('name'),
                    'full_name': court.get('full_name'),
                    'citation_string': court.get('citation_string'),
                    'jurisdiction': court.get('jurisdiction', 'Unknown'),
                    'standardized': True
                }
        return {'id': court_id, 'standardized': False}
    
    def normalize_reporters(self, citations: list) -> list:
        """Normalize reporter citations using Reporters-DB"""
        normalized = []
        
        for citation in citations:
            if 'reporter' in citation:
                reporter = citation['reporter']
                
                # Search in REPORTERS database
                for rep_key, editions in REPORTERS.items():
                    for edition in editions:
                        if isinstance(edition, dict) and reporter == edition.get('cite_type'):
                            citation['normalized_reporter'] = {
                                'cite_type': edition.get('cite_type'),
                                'name': edition.get('name', rep_key),
                                'examples': edition.get('examples', [])[:2]
                            }
                            normalized.append(citation)
                            break
                            
        return normalized
    
    async def process_document(self, pdf_path: Path, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Complete document processing pipeline:
        1. Extract text with Doctor
        2. Extract citations with Eyecite
        3. Standardize courts with Courts-DB
        4. Normalize reporters with Reporters-DB
        """
        result = {
            'success': False,
            'pdf_path': str(pdf_path),
            'metadata': metadata,
            'processing_timestamp': datetime.now().isoformat()
        }
        
        # Check Doctor availability
        if not await self.check_doctor_health():
            result['error'] = "Doctor service not available"
            return result
        
        # 1. Extract text with Doctor
        logger.info(f"Processing {pdf_path.name} with Doctor...")
        extraction = await self.process_pdf_with_doctor(pdf_path)
        
        if not extraction['success']:
            result['error'] = extraction.get('error', 'Unknown extraction error')
            return result
        
        result['text'] = extraction['text']
        result['extraction_metadata'] = extraction['metadata']
        
        # 2. Extract citations
        logger.info("Extracting citations...")
        citations = self.extract_citations(extraction['text'])
        result['citations'] = citations
        result['citation_count'] = len(citations)
        
        # 3. Normalize reporters
        normalized_citations = self.normalize_reporters(citations)
        result['normalized_citations'] = normalized_citations
        
        # 4. Standardize court if provided
        if 'court' in metadata:
            court_info = self.standardize_court(metadata['court'])
            result['court_info'] = court_info
        
        # 5. Generate thumbnail
        thumbnail = await self.generate_thumbnail(pdf_path, size="small")
        if thumbnail:
            result['has_thumbnail'] = True
            # Store thumbnail path or data as needed
        
        result['success'] = True
        result['flp_components_used'] = [
            'doctor', 'eyecite', 'courts_db', 'reporters_db'
        ]
        
        return result
    
    def save_to_database(self, conn, result: Dict[str, Any]):
        """Save processed document to PostgreSQL"""
        cursor = conn.cursor()
        
        try:
            # Prepare document record
            case_number = result['metadata'].get('case_number', f"DOC-{datetime.now().timestamp()}")
            
            metadata = {
                **result['metadata'],
                'doctor_extraction': result.get('extraction_metadata', {}),
                'citations_found': result.get('citation_count', 0),
                'citations': result.get('citations', [])[:20],  # Store first 20
                'court_info': result.get('court_info', {}),
                'flp_processed': True,
                'flp_components': result.get('flp_components_used', []),
                'processing_timestamp': result['processing_timestamp']
            }
            
            cursor.execute("""
                INSERT INTO court_documents (
                    case_number, document_type, file_path, content, metadata, processed
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                case_number,
                'opinion_doctor',
                str(result['pdf_path']),
                result.get('text', ''),
                Json(metadata),
                True
            ))
            
            conn.commit()
            logger.info(f"Saved {case_number} to database")
            
        except Exception as e:
            logger.error(f"Database save failed: {e}")
            conn.rollback()
            raise
        finally:
            cursor.close()


async def process_pdf_file(pdf_path: str, metadata: Dict[str, Any] = None):
    """Process a single PDF file through the FLP pipeline"""
    async with FLPDocumentProcessor() as processor:
        result = await processor.process_document(
            Path(pdf_path),
            metadata or {}
        )
        
        if result['success']:
            # Save to database
            conn = psycopg2.connect(
                host='db',
                database='aletheia',
                user='aletheia',
                password='aletheia123'
            )
            processor.save_to_database(conn, result)
            conn.close()
            
        return result


if __name__ == "__main__":
    # Test with a sample PDF
    import sys
    
    if len(sys.argv) > 1:
        pdf_file = sys.argv[1]
        metadata = {
            'court': 'cafc',
            'case_number': 'TEST-001',
            'source': 'manual_test'
        }
        
        result = asyncio.run(process_pdf_file(pdf_file, metadata))
        
        if result['success']:
            print(f"✅ Successfully processed {pdf_file}")
            print(f"   Text length: {len(result['text'])}")
            print(f"   Citations found: {result['citation_count']}")
        else:
            print(f"❌ Failed: {result.get('error', 'Unknown error')}")
    else:
        print("Usage: python flp_document_processor.py <pdf_file>")