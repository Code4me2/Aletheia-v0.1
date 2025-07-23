#!/usr/bin/env python3
"""
Test the enhanced pipeline with various document types
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from services.courtlistener_service import CourtListenerService
from eleven_stage_pipeline_enhanced import EnhancedElevenStagePipeline

# Test API token
API_TOKEN = 'f751990518aacab953214f2e56ac6ccbff9e2c14'

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_with_opinions():
    """Test pipeline with opinion data (should have higher completeness)"""
    
    service = CourtListenerService(api_key=API_TOKEN)
    
    # Fetch opinions instead of dockets
    logger.info("Fetching opinions from CourtListener...")
    
    opinions = await service.fetch_opinions(
        court='txed',
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        limit=5
    )
    
    if not opinions:
        logger.error("No opinions fetched")
        return None
    
    logger.info(f"Fetched {len(opinions)} opinions")
    
    # Store and process
    stored = await service.store_documents(opinions, 'opinion')
    logger.info(f"Stored {stored} opinions")
    
    # Run enhanced pipeline
    pipeline = EnhancedElevenStagePipeline()
    results = await pipeline.process_batch(limit=5)
    
    return results


async def test_with_mixed_documents():
    """Test with both dockets and opinions"""
    
    service = CourtListenerService(api_key=API_TOKEN)
    
    # Fetch some dockets
    logger.info("Fetching dockets...")
    session = await service._get_session()
    
    params = {
        'court__id': 'txed',
        'cluster__date_filed__gte': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
        'order_by': '-cluster__date_filed',
        'page_size': 3
    }
    
    url = f"{service.BASE_URL}{service.DOCKETS_ENDPOINT}"
    documents = []
    
    try:
        async with session.get(url, params=params, headers=service.headers) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                
                # Transform dockets
                for docket in results:
                    content = f"Case: {docket.get('case_name', 'Unknown')}\n"
                    content += f"Docket Number: {docket.get('docket_number', 'Unknown')}\n"
                    
                    metadata = {
                        'court_id': docket.get('court_id', 'txed'),
                        'case_name': docket.get('case_name'),
                        'federal_dn_judge_initials_assigned': docket.get('federal_dn_judge_initials_assigned'),
                        'docket_number': docket.get('docket_number')
                    }
                    
                    doc = {
                        'case_number': docket.get('docket_number', f'DOCKET-{len(documents)}'),
                        'document_type': 'docket',
                        'content': content,
                        'metadata': metadata
                    }
                    documents.append(doc)
        
        # Now fetch some opinions
        logger.info("Fetching opinions...")
        opinions = await service.fetch_opinions(
            court='txed',
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            limit=2
        )
        
        if opinions:
            documents.extend(opinions)
        
        # Store all documents
        if documents:
            logger.info(f"Storing {len(documents)} mixed documents...")
            stored_count = 0
            for doc in documents:
                stored = await service.store_documents([doc], doc.get('document_type', 'unknown'))
                stored_count += stored
            
            logger.info(f"Stored {stored_count} documents")
            
            # Run enhanced pipeline
            pipeline = EnhancedElevenStagePipeline()
            results = await pipeline.process_batch(limit=len(documents))
            
            return results
            
    finally:
        await session.close()
    
    return None


async def main():
    """Run comprehensive tests"""
    
    print("\n" + "=" * 80)
    print("ENHANCED PIPELINE TESTING")
    print("=" * 80)
    
    # Test 1: Opinions (should have higher completeness)
    print("\n\n🧪 TEST 1: Opinion Documents")
    print("-" * 40)
    
    opinion_results = await test_with_opinions()
    
    if opinion_results and opinion_results['success']:
        verification = opinion_results['verification']
        print(f"\nOpinion Completeness: {verification['completeness_score']:.1f}%")
        
        if 'completeness_by_type' in verification:
            for doc_type, stats in verification['completeness_by_type'].items():
                print(f"  {doc_type}: {stats['completeness']:.1f}% ({stats['documents']} docs)")
    
    # Test 2: Mixed documents
    print("\n\n🧪 TEST 2: Mixed Document Types")
    print("-" * 40)
    
    mixed_results = await test_with_mixed_documents()
    
    if mixed_results and mixed_results['success']:
        verification = mixed_results['verification']
        print(f"\nOverall Completeness: {verification['completeness_score']:.1f}%")
        
        if 'completeness_by_type' in verification:
            print("\nCompleteness by Type:")
            for doc_type, stats in verification['completeness_by_type'].items():
                print(f"  {doc_type}: {stats['completeness']:.1f}% ({stats['documents']} docs)")
        
        # Show improvements
        improvements = verification.get('extraction_improvements', {})
        print(f"\nExtraction Improvements:")
        print(f"  Courts from content: {improvements.get('courts_from_content', 0)}")
        print(f"  Judges from content: {improvements.get('judges_from_content', 0)}")
        print(f"  Judges from initials: {improvements.get('judges_from_initials', 0)}")
        print(f"  Citations from dockets: {improvements.get('citations_from_docket_entries', 0)}")
    
    print("\n" + "=" * 80)
    print("Testing complete!")


if __name__ == "__main__":
    asyncio.run(main())