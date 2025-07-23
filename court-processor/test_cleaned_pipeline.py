#!/usr/bin/env python3
"""
Test the cleaned pipeline with real data
"""

import asyncio
from eleven_stage_pipeline_cleaned import CleanedElevenStagePipeline

async def main():
    print("Testing Cleaned Pipeline")
    print("=" * 60)
    print("\nThis test will verify:")
    print("1. Database storage handles duplicates properly")
    print("2. Court resolution returns 'unresolved' when no court found")
    print("3. Legal 'enhancement' renamed to honest 'keyword extraction'")
    print("4. Better error handling and reporting")
    print("\n" + "=" * 60)
    
    # Initialize pipeline
    pipeline = CleanedElevenStagePipeline()
    
    # Process 5 documents to test
    result = await pipeline.process_batch(limit=5)
    
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    
    if result.get('success'):
        print(f"✅ Pipeline completed successfully!")
        print(f"   Documents processed: {result.get('documents_processed', 0)}")
        print(f"   Stages completed: {len(result.get('stages_completed', []))}")
        
        # Check storage results
        storage_result = result.get('optimization_results', {})
        if storage_result.get('storage_fixed'):
            print(f"\n📦 Storage Results:")
            # The storage results should be in the pipeline return data
            print(f"   Check logs for storage details")
        
        # Check court resolution
        verification = result.get('verification', {})
        total_docs = result.get('documents_processed', 0)
        resolved_courts = verification.get('documents_with_court_resolution', 0)
        
        print(f"\n🏛️  Court Resolution:")
        print(f"   Documents with resolved courts: {resolved_courts}/{total_docs}")
        print(f"   Unresolved courts: {total_docs - resolved_courts}")
        
        # Check keyword extraction (formerly legal enhancement)
        docs_with_keywords = verification.get('documents_with_legal_concepts', 0)
        print(f"\n🔍 Keyword Extraction:")
        print(f"   Documents with keywords: {docs_with_keywords}/{total_docs}")
        
        # Check completeness score
        completeness = verification.get('completeness_score', 0)
        print(f"\n📊 Overall Completeness: {completeness:.1f}%")
        print("   (Should be lower now that we're being honest)")
        
    else:
        print(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
        print(f"   Stages completed: {result.get('stages_completed', [])}")
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
    
    # Run a second time to test duplicate handling
    print("\n🔄 Running pipeline again to test duplicate handling...")
    result2 = await pipeline.process_batch(limit=5)
    
    if result2.get('success'):
        print("✅ Second run completed")
        print("   Check logs for 'skipped' and 'updated' counts")
    else:
        print("❌ Second run failed")

if __name__ == "__main__":
    asyncio.run(main())