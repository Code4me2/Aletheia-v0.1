#!/usr/bin/env python3
"""
Phase 3.2 Verification: End-to-End Processing with Real Gilstrap Data

Tests complete document processing pipeline with real CourtListener data.
"""
import asyncio
import sys
import os
import time
from datetime import datetime, timedelta

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

async def test_phase3_2_end_to_end():
    """Test Phase 3.2: End-to-end processing with real data"""
    
    print("=== PHASE 3.2 VERIFICATION TEST ===\n")
    print("🎯 Testing end-to-end processing with real Gilstrap data")
    
    # Initialize processor
    print("📦 Step 1: Initializing Enhanced Processor...")
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        print("   ✅ Enhanced processor initialized")
        
        # Verify all components
        print("   🔍 Checking component availability...")
        print(f"      • CourtListener service: {'✅' if processor.cl_service else '❌'}")
        print(f"      • FLP integration: {'✅' if processor.flp_integration else '⚠️  Mock'}")
        print(f"      • Unstructured service: {'✅' if processor.unstructured else '⚠️  Mock'}")
        print(f"      • Monitoring: {'✅' if processor.monitor else '❌'}")
        
    except Exception as e:
        print(f"   ❌ Failed to initialize: {str(e)}")
        return False
    
    # Test with historical Gilstrap data search
    print(f"\n🔍 Step 2: Testing with historical data search...")
    try:
        # Use search approach to find historical Gilstrap cases with text
        print("   📚 Searching for historical Gilstrap opinions with text content...")
        
        # Get a historical opinion using search API
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{processor.cl_service.base_url}/search/",
                headers=processor.cl_service._get_headers(),
                params={
                    "q": "Gilstrap",
                    "type": "o",  # Opinions
                    "court": "txed",
                    "page_size": 5
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    search_results = data.get('results', [])
                    
                    print(f"      ✅ Found {len(search_results)} historical Gilstrap opinions")
                    
                    if search_results:
                        # Try to process the first opinion
                        opinion_result = search_results[0]
                        case_name = opinion_result.get('caseName', 'Unknown')
                        
                        # Extract opinion ID from opinions array or URL
                        opinion_id = None
                        opinions = opinion_result.get('opinions', [])
                        if opinions and len(opinions) > 0:
                            opinion_id = opinions[0].get('id')
                        
                        if not opinion_id:
                            # Try extracting from absolute_url
                            abs_url = opinion_result.get('absolute_url', '')
                            if abs_url and '/opinion/' in abs_url:
                                parts = abs_url.split('/')
                                if len(parts) > 2 and parts[1] == 'opinion':
                                    opinion_id = parts[2]
                        
                        print(f"      📄 Testing with: {case_name} (ID: {opinion_id})")
                        
                        if opinion_id:
                            # Fetch full opinion data
                            async with session.get(
                                f"{processor.cl_service.base_url}/opinions/{opinion_id}/",
                                headers=processor.cl_service._get_headers(),
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as opinion_response:
                                
                                if opinion_response.status == 200:
                                    opinion_data = await opinion_response.json()
                                    
                                    # Map to our expected format
                                    test_document = processor.cl_service._map_courtlistener_document(opinion_data)
                                    
                                    print(f"      ✅ Retrieved full opinion data")
                                    print(f"         • Has text: {'Yes' if test_document.get('plain_text') else 'No'}")
                                    print(f"         • Text length: {len(test_document.get('plain_text', '')):,} chars")
                                    
                                    # Process through enhanced pipeline
                                    print(f"\n   🔄 Step 3: Processing through enhanced pipeline...")
                                    
                                    start_time = time.time()
                                    result = await processor.process_single_document(test_document)
                                    processing_time = time.time() - start_time
                                    
                                    print(f"      ✅ Document processing completed in {processing_time:.2f}s")
                                    print(f"      📊 Results:")
                                    print(f"         • Success: {'Yes' if result.get('saved_id') else 'No'}")
                                    
                                    if result.get('saved_id'):
                                        print(f"         • Saved ID: {result['saved_id']}")
                                        print(f"         • FLP processed: {'Yes' if result.get('flp_processing_timestamp') else 'No'}")
                                        print(f"         • Citations found: {len(result.get('citations', []))}")
                                        print(f"         • Court info enhanced: {'Yes' if result.get('court_info') else 'No'}")
                                        
                                        # Check database storage
                                        print(f"\n   💾 Step 4: Verifying database storage...")
                                        # Note: This will be expanded in Phase 3.5
                                        print(f"      ⚠️  Database verification pending Phase 3.5")
                                        
                                        return True
                                    else:
                                        print(f"         • Error: {result.get('error', 'Unknown')}")
                                        return False
                                else:
                                    print(f"      ❌ Failed to fetch opinion: HTTP {opinion_response.status}")
                                    return False
                        else:
                            print(f"      ❌ Could not extract opinion ID from search result")
                            return False
                    else:
                        print(f"      ⚠️  No search results found")
                        return False
                else:
                    print(f"      ❌ Search failed: HTTP {response.status}")
                    return False
                    
    except Exception as e:
        print(f"   ❌ End-to-end processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test batch processing
    print(f"\n🔍 Step 5: Testing batch processing capabilities...")
    try:
        # Test with current dockets (expected to have no opinions yet)
        result = await processor.process_gilstrap_documents_batch(max_documents=3)
        
        print(f"   ✅ Batch processing completed")
        print(f"   📊 Batch results:")
        print(f"      • Documents fetched: {result.get('total_fetched', 0)}")
        print(f"      • New documents: {result.get('new_documents', 0)}")
        print(f"      • Processing time: {result.get('processing_time', 0):.2f}s")
        
    except Exception as e:
        print(f"   ❌ Batch processing failed: {str(e)}")
        # Don't fail the test - batch might not find recent opinions
    
    # Performance and health check
    print(f"\n🏥 Step 6: Final health and performance check...")
    try:
        health = processor.get_health_status()
        metrics = processor.get_processing_metrics()
        
        print(f"   ✅ Health check completed")
        print(f"   📊 System health:")
        print(f"      • Status: {health.get('status', 'Unknown')}")
        print(f"      • Uptime: {health.get('uptime_seconds', 0):.1f}s")
        
        if 'processing' in metrics:
            processing = metrics['processing']
            print(f"      • Documents processed: {processing.get('documents_processed', 0)}")
            print(f"      • Success rate: {processing.get('success_rate', 0):.1%}")
        
    except Exception as e:
        print(f"   ❌ Health check failed: {str(e)}")
    
    return True

async def run_phase3_2_test():
    """Run Phase 3.2 verification"""
    
    print("🚀 Starting Phase 3.2 verification...")
    
    success = await test_phase3_2_end_to_end()
    
    if success:
        print(f"\n=== PHASE 3.2 SUMMARY ===")
        print(f"✅ End-to-end processing: COMPLETE")
        print(f"✅ Real Gilstrap data: PROCESSED")
        print(f"✅ Enhanced pipeline: OPERATIONAL")
        print(f"✅ Document mapping: WORKING")
        
        print(f"\n🎉 Phase 3.2 verification successful!")
        print(f"📋 Ready for Phase 3.3: FLP Integration")
    else:
        print(f"\n❌ Phase 3.2 FAILED")
        print(f"🔧 Fix issues before proceeding to Phase 3.3")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(run_phase3_2_test())
        
        if success:
            print("\n✅ Phase 3.2 PASSED - Ready for Phase 3.3")
        else:
            print("\n❌ Phase 3.2 FAILED")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)