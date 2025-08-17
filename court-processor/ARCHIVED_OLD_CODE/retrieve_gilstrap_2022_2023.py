#!/usr/bin/env python3
"""
Retrieve Judge Rodney Gilstrap Cases from E.D. Texas (2022-2023)

This script focuses on retrieving Judge Gilstrap's cases from the Eastern District of Texas
for the years 2022-2023, with emphasis on patent cases.
"""

import asyncio
import os
import logging
from datetime import datetime
import json
from typing import Dict, Any, List
import sys

# Add parent directories to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Set up environment - using the API key from the existing script
os.environ['COURTLISTENER_API_KEY'] = os.getenv('COURTLISTENER_API_KEY', 'f751990518aacab953214f2e56ac6ccbff9e2c14')

from services.document_ingestion_service import DocumentIngestionService
from services.courtlistener_service import CourtListenerService
from court_processor_orchestrator import CourtProcessorOrchestrator
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GilstrapRetriever:
    """Specialized retriever for Judge Rodney Gilstrap cases"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        self.stats = {
            'total_cases_found': 0,
            'gilstrap_opinions': 0,
            'gilstrap_dockets': 0,
            'patent_cases': 0,
            'opinions_retrieved': 0,
            'dockets_retrieved': 0,
            'pdfs_extracted': 0,
            'total_text_chars': 0,
            'by_year': {}
        }
    
    async def retrieve_gilstrap_cases(self, start_year: int = 2022, end_year: int = 2023):
        """
        Retrieve Judge Gilstrap's cases from E.D. Texas for specified years
        
        Strategy:
        1. Search specifically for "Gilstrap" in E.D. Texas opinions
        2. Search for patent dockets assigned to Gilstrap
        3. Extract text from PDFs when available
        4. Process through the 11-stage pipeline
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"RETRIEVING JUDGE RODNEY GILSTRAP CASES (E.D. TEXAS)")
        logger.info(f"Date Range: {start_year}-{end_year}")
        logger.info(f"{'='*80}")
        logger.info(f"Current date: {datetime.now().strftime('%B %d, %Y')}")
        logger.info(f"Focus: Judge Rodney Gilstrap (Chief Judge, E.D. Texas)")
        logger.info(f"Primary interest: Patent cases (Nature of Suit: 830)")
        
        all_documents = []
        
        # Process year by year
        for year in range(start_year, end_year + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Year: {year}")
            logger.info(f"{'='*60}")
            
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31"
            
            self.stats['by_year'][year] = {
                'opinions': 0,
                'dockets': 0,
                'gilstrap_opinions': 0,
                'gilstrap_dockets': 0,
                'patent': 0
            }
            
            # 1. Search specifically for Gilstrap opinions
            logger.info(f"\nSearching for Judge Gilstrap opinions in {year}...")
            gilstrap_opinions = await self._search_gilstrap_opinions(year_start, year_end)
            self.stats['by_year'][year]['gilstrap_opinions'] = len(gilstrap_opinions)
            all_documents.extend(gilstrap_opinions)
            
            # 2. Search for patent dockets assigned to Gilstrap
            logger.info(f"\nSearching for patent dockets assigned to Judge Gilstrap in {year}...")
            gilstrap_dockets = await self._search_gilstrap_patent_dockets(year_start, year_end)
            self.stats['by_year'][year]['gilstrap_dockets'] = len(gilstrap_dockets)
            all_documents.extend(gilstrap_dockets)
            
            # 3. Also get general E.D. Texas opinions that might mention Gilstrap
            logger.info(f"\nFetching additional E.D. Texas opinions for {year}...")
            txed_opinions = await self._fetch_txed_opinions_with_gilstrap_check(year_start, year_end)
            self.stats['by_year'][year]['opinions'] = len(txed_opinions)
            all_documents.extend(txed_opinions)
            
            # Log year summary
            logger.info(f"\nYear {year} Summary:")
            logger.info(f"  Gilstrap opinions found: {self.stats['by_year'][year]['gilstrap_opinions']}")
            logger.info(f"  Gilstrap patent dockets: {self.stats['by_year'][year]['gilstrap_dockets']}")
            logger.info(f"  Additional E.D. Texas opinions: {self.stats['by_year'][year]['opinions']}")
            logger.info(f"  Total patent cases: {self.stats['by_year'][year]['patent']}")
        
        # Store all documents
        logger.info(f"\n\n{'='*80}")
        logger.info(f"STORING RETRIEVED DOCUMENTS")
        logger.info(f"{'='*80}")
        
        if all_documents:
            await self._store_documents(all_documents)
        
        # Generate report
        self._generate_retrieval_report()
        
        return self.stats
    
    async def _search_gilstrap_opinions(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Search specifically for opinions by Judge Gilstrap"""
        documents = []
        
        try:
            session = await self.cl_service._get_session()
            search_url = f"{self.cl_service.BASE_URL}/api/rest/v4/search/"
            
            # Search for "Gilstrap" in opinions
            params = {
                'q': 'Gilstrap OR "Rodney Gilstrap" OR "Judge Gilstrap" OR "Chief Judge Gilstrap"',
                'type': 'o',  # opinions
                'court': 'txed',
                'filed_after': date_start,
                'filed_before': date_end,
                'page_size': 20  # Get more results
            }
            
            logger.info(f"  Search query: {params['q']}")
            
            async with session.get(search_url, params=params, headers=self.cl_service.headers) as response:
                if response.status == 200:
                    results = await response.json()
                    logger.info(f"  Found {results.get('count', 0)} Gilstrap opinions")
                    
                    if results.get('results'):
                        for result in results['results']:
                            self.stats['gilstrap_opinions'] += 1
                            self.stats['opinions_retrieved'] += 1
                            
                            # Check if it's a patent case
                            case_name = result.get('caseName', '').lower()
                            if any(term in case_name for term in ['patent', 'infringement', '830', 'ip']):
                                self.stats['patent_cases'] += 1
                                self.stats['by_year'][int(date_start[:4])]['patent'] += 1
                                logger.info(f"    Patent case: {result.get('caseName', 'Unknown')}")
                            
                            # Convert to document format
                            doc = {
                                'case_number': f"OPINION-TXED-{result.get('id', '')}",
                                'document_type': 'opinion',
                                'content': result.get('snippet', ''),  # Will be expanded later
                                'metadata': {
                                    'case_name': result.get('caseName', ''),
                                    'source': 'courtlistener_search',
                                    'opinion_id': result.get('id'),
                                    'court_id': 'txed',
                                    'judge': 'Rodney Gilstrap',
                                    'date_filed': result.get('dateFiled'),
                                    'docket_number': result.get('docketNumber')
                                }
                            }
                            
                            documents.append(doc)
                            
                            # Log significant cases
                            if 'patent' in case_name:
                                logger.info(f"    Found Gilstrap patent opinion: {result.get('caseName')}")
                else:
                    logger.error(f"Search failed: {response.status}")
                    
        except Exception as e:
            logger.error(f"Error searching Gilstrap opinions: {e}")
        
        return documents
    
    async def _search_gilstrap_patent_dockets(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Search for patent dockets assigned to Judge Gilstrap"""
        documents = []
        
        try:
            # Search RECAP dockets
            dockets = await self.cl_service.fetch_recap_dockets(
                court_ids=['txed'],
                nature_of_suit=['830'],  # Patent cases
                date_filed_after=date_start,
                max_results=50
            )
            
            for docket in dockets:
                assigned_to = docket.get('assigned_to_str', '').lower()
                referred_to = docket.get('referred_to_str', '').lower()
                
                # Check if assigned to Gilstrap
                if 'gilstrap' in assigned_to or 'gilstrap' in referred_to:
                    self.stats['gilstrap_dockets'] += 1
                    self.stats['dockets_retrieved'] += 1
                    self.stats['patent_cases'] += 1
                    self.stats['by_year'][int(date_start[:4])]['patent'] += 1
                    
                    logger.info(f"    Gilstrap patent docket: {docket.get('case_name')}")
                    logger.info(f"      Docket #: {docket.get('docket_number')}")
                    logger.info(f"      Filed: {docket.get('date_filed')}")
                    
                    # Convert to document format
                    doc = {
                        'case_number': f"RECAP-TXED-{docket.get('id')}",
                        'document_type': 'docket',
                        'content': f"Docket: {docket.get('docket_number', '')}",
                        'metadata': {
                            'case_name': docket.get('case_name', ''),
                            'source': 'courtlistener_recap',
                            'docket_id': docket.get('id'),
                            'court_id': 'txed',
                            'assigned_to': 'Rodney Gilstrap',
                            'nature_of_suit': '830 - Patent',
                            'date_filed': docket.get('date_filed'),
                            'parties': docket.get('parties', [])
                        }
                    }
                    
                    documents.append(doc)
                    
        except Exception as e:
            logger.error(f"Error searching Gilstrap patent dockets: {e}")
        
        return documents
    
    async def _fetch_txed_opinions_with_gilstrap_check(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Fetch E.D. Texas opinions and check for Gilstrap authorship"""
        documents = []
        
        async with DocumentIngestionService() as service:
            # Fetch a batch of E.D. Texas opinions
            opinions = await self.cl_service.fetch_opinions(
                court_id='txed',
                date_filed_after=date_start,
                max_results=30  # Reasonable batch size
            )
            
            for opinion in opinions:
                self.stats['opinions_retrieved'] += 1
                
                # Check for Gilstrap in author field
                author = opinion.get('author_str', '').lower()
                if 'gilstrap' in author or 'jrg' in author.lower():
                    self.stats['gilstrap_opinions'] += 1
                    logger.info(f"    Found Gilstrap opinion by author field: {opinion.get('case_name')}")
                
                # Process the opinion
                processed = await service._process_opinion(opinion, 'txed')
                if processed:
                    # Check content for Gilstrap mentions
                    content = processed.get('content', '').lower()
                    if 'gilstrap' in content:
                        processed['metadata']['likely_gilstrap'] = True
                        logger.info(f"    Opinion mentions Gilstrap: {processed.get('case_name')}")
                    
                    documents.append(processed)
                    self.stats['total_text_chars'] += len(processed.get('content', ''))
        
        return documents
    
    async def _store_documents(self, documents: List[Dict[str, Any]]):
        """Store documents using the ingestion service"""
        async with DocumentIngestionService() as service:
            storage_results = await service._store_documents(documents)
            
            logger.info(f"\nStorage Results:")
            logger.info(f"  Stored: {storage_results['stored']}")
            logger.info(f"  Updated: {storage_results['updated']}")
            logger.info(f"  Failed: {storage_results['failed']}")
    
    def _generate_retrieval_report(self):
        """Generate comprehensive retrieval report"""
        
        # Calculate totals
        self.stats['total_cases_found'] = (
            self.stats['opinions_retrieved'] + 
            self.stats['dockets_retrieved']
        )
        
        # Create report
        report = {
            'retrieval_date': datetime.now().isoformat(),
            'date_range': '2022-01-01 to 2023-12-31',
            'court': 'Eastern District of Texas',
            'judge': 'Rodney Gilstrap (Chief Judge)',
            'statistics': self.stats,
            'summary': {
                'total_documents': self.stats['total_cases_found'],
                'gilstrap_opinions': self.stats['gilstrap_opinions'],
                'gilstrap_dockets': self.stats['gilstrap_dockets'],
                'patent_cases': self.stats['patent_cases'],
                'gilstrap_percentage': (
                    ((self.stats['gilstrap_opinions'] + self.stats['gilstrap_dockets']) / 
                     self.stats['total_cases_found'] * 100)
                    if self.stats['total_cases_found'] > 0 else 0
                ),
                'patent_percentage': (
                    (self.stats['patent_cases'] / self.stats['total_cases_found'] * 100)
                    if self.stats['total_cases_found'] > 0 else 0
                )
            }
        }
        
        # Save report
        report_file = f"gilstrap_retrieval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Log summary
        logger.info(f"\n\n{'='*80}")
        logger.info(f"RETRIEVAL COMPLETE - JUDGE RODNEY GILSTRAP CASES")
        logger.info(f"{'='*80}")
        logger.info(f"\nSummary:")
        logger.info(f"  Total documents retrieved: {self.stats['total_cases_found']}")
        logger.info(f"  Gilstrap opinions: {self.stats['gilstrap_opinions']}")
        logger.info(f"  Gilstrap dockets: {self.stats['gilstrap_dockets']}")
        logger.info(f"  Patent cases: {self.stats['patent_cases']} ({report['summary']['patent_percentage']:.1f}%)")
        logger.info(f"  Gilstrap case percentage: {report['summary']['gilstrap_percentage']:.1f}%")
        
        logger.info(f"\nBy Year:")
        for year, year_stats in self.stats['by_year'].items():
            logger.info(f"  {year}:")
            logger.info(f"    Gilstrap opinions: {year_stats['gilstrap_opinions']}")
            logger.info(f"    Gilstrap dockets: {year_stats['gilstrap_dockets']}")
            logger.info(f"    Patent cases: {year_stats['patent']}")
        
        logger.info(f"\nReport saved to: {report_file}")


async def process_retrieved_cases():
    """Process the retrieved cases through the 11-stage pipeline"""
    
    logger.info(f"\n\n{'='*80}")
    logger.info(f"PROCESSING RETRIEVED CASES THROUGH 11-STAGE PIPELINE")
    logger.info(f"{'='*80}")
    
    # Use the robust pipeline with PDF extraction
    pipeline = RobustElevenStagePipeline()
    
    # Process in batches
    total_processed = 0
    batch_num = 1
    
    while True:
        logger.info(f"\nProcessing batch {batch_num}...")
        
        results = await pipeline.process_batch(
            limit=20,  # Smaller batches for better monitoring
            source_table='public.court_documents',
            extract_pdfs=True  # Extract PDFs if text is missing
        )
        
        if not results['success'] or results['statistics']['documents_processed'] == 0:
            break
        
        batch_processed = results['statistics']['documents_processed']
        total_processed += batch_processed
        
        logger.info(f"  Processed: {batch_processed} documents")
        logger.info(f"  Completeness: {results['verification']['completeness_score']:.1f}%")
        logger.info(f"  Quality: {results['verification']['quality_score']:.1f}%")
        
        # Show some details about Gilstrap cases
        if results.get('documents'):
            for doc in results['documents']:
                if 'gilstrap' in str(doc.get('metadata', {})).lower():
                    logger.info(f"    Processed Gilstrap case: {doc.get('case_name')}")
        
        batch_num += 1
        
        # Reasonable limit
        if total_processed >= 100:
            logger.info("Reached processing limit (100 documents)")
            break
    
    logger.info(f"\nTotal documents processed: {total_processed}")
    
    # Send to Haystack for indexing
    if total_processed > 0:
        logger.info(f"\nDocuments have been processed and sent to Haystack for indexing")
        logger.info(f"Access Haystack at: http://localhost:8500/docs")


async def main():
    """Main entry point"""
    
    # Step 1: Retrieve Judge Gilstrap cases for 2022-2023
    retriever = GilstrapRetriever()
    retrieval_stats = await retriever.retrieve_gilstrap_cases(
        start_year=2022,
        end_year=2023
    )
    
    # Step 2: Process retrieved cases through the pipeline
    if retrieval_stats['total_cases_found'] > 0:
        logger.info(f"\nReady to process {retrieval_stats['total_cases_found']} documents")
        logger.info("Starting pipeline processing...")
        await process_retrieved_cases()
    else:
        logger.warning("No cases retrieved to process")
    
    logger.info(f"\n{'='*80}")
    logger.info("COMPLETE: Gilstrap case retrieval and ingestion finished")
    logger.info(f"{'='*80}")


if __name__ == "__main__":
    asyncio.run(main())