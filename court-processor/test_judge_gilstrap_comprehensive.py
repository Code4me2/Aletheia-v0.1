#!/usr/bin/env python3
"""
Comprehensive Judge Gilstrap Data Retrieval Test

Tests the enhanced processor's ability to fetch all textual data for 
Judge Gilstrap from the last 2 years to establish retrieval limitations.
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor
from enhanced.config import get_settings

class GilstrapDataRetrieval:
    """Comprehensive data retrieval for Judge Gilstrap"""
    
    def __init__(self):
        self.processor = EnhancedUnifiedDocumentProcessor()
        self.cl_service = self.processor.cl_service
        self.start_time = time.time()
        
        # Calculate date range (last 2 years)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=730)  # 2 years
        
        # Statistics tracking
        self.stats = {
            'total_documents': 0,
            'documents_with_text': 0,
            'total_characters': 0,
            'api_calls': 0,
            'rate_limits_hit': 0,
            'errors': 0,
            'processing_time': 0,
            'largest_document': 0,
            'smallest_document': float('inf'),
            'judges_found': set(),
            'courts_found': set(),
            'document_types': {},
            'date_range_actual': {'earliest': None, 'latest': None}
        }
        
        self.documents = []
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    def print_progress(self, current: int, total: int, message: str = ""):
        """Print progress indicator"""
        if total > 0:
            percent = (current / total) * 100
            print(f"📊 Progress: {current}/{total} ({percent:.1f}%) {message}")
        else:
            print(f"📊 {message}: {current}")
    
    async def search_gilstrap_documents(self) -> List[Dict[str, Any]]:
        """Search for all Judge Gilstrap documents in the last 2 years"""
        print("🔍 Searching for Judge Gilstrap documents...")
        print(f"📅 Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        
        all_documents = []
        page_size = 100  # Maximum allowed by CourtListener API
        total_found = None
        
        # Search strategies for Judge Gilstrap
        search_terms = [
            "Gilstrap",  # Judge's last name
            "Judge Gilstrap",
            "Hon. Gilstrap",
            "Rodney Gilstrap"
        ]
        
        # Courts where Judge Gilstrap serves (Eastern District of Texas)
        courts = ["txed"]  # Eastern District of Texas
        
        for court in courts:
            for search_term in search_terms:
                print(f"\n🔎 Searching {court} for '{search_term}'...")
                
                try:
                    # Fetch with date filtering
                    documents = await self.cl_service.fetch_opinions(
                        court_id=court,
                        max_documents=1000,  # Large batch for comprehensive search
                        q=search_term,  # Search query
                        filed_after=self.start_date.strftime('%Y-%m-%d'),
                        filed_before=self.end_date.strftime('%Y-%m-%d'),
                        ordering="-date_filed"
                    )
                    
                    self.stats['api_calls'] += 1
                    
                    if documents:
                        print(f"   ✅ Found {len(documents)} documents")
                        all_documents.extend(documents)
                        
                        # Update statistics
                        for doc in documents:
                            if doc.get('author_str'):
                                self.stats['judges_found'].add(doc['author_str'])
                            if doc.get('court_id'):
                                self.stats['courts_found'].add(doc['court_id'])
                    else:
                        print(f"   ❌ No documents found")
                        
                except Exception as e:
                    print(f"   ❌ Error searching: {str(e)}")
                    self.stats['errors'] += 1
                    
                # Rate limiting pause
                await asyncio.sleep(1)
        
        # Remove duplicates based on document ID
        unique_docs = {}
        for doc in all_documents:
            if doc.get('id') and doc['id'] not in unique_docs:
                unique_docs[doc['id']] = doc
        
        self.documents = list(unique_docs.values())
        self.stats['total_documents'] = len(self.documents)
        
        print(f"\n📊 Total unique documents found: {self.stats['total_documents']}")
        return self.documents
    
    def analyze_document_metadata(self) -> Dict[str, Any]:
        """Analyze document metadata to understand the dataset"""
        print("\n📊 Analyzing document metadata...")
        
        analysis = {
            'date_distribution': {},
            'judge_distribution': {},
            'document_types': {},
            'text_availability': {'with_text': 0, 'without_text': 0},
            'text_length_distribution': {'ranges': {}, 'stats': {}}
        }
        
        text_lengths = []
        
        for doc in self.documents:
            # Date distribution
            date_filed = doc.get('date_filed') or doc.get('date_created', '')
            if date_filed:
                year_month = date_filed[:7]  # YYYY-MM format
                analysis['date_distribution'][year_month] = analysis['date_distribution'].get(year_month, 0) + 1
                
                # Track actual date range
                if not self.stats['date_range_actual']['earliest'] or date_filed < self.stats['date_range_actual']['earliest']:
                    self.stats['date_range_actual']['earliest'] = date_filed
                if not self.stats['date_range_actual']['latest'] or date_filed > self.stats['date_range_actual']['latest']:
                    self.stats['date_range_actual']['latest'] = date_filed
            
            # Judge distribution
            author = doc.get('author_str', 'Unknown')
            analysis['judge_distribution'][author] = analysis['judge_distribution'].get(author, 0) + 1
            
            # Document types
            doc_type = doc.get('type', 'unknown')
            analysis['document_types'][doc_type] = analysis['document_types'].get(doc_type, 0) + 1
            
            # Text availability and length
            plain_text = doc.get('plain_text', '')
            if plain_text and plain_text.strip():
                analysis['text_availability']['with_text'] += 1
                text_length = len(plain_text)
                text_lengths.append(text_length)
                
                self.stats['total_characters'] += text_length
                if text_length > self.stats['largest_document']:
                    self.stats['largest_document'] = text_length
                if text_length < self.stats['smallest_document']:
                    self.stats['smallest_document'] = text_length
            else:
                analysis['text_availability']['without_text'] += 1
        
        # Calculate text length statistics
        if text_lengths:
            text_lengths.sort()
            n = len(text_lengths)
            analysis['text_length_distribution']['stats'] = {
                'mean': sum(text_lengths) / n,
                'median': text_lengths[n//2],
                'min': min(text_lengths),
                'max': max(text_lengths),
                'total': sum(text_lengths)
            }
            
            # Length ranges
            ranges = [
                (0, 1000, 'Very Short (0-1K)'),
                (1001, 10000, 'Short (1K-10K)'),
                (10001, 50000, 'Medium (10K-50K)'),
                (50001, 100000, 'Long (50K-100K)'),
                (100001, float('inf'), 'Very Long (100K+)')
            ]
            
            for min_len, max_len, label in ranges:
                count = sum(1 for length in text_lengths if min_len <= length <= max_len)
                analysis['text_length_distribution']['ranges'][label] = count
        
        self.stats['documents_with_text'] = analysis['text_availability']['with_text']
        
        return analysis
    
    async def process_sample_documents(self, sample_size: int = 5) -> List[Dict[str, Any]]:
        """Process a sample of documents through the full pipeline"""
        print(f"\n🔄 Processing {sample_size} sample documents through full pipeline...")
        
        # Select sample documents with text
        documents_with_text = [doc for doc in self.documents if doc.get('plain_text', '').strip()]
        sample_docs = documents_with_text[:sample_size] if len(documents_with_text) >= sample_size else documents_with_text
        
        processed_results = []
        
        for i, doc in enumerate(sample_docs):
            try:
                print(f"   📄 Processing document {i+1}/{len(sample_docs)}: ID {doc.get('id')}")
                
                start_time = time.time()
                result = await self.processor.process_single_document(doc)
                processing_time = time.time() - start_time
                
                if 'saved_id' in result:
                    print(f"      ✅ Processed successfully in {processing_time:.2f}s")
                    print(f"      💾 Saved with ID: {result['saved_id']}")
                    print(f"      📚 Citations found: {len(result.get('citations', []))}")
                    
                    processed_results.append({
                        'original_id': doc.get('id'),
                        'saved_id': result['saved_id'],
                        'processing_time': processing_time,
                        'citations_count': len(result.get('citations', [])),
                        'success': True
                    })
                else:
                    print(f"      ❌ Processing failed: {result.get('error')}")
                    processed_results.append({
                        'original_id': doc.get('id'),
                        'error': result.get('error'),
                        'processing_time': processing_time,
                        'success': False
                    })
                    
            except Exception as e:
                print(f"      ❌ Exception during processing: {str(e)}")
                processed_results.append({
                    'original_id': doc.get('id'),
                    'error': str(e),
                    'success': False
                })
        
        return processed_results
    
    def print_limitations_analysis(self, analysis: Dict[str, Any]):
        """Print comprehensive limitations analysis"""
        self.print_header("RETRIEVAL LIMITATIONS ANALYSIS")
        
        print("📊 **Data Availability:**")
        print(f"   • Total documents found: {self.stats['total_documents']}")
        print(f"   • Documents with text: {self.stats['documents_with_text']}")
        print(f"   • Text availability rate: {(self.stats['documents_with_text']/max(self.stats['total_documents'], 1))*100:.1f}%")
        
        print(f"\n📅 **Date Range Coverage:**")
        print(f"   • Requested: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        print(f"   • Actual: {self.stats['date_range_actual']['earliest']} to {self.stats['date_range_actual']['latest']}")
        
        print(f"\n📈 **Volume Statistics:**")
        print(f"   • Total characters: {self.stats['total_characters']:,}")
        print(f"   • Average document size: {(self.stats['total_characters']/max(self.stats['documents_with_text'], 1)):,.0f} characters")
        print(f"   • Largest document: {self.stats['largest_document']:,} characters")
        if self.stats['smallest_document'] != float('inf'):
            print(f"   • Smallest document: {self.stats['smallest_document']:,} characters")
        
        print(f"\n🔧 **API Performance:**")
        print(f"   • API calls made: {self.stats['api_calls']}")
        print(f"   • Rate limits hit: {self.stats['rate_limits_hit']}")
        print(f"   • Errors encountered: {self.stats['errors']}")
        print(f"   • Total processing time: {time.time() - self.start_time:.1f}s")
        
        print(f"\n👥 **Judge Distribution:**")
        for judge, count in sorted(analysis['judge_distribution'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   • {judge}: {count} documents")
        
        print(f"\n📄 **Document Types:**")
        for doc_type, count in sorted(analysis['document_types'].items(), key=lambda x: x[1], reverse=True):
            print(f"   • {doc_type}: {count} documents")
        
        print(f"\n📏 **Text Length Distribution:**")
        for range_label, count in analysis['text_length_distribution']['ranges'].items():
            print(f"   • {range_label}: {count} documents")
    
    def generate_recommendations(self) -> List[str]:
        """Generate recommendations based on limitations found"""
        recommendations = []
        
        # Text availability
        text_rate = (self.stats['documents_with_text']/max(self.stats['total_documents'], 1))*100
        if text_rate < 80:
            recommendations.append(
                f"⚠️  **Low text availability ({text_rate:.1f}%)** - Consider PDF extraction pipeline for missing text"
            )
        
        # Volume considerations
        if self.stats['total_characters'] > 10_000_000:  # 10MB+
            recommendations.append(
                "📊 **Large dataset detected** - Consider batch processing and pagination strategies"
            )
        
        # Date coverage
        if self.stats['total_documents'] < 50:
            recommendations.append(
                "📅 **Low document count** - May need broader search terms or different courts"
            )
        
        # API efficiency
        if self.stats['errors'] > 0:
            recommendations.append(
                f"🔧 **{self.stats['errors']} API errors** - Implement retry logic and error handling"
            )
        
        # Judge specificity
        gilstrap_docs = sum(1 for judge in self.stats['judges_found'] if 'gilstrap' in judge.lower())
        if gilstrap_docs == 0:
            recommendations.append(
                "🎯 **No Gilstrap documents found** - Search strategy needs refinement"
            )
        
        # Performance
        if len(self.documents) > 0:
            time_per_doc = (time.time() - self.start_time) / len(self.documents)
            if time_per_doc > 2:
                recommendations.append(
                    f"⏱️  **Slow processing ({time_per_doc:.1f}s/doc)** - Consider async optimization"
                )
        
        return recommendations

async def run_comprehensive_test():
    """Run comprehensive Judge Gilstrap data retrieval test"""
    retrieval = GilstrapDataRetrieval()
    
    retrieval.print_header("JUDGE GILSTRAP COMPREHENSIVE DATA RETRIEVAL TEST")
    print("🎯 Objective: Establish retrieval limitations for Judge Gilstrap's textual data (last 2 years)")
    print(f"📅 Date range: {retrieval.start_date.strftime('%Y-%m-%d')} to {retrieval.end_date.strftime('%Y-%m-%d')}")
    
    # Step 1: Search for documents
    retrieval.print_header("STEP 1: DOCUMENT DISCOVERY")
    documents = await retrieval.search_gilstrap_documents()
    
    if not documents:
        print("❌ No documents found. Unable to proceed with analysis.")
        return False
    
    # Step 2: Analyze metadata
    retrieval.print_header("STEP 2: METADATA ANALYSIS")
    analysis = retrieval.analyze_document_metadata()
    
    # Step 3: Process sample documents
    retrieval.print_header("STEP 3: PIPELINE PROCESSING TEST")
    sample_results = await retrieval.process_sample_documents(5)
    
    # Step 4: Limitations analysis
    retrieval.print_limitations_analysis(analysis)
    
    # Step 5: Recommendations
    retrieval.print_header("RECOMMENDATIONS")
    recommendations = retrieval.generate_recommendations()
    
    if recommendations:
        for rec in recommendations:
            print(f"   {rec}")
    else:
        print("   ✅ No major limitations identified!")
    
    # Step 6: Summary
    retrieval.print_header("EXECUTIVE SUMMARY")
    print(f"📊 **Dataset Summary:**")
    print(f"   • {retrieval.stats['total_documents']} documents found")
    print(f"   • {retrieval.stats['documents_with_text']} with full text")
    print(f"   • {retrieval.stats['total_characters']:,} total characters")
    print(f"   • {len(retrieval.stats['judges_found'])} unique judges")
    print(f"   • {retrieval.stats['api_calls']} API calls required")
    
    successful_processing = sum(1 for r in sample_results if r.get('success'))
    print(f"\n🔄 **Processing Results:**")
    print(f"   • {successful_processing}/{len(sample_results)} sample documents processed successfully")
    
    if sample_results:
        avg_time = sum(r.get('processing_time', 0) for r in sample_results) / len(sample_results)
        print(f"   • Average processing time: {avg_time:.2f}s per document")
    
    total_time = time.time() - retrieval.start_time
    print(f"\n⏱️  **Total Test Duration:** {total_time:.1f}s")
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 Starting comprehensive Judge Gilstrap data retrieval test...")
        success = asyncio.run(run_comprehensive_test())
        
        if success:
            print("\n✅ Comprehensive test completed successfully!")
        else:
            print("\n❌ Test failed - see errors above")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)