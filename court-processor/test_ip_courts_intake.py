#!/usr/bin/env python3
"""
Test larger scale intake of IP courts data from CourtListener

This script fetches IP-related cases from key venues and processes them
through the pipeline to see if we get better metadata and scores.
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.courtlistener_service import CourtListenerService
from services.database import get_db_connection
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
import json
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def fetch_ip_court_data():
    """Fetch IP-focused court data from CourtListener"""
    logger.info("\n" + "="*80)
    logger.info("FETCHING IP COURT DATA FROM COURTLISTENER")
    logger.info("="*80)
    
    service = CourtListenerService()
    all_documents = []
    
    # 1. Try RECAP dockets for IP cases (these have better metadata)
    logger.info("\n1. Fetching RECAP IP dockets...")
    try:
        # Key IP courts
        ip_courts = ['txed', 'deld', 'cand', 'nysd', 'ilnd']
        # Patent nature of suit codes
        patent_nos = ['830', '835']  # Patent, Patent-ANDA
        
        recap_dockets = await service.fetch_recap_dockets(
            court_ids=ip_courts,
            nature_of_suit=patent_nos,
            date_filed_after='2024-01-01',
            max_results=20
        )
        
        logger.info(f"   Found {len(recap_dockets)} RECAP patent dockets")
        
        # Convert RECAP dockets to our format
        for docket in recap_dockets:
            doc = {
                'case_number': f"RECAP-{docket.get('docket_number', 'unknown')}",
                'document_type': 'docket',
                'content': json.dumps(docket, indent=2)[:5000],  # Store docket data as content
                'metadata': {
                    'source': 'courtlistener_recap',
                    'court': docket.get('court'),
                    'court_id': docket.get('court_id'),
                    'case_name': docket.get('case_name'),
                    'date_filed': docket.get('date_filed'),
                    'nature_of_suit': docket.get('nature_of_suit'),
                    'assigned_to': docket.get('assigned_to_str'),  # Judge name!
                    'referred_to': docket.get('referred_to_str'),
                    'cause': docket.get('cause'),
                    'jurisdiction_type': docket.get('jurisdiction_type'),
                    'recap_id': docket.get('id')
                }
            }
            all_documents.append(doc)
            
    except Exception as e:
        logger.error(f"Failed to fetch RECAP dockets: {e}")
    
    # 2. Try Federal Circuit opinions
    logger.info("\n2. Fetching Federal Circuit opinions...")
    try:
        fed_circuit_opinions = await service.fetch_opinions(
            court_id='cafc',  # Court of Appeals for Federal Circuit
            date_filed_after='2024-01-01',
            max_results=10
        )
        
        logger.info(f"   Found {len(fed_circuit_opinions)} Federal Circuit opinions")
        
        for opinion in fed_circuit_opinions:
            doc = {
                'case_number': f"CAFC-{opinion.get('id', 'unknown')}",
                'document_type': 'opinion',
                'content': opinion.get('plain_text', opinion.get('html', ''))[:5000],
                'metadata': {
                    'source': 'courtlistener_opinion',
                    'court': 'cafc',  # We know this from our query
                    'cluster': opinion.get('cluster'),
                    'type': opinion.get('type'),
                    'author': opinion.get('author_str'),
                    'joined_by': opinion.get('joined_by_str'),
                    'cl_id': opinion.get('id')
                }
            }
            all_documents.append(doc)
            
    except Exception as e:
        logger.error(f"Failed to fetch Federal Circuit opinions: {e}")
    
    # 3. Search for specific IP terms
    logger.info("\n3. Searching for patent infringement cases...")
    try:
        search_results = await service.search_recap(
            query='patent infringement',
            court_ids=['txed', 'deld'],
            date_range=('2024-01-01', '2024-12-31'),
            max_results=10
        )
        
        logger.info(f"   Found {len(search_results)} search results")
        
        for result in search_results:
            doc = {
                'case_number': f"SEARCH-{result.get('docket_id', 'unknown')}",
                'document_type': 'search_result',
                'content': result.get('snippet', '')[:5000],
                'metadata': {
                    'source': 'courtlistener_search',
                    'court': result.get('court'),
                    'case_name': result.get('caseName'),
                    'date_filed': result.get('dateFiled'),
                    'docket_id': result.get('docket_id'),
                    'result_type': result.get('type')
                }
            }
            all_documents.append(doc)
            
    except Exception as e:
        logger.error(f"Failed to search: {e}")
    
    await service.close()
    
    logger.info(f"\nTotal documents fetched: {len(all_documents)}")
    logger.info(f"Document types: {[d['document_type'] for d in all_documents[:5]]}...")
    
    return all_documents


async def store_documents(documents):
    """Store documents in database"""
    logger.info("\n" + "="*80)
    logger.info("STORING DOCUMENTS IN DATABASE")
    logger.info("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    stored_count = 0
    
    for doc in documents:
        try:
            # Check if exists
            cursor.execute("""
                SELECT id FROM public.court_documents 
                WHERE case_number = %s
            """, (doc['case_number'],))
            existing = cursor.fetchone()
            
            if existing:
                # Update
                cursor.execute("""
                    UPDATE public.court_documents 
                    SET metadata = %s,
                        content = %s,
                        document_type = %s,
                        updated_at = NOW()
                    WHERE case_number = %s
                """, (
                    json.dumps(doc['metadata']),
                    doc['content'],
                    doc['document_type'],
                    doc['case_number']
                ))
            else:
                # Insert
                cursor.execute("""
                    INSERT INTO public.court_documents 
                    (case_number, document_type, content, metadata, created_at)
                    VALUES (%s, %s, %s, %s, NOW())
                """, (
                    doc['case_number'],
                    doc['document_type'],
                    doc['content'],
                    json.dumps(doc['metadata'])
                ))
            
            stored_count += 1
            
        except Exception as e:
            logger.error(f"Failed to store document {doc['case_number']}: {e}")
    
    conn.commit()
    conn.close()
    
    logger.info(f"Stored {stored_count}/{len(documents)} documents")
    return stored_count


async def process_pipeline():
    """Process stored documents through pipeline"""
    logger.info("\n" + "="*80)
    logger.info("PROCESSING THROUGH PIPELINE")
    logger.info("="*80)
    
    pipeline = RobustElevenStagePipeline()
    results = await pipeline.process_batch(limit=50)  # Process up to 50 documents
    
    return results


async def main():
    """Main execution"""
    logger.info("\n" + "="*80)
    logger.info("IP COURTS LARGE SCALE INTAKE TEST")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now()}")
    
    # 1. Fetch IP court data
    documents = await fetch_ip_court_data()
    
    if not documents:
        logger.error("No documents fetched!")
        return
    
    # 2. Store in database
    stored = await store_documents(documents)
    
    if stored == 0:
        logger.error("No documents stored!")
        return
    
    # 3. Process through pipeline
    results = await process_pipeline()
    
    # 4. Analyze results
    logger.info("\n" + "="*80)
    logger.info("RESULTS ANALYSIS")
    logger.info("="*80)
    
    if results['success']:
        stats = results['statistics']
        logger.info(f"\nDocuments processed: {stats['documents_processed']}")
        logger.info(f"Courts resolved: {stats['courts_resolved']} ({stats['courts_resolved']/stats['documents_processed']*100:.1f}%)")
        logger.info(f"Citations extracted: {stats['citations_extracted']}")
        logger.info(f"Judges identified: {stats['judges_enhanced'] + stats['judges_extracted_from_content']}")
        
        # Document type breakdown
        logger.info("\nDocument Type Distribution:")
        for doc_type, info in results['document_type_statistics'].items():
            logger.info(f"  {doc_type}: {info['count']} ({info['percentage']:.1f}%)")
        
        # Quality metrics
        quality = results['quality_metrics']
        logger.info(f"\nQuality Metrics:")
        logger.info(f"  Court resolution rate: {quality['court_resolution_rate']:.1f}%")
        logger.info(f"  Citation extraction rate: {quality['citation_extraction_rate']:.1f}%")
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
                logger.info(f"    Total: {metrics['total']} documents")
                logger.info(f"    Court resolution: {metrics['court_resolution_rate']:.1f}%")
                logger.info(f"    Judge identification: {metrics['judge_identification_rate']:.1f}%")
                logger.info(f"    Quality score: {metrics['quality_score']:.1f}%")
        
        # Save detailed results
        output_file = f"ip_courts_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        logger.info(f"\nDetailed results saved to: {output_file}")
        
    else:
        logger.error(f"Pipeline failed: {results.get('error')}")
    
    logger.info(f"\nCompleted at: {datetime.now()}")


if __name__ == "__main__":
    if not os.getenv('DATABASE_URL'):
        print("\nERROR: Must run inside Docker container")
        print("Usage: docker-compose exec court-processor python test_ip_courts_intake.py")
        sys.exit(1)
    
    asyncio.run(main())