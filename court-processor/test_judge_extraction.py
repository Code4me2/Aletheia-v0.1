#!/usr/bin/env python3
"""
Test judge extraction improvements
"""

import asyncio
import logging
from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline
from datetime import datetime
from services.database import get_db_connection
import json

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_judge_extraction():
    """Test judge extraction with different scenarios"""
    
    # Create a pipeline instance
    pipeline = OptimizedElevenStagePipeline()
    
    test_cases = [
        {
            'name': 'Judge initials only (docket style)',
            'document': {
                'metadata': {
                    'federal_dn_judge_initials_assigned': 'RG',
                    'court_id': 'txed'
                },
                'content': 'Test document with no judge name in content'
            }
        },
        {
            'name': 'Full judge name in metadata',
            'document': {
                'metadata': {
                    'judge_name': 'Rodney Gilstrap',
                    'court_id': 'txed'
                },
                'content': 'Test document'
            }
        },
        {
            'name': 'Judge in assigned_to field',
            'document': {
                'metadata': {
                    'assigned_to': 'Rodney Gilstrap',
                    'court_id': 'txed'
                },
                'content': 'Test document'
            }
        },
        {
            'name': 'Judge name in content only',
            'document': {
                'metadata': {'court_id': 'txed'},
                'content': 'UNITED STATES DISTRICT COURT\nEASTERN DISTRICT OF TEXAS\n\nBefore: Honorable Judge Rodney Gilstrap, Chief District Judge\n\nThis is a test opinion.'
            }
        },
        {
            'name': 'Judge signature at end',
            'document': {
                'metadata': {'court_id': 'txed'},
                'content': 'This is a test document.\n\n' + 'x' * 1000 + '\n\nSigned by Judge Rodney Gilstrap\nUnited States District Judge'
            }
        },
        {
            'name': 'No judge information',
            'document': {
                'metadata': {'court_id': 'txed'},
                'content': 'Test document with no judge information whatsoever.'
            }
        },
        {
            'name': 'Judge initials and name',
            'document': {
                'metadata': {
                    'federal_dn_judge_initials_assigned': 'RG',
                    'judge_name': 'Rodney Gilstrap'
                },
                'content': 'Test document'
            }
        },
        {
            'name': 'Different judge',
            'document': {
                'metadata': {
                    'assigned_to': 'Amos Mazzant',
                    'court_id': 'txed'
                },
                'content': 'Test document'
            }
        }
    ]
    
    print("JUDGE EXTRACTION TEST RESULTS")
    print("=" * 80)
    
    enhanced_count = 0
    partial_count = 0
    
    for test in test_cases:
        print(f"\nTest: {test['name']}")
        print("-" * 40)
        
        # Call the optimized judge extraction method
        result = pipeline._enhance_judge_info_optimized(test['document'])
        
        if result.get('enhanced'):
            enhanced_count += 1
            print(f"✅ ENHANCED")
            print(f"   Judge ID: {result.get('judge_id')}")
            print(f"   Full Name: {result.get('full_name')}")
            print(f"   Photo Available: {result.get('photo_available', False)}")
            print(f"   From Content: {result.get('extracted_from_content', False)}")
        elif result.get('judge_name_found') or result.get('judge_initials'):
            partial_count += 1
            print(f"⚠️  PARTIAL INFO")
            print(f"   Judge Found: {result.get('judge_name_found', result.get('attempted_name', ''))}")
            print(f"   Initials: {result.get('judge_initials', 'N/A')}")
            print(f"   Reason: {result.get('reason')}")
        else:
            print(f"❌ NOT ENHANCED")
            print(f"   Reason: {result.get('reason')}")
            if result.get('error'):
                print(f"   Error: {result.get('error')}")
    
    total_with_info = enhanced_count + partial_count
    print(f"\n\nSUMMARY:")
    print(f"  Fully Enhanced: {enhanced_count}/{len(test_cases)} ({enhanced_count/len(test_cases)*100:.1f}%)")
    print(f"  Partial Info: {partial_count}/{len(test_cases)} ({partial_count/len(test_cases)*100:.1f}%)")
    print(f"  Total with Info: {total_with_info}/{len(test_cases)} ({total_with_info/len(test_cases)*100:.1f}%)")
    
    # Close DB connection
    if pipeline.db_conn:
        pipeline.db_conn.close()


if __name__ == "__main__":
    test_judge_extraction()