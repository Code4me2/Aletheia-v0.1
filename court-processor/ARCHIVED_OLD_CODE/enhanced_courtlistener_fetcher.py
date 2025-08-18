"""
Enhanced CourtListener fetcher with proper 3-step traversal
"""
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedCourtListenerFetcher:
    """
    Fetches complete document data using 3-step traversal:
    1. Opinion -> Get text content
    2. Cluster -> Get case name and filing date
    3. Docket -> Get court ID, docket number, and judge
    """
    
    def __init__(self, cl_service):
        self.cl_service = cl_service
        self._cluster_cache = {}  # Cache clusters to avoid refetching
        self._docket_cache = {}   # Cache dockets to avoid refetching
    
    async def fetch_complete_document(self, opinion: Dict) -> Dict:
        """
        Fetch complete document data with all metadata
        
        Args:
            opinion: Opinion data from CourtListener API
            
        Returns:
            Enhanced opinion dict with _cluster and _docket data
        """
        logger.debug(f"Fetching complete data for opinion {opinion.get('id')}")
        
        # Step 1: Opinion data is already provided
        enhanced_opinion = opinion.copy()
        
        # Step 2: Fetch cluster if available
        cluster_url = opinion.get('cluster')
        if cluster_url:
            cluster = await self._fetch_cluster(cluster_url)
            if cluster:
                enhanced_opinion['_cluster'] = cluster
                
                # Step 3: Fetch docket if available
                docket_url = cluster.get('docket')
                if docket_url:
                    docket = await self._fetch_docket(docket_url)
                    if docket:
                        enhanced_opinion['_docket'] = docket
                else:
                    logger.warning(f"No docket URL in cluster for opinion {opinion.get('id')}")
            else:
                logger.error(f"Failed to fetch cluster for opinion {opinion.get('id')}")
        else:
            logger.warning(f"No cluster URL for opinion {opinion.get('id')}")
        
        return enhanced_opinion
    
    async def _fetch_cluster(self, cluster_url: str) -> Optional[Dict]:
        """Fetch cluster data with caching"""
        # Check cache first
        if cluster_url in self._cluster_cache:
            logger.debug(f"Using cached cluster: {cluster_url}")
            return self._cluster_cache[cluster_url]
        
        try:
            session = await self.cl_service._get_session()
            async with session.get(cluster_url, headers=self.cl_service.headers) as response:
                if response.status == 200:
                    cluster = await response.json()
                    # Cache the result
                    self._cluster_cache[cluster_url] = cluster
                    logger.debug(f"Fetched cluster: {cluster.get('case_name', 'Unknown')}")
                    return cluster
                else:
                    logger.error(f"Failed to fetch cluster {cluster_url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching cluster {cluster_url}: {e}")
            return None
    
    async def _fetch_docket(self, docket_url: str) -> Optional[Dict]:
        """Fetch docket data with caching"""
        # Check cache first
        if docket_url in self._docket_cache:
            logger.debug(f"Using cached docket: {docket_url}")
            return self._docket_cache[docket_url]
        
        try:
            session = await self.cl_service._get_session()
            async with session.get(docket_url, headers=self.cl_service.headers) as response:
                if response.status == 200:
                    docket = await response.json()
                    # Cache the result
                    self._docket_cache[docket_url] = docket
                    logger.debug(f"Fetched docket: {docket.get('docket_number', 'Unknown')}")
                    return docket
                else:
                    logger.error(f"Failed to fetch docket {docket_url}: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching docket {docket_url}: {e}")
            return None
    
    async def fetch_complete_batch(self, opinions: List[Dict]) -> List[Dict]:
        """
        Fetch complete data for a batch of opinions
        
        Args:
            opinions: List of opinion dicts from CourtListener
            
        Returns:
            List of enhanced opinion dicts with cluster and docket data
        """
        logger.info(f"Fetching complete data for {len(opinions)} opinions")
        
        # Process in parallel for efficiency
        tasks = [self.fetch_complete_document(op) for op in opinions]
        enhanced_opinions = await asyncio.gather(*tasks)
        
        # Log cache statistics
        logger.info(f"Cache stats - Clusters: {len(self._cluster_cache)}, Dockets: {len(self._docket_cache)}")
        
        return enhanced_opinions
    
    def extract_metadata(self, enhanced_opinion: Dict) -> Dict:
        """
        Extract all metadata from the enhanced opinion
        
        Returns dict with:
        - case_name (from cluster)
        - court_id (from docket)
        - docket_number (from docket)
        - date_filed (from cluster)
        - assigned_judge (from docket)
        - judge_initials (from docket number suffix)
        """
        metadata = {
            'case_name': None,
            'court_id': None,
            'docket_number': None,
            'date_filed': None,
            'assigned_judge': None,
            'judge_initials': None
        }
        
        # Extract from cluster
        cluster = enhanced_opinion.get('_cluster', {})
        if cluster:
            metadata['case_name'] = cluster.get('case_name')
            metadata['date_filed'] = cluster.get('date_filed')
        
        # Extract from docket
        docket = enhanced_opinion.get('_docket', {})
        if docket:
            metadata['court_id'] = docket.get('court_id') or self._extract_court_from_url(docket.get('court'))
            metadata['docket_number'] = docket.get('docket_number')
            metadata['assigned_judge'] = docket.get('assigned_to_str')
            
            # Extract judge initials from docket suffix
            if metadata['docket_number'] and '-' in metadata['docket_number']:
                suffix = metadata['docket_number'].split('-')[-1]
                if suffix and suffix.isupper() and len(suffix) <= 4:
                    metadata['judge_initials'] = suffix
        
        return metadata
    
    def _extract_court_from_url(self, court_url: str) -> Optional[str]:
        """Extract court ID from court URL if needed"""
        if court_url and '/api/rest/v4/courts/' in court_url:
            # URL format: .../api/rest/v4/courts/txed/
            parts = court_url.rstrip('/').split('/')
            if parts:
                return parts[-1]
        return None