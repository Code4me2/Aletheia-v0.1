#!/usr/bin/env python3
"""
Unified Test Suite for Court Processor Pipeline

This is the main entry point for all pipeline testing.
Provides a clear, organized way to test the entire system.
"""

import asyncio
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.courtlistener_service import CourtListenerService
from services.database import get_db_connection
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PipelineTestSuite:
    """Comprehensive test suite for the court processor pipeline"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests_run': 0,
            'tests_passed': 0,
            'tests_failed': 0,
            'details': {}
        }
    
    async def test_courtlistener_connection(self) -> bool:
        """Test 1: Verify CourtListener API connection"""
        test_name = "courtlistener_connection"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 1: CourtListener API Connection")
        logger.info(f"{'='*60}")
        
        try:
            service = CourtListenerService()
            
            # Test with a simple query
            results = await service.fetch_opinions(
                court_id='scotus',
                max_results=1
            )
            
            if results:
                logger.info(f"✅ Successfully connected to CourtListener API")
                logger.info(f"   Retrieved {len(results)} test document(s)")
                self.results['details'][test_name] = {
                    'status': 'PASSED',
                    'message': f'Retrieved {len(results)} documents',
                    'api_key_present': bool(service.api_key)
                }
                await service.close()
                return True
            else:
                logger.error("❌ No results from CourtListener API")
                self.results['details'][test_name] = {
                    'status': 'FAILED',
                    'message': 'No results returned'
                }
                await service.close()
                return False
                
        except Exception as e:
            logger.error(f"❌ CourtListener connection failed: {e}")
            self.results['details'][test_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    async def test_courtlistener_to_database(self) -> bool:
        """Test 2: Fetch from CourtListener and store in database"""
        test_name = "courtlistener_to_database"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 2: CourtListener → Database Flow")
        logger.info(f"{'='*60}")
        
        try:
            # Fetch fresh data from CourtListener
            service = CourtListenerService()
            cl_docs = await service.fetch_opinions(
                date_filed_after='2024-01-01',
                max_results=5
            )
            await service.close()
            
            if not cl_docs:
                logger.warning("No documents fetched from CourtListener")
                self.results['details'][test_name] = {
                    'status': 'SKIPPED',
                    'message': 'No documents available from CourtListener'
                }
                return False
            
            # Store in database
            conn = get_db_connection()
            cursor = conn.cursor()
            
            stored_count = 0
            for doc in cl_docs:
                try:
                    # Create case number from document data
                    case_number = f"CL-{doc.get('id', 'unknown')}"
                    
                    # Store document
                    # First check if document exists
                    cursor.execute("""
                        SELECT id FROM public.court_documents 
                        WHERE case_number = %s
                    """, (case_number,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing
                        cursor.execute("""
                            UPDATE public.court_documents 
                            SET metadata = %s,
                                updated_at = NOW()
                            WHERE case_number = %s
                            RETURNING id
                        """, (
                            json.dumps({
                                'source': 'courtlistener',
                                'cl_id': doc.get('id'),
                                'court': doc.get('court'),
                                'date_filed': doc.get('date_filed'),
                                'case_name': doc.get('case_name'),
                                'cluster': doc.get('cluster')
                            }),
                            case_number
                        ))
                    else:
                        # Insert new
                        cursor.execute("""
                            INSERT INTO public.court_documents 
                            (case_number, document_type, content, metadata, created_at)
                            VALUES (%s, %s, %s, %s, NOW())
                            RETURNING id
                        """, (
                        case_number,
                        'opinion',
                        doc.get('plain_text', doc.get('html', ''))[:1000],  # Sample content
                        json.dumps({
                            'source': 'courtlistener',
                            'cl_id': doc.get('id'),
                            'court': doc.get('court'),
                            'date_filed': doc.get('date_filed'),
                            'case_name': doc.get('case_name'),
                            'cluster': doc.get('cluster')
                        })
                    ))
                    stored_count += 1
                except Exception as e:
                    logger.error(f"Failed to store document: {e}")
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Stored {stored_count}/{len(cl_docs)} documents in database")
            
            self.results['details'][test_name] = {
                'status': 'PASSED' if stored_count > 0 else 'FAILED',
                'fetched': len(cl_docs),
                'stored': stored_count
            }
            
            return stored_count > 0
            
        except Exception as e:
            logger.error(f"❌ Database storage failed: {e}")
            self.results['details'][test_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    async def test_pipeline_processing(self) -> bool:
        """Test 3: Process documents through the pipeline"""
        test_name = "pipeline_processing"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 3: Pipeline Processing")
        logger.info(f"{'='*60}")
        
        try:
            pipeline = RobustElevenStagePipeline()
            results = await pipeline.process_batch(limit=5)
            
            if results['success']:
                stats = results['statistics']
                logger.info(f"✅ Pipeline processed successfully")
                logger.info(f"   Documents: {stats['documents_processed']}")
                logger.info(f"   Courts resolved: {stats['courts_resolved']}")
                logger.info(f"   Citations extracted: {stats['citations_extracted']}")
                
                self.results['details'][test_name] = {
                    'status': 'PASSED',
                    'documents_processed': stats['documents_processed'],
                    'completeness': results['verification']['completeness_score'],
                    'quality': results['verification']['quality_score']
                }
                return True
            else:
                logger.error(f"❌ Pipeline failed: {results.get('error')}")
                self.results['details'][test_name] = {
                    'status': 'FAILED',
                    'error': results.get('error')
                }
                return False
                
        except Exception as e:
            logger.error(f"❌ Pipeline processing failed: {e}")
            self.results['details'][test_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    async def test_haystack_storage(self) -> bool:
        """Test 4: Verify Haystack integration"""
        test_name = "haystack_storage"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 4: Haystack Storage Verification")
        logger.info(f"{'='*60}")
        
        try:
            # Check if Haystack is accessible
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://haystack-service:8000/health') as resp:
                    if resp.status == 200:
                        logger.info("✅ Haystack service is healthy")
                        
                        # Run pipeline with Haystack integration
                        pipeline = RobustElevenStagePipeline()
                        results = await pipeline.process_batch(limit=2)
                        
                        if results['success'] and results.get('haystack_results', {}).get('indexed_count', 0) > 0:
                            logger.info(f"✅ Documents indexed to Haystack: {results['haystack_results']['indexed_count']}")
                            self.results['details'][test_name] = {
                                'status': 'PASSED',
                                'indexed': results['haystack_results']['indexed_count']
                            }
                            return True
                        else:
                            logger.warning("⚠️ No documents indexed to Haystack")
                            self.results['details'][test_name] = {
                                'status': 'WARNING',
                                'message': 'Pipeline succeeded but no Haystack indexing'
                            }
                            return False
                    else:
                        logger.error("❌ Haystack service not available")
                        self.results['details'][test_name] = {
                            'status': 'FAILED',
                            'message': 'Haystack service not healthy'
                        }
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Haystack test failed: {e}")
            self.results['details'][test_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    async def test_end_to_end(self) -> bool:
        """Test 5: Complete end-to-end flow"""
        test_name = "end_to_end"
        logger.info(f"\n{'='*60}")
        logger.info(f"TEST 5: End-to-End Flow")
        logger.info(f"{'='*60}")
        
        try:
            # 1. Fetch from CourtListener
            logger.info("Step 1: Fetching from CourtListener...")
            service = CourtListenerService()
            cl_docs = await service.fetch_opinions(
                date_filed_after='2024-01-01',
                max_results=2
            )
            await service.close()
            
            if not cl_docs:
                self.results['details'][test_name] = {
                    'status': 'SKIPPED',
                    'message': 'No documents from CourtListener'
                }
                return False
            
            # 2. Store in database
            logger.info("Step 2: Storing in database...")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            doc_ids = []
            for doc in cl_docs:
                case_number = f"E2E-TEST-{doc.get('id', 'unknown')}"
                
                # Check if exists
                cursor.execute("""
                    SELECT id FROM public.court_documents 
                    WHERE case_number = %s
                """, (case_number,))
                existing = cursor.fetchone()
                
                if existing:
                    # Update
                    cursor.execute("""
                        UPDATE public.court_documents 
                        SET metadata = %s,
                            content = %s,
                            updated_at = NOW()
                        WHERE case_number = %s
                        RETURNING id
                    """, (
                        json.dumps({
                            'source': 'courtlistener_e2e_test',
                            'cl_id': doc.get('id'),
                            'court': doc.get('court'),
                            'cluster': doc.get('cluster')
                        }),
                        doc.get('plain_text', doc.get('html', ''))[:5000],
                        case_number
                    ))
                    doc_ids.append(cursor.fetchone()[0])
                else:
                    # Insert
                    cursor.execute("""
                        INSERT INTO public.court_documents 
                        (case_number, document_type, content, metadata, created_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        RETURNING id
                    """, (
                    case_number,
                    'opinion',
                    doc.get('plain_text', doc.get('html', ''))[:5000],
                    json.dumps({
                        'source': 'courtlistener_e2e_test',
                        'cl_id': doc.get('id'),
                        'court': doc.get('court'),
                        'cluster': doc.get('cluster')
                    })
                ))
                doc_ids.append(cursor.fetchone()[0])
            
            conn.commit()
            
            # 3. Process through pipeline
            logger.info("Step 3: Processing through pipeline...")
            pipeline = RobustElevenStagePipeline()
            
            # Process specifically our test documents
            cursor.execute("""
                SELECT COUNT(*) FROM public.court_documents
                WHERE id = ANY(%s)
            """, (doc_ids,))
            count = cursor.fetchone()[0]
            
            conn.close()
            
            results = await pipeline.process_batch(limit=10)  # Process recent docs including ours
            
            if results['success']:
                logger.info("✅ End-to-end test completed successfully")
                logger.info(f"   Fetched: {len(cl_docs)} documents")
                logger.info(f"   Stored: {len(doc_ids)} documents")
                logger.info(f"   Processed: {results['statistics']['documents_processed']} documents")
                
                self.results['details'][test_name] = {
                    'status': 'PASSED',
                    'courtlistener_docs': len(cl_docs),
                    'stored_docs': len(doc_ids),
                    'processed_docs': results['statistics']['documents_processed'],
                    'pipeline_completeness': results['verification']['completeness_score']
                }
                return True
            else:
                logger.error("❌ Pipeline processing failed in E2E test")
                self.results['details'][test_name] = {
                    'status': 'FAILED',
                    'error': 'Pipeline processing failed'
                }
                return False
                
        except Exception as e:
            logger.error(f"❌ End-to-end test failed: {e}")
            self.results['details'][test_name] = {
                'status': 'FAILED',
                'error': str(e)
            }
            return False
    
    async def run_all_tests(self):
        """Run all tests in sequence"""
        logger.info(f"\n{'='*80}")
        logger.info(f"COURT PROCESSOR PIPELINE TEST SUITE")
        logger.info(f"{'='*80}")
        logger.info(f"Starting at: {datetime.now()}")
        
        tests = [
            self.test_courtlistener_connection,
            self.test_courtlistener_to_database,
            self.test_pipeline_processing,
            self.test_haystack_storage,
            self.test_end_to_end
        ]
        
        for test_func in tests:
            self.results['tests_run'] += 1
            try:
                if await test_func():
                    self.results['tests_passed'] += 1
                else:
                    self.results['tests_failed'] += 1
            except Exception as e:
                logger.error(f"Test {test_func.__name__} crashed: {e}")
                self.results['tests_failed'] += 1
        
        # Summary
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST SUITE SUMMARY")
        logger.info(f"{'='*80}")
        logger.info(f"Total tests run: {self.results['tests_run']}")
        logger.info(f"Passed: {self.results['tests_passed']}")
        logger.info(f"Failed: {self.results['tests_failed']}")
        
        # Save results
        with open('test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nDetailed results saved to: test_results.json")
        
        return self.results['tests_failed'] == 0


async def main():
    """Main entry point"""
    suite = PipelineTestSuite()
    success = await suite.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    if not os.getenv('DATABASE_URL'):
        print("\nERROR: Must run inside Docker container")
        print("Usage: docker-compose exec court-processor python test_suite.py")
        sys.exit(1)
    
    asyncio.run(main())