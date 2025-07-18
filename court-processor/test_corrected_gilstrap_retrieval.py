#!/usr/bin/env python3
"""
Test Corrected Judge Gilstrap Retrieval

Tests the updated CourtListener service with correct docket-first API syntax.
"""
import asyncio
import sys
import os
import time

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

async def test_corrected_gilstrap_retrieval():
    """Test corrected Judge Gilstrap retrieval approach"""
    
    print("=== CORRECTED JUDGE GILSTRAP RETRIEVAL TEST ===\n")
    print("🎯 Using corrected docket-first API approach")
    
    cl_service = CourtListenerService()
    
    # Test connection
    if not await cl_service.test_connection():
        print("❌ API connection failed")
        return False
    
    print("✅ API connected\n")
    
    # Step 1: Test docket search for Gilstrap
    print("🔍 Step 1: Testing docket search for Judge Gilstrap...")
    
    start_time = time.time()
    dockets = await cl_service.fetch_dockets_by_judge(
        judge_name="Gilstrap",
        court_id="txed",
        max_documents=10
    )
    search_time = time.time() - start_time
    
    print(f"   ✅ Found {len(dockets)} dockets in {search_time:.2f}s")
    
    if dockets:
        # Show sample dockets
        for i, docket in enumerate(dockets[:3]):
            print(f"\n   📄 Docket {i+1}:")
            print(f"      Case: {docket.get('case_name')}")
            print(f"      Judge: {docket.get('assigned_to_str')}")
            print(f"      Date: {docket.get('date_filed')}")
            print(f"      Nature: {docket.get('nature_of_suit')}")
    
    # Step 2: Test comprehensive Gilstrap document retrieval
    print(f"\n🔍 Step 2: Testing comprehensive Gilstrap document retrieval...")
    
    start_time = time.time()
    documents = await cl_service.fetch_gilstrap_documents(
        max_documents=20,
        include_text=True
    )
    retrieval_time = time.time() - start_time
    
    print(f"   ✅ Retrieved {len(documents)} documents in {retrieval_time:.2f}s")
    
    if documents:
        # Analyze document types
        doc_types = {}
        has_text_count = 0
        
        for doc in documents:
            # Count by type
            doc_type = type(doc.get('data_source', 'unknown'))
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
            
            # Count text availability
            if doc.get('plain_text'):
                has_text_count += 1
        
        print(f"\n   📊 Document Analysis:")
        print(f"      • Documents with text: {has_text_count}/{len(documents)}")
        print(f"      • Data sources: {list(doc_types.keys())}")
        
        # Show sample document
        sample = documents[0]
        print(f"\n   📄 Sample Document:")
        print(f"      • ID: {sample.get('id') or sample.get('docket_id')}")
        print(f"      • Case: {sample.get('case_name')}")
        print(f"      • Judge: {sample.get('assigned_to_str')}")
        print(f"      • Has text: {'Yes' if sample.get('plain_text') else 'No'}")
        print(f"      • Source: {sample.get('data_source')}")
    
    # Step 3: Performance summary
    print(f"\n=== PERFORMANCE SUMMARY ===")
    print(f"✅ Docket search: {len(dockets)} results in {search_time:.2f}s")
    print(f"✅ Document retrieval: {len(documents)} results in {retrieval_time:.2f}s")
    
    success = len(dockets) > 0 or len(documents) > 0
    
    if success:
        print(f"\n🎉 SUCCESS: Corrected API approach found Judge Gilstrap data!")
        print(f"📊 Found {len(dockets)} dockets and {len(documents)} documents")
    else:
        print(f"\n🔧 No results found - need further investigation")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(test_corrected_gilstrap_retrieval())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)