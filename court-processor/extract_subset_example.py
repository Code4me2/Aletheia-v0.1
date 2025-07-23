#!/usr/bin/env python3
"""
Example: Extract Specific Subsets Through Complete Pipeline
Demonstrates best practices for subset extraction from CourtListener to Haystack
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import aiohttp
from pathlib import Path

# Import our services
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from services.service_config import SERVICES, COURTLISTENER_API_TOKEN
from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SubsetExtractor:
    """
    Handles extraction of specific subsets from CourtListener through the pipeline
    """
    
    def __init__(self, api_token: str = None):
        self.api_token = api_token or COURTLISTENER_API_TOKEN
        self.base_url = "https://www.courtlistener.com/api/rest/v3"
        self.checkpoint_file = Path("extraction_checkpoint.json")
        self.metrics = {
            'api_calls': 0,
            'documents_fetched': 0,
            'documents_processed': 0,
            'courts_processed': [],
            'errors': []
        }
    
    async def extract_ip_cases_by_court(self, 
                                       courts: List[str],
                                       start_date: str,
                                       end_date: Optional[str] = None,
                                       limit: int = 1000) -> Dict[str, Any]:
        """
        Extract IP cases from specific courts
        
        Example: Extract patent cases from Eastern District of Texas
        """
        logger.info(f"Extracting IP cases from {len(courts)} courts")
        
        # IP Nature of Suit codes
        ip_nos_codes = ['820', '830', '835', '840']  # Copyright, Patent, Patent-ANDA, Trademark
        
        all_results = []
        
        for court in courts:
            logger.info(f"Processing court: {court}")
            
            # Build query
            query_parts = [f'nos_code:{code}' for code in ip_nos_codes]
            query = f"({' OR '.join(query_parts)})"
            
            params = {
                'q': query,
                'court': court,
                'filed_after': start_date,
                'order_by': '-date_filed',
                'page_size': min(100, limit)  # API max is 100
            }
            
            if end_date:
                params['filed_before'] = end_date
            
            # Fetch documents
            court_docs = await self._fetch_with_pagination(
                endpoint='search',
                params=params,
                limit=limit
            )
            
            all_results.extend(court_docs)
            self.metrics['courts_processed'].append(court)
            
            logger.info(f"Found {len(court_docs)} IP cases in {court}")
        
        return {
            'documents': all_results,
            'total': len(all_results),
            'metrics': self.metrics
        }
    
    async def extract_judge_specific_cases(self,
                                         judge_name: str,
                                         court: Optional[str] = None,
                                         case_types: Optional[List[str]] = None,
                                         start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract cases from a specific judge
        
        Example: All patent cases from Judge Gilstrap since 2023
        """
        logger.info(f"Extracting cases for judge: {judge_name}")
        
        # Build query
        query_parts = [f'judge:{judge_name}']
        
        if case_types:
            type_query = ' OR '.join([f'nos_code:{ct}' for ct in case_types])
            query_parts.append(f'({type_query})')
        
        params = {
            'q': ' AND '.join(query_parts),
            'order_by': '-date_filed',
            'page_size': 100
        }
        
        if court:
            params['court'] = court
        if start_date:
            params['filed_after'] = start_date
        
        results = await self._fetch_with_pagination(
            endpoint='search',
            params=params,
            limit=5000  # Reasonable limit for single judge
        )
        
        return {
            'documents': results,
            'total': len(results),
            'judge': judge_name,
            'metrics': self.metrics
        }
    
    async def extract_recent_high_impact_cases(self,
                                             days_back: int = 30,
                                             min_docket_entries: int = 50) -> Dict[str, Any]:
        """
        Extract recent cases with high activity (many docket entries)
        """
        logger.info(f"Extracting high-impact cases from last {days_back} days")
        
        start_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        params = {
            'filed_after': start_date,
            'order_by': '-entry_count',  # Order by docket activity
            'page_size': 100
        }
        
        # Fetch cases
        all_cases = await self._fetch_with_pagination(
            endpoint='search',
            params=params,
            limit=1000
        )
        
        # Filter for high activity
        high_impact = [
            case for case in all_cases
            if case.get('entry_count', 0) >= min_docket_entries
        ]
        
        logger.info(f"Found {len(high_impact)} high-impact cases out of {len(all_cases)}")
        
        return {
            'documents': high_impact,
            'total': len(high_impact),
            'metrics': self.metrics
        }
    
    async def extract_citation_rich_opinions(self,
                                           court: str,
                                           min_citations: int = 20,
                                           start_date: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract opinions with many citations (good for precedent analysis)
        """
        logger.info(f"Extracting citation-rich opinions from {court}")
        
        # First get opinions
        params = {
            'court': court,
            'type': 'opinion',  # Only opinions, not orders
            'order_by': '-date_filed',
            'page_size': 100
        }
        
        if start_date:
            params['filed_after'] = start_date
        
        opinions = await self._fetch_with_pagination(
            endpoint='opinions',
            params=params,
            limit=500
        )
        
        # Process through pipeline to count citations
        pipeline = OptimizedElevenStagePipeline()
        citation_rich = []
        
        for batch in self._chunk_list(opinions, 10):
            results = await pipeline.process_batch(
                documents=batch,
                source='courtlistener_api'
            )
            
            # Filter for citation-rich
            for doc in results.get('enhanced_documents', []):
                if doc.get('citations_extracted', {}).get('count', 0) >= min_citations:
                    citation_rich.append(doc)
        
        return {
            'documents': citation_rich,
            'total': len(citation_rich),
            'metrics': self.metrics
        }
    
    async def _fetch_with_pagination(self, 
                                   endpoint: str, 
                                   params: Dict[str, Any],
                                   limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Fetch data with cursor-based pagination
        """
        headers = {
            'Authorization': f'Token {self.api_token}'
        }
        
        all_results = []
        next_url = f"{self.base_url}/{endpoint}/"
        
        async with aiohttp.ClientSession() as session:
            while next_url and len(all_results) < limit:
                try:
                    self.metrics['api_calls'] += 1
                    
                    # Use params only for first request
                    if next_url == f"{self.base_url}/{endpoint}/":
                        async with session.get(next_url, params=params, headers=headers) as response:
                            response.raise_for_status()
                            data = await response.json()
                    else:
                        async with session.get(next_url, headers=headers) as response:
                            response.raise_for_status()
                            data = await response.json()
                    
                    results = data.get('results', [])
                    all_results.extend(results)
                    self.metrics['documents_fetched'] += len(results)
                    
                    next_url = data.get('next')
                    
                    # Rate limiting
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"API error: {e}")
                    self.metrics['errors'].append(str(e))
                    break
        
        return all_results[:limit]
    
    def _chunk_list(self, lst: List[Any], chunk_size: int) -> List[List[Any]]:
        """Split list into chunks"""
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]
    
    def save_checkpoint(self, last_processed_id: str):
        """Save progress for resume capability"""
        checkpoint = {
            'last_processed_id': last_processed_id,
            'timestamp': datetime.now().isoformat(),
            'metrics': self.metrics
        }
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoint, f)
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load previous checkpoint"""
        if self.checkpoint_file.exists():
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        return None


async def main():
    """
    Demonstrate various subset extraction patterns
    """
    extractor = SubsetExtractor()
    
    print("=" * 80)
    print("SUBSET EXTRACTION EXAMPLES")
    print("=" * 80)
    
    # Example 1: Extract patent cases from key districts
    print("\n1. Extracting patent cases from Eastern District of Texas (2024)")
    ip_results = await extractor.extract_ip_cases_by_court(
        courts=['txed'],
        start_date='2024-01-01',
        limit=100
    )
    print(f"   Found: {ip_results['total']} patent cases")
    
    # Example 2: Extract Judge Gilstrap's patent cases
    print("\n2. Extracting Judge Gilstrap's patent cases")
    gilstrap_results = await extractor.extract_judge_specific_cases(
        judge_name='gilstrap',
        court='txed',
        case_types=['830'],  # Patent
        start_date='2023-01-01'
    )
    print(f"   Found: {gilstrap_results['total']} cases")
    
    # Example 3: Recent high-impact cases
    print("\n3. Extracting recent high-impact cases (last 30 days)")
    high_impact_results = await extractor.extract_recent_high_impact_cases(
        days_back=30,
        min_docket_entries=25
    )
    print(f"   Found: {high_impact_results['total']} high-activity cases")
    
    # Show metrics
    print("\n" + "=" * 80)
    print("EXTRACTION METRICS")
    print("=" * 80)
    print(f"Total API calls: {extractor.metrics['api_calls']}")
    print(f"Documents fetched: {extractor.metrics['documents_fetched']}")
    print(f"Courts processed: {', '.join(extractor.metrics['courts_processed'])}")
    if extractor.metrics['errors']:
        print(f"Errors encountered: {len(extractor.metrics['errors'])}")
    
    # Process through pipeline
    if ip_results['documents']:
        print("\n" + "=" * 80)
        print("PROCESSING THROUGH ENHANCEMENT PIPELINE")
        print("=" * 80)
        
        pipeline = OptimizedElevenStagePipeline()
        pipeline_results = await pipeline.process_batch(
            limit=10,  # Process first 10
            documents=ip_results['documents'][:10]
        )
        
        print(f"Pipeline success: {pipeline_results['success']}")
        print(f"Completeness score: {pipeline_results['verification']['completeness_score']:.1f}%")
        print(f"Enhancements per document: {pipeline_results['enhancements_per_document']:.1f}")


if __name__ == "__main__":
    asyncio.run(main()