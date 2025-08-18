#!/usr/bin/env python3
"""
Test the unified pipeline with enhanced 3-step traversal
"""
import asyncio
import sys
import os
from datetime import datetime
import json
from typing import Dict, Optional
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import UnifiedDocumentProcessor
from services.enhanced_courtlistener_fetcher import EnhancedCourtListenerFetcher
from services.database import get_db_connection

logger = logging.getLogger(__name__)

class EnhancedUnifiedProcessor(UnifiedDocumentProcessor):
    """Unified processor with 3-step traversal enhancement"""
    
    def __init__(self):
        super().__init__()
        self.enhanced_fetcher = EnhancedCourtListenerFetcher(self.cl_service)
    
    async def process_courtlistener_batch(self, 
                                        court_id: Optional[str] = None,
                                        date_filed_after: Optional[str] = None,
                                        max_documents: int = 100) -> Dict:
        """Override to use enhanced fetcher"""
        result = {
            'total_fetched': 0,
            'enhanced': 0,
            'saved': 0,
            'errors': 0,
            'processing_time': datetime.utcnow().isoformat()
        }
        
        try:
            # Fetch opinions
            opinions = await self.cl_service.fetch_opinions(
                court_id=court_id,
                date_filed_after=date_filed_after,
                max_results=max_documents
            )
            
            result['total_fetched'] = len(opinions)
            print(f"\nFetched {len(opinions)} opinions")
            
            if not opinions:
                return result
            
            # Enhance with 3-step traversal
            print("Performing 3-step traversal to fetch complete metadata...")
            enhanced_opinions = await self.enhanced_fetcher.fetch_complete_batch(opinions)
            result['enhanced'] = len(enhanced_opinions)
            
            # Process each enhanced opinion
            for i, enhanced_op in enumerate(enhanced_opinions):
                print(f"\nProcessing opinion {i+1}/{len(enhanced_opinions)}: {enhanced_op.get('id')}")
                
                # Extract metadata using the enhanced fetcher
                metadata = self.enhanced_fetcher.extract_metadata(enhanced_op)
                
                # Merge metadata into the opinion
                for key, value in metadata.items():
                    if value and not enhanced_op.get(key):
                        enhanced_op[key] = value
                
                # Show what we extracted
                print(f"  Case: {metadata['case_name'] or 'MISSING'}")
                print(f"  Court: {metadata['court_id'] or 'MISSING'}")
                print(f"  Docket: {metadata['docket_number'] or 'MISSING'}")
                print(f"  Judge: {metadata['assigned_judge'] or 'MISSING'}")
                print(f"  Judge initials: {metadata['judge_initials'] or 'N/A'}")
                
                try:
                    # Process with the existing pipeline
                    processed = await self.process_single_document(enhanced_op)
                    if processed:
                        result['saved'] += 1
                except Exception as e:
                    print(f"  ERROR: {e}")
                    result['errors'] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            result['errors'] += 1
            return result


async def test_enhanced_traversal():
    print("="*80)
    print("ENHANCED 3-STEP TRAVERSAL TEST")
    print("="*80)
    print(f"Start time: {datetime.now()}")
    
    processor = EnhancedUnifiedProcessor()
    
    # Test with E.D. Texas opinions looking for Gilstrap
    params = {
        'court_id': 'txed',
        'date_filed_after': '2016-06-01',
        'max_documents': 5  # Small batch for testing
    }
    
    print(f"\nTest parameters: {json.dumps(params, indent=2)}")
    
    try:
        # Clear some documents for fresh test
        print("\n1. Preparing for fresh test...")
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Delete a few test documents to allow fresh processing
        cursor.execute("""
            DELETE FROM court_data.opinions_unified 
            WHERE cl_id IN (
                SELECT cl_id FROM court_data.opinions_unified 
                WHERE court_id = 'txed' OR court_id IS NULL
                LIMIT 5
            )
            RETURNING cl_id
        """)
        deleted = cursor.fetchall()
        conn.commit()
        print(f"Cleared {len(deleted)} documents for fresh processing")
        
        cursor.close()
        conn.close()
        
        # Run enhanced processor
        print("\n2. Running enhanced unified processor...")
        results = await processor.process_courtlistener_batch(
            court_id=params['court_id'],
            date_filed_after=params['date_filed_after'],
            max_documents=params['max_documents']
        )
        
        print(f"\n3. Processing results: {json.dumps(results, indent=2)}")
        
        # Check what was saved
        if results.get('saved', 0) > 0:
            print("\n4. Checking saved documents...")
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    id,
                    case_name,
                    court_id,
                    docket_number,
                    author_str,
                    assigned_judge_name
                FROM court_data.opinions_unified
                WHERE created_at >= NOW() - INTERVAL '5 minutes'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            print("\nSaved documents:")
            gilstrap_found = 0
            for row in cursor.fetchall():
                print(f"\nDoc ID: {row[0]}")
                print(f"  Case: {row[1] or 'MISSING'}")
                print(f"  Court: {row[2] or 'MISSING'}")
                print(f"  Docket: {row[3] or 'MISSING'}")
                print(f"  Author: {row[4] or 'MISSING'}")
                print(f"  Assigned: {row[5] or 'MISSING'}")
                
                # Check for Gilstrap
                docket_suffix = row[3].split('-')[-1] if row[3] and '-' in row[3] else ''
                if any(['Gilstrap' in str(field) for field in row[4:6]]) or docket_suffix == 'JRG':
                    print("  *** GILSTRAP CASE FOUND! ***")
                    gilstrap_found += 1
            
            print(f"\nTotal Gilstrap cases found: {gilstrap_found}")
            
            cursor.close()
            conn.close()
            
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await processor.cl_service.close()


if __name__ == "__main__":
    asyncio.run(test_enhanced_traversal())