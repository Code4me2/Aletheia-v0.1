"""
Enhanced retry logic for handling CourtListener 202 responses

This module provides improved retry mechanisms with:
- Exponential backoff with jitter
- Configurable retry strategies
- Detailed logging for debugging
- Content validation after retries
"""

import asyncio
import aiohttp
import logging
import random
from typing import Optional, Dict, Callable, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry behavior"""
    def __init__(
        self,
        max_attempts: int = 5,
        initial_delay: float = 2.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retry_on_statuses: list = None
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retry_on_statuses = retry_on_statuses or [202, 429, 500, 502, 503, 504]


class RetryStats:
    """Track retry statistics for analysis"""
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.retry_counts = {}  # URL -> retry count
        self.status_counts = {}  # status code -> count
        self.total_retry_time = 0
        self.content_retrieved_after_retry = 0
        
    def log_attempt(self, url: str, status: int, attempt: int, delay: float = 0):
        """Log a retry attempt"""
        self.total_requests += 1
        self.status_counts[status] = self.status_counts.get(status, 0) + 1
        
        if url not in self.retry_counts:
            self.retry_counts[url] = 0
        if attempt > 0:
            self.retry_counts[url] = attempt
            self.total_retry_time += delay
            
    def log_success(self, url: str, had_content: bool, after_retry: bool):
        """Log successful retrieval"""
        self.successful_requests += 1
        if after_retry and had_content:
            self.content_retrieved_after_retry += 1
            
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics"""
        retry_urls = [url for url, count in self.retry_counts.items() if count > 0]
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'retry_rate': len(retry_urls) / max(1, self.total_requests) * 100,
            'content_after_retry_rate': self.content_retrieved_after_retry / max(1, len(retry_urls)) * 100,
            'avg_retries': sum(self.retry_counts.values()) / max(1, len(retry_urls)),
            'total_retry_time_seconds': self.total_retry_time,
            'status_distribution': self.status_counts,
            'urls_requiring_retry': len(retry_urls)
        }


class EnhancedRetryClient:
    """HTTP client with enhanced retry capabilities"""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.stats = RetryStats()
        
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter"""
        delay = min(
            self.config.initial_delay * (self.config.backoff_factor ** attempt),
            self.config.max_delay
        )
        
        if self.config.jitter:
            # Add jitter: ±25% of the delay
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
            
        return max(0.1, delay)  # Ensure minimum delay
        
    async def fetch_with_retry(
        self,
        session: aiohttp.ClientSession,
        url: str,
        headers: Optional[Dict] = None,
        validate_content: Optional[Callable[[Dict], bool]] = None
    ) -> Optional[Dict]:
        """
        Fetch URL with enhanced retry logic
        
        Args:
            session: aiohttp session
            url: URL to fetch
            headers: Request headers
            validate_content: Optional function to validate response content
            
        Returns:
            Response data or None if all retries failed
        """
        start_time = datetime.now()
        
        for attempt in range(self.config.max_attempts):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt - 1)
                    logger.info(
                        f"Retry {attempt}/{self.config.max_attempts} for {url} "
                        f"after {delay:.1f}s delay"
                    )
                    await asyncio.sleep(delay)
                    self.stats.total_retry_time += delay
                
                async with session.get(url, headers=headers) as response:
                    status = response.status
                    self.stats.log_attempt(url, status, attempt)
                    
                    if status == 200:
                        data = await response.json()
                        
                        # Validate content if validator provided
                        if validate_content and not validate_content(data):
                            logger.warning(
                                f"Content validation failed for {url}, "
                                f"attempt {attempt + 1}/{self.config.max_attempts}"
                            )
                            if attempt < self.config.max_attempts - 1:
                                continue
                        
                        # Success!
                        elapsed = (datetime.now() - start_time).total_seconds()
                        logger.info(
                            f"Successfully fetched {url} after {attempt + 1} attempts "
                            f"({elapsed:.1f}s total)"
                        )
                        
                        has_content = bool(data.get('plain_text') or data.get('html'))
                        self.stats.log_success(url, has_content, attempt > 0)
                        
                        return data
                        
                    elif status in self.config.retry_on_statuses:
                        if status == 202:
                            logger.info(
                                f"Document still processing (202) for {url}, "
                                f"attempt {attempt + 1}/{self.config.max_attempts}"
                            )
                        elif status == 429:
                            logger.warning(f"Rate limited (429) for {url}")
                        else:
                            logger.warning(
                                f"Retryable error {status} for {url}, "
                                f"attempt {attempt + 1}/{self.config.max_attempts}"
                            )
                        
                        if attempt == self.config.max_attempts - 1:
                            logger.error(
                                f"Max retries reached for {url} with status {status}"
                            )
                    else:
                        logger.error(f"Non-retryable status {status} for {url}")
                        return None
                        
            except asyncio.TimeoutError:
                logger.error(f"Timeout for {url}, attempt {attempt + 1}")
                if attempt == self.config.max_attempts - 1:
                    return None
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}, attempt {attempt + 1}")
                if attempt == self.config.max_attempts - 1:
                    return None
        
        # All retries exhausted
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.error(f"Failed to fetch {url} after {self.config.max_attempts} attempts ({elapsed:.1f}s total)")
        return None
        
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get retry statistics summary"""
        return self.stats.get_summary()


# Content validators for CourtListener responses
def validate_opinion_content(data: Dict) -> bool:
    """Validate that opinion has actual content"""
    if not data:
        return False
        
    # Check for text content
    has_text = bool(
        data.get('plain_text') or 
        data.get('html') or 
        data.get('html_lawbox') or
        data.get('html_columbia') or
        data.get('html_with_citations')
    )
    
    # Check if it's marked as unavailable
    is_unavailable = (
        data.get('plain_text', '').strip().lower() == 'unavailable' or
        data.get('sha1') == ''  # Empty SHA1 often indicates no content
    )
    
    return has_text and not is_unavailable


def validate_cluster_content(data: Dict) -> bool:
    """Validate cluster data"""
    return bool(data and data.get('docket'))


def validate_docket_content(data: Dict) -> bool:
    """Validate docket data"""
    return bool(data and (data.get('assigned_to_str') or data.get('assigned_to')))