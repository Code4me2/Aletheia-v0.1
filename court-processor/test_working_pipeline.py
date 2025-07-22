#!/usr/bin/env python3
"""
Test the working pipeline with proper Docker integration
Uses actual database schema and service configuration
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any
import json
import aiohttp

# Import our new service configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from services.service_config import SERVICES, IS_DOCKER
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkingPipeline:
    """
    A working version of the pipeline that uses actual services and schema
    """
    
    def __init__(self):
        self.db_conn = get_db_connection()
        self.results = {
            'stages_completed': [],
            'total_enhancements': 0,
            'processing_time': 0,
            'documents_processed': 0
        }
    
    async def run_pipeline(self, sample_size: int = 5) -> Dict[str, Any]:
        """Run the pipeline with actual working components"""
        start_time = datetime.now()
        
        try:
            # Stage 1: Fetch documents from actual schema
            logger.info("Stage 1: Document Retrieval from opinions_unified")
            documents = self._fetch_real_documents(sample_size)
            self.results['stages_completed'].append('Document Retrieval')
            self.results['documents_processed'] = len(documents)
            logger.info(f"  Found {len(documents)} documents")
            
            if not documents:
                # Try alternate schema if opinions_unified is empty
                logger.info("  No documents in opinions_unified, trying public.court_documents")
                documents = self._fetch_from_court_documents_table(sample_size)
                
            # Stage 2: Test FLP components (these we know work)
            logger.info("Stage 2: FLP Component Testing")
            flp_results = await self._test_flp_components(documents)
            self.results['stages_completed'].append('FLP Components')
            
            # Stage 3: Test Haystack connectivity
            logger.info("Stage 3: Haystack Service Check")
            haystack_status = await self._check_haystack_service()
            self.results['stages_completed'].append('Haystack Check')
            
            # Stage 4: Test Doctor connectivity (if needed)
            logger.info("Stage 4: Doctor Service Check")
            doctor_status = await self._check_doctor_service()
            self.results['stages_completed'].append('Doctor Check')
            
            # Calculate results
            end_time = datetime.now()
            self.results['processing_time'] = (end_time - start_time).total_seconds()
            
            return {
                'pipeline_name': 'Working Pipeline Test',
                'docker_environment': IS_DOCKER,
                'stages_completed': self.results['stages_completed'],
                'documents_found': self.results['documents_processed'],
                'services': {
                    'database': 'connected',
                    'haystack': haystack_status,
                    'doctor': doctor_status,
                    'flp_components': flp_results
                },
                'processing_time_seconds': self.results['processing_time'],
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'stages_completed': self.results['stages_completed']
            }
        finally:
            if self.db_conn:
                self.db_conn.close()
    
    def _fetch_real_documents(self, sample_size: int) -> List[Dict[str, Any]]:
        """Fetch documents from opinions_unified table"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # First check if table exists and has data
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM court_data.opinions_unified
                """)
                count = cursor.fetchone()['count']
                logger.info(f"  opinions_unified has {count} total documents")
                
                if count == 0:
                    return []
                
                # Fetch sample documents
                cursor.execute("""
                    SELECT id, cl_id, court_id, case_name, date_filed, 
                           plain_text, citations, judge_info, court_info
                    FROM court_data.opinions_unified
                    WHERE plain_text IS NOT NULL 
                    AND LENGTH(plain_text) > 1000
                    LIMIT %s
                """, (sample_size,))
                
                documents = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    doc['content'] = doc.get('plain_text', '')
                    doc['metadata'] = {
                        'court_id': doc.get('court_id'),
                        'case_name': doc.get('case_name'),
                        'date_filed': str(doc.get('date_filed')) if doc.get('date_filed') else None
                    }
                    documents.append(doc)
                
                return documents
                
        except Exception as e:
            logger.error(f"Error fetching from opinions_unified: {e}")
            return []
    
    def _fetch_from_court_documents_table(self, sample_size: int) -> List[Dict[str, Any]]:
        """Fallback: fetch from court_documents table"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, case_number, document_type, content, 
                           metadata, created_at
                    FROM public.court_documents
                    WHERE content IS NOT NULL
                    AND LENGTH(content) > 1000
                    LIMIT %s
                """, (sample_size,))
                
                documents = []
                for row in cursor.fetchall():
                    doc = dict(row)
                    # content field is already named 'content'
                    doc['metadata'] = doc.get('metadata', {})
                    documents.append(doc)
                
                logger.info(f"  Found {len(documents)} documents in court_documents table")
                return documents
                
        except Exception as e:
            logger.error(f"Error fetching from opinions table: {e}")
            return []
    
    async def _test_flp_components(self, documents: List[Dict]) -> Dict[str, Any]:
        """Test FLP components that we know work"""
        results = {}
        
        try:
            # Test courts-db
            from courts_db import find_court
            test_court = "Eastern District of Texas"
            court_ids = find_court(test_court)
            results['courts_db'] = {
                'working': True,
                'test_result': f"Found {len(court_ids)} matches for '{test_court}'"
            }
        except Exception as e:
            results['courts_db'] = {'working': False, 'error': str(e)}
        
        try:
            # Test eyecite
            from eyecite import get_citations
            if documents and documents[0].get('content'):
                citations = get_citations(documents[0]['content'][:1000])
                results['eyecite'] = {
                    'working': True,
                    'test_result': f"Found {len(citations)} citations in first document"
                }
            else:
                results['eyecite'] = {'working': True, 'test_result': 'No documents to test'}
        except Exception as e:
            results['eyecite'] = {'working': False, 'error': str(e)}
        
        try:
            # Test reporters-db
            from reporters_db import REPORTERS
            results['reporters_db'] = {
                'working': True,
                'test_result': f"Loaded {len(REPORTERS)} reporters"
            }
        except Exception as e:
            results['reporters_db'] = {'working': False, 'error': str(e)}
        
        return results
    
    async def _check_haystack_service(self) -> Dict[str, Any]:
        """Check Haystack service connectivity"""
        try:
            async with aiohttp.ClientSession() as session:
                health_url = SERVICES['haystack']['endpoints']['health']
                logger.info(f"  Checking Haystack at: {health_url}")
                
                async with session.get(health_url, timeout=5) as response:
                    if response.status == 200:
                        return {
                            'status': 'connected',
                            'url': SERVICES['haystack']['url'],
                            'health_check': 'passed'
                        }
                    else:
                        return {
                            'status': 'error',
                            'url': SERVICES['haystack']['url'],
                            'http_status': response.status
                        }
        except Exception as e:
            return {
                'status': 'error',
                'url': SERVICES['haystack']['url'],
                'error': str(e)
            }
    
    async def _check_doctor_service(self) -> Dict[str, Any]:
        """Check Doctor service connectivity"""
        try:
            async with aiohttp.ClientSession() as session:
                # Doctor doesn't have a health endpoint, so we'll check the base URL
                base_url = SERVICES['doctor']['url']
                logger.info(f"  Checking Doctor at: {base_url}")
                
                async with session.get(base_url, timeout=5) as response:
                    return {
                        'status': 'connected' if response.status < 500 else 'error',
                        'url': base_url,
                        'http_status': response.status
                    }
        except Exception as e:
            return {
                'status': 'error',
                'url': SERVICES['doctor']['url'],
                'error': str(e)
            }

async def main():
    """Run the working pipeline test"""
    pipeline = WorkingPipeline()
    results = await pipeline.run_pipeline(sample_size=3)
    
    print("=" * 80)
    print("WORKING PIPELINE TEST RESULTS")
    print("=" * 80)
    print(f"Environment: {'Docker' if IS_DOCKER else 'Local'}")
    print(f"Success: {results.get('success')}")
    print(f"Stages Completed: {len(results.get('stages_completed', []))}")
    
    if results.get('services'):
        print("\nService Status:")
        for service, status in results['services'].items():
            print(f"  {service}: {status}")
    
    if results.get('error'):
        print(f"\nError: {results['error']}")
    
    print(f"\nProcessing Time: {results.get('processing_time_seconds', 0):.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())