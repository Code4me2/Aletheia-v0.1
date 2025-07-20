#!/usr/bin/env python3
"""
Test 20 Real Gilstrap Documents with Deduplication
CourtListener → Processing → Haystack (with deduplication testing)

Focus on testing deduplication and large volume retrieval.
"""

import asyncio
import logging
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests

# Import our working standalone processor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from standalone_enhanced_processor import StandaloneEnhancedProcessor, ProcessorConfig

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gilstrap_20_docs_test")

class GilstrapTwentyDocsTest:
    """Test 20 Gilstrap documents with deduplication focus"""
    
    def __init__(self):
        self.config = ProcessorConfig()
        self.config.courtlistener_api_key = os.getenv('COURTLISTENER_API_TOKEN', '')
        
        # Initialize standalone processor
        self.processor = StandaloneEnhancedProcessor(self.config)
        
        # Stats tracking
        self.stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'haystack_ingested': 0,
            'errors': 0,
            'processing_time': 0,
            'content_volume': 0,
            'average_content_length': 0
        }
        
        # Track processed documents for deduplication testing
        self.processed_documents = []
        self.document_checksums = set()
    
    def calculate_content_checksum(self, content: str) -> str:
        """Calculate a simple checksum for content deduplication"""
        return str(hash(content))
    
    def detect_content_duplicates(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect duplicates in the document set"""
        content_checksums = {}
        duplicates = []
        
        for i, doc in enumerate(documents):
            content = doc.get('content', '')
            checksum = self.calculate_content_checksum(content)
            
            if checksum in content_checksums:
                duplicates.append({
                    'doc_index': i,
                    'duplicate_of': content_checksums[checksum],
                    'case_name': doc.get('meta', {}).get('case_name', 'Unknown'),
                    'content_length': len(content)
                })
            else:
                content_checksums[checksum] = i
        
        return {
            'total_documents': len(documents),
            'unique_documents': len(content_checksums),
            'duplicate_count': len(duplicates),
            'duplicates': duplicates
        }
    
    def analyze_document_content(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the content volume and characteristics"""
        if not documents:
            return {}
        
        content_lengths = []
        total_content = 0
        legal_issues_count = {}
        patent_cases = 0
        
        for doc in documents:
            content = doc.get('content', '')
            meta = doc.get('meta', {})
            
            content_length = len(content)
            content_lengths.append(content_length)
            total_content += content_length
            
            # Count legal issues
            legal_issues = meta.get('legal_issues', [])
            for issue in legal_issues:
                legal_issues_count[issue] = legal_issues_count.get(issue, 0) + 1
            
            # Count patent cases
            if meta.get('is_patent_case', False):
                patent_cases += 1
        
        return {
            'total_content_chars': total_content,
            'average_content_length': total_content / len(documents),
            'min_content_length': min(content_lengths),
            'max_content_length': max(content_lengths),
            'content_lengths': content_lengths,
            'legal_issues_frequency': legal_issues_count,
            'patent_cases': patent_cases,
            'patent_case_percentage': (patent_cases / len(documents)) * 100
        }
    
    async def test_deduplication_with_refetch(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test deduplication by refetching some of the same documents"""
        logger.info("Testing deduplication by refetching documents")
        
        # First batch - original documents
        original_count = len(documents)
        
        # Second batch - fetch again to test deduplication
        logger.info("Fetching documents again to test deduplication...")
        second_batch = await self.processor.process_gilstrap_documents(
            max_documents=10,  # Fetch 10 more (should have overlaps)
            court_id="txed"
        )
        
        # Combine and test deduplication
        all_documents = documents + second_batch.get('documents', [])
        
        # Use the processor's deduplication manager
        deduplicated_documents = []
        duplicate_count = 0
        
        for doc in all_documents:
            if not self.processor.dedup_manager.is_duplicate(doc):
                deduplicated_documents.append(doc)
                self.processor.dedup_manager.mark_processed(doc)
            else:
                duplicate_count += 1
        
        return {
            'original_count': original_count,
            'second_batch_count': len(second_batch.get('documents', [])),
            'total_before_dedup': len(all_documents),
            'duplicates_found': duplicate_count,
            'unique_after_dedup': len(deduplicated_documents),
            'deduplication_effectiveness': duplicate_count / len(all_documents) * 100 if all_documents else 0
        }
    
    async def test_haystack_search_quality(self, ingested_count: int) -> Dict[str, Any]:
        """Test the quality of Haystack search after ingestion"""
        
        # Test queries specifically for Gilstrap content
        test_queries = [
            "Judge Rodney Gilstrap",
            "Eastern District of Texas patent",
            "summary judgment motion",
            "claim construction Markman",
            "preliminary injunction patent",
            "obviousness anticipation",
            "infringement damages",
            "Texas Eastern District",
            "patent validity",
            "Gilstrap patent infringement"
        ]
        
        search_results = {}
        total_results = 0
        
        for query in test_queries:
            try:
                response = requests.post(
                    f"{self.config.haystack_url}/search",
                    json={"query": query, "top_k": 10},
                    timeout=15
                )
                
                if response.status_code == 200:
                    results = response.json()
                    found_docs = results.get('results', [])
                    
                    # Analyze result quality
                    gilstrap_results = 0
                    patent_results = 0
                    high_score_results = 0
                    
                    for doc in found_docs:
                        content = doc.get('content', '').lower()
                        score = doc.get('score', 0)
                        
                        if 'gilstrap' in content:
                            gilstrap_results += 1
                        if any(term in content for term in ['patent', 'infringement', 'claim']):
                            patent_results += 1
                        if score > 2.0:  # High relevance score
                            high_score_results += 1
                    
                    search_results[query] = {
                        'total_found': len(found_docs),
                        'gilstrap_matches': gilstrap_results,
                        'patent_matches': patent_results,
                        'high_score_matches': high_score_results,
                        'avg_score': sum(doc.get('score', 0) for doc in found_docs) / len(found_docs) if found_docs else 0,
                        'top_score': max(doc.get('score', 0) for doc in found_docs) if found_docs else 0
                    }
                    
                    total_results += len(found_docs)
                    
                    logger.info(f"Query '{query}': {len(found_docs)} results, {gilstrap_results} Gilstrap matches")
                    
                else:
                    search_results[query] = {'error': f"HTTP {response.status_code}"}
                    
            except Exception as e:
                search_results[query] = {'error': str(e)}
        
        return {
            'queries_tested': len(test_queries),
            'total_results_found': total_results,
            'average_results_per_query': total_results / len(test_queries),
            'search_results': search_results,
            'ingested_documents': ingested_count
        }
    
    async def run_twenty_docs_test(self) -> Dict[str, Any]:
        """Run the complete 20 documents test"""
        
        logger.info("="*80)
        logger.info("20 REAL GILSTRAP DOCUMENTS TEST")
        logger.info("="*80)
        logger.info("Focus: Large volume retrieval + Deduplication + Haystack quality")
        logger.info("")
        
        start_time = time.time()
        
        # Step 1: Fetch 20 documents
        logger.info("Step 1: Fetching 20 Gilstrap documents from CourtListener")
        processing_result = await self.processor.process_gilstrap_documents(
            max_documents=20,
            court_id="txed"
        )
        
        self.stats['total_fetched'] = processing_result['total_fetched']
        self.stats['new_documents'] = processing_result['new_documents']
        self.stats['errors'] = processing_result['errors']
        
        if not processing_result['documents']:
            logger.error("No documents fetched. Cannot continue test.")
            return {'error': 'No documents fetched'}
        
        logger.info(f"✅ Successfully fetched {len(processing_result['documents'])} documents")
        
        # Step 2: Analyze content volume
        logger.info(f"\nStep 2: Analyzing document content")
        content_analysis = self.analyze_document_content(processing_result['documents'])
        
        self.stats['content_volume'] = content_analysis.get('total_content_chars', 0)
        self.stats['average_content_length'] = content_analysis.get('average_content_length', 0)
        
        logger.info(f"✅ Total content: {content_analysis.get('total_content_chars', 0):,} characters")
        logger.info(f"✅ Average content per document: {content_analysis.get('average_content_length', 0):,.0f} characters")
        logger.info(f"✅ Patent cases: {content_analysis.get('patent_cases', 0)} ({content_analysis.get('patent_case_percentage', 0):.1f}%)")
        
        # Step 3: Test deduplication
        logger.info(f"\nStep 3: Testing deduplication")
        dedup_test = await self.test_deduplication_with_refetch(processing_result['documents'])
        
        logger.info(f"✅ Deduplication test: {dedup_test['duplicates_found']} duplicates found")
        logger.info(f"✅ Deduplication effectiveness: {dedup_test['deduplication_effectiveness']:.1f}%")
        
        # Step 4: Ingest to Haystack
        logger.info(f"\nStep 4: Ingesting documents to Haystack")
        haystack_result = await self.processor.ingest_to_haystack(processing_result['documents'])
        
        self.stats['haystack_ingested'] = haystack_result['successful_ingestions']
        
        logger.info(f"✅ Successfully ingested {haystack_result['successful_ingestions']} documents to Haystack")
        
        # Step 5: Test Haystack search quality
        logger.info(f"\nStep 5: Testing Haystack search quality")
        search_quality = await self.test_haystack_search_quality(haystack_result['successful_ingestions'])
        
        logger.info(f"✅ Search test: {search_quality['total_results_found']} total results across {search_quality['queries_tested']} queries")
        
        # Calculate final stats
        self.stats['processing_time'] = time.time() - start_time
        
        return {
            'stats': self.stats,
            'content_analysis': content_analysis,
            'deduplication_test': dedup_test,
            'haystack_result': haystack_result,
            'search_quality': search_quality
        }
    
    def print_comprehensive_report(self, results: Dict[str, Any]):
        """Print detailed test report"""
        
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE TEST REPORT: 20 GILSTRAP DOCUMENTS")
        logger.info("="*80)
        
        stats = results.get('stats', {})
        content_analysis = results.get('content_analysis', {})
        dedup_test = results.get('deduplication_test', {})
        search_quality = results.get('search_quality', {})
        
        # Core Performance
        logger.info(f"🚀 CORE PERFORMANCE")
        logger.info(f"   Documents fetched: {stats.get('total_fetched', 0)}")
        logger.info(f"   Documents processed: {stats.get('new_documents', 0)}")
        logger.info(f"   Haystack ingested: {stats.get('haystack_ingested', 0)}")
        logger.info(f"   Processing time: {stats.get('processing_time', 0):.2f}s")
        logger.info(f"   Processing rate: {stats.get('new_documents', 0) / stats.get('processing_time', 1):.1f} docs/sec")
        
        # Content Volume Analysis
        logger.info(f"\n📊 CONTENT VOLUME ANALYSIS")
        logger.info(f"   Total content: {content_analysis.get('total_content_chars', 0):,} characters")
        logger.info(f"   Average per document: {content_analysis.get('average_content_length', 0):,.0f} characters")
        logger.info(f"   Largest document: {content_analysis.get('max_content_length', 0):,} characters")
        logger.info(f"   Smallest document: {content_analysis.get('min_content_length', 0):,} characters")
        logger.info(f"   Patent cases: {content_analysis.get('patent_cases', 0)}/{stats.get('new_documents', 0)} ({content_analysis.get('patent_case_percentage', 0):.1f}%)")
        
        # Legal Issues Frequency
        if content_analysis.get('legal_issues_frequency'):
            logger.info(f"\n⚖️ LEGAL ISSUES FREQUENCY")
            sorted_issues = sorted(content_analysis['legal_issues_frequency'].items(), key=lambda x: x[1], reverse=True)
            for issue, count in sorted_issues[:5]:  # Top 5
                logger.info(f"   {issue}: {count} cases")
        
        # Deduplication Testing
        logger.info(f"\n🔍 DEDUPLICATION TESTING")
        logger.info(f"   Original documents: {dedup_test.get('original_count', 0)}")
        logger.info(f"   Second batch: {dedup_test.get('second_batch_count', 0)}")
        logger.info(f"   Total before dedup: {dedup_test.get('total_before_dedup', 0)}")
        logger.info(f"   Duplicates detected: {dedup_test.get('duplicates_found', 0)}")
        logger.info(f"   Unique after dedup: {dedup_test.get('unique_after_dedup', 0)}")
        logger.info(f"   Deduplication effectiveness: {dedup_test.get('deduplication_effectiveness', 0):.1f}%")
        
        # Haystack Search Quality
        logger.info(f"\n🔍 HAYSTACK SEARCH QUALITY")
        logger.info(f"   Queries tested: {search_quality.get('queries_tested', 0)}")
        logger.info(f"   Total results: {search_quality.get('total_results_found', 0)}")
        logger.info(f"   Average results per query: {search_quality.get('average_results_per_query', 0):.1f}")
        
        # Top performing queries
        search_results = search_quality.get('search_results', {})
        if search_results:
            logger.info(f"\n🎯 TOP PERFORMING QUERIES")
            sorted_queries = sorted(
                [(q, r) for q, r in search_results.items() if 'error' not in r],
                key=lambda x: x[1].get('total_found', 0),
                reverse=True
            )
            for query, result in sorted_queries[:3]:
                logger.info(f"   '{query}': {result['total_found']} results (avg score: {result.get('avg_score', 0):.2f})")
        
        # Overall Success Assessment
        overall_success = (
            stats.get('new_documents', 0) >= 15 and  # At least 15 documents
            stats.get('haystack_ingested', 0) >= 15 and  # At least 15 ingested
            stats.get('content_volume', 0) > 500000 and  # At least 500k characters
            dedup_test.get('duplicates_found', 0) > 0 and  # Deduplication working
            search_quality.get('total_results_found', 0) > 50  # Good search results
        )
        
        logger.info(f"\n🏆 OVERALL ASSESSMENT")
        logger.info(f"   Result: {'✅ EXCELLENT' if overall_success else '⚠️ NEEDS IMPROVEMENT'}")
        logger.info(f"   Large volume retrieval: {'✅ SUCCESS' if stats.get('content_volume', 0) > 500000 else '❌ INSUFFICIENT'}")
        logger.info(f"   Deduplication testing: {'✅ SUCCESS' if dedup_test.get('duplicates_found', 0) > 0 else '❌ NOT TESTED'}")
        logger.info(f"   Haystack integration: {'✅ SUCCESS' if stats.get('haystack_ingested', 0) >= 15 else '❌ INSUFFICIENT'}")
        logger.info(f"   Search quality: {'✅ SUCCESS' if search_quality.get('total_results_found', 0) > 50 else '❌ INSUFFICIENT'}")
        
        logger.info("="*80)

async def main():
    """Main function"""
    
    # Create and run the test
    test_runner = GilstrapTwentyDocsTest()
    results = await test_runner.run_twenty_docs_test()
    
    # Print comprehensive report
    test_runner.print_comprehensive_report(results)
    
    return results

if __name__ == "__main__":
    asyncio.run(main())