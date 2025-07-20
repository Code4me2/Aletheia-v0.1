"""
Extracted pagination patterns from fetch_with_pagination.py
Provides robust pagination handling with rate limiting and error recovery
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, AsyncGenerator
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)


class RobustPaginator:
    """
    Handles pagination with rate limiting and error recovery
    
    Extracted from fetch_with_pagination.py for reuse across the application
    """
    
    def __init__(self, 
                 base_url: Optional[str] = None,
                 page_size: int = 20,
                 max_pages: int = 10,
                 rate_limit_delay: float = 0.5,
                 rate_limit_seconds: Optional[float] = None,  # Alias for backward compatibility
                 max_retries: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize paginator with configuration
        
        Args:
            base_url: Base URL for API requests (optional)
            page_size: Number of items per page
            max_pages: Maximum pages to fetch (safety limit)
            rate_limit_delay: Delay between page requests (seconds)
            rate_limit_seconds: Alias for rate_limit_delay (backward compatibility)
            max_retries: Maximum retry attempts for failed requests
            retry_delay: Delay between retry attempts (seconds)
        """
        self.base_url = base_url
        self.page_size = page_size
        self.max_pages = max_pages
        # Handle backward compatibility
        if rate_limit_seconds is not None:
            self.rate_limit_delay = rate_limit_seconds
        else:
            self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Statistics tracking
        self.stats = {
            'pages_fetched': 0,
            'items_fetched': 0,
            'errors': 0,
            'retries': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def fetch_with_retry(self, 
                             session: aiohttp.ClientSession, 
                             url: str, 
                             headers: Dict[str, str],
                             params: Dict[str, Any],
                             max_retries: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch a single page with exponential backoff retry
        
        Args:
            session: aiohttp session
            url: URL to fetch
            headers: Request headers
            params: Request parameters
            max_retries: Override default max_retries
            
        Returns:
            Response data or None if all retries failed
        """
        max_retries = max_retries or self.max_retries
        
        for attempt in range(max_retries + 1):
            try:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data
                    elif response.status == 403:
                        logger.warning(f"Access forbidden (403) for {url}")
                        return None
                    elif response.status == 429:  # Rate limited
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limited (429), waiting {wait_time}s before retry")
                        await asyncio.sleep(wait_time)
                        self.stats['retries'] += 1
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        if attempt < max_retries:
                            await asyncio.sleep(self.retry_delay * (attempt + 1))
                            self.stats['retries'] += 1
                            continue
                        return None
                        
            except asyncio.TimeoutError:
                logger.warning(f"Timeout on attempt {attempt + 1} for {url}")
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    self.stats['retries'] += 1
                    continue
                return None
                
            except Exception as e:
                logger.error(f"Error on attempt {attempt + 1} for {url}: {e}")
                if attempt < max_retries:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    self.stats['retries'] += 1
                    continue
                self.stats['errors'] += 1
                return None
        
        return None
    
    async def fetch_all_pages(self,
                            session: aiohttp.ClientSession,
                            base_url: str,
                            headers: Dict[str, str],
                            params: Dict[str, Any],
                            result_processor: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        Fetch all pages using pagination
        
        Args:
            session: aiohttp session
            base_url: Base URL for the API
            headers: Request headers
            params: Base request parameters
            result_processor: Optional function to process each item
            
        Returns:
            List of all items from all pages
        """
        self.stats['start_time'] = datetime.now()
        all_results = []
        page = 1
        
        logger.info(f"Starting paginated fetch from {base_url} (max_pages: {self.max_pages})")
        
        while page <= self.max_pages:
            # Add pagination parameters
            page_params = params.copy()
            page_params.update({
                'page': page,
                'page_size': self.page_size
            })
            
            logger.debug(f"Fetching page {page}...")
            
            # Fetch the page
            data = await self.fetch_with_retry(session, base_url, headers, page_params)
            
            if data is None:
                logger.warning(f"Failed to fetch page {page}, stopping pagination")
                break
            
            # Extract results
            results = data.get('results', [])
            if not results:
                logger.info(f"No results on page {page}, stopping pagination")
                break
            
            # Process results if processor provided
            if result_processor:
                processed_results = []
                for item in results:
                    try:
                        processed_item = result_processor(item)
                        if processed_item:
                            processed_results.append(processed_item)
                    except Exception as e:
                        logger.error(f"Error processing item: {e}")
                        continue
                results = processed_results
            
            all_results.extend(results)
            self.stats['pages_fetched'] += 1
            self.stats['items_fetched'] += len(results)
            
            logger.info(f"Page {page}: {len(results)} items (total: {len(all_results)})")
            
            # Check if there's a next page
            if not data.get('next'):
                logger.info("No next page, pagination complete")
                break
            
            page += 1
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Pagination complete: {len(all_results)} items from {self.stats['pages_fetched']} pages in {duration:.1f}s")
        
        return all_results
    
    async def fetch_paginated_stream(self,
                                   session: aiohttp.ClientSession,
                                   base_url: str,
                                   headers: Dict[str, str],
                                   params: Dict[str, Any],
                                   result_processor: Optional[Callable] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Stream paginated results one item at a time
        
        Useful for processing large datasets without loading everything into memory
        
        Args:
            session: aiohttp session
            base_url: Base URL for the API
            headers: Request headers
            params: Base request parameters
            result_processor: Optional function to process each item
            
        Yields:
            Individual items from paginated results
        """
        self.stats['start_time'] = datetime.now()
        page = 1
        
        logger.info(f"Starting streaming paginated fetch from {base_url}")
        
        while page <= self.max_pages:
            # Add pagination parameters
            page_params = params.copy()
            page_params.update({
                'page': page,
                'page_size': self.page_size
            })
            
            logger.debug(f"Streaming page {page}...")
            
            # Fetch the page
            data = await self.fetch_with_retry(session, base_url, headers, page_params)
            
            if data is None:
                logger.warning(f"Failed to fetch page {page}, stopping stream")
                break
            
            # Extract and yield results
            results = data.get('results', [])
            if not results:
                logger.info(f"No results on page {page}, stopping stream")
                break
            
            for item in results:
                try:
                    # Process item if processor provided
                    if result_processor:
                        processed_item = result_processor(item)
                        if processed_item:
                            yield processed_item
                    else:
                        yield item
                    
                    self.stats['items_fetched'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing/yielding item: {e}")
                    continue
            
            self.stats['pages_fetched'] += 1
            logger.debug(f"Page {page}: {len(results)} items streamed")
            
            # Check if there's a next page
            if not data.get('next'):
                logger.info("No next page, stream complete")
                break
            
            page += 1
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
        
        self.stats['end_time'] = datetime.now()
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        logger.info(f"Stream complete: {self.stats['items_fetched']} items from {self.stats['pages_fetched']} pages in {duration:.1f}s")
    
    def resume_from_checkpoint(self, checkpoint_file: str) -> int:
        """
        Resume interrupted processing from checkpoint
        
        Args:
            checkpoint_file: Path to checkpoint file
            
        Returns:
            Page number to resume from
        """
        try:
            import json
            from pathlib import Path
            
            checkpoint_path = Path(checkpoint_file)
            if not checkpoint_path.exists():
                logger.info("No checkpoint file found, starting from page 1")
                return 1
            
            with open(checkpoint_path, 'r') as f:
                checkpoint_data = json.load(f)
            
            resume_page = checkpoint_data.get('last_completed_page', 0) + 1
            logger.info(f"Resuming from checkpoint: page {resume_page}")
            
            return resume_page
            
        except Exception as e:
            logger.error(f"Error reading checkpoint file: {e}")
            return 1
    
    def save_checkpoint(self, checkpoint_file: str, page: int, additional_data: Optional[Dict] = None):
        """
        Save processing checkpoint
        
        Args:
            checkpoint_file: Path to checkpoint file
            page: Current page number
            additional_data: Optional additional data to save
        """
        try:
            import json
            from pathlib import Path
            
            checkpoint_data = {
                'last_completed_page': page,
                'timestamp': datetime.now().isoformat(),
                'stats': self.stats.copy()
            }
            
            if additional_data:
                checkpoint_data.update(additional_data)
            
            checkpoint_path = Path(checkpoint_file)
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(checkpoint_path, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            logger.debug(f"Checkpoint saved: page {page}")
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pagination statistics"""
        stats = self.stats.copy()
        
        if stats['start_time'] and stats['end_time']:
            duration = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['duration_seconds'] = duration
            
            if duration > 0:
                stats['items_per_second'] = stats['items_fetched'] / duration
                stats['pages_per_second'] = stats['pages_fetched'] / duration
        
        return stats
    
    def reset_stats(self):
        """Reset pagination statistics"""
        self.stats = {
            'pages_fetched': 0,
            'items_fetched': 0,
            'errors': 0,
            'retries': 0,
            'start_time': None,
            'end_time': None
        }


# Convenience functions for common pagination patterns

async def fetch_courtlistener_paginated(session: aiohttp.ClientSession,
                                       endpoint: str,
                                       headers: Dict[str, str],
                                       params: Dict[str, Any],
                                       max_documents: int = 1000,
                                       page_size: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience function for CourtListener API pagination
    
    Args:
        session: aiohttp session
        endpoint: API endpoint (e.g., 'opinions', 'dockets')
        headers: Request headers with Authorization
        params: Query parameters
        max_documents: Maximum documents to fetch
        page_size: Items per page
        
    Returns:
        List of all fetched items
    """
    base_url = f'https://www.courtlistener.com/api/rest/v3/{endpoint}/'
    
    # Calculate max pages needed
    max_pages = min((max_documents + page_size - 1) // page_size, 100)  # Safety limit
    
    paginator = RobustPaginator(
        page_size=page_size,
        max_pages=max_pages,
        rate_limit_delay=0.5,  # CourtListener rate limiting
        max_retries=3
    )
    
    results = await paginator.fetch_all_pages(session, base_url, headers, params)
    
    # Truncate to max_documents if needed
    if len(results) > max_documents:
        results = results[:max_documents]
    
    logger.info(f"Fetched {len(results)} items from CourtListener {endpoint}")
    return results


async def stream_courtlistener_paginated(session: aiohttp.ClientSession,
                                        endpoint: str,
                                        headers: Dict[str, str],
                                        params: Dict[str, Any],
                                        max_documents: Optional[int] = None,
                                        page_size: int = 100) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream CourtListener API results for memory-efficient processing
    
    Args:
        session: aiohttp session
        endpoint: API endpoint
        headers: Request headers
        params: Query parameters
        max_documents: Optional limit on total documents
        page_size: Items per page
        
    Yields:
        Individual items from API
    """
    base_url = f'https://www.courtlistener.com/api/rest/v3/{endpoint}/'
    
    max_pages = 1000 if max_documents is None else min((max_documents + page_size - 1) // page_size, 1000)
    
    paginator = RobustPaginator(
        page_size=page_size,
        max_pages=max_pages,
        rate_limit_delay=0.5,
        max_retries=3
    )
    
    count = 0
    async for item in paginator.fetch_paginated_stream(session, base_url, headers, params):
        yield item
        count += 1
        
        if max_documents and count >= max_documents:
            break