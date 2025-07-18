"""
Real CourtListener API Integration Service

Handles actual CourtListener API requests with proper field mapping,
authentication, and error handling.
"""
import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from ..config import get_settings
from ..utils.logging import get_logger


class CourtListenerService:
    """Service for interacting with CourtListener API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("courtlistener_service")
        self.base_url = self.settings.services.courtlistener_base_url
        self.api_key = self.settings.services.courtlistener_api_key
        self.timeout = self.settings.services.courtlistener_timeout
        
        if not self.api_key:
            self.logger.warning("No CourtListener API key configured")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "User-Agent": "Enhanced Court Processor v1.0",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        
        return headers
    
    def _map_courtlistener_document(self, raw_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map raw CourtListener API response to our expected document format
        
        CourtListener API Response Structure:
        - id: integer
        - cluster_id: integer  
        - author_str: string (may be empty)
        - date_created: "2025-07-17T18:01:15.272690-07:00"
        - date_modified: "2025-07-17T18:42:21.628394-07:00"
        - type: "010combined"
        - plain_text: string
        - download_url: string
        - local_path: string
        - cluster: URL to cluster resource
        
        Our Expected Format:
        - id: integer
        - court_id: string
        - case_name: string
        - date_filed: ISO date string
        - author_str: string
        - plain_text: string
        - type: string
        """
        try:
            mapped_doc = {
                'id': raw_doc.get('id'),
                'cluster_id': raw_doc.get('cluster_id'),
                'author_str': raw_doc.get('author_str', ''),
                'plain_text': raw_doc.get('plain_text', ''),
                'type': raw_doc.get('type', 'opinion'),
                'download_url': raw_doc.get('download_url'),
                'local_path': raw_doc.get('local_path'),
                'absolute_url': raw_doc.get('absolute_url'),
                'sha1': raw_doc.get('sha1'),
                'page_count': raw_doc.get('page_count', 0),
                'per_curiam': raw_doc.get('per_curiam', False),
                
                # Map date fields
                'date_created': self._parse_date(raw_doc.get('date_created')),
                'date_modified': self._parse_date(raw_doc.get('date_modified')),
                
                # Default values for missing fields (will be enriched by FLP)
                'court_id': None,  # Will be filled from cluster data
                'case_name': None,  # Will be filled from cluster data  
                'date_filed': None,  # Will be filled from cluster data
                
                # Metadata
                'cluster_url': raw_doc.get('cluster'),
                'author_url': raw_doc.get('author'),
                'resource_uri': raw_doc.get('resource_uri'),
                
                # Processing metadata
                'processing_timestamp': datetime.utcnow().isoformat(),
                'source': 'courtlistener_api',
                'api_version': 'v4'
            }
            
            self.logger.debug(f"Mapped CourtListener document ID {mapped_doc['id']}, has_text: {bool(mapped_doc['plain_text'])}")
            
            return mapped_doc
            
        except Exception as e:
            self.logger.error(f"Failed to map CourtListener document: {str(e)} (keys: {list(raw_doc.keys())})")
            # Return raw document with minimal mapping
            return {
                'id': raw_doc.get('id'),
                'raw_document': raw_doc,
                'mapping_error': str(e),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def _parse_date(self, date_str: Optional[str]) -> Optional[str]:
        """Parse CourtListener date format to ISO format"""
        if not date_str:
            return None
            
        try:
            # Parse: "2025-07-17T18:01:15.272690-07:00"
            # Remove microseconds and timezone for simplified handling
            if 'T' in date_str:
                date_part = date_str.split('T')[0]
                return date_part  # Return just the date portion: "2025-07-17"
            return date_str
        except Exception as e:
            self.logger.warning(f"Failed to parse date {date_str}: {str(e)}")
            return date_str  # Return original if parsing fails
    
    async def fetch_cluster_data(self, cluster_url: str) -> Optional[Dict[str, Any]]:
        """
        Fetch cluster data to get court_id and case_name
        """
        if not cluster_url or not self.api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    cluster_url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        cluster_data = await response.json()
                        return {
                            'court_id': cluster_data.get('court_id'),
                            'case_name': cluster_data.get('case_name'),
                            'date_filed': self._parse_date(cluster_data.get('date_filed')),
                            'docket_number': cluster_data.get('docket_number'),
                            'citation_count': cluster_data.get('citation_count', 0)
                        }
                    else:
                        self.logger.warning(f"Failed to fetch cluster data from {cluster_url}: HTTP {response.status}")
                        return None
        except Exception as e:
            self.logger.error(f"Error fetching cluster data from {cluster_url}: {str(e)}")
            return None
    
    async def fetch_dockets_by_judge(
        self,
        judge_name: str,
        court_id: Optional[str] = None,
        max_documents: int = 100,
        date_filed_after: Optional[str] = None,
        date_filed_before: Optional[str] = None,
        ordering: str = "-date_filed"
    ) -> List[Dict[str, Any]]:
        """
        Fetch dockets by judge name (CORRECTED: docket-first approach)
        
        Judge information is stored in dockets.assigned_to_str, not clusters.
        This is the correct method for finding documents by specific judges.
        """
        if not self.api_key:
            self.logger.error("No API key configured for CourtListener")
            return []
        
        # Build query parameters for docket search with correct syntax
        params = {
            "page_size": min(max_documents, 100),
            "ordering": ordering
        }
        
        if court_id:
            params["court"] = court_id
        
        if date_filed_after:
            params["date_filed__gte"] = date_filed_after
            
        if date_filed_before:
            params["date_filed__lte"] = date_filed_before
        
        try:
            self.logger.info(f"Searching dockets for judge '{judge_name}' (court: {court_id}, max: {max_documents})")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/dockets/",
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        dockets = data.get('results', [])
                        
                        self.logger.info(f"Found {len(dockets)} dockets in court '{court_id}' (total available: {data.get('count', 'unknown')})")
                        
                        # Filter for specific judge and map docket data
                        mapped_dockets = []
                        for docket in dockets:
                            assigned_to = docket.get('assigned_to_str', '')
                            if judge_name.lower() in assigned_to.lower():
                                mapped_docket = self._map_docket_data(docket)
                                mapped_dockets.append(mapped_docket)
                        
                        self.logger.info(f"Found {len(mapped_dockets)} dockets assigned to judge '{judge_name}'")
                        return mapped_dockets
                    
                    elif response.status == 401:
                        self.logger.error("Authentication failed - invalid API key")
                        return []
                    
                    elif response.status == 429:
                        self.logger.warning("Rate limit exceeded")
                        return []
                    
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Cluster search failed: HTTP {response.status} - {error_text}")
                        return []
        
        except asyncio.TimeoutError:
            self.logger.error("Request timeout while searching clusters")
            return []
        
        except Exception as e:
            self.logger.error(f"Unexpected error searching clusters: {str(e)}")
            return []
    
    def _map_docket_data(self, docket: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map docket data to our expected format with judge information
        """
        try:
            mapped_docket = {
                'docket_id': docket.get('id'),
                'case_name': docket.get('case_name'),
                'case_name_short': docket.get('case_name_short'),
                'case_name_full': docket.get('case_name_full'),
                'court_id': docket.get('court_id'),
                'date_filed': docket.get('date_filed'),
                'docket_number': docket.get('docket_number'),
                
                # Judge information (key enhancement!)
                'assigned_to_str': docket.get('assigned_to_str', ''),
                'assigned_to_id': docket.get('assigned_to'),
                'referred_to_str': docket.get('referred_to_str', ''),
                'referred_to_id': docket.get('referred_to'),
                
                # Case details
                'nature_of_suit': docket.get('nature_of_suit', ''),
                'cause': docket.get('cause', ''),
                'jurisdiction_type': docket.get('jurisdiction_type'),
                'jury_demand': docket.get('jury_demand', ''),
                'date_terminated': docket.get('date_terminated'),
                'date_last_filing': docket.get('date_last_filing'),
                
                # Source and PACER info
                'source': docket.get('source'),
                'pacer_case_id': docket.get('pacer_case_id'),
                'absolute_url': docket.get('absolute_url'),
                'date_created': self._parse_date(docket.get('date_created')),
                'date_modified': self._parse_date(docket.get('date_modified')),
                
                # Processing metadata
                'processing_timestamp': datetime.utcnow().isoformat(),
                'data_source': 'courtlistener_dockets',
                'api_version': 'v4'
            }
            
            self.logger.debug(f"Mapped docket {mapped_docket['docket_id']}: {mapped_docket['case_name']} (Judge: {mapped_docket['assigned_to_str']})")
            
            return mapped_docket
            
        except Exception as e:
            self.logger.error(f"Failed to map docket data: {str(e)} (keys: {list(docket.keys())})") 
            return {
                'docket_id': docket.get('id'),
                'mapping_error': str(e),
                'raw_docket': docket,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    def _map_cluster_data(self, cluster: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map cluster data to our expected format with judge information
        """
        try:
            mapped_cluster = {
                'cluster_id': cluster.get('id'),
                'case_name': cluster.get('case_name'),
                'case_name_short': cluster.get('case_name_short'),
                'case_name_full': cluster.get('case_name_full'),
                'court_id': None,  # Will be extracted from docket
                'date_filed': cluster.get('date_filed'),
                'date_filed_is_approximate': cluster.get('date_filed_is_approximate', False),
                'docket_id': cluster.get('docket_id'),
                'docket_url': cluster.get('docket'),
                'slug': cluster.get('slug'),
                
                # Judge information (key enhancement!)
                'judges': cluster.get('judges', ''),
                'panel': cluster.get('panel', []),
                'non_participating_judges': cluster.get('non_participating_judges', []),
                
                # Case details
                'citations': cluster.get('citations', []),
                'citation_count': cluster.get('citation_count', 0),
                'precedential_status': cluster.get('precedential_status'),
                'nature_of_suit': cluster.get('nature_of_suit', ''),
                'attorneys': cluster.get('attorneys', ''),
                'procedural_history': cluster.get('procedural_history', ''),
                'posture': cluster.get('posture', ''),
                'syllabus': cluster.get('syllabus', ''),
                'disposition': cluster.get('disposition', ''),
                
                # Technical metadata
                'absolute_url': cluster.get('absolute_url'),
                'date_created': self._parse_date(cluster.get('date_created')),
                'date_modified': self._parse_date(cluster.get('date_modified')),
                'source': cluster.get('source'),
                'blocked': cluster.get('blocked', False),
                'date_blocked': cluster.get('date_blocked'),
                
                # Processing metadata
                'processing_timestamp': datetime.utcnow().isoformat(),
                'data_source': 'courtlistener_clusters',
                'api_version': 'v4'
            }
            
            # Extract court_id from docket if needed
            if cluster.get('docket') and not mapped_cluster['court_id']:
                # We'll fetch this in a separate method
                mapped_cluster['needs_court_enrichment'] = True
            
            self.logger.debug(f"Mapped cluster {mapped_cluster['cluster_id']}: {mapped_cluster['case_name']}")
            
            return mapped_cluster
            
        except Exception as e:
            self.logger.error(f"Failed to map cluster data: {str(e)} (keys: {list(cluster.keys())})")
            return {
                'cluster_id': cluster.get('id'),
                'mapping_error': str(e),
                'raw_cluster': cluster,
                'processing_timestamp': datetime.utcnow().isoformat()
            }
    
    async def fetch_opinions_from_clusters(
        self,
        clusters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Fetch opinion documents from cluster data
        
        Takes cluster results and fetches the actual opinion text content
        """
        if not clusters:
            return []
        
        opinions = []
        
        for cluster in clusters:
            cluster_id = cluster.get('cluster_id')
            if not cluster_id:
                continue
                
            try:
                # Fetch opinions for this cluster
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/opinions/",
                        headers=self._get_headers(),
                        params={"cluster_id": cluster_id},
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            cluster_opinions = data.get('results', [])
                            
                            for opinion in cluster_opinions:
                                # Merge cluster data with opinion data
                                enhanced_opinion = self._merge_cluster_and_opinion(cluster, opinion)
                                opinions.append(enhanced_opinion)
                                
                        else:
                            self.logger.warning(f"Failed to fetch opinions for cluster {cluster_id}: HTTP {response.status}")
                            
            except Exception as e:
                self.logger.error(f"Error fetching opinions for cluster {cluster_id}: {str(e)}")
                continue
        
        self.logger.info(f"Retrieved {len(opinions)} opinions from {len(clusters)} clusters")
        return opinions
    
    def _merge_cluster_and_opinion(self, cluster: Dict[str, Any], opinion: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge cluster metadata with opinion content
        
        This creates the complete document with both judge info and text content
        """
        # Start with the opinion data (contains text content)
        merged = self._map_courtlistener_document(opinion)
        
        # Enhance with cluster metadata (contains judge info)
        cluster_enhancements = {
            'case_name': cluster.get('case_name'),
            'case_name_short': cluster.get('case_name_short'),
            'case_name_full': cluster.get('case_name_full'),
            'date_filed': cluster.get('date_filed'),
            'judges': cluster.get('judges'),  # Key enhancement!
            'panel': cluster.get('panel'),
            'non_participating_judges': cluster.get('non_participating_judges'),
            'citations': cluster.get('citations'),
            'citation_count': cluster.get('citation_count'),
            'precedential_status': cluster.get('precedential_status'),
            'nature_of_suit': cluster.get('nature_of_suit'),
            'attorneys': cluster.get('attorneys'),
            'procedural_history': cluster.get('procedural_history'),
            'posture': cluster.get('posture'),
            'syllabus': cluster.get('syllabus'),
            'disposition': cluster.get('disposition'),
            'docket_id': cluster.get('docket_id'),
            'blocked': cluster.get('blocked'),
            'date_blocked': cluster.get('date_blocked'),
            
            # Mark as enhanced
            'cluster_enhanced': True,
            'has_judge_info': bool(cluster.get('judges'))
        }
        
        # Update merged document with cluster enhancements
        merged.update(cluster_enhancements)
        
        return merged
    
    async def fetch_opinions(
        self, 
        court_id: Optional[str] = None,
        max_documents: int = 100,
        ordering: str = "-date_filed",
        **filters
    ) -> List[Dict[str, Any]]:
        """
        Fetch opinions from CourtListener API with proper mapping
        """
        if not self.api_key:
            self.logger.error("No API key configured for CourtListener")
            return []
        
        # Build query parameters
        params = {
            "page_size": min(max_documents, 100),  # API limit
            "ordering": ordering
        }
        
        if court_id:
            params["court"] = court_id
        
        # Add any additional filters
        params.update(filters)
        
        try:
            self.logger.info(f"Fetching opinions from CourtListener (court: {court_id}, max: {max_documents})")
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/opinions/",
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        raw_documents = data.get('results', [])
                        
                        self.logger.info(f"Retrieved {len(raw_documents)} raw documents (total available: {data.get('count', 'unknown')})")
                        
                        # Map all documents
                        mapped_documents = []
                        for raw_doc in raw_documents:
                            mapped_doc = self._map_courtlistener_document(raw_doc)
                            
                            # Enrich with cluster data if needed
                            if mapped_doc.get('cluster_url') and not mapped_doc.get('court_id'):
                                cluster_data = await self.fetch_cluster_data(mapped_doc['cluster_url'])
                                if cluster_data:
                                    mapped_doc.update(cluster_data)
                            
                            mapped_documents.append(mapped_doc)
                        
                        self.logger.info(f"Mapped {len(mapped_documents)} CourtListener documents")
                        
                        return mapped_documents
                    
                    elif response.status == 401:
                        self.logger.error("Authentication failed - invalid API key")
                        return []
                    
                    elif response.status == 429:
                        self.logger.warning("Rate limit exceeded")
                        return []
                    
                    else:
                        error_text = await response.text()
                        self.logger.error(f"API request failed: HTTP {response.status} - {error_text}")
                        return []
        
        except asyncio.TimeoutError:
            self.logger.error("Request timeout while fetching opinions")
            return []
        
        except Exception as e:
            self.logger.error(f"Unexpected error fetching opinions: {str(e)}")
            return []
    
    async def fetch_opinion_by_id(self, opinion_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a specific opinion by ID"""
        if not self.api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/opinions/{opinion_id}/",
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        raw_doc = await response.json()
                        mapped_doc = self._map_courtlistener_document(raw_doc)
                        
                        # Enrich with cluster data
                        if mapped_doc.get('cluster_url'):
                            cluster_data = await self.fetch_cluster_data(mapped_doc['cluster_url'])
                            if cluster_data:
                                mapped_doc.update(cluster_data)
                        
                        return mapped_doc
                    else:
                        self.logger.error(f"Failed to fetch opinion {opinion_id}: HTTP {response.status}")
                        return None
        
        except Exception as e:
            self.logger.error(f"Error fetching opinion by ID {opinion_id}: {str(e)}")
            return None
    
    async def fetch_judge_documents(
        self,
        judge_name: str,
        court_id: Optional[str] = None,
        max_documents: int = 100,
        date_filed_after: Optional[str] = None,
        date_filed_before: Optional[str] = None,
        include_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        High-level method to fetch all documents for a specific judge
        
        Uses cluster-first approach to find judge's cases, then fetches opinion text
        """
        self.logger.info(f"Fetching documents for Judge {judge_name}")
        
        # Step 1: Find clusters by judge name
        clusters = await self.fetch_clusters_by_judge(
            judge_name=judge_name,
            court_id=court_id,
            max_documents=max_documents,
            date_filed_after=date_filed_after,
            date_filed_before=date_filed_before
        )
        
        if not clusters:
            self.logger.warning(f"No clusters found for judge {judge_name}")
            return []
        
        self.logger.info(f"Found {len(clusters)} clusters for judge {judge_name}")
        
        if not include_text:
            # Return cluster metadata only
            return clusters
        
        # Step 2: Fetch opinion text for each cluster
        opinions = await self.fetch_opinions_from_clusters(clusters)
        
        if not opinions:
            self.logger.warning(f"No opinions retrieved for judge {judge_name}")
            return clusters  # Return cluster data as fallback
        
        self.logger.info(f"Retrieved {len(opinions)} complete documents for judge {judge_name}")
        return opinions
    
    async def fetch_gilstrap_documents(
        self,
        max_documents: int = 1000,
        date_filed_after: Optional[str] = None,
        date_filed_before: Optional[str] = None,
        include_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Specialized method for Judge Gilstrap document retrieval
        
        CORRECTED: Uses docket-first approach with proper API syntax
        """
        judge_variations = [
            "Gilstrap",
            "Rodney Gilstrap"
        ]
        
        all_documents = []
        seen_docket_ids = set()
        
        for judge_name in judge_variations:
            self.logger.info(f"Searching for dockets with judge name: '{judge_name}'")
            
            try:
                # Step 1: Find dockets assigned to this judge
                dockets = await self.fetch_dockets_by_judge(
                    judge_name=judge_name,
                    court_id="txed",  # Eastern District of Texas
                    max_documents=max_documents,
                    date_filed_after=date_filed_after,
                    date_filed_before=date_filed_before
                )
                
                # Step 2: Get opinions for each docket if text is needed
                for docket in dockets:
                    docket_id = docket.get('docket_id')
                    if docket_id and docket_id not in seen_docket_ids:
                        seen_docket_ids.add(docket_id)
                        
                        if include_text:
                            # Find clusters and opinions for this docket
                            opinions = await self.fetch_opinions_for_docket(docket)
                            all_documents.extend(opinions)
                        else:
                            # Just return docket metadata
                            all_documents.append(docket)
                        
            except Exception as e:
                self.logger.error(f"Error searching for '{judge_name}': {str(e)}")
                continue
        
        # Filter for actual Gilstrap documents (verify judge name)
        gilstrap_documents = []
        for doc in all_documents:
            assigned_to = doc.get('assigned_to_str', '').lower()
            if 'gilstrap' in assigned_to:
                gilstrap_documents.append(doc)
        
        self.logger.info(f"Found {len(gilstrap_documents)} verified Gilstrap documents out of {len(all_documents)} total")
        
        return gilstrap_documents
    
    async def fetch_opinions_for_docket(self, docket: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch opinions for a specific docket
        
        Uses the corrected API approach: docket -> clusters -> opinions
        """
        docket_id = docket.get('docket_id')
        if not docket_id:
            return []
        
        try:
            # Step 1: Find clusters for this docket
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/clusters/",
                    headers=self._get_headers(),
                    params={"docket": docket_id},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        clusters = data.get('results', [])
                        
                        # Step 2: Get opinions for each cluster
                        all_opinions = []
                        for cluster in clusters:
                            cluster_opinions = await self.fetch_opinions_from_clusters([cluster])
                            
                            # Enhance opinions with docket judge information
                            for opinion in cluster_opinions:
                                opinion.update({
                                    'assigned_to_str': docket.get('assigned_to_str'),
                                    'assigned_to_id': docket.get('assigned_to_id'),
                                    'docket_enhanced': True
                                })
                                all_opinions.append(opinion)
                        
                        return all_opinions
                    else:
                        self.logger.warning(f"Failed to fetch clusters for docket {docket_id}: HTTP {response.status}")
                        return []
                        
        except Exception as e:
            self.logger.error(f"Error fetching opinions for docket {docket_id}: {str(e)}")
            return []
    
    async def test_connection(self) -> bool:
        """Test API connection and authentication"""
        if not self.api_key:
            return False
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/opinions/",
                    headers=self._get_headers(),
                    params={"page_size": 1},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    success = response.status == 200
                    if success:
                        self.logger.info("CourtListener API connection test successful")
                    else:
                        self.logger.error(f"CourtListener API connection test failed: HTTP {response.status}")
                    return success
        
        except Exception as e:
            self.logger.error(f"CourtListener API connection test error: {str(e)}")
            return False