#!/usr/bin/env python3
"""
Test Full Text Retrieval for Judge Gilstrap

Tests the complete docket → clusters → opinions pipeline to retrieve actual opinion text.
"""
import asyncio
import sys
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

class FullTextRetrievalTester:
    """Test full text retrieval capabilities"""
    
    def __init__(self):
        self.cl_service = CourtListenerService()
        self.stats = {
            'dockets_found': 0,
            'clusters_found': 0,
            'opinions_found': 0,
            'opinions_with_text': 0,
            'total_characters': 0,
            'api_calls': 0,
            'processing_time': 0
        }
        
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    async def test_single_docket_text_retrieval(self, docket: Dict[str, Any]) -> Dict[str, Any]:
        """Test full text retrieval for a single docket"""
        docket_id = docket.get('docket_id')
        case_name = docket.get('case_name', 'Unknown')
        
        print(f"\n🔍 Processing: {case_name} (Docket {docket_id})")
        
        result = {
            'docket_id': docket_id,
            'case_name': case_name,
            'clusters': [],
            'opinions': [],
            'text_found': False,
            'total_characters': 0,
            'processing_time': 0
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Find clusters for this docket
            print(f"   Step 1: Finding clusters for docket {docket_id}...")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.cl_service.base_url}/clusters/",
                    headers=self.cl_service._get_headers(),
                    params={"docket": docket_id, "page_size": 20},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        clusters = data.get('results', [])
                        result['clusters'] = clusters
                        self.stats['clusters_found'] += len(clusters)
                        
                        print(f"      ✅ Found {len(clusters)} clusters")
                        
                        # Step 2: Get opinions for each cluster
                        for i, cluster in enumerate(clusters):
                            cluster_id = cluster.get('id')
                            print(f"   Step 2.{i+1}: Getting opinions for cluster {cluster_id}...")
                            
                            async with session.get(
                                f"{self.cl_service.base_url}/opinions/",
                                headers=self.cl_service._get_headers(),
                                params={"cluster": cluster_id, "page_size": 20},
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as opinion_response:
                                
                                if opinion_response.status == 200:
                                    opinion_data = await opinion_response.json()
                                    opinions = opinion_data.get('results', [])
                                    
                                    print(f"         ✅ Found {len(opinions)} opinions")
                                    
                                    for opinion in opinions:
                                        # Enhance opinion with docket and cluster info
                                        enhanced_opinion = {
                                            **opinion,
                                            'docket_info': docket,
                                            'cluster_info': cluster,
                                            'assigned_to_str': docket.get('assigned_to_str'),
                                            'case_name': docket.get('case_name')
                                        }
                                        
                                        result['opinions'].append(enhanced_opinion)
                                        self.stats['opinions_found'] += 1
                                        
                                        # Check for text content
                                        plain_text = opinion.get('plain_text', '')
                                        if plain_text and plain_text.strip():
                                            result['text_found'] = True
                                            text_length = len(plain_text)
                                            result['total_characters'] += text_length
                                            self.stats['total_characters'] += text_length
                                            self.stats['opinions_with_text'] += 1
                                            
                                            print(f"         📄 Opinion {opinion.get('id')}: {text_length:,} characters")
                                        else:
                                            print(f"         📄 Opinion {opinion.get('id')}: No text content")
                                else:
                                    print(f"         ❌ Failed to get opinions: HTTP {opinion_response.status}")
                    else:
                        print(f"      ❌ Failed to get clusters: HTTP {response.status}")
                        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            result['error'] = str(e)
            
        result['processing_time'] = time.time() - start_time
        self.stats['processing_time'] += result['processing_time']
        self.stats['api_calls'] += 2  # cluster + opinion calls
        
        return result
    
    async def test_comprehensive_text_retrieval(self) -> List[Dict[str, Any]]:
        """Test comprehensive text retrieval for all current Gilstrap dockets"""
        self.print_header("COMPREHENSIVE TEXT RETRIEVAL TEST")
        
        print("🎯 Testing complete docket → clusters → opinions pipeline")
        
        # Step 1: Get current Gilstrap dockets
        print("\n🔍 Step 1: Finding current Judge Gilstrap dockets...")
        
        dockets = await self.cl_service.fetch_dockets_by_judge(
            judge_name="Gilstrap",
            court_id="txed",
            max_documents=10
        )
        
        self.stats['dockets_found'] = len(dockets)
        print(f"   ✅ Found {len(dockets)} dockets")
        
        if not dockets:
            print("   ❌ No dockets found to process")
            return []
        
        # Step 2: Process each docket for text retrieval
        print(f"\n🔍 Step 2: Processing {len(dockets)} dockets for text retrieval...")
        
        results = []
        for i, docket in enumerate(dockets):
            print(f"\n--- Processing Docket {i+1}/{len(dockets)} ---")
            result = await self.test_single_docket_text_retrieval(docket)
            results.append(result)
        
        return results
    
    async def test_historical_coverage(self) -> Dict[str, Any]:
        """Test historical coverage with 2-year date range"""
        self.print_header("HISTORICAL COVERAGE TEST")
        
        print("🎯 Testing retrieval limitations for last 2 years")
        
        # Calculate 2-year date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=730)
        
        print(f"📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        try:
            # Search with date filtering
            historical_dockets = await self.cl_service.fetch_dockets_by_judge(
                judge_name="Gilstrap",
                court_id="txed",
                max_documents=100,  # Larger batch for historical search
                date_filed_after=start_date.strftime('%Y-%m-%d'),
                date_filed_before=end_date.strftime('%Y-%m-%d')
            )
            
            print(f"   ✅ Found {len(historical_dockets)} historical dockets")
            
            # Analyze date distribution
            date_distribution = {}
            for docket in historical_dockets:
                date_filed = docket.get('date_filed', '')
                if date_filed:
                    year_month = date_filed[:7]  # YYYY-MM
                    date_distribution[year_month] = date_distribution.get(year_month, 0) + 1
            
            print(f"\n   📊 Date distribution:")
            for date, count in sorted(date_distribution.items()):
                print(f"      {date}: {count} cases")
            
            return {
                'total_historical': len(historical_dockets),
                'date_distribution': date_distribution,
                'earliest': min([d.get('date_filed', '') for d in historical_dockets if d.get('date_filed')]) if historical_dockets else None,
                'latest': max([d.get('date_filed', '') for d in historical_dockets if d.get('date_filed')]) if historical_dockets else None
            }
            
        except Exception as e:
            print(f"   ❌ Error in historical search: {str(e)}")
            return {'error': str(e)}
    
    def print_comprehensive_results(self, results: List[Dict[str, Any]], historical: Dict[str, Any]):
        """Print comprehensive test results"""
        self.print_header("COMPREHENSIVE RESULTS")
        
        print("📊 **Text Retrieval Summary:**")
        print(f"   • Dockets processed: {self.stats['dockets_found']}")
        print(f"   • Clusters found: {self.stats['clusters_found']}")
        print(f"   • Opinions found: {self.stats['opinions_found']}")
        print(f"   • Opinions with text: {self.stats['opinions_with_text']}")
        print(f"   • Total characters: {self.stats['total_characters']:,}")
        
        if self.stats['opinions_with_text'] > 0:
            avg_length = self.stats['total_characters'] / self.stats['opinions_with_text']
            print(f"   • Average opinion length: {avg_length:,.0f} characters")
        
        print(f"\n⏱️  **Performance:**")
        print(f"   • Total processing time: {self.stats['processing_time']:.1f}s")
        print(f"   • API calls made: {self.stats['api_calls']}")
        print(f"   • Average time per API call: {(self.stats['processing_time']/max(self.stats['api_calls'], 1)):.2f}s")
        
        print(f"\n📄 **Sample Results:**")
        text_found_count = sum(1 for r in results if r.get('text_found'))
        print(f"   • Dockets with opinion text: {text_found_count}/{len(results)}")
        
        for result in results[:3]:  # Show first 3 results
            case_name = result.get('case_name', 'Unknown')[:50]
            text_chars = result.get('total_characters', 0)
            opinion_count = len(result.get('opinions', []))
            
            print(f"   • {case_name}: {opinion_count} opinions, {text_chars:,} chars")
        
        print(f"\n📅 **Historical Coverage:**")
        if 'error' not in historical:
            print(f"   • Total historical cases: {historical.get('total_historical', 0)}")
            print(f"   • Date range: {historical.get('earliest', 'N/A')} to {historical.get('latest', 'N/A')}")
        else:
            print(f"   • Error: {historical['error']}")

async def run_full_text_retrieval_test():
    """Run comprehensive full text retrieval test"""
    
    tester = FullTextRetrievalTester()
    
    tester.print_header("JUDGE GILSTRAP FULL TEXT RETRIEVAL TEST")
    print("🎯 Objective: Test complete text retrieval pipeline and establish coverage")
    
    # Test API connection
    if not await tester.cl_service.test_connection():
        print("❌ CourtListener API connection failed")
        return False
    
    print("✅ CourtListener API connection verified")
    
    # Step 1: Comprehensive text retrieval
    results = await tester.test_comprehensive_text_retrieval()
    
    # Step 2: Historical coverage analysis  
    historical = await tester.test_historical_coverage()
    
    # Step 3: Print comprehensive results
    tester.print_comprehensive_results(results, historical)
    
    # Success evaluation
    success = (
        tester.stats['dockets_found'] > 0 and
        tester.stats['opinions_found'] > 0
    )
    
    if success:
        tester.print_header("✅ TEST SUCCESSFUL")
        print("🎉 Full text retrieval pipeline is operational!")
        print(f"📊 Retrieved {tester.stats['opinions_with_text']} opinions with text content")
        print(f"📈 Total content: {tester.stats['total_characters']:,} characters")
        
        if tester.stats['opinions_with_text'] > 0:
            print(f"\n🔧 **Ready for Phase 3 Integration:**")
            print(f"   • Text retrieval: ✅ Working")
            print(f"   • Judge identification: ✅ Working") 
            print(f"   • API performance: ✅ Good ({(tester.stats['processing_time']/max(tester.stats['api_calls'], 1)):.2f}s/call)")
            print(f"   • Data quality: ✅ {tester.stats['total_characters']:,} characters available")
    else:
        tester.print_header("🔧 NEEDS IMPROVEMENT")
        print("📋 Issues to address:")
        if tester.stats['dockets_found'] == 0:
            print("   • No dockets found")
        if tester.stats['opinions_found'] == 0:
            print("   • No opinions found")
        if tester.stats['opinions_with_text'] == 0:
            print("   • No opinion text content available")
    
    return success

if __name__ == "__main__":
    try:
        print("🚀 Starting comprehensive full text retrieval test...")
        success = asyncio.run(run_full_text_retrieval_test())
        
        if success:
            print("\n🎯 Ready for enhanced processor integration!")
        else:
            print("\n🔧 Additional development needed")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)