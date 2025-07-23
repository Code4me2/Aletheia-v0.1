#!/usr/bin/env python3
"""
Run the optimized pipeline on test data
"""

import asyncio
from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline

async def main():
    print("Running Optimized Pipeline Test")
    print("=" * 60)
    
    # Initialize pipeline
    pipeline = OptimizedElevenStagePipeline()
    
    # Process 10 documents
    result = await pipeline.process_batch(limit=10)
    
    print("\n" + "=" * 60)
    print("PIPELINE RESULTS")
    print("=" * 60)
    
    if result['success']:
        print(f"✅ Pipeline completed successfully!")
        print(f"   Documents processed: {result.get('documents_processed', 0)}")
        print(f"   Stages completed: {len(result.get('stages_completed', []))}")
        print(f"   Completeness score: {result.get('completeness_score', 0):.1f}%")
        print(f"   Time taken: {result.get('processing_time', 'N/A')}")
        
        # Show enhancement stats
        stats = result.get('enhancement_stats', {})
        if stats:
            print("\nEnhancement Statistics:")
            for key, value in stats.items():
                if isinstance(value, dict) and 'success' in value:
                    print(f"   {key}: {value['success']}/{value.get('total', 0)} ({value['success']/value.get('total', 1)*100:.0f}%)")
        
        # Show Haystack result
        if 'haystack_result' in result:
            hr = result['haystack_result']
            if hr.get('success'):
                print(f"\n✅ Haystack indexing successful")
                print(f"   Documents sent: {hr.get('document_count', 0)}")
            else:
                print(f"\n❌ Haystack indexing failed: {hr.get('error', 'Unknown error')}")
    else:
        print(f"❌ Pipeline failed: {result.get('error', 'Unknown error')}")
        print(f"   Stages completed: {result.get('stages_completed', [])}")

if __name__ == "__main__":
    asyncio.run(main())