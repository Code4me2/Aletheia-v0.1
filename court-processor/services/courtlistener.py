"""
CourtListener API Service with RECAP Support

Implements bulk data retrieval from CourtListener including:
- Opinion data (traditional CL data)
- RECAP docket data
- RECAP document metadata
- Efficient pagination strategies
"""
import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, AsyncIterator, Any
from datetime import datetime, date, timedelta
from urllib.parse import urlencode, urlparse, parse_qs
import os

logger = logging.getLogger(__name__)


class CourtListenerService:
    """
    Service for interacting with CourtListener API including RECAP data
    """
    
    # API Endpoints
    BASE_URL = "https://www.courtlistener.com"
    OPINIONS_ENDPOINT = "/api/rest/v4/opinions/"
    SEARCH_ENDPOINT = "/api/rest/v4/search/"
    DOCKETS_ENDPOINT = "/api/rest/v4/dockets/"
    RECAP_DOCS_ENDPOINT = "/api/rest/v4/recap-documents/"
    RECAP_FETCH_ENDPOINT = "/api/rest/v4/recap-fetch/"
    RECAP_QUERY_ENDPOINT = "/api/rest/v4/recap-query/"
    PEOPLE_ENDPOINT = "/api/rest/v4/people/"
    CITATION_LOOKUP_ENDPOINT = "/api/rest/v4/citation-lookup/"
    BULK_DATA_ENDPOINT = "/api/bulk-data/"
    
    # Court IDs for IP-heavy venues
    IP_COURTS = {
        'federal_circuit': ['cafc', 'uscfc', 'cit'],
        'district_heavy_ip': ['txed', 'deld', 'cand', 'nysd', 'ilnd'],
        'all_federal_district': 'FD'  # jurisdiction code
    }
    
    # Nature of Suit codes for IP cases
    IP_NATURE_OF_SUIT = {
        '820': 'Copyright',
        '830': 'Patent',
        '835': 'Patent - Abbreviated New Drug Application',
        '840': 'Trademark'
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('COURTLISTENER_API_KEY')
        self.session = None
        self.rate_limit_remaining = 5000
        self.rate_limit_reset = None
    
    @property
    def headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {'User-Agent': 'Aletheia Legal Processor/1.0'}
        if self.api_key:
            headers['Authorization'] = f'Token {self.api_key}'
        return headers
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _handle_rate_limit(self, response: aiohttp.ClientResponse):
        """Handle rate limit headers"""
        if 'X-RateLimit-Remaining' in response.headers:
            self.rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
        if 'X-RateLimit-Reset' in response.headers:
            self.rate_limit_reset = datetime.fromtimestamp(
                int(response.headers['X-RateLimit-Reset'])
            )
        
        # If we're close to limit, slow down
        if self.rate_limit_remaining < 100:
            logger.warning(f"Rate limit low: {self.rate_limit_remaining} remaining")
            await asyncio.sleep(1)
    
    def _extract_cursor_from_url(self, url: str) -> Optional[str]:
        """Extract cursor parameter from next URL"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get('cursor', [None])[0]
    
    async def fetch_opinions(self, 
                           court_id: Optional[str] = None,
                           date_filed_after: Optional[str] = None,
                           max_results: int = 100) -> List[Dict]:
        """
        Fetch traditional opinion data (non-RECAP)
        
        Args:
            court_id: Court identifier (e.g., 'ca9')
            date_filed_after: ISO date string for filtering
            max_results: Maximum number of results to return
            
        Returns:
            List of opinion documents
        """
        session = await self._get_session()
        results = []
        
        params = {
            'page_size': min(100, max_results)
        }
        
        if court_id:
            # Use the correct parameter for filtering opinions by court
            params['cluster__docket__court'] = court_id
        if date_filed_after:
            params['date_filed__gte'] = date_filed_after
        
        url = f"{self.BASE_URL}{self.OPINIONS_ENDPOINT}"
        
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results.extend(data.get('results', []))
                
                # Handle pagination with cursor
                while data.get('next') and len(results) < max_results:
                    cursor = self._extract_cursor_from_url(data['next'])
                    params['cursor'] = cursor
                    
                    async with session.get(url, params=params, headers=self.headers) as resp:
                        await self._handle_rate_limit(resp)
                        data = await resp.json()
                        results.extend(data.get('results', []))
            else:
                logger.error(f"Failed to fetch opinions: {response.status}")
        
        return results[:max_results]
    
    async def fetch_recap_dockets(self,
                                court_ids: Optional[List[str]] = None,
                                date_filed_after: Optional[str] = None,
                                nature_of_suit: Optional[List[str]] = None,
                                max_results: int = 100) -> List[Dict]:
        """
        Fetch RECAP docket data with IP filtering
        
        Args:
            court_ids: List of court IDs to filter
            date_filed_after: ISO date string
            nature_of_suit: List of nature of suit codes (e.g., ['830', '840'])
            max_results: Maximum results to return
            
        Returns:
            List of docket metadata
        """
        session = await self._get_session()
        results = []
        
        params = {
            'page_size': min(100, max_results)
        }
        
        if court_ids:
            params['court__in'] = ','.join(court_ids)
        if date_filed_after:
            params['date_filed__gte'] = date_filed_after
        if nature_of_suit:
            params['nature_of_suit__in'] = ','.join(nature_of_suit)
        
        url = f"{self.BASE_URL}{self.DOCKETS_ENDPOINT}"
        
        logger.info(f"Fetching RECAP dockets with params: {params}")
        
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results.extend(data.get('results', []))
                
                # Cursor pagination for large datasets
                while data.get('next') and len(results) < max_results:
                    cursor = self._extract_cursor_from_url(data['next'])
                    params['cursor'] = cursor
                    
                    async with session.get(url, params=params, headers=self.headers) as resp:
                        await self._handle_rate_limit(resp)
                        data = await resp.json()
                        results.extend(data.get('results', []))
                        
                        # Log progress
                        logger.info(f"Fetched {len(results)} dockets...")
            else:
                logger.error(f"Failed to fetch dockets: {response.status}")
                error_text = await response.text()
                logger.error(f"Error response: {error_text}")
        
        return results[:max_results]
    
    async def fetch_recap_documents(self,
                                  docket_id: int,
                                  document_type: Optional[str] = None) -> List[Dict]:
        """
        Fetch RECAP documents for a specific docket
        
        Args:
            docket_id: The docket ID
            document_type: Filter by document type
            
        Returns:
            List of document metadata
        """
        session = await self._get_session()
        
        params = {
            'docket_entry__docket__id': docket_id,
            'page_size': 100
        }
        
        if document_type:
            params['document_type'] = document_type
        
        url = f"{self.BASE_URL}{self.RECAP_DOCS_ENDPOINT}"
        results = []
        
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results.extend(data.get('results', []))
                
                # Get all documents for this docket
                while data.get('next'):
                    cursor = self._extract_cursor_from_url(data['next'])
                    params['cursor'] = cursor
                    
                    async with session.get(url, params=params, headers=self.headers) as resp:
                        await self._handle_rate_limit(resp)
                        data = await resp.json()
                        results.extend(data.get('results', []))
        
        return results
    
    async def search_recap_documents(self,
                                   params: Dict[str, Any],
                                   max_results: int = 100) -> List[Dict]:
        """
        Search RECAP documents with specific parameters
        
        Args:
            params: Search parameters including court, dates, etc.
            max_results: Maximum results to return
            
        Returns:
            List of RECAP documents
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        
        # Set default params and page size
        search_params = {
            'page_size': min(100, max_results),
            **params
        }
        
        results = []
        try:
            # Log the request for debugging
            logger.debug(f"RECAP search URL: {url}")
            logger.debug(f"RECAP search params: {search_params}")
            
            async with session.get(url, params=search_params, headers=self.headers) as response:
                if response.status == 200:
                    data = await response.json()
                    results = data.get('results', [])[:max_results]
                    logger.info(f"Found {len(results)} RECAP documents")
                else:
                    error_text = await response.text()
                    logger.error(f"RECAP search failed: {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"RECAP search error: {e}")
        
        return results
    
    async def search_recap(self,
                         query: str,
                         court_ids: Optional[List[str]] = None,
                         date_range: Optional[tuple] = None,
                         max_results: int = 100) -> List[Dict]:
        """
        Full-text search of RECAP documents
        
        Args:
            query: Search query
            court_ids: List of courts to search
            date_range: Tuple of (start_date, end_date)
            max_results: Maximum results
            
        Returns:
            List of search results
        """
        session = await self._get_session()
        
        params = {
            'q': query,
            'type': 'r',  # RECAP documents
            'page_size': min(100, max_results)
        }
        
        if court_ids:
            params['court'] = ' OR '.join(court_ids)
        
        if date_range:
            params['filed_after'] = date_range[0]
            params['filed_before'] = date_range[1]
        
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        results = []
        
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results.extend(data.get('results', []))
                
                # Pagination
                page = 2
                while data.get('next') and len(results) < max_results and page <= 100:
                    params['page'] = page
                    
                    async with session.get(url, params=params, headers=self.headers) as resp:
                        await self._handle_rate_limit(resp)
                        data = await resp.json()
                        results.extend(data.get('results', []))
                        page += 1
        
        return results[:max_results]
    
    async def fetch_ip_cases_bulk(self,
                                start_date: str,
                                end_date: Optional[str] = None,
                                include_documents: bool = False) -> AsyncIterator[Dict]:
        """
        Bulk fetch IP-related cases from RECAP
        
        Args:
            start_date: Start date for filtering
            end_date: End date (defaults to today)
            include_documents: Whether to fetch associated documents
            
        Yields:
            Docket data with optional document list
        """
        # Default to today if no end date
        if not end_date:
            end_date = date.today().isoformat()
        
        # Stage 1: Federal Circuit courts
        logger.info("Fetching Federal Circuit IP cases...")
        federal_dockets = await self.fetch_recap_dockets(
            court_ids=self.IP_COURTS['federal_circuit'],
            date_filed_after=start_date,
            max_results=1000
        )
        
        for docket in federal_dockets:
            if include_documents:
                docket['documents'] = await self.fetch_recap_documents(docket['id'])
            yield docket
        
        # Stage 2: District courts with IP nature of suit
        logger.info("Fetching District Court IP cases...")
        district_dockets = await self.fetch_recap_dockets(
            court_ids=self.IP_COURTS['district_heavy_ip'],
            date_filed_after=start_date,
            nature_of_suit=list(self.IP_NATURE_OF_SUIT.keys()),
            max_results=5000
        )
        
        for docket in district_dockets:
            if include_documents:
                docket['documents'] = await self.fetch_recap_documents(docket['id'])
            yield docket
    
    async def check_document_availability(self, filepath_local: str) -> bool:
        """
        Check if a RECAP document PDF is available
        
        Args:
            filepath_local: The filepath_local from document metadata
            
        Returns:
            Boolean indicating if PDF is available
        """
        if not filepath_local:
            return False
        
        # Check if it's a RECAP path
        if not filepath_local.startswith('recap/'):
            return False
        
        # Could make HEAD request to check, but for now just return True
        # if the path exists (actual download would need separate implementation)
        return True
    
    async def get_docket_entries_with_documents(self, docket_id: int) -> Dict:
        """
        Get structured docket entries with associated documents
        
        Args:
            docket_id: The docket ID
            
        Returns:
            Dictionary with docket info and entries with documents
        """
        session = await self._get_session()
        
        # Get docket metadata
        docket_url = f"{self.BASE_URL}{self.DOCKETS_ENDPOINT}{docket_id}/"
        async with session.get(docket_url, headers=self.headers) as response:
            if response.status != 200:
                return {}
            docket_data = await response.json()
        
        # Get all documents for this docket
        documents = await self.fetch_recap_documents(docket_id)
        
        # Group documents by docket entry
        entries_dict = {}
        for doc in documents:
            entry_id = doc.get('docket_entry')
            if entry_id:
                if entry_id not in entries_dict:
                    entries_dict[entry_id] = {
                        'id': entry_id,
                        'documents': []
                    }
                entries_dict[entry_id]['documents'].append(doc)
        
        # Combine with docket data
        docket_data['entries_with_documents'] = list(entries_dict.values())
        
        return docket_data
    
    async def check_recap_availability(self, 
                                      court: str,
                                      pacer_doc_ids: List[str]) -> List[Dict]:
        """
        Check if RECAP documents are available before attempting download
        
        Args:
            court: Court ID (e.g., 'txed')
            pacer_doc_ids: List of PACER document IDs to check
            
        Returns:
            List of available documents with metadata
        """
        if not pacer_doc_ids:
            return []
            
        session = await self._get_session()
        url = f"{self.BASE_URL}{self.RECAP_QUERY_ENDPOINT}"
        
        params = {
            'docket_entry__docket__court': court,
            'pacer_doc_id__in': ','.join(pacer_doc_ids),
            'page_size': 100
        }
        
        results = []
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                logger.info(f"RECAP availability check: {len(results)}/{len(pacer_doc_ids)} documents available")
            else:
                logger.warning(f"RECAP query failed: {response.status}")
                
        return results
    
    async def fetch_judge_info(self, 
                             judge_name: Optional[str] = None,
                             court: Optional[str] = None) -> List[Dict]:
        """
        Fetch judge information from the people endpoint
        
        Args:
            judge_name: Judge's last name or full name
            court: Court ID to filter by
            
        Returns:
            List of matching judge records
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{self.PEOPLE_ENDPOINT}"
        
        params = {'page_size': 50}
        
        if judge_name:
            # Try to extract last name if full name provided
            name_parts = judge_name.strip().split()
            if len(name_parts) > 1:
                params['name_last'] = name_parts[-1]
                params['name_first'] = name_parts[0]
            else:
                params['name_last'] = judge_name
                
        if court:
            params['court'] = court
            
        results = []
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                
                # Filter for exact matches if full name provided
                if judge_name and len(name_parts) > 1:
                    results = [
                        r for r in results 
                        if judge_name.lower() in f"{r.get('name_first', '')} {r.get('name_last', '')}".lower()
                    ]
            else:
                logger.warning(f"Judge search failed: {response.status}")
                
        return results
    
    async def validate_citations(self, text: str) -> Dict:
        """
        Validate and extract citations from text using citation-lookup
        
        Args:
            text: Text containing legal citations
            
        Returns:
            Dictionary with extracted citations and validation results
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{self.CITATION_LOOKUP_ENDPOINT}"
        
        # This is a POST endpoint
        data = {'text': text[:50000]}  # API has a text length limit
        
        async with session.post(url, json=data, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                result = await response.json()
                return result
            else:
                logger.warning(f"Citation validation failed: {response.status}")
                return {'citations': [], 'errors': ['API request failed']}
    
    async def search_with_filters(self,
                                query: str = None,
                                search_type: str = 'o',
                                court_ids: Optional[List[str]] = None,
                                nature_of_suit: Optional[List[str]] = None,
                                date_range: Optional[tuple] = None,
                                max_results: int = 100) -> List[Dict]:
        """
        Enhanced search with multiple filters and search types
        
        Args:
            query: Search query (optional)
            search_type: 'o' (opinions), 'r' (RECAP), 'rd' (RECAP docs), 'd' (dockets), 'p' (people)
            court_ids: List of court IDs
            nature_of_suit: List of nature of suit codes (for IP: 820, 830, 840)
            date_range: Tuple of (start_date, end_date)
            max_results: Maximum results
            
        Returns:
            List of search results
        """
        session = await self._get_session()
        url = f"{self.BASE_URL}{self.SEARCH_ENDPOINT}"
        
        params = {
            'type': search_type,
            'page_size': min(100, max_results)
        }
        
        if query:
            params['q'] = query
            
        if court_ids:
            params['court'] = ' OR '.join(court_ids)
            
        if nature_of_suit and search_type in ['r', 'd']:
            params['nature_of_suit'] = ' OR '.join(nature_of_suit)
            
        if date_range:
            params['filed_after'] = date_range[0]
            params['filed_before'] = date_range[1]
            
        results = []
        async with session.get(url, params=params, headers=self.headers) as response:
            await self._handle_rate_limit(response)
            
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                
                # Handle pagination
                page = 2
                while data.get('next') and len(results) < max_results and page <= 100:
                    params['page'] = page
                    
                    async with session.get(url, params=params, headers=self.headers) as resp:
                        await self._handle_rate_limit(resp)
                        if resp.status == 200:
                            data = await resp.json()
                            results.extend(data.get('results', []))
                        page += 1
            else:
                logger.error(f"Search failed: {response.status}")
                
        return results[:max_results]
    
    def extract_all_text_fields(self, opinion: Dict) -> str:
        """
        Extract text from all available fields in order of preference
        
        Args:
            opinion: Opinion document dictionary
            
        Returns:
            Combined text content
        """
        # Try fields in order of preference
        text_fields = [
            'plain_text',
            'html',
            'xml_harvard',
            'html_lawbox',
            'html_columbia',
            'text'  # Generic fallback
        ]
        
        content_parts = []
        for field in text_fields:
            if field in opinion and opinion[field]:
                content = opinion[field]
                if isinstance(content, str) and content.strip():
                    # Clean HTML if needed
                    if field.startswith('html'):
                        # Basic HTML stripping (in production, use BeautifulSoup)
                        import re
                        content = re.sub('<[^<]+?>', '', content)
                    content_parts.append(content.strip())
                    break  # Use first available field
                    
        return '\n\n'.join(content_parts)

    async def close(self):
        """Close the aiohttp session"""
        if self.session:
            await self.session.close()


# Convenience functions for common use cases
async def get_recent_patent_cases(days_back: int = 30) -> List[Dict]:
    """Get recent patent cases from key venues"""
    service = CourtListenerService()
    
    start_date = (date.today() - timedelta(days=days_back)).isoformat()
    
    try:
        results = await service.fetch_recap_dockets(
            court_ids=['txed', 'deld', 'cand'],
            date_filed_after=start_date,
            nature_of_suit=['830', '835'],
            max_results=500
        )
        return results
    finally:
        await service.close()


async def search_ip_cases(search_term: str, court: Optional[str] = None) -> List[Dict]:
    """Search for IP cases by term"""
    service = CourtListenerService()
    
    try:
        courts = [court] if court else CourtListenerService.IP_COURTS['district_heavy_ip']
        results = await service.search_recap(
            query=search_term,
            court_ids=courts,
            max_results=100
        )
        return results
    finally:
        await service.close()