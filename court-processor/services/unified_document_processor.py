"""
Unified Document Processor: CL → FLP → Unstructured → PostgreSQL Pipeline
"""
import asyncio
import hashlib
import json
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime
import base64
import aiohttp
try:
    from unstructured.partition.auto import partition
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    partition = None
import tempfile
import os

from .flp_integration import FLPIntegration
from .courtlistener_service import CourtListenerService
from .database import get_db_connection
from .legal_document_enhancer import enhance_legal_document

logger = logging.getLogger(__name__)


class DeduplicationManager:
    """Manages document deduplication using SHA-256 hashing"""
    
    def __init__(self):
        self.processed_hashes: Set[str] = set()
        self._load_existing_hashes()
    
    def _load_existing_hashes(self):
        """Load existing document hashes from PostgreSQL"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT document_hash 
                FROM court_data.opinions_unified 
                WHERE document_hash IS NOT NULL
            """)
            self.processed_hashes = {row[0] for row in cursor.fetchall()}
            conn.close()
            logger.info(f"Loaded {len(self.processed_hashes)} existing document hashes")
        except Exception as e:
            logger.error(f"Failed to load existing hashes: {e}")
    
    def generate_hash(self, document: Dict) -> str:
        """Generate SHA-256 hash from document fields"""
        # Create deterministic string from key fields
        hash_fields = {
            'court_id': document.get('court_id', ''),
            'docket_number': document.get('docket_number', ''),
            'case_name': document.get('case_name', ''),
            'date_filed': str(document.get('date_filed', '')),
            'author_str': document.get('author_str', ''),
            # Include first 1000 chars of text for uniqueness
            'text_preview': (document.get('plain_text', '') or 
                           document.get('html', '') or 
                           document.get('html_lawbox', '') or 
                           document.get('html_columbia', ''))[:1000]
        }
        
        hash_string = json.dumps(hash_fields, sort_keys=True)
        return hashlib.sha256(hash_string.encode()).hexdigest()
    
    def is_duplicate(self, document: Dict) -> bool:
        """Check if document already exists"""
        doc_hash = self.generate_hash(document)
        return doc_hash in self.processed_hashes
    
    def mark_processed(self, document: Dict):
        """Mark document as processed"""
        doc_hash = self.generate_hash(document)
        self.processed_hashes.add(doc_hash)


