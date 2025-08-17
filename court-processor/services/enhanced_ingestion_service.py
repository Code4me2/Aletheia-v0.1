"""
Enhanced Document Ingestion Service for Judiciary Insights

This service properly implements the 3-step traversal required by CourtListener API:
1. Search/Opinion → 2. Cluster → 3. Docket

Key improvements:
- Uses Search API for accurate date filtering
- Fetches complete docket information including judges
- Implements field mapping for consistency
- Handles rate limits gracefully
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import os

from .courtlistener_service import CourtListenerService
from .database import get_db_connection
from .enhanced_retry_logic import EnhancedRetryClient, RetryConfig, validate_opinion_content

# Import comprehensive judge extractor
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from comprehensive_judge_extractor import ComprehensiveJudgeExtractor

logger = logging.getLogger(__name__)


@dataclass
class JudiciaryDocument:
    """Unified document model for judiciary insights"""
    # Core identifiers
    cl_opinion_id: str
    cl_cluster_id: Optional[str] = None
    cl_docket_id: Optional[str] = None
    
    # Case information
    case_name: str = ""
    docket_number: str = ""
    court_id: str = ""
    
    # Temporal data
    date_filed: Optional[datetime] = None
    date_argued: Optional[datetime] = None
    date_terminated: Optional[datetime] = None
    
    # Judge information (our primary goal)
    judge_name: str = ""
    judge_id: Optional[str] = None
    judge_source: str = ""  # tracks where we got the judge info
    
    # Document content
    opinion_type: str = ""
    text: str = ""
    html: str = ""
    
    # Additional metadata
    citations: List[str] = None
    parties: List[str] = None
    attorneys: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.citations is None:
            self.citations = []
        if self.parties is None:
            self.parties = []
        if self.attorneys is None:
            self.attorneys = []
        if self.metadata is None:
            self.metadata = {}


class FieldMapper:
    """Standardize field names across different API responses"""
    
    # Judge field mappings
    JUDGE_FIELDS = {
        'assigned_to_str': 'judge_name',      # From dockets
        'assigned_to': 'judge_name',          # From dockets (alt)
        'judges': 'judge_name',               # From clusters (IMPORTANT!)
        'judge': 'judge_name',                # From search results
        'author_str': 'judge_name',           # From opinions
        'panel_names': 'judge_name',          # From clusters (panel cases)
    }
    
    # Case name mappings
    CASE_NAME_FIELDS = {
        'caseName': 'case_name',
        'case_name': 'case_name',
        'case_name_full': 'case_name',
        'case_name_short': 'case_name',
    }
    
    # Date mappings
    DATE_FIELDS = {
        'dateFiled': 'date_filed',
        'date_filed': 'date_filed',
        'dateArgued': 'date_argued',
        'date_argued': 'date_argued',
        'dateTerminated': 'date_terminated',
        'date_terminated': 'date_terminated',
    }
    
    # Docket mappings
    DOCKET_FIELDS = {
        'docketNumber': 'docket_number',
        'docket_number': 'docket_number',
    }
    
    @classmethod
    def extract_judge(cls, data: Dict) -> tuple[str, str]:
        """Extract judge name and source from various fields"""
        for field, mapped in cls.JUDGE_FIELDS.items():
            if field in data and data[field]:
                return str(data[field]), field
        return "", "not_found"
    
    @classmethod
    def extract_case_name(cls, data: Dict) -> str:
        """Extract case name from various fields"""
        for field in cls.CASE_NAME_FIELDS:
            if field in data and data[field]:
                return str(data[field])
        return ""
    
    @classmethod
    def extract_date(cls, data: Dict, date_type: str = 'date_filed') -> Optional[datetime]:
        """Extract and parse date from various fields"""
        for field, mapped in cls.DATE_FIELDS.items():
            if mapped == date_type and field in data and data[field]:
                try:
                    if isinstance(data[field], str):
                        return datetime.fromisoformat(data[field].replace('Z', '+00:00'))
                    return data[field]
                except:
                    logger.warning(f"Failed to parse date: {data[field]}")
        return None


class JudgeExtractor:
    """Enhanced judge extraction with multiple strategies"""
    
    # Common judge initials in E.D. Texas and their full names
    JUDGE_INITIALS_MAP = {
        # Eastern District of Texas
        'JRG': 'Rodney Gilstrap',
        'RWS': 'Robert W. Schroeder III',
        'RSP': 'Roy S. Payne',
        'MSS': 'Mitchell S. Sandlin',
        'JDC': 'J. Campbell Barker',
        
        # Add more as discovered
    }
    
    @classmethod
    def extract_from_docket_number(cls, docket_number: str) -> Optional[str]:
        """Extract judge from docket number pattern like 2:16-CV-682-JRG"""
        if not docket_number:
            return None
            
        import re
        # Pattern: ends with dash followed by 2-3 uppercase letters
        match = re.search(r'-([A-Z]{2,3})(?:-\d+)?$', docket_number)
        if match:
            initials = match.group(1)
            return cls.JUDGE_INITIALS_MAP.get(initials, initials)
        return None


class EnhancedIngestionService:
    """Streamlined ingestion with 3-step traversal for complete data"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        # Configure retry logic with more aggressive settings for 202 responses
        retry_config = RetryConfig(
            max_attempts=6,  # More attempts for 202 processing
            initial_delay=3.0,  # Start with 3 seconds
            max_delay=30.0,  # Cap at 30 seconds
            backoff_factor=1.8,  # Less aggressive backoff (3, 5.4, 9.7, 17.5, 30, 30)
            jitter=True,  # Add randomness to avoid thundering herd
            retry_on_statuses=[202, 429, 500, 502, 503, 504]
        )
        self.retry_client = EnhancedRetryClient(retry_config)
        self.stats = {
            'documents_fetched': 0,
            'clusters_fetched': 0,
            'dockets_fetched': 0,
            'judges_found': 0,
            'documents_saved': 0,
            'errors': 0
        }
    
    async def ingest_by_judge(self, judge_name: str, court_id: Optional[str] = None,
                             date_after: Optional[str] = None, date_before: Optional[str] = None,
                             limit: int = 100) -> Dict[str, Any]:
        """Ingest opinions by judge name using Search API"""
        logger.info(f"Ingesting opinions by judge: {judge_name}")
        
        # Use Search API for accurate results
        search_params = {
            'q': judge_name,
            'type': 'o',  # opinions
            'page_size': min(limit, 100)
        }
        
        if court_id:
            search_params['court'] = court_id
        if date_after:
            search_params['filed_after'] = date_after
        if date_before:
            search_params['filed_before'] = date_before
            
        documents = await self._fetch_and_process_search_results(search_params)
        
        return {
            'stats': self.stats,
            'documents': len(documents),
            'judge_attribution_rate': (self.stats['judges_found'] / max(1, self.stats['documents_fetched'])) * 100,
            'documents_skipped': self.stats.get('documents_skipped', 0)
        }
    
    async def ingest_by_court(self, court_id: str, date_after: Optional[str] = None,
                             date_before: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Ingest opinions from a specific court"""
        logger.info(f"Ingesting opinions from court: {court_id}")
        
        search_params = {
            'court': court_id,
            'type': 'o',
            'page_size': min(limit, 100)
        }
        
        if date_after:
            search_params['filed_after'] = date_after
        if date_before:
            search_params['filed_before'] = date_before
            
        documents = await self._fetch_and_process_search_results(search_params)
        
        return {
            'stats': self.stats,
            'documents': len(documents),
            'judge_attribution_rate': (self.stats['judges_found'] / max(1, self.stats['documents_fetched'])) * 100,
            'documents_skipped': self.stats.get('documents_skipped', 0)
        }
    
    async def _fetch_and_process_search_results(self, search_params: Dict) -> List[JudiciaryDocument]:
        """Fetch search results and process through 3-step traversal"""
        documents = []
        
        try:
            session = await self.cl_service._get_session()
            search_url = f"{self.cl_service.BASE_URL}{self.cl_service.SEARCH_ENDPOINT}"
            
            async with session.get(search_url, params=search_params, headers=self.cl_service.headers) as response:
                if response.status != 200:
                    logger.error(f"Search failed: {response.status}")
                    return documents
                
                data = await response.json()
                results = data.get('results', [])
                total_count = data.get('count', 0)
                
                logger.info(f"Found {total_count} results, processing {len(results)}")
                
                # Process each search result
                for result in results:
                    try:
                        doc = await self._process_search_result(result, session)
                        if doc:
                            documents.append(doc)
                            self.stats['documents_fetched'] += 1
                            if doc.judge_name:
                                self.stats['judges_found'] += 1
                    except Exception as e:
                        logger.error(f"Error processing result: {e}")
                        self.stats['errors'] += 1
                        
        except Exception as e:
            logger.error(f"Search error: {e}")
            self.stats['errors'] += 1
            
        # Save all documents to database
        await self._save_documents(documents)
        
        return documents
    
    async def _process_search_result(self, result: Dict, session: aiohttp.ClientSession) -> Optional[JudiciaryDocument]:
        """Process a single search result through 3-step traversal"""
        
        # Extract opinion ID from absolute_url (format: /opinion/{id}/...)
        opinion_id = ''
        if result.get('absolute_url'):
            import re
            match = re.search(r'/opinion/(\d+)/', result['absolute_url'])
            if match:
                opinion_id = match.group(1)
        
        # Initialize document with search result data
        doc = JudiciaryDocument(
            cl_opinion_id=opinion_id,
            cl_cluster_id=str(result.get('cluster_id', '')),
            cl_docket_id=str(result.get('docket_id', '')),
            case_name=FieldMapper.extract_case_name(result),
            court_id=result.get('court_id', result.get('court', '')),
            date_filed=FieldMapper.extract_date(result),
            docket_number=result.get('docketNumber', '')
        )
        
        # Initialize variables for comprehensive judge extraction
        opinion_data = None
        cluster_data = None
        docket_data = None
        
        # Step 1: Fetch full opinion data using the opinion ID
        # Note: cluster_id in search results corresponds to opinion ID in the API
        if result.get('cluster_id'):
            opinion_data = await self._fetch_opinion(str(result['cluster_id']), session)
            if opinion_data:
                # Update with opinion data
                doc.text = opinion_data.get('plain_text', '')
                doc.html = opinion_data.get('html', opinion_data.get('html_lawbox', ''))
                doc.opinion_type = opinion_data.get('type', '')
            else:
                # If opinion fetch failed (202 or error), mark document as pending
                doc.metadata = doc.metadata or {}
                doc.metadata['processing_status'] = '202_pending'
                doc.metadata['fetch_attempted'] = datetime.now().isoformat()
                
                # Try to get text from search result as fallback
                if result.get('text'):
                    doc.text = result.get('text')
                    logger.info(f"Using text from search result for opinion {doc.cl_opinion_id}")
                else:
                    # No content available - don't save this document
                    logger.warning(f"Skipping document with no content: {doc.cl_opinion_id} - {doc.case_name}")
                    self.stats['documents_skipped'] = self.stats.get('documents_skipped', 0) + 1
                    return None
            
            # Only proceed with cluster/docket if we got opinion data
            if opinion_data:
                # Step 2: Fetch cluster data
                if opinion_data.get('cluster'):
                    cluster_data = await self._fetch_cluster(opinion_data['cluster'], session)
                    if cluster_data:
                        doc.cl_cluster_id = str(cluster_data.get('id', ''))
                        self.stats['clusters_fetched'] += 1
                        
                        # Update case name and dates from cluster
                        if not doc.case_name:
                            doc.case_name = FieldMapper.extract_case_name(cluster_data)
                        if not doc.date_filed:
                            doc.date_filed = FieldMapper.extract_date(cluster_data)
                            
                        # Step 3: Fetch docket data
                        if cluster_data.get('docket'):
                            docket_data = await self._fetch_docket(cluster_data['docket'], session)
                            if docket_data:
                                doc.cl_docket_id = str(docket_data.get('id', ''))
                                self.stats['dockets_fetched'] += 1
                                
                                # Get additional docket info
                                if not doc.docket_number:
                                    doc.docket_number = docket_data.get('docket_number', '')
                                doc.parties = self._extract_parties(docket_data)
                                doc.date_terminated = FieldMapper.extract_date(docket_data, 'date_terminated')
        
        # Use comprehensive judge extraction with all available data
        judge_info = ComprehensiveJudgeExtractor.extract_comprehensive_judge_info(
            search_result=result,
            opinion_data=opinion_data,
            cluster_data=cluster_data,
            docket_data=docket_data,
            docket_number=doc.docket_number
        )
        
        if judge_info:
            doc.judge_name = judge_info.name
            doc.judge_source = judge_info.source
            
            # Log all sources we found for debugging
            if len(judge_info.all_sources) > 1:
                logger.info(f"Multiple judge sources for {doc.case_name}: {judge_info.all_sources}")
                
            self.stats['judges_found'] += 1
        else:
            logger.debug(f"No judge found for {doc.case_name} ({doc.docket_number})")
        
        return doc
    
    async def _fetch_opinion(self, opinion_id: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Fetch full opinion data with enhanced retry logic for 202 responses"""
        # Construct proper API endpoint URL
        full_url = f"{self.cl_service.BASE_URL}/opinions/{opinion_id}/"
        
        # Use enhanced retry client with content validation
        data = await self.retry_client.fetch_with_retry(
            session=session,
            url=full_url,
            headers=self.cl_service.headers,
            validate_content=validate_opinion_content
        )
        
        if data:
            logger.info(f"Opinion fetched successfully, text length: {len(data.get('plain_text', ''))}")
        else:
            logger.warning(f"Failed to fetch opinion with valid content: {opinion_id}")
            
        return data
    
    async def _fetch_cluster(self, cluster_url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Fetch cluster data"""
        try:
            async with session.get(cluster_url, headers=self.cl_service.headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching cluster: {e}")
        return None
    
    async def _fetch_docket(self, docket_url: str, session: aiohttp.ClientSession) -> Optional[Dict]:
        """Fetch docket data - this often has the judge information"""
        try:
            async with session.get(docket_url, headers=self.cl_service.headers) as response:
                if response.status == 200:
                    return await response.json()
        except Exception as e:
            logger.error(f"Error fetching docket: {e}")
        return None
    
    def _extract_parties(self, docket_data: Dict) -> List[str]:
        """Extract party names from docket data"""
        parties = []
        # CourtListener may have parties in different formats
        if 'parties' in docket_data:
            # Handle array of party objects
            for party in docket_data['parties']:
                if isinstance(party, dict) and 'name' in party:
                    parties.append(party['name'])
                elif isinstance(party, str):
                    parties.append(party)
        return parties
    
    async def _save_documents(self, documents: List[JudiciaryDocument]):
        """Save documents to database with unified schema"""
        if not documents:
            return
            
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            for doc in documents:
                # Save to court_documents for pipeline processing
                # First check if exists
                case_num = f"OPINION-{doc.cl_opinion_id}"
                cursor.execute("""
                    SELECT id FROM public.court_documents 
                    WHERE case_number = %s
                """, (case_num,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing
                    cursor.execute("""
                        UPDATE public.court_documents SET
                            content = COALESCE(%s, content),
                            metadata = %s::jsonb,
                            updated_at = NOW()
                        WHERE case_number = %s
                    """, (
                        doc.text or doc.html,
                        json.dumps({
                            'cl_opinion_id': doc.cl_opinion_id,
                            'cl_cluster_id': doc.cl_cluster_id,
                            'cl_docket_id': doc.cl_docket_id,
                            'case_name': doc.case_name,
                            'docket_number': doc.docket_number,
                            'court_id': doc.court_id,
                            'date_filed': doc.date_filed.isoformat() if doc.date_filed else None,
                            'judge_name': doc.judge_name,
                            'judge_source': doc.judge_source,
                            'opinion_type': doc.opinion_type,
                            'parties': doc.parties,
                            **doc.metadata  # Include any additional metadata
                        }),
                        case_num
                    ))
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO public.court_documents (
                            case_number, document_type, content, metadata, created_at
                        ) VALUES (%s, %s, %s, %s::jsonb, NOW())
                    """, (
                        case_num,
                        'opinion',
                        doc.text or doc.html,
                        json.dumps({
                            'cl_opinion_id': doc.cl_opinion_id,
                            'cl_cluster_id': doc.cl_cluster_id,
                            'cl_docket_id': doc.cl_docket_id,
                            'case_name': doc.case_name,
                            'docket_number': doc.docket_number,
                            'court_id': doc.court_id,
                            'date_filed': doc.date_filed.isoformat() if doc.date_filed else None,
                            'judge_name': doc.judge_name,
                            'judge_source': doc.judge_source,
                            'opinion_type': doc.opinion_type,
                            'parties': doc.parties,
                            **doc.metadata  # Include any additional metadata
                        })
                    ))
                
                # Also save docket info if we have it
                if doc.cl_docket_id and doc.judge_name:
                    cursor.execute("""
                        INSERT INTO court_data.cl_dockets (
                            id, court_id, case_name, docket_number,
                            date_filed, date_terminated, assigned_to_str,
                            imported_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (id) DO UPDATE SET
                            assigned_to_str = EXCLUDED.assigned_to_str,
                            updated_at = NOW()
                    """, (
                        doc.cl_docket_id,
                        doc.court_id,
                        doc.case_name,
                        doc.docket_number,
                        doc.date_filed,
                        doc.date_terminated,
                        doc.judge_name
                    ))
                
                self.stats['documents_saved'] += 1
                
            conn.commit()
            logger.info(f"Saved {self.stats['documents_saved']} documents")
            
        except Exception as e:
            logger.error(f"Database save error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    async def close(self):
        """Clean up resources and log retry statistics"""
        # Log retry statistics
        retry_stats = self.retry_client.get_stats_summary()
        if retry_stats['total_requests'] > 0:
            logger.info("=== Retry Statistics ===")
            logger.info(f"Total requests: {retry_stats['total_requests']}")
            logger.info(f"Successful: {retry_stats['successful_requests']}")
            logger.info(f"Retry rate: {retry_stats['retry_rate']:.1f}%")
            logger.info(f"Content retrieved after retry: {retry_stats['content_after_retry_rate']:.1f}%")
            logger.info(f"Average retries per URL: {retry_stats['avg_retries']:.1f}")
            logger.info(f"Total retry time: {retry_stats['total_retry_time_seconds']:.1f}s")
            logger.info(f"Status distribution: {retry_stats['status_distribution']}")
        
        await self.cl_service.close()
    
    def get_retry_stats(self) -> Dict[str, Any]:
        """Get retry statistics for analysis"""
        return self.retry_client.get_stats_summary()


# Convenience functions for CLI usage
async def ingest_judge_cases(judge_name: str, court_id: Optional[str] = None,
                           year: Optional[int] = None, limit: int = 100):
    """Ingest cases by a specific judge"""
    service = EnhancedIngestionService()
    
    date_after = f"{year}-01-01" if year else None
    date_before = f"{year}-12-31" if year else None
    
    try:
        results = await service.ingest_by_judge(
            judge_name=judge_name,
            court_id=court_id,
            date_after=date_after,
            date_before=date_before,
            limit=limit
        )
        return results
    finally:
        await service.close()


async def ingest_court_cases(court_id: str, date_after: Optional[str] = None,
                           date_before: Optional[str] = None, limit: int = 100):
    """Ingest cases from a specific court"""
    service = EnhancedIngestionService()
    
    try:
        results = await service.ingest_by_court(
            court_id=court_id,
            date_after=date_after,
            date_before=date_before,
            limit=limit
        )
        return results
    finally:
        await service.close()