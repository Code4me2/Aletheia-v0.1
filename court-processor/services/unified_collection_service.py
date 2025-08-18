#!/usr/bin/env python3
"""
Unified Collection Service

This service integrates:
1. Enhanced Standalone Processor for content retrieval via Search API
2. ComprehensiveJudgeExtractor for judge attribution
3. Optional 11-stage pipeline for comprehensive enrichment
4. Database storage with deduplication

This is the main service that the CLI will use for document collection.
"""

import asyncio
import logging
import json
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our components
from services.enhanced_standalone_processor import EnhancedStandaloneProcessor, ProcessorConfig
from services.database import get_db_connection
from services.document_ingestion_service import DocumentIngestionService

# Import pipeline if available
try:
    from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
    PIPELINE_AVAILABLE = True
except ImportError:
    PIPELINE_AVAILABLE = False
    logging.warning("11-stage pipeline not available - proceeding without enrichment option")

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UnifiedCollectionService:
    """
    Unified service for comprehensive document collection and processing
    
    Features:
    - Flexible search parameters (court, judge, date, custom query)
    - Content retrieval via Search API
    - Comprehensive judge extraction
    - Optional 11-stage pipeline enrichment
    - PDF extraction fallback
    - Database storage with deduplication
    """
    
    def __init__(self, config: Optional[ProcessorConfig] = None):
        """
        Initialize unified collection service
        
        Args:
            config: Optional processor configuration
        """
        self.config = config or ProcessorConfig()
        self.standalone_processor = EnhancedStandaloneProcessor(self.config)
        self.pipeline = RobustElevenStagePipeline() if PIPELINE_AVAILABLE else None
        self.doc_ingestion_service = None  # Initialize when needed
        self.db_conn = None
        
        # Statistics tracking
        self.stats = {
            'total_processed': 0,
            'content_retrieved': 0,
            'judge_attributed': 0,
            'pipeline_enhanced': 0,
            'pdf_extracted': 0,
            'stored_to_db': 0,
            'errors': 0
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        try:
            self.db_conn = get_db_connection()
            self.doc_ingestion_service = DocumentIngestionService(
                api_key=self.config.courtlistener_api_key
            )
            await self.doc_ingestion_service.__aenter__()
        except Exception as e:
            logger.warning(f"Could not initialize all services: {str(e)}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.doc_ingestion_service:
            await self.doc_ingestion_service.__aexit__(exc_type, exc_val, exc_tb)
        if self.db_conn:
            self.db_conn.close()
    
    async def collect_documents(self,
                               court_id: Optional[str] = None,
                               judge_name: Optional[str] = None,
                               date_after: Optional[str] = None,
                               date_before: Optional[str] = None,
                               max_documents: int = 50,
                               custom_query: Optional[str] = None,
                               run_pipeline: bool = False,
                               extract_pdfs: bool = True,
                               store_to_db: bool = True) -> Dict[str, Any]:
        """
        Collect and process court documents with all enhancements
        
        Args:
            court_id: Court identifier (e.g., 'txed', 'ded', 'cafc')
            judge_name: Judge name to filter by
            date_after: Start date (YYYY-MM-DD)
            date_before: End date (YYYY-MM-DD)  
            max_documents: Maximum documents to collect
            custom_query: Additional search query
            run_pipeline: Whether to run 11-stage pipeline enrichment
            extract_pdfs: Whether to attempt PDF extraction for empty content
            store_to_db: Whether to store results in database
            
        Returns:
            Collection results with statistics and documents
        """
        
        results = {
            'success': True,
            'documents': [],
            'statistics': {
                'total_fetched': 0,
                'new_documents': 0,
                'duplicates': 0,
                'with_content': 0,
                'with_judges': 0,
                'pipeline_enhanced': 0,
                'pdf_extracted': 0,
                'stored_to_db': 0,
                'errors': 0
            },
            'performance': {
                'fetch_time': 0,
                'pipeline_time': 0,
                'storage_time': 0,
                'total_time': 0
            },
            'errors': []
        }
        
        start_time = datetime.now()
        
        try:
            # Step 1: Fetch documents using enhanced standalone processor
            logger.info("="*60)
            logger.info("STEP 1: Fetching documents via Search API")
            logger.info("="*60)
            
            fetch_start = datetime.now()
            
            processor_results = await self.standalone_processor.process_court_documents(
                court_id=court_id,
                judge_name=judge_name,
                date_after=date_after,
                date_before=date_before,
                max_documents=max_documents,
                custom_query=custom_query,
                extract_judges=True  # Always extract judges
            )
            
            results['performance']['fetch_time'] = (datetime.now() - fetch_start).total_seconds()
            
            # Update statistics
            results['statistics']['total_fetched'] = processor_results['total_fetched']
            results['statistics']['new_documents'] = processor_results['new_documents']
            results['statistics']['duplicates'] = processor_results['duplicates']
            results['statistics']['errors'] = processor_results['errors']
            
            documents = processor_results['documents']
            
            logger.info(f"Fetched {len(documents)} documents")
            logger.info(f"Judge attribution rate: {processor_results.get('judge_attribution_rate', 0):.1f}%")
            logger.info(f"Content extraction rate: {processor_results.get('content_extraction_rate', 0):.1f}%")
            
            # Step 2: PDF extraction for documents without content
            if extract_pdfs and self.doc_ingestion_service and documents:
                logger.info("\n" + "="*60)
                logger.info("STEP 2: PDF Extraction for Empty Content")
                logger.info("="*60)
                
                pdf_count = 0
                for doc in documents:
                    if not doc.get('content') or doc['content'].startswith('[PDF available:'):
                        # Try to extract from PDF
                        pdf_url = doc.get('meta', {}).get('download_url')
                        if pdf_url:
                            try:
                                logger.info(f"Attempting PDF extraction for {doc.get('meta', {}).get('case_name', 'Unknown')}")
                                
                                # Use document ingestion service for PDF extraction
                                text_content = await self.doc_ingestion_service._download_and_extract_pdf(pdf_url)
                                
                                if text_content:
                                    doc['content'] = text_content
                                    doc['meta']['pdf_extracted'] = True
                                    doc['meta']['content_length'] = len(text_content)
                                    doc['meta']['has_content'] = True
                                    pdf_count += 1
                                    results['statistics']['pdf_extracted'] += 1
                                    logger.info(f"  ✓ Extracted {len(text_content)} characters from PDF")
                                else:
                                    logger.warning(f"  ✗ PDF extraction failed")
                                    
                            except Exception as e:
                                logger.error(f"PDF extraction error: {str(e)}")
                                
                logger.info(f"PDF extraction complete: {pdf_count} documents enhanced")
            
            # Step 3: Run 11-stage pipeline if requested
            if run_pipeline and self.pipeline and documents:
                logger.info("\n" + "="*60)
                logger.info("STEP 3: 11-Stage Pipeline Enhancement")
                logger.info("="*60)
                
                pipeline_start = datetime.now()
                
                try:
                    # Convert documents to pipeline format
                    pipeline_docs = []
                    for doc in documents:
                        pipeline_doc = {
                            'id': doc.get('id'),
                            'case_number': doc.get('meta', {}).get('case_number', ''),
                            'case_name': doc.get('meta', {}).get('case_name', ''),
                            'content': doc.get('content', ''),
                            'metadata': doc.get('meta', {}),
                            'document_type': doc.get('meta', {}).get('document_type', 'opinion')
                        }
                        pipeline_docs.append(pipeline_doc)
                    
                    # Run pipeline using in-memory processing
                    pipeline_results = await self.pipeline.process_documents_in_memory(
                        pipeline_docs,
                        validate_strict=False
                    )
                    
                    # Merge pipeline enhancements back
                    enhanced_docs = pipeline_results.get('documents', [])
                    for i, enhanced in enumerate(enhanced_docs):
                        if i < len(documents):
                            # Merge enhanced metadata
                            documents[i]['meta'].update(enhanced.get('metadata', {}))
                            # Update content if enhanced
                            if enhanced.get('content'):
                                documents[i]['content'] = enhanced['content']
                    
                    results['statistics']['pipeline_enhanced'] = len(enhanced_docs)
                    results['performance']['pipeline_time'] = (datetime.now() - pipeline_start).total_seconds()
                    
                    logger.info(f"Pipeline enhancement complete: {len(enhanced_docs)} documents")
                    logger.info(f"Pipeline statistics:")
                    for key, value in pipeline_results.get('statistics', {}).items():
                        logger.info(f"  {key}: {value}")
                        
                except Exception as e:
                    logger.error(f"Pipeline enhancement failed: {str(e)}")
                    results['errors'].append(f"Pipeline error: {str(e)}")
            
            # Step 4: Store to database
            if store_to_db and self.db_conn and documents:
                logger.info("\n" + "="*60)
                logger.info("STEP 4: Database Storage")
                logger.info("="*60)
                
                storage_start = datetime.now()
                stored_count = 0
                
                try:
                    cursor = self.db_conn.cursor()
                    
                    for doc in documents:
                        try:
                            # Check if document already exists
                            case_number = doc.get('meta', {}).get('case_number', '')
                            doc_type = doc.get('meta', {}).get('document_type', 'opinion')
                            
                            if case_number:
                                cursor.execute("""
                                    SELECT id FROM court_documents 
                                    WHERE case_number = %s AND document_type = %s
                                """, (case_number, doc_type))
                                
                                existing = cursor.fetchone()
                                
                                if existing:
                                    # Update existing document
                                    cursor.execute("""
                                        UPDATE court_documents
                                        SET content = %s,
                                            metadata = %s,
                                            updated_at = NOW()
                                        WHERE id = %s
                                    """, (
                                        doc.get('content', ''),
                                        json.dumps(doc.get('meta', {})),
                                        existing[0]
                                    ))
                                    logger.info(f"Updated existing document: {case_number}")
                                else:
                                    # Insert new document
                                    cursor.execute("""
                                        INSERT INTO court_documents 
                                        (case_number, case_name, document_type, content, metadata, created_at, updated_at)
                                        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                                    """, (
                                        case_number,
                                        doc.get('meta', {}).get('case_name', ''),
                                        doc_type,
                                        doc.get('content', ''),
                                        json.dumps(doc.get('meta', {}))
                                    ))
                                    logger.info(f"Stored new document: {case_number}")
                                
                                stored_count += 1
                                
                        except Exception as e:
                            logger.error(f"Failed to store document: {str(e)}")
                            results['statistics']['errors'] += 1
                    
                    self.db_conn.commit()
                    results['statistics']['stored_to_db'] = stored_count
                    results['performance']['storage_time'] = (datetime.now() - storage_start).total_seconds()
                    
                    logger.info(f"Database storage complete: {stored_count} documents")
                    
                except Exception as e:
                    logger.error(f"Database storage failed: {str(e)}")
                    results['errors'].append(f"Storage error: {str(e)}")
                    if self.db_conn:
                        self.db_conn.rollback()
            
            # Update final statistics
            results['documents'] = documents
            results['statistics']['with_content'] = sum(
                1 for doc in documents 
                if doc.get('content') and not doc['content'].startswith('[PDF available:')
            )
            results['statistics']['with_judges'] = sum(
                1 for doc in documents 
                if doc.get('meta', {}).get('judge_name')
            )
            
            results['performance']['total_time'] = (datetime.now() - start_time).total_seconds()
            
            # Summary logging
            logger.info("\n" + "="*60)
            logger.info("COLLECTION SUMMARY")
            logger.info("="*60)
            logger.info(f"Total documents collected: {len(documents)}")
            logger.info(f"Documents with content: {results['statistics']['with_content']}")
            logger.info(f"Documents with judges: {results['statistics']['with_judges']}")
            logger.info(f"PDF extractions: {results['statistics']['pdf_extracted']}")
            logger.info(f"Pipeline enhancements: {results['statistics']['pipeline_enhanced']}")
            logger.info(f"Stored to database: {results['statistics']['stored_to_db']}")
            logger.info(f"Total time: {results['performance']['total_time']:.2f}s")
            
            return results
            
        except Exception as e:
            logger.error(f"Collection failed: {str(e)}")
            results['success'] = False
            results['errors'].append(str(e))
            results['performance']['total_time'] = (datetime.now() - start_time).total_seconds()
            return results
    
    async def reprocess_empty_documents(self, limit: int = 100) -> Dict[str, Any]:
        """
        Find and reprocess documents that have no content
        
        This can recover documents that were ingested when the API wasn't providing content
        
        Args:
            limit: Maximum documents to reprocess
            
        Returns:
            Reprocessing results
        """
        results = {
            'success': True,
            'processed': 0,
            'enhanced': 0,
            'errors': 0
        }
        
        if not self.db_conn:
            logger.error("No database connection available")
            results['success'] = False
            return results
        
        try:
            cursor = self.db_conn.cursor()
            
            # Find empty documents
            cursor.execute("""
                SELECT id, case_number, case_name, document_type, metadata
                FROM court_documents
                WHERE (content IS NULL OR content = '' OR LENGTH(content) < 100)
                AND metadata IS NOT NULL
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            empty_docs = cursor.fetchall()
            logger.info(f"Found {len(empty_docs)} empty documents to reprocess")
            
            for doc_id, case_number, case_name, doc_type, metadata in empty_docs:
                try:
                    meta = json.loads(metadata) if isinstance(metadata, str) else metadata
                    
                    # Try to re-fetch using case information
                    logger.info(f"Reprocessing: {case_number}")
                    
                    # Search for the document again
                    processor_results = await self.standalone_processor.process_court_documents(
                        court_id=meta.get('court_id'),
                        custom_query=f'caseName:"{case_name}"' if case_name else None,
                        max_documents=1,
                        extract_judges=True
                    )
                    
                    if processor_results['documents']:
                        new_doc = processor_results['documents'][0]
                        
                        # Update database with new content
                        if new_doc.get('content'):
                            cursor.execute("""
                                UPDATE court_documents
                                SET content = %s,
                                    metadata = metadata || %s,
                                    updated_at = NOW()
                                WHERE id = %s
                            """, (
                                new_doc['content'],
                                json.dumps({
                                    'reprocessed': True,
                                    'reprocessed_at': datetime.utcnow().isoformat(),
                                    'content_length': len(new_doc['content'])
                                }),
                                doc_id
                            ))
                            
                            self.db_conn.commit()
                            results['enhanced'] += 1
                            logger.info(f"  ✓ Enhanced with {len(new_doc['content'])} chars")
                        else:
                            logger.info(f"  ✗ No content found")
                    
                    results['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Failed to reprocess document {doc_id}: {str(e)}")
                    results['errors'] += 1
                
                # Rate limiting
                await asyncio.sleep(0.5)
            
            logger.info(f"Reprocessing complete: {results['enhanced']}/{results['processed']} documents enhanced")
            
        except Exception as e:
            logger.error(f"Reprocessing failed: {str(e)}")
            results['success'] = False
        
        return results


# Convenience function for CLI integration
async def collect_with_unified_service(
    court_id: Optional[str] = None,
    judge_name: Optional[str] = None,
    date_after: Optional[str] = None,
    date_before: Optional[str] = None,
    limit: int = 50,
    enhance: bool = False,
    extract_pdfs: bool = True,
    store: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for CLI integration
    
    This can be called directly from the CLI collect command
    """
    async with UnifiedCollectionService() as service:
        return await service.collect_documents(
            court_id=court_id,
            judge_name=judge_name,
            date_after=date_after,
            date_before=date_before,
            max_documents=limit,
            run_pipeline=enhance,
            extract_pdfs=extract_pdfs,
            store_to_db=store
        )


# Testing
async def test_unified_service():
    """Test the unified collection service"""
    
    print("\n" + "="*60)
    print("Testing Unified Collection Service")
    print("="*60)
    
    async with UnifiedCollectionService() as service:
        # Test basic collection
        results = await service.collect_documents(
            court_id='txed',
            date_after='2024-01-01',
            max_documents=2,
            run_pipeline=False,  # Skip pipeline for quick test
            store_to_db=False    # Don't store during test
        )
        
        print(f"\n✅ Collection Results:")
        print(f"  Total fetched: {results['statistics']['total_fetched']}")
        print(f"  With content: {results['statistics']['with_content']}")
        print(f"  With judges: {results['statistics']['with_judges']}")
        print(f"  Processing time: {results['performance']['total_time']:.2f}s")
        
        if results['documents']:
            doc = results['documents'][0]
            meta = doc.get('meta', {})
            print(f"\n📄 Sample Document:")
            print(f"  Case: {meta.get('case_name', 'Unknown')}")
            print(f"  Judge: {meta.get('judge_name', 'Unknown')} ({meta.get('judge_confidence', 0):.2f} confidence)")
            print(f"  Content length: {len(doc.get('content', ''))}")
            print(f"  Document type: {meta.get('document_type', 'Unknown')}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_unified_service())