class UnstructuredProcessor:
    """Handles unstructured.io processing without n8n dependency"""
    
    def __init__(self, service_url: str = "http://unstructured-service:8880"):
        self.service_url = service_url
    
    async def process_document(self, content: bytes, filename: str, doc_type: str = None) -> Dict:
        """Process document through unstructured.io service"""
        try:
            # Convert to base64
            base64_content = base64.b64encode(content).decode('utf-8')
            
            # Call unstructured service
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.service_url}/parse_documents",
                    json={
                        "file_name": filename,
                        "input_base64": base64_content
                    }
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # For remote processing, we get back text arrays
                        # Convert to element-like structure for enhancement
                        elements = []
                        for text in result.get('structured_text', []):
                            # Create mock element
                            class MockElement:
                                def __init__(self, text):
                                    self.text = text
                                    self.category = 'NarrativeText'
                                    self.metadata = type('obj', (object,), {'legal': {}})()
                            
                            elements.append(MockElement(text))
                        
                        # Apply legal enhancements if we have elements
                        if elements and doc_type:
                            elements = enhance_legal_document(elements, doc_type)
                        
                        return {
                            'full_text': result.get('text', ''),
                            'structured_elements': result.get('structured_text', []),
                            'enhanced_elements': [
                                {
                                    'text': el.text,
                                    'legal_metadata': el.metadata.legal if hasattr(el.metadata, 'legal') else {}
                                }
                                for el in elements
                            ] if elements else [],
                            'processing_timestamp': datetime.utcnow().isoformat()
                        }
                    else:
                        logger.error(f"Unstructured service error: {response.status}")
                        return {}
        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            return {}
    
    async def process_local_file(self, file_path: str, doc_type: str = None) -> Dict:
        """Process a local file directly using unstructured library"""
        try:
            if not UNSTRUCTURED_AVAILABLE:
                logger.warning("Unstructured library not available, skipping local processing")
                return {}
            elements = partition(filename=file_path)
            
            # Apply legal enhancements
            enhanced_elements = enhance_legal_document(elements, doc_type)
            
            return {
                'full_text': "\n\n".join([str(el) for el in enhanced_elements]),
                'structured_elements': [
                    {
                        'type': el.__class__.__name__,
                        'text': str(el),
                        'metadata': el.metadata.to_dict() if hasattr(el, 'metadata') else {},
                        'legal_metadata': el.metadata.legal if hasattr(el.metadata, 'legal') else {}
                    }
                    for el in enhanced_elements
                ],
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Local unstructured processing failed: {e}")
            return {}


class UnifiedDocumentProcessor:
    """Main pipeline: CL → FLP → Unstructured → PostgreSQL"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        # FLPIntegration will need database connection when used
        self.flp_integration = None
        self.unstructured = UnstructuredProcessor()
        self.dedup_manager = DeduplicationManager()
    
    def _get_flp_integration(self):
        """Get or create FLP integration with database connection"""
        if not self.flp_integration:
            conn = get_db_connection()
            self.flp_integration = FLPIntegration(conn)
        return self.flp_integration
    
    async def process_courtlistener_batch(self, 
                                        court_id: Optional[str] = None,
                                        date_filed_after: Optional[str] = None,
                                        max_documents: int = 100) -> Dict:
        """Process a batch of documents from CourtListener"""
        stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'errors': 0,
            'processing_time': datetime.utcnow().isoformat()
        }
        
        try:
            # Fetch from CourtListener
            cl_documents = await self.cl_service.fetch_opinions(
                court_id=court_id,
                date_filed_after=date_filed_after,
                max_results=max_documents
            )
            stats['total_fetched'] = len(cl_documents)
            
            # Process each document
            for cl_doc in cl_documents:
                try:
                    # Check for duplicates first
                    if self.dedup_manager.is_duplicate(cl_doc):
                        stats['duplicates'] += 1
                        logger.info(f"Skipping duplicate: {cl_doc.get('id')}")
                        continue
                    
                    # Process through pipeline
                    processed_doc = await self.process_single_document(cl_doc)
                    
                    if processed_doc.get('saved_id'):
                        stats['new_documents'] += 1
                        self.dedup_manager.mark_processed(cl_doc)
                    else:
                        stats['errors'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing document {cl_doc.get('id')}: {e}")
                    stats['errors'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            stats['error'] = str(e)
            return stats
    
    async def process_single_document(self, cl_document: Dict) -> Dict:
        """Process a single document through the entire pipeline"""
        try:
            # Step 1: FLP Enhancement
            flp_enhanced = await self._flp_enhance(cl_document)
            
            # Step 2: Unstructured.io Processing
            if flp_enhanced.get('plain_text') or flp_enhanced.get('pdf_url'):
                structured_data = await self._unstructured_process(flp_enhanced)
                flp_enhanced['structured_elements'] = structured_data
            
            # Step 3: Save to PostgreSQL
            saved_id = await self._save_to_postgres(flp_enhanced)
            flp_enhanced['saved_id'] = saved_id
            
            return flp_enhanced
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            return {'error': str(e), 'cl_id': cl_document.get('id')}
    
    async def _flp_enhance(self, cl_document: Dict) -> Dict:
        """Enhance document with FLP tools"""
        enhanced = cl_document.copy()
        
        try:
            # Get plain text if available
            text_content = (cl_document.get('plain_text') or 
                          cl_document.get('html') or 
                          cl_document.get('html_lawbox') or 
                          cl_document.get('html_columbia', ''))
            
            if text_content:
                # Extract citations
                flp = self._get_flp_integration()
                citations = await flp.extract_citations(text_content)
                enhanced['citations'] = citations
                
                # Get judge information if available
                if cl_document.get('author_id'):
                    judge_info = await flp.get_judge_info(
                        cl_document['author_id']
                    )
                    enhanced['judge_info'] = judge_info
                
                # Enhance court information
                if cl_document.get('court_id'):
                    court_info = await flp.get_court_info(
                        cl_document['court_id']
                    )
                    enhanced['court_info'] = court_info
            
            enhanced['flp_processing_timestamp'] = datetime.utcnow().isoformat()
            
        except Exception as e:
            logger.error(f"FLP enhancement failed: {e}")
            enhanced['flp_error'] = str(e)
        
        return enhanced
    
    async def _unstructured_process(self, document: Dict) -> Dict:
        """Process document through unstructured.io"""
        try:
            # Try to detect document type from metadata
            doc_type = self._detect_document_type(document)
            
            # If we have a PDF URL, download it first
            if document.get('pdf_url') and not document.get('plain_text'):
                async with aiohttp.ClientSession() as session:
                    async with session.get(document['pdf_url']) as response:
                        if response.status == 200:
                            content = await response.read()
                            filename = f"opinion_{document.get('id', 'unknown')}.pdf"
                            return await self.unstructured.process_document(
                                content, filename, doc_type
                            )
            
            # If we have plain text, save it temporarily and process
            elif document.get('plain_text'):
                with tempfile.NamedTemporaryFile(
                    mode='w', 
                    suffix='.txt', 
                    delete=False
                ) as tmp_file:
                    tmp_file.write(document['plain_text'])
                    tmp_file.flush()
                    
                    result = await self.unstructured.process_local_file(
                        tmp_file.name, doc_type
                    )
                    os.unlink(tmp_file.name)
                    return result
            
            return {}
            
        except Exception as e:
            logger.error(f"Unstructured processing failed: {e}")
            return {'error': str(e)}
    
    def _detect_document_type(self, document: Dict) -> str:
        """Detect document type from CourtListener metadata"""
        # Check if it's a transcript based on source
        if document.get('source') == 'R' or 'transcript' in document.get('type', '').lower():
            return 'transcript'
        
        # Check for docket entries
        if document.get('type') == 'docket':
            return 'docket'
        
        # Check for orders
        if 'order' in document.get('case_name', '').lower():
            return 'order'
        
        # Default to opinion
        return 'opinion'
    
    async def _save_to_postgres(self, document: Dict) -> Optional[int]:
        """Save processed document to PostgreSQL"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Generate document hash
            doc_hash = self.dedup_manager.generate_hash(document)
            
            # Prepare data for insertion
            insert_data = {
                'cl_id': document.get('id'),
                'court_id': document.get('court_id'),
                'docket_number': document.get('docket_number'),
                'case_name': document.get('case_name'),
                'date_filed': document.get('date_filed'),
                'author_str': document.get('author_str'),
                'per_curiam': document.get('per_curiam', False),
                'type': document.get('type'),
                'plain_text': document.get('plain_text'),
                'html': document.get('html'),
                'pdf_url': document.get('pdf_url'),
                'citations': json.dumps(document.get('citations', [])),
                'judge_info': json.dumps(document.get('judge_info', {})),
                'court_info': json.dumps(document.get('court_info', {})),
                'structured_elements': json.dumps(
                    document.get('structured_elements', {})
                ),
                'document_hash': doc_hash,
                'cl_processing_timestamp': document.get('date_created'),
                'flp_processing_timestamp': document.get('flp_processing_timestamp'),
                'unstructured_processing_timestamp': document.get(
                    'structured_elements', {}
                ).get('processing_timestamp'),
                'created_at': datetime.utcnow()
            }
            
            # Insert into database
            cursor.execute("""
                INSERT INTO court_data.opinions_unified (
                    cl_id, court_id, docket_number, case_name, date_filed,
                    author_str, per_curiam, type, plain_text, html, pdf_url,
                    citations, judge_info, court_info, structured_elements,
                    document_hash, cl_processing_timestamp, 
                    flp_processing_timestamp, unstructured_processing_timestamp,
                    created_at
                ) VALUES (
                    %(cl_id)s, %(court_id)s, %(docket_number)s, %(case_name)s,
                    %(date_filed)s, %(author_str)s, %(per_curiam)s, %(type)s,
                    %(plain_text)s, %(html)s, %(pdf_url)s, %(citations)s,
                    %(judge_info)s, %(court_info)s, %(structured_elements)s,
                    %(document_hash)s, %(cl_processing_timestamp)s,
                    %(flp_processing_timestamp)s, 
                    %(unstructured_processing_timestamp)s, %(created_at)s
                ) RETURNING id
            """, insert_data)
            
            saved_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            logger.info(f"Saved document {document.get('id')} as {saved_id}")
            return saved_id
            
        except Exception as e:
            logger.error(f"PostgreSQL save failed: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return None


# API endpoints for testing and monitoring
async def process_batch_endpoint(
    court_id: Optional[str] = None,
    date_after: Optional[str] = None,
    max_documents: int = 100
):
    """API endpoint for batch processing"""
    processor = UnifiedDocumentProcessor()
    return await processor.process_courtlistener_batch(
        court_id=court_id,
        date_filed_after=date_after,
        max_documents=max_documents
    )