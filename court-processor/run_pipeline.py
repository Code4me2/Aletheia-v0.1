#!/usr/bin/env python3
"""
Simple Pipeline Runner

Usage:
    python run_pipeline.py                    # Process 10 documents (default)
    python run_pipeline.py 50                 # Process 50 documents
    python run_pipeline.py 100 --no-strict    # Process 100 documents, include warnings
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
import argparse
import json


async def run_pipeline(limit: int = 10, strict: bool = True):
    """Run the pipeline with specified parameters"""
    print(f"\n{'='*80}")
    print(f"Running Pipeline: {limit} documents, strict={strict}")
    print(f"{'='*80}\n")
    
    try:
        pipeline = RobustElevenStagePipeline()
        results = await pipeline.process_batch(
            limit=limit,
            validate_strict=strict
        )
        
        # Display results
        if results['success']:
            print(f"\n{'='*80}")
            print("PIPELINE RESULTS")
            print(f"{'='*80}")
            
            stats = results['statistics']
            print(f"\nDocuments processed: {stats['documents_processed']}")
            print(f"Courts resolved: {stats['courts_resolved']}")
            print(f"Citations extracted: {stats['citations_extracted']}")
            print(f"Judges identified: {stats['judges_enhanced'] + stats['judges_extracted_from_content']}")
            
            # Document type breakdown
            print("\nDocument Type Distribution:")
            for doc_type, info in results['document_type_statistics'].items():
                print(f"  {doc_type}: {info['count']} ({info['percentage']:.1f}%)")
            
            # Quality metrics
            quality = results['quality_metrics']
            print(f"\nQuality Metrics:")
            print(f"  Court resolution rate: {quality['court_resolution_rate']:.1f}%")
            print(f"  Citation extraction rate: {quality['citation_extraction_rate']:.1f}%")
            print(f"  Judge identification rate: {quality['judge_identification_rate']:.1f}%")
            
            # Verification scores
            verification = results['verification']
            print(f"\nOverall Performance:")
            print(f"  Completeness: {verification['completeness_score']:.1f}%")
            print(f"  Quality: {verification['quality_score']:.1f}%")
            
            # Type-specific performance
            if verification.get('by_document_type'):
                print("\nPerformance by Document Type:")
                for doc_type, metrics in verification['by_document_type'].items():
                    print(f"\n  {doc_type.upper()}:")
                    print(f"    Total: {metrics['total']} documents")
                    print(f"    Court resolution: {metrics['court_resolution_rate']:.1f}%")
                    print(f"    Judge identification: {metrics['judge_identification_rate']:.1f}%")
                    print(f"    Quality score: {metrics['quality_score']:.1f}%")
            
            # Save detailed results
            output_file = f"pipeline_results_{results['run_id']}.json"
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"\nDetailed results saved to: {output_file}")
            
        else:
            print(f"\nPipeline failed: {results.get('error', 'Unknown error')}")
            print(f"Error type: {results.get('error_type', 'Unknown')}")
            
    except Exception as e:
        print(f"\nError running pipeline: {e}")
        import traceback
        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description='Run the court document processing pipeline')
    parser.add_argument('limit', nargs='?', type=int, default=10,
                       help='Number of documents to process (default: 10)')
    parser.add_argument('--no-strict', action='store_true',
                       help='Process documents even with validation warnings')
    parser.add_argument('--table', type=str, default='public.court_documents',
                       help='Source table (default: public.court_documents)')
    
    args = parser.parse_args()
    
    # Check if running in Docker
    if not os.getenv('DATABASE_URL'):
        print("\nERROR: Database connection not available.")
        print("Please run this script inside the Docker container:")
        print(f"\n  docker-compose exec court-processor python run_pipeline.py {args.limit}")
        if args.no_strict:
            print("  --no-strict")
        sys.exit(1)
    
    # Run the pipeline
    asyncio.run(run_pipeline(
        limit=args.limit,
        strict=not args.no_strict
    ))


if __name__ == "__main__":
    main()