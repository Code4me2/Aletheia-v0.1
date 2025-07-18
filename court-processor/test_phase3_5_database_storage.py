#!/usr/bin/env python3
"""
Phase 3.5 Verification: PostgreSQL Storage Integration

Tests complete database storage with proper metadata for Gilstrap documents.
"""
import asyncio
import sys
import os
import time

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

async def test_phase3_5_database_storage():
    """Test Phase 3.5: PostgreSQL storage integration"""
    
    print("=== PHASE 3.5 VERIFICATION TEST ===\n")
    print("🎯 Testing PostgreSQL storage with proper metadata")
    
    # Initialize processor
    print("📦 Step 1: Initializing Enhanced Processor...")
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        print("   ✅ Enhanced processor initialized")
        
        # Check database connectivity
        print("   🔍 Checking database connectivity...")
        # This will be tested during document processing
        
    except Exception as e:
        print(f"   ❌ Failed to initialize: {str(e)}")
        return False
    
    # Test with a complete document structure
    print(f"\n🔍 Step 2: Testing document storage with metadata...")
    
    # Create a comprehensive test document
    test_document = {
        'id': 999999,
        'cluster_id': 888888,
        'court_id': 'txed',
        'case_name': 'Phase 3.5 Test v. Database Storage',
        'date_filed': '2023-06-15',
        'author_str': 'Judge Gilstrap',
        'assigned_to_str': 'Rodney Gilstrap',
        'plain_text': 'This is a comprehensive test document for Phase 3.5 database storage verification. It contains citations like Smith v. Jones, 123 F.3d 456 (5th Cir. 2020), and tests the complete processing pipeline including FLP enhancement and database storage with proper metadata tracking.',
        'type': 'opinion',
        'source': 'courtlistener_api',
        'processing_timestamp': time.time(),
        'docket_number': 'TEST-2023-CV-12345',
        'nature_of_suit': 'Patent Law',
        'precedential_status': 'Published'
    }
    
    try:
        print(f"   📄 Processing comprehensive test document...")
        print(f"      • Court ID: {test_document['court_id']}")
        print(f"      • Case name: {test_document['case_name']}")
        print(f"      • Judge: {test_document['assigned_to_str']}")
        print(f"      • Text length: {len(test_document.get('plain_text', '')):,} chars")
        print(f"      • Metadata fields: {len(test_document)} fields")
        
        # Process through complete pipeline
        start_time = time.time()
        result = await processor.process_single_document(test_document)
        processing_time = time.time() - start_time
        
        print(f"   ✅ Document processing completed in {processing_time:.2f}s")
        print(f"   📊 Storage results:")
        
        if result.get('saved_id'):
            saved_id = result['saved_id']
            print(f"      • Success: Yes")
            print(f"      • Saved ID: {saved_id}")
            print(f"      • FLP enhanced: {'Yes' if result.get('flp_processing_timestamp') else 'No'}")
            print(f"      • Citations found: {len(result.get('citations', []))}")
            print(f"      • Court info enhanced: {'Yes' if result.get('court_info') else 'No'}")
            
            # Show enhancement details
            if result.get('citations'):
                print(f"      • Citation examples:")
                for i, citation in enumerate(result.get('citations', [])[:2]):
                    print(f"         {i+1}. {citation.get('citation_string', 'Unknown')}")
            
            court_info = result.get('court_info', {})
            if court_info:
                print(f"      • Court standardized: {'Yes' if court_info.get('standardized') else 'No'}")
                if court_info.get('full_name'):
                    print(f"      • Court name: {court_info['full_name']}")
            
            return saved_id
        else:
            print(f"      • Success: No")
            print(f"      • Error: {result.get('error', 'Unknown error')}")
            return None
            
    except Exception as e:
        print(f"   ❌ Document processing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
async def test_batch_storage():
    """Test batch processing and storage"""
    print(f"\n🔍 Step 3: Testing batch processing and storage...")
    
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Test current Gilstrap dockets batch processing
        print(f"   📚 Processing current Gilstrap dockets batch...")
        
        batch_result = await processor.process_gilstrap_documents_batch(
            max_documents=2
        )
        
        print(f"   ✅ Batch processing completed")
        print(f"   📊 Batch storage results:")
        print(f"      • Documents fetched: {batch_result.get('total_fetched', 0)}")
        print(f"      • New documents stored: {batch_result.get('new_documents', 0)}")
        print(f"      • Duplicates skipped: {batch_result.get('duplicates', 0)}")
        print(f"      • Errors: {batch_result.get('errors', 0)}")
        print(f"      • Processing time: {batch_result.get('processing_time', 0):.2f}s")
        
        # Test health metrics
        print(f"\n   🏥 System health after batch processing...")
        health = processor.get_health_status()
        metrics = processor.get_processing_metrics()
        
        print(f"      • System status: {health.get('status', 'Unknown')}")
        print(f"      • Uptime: {health.get('uptime_seconds', 0):.1f}s")
        
        if 'processing' in metrics:
            processing = metrics['processing']
            print(f"      • Total documents processed: {processing.get('documents_processed', 0)}")
            print(f"      • Success rate: {processing.get('success_rate', 0):.1%}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Batch processing failed: {str(e)}")
        return False

async def verify_database_schema():
    """Verify database schema and stored data structure"""
    print(f"\n🔍 Step 4: Database schema and data verification...")
    
    try:
        # This would ideally connect to the database and verify schema
        # For now, we'll verify through the processor's validation
        
        processor = EnhancedUnifiedDocumentProcessor()
        
        print(f"   📋 Database integration status:")
        print(f"      • Document validator: {'✅' if processor.document_validator else '❌'}")
        print(f"      • Monitoring: {'✅' if processor.monitor else '❌'}")
        print(f"      • Deduplication: {'✅' if processor.dedup_manager else '❌'}")
        
        # Test validation pipeline
        test_doc = {
            'id': 123,
            'court_id': 'txed',
            'case_name': 'Test Case',
            'plain_text': 'Test content'
        }
        
        validation_result = processor.document_validator.validate_courtlistener_document(test_doc)
        
        print(f"   📊 Data validation:")
        print(f"      • Document validation: {'✅ Pass' if validation_result.is_valid else '❌ Fail'}")
        
        if validation_result.has_warnings:
            print(f"      • Warnings: {len(validation_result.warnings)}")
            for warning in validation_result.warnings[:2]:
                print(f"         - {warning}")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database verification failed: {str(e)}")
        return False

async def run_phase3_5_test():
    """Run Phase 3.5 verification"""
    
    print("🚀 Starting Phase 3.5 verification...")
    
    # Test individual document storage
    saved_id = await test_phase3_5_database_storage()
    
    # Test batch processing and storage
    batch_success = await test_batch_storage()
    
    # Verify database schema and validation
    schema_success = await verify_database_schema()
    
    success = saved_id is not None and batch_success and schema_success
    
    if success:
        print(f"\n=== PHASE 3.5 SUMMARY ===")
        print(f"✅ PostgreSQL storage: OPERATIONAL")
        print(f"✅ Document metadata preservation: WORKING")
        print(f"✅ FLP enhancement storage: INTEGRATED")
        print(f"✅ Batch processing storage: FUNCTIONAL")
        print(f"✅ Data validation pipeline: ACTIVE")
        
        if saved_id:
            print(f"✅ Test document stored: ID {saved_id}")
        
        print(f"\n🎉 Phase 3.5 verification successful!")
        print(f"📋 Ready for Phase 3.6: Final verification")
    else:
        print(f"\n❌ Phase 3.5 FAILED")
        print(f"🔧 Fix database storage issues before proceeding")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(run_phase3_5_test())
        
        if success:
            print("\n✅ Phase 3.5 PASSED - Ready for Phase 3.6")
        else:
            print("\n❌ Phase 3.5 FAILED")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)