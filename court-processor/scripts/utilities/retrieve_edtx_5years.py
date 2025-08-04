#!/usr/bin/env python3
"""
Retrieve 5 Years of Eastern District of Texas Cases (2020-2025)

This script focuses on retrieving as many E.D. Texas cases as possible,
with special attention to Judge Gilstrap's patent cases.
"""

import asyncio
import os
import logging
from datetime import datetime, timedelta
import json
from typing import Dict, Any, List

# Set up environment
os.environ['COURTLISTENER_API_KEY'] = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

from services.document_ingestion_service import DocumentIngestionService
from services.courtlistener_service import CourtListenerService
from court_processor_orchestrator import CourtProcessorOrchestrator
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EDTXBulkRetriever:
    """Specialized retriever for Eastern District of Texas cases"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        self.stats = {
            'total_cases_found': 0,
            'gilstrap_cases': 0,
            'patent_cases': 0,
            'opinions_retrieved': 0,
            'dockets_retrieved': 0,
            'pdfs_extracted': 0,
            'total_text_chars': 0,
            'by_year': {}
        }
    
    async def retrieve_edtx_cases(self, start_year: int = 2020, end_year: int = 2025):
        """
        Retrieve E.D. Texas cases from specified years
        
        Strategy:
        1. Search for all E.D. Texas opinions by year
        2. Filter for Judge Gilstrap cases
        3. Focus on patent cases (nature of suit: 830)
        4. Extract text from PDFs
        5. Process through pipeline
        """
        
        logger.info(f"\n{'='*80}")
        logger.info(f"RETRIEVING E.D. TEXAS CASES ({start_year}-{end_year})")
        logger.info(f"{'='*80}")
        logger.info(f"Current date: July 22, 2025")
        logger.info(f"Focus: Judge Rodney Gilstrap patent cases")
        
        all_documents = []
        
        # Process year by year for better control
        for year in range(start_year, end_year + 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing Year: {year}")
            logger.info(f"{'='*60}")
            
            year_start = f"{year}-01-01"
            year_end = f"{year}-12-31" if year < 2025 else "2025-07-22"
            
            self.stats['by_year'][year] = {
                'opinions': 0,
                'dockets': 0,
                'gilstrap': 0,
                'patent': 0
            }
            
            # 1. Fetch opinions
            logger.info(f"\nFetching opinions for {year}...")
            opinions = await self._fetch_year_opinions(year_start, year_end)
            self.stats['by_year'][year]['opinions'] = len(opinions)
            all_documents.extend(opinions)
            
            # 2. Search for RECAP dockets (especially patent cases)
            logger.info(f"\nSearching for patent dockets in {year}...")
            dockets = await self._fetch_patent_dockets(year_start, year_end)
            self.stats['by_year'][year]['dockets'] = len(dockets)
            all_documents.extend(dockets)
            
            # 3. Search specifically for Judge Gilstrap cases
            logger.info(f"\nSearching for Judge Gilstrap cases in {year}...")
            gilstrap_cases = await self._search_gilstrap_cases(year_start, year_end)
            self.stats['by_year'][year]['gilstrap'] = len(gilstrap_cases)
            
            # Log year summary
            logger.info(f"\nYear {year} Summary:")
            logger.info(f"  Opinions: {self.stats['by_year'][year]['opinions']}")
            logger.info(f"  Dockets: {self.stats['by_year'][year]['dockets']}")
            logger.info(f"  Gilstrap cases found: {self.stats['by_year'][year]['gilstrap']}")
        
        # Store all documents
        logger.info(f"\n\n{'='*80}")
        logger.info(f"STORING RETRIEVED DOCUMENTS")
        logger.info(f"{'='*80}")
        
        if all_documents:
            await self._store_documents(all_documents)
        
        # Generate report
        self._generate_retrieval_report()
        
        return self.stats
    
    async def _fetch_year_opinions(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Fetch all E.D. Texas opinions for a year"""
        documents = []
        
        # Use the document ingestion service
        async with DocumentIngestionService() as service:
            # Fetch opinions in batches
            page = 1
            total_pages = None
            
            while True:
                logger.info(f"  Fetching opinions page {page}...")
                
                # Direct API call for more control
                opinions = await self.cl_service.fetch_opinions(
                    court_id='txed',
                    date_filed_after=date_start,
                    max_results=100  # Max per request
                )
                
                if not opinions:
                    break
                
                # Process each opinion
                for opinion in opinions:
                    self.stats['opinions_retrieved'] += 1
                    
                    # Check for Judge Gilstrap
                    author = opinion.get('author_str', '').lower()
                    if 'gilstrap' in author:
                        self.stats['gilstrap_cases'] += 1
                    
                    # Process the opinion
                    processed = await service._process_opinion(opinion, 'txed')
                    if processed:
                        documents.append(processed)
                        self.stats['total_text_chars'] += len(processed.get('content', ''))
                
                # Check if we should continue
                if len(opinions) < 100:
                    break
                
                page += 1
                
                # Rate limiting
                await asyncio.sleep(1)
        
        return documents
    
    async def _fetch_patent_dockets(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Fetch patent-related dockets"""
        documents = []
        
        try:
            # Search for patent cases (nature of suit: 830)
            dockets = await self.cl_service.fetch_recap_dockets(
                court_ids=['txed'],
                nature_of_suit=['830'],  # Patent
                date_filed_after=date_start,
                max_results=100
            )
            
            for docket in dockets:
                self.stats['dockets_retrieved'] += 1
                
                # Check for Judge Gilstrap
                assigned_to = docket.get('assigned_to_str', '').lower()
                if 'gilstrap' in assigned_to:
                    self.stats['gilstrap_cases'] += 1
                    logger.info(f"    Found Gilstrap docket: {docket.get('case_name')}")
                
                # Convert to document format
                doc = {
                    'case_number': f"RECAP-TXED-{docket.get('id')}",
                    'case_name': docket.get('case_name', ''),
                    'document_type': 'docket',
                    'content': docket.get('docket_number', ''),  # Limited content
                    'metadata': {
                        'source': 'courtlistener_recap',
                        'docket_id': docket.get('id'),
                        'court_id': 'txed',
                        'assigned_to': assigned_to,
                        'nature_of_suit': docket.get('nature_of_suit'),
                        'date_filed': docket.get('date_filed')
                    }
                }
                
                documents.append(doc)
                self.stats['patent_cases'] += 1
        
        except Exception as e:
            logger.error(f"Error fetching patent dockets: {e}")
        
        return documents
    
    async def _search_gilstrap_cases(self, date_start: str, date_end: str) -> List[Dict[str, Any]]:
        """Search specifically for Judge Gilstrap cases"""
        gilstrap_results = []
        
        try:
            # Search for "Gilstrap" in E.D. Texas
            search_results = await self.cl_service.search_recap(
                query='Gilstrap',
                court_ids=['txed'],
                date_range=(date_start, date_end),
                max_results=50
            )
            
            for result in search_results:
                if 'gilstrap' in str(result).lower():
                    gilstrap_results.append(result)
                    
                    # Log significant cases
                    case_name = result.get('caseName', 'Unknown')
                    if 'patent' in case_name.lower() or '830' in str(result.get('natureOfSuit', '')):
                        logger.info(f"    Gilstrap patent case: {case_name}")
        
        except Exception as e:
            logger.error(f"Error searching Gilstrap cases: {e}")
        
        return gilstrap_results
    
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
            'date_range': '2020-01-01 to 2025-07-22',
            'court': 'Eastern District of Texas',
            'statistics': self.stats,
            'summary': {
                'total_documents': self.stats['total_cases_found'],
                'gilstrap_percentage': (
                    (self.stats['gilstrap_cases'] / self.stats['total_cases_found'] * 100)
                    if self.stats['total_cases_found'] > 0 else 0
                ),
                'patent_percentage': (
                    (self.stats['patent_cases'] / self.stats['total_cases_found'] * 100)
                    if self.stats['total_cases_found'] > 0 else 0
                ),
                'average_text_length': (
                    self.stats['total_text_chars'] / self.stats['total_cases_found']
                    if self.stats['total_cases_found'] > 0 else 0
                )
            }
        }
        
        # Save report
        report_file = f"edtx_5year_retrieval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Log summary
        logger.info(f"\n\n{'='*80}")
        logger.info(f"RETRIEVAL COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"\nSummary:")
        logger.info(f"  Total cases retrieved: {self.stats['total_cases_found']}")
        logger.info(f"  Judge Gilstrap cases: {self.stats['gilstrap_cases']} ({report['summary']['gilstrap_percentage']:.1f}%)")
        logger.info(f"  Patent cases: {self.stats['patent_cases']} ({report['summary']['patent_percentage']:.1f}%)")
        logger.info(f"  Total text extracted: {self.stats['total_text_chars']:,} characters")
        
        logger.info(f"\nBy Year:")
        for year, year_stats in self.stats['by_year'].items():
            logger.info(f"  {year}: {year_stats['opinions']} opinions, {year_stats['dockets']} dockets, {year_stats['gilstrap']} Gilstrap")
        
        logger.info(f"\nReport saved to: {report_file}")


async def process_retrieved_cases():
    """Process the retrieved cases through the pipeline"""
    
    logger.info(f"\n\n{'='*80}")
    logger.info(f"PROCESSING RETRIEVED CASES")
    logger.info(f"{'='*80}")
    
    # Use the orchestrator for complete processing
    config = {
        'processing': {
            'batch_size': 100,
            'extract_pdfs': True,
            'validate_strict': False  # Be lenient with validation
        }
    }
    
    orchestrator = CourtProcessorOrchestrator(config)
    
    # Run just the processing phase (documents already ingested)
    pipeline = RobustElevenStagePipeline()
    
    # Process in batches
    total_processed = 0
    batch_num = 1
    
    while True:
        logger.info(f"\nProcessing batch {batch_num}...")
        
        results = await pipeline.process_batch(
            limit=100,
            source_table='public.court_documents',
            extract_pdfs=True
        )
        
        if not results['success'] or results['statistics']['documents_processed'] == 0:
            break
        
        batch_processed = results['statistics']['documents_processed']
        total_processed += batch_processed
        
        logger.info(f"  Processed: {batch_processed} documents")
        logger.info(f"  Completeness: {results['verification']['completeness_score']:.1f}%")
        
        batch_num += 1
        
        # Don't process forever
        if batch_num > 50:  # Max 5000 documents
            logger.info("Reached processing limit")
            break
    
    logger.info(f"\nTotal documents processed: {total_processed}")


async def main():
    """Main entry point"""
    
    # Step 1: Retrieve E.D. Texas cases
    retriever = EDTXBulkRetriever()
    retrieval_stats = await retriever.retrieve_edtx_cases(
        start_year=2020,
        end_year=2025
    )
    
    # Step 2: Process retrieved cases
    if retrieval_stats['total_cases_found'] > 0:
        await process_retrieved_cases()
    else:
        logger.warning("No cases retrieved to process")


if __name__ == "__main__":
    asyncio.run(main())