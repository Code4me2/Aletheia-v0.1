#!/usr/bin/env python3
"""
Pipeline Usage Guide and Gap Analysis

This script demonstrates how to activate the functional pipeline with various parameters
and identifies current implementation gaps.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from services.database import get_db_connection
import json


async def demonstrate_basic_usage():
    """Basic pipeline usage with default parameters"""
    print("\n" + "=" * 80)
    print("1. BASIC USAGE - Process 10 documents with defaults")
    print("=" * 80)
    
    pipeline = RobustElevenStagePipeline()
    results = await pipeline.process_batch()
    
    print(f"Success: {results['success']}")
    print(f"Documents processed: {results['statistics']['documents_processed']}")
    print(f"Completeness: {results['verification']['completeness_score']:.1f}%")


async def demonstrate_custom_parameters():
    """Pipeline usage with custom parameters"""
    print("\n" + "=" * 80)
    print("2. CUSTOM PARAMETERS - Process specific number of documents")
    print("=" * 80)
    
    pipeline = RobustElevenStagePipeline()
    
    # Process 25 documents
    results = await pipeline.process_batch(
        limit=25,
        source_table='public.court_documents',
        validate_strict=False  # Process documents even with validation warnings
    )
    
    print(f"Documents processed: {results['statistics']['documents_processed']}")
    print(f"Validation failures: {results['statistics']['validation_failures']}")


async def demonstrate_selective_retrieval():
    """Show current retrieval limitations and gaps"""
    print("\n" + "=" * 80)
    print("3. SELECTIVE RETRIEVAL - Current Limitations")
    print("=" * 80)
    
    print("\nCURRENT RETRIEVAL OPTIONS:")
    print("- limit: Number of documents (e.g., 10, 50, 100)")
    print("- source_table: Table name (default: 'public.court_documents')")
    print("- validate_strict: Skip invalid documents (default: True)")
    
    print("\nGAPS - NO BUILT-IN FILTERS FOR:")
    print("❌ Date range filtering")
    print("❌ Court-specific filtering")
    print("❌ Judge-specific filtering")
    print("❌ Document type filtering")
    print("❌ Case number pattern matching")
    print("❌ Content keyword search")
    print("❌ Metadata field filtering")
    print("❌ Processing status filtering (skip already processed)")


def show_implementation_gaps():
    """Identify gaps in current implementation"""
    print("\n" + "=" * 80)
    print("4. IMPLEMENTATION GAPS ANALYSIS")
    print("=" * 80)
    
    print("\nRETRIEVAL GAPS:")
    print("1. No query builder for complex filters")
    print("2. No pagination support for large datasets")
    print("3. No ability to resume from last processed document")
    print("4. No support for filtering by processing status")
    print("5. No CourtListener API integration for retrieval")
    
    print("\nPROCESSING GAPS:")
    print("1. No parallel processing of documents")
    print("2. No checkpointing for long-running processes")
    print("3. No ability to reprocess specific stages")
    print("4. No dry-run mode to preview what would be processed")
    
    print("\nINTEGRATION GAPS:")
    print("1. No direct CourtListener API document fetching")
    print("2. No automatic RECAP document download")
    print("3. No real-time processing triggers")
    print("4. No webhook support for new document notifications")
    
    print("\nOUTPUT GAPS:")
    print("1. No export to different formats (CSV, JSON, etc.)")
    print("2. No summary report generation")
    print("3. No email notifications on completion")
    print("4. No integration with monitoring systems")


def propose_enhanced_interface():
    """Propose enhanced interface for better retrieval"""
    print("\n" + "=" * 80)
    print("5. PROPOSED ENHANCED INTERFACE")
    print("=" * 80)
    
    print("\nPROPOSED METHOD SIGNATURE:")
    print("""
async def process_batch(
    self,
    # Quantity controls
    limit: int = 10,
    offset: int = 0,
    
    # Source controls
    source_table: str = 'public.court_documents',
    source_type: str = 'database',  # 'database', 'courtlistener', 'file'
    
    # Filtering
    filters: Dict[str, Any] = None,
    # Example filters:
    # {
    #     'date_range': {'start': '2024-01-01', 'end': '2024-12-31'},
    #     'courts': ['nysd', 'cand'],
    #     'judges': ['Kaplan', 'Chen'],
    #     'document_types': ['opinion', 'order'],
    #     'case_numbers': ['pattern:.*cv.*'],
    #     'content_search': 'patent infringement',
    #     'metadata_filters': {'has_pdf': True}
    # }
    
    # Processing controls
    validate_strict: bool = True,
    skip_processed: bool = True,
    parallel_workers: int = 1,
    checkpoint_interval: int = 100,
    
    # Output controls
    output_format: str = 'dict',  # 'dict', 'json', 'csv'
    output_file: str = None,
    send_notifications: bool = False
) -> Dict[str, Any]:
    """)
    
    print("\nPROPOSED QUERY BUILDER:")
    print("""
# Example usage with query builder
from pipeline_query_builder import QueryBuilder

query = (QueryBuilder()
    .from_courts(['nysd', 'cand'])
    .filed_between('2024-01-01', '2024-12-31')
    .with_judges(['Kaplan', 'Chen'])
    .document_types(['opinion'])
    .containing_text('patent infringement')
    .limit(100))

pipeline = RobustElevenStagePipeline()
results = await pipeline.process_query(query)
    """)


def show_current_workarounds():
    """Show how to work around current limitations"""
    print("\n" + "=" * 80)
    print("6. CURRENT WORKAROUNDS")
    print("=" * 80)
    
    print("\nFOR DATE FILTERING:")
    print("""
# Create a filtered view in PostgreSQL:
CREATE VIEW recent_documents AS
SELECT * FROM public.court_documents
WHERE created_at >= '2024-01-01'
AND created_at < '2025-01-01';

# Then use:
pipeline.process_batch(source_table='public.recent_documents')
    """)
    
    print("\nFOR COURT/JUDGE FILTERING:")
    print("""
# Pre-filter in database:
cursor.execute('''
    SELECT id FROM public.court_documents
    WHERE metadata->>'court' = 'nysd'
    OR content ILIKE '%Judge Kaplan%'
''')
doc_ids = [row['id'] for row in cursor.fetchall()]

# Then modify _fetch_documents to accept ID list
    """)
    
    print("\nFOR COURTLISTENER INTEGRATION:")
    print("""
# Use separate fetch script first:
from courtlistener_integration/bulk_download.py import download_documents
docs = download_documents(court='nysd', filed_after='2024-01-01')

# Load into database, then process:
pipeline.process_batch()
    """)


async def main():
    """Run all demonstrations"""
    # Basic usage
    await demonstrate_basic_usage()
    
    # Custom parameters
    await demonstrate_custom_parameters()
    
    # Selective retrieval
    await demonstrate_selective_retrieval()
    
    # Implementation gaps
    show_implementation_gaps()
    
    # Enhanced interface proposal
    propose_enhanced_interface()
    
    # Current workarounds
    show_current_workarounds()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("""
The pipeline is fully functional for basic batch processing but lacks:
1. Flexible retrieval filters
2. Direct API integration
3. Parallel processing
4. Advanced output options

Key recommendation: Implement a QueryBuilder pattern for flexible filtering
while maintaining the robust 11-stage processing core.
    """)


if __name__ == "__main__":
    # Only run demonstrations if inside Docker
    if os.getenv('DATABASE_URL'):
        asyncio.run(main())
    else:
        # Just show the analysis
        demonstrate_selective_retrieval()
        show_implementation_gaps()
        propose_enhanced_interface()
        show_current_workarounds()
        
        print("\n" + "=" * 80)
        print("ACTIVATION EXAMPLES")
        print("=" * 80)
        print("""
# Basic activation (inside Docker):
docker-compose exec court-processor python -c "
import asyncio
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
pipeline = RobustElevenStagePipeline()
asyncio.run(pipeline.process_batch(limit=50))
"

# With custom parameters:
docker-compose exec court-processor python -c "
import asyncio
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
pipeline = RobustElevenStagePipeline()
asyncio.run(pipeline.process_batch(
    limit=100,
    validate_strict=False
))
"
        """)