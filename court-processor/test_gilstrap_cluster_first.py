#!/usr/bin/env python3
"""
Judge Gilstrap Cluster-First Retrieval Test

Tests the enhanced cluster-first approach for finding Judge Gilstrap's documents
using the corrected CourtListener API methodology.
"""
import asyncio
import sys
import os
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

class GilstrapClusterFirstTest:
    """Test the enhanced cluster-first Judge Gilstrap retrieval"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        self.start_time = time.time()
        
        # Calculate 2-year date range
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=730)
        
        self.stats = {
            'clusters_found': 0,
            'opinions_retrieved': 0,
            'verified_gilstrap_docs': 0,
            'total_characters': 0,
            'api_calls': 0,
            'processing_time': 0,
            'judge_variations_tested': 0,
            'unique_cases': set(),
            'date_range_coverage': {'earliest': None, 'latest': None},
            'document_types': {},
            'case_categories': {}
        }
        
        self.documents = []
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    def print_progress(self, current: int, total: int, item: str = ""):
        """Print progress with details"""
        if total > 0:
            percent = (current / total) * 100
            print(f"📊 Progress: {current}/{total} ({percent:.1f}%) {item}")
        else:
            print(f"📊 {item}: {current}")
    
    async def test_cluster_search_methods(self) -> Dict[str, Any]:
        """Test different cluster search approaches"""
        self.print_header("CLUSTER SEARCH METHODS TESTING")
        
        search_methods = {
            "direct_judge_name": "Gilstrap",
            "full_name": "Rodney Gilstrap",
            "formal_title": "Judge Gilstrap",
            "honorific": "Hon. Gilstrap"
        }
        
        method_results = {}
        
        for method_name, judge_name in search_methods.items():
            print(f"\n🔍 Testing method: {method_name} ('{judge_name}')")
            
            try:
                start_time = time.time()
                clusters = await self.cl_service.fetch_clusters_by_judge(
                    judge_name=judge_name,
                    court_id="txed",
                    max_documents=50,
                    date_filed_after=self.start_date.strftime('%Y-%m-%d'),
                    date_filed_before=self.end_date.strftime('%Y-%m-%d')
                )
                search_time = time.time() - start_time
                
                # Analyze results
                verified_clusters = []
                for cluster in clusters:
                    judges_str = cluster.get('judges', '').lower()
                    if 'gilstrap' in judges_str:
                        verified_clusters.append(cluster)
                
                print(f"   📊 Found {len(clusters)} total clusters")
                print(f"   ✅ {len(verified_clusters)} verified Gilstrap clusters")
                print(f"   ⏱️  Search time: {search_time:.2f}s")
                
                # Show sample results
                if verified_clusters:
                    sample = verified_clusters[0]
                    print(f"   📄 Sample case: {sample.get('case_name', 'Unknown')}")
                    print(f"   👨‍⚖️ Judge: {sample.get('judges', 'Unknown')}")
                    print(f"   📅 Date: {sample.get('date_filed', 'Unknown')}")
                
                method_results[method_name] = {
                    'total_clusters': len(clusters),
                    'verified_clusters': len(verified_clusters),
                    'search_time': search_time,
                    'sample_data': verified_clusters[:3] if verified_clusters else []
                }
                
                self.stats['api_calls'] += 1
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                method_results[method_name] = {
                    'error': str(e),
                    'total_clusters': 0,
                    'verified_clusters': 0
                }
        
        return method_results
    
    async def test_comprehensive_gilstrap_retrieval(self) -> List[Dict[str, Any]]:
        """Test the comprehensive Gilstrap document retrieval"""
        self.print_header("COMPREHENSIVE GILSTRAP DOCUMENT RETRIEVAL")
        
        print(f"📅 Date range: {self.start_date.strftime('%Y-%m-%d')} to {self.end_date.strftime('%Y-%m-%d')}")
        print("🎯 Using specialized fetch_gilstrap_documents method...")
        
        try:
            start_time = time.time()
            
            # Use the specialized Gilstrap method
            documents = await self.cl_service.fetch_gilstrap_documents(
                max_documents=500,  # Larger batch for comprehensive search
                date_filed_after=self.start_date.strftime('%Y-%m-%d'),
                date_filed_before=self.end_date.strftime('%Y-%m-%d'),
                include_text=True
            )
            
            retrieval_time = time.time() - start_time
            
            print(f"✅ Retrieved {len(documents)} verified Gilstrap documents")
            print(f"⏱️  Total retrieval time: {retrieval_time:.2f}s")
            
            self.documents = documents
            self.stats['opinions_retrieved'] = len(documents)
            self.stats['verified_gilstrap_docs'] = len(documents)
            self.stats['processing_time'] = retrieval_time
            
            return documents
            
        except Exception as e:
            print(f"❌ Error in comprehensive retrieval: {str(e)}")
            return []
    
    def analyze_retrieved_documents(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze the retrieved Gilstrap documents"""
        self.print_header("DOCUMENT ANALYSIS")
        
        if not documents:
            print("❌ No documents to analyze")
            return {}
        
        analysis = {
            'total_documents': len(documents),
            'date_distribution': {},
            'case_types': {},
            'text_statistics': {
                'documents_with_text': 0,
                'total_characters': 0,
                'average_length': 0,
                'longest_document': 0,
                'shortest_document': float('inf')
            },
            'judge_verification': {
                'confirmed_gilstrap': 0,
                'judge_variations_found': set()
            },
            'case_details': {
                'precedential_status': {},
                'case_name_patterns': [],
                'nature_of_suit': {}
            }
        }
        
        text_lengths = []
        
        for doc in documents:
            # Date analysis
            date_filed = doc.get('date_filed', '')
            if date_filed:
                year_month = date_filed[:7]  # YYYY-MM
                analysis['date_distribution'][year_month] = analysis['date_distribution'].get(year_month, 0) + 1
                
                # Track actual date range
                if not self.stats['date_range_coverage']['earliest'] or date_filed < self.stats['date_range_coverage']['earliest']:
                    self.stats['date_range_coverage']['earliest'] = date_filed
                if not self.stats['date_range_coverage']['latest'] or date_filed > self.stats['date_range_coverage']['latest']:
                    self.stats['date_range_coverage']['latest'] = date_filed
            
            # Judge verification
            judges_str = doc.get('judges', '')
            if 'gilstrap' in judges_str.lower():
                analysis['judge_verification']['confirmed_gilstrap'] += 1
                analysis['judge_verification']['judge_variations_found'].add(judges_str)
            
            # Text analysis
            plain_text = doc.get('plain_text', '')
            if plain_text and plain_text.strip():
                analysis['text_statistics']['documents_with_text'] += 1
                text_length = len(plain_text)
                text_lengths.append(text_length)
                analysis['text_statistics']['total_characters'] += text_length
                
                if text_length > analysis['text_statistics']['longest_document']:
                    analysis['text_statistics']['longest_document'] = text_length
                if text_length < analysis['text_statistics']['shortest_document']:
                    analysis['text_statistics']['shortest_document'] = text_length
            
            # Case details
            precedential = doc.get('precedential_status', 'Unknown')
            analysis['case_details']['precedential_status'][precedential] = analysis['case_details']['precedential_status'].get(precedential, 0) + 1
            
            nature_suit = doc.get('nature_of_suit', 'Unknown')
            if nature_suit and nature_suit.strip():
                analysis['case_details']['nature_of_suit'][nature_suit] = analysis['case_details']['nature_of_suit'].get(nature_suit, 0) + 1
            
            # Collect case names for pattern analysis
            case_name = doc.get('case_name', '')
            if case_name and len(analysis['case_details']['case_name_patterns']) < 10:
                analysis['case_details']['case_name_patterns'].append(case_name)
            
            # Track unique cases
            cluster_id = doc.get('cluster_id')
            if cluster_id:
                self.stats['unique_cases'].add(cluster_id)
        
        # Calculate averages
        if text_lengths:
            analysis['text_statistics']['average_length'] = sum(text_lengths) / len(text_lengths)
            if analysis['text_statistics']['shortest_document'] == float('inf'):
                analysis['text_statistics']['shortest_document'] = 0
        
        # Update global stats
        self.stats['total_characters'] = analysis['text_statistics']['total_characters']
        
        return analysis
    
    def print_comprehensive_results(self, method_results: Dict[str, Any], analysis: Dict[str, Any]):
        """Print comprehensive test results"""
        self.print_header("COMPREHENSIVE TEST RESULTS")
        
        print("🔍 **Search Method Performance:**")
        for method_name, result in method_results.items():
            if 'error' in result:
                print(f"   ❌ {method_name}: {result['error']}")
            else:
                print(f"   ✅ {method_name}: {result['verified_clusters']} verified clusters ({result['search_time']:.2f}s)")
        
        if analysis:
            print(f"\n📊 **Document Retrieval Summary:**")
            print(f"   • Total verified documents: {analysis['total_documents']}")
            print(f"   • Unique cases: {len(self.stats['unique_cases'])}")
            print(f"   • Documents with full text: {analysis['text_statistics']['documents_with_text']}")
            print(f"   • Total characters: {analysis['text_statistics']['total_characters']:,}")
            
            if analysis['text_statistics']['documents_with_text'] > 0:
                avg_length = analysis['text_statistics']['average_length']
                print(f"   • Average document length: {avg_length:,.0f} characters")
                print(f"   • Longest document: {analysis['text_statistics']['longest_document']:,} characters")
                print(f"   • Shortest document: {analysis['text_statistics']['shortest_document']:,} characters")
            
            print(f"\n📅 **Date Coverage:**")
            earliest = self.stats['date_range_coverage']['earliest']
            latest = self.stats['date_range_coverage']['latest']
            print(f"   • Earliest document: {earliest or 'None'}")
            print(f"   • Latest document: {latest or 'None'}")
            
            print(f"\n👨‍⚖️ **Judge Verification:**")
            print(f"   • Confirmed Gilstrap documents: {analysis['judge_verification']['confirmed_gilstrap']}")
            judge_variations = list(analysis['judge_verification']['judge_variations_found'])
            for variation in judge_variations[:5]:  # Show up to 5 variations
                print(f"   • Judge name found: \"{variation}\"")
            
            print(f"\n📄 **Case Types:**")
            for status, count in sorted(analysis['case_details']['precedential_status'].items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {status}: {count} cases")
            
            print(f"\n📝 **Sample Cases:**")
            for i, case_name in enumerate(analysis['case_details']['case_name_patterns'][:5]):
                print(f"   {i+1}. {case_name}")
        
        print(f"\n⏱️  **Performance Metrics:**")
        print(f"   • Total processing time: {time.time() - self.start_time:.1f}s")
        print(f"   • API calls made: {self.stats['api_calls']}")
        print(f"   • Average time per API call: {(time.time() - self.start_time) / max(self.stats['api_calls'], 1):.2f}s")

async def run_gilstrap_cluster_first_test():
    """Run comprehensive Judge Gilstrap cluster-first retrieval test"""
    
    test = GilstrapClusterFirstTest()
    
    test.print_header("JUDGE GILSTRAP CLUSTER-FIRST RETRIEVAL TEST")
    print("🎯 Objective: Test enhanced cluster-first approach for Judge Gilstrap document retrieval")
    print("🔄 Using corrected API methodology based on field analysis")
    
    # Test API connection
    if not await test.cl_service.test_connection():
        print("❌ CourtListener API connection failed")
        return False
    
    print("✅ CourtListener API connection verified")
    
    # Step 1: Test different cluster search methods
    method_results = await test.test_cluster_search_methods()
    
    # Step 2: Comprehensive Gilstrap document retrieval
    documents = await test.test_comprehensive_gilstrap_retrieval()
    
    # Step 3: Analyze retrieved documents
    analysis = test.analyze_retrieved_documents(documents) if documents else {}
    
    # Step 4: Print comprehensive results
    test.print_comprehensive_results(method_results, analysis)
    
    # Step 5: Success evaluation
    success = (
        len(documents) > 0 and
        analysis.get('judge_verification', {}).get('confirmed_gilstrap', 0) > 0
    )
    
    if success:
        test.print_header("✅ TEST SUCCESSFUL")
        print("🎉 Cluster-first approach successfully found Judge Gilstrap documents!")
        print(f"📊 Retrieved {len(documents)} verified documents with proper judge metadata")
        
        if documents:
            sample_doc = documents[0]
            print(f"\n📄 Sample verification:")
            print(f"   • Case: {sample_doc.get('case_name', 'Unknown')}")
            print(f"   • Judge: {sample_doc.get('judges', 'Unknown')}")
            print(f"   • Date: {sample_doc.get('date_filed', 'Unknown')}")
            print(f"   • Has text: {'Yes' if sample_doc.get('plain_text') else 'No'}")
            print(f"   • Cluster enhanced: {'Yes' if sample_doc.get('cluster_enhanced') else 'No'}")
    else:
        test.print_header("❌ TEST NEEDS IMPROVEMENT")
        print("🔧 Issues found - see analysis above for recommendations")
    
    return success

if __name__ == "__main__":
    try:
        print("🚀 Starting Judge Gilstrap cluster-first retrieval test...")
        success = asyncio.run(run_gilstrap_cluster_first_test())
        
        if success:
            print("\n🎯 Ready to implement enhanced processor integration!")
        else:
            print("\n🔧 Additional API exploration needed")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)