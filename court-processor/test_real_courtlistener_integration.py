#!/usr/bin/env python3
"""
Test script for Phase 2 real CourtListener integration

Tests the enhanced processor with real CourtListener data and 
verifies complete end-to-end functionality.
"""
import asyncio
import sys
import os

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor
from enhanced.config import get_settings

async def test_real_integration():
    """Test real CourtListener integration"""
    print("=== Phase 2 Real CourtListener Integration Test ===\n")
    
    # Initialize enhanced processor
    print("1. Initializing Enhanced Processor...")
    processor = EnhancedUnifiedDocumentProcessor()
    print("   ✅ Enhanced processor initialized")
    
    # Test CourtListener connection
    print("\n2. Testing CourtListener Connection...")
    settings = get_settings()
    if settings.services.courtlistener_api_key:
        connection_test = await processor.cl_service.test_connection()
        if connection_test:
            print("   ✅ CourtListener API connection successful")
        else:
            print("   ❌ CourtListener API connection failed")
            return False
    else:
        print("   ⚠️  No API key configured")
        return False
    
    # Fetch real documents
    print("\n3. Fetching Real CourtListener Documents...")
    try:
        documents = await processor.cl_service.fetch_opinions(
            court_id="cafc",  # Federal Circuit
            max_documents=2
        )
        print(f"   ✅ Fetched {len(documents)} real documents")
        
        if not documents:
            print("   ❌ No documents returned")
            return False
            
        # Show sample document structure
        sample_doc = documents[0]
        print(f"   📄 Sample document ID: {sample_doc.get('id')}")
        print(f"   📄 Has text: {'Yes' if sample_doc.get('plain_text') else 'No'}")
        print(f"   📄 Court ID: {sample_doc.get('court_id', 'None')}")
        print(f"   📄 Case name: {sample_doc.get('case_name', 'None')}")
        
    except Exception as e:
        print(f"   ❌ Error fetching documents: {e}")
        return False
    
    # Process real document
    print("\n4. Processing Real Document with Enhanced Pipeline...")
    try:
        sample_doc = documents[0]
        result = await processor.process_single_document(sample_doc)
        
        if 'saved_id' in result:
            print(f"   ✅ Document processed successfully")
            print(f"   💾 Saved with ID: {result['saved_id']}")
            print(f"   📚 Citations found: {len(result.get('citations', []))}")
            
            # Show FLP enhancements
            if 'flp_processing_timestamp' in result:
                print(f"   🔍 FLP processing completed")
            if 'court_info' in result:
                print(f"   🏛️  Court info enhanced")
                
        else:
            print(f"   ❌ Document processing failed: {result.get('error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error processing document: {e}")
        return False
    
    # Test batch processing with real data  
    print("\n5. Testing Batch Processing with Real Data...")
    try:
        batch_result = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=2
        )
        
        print(f"   ✅ Batch processing completed")
        print(f"   📊 Total fetched: {batch_result['total_fetched']}")
        print(f"   ✨ New documents: {batch_result['new_documents']}")
        print(f"   🔄 Duplicates: {batch_result['duplicates']}")
        print(f"   ❌ Errors: {batch_result['errors']}")
        
    except Exception as e:
        print(f"   ❌ Error in batch processing: {e}")
        return False
    
    # Get health status
    print("\n6. System Health Check...")
    health = processor.get_health_status()
    print(f"   📊 Health Status: {health.get('status')}")
    print(f"   ⏱️  Uptime: {health.get('uptime_seconds', 0):.1f}s")
    
    metrics = processor.get_processing_metrics()
    if 'processing' in metrics:
        processing = metrics['processing']
        print(f"   📈 Documents processed: {processing.get('documents_processed', 0)}")
        print(f"   ✅ Success rate: {processing.get('success_rate', 0):.1%}")
    
    print("\n=== Integration Test Completed Successfully ===")
    print("🎉 Phase 2 real CourtListener integration is fully operational!")
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_real_integration())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)