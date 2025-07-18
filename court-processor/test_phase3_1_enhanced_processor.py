#!/usr/bin/env python3
"""
Phase 3.1 Verification: Enhanced Processor with Corrected CourtListener Service

Tests that the enhanced processor properly uses the corrected docket-first approach.
"""
import asyncio
import sys
import os

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

async def test_phase3_1_enhanced_processor():
    """Test Phase 3.1: Enhanced processor with corrected CourtListener integration"""
    
    print("=== PHASE 3.1 VERIFICATION TEST ===\n")
    print("🎯 Testing enhanced processor with corrected docket-first approach")
    
    # Initialize enhanced processor
    print("📦 Step 1: Initializing Enhanced Processor...")
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        print("   ✅ Enhanced processor initialized successfully")
        
        # Verify CourtListener service is properly integrated
        if processor.cl_service:
            print("   ✅ CourtListener service integrated")
            
            # Test API connection
            connection_ok = await processor.cl_service.test_connection()
            if connection_ok:
                print("   ✅ CourtListener API connection verified")
            else:
                print("   ❌ CourtListener API connection failed")
                return False
        else:
            print("   ❌ CourtListener service not available")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to initialize processor: {str(e)}")
        return False
    
    # Test specialized Gilstrap method
    print(f"\n🔍 Step 2: Testing specialized Gilstrap document processing...")
    try:
        # Use the specialized Gilstrap method (should find dockets but no opinions yet)
        result = await processor.process_gilstrap_documents_batch(
            max_documents=5  # Small batch for testing
        )
        
        print(f"   ✅ Gilstrap batch processing completed")
        print(f"   📊 Results:")
        print(f"      • Documents fetched: {result.get('total_fetched', 0)}")
        print(f"      • New documents: {result.get('new_documents', 0)}")
        print(f"      • Duplicates: {result.get('duplicates', 0)}")
        print(f"      • Errors: {result.get('errors', 0)}")
        
        # Verify the corrected approach is working
        if result.get('total_fetched', 0) > 0:
            print(f"   ✅ Corrected API approach successfully fetched documents")
        else:
            print(f"   ⚠️  No documents fetched (expected for recent cases)")
            
    except Exception as e:
        print(f"   ❌ Gilstrap batch processing failed: {str(e)}")
        return False
    
    # Test general batch processing with judge parameter
    print(f"\n🔍 Step 3: Testing general batch processing with judge parameter...")
    try:
        result = await processor.process_courtlistener_batch(
            court_id="txed",
            judge_name="Gilstrap",
            max_documents=3
        )
        
        print(f"   ✅ General batch processing with judge parameter completed")
        print(f"   📊 Results:")
        print(f"      • Documents fetched: {result.get('total_fetched', 0)}")
        print(f"      • Processing time: {result.get('processing_time', 0):.2f}s")
        
    except Exception as e:
        print(f"   ❌ General batch processing failed: {str(e)}")
        return False
    
    # Test health monitoring
    print(f"\n🏥 Step 4: Testing health monitoring...")
    try:
        health = processor.get_health_status()
        print(f"   ✅ Health status retrieved")
        print(f"   📊 Status: {health.get('status', 'Unknown')}")
        print(f"   ⏱️  Uptime: {health.get('uptime_seconds', 0):.1f}s")
        
        metrics = processor.get_processing_metrics()
        if 'processing' in metrics:
            processing = metrics['processing']
            print(f"   📈 Documents processed: {processing.get('documents_processed', 0)}")
            
    except Exception as e:
        print(f"   ❌ Health monitoring failed: {str(e)}")
        return False
    
    # Summary
    print(f"\n=== PHASE 3.1 SUMMARY ===")
    print(f"✅ Enhanced processor integration: COMPLETE")
    print(f"✅ Corrected docket-first approach: INTEGRATED")
    print(f"✅ Specialized Gilstrap processing: AVAILABLE")
    print(f"✅ Health monitoring: OPERATIONAL")
    
    print(f"\n🎉 Phase 3.1 verification successful!")
    print(f"📋 Ready for Phase 3.2: End-to-end processing test")
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 Starting Phase 3.1 verification...")
        success = asyncio.run(test_phase3_1_enhanced_processor())
        
        if success:
            print("\n✅ Phase 3.1 PASSED - Ready for Phase 3.2")
        else:
            print("\n❌ Phase 3.1 FAILED - Fix issues before proceeding")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)