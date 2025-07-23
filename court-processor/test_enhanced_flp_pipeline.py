#!/usr/bin/env python3
"""
Test Enhanced FLP Pipeline with proper field mapping
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from enhanced_flp_pipeline import enhance_pipeline_with_flp, EnhancedFLPFieldMapper
from services.database import get_db_connection
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_enhanced_pipeline():
    """Test the enhanced pipeline with FLP improvements"""
    
    logger.info("\n" + "="*80)
    logger.info("TESTING ENHANCED FLP PIPELINE")
    logger.info("="*80)
    
    # Test 1: Field mapper functionality
    logger.info("\n1. Testing Enhanced Field Mapper...")
    
    test_cases = [
        {
            'metadata': {
                'court': 'https://www.courtlistener.com/api/rest/v4/courts/txed/',
                'assigned_to_str': 'Judge Rodney Gilstrap'
            },
            'doc_type': 'docket',
            'expected_court': 'txed',
            'expected_judge': 'Judge Rodney Gilstrap'
        },
        {
            'metadata': {
                'court_id': 'cafc',
                'author_str': 'Newman'
            },
            'doc_type': 'opinion',
            'expected_court': 'cafc',
            'expected_judge': 'Newman'
        },
        {
            'metadata': {
                'court': 'https://www.courtlistener.com/api/rest/v4/courts/mdd/',
                'assignedTo': 'Smith, John'
            },
            'doc_type': 'search_result',
            'expected_court': 'mdd',
            'expected_judge': 'Smith, John'
        }
    ]
    
    for i, test in enumerate(test_cases):
        court = EnhancedFLPFieldMapper.extract_court_from_metadata(
            test['metadata'], test['doc_type']
        )
        judge = EnhancedFLPFieldMapper.extract_judge_from_metadata(
            test['metadata'], test['doc_type']
        )
        
        logger.info(f"\n  Test case {i+1}:")
        logger.info(f"    Doc type: {test['doc_type']}")
        logger.info(f"    Court: {court} (expected: {test['expected_court']})")
        logger.info(f"    Judge: {judge} (expected: {test['expected_judge']})")
        logger.info(f"    ✅ Pass" if court == test['expected_court'] and judge == test['expected_judge'] else "    ❌ Fail")
    
    # Test 2: Run enhanced pipeline on real data
    logger.info("\n\n2. Testing Enhanced Pipeline on Database Documents...")
    
    # Create enhanced pipeline instance
    pipeline = RobustElevenStagePipeline()
    pipeline = enhance_pipeline_with_flp(pipeline)
    
    # Process documents
    results = await pipeline.process_batch(limit=20)
    
    if results['success']:
        stats = results['statistics']
        logger.info(f"\nProcessing Results:")
        logger.info(f"  Documents processed: {stats['documents_processed']}")
        logger.info(f"  Courts resolved: {stats['courts_resolved']} ({stats['courts_resolved']/stats['documents_processed']*100:.1f}%)")
        logger.info(f"  Judges identified: {stats['judges_enhanced'] + stats['judges_extracted_from_content']}")
        
        # Quality metrics
        quality = results['quality_metrics']
        logger.info(f"\nQuality Metrics:")
        logger.info(f"  Court resolution rate: {quality['court_resolution_rate']:.1f}%")
        logger.info(f"  Judge identification rate: {quality['judge_identification_rate']:.1f}%")
        
        # Verification scores
        verification = results['verification']
        logger.info(f"\nOverall Performance:")
        logger.info(f"  Completeness: {verification['completeness_score']:.1f}%")
        logger.info(f"  Quality: {verification['quality_score']:.1f}%")
        
        # Type-specific performance
        if verification.get('by_document_type'):
            logger.info("\nPerformance by Document Type:")
            for doc_type, metrics in verification['by_document_type'].items():
                logger.info(f"\n  {doc_type.upper()}:")
                logger.info(f"    Court resolution: {metrics['court_resolution_rate']:.1f}%")
                logger.info(f"    Judge identification: {metrics['judge_identification_rate']:.1f}%")
                logger.info(f"    Quality score: {metrics['quality_score']:.1f}%")
    
    # Test 3: Check specific document improvements
    logger.info("\n\n3. Checking Specific Document Improvements...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get some RECAP dockets
    cursor.execute("""
        SELECT id, case_number, metadata
        FROM public.court_documents
        WHERE case_number LIKE 'RECAP-%'
        LIMIT 5
    """)
    
    for doc_id, case_number, metadata in cursor.fetchall():
        if isinstance(metadata, dict):
            metadata_dict = metadata
        elif isinstance(metadata, str):
            metadata_dict = json.loads(metadata)
        else:
            metadata_dict = {}
        
        # Apply enhanced extraction
        court = EnhancedFLPFieldMapper.extract_court_from_metadata(metadata_dict, 'docket')
        judge = EnhancedFLPFieldMapper.extract_judge_from_metadata(metadata_dict, 'docket')
        
        logger.info(f"\n  Document: {case_number}")
        logger.info(f"    Original court: {metadata_dict.get('court', 'None')}")
        logger.info(f"    Extracted court: {court}")
        logger.info(f"    Original judge: {metadata_dict.get('assigned_to_str', 'None')}")
        logger.info(f"    Extracted judge: {judge}")
    
    conn.close()
    
    logger.info("\n" + "="*80)
    logger.info("ENHANCED FLP PIPELINE TEST COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    if not os.getenv('DATABASE_URL'):
        # Test field mapper outside Docker
        logger.info("Running field mapper tests only (outside Docker)...")
        
        # Test cases
        test_url = 'https://www.courtlistener.com/api/rest/v4/courts/txed/'
        court_id = EnhancedFLPFieldMapper.extract_court_from_metadata(
            {'court': test_url}, 'docket'
        )
        logger.info(f"Extracted court ID '{court_id}' from URL: {test_url}")
        
        judge_name = EnhancedFLPFieldMapper.extract_judge_from_metadata(
            {'assigned_to_str': 'Judge Rodney Gilstrap'}, 'docket'
        )
        logger.info(f"Extracted judge: {judge_name}")
    else:
        # Run full test inside Docker
        asyncio.run(test_enhanced_pipeline())