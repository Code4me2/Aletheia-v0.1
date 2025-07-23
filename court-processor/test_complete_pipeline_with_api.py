#!/usr/bin/env python3
"""
Complete Pipeline Test with Real CourtListener API Data
Tests: API → Enhancement → PostgreSQL → Haystack
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
from psycopg2.extras import RealDictCursor

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from services.service_config import SERVICES
from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# CourtListener API configuration
COURTLISTENER_API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
COURTLISTENER_BASE_URL = "https://www.courtlistener.com/api/rest/v4"


class CompletePipelineTest:
    """Test complete pipeline with real CourtListener data"""
    
    def __init__(self):
        self.api_token = COURTLISTENER_API_TOKEN
        self.stats = {
            'api_documents_fetched': 0,
            'documents_enhanced': 0,
            'documents_stored': 0,
            'documents_indexed': 0,
            'total_citations': 0,
            'total_enhancements': 0
        }
    
    async def fetch_recent_opinions(self, 
                                  court: str = 'txed',
                                  days_back: int = 30,
                                  limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent opinions from CourtListener API"""
        logger.info(f"Fetching recent opinions from {court} (last {days_back} days)")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # API parameters for V4
        params = {
            'court__id': court,  # V4 uses court__id
            'cluster__date_filed__gte': start_date.strftime('%Y-%m-%d'),
            'cluster__date_filed__lte': end_date.strftime('%Y-%m-%d'),
            'order_by': '-cluster__date_filed',
            'page_size': limit
        }
        
        headers = {
            'Authorization': f'Token {self.api_token}'
        }
        
        documents = []
        url = f"{COURTLISTENER_BASE_URL}/search/"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        # Process results to match our pipeline format
                        for result in results[:limit]:
                            # Fetch full opinion details if needed
                            if result.get('absolute_url'):
                                opinion_url = f"{COURTLISTENER_BASE_URL}/opinions/{result.get('id')}/"
                                async with session.get(opinion_url, headers=headers) as op_response:
                                    if op_response.status == 200:
                                        opinion_data = await op_response.json()
                                        
                                        # Format for our pipeline
                                        doc = {
                                            'id': str(opinion_data.get('id')),
                                            'case_number': opinion_data.get('docket', {}).get('docket_number', ''),
                                            'case_name': result.get('caseName', ''),
                                            'document_type': 'opinion',
                                            'content': opinion_data.get('plain_text', '') or opinion_data.get('html', ''),
                                            'metadata': {
                                                'court_id': court,
                                                'court_name': result.get('court_citation_string', ''),
                                                'date_filed': result.get('dateFiled'),
                                                'judge_name': opinion_data.get('author_str', ''),
                                                'citation': result.get('citation', []),
                                                'docket_id': opinion_data.get('docket'),
                                                'cluster_id': opinion_data.get('cluster'),
                                                'source': 'courtlistener_api'
                                            },
                                            'created_at': datetime.now()
                                        }
                                        
                                        if doc['content']:  # Only add if we have content
                                            documents.append(doc)
                                            self.stats['api_documents_fetched'] += 1
                        
                        logger.info(f"Fetched {len(documents)} opinions with content")
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        
            except Exception as e:
                logger.error(f"Error fetching from CourtListener: {e}")
        
        return documents
    
    async def fetch_patent_cases(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch recent patent cases specifically"""
        logger.info("Fetching recent patent cases")
        
        params = {
            'q': 'nos_code:830',  # Patent cases
            'court': 'txed',
            'filed_after': (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d'),
            'order_by': '-date_filed',
            'type': 'r'  # RECAP documents
        }
        
        headers = {
            'Authorization': f'Token {self.api_token}'
        }
        
        documents = []
        url = f"{COURTLISTENER_BASE_URL}/search/"
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        
                        for result in results[:limit]:
                            # Format for pipeline
                            doc = {
                                'id': str(result.get('id', '')),
                                'case_number': result.get('docketNumber', ''),
                                'case_name': result.get('caseName', ''),
                                'document_type': 'docket',
                                'content': result.get('snippet', ''),  # Limited content from search
                                'metadata': {
                                    'court_id': 'txed',
                                    'date_filed': result.get('dateFiled'),
                                    'docket_entries': result.get('entry_count', 0),
                                    'nature_of_suit': 'Patent',
                                    'nos_code': '830',
                                    'source': 'courtlistener_recap'
                                },
                                'created_at': datetime.now()
                            }
                            
                            documents.append(doc)
                            self.stats['api_documents_fetched'] += 1
                        
                        logger.info(f"Fetched {len(documents)} patent cases")
                    else:
                        error_text = await response.text()
                        logger.error(f"API error {response.status}: {error_text}")
                        
            except Exception as e:
                logger.error(f"Error fetching patent cases: {e}")
        
        return documents
    
    async def process_through_pipeline(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Process documents through the 11-stage enhancement pipeline"""
        logger.info(f"Processing {len(documents)} documents through enhancement pipeline")
        
        # Store documents in database first
        stored_ids = self._store_raw_documents(documents)
        
        if not stored_ids:
            logger.error("Failed to store documents in database")
            return {'success': False, 'error': 'Database storage failed'}
        
        # Process through pipeline
        pipeline = OptimizedElevenStagePipeline()
        results = await pipeline.process_batch(
            limit=len(stored_ids),
            source_table='public.court_documents'
        )
        
        if results['success']:
            self.stats['documents_enhanced'] = results['statistics']['documents_processed']
            self.stats['total_citations'] = results['statistics']['citations_extracted']
            self.stats['total_enhancements'] = results['statistics']['total_enhancements']
            self.stats['documents_stored'] = results['statistics']['documents_stored']
            self.stats['documents_indexed'] = results['statistics']['documents_indexed']
        
        return results
    
    def _store_raw_documents(self, documents: List[Dict[str, Any]]) -> List[int]:
        """Store raw documents in database for pipeline processing"""
        stored_ids = []
        
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                for doc in documents:
                    # Insert into court_documents table
                    cursor.execute("""
                        INSERT INTO public.court_documents (
                            case_number, document_type, content, metadata, created_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (case_number, document_type) DO UPDATE
                        SET content = EXCLUDED.content,
                            metadata = EXCLUDED.metadata,
                            created_at = EXCLUDED.created_at
                        RETURNING id
                    """, (
                        doc['case_number'],
                        doc['document_type'],
                        doc['content'],
                        json.dumps(doc['metadata']),
                        doc['created_at']
                    ))
                    
                    result = cursor.fetchone()
                    if result:
                        stored_ids.append(result[0])
                
                conn.commit()
                logger.info(f"Stored {len(stored_ids)} documents in database")
                
        except Exception as e:
            logger.error(f"Database storage error: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        return stored_ids
    
    async def verify_pipeline_results(self) -> Dict[str, Any]:
        """Verify documents were properly processed and stored"""
        verification = {
            'database_check': self._verify_database_storage(),
            'haystack_check': await self._verify_haystack_indexing(),
            'metadata_quality': self._check_metadata_quality()
        }
        
        return verification
    
    def _verify_database_storage(self) -> Dict[str, Any]:
        """Check enhanced documents in PostgreSQL"""
        try:
            conn = get_db_connection()
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Check opinions_unified table
                cursor.execute("""
                    SELECT COUNT(*) as total,
                           COUNT(DISTINCT court_id) as courts,
                           COUNT(DISTINCT judge_info->>'full_name') as judges,
                           AVG((citations->>'count')::int) as avg_citations
                    FROM court_data.opinions_unified
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                
                result = dict(cursor.fetchone())
                
                # Get sample enhanced document
                cursor.execute("""
                    SELECT cl_id, court_id, case_name, 
                           citations->>'count' as citation_count,
                           judge_info->>'full_name' as judge_name,
                           court_info->>'court_name' as court_name
                    FROM court_data.opinions_unified
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                    LIMIT 1
                """)
                
                sample = cursor.fetchone()
                if sample:
                    result['sample_document'] = dict(sample)
                
                return result
                
        except Exception as e:
            logger.error(f"Database verification error: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()
    
    async def _verify_haystack_indexing(self) -> Dict[str, Any]:
        """Check if documents were indexed in Haystack"""
        try:
            url = f"{SERVICES['haystack']['url']}/documents"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'status': 'connected',
                            'document_count': len(data.get('documents', [])),
                            'available': True
                        }
                    else:
                        return {
                            'status': 'error',
                            'http_status': response.status,
                            'available': False
                        }
                        
        except Exception as e:
            logger.error(f"Haystack verification error: {e}")
            return {'status': 'error', 'error': str(e), 'available': False}
    
    def _check_metadata_quality(self) -> Dict[str, Any]:
        """Analyze metadata quality of processed documents"""
        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_docs,
                        COUNT(court_id) as has_court,
                        COUNT(judge_info->>'full_name') as has_judge,
                        COUNT(CASE WHEN (citations->>'count')::int > 0 THEN 1 END) as has_citations,
                        AVG(
                            CASE WHEN court_id IS NOT NULL THEN 1 ELSE 0 END +
                            CASE WHEN judge_info->>'full_name' IS NOT NULL THEN 1 ELSE 0 END +
                            CASE WHEN (citations->>'count')::int > 0 THEN 1 ELSE 0 END +
                            CASE WHEN structured_elements IS NOT NULL THEN 1 ELSE 0 END
                        ) * 25 as metadata_completeness_pct
                    FROM court_data.opinions_unified
                    WHERE created_at > NOW() - INTERVAL '1 hour'
                """)
                
                result = cursor.fetchone()
                
                return {
                    'total_documents': result[0],
                    'with_court_info': result[1],
                    'with_judge_info': result[2],
                    'with_citations': result[3],
                    'metadata_completeness': float(result[4]) if result[4] else 0
                }
                
        except Exception as e:
            logger.error(f"Metadata quality check error: {e}")
            return {'error': str(e)}
        finally:
            if conn:
                conn.close()


async def main():
    """Run complete pipeline test"""
    print("\n" + "=" * 80)
    print("COMPLETE PIPELINE TEST WITH COURTLISTENER API")
    print("=" * 80)
    print(f"API Token: {COURTLISTENER_API_TOKEN[:10]}...{COURTLISTENER_API_TOKEN[-4:]}")
    print("=" * 80 + "\n")
    
    test = CompletePipelineTest()
    
    # Step 1: Fetch real data from CourtListener
    print("STEP 1: Fetching data from CourtListener API...")
    
    # Try opinions first
    opinions = await test.fetch_recent_opinions(court='txed', days_back=7, limit=5)
    
    # If no opinions, try patent cases
    if not opinions:
        print("No recent opinions found, trying patent cases...")
        opinions = await test.fetch_patent_cases(limit=5)
    
    if not opinions:
        print("❌ No documents fetched from API. Check API token and parameters.")
        return
    
    print(f"✅ Fetched {len(opinions)} documents from CourtListener")
    
    # Step 2: Process through enhancement pipeline
    print("\nSTEP 2: Processing through 11-stage enhancement pipeline...")
    pipeline_results = await test.process_through_pipeline(opinions)
    
    if pipeline_results['success']:
        print(f"✅ Pipeline processing complete!")
        print(f"   - Documents enhanced: {test.stats['documents_enhanced']}")
        print(f"   - Total citations extracted: {test.stats['total_citations']}")
        print(f"   - Total enhancements: {test.stats['total_enhancements']}")
        print(f"   - Completeness score: {pipeline_results['verification']['completeness_score']:.1f}%")
    else:
        print(f"❌ Pipeline processing failed: {pipeline_results.get('error')}")
        return
    
    # Step 3: Verify results
    print("\nSTEP 3: Verifying pipeline results...")
    verification = await test.verify_pipeline_results()
    
    # Database verification
    db_check = verification['database_check']
    if 'error' not in db_check:
        print(f"\n✅ Database Storage Verified:")
        print(f"   - Total documents: {db_check.get('total', 0)}")
        print(f"   - Unique courts: {db_check.get('courts', 0)}")
        print(f"   - Unique judges: {db_check.get('judges', 0)}")
        print(f"   - Average citations: {db_check.get('avg_citations', 0):.1f}")
        
        if 'sample_document' in db_check:
            print(f"\n   Sample Document:")
            sample = db_check['sample_document']
            print(f"   - Case: {sample.get('case_name', 'N/A')}")
            print(f"   - Court: {sample.get('court_name', 'N/A')}")
            print(f"   - Judge: {sample.get('judge_name', 'N/A')}")
            print(f"   - Citations: {sample.get('citation_count', 0)}")
    
    # Metadata quality
    meta_check = verification['metadata_quality']
    if 'error' not in meta_check:
        print(f"\n✅ Metadata Quality:")
        print(f"   - Documents with court info: {meta_check.get('with_court_info', 0)}")
        print(f"   - Documents with judge info: {meta_check.get('with_judge_info', 0)}")
        print(f"   - Documents with citations: {meta_check.get('with_citations', 0)}")
        print(f"   - Overall completeness: {meta_check.get('metadata_completeness', 0):.1f}%")
    
    # Haystack verification
    haystack_check = verification['haystack_check']
    print(f"\n{'✅' if haystack_check.get('available') else '❌'} Haystack Integration:")
    print(f"   - Status: {haystack_check.get('status')}")
    if haystack_check.get('document_count') is not None:
        print(f"   - Documents indexed: {haystack_check.get('document_count')}")
    
    # Final summary
    print("\n" + "=" * 80)
    print("PIPELINE TEST SUMMARY")
    print("=" * 80)
    print(f"API Documents Fetched: {test.stats['api_documents_fetched']}")
    print(f"Documents Enhanced: {test.stats['documents_enhanced']}")
    print(f"Documents Stored: {test.stats['documents_stored']}")
    print(f"Documents Indexed: {test.stats['documents_indexed']}")
    print(f"Total Citations: {test.stats['total_citations']}")
    print(f"Total Enhancements: {test.stats['total_enhancements']}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())