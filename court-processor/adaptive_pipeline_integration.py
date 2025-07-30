#!/usr/bin/env python3
"""
Integration of adaptive processing into the existing pipeline
Handles errors and validates actual processing
"""
import asyncio
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

sys.path.append('/app')

from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
from document_type_detector import DocumentTypeDetector
from pipeline_adapter import PipelineAdapter
from services.database import get_db_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AdaptiveElevenStagePipeline(RobustElevenStagePipeline):
    """Enhanced pipeline with adaptive document processing"""
    
    def __init__(self):
        super().__init__()
        self.adapter = PipelineAdapter()
        self.detector = DocumentTypeDetector()
        
        # Track what actually happened
        self.processing_summary = {
            'documents_attempted': 0,
            'documents_processed': 0,
            'stages_skipped': 0,
            'empty_results': 0,
            'errors_caught': 0,
            'adaptations_made': 0
        }
    
    async def process_batch(self, limit: int = 10, **kwargs) -> Dict[str, Any]:
        """Override to add pre-processing fixes"""
        
        # First, ensure Texas documents have cl_id
        self._fix_missing_cl_ids()
        
        # Then process normally
        return await super().process_batch(limit=limit, **kwargs)
    
    def _fix_missing_cl_ids(self):
        """Fix documents missing cl_id before processing"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Add cl_id where missing
            cursor.execute("""
                UPDATE public.court_documents
                SET metadata = 
                    CASE 
                        WHEN metadata IS NULL THEN jsonb_build_object('cl_id', id::text)
                        WHEN metadata->>'cl_id' IS NULL THEN metadata || jsonb_build_object('cl_id', id::text)
                        ELSE metadata
                    END
                WHERE metadata->>'cl_id' IS NULL 
                   OR metadata->>'cl_id' = ''
                RETURNING id
            """)
            
            fixed_ids = [row[0] for row in cursor.fetchall()]
            if fixed_ids:
                conn.commit()
                logger.info(f"Fixed {len(fixed_ids)} documents with missing cl_id")
                self.processing_summary['adaptations_made'] += len(fixed_ids)
            
        except Exception as e:
            logger.error(f"Error fixing cl_ids: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    async def stage_3_citation_extraction(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Adaptive citation extraction"""
        self.processing_summary['documents_attempted'] += 1
        
        # Check if we should run this stage
        if not self.adapter.should_run_stage('citation_extraction', document):
            self.processing_summary['stages_skipped'] += 1
            logger.info(f"Skipping citation extraction for {document.get('document_type')} document")
            return {
                'citations_extracted': [],
                'citations_validated': [],
                'skipped': True,
                'reason': f"Not applicable for {document.get('document_type')} documents"
            }
        
        # Run original stage
        result = await super().stage_3_citation_extraction(document)
        
        # Validate we got actual results
        if not result.get('citations_extracted') and len(document.get('content', '')) > 5000:
            self.processing_summary['empty_results'] += 1
            logger.warning(f"No citations found in large document {document.get('cl_id')}")
        
        return result
    
    async def stage_6_judge_enhancement(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Adaptive judge extraction"""
        
        method = self.adapter.get_judge_extraction_method(document)
        
        if method in ['metadata_only', 'metadata']:
            # Extract from metadata
            metadata = document.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            
            judge_name = (
                metadata.get('assigned_to') or 
                metadata.get('assigned_to_str') or
                metadata.get('judge') or
                metadata.get('judges', [None])[0] if isinstance(metadata.get('judges'), list) else None
            )
            
            if judge_name:
                # Clean up judge name if it's a URL
                if isinstance(judge_name, str) and 'courtlistener.com' in judge_name:
                    # Extract name from URL like /api/rest/v4/people/rodney-gilstrap/
                    parts = judge_name.strip('/').split('/')
                    if parts:
                        judge_name = parts[-1].replace('-', ' ').title()
                
                logger.info(f"Extracted judge from metadata: {judge_name}")
                self.processing_summary['adaptations_made'] += 1
                
                return {
                    'enhanced': True,
                    'full_name': judge_name,
                    'source': 'metadata.assigned_to',
                    'extracted_from_content': False,
                    'validation': {'valid': True}
                }
        
        # Otherwise use content extraction
        result = await super().stage_6_judge_enhancement(document)
        
        # If content extraction failed but we have metadata, try that
        if not result.get('enhanced') and method == 'content_and_metadata':
            metadata_result = await self.stage_6_judge_enhancement({**document, 'force_metadata': True})
            if metadata_result.get('enhanced'):
                return metadata_result
        
        return result
    
    async def stage_11_verification(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Enhanced verification with adaptive metrics"""
        
        # Get base verification
        base_verification = await super().stage_11_verification(documents)
        
        # Adapt metrics for each document type
        adapted_scores = {
            'opinion': {'count': 0, 'total_score': 0.0},
            'docket': {'count': 0, 'total_score': 0.0},
            'order': {'count': 0, 'total_score': 0.0},
            'other': {'count': 0, 'total_score': 0.0}
        }
        
        for doc in documents:
            doc_type, confidence, _ = self.detector.detect_type(doc)
            
            # Calculate appropriate metrics
            if doc_type == 'docket':
                # Docket-specific scoring
                score = self._calculate_docket_score(doc)
                adapted_scores['docket']['count'] += 1
                adapted_scores['docket']['total_score'] += score
            elif doc_type == 'opinion':
                # Opinion scoring (original method)
                score = self._calculate_opinion_score(doc)
                adapted_scores['opinion']['count'] += 1
                adapted_scores['opinion']['total_score'] += score
            else:
                # Generic scoring
                score = 50.0  # Base score
                category = 'order' if doc_type == 'order' else 'other'
                adapted_scores[category]['count'] += 1
                adapted_scores[category]['total_score'] += score
        
        # Add adapted metrics to verification
        base_verification['adapted_metrics'] = {}
        for doc_type, data in adapted_scores.items():
            if data['count'] > 0:
                avg_score = data['total_score'] / data['count']
                base_verification['adapted_metrics'][doc_type] = {
                    'count': data['count'],
                    'average_score': avg_score
                }
        
        # Add processing summary
        base_verification['processing_summary'] = self.processing_summary
        
        # Validate we actually processed something
        if self.processing_summary['documents_processed'] == 0:
            logger.error("WARNING: Pipeline completed but no documents were actually processed!")
            base_verification['warning'] = "No documents were processed despite successful completion"
        
        return base_verification
    
    def _calculate_docket_score(self, document: Dict[str, Any]) -> float:
        """Calculate quality score for docket documents"""
        score = 0.0
        metadata = document.get('metadata', {})
        
        # Court resolution (40 points)
        if document.get('court_enhanced'):
            score += 40.0
        
        # Judge identification (30 points)
        if document.get('judge_enhanced') or metadata.get('assigned_to'):
            score += 30.0
        
        # Metadata completeness (30 points)
        important_fields = ['case_name', 'date_filed', 'docket_number', 'nature_of_suit']
        present = sum(1 for field in important_fields if metadata.get(field))
        score += (present / len(important_fields)) * 30.0
        
        return score
    
    def _calculate_opinion_score(self, document: Dict[str, Any]) -> float:
        """Calculate quality score for opinion documents"""
        score = 0.0
        
        # Court (25 points)
        if document.get('court_enhanced'):
            score += 25.0
        
        # Citations (25 points)  
        citations = document.get('citations_extracted', [])
        if len(citations) > 10:
            score += 25.0
        elif len(citations) > 0:
            score += (len(citations) / 10) * 25.0
        
        # Judge (25 points)
        if document.get('judge_enhanced'):
            score += 25.0
        
        # Structure/Keywords (25 points)
        if document.get('keywords_extracted'):
            score += 12.5
        if document.get('structure_analyzed'):
            score += 12.5
        
        return score


async def test_adaptive_pipeline():
    """Test the adaptive pipeline with validation"""
    
    logger.info("=" * 80)
    logger.info("TESTING ADAPTIVE PIPELINE")
    logger.info("=" * 80)
    
    pipeline = AdaptiveElevenStagePipeline()
    
    # Process a mix of documents
    results = await pipeline.process_batch(limit=30, force_reprocess=True)
    
    if results['success']:
        print("\n" + "=" * 80)
        print("ADAPTIVE PIPELINE RESULTS")
        print("=" * 80)
        
        # Standard metrics
        stats = results['statistics']
        print(f"\nDocuments processed: {stats['documents_processed']}")
        print(f"Processing summary: {results['verification']['processing_summary']}")
        
        # Adapted metrics by type
        if 'adapted_metrics' in results['verification']:
            print("\nAdapted Metrics by Document Type:")
            for doc_type, metrics in results['verification']['adapted_metrics'].items():
                if metrics['count'] > 0:
                    print(f"  {doc_type}: {metrics['count']} docs, avg score: {metrics['average_score']:.1f}%")
        
        # Warnings
        if 'warning' in results['verification']:
            print(f"\n⚠️  WARNING: {results['verification']['warning']}")
        
        # Validation checks
        summary = results['verification']['processing_summary']
        if summary['empty_results'] > 0:
            print(f"\n⚠️  Found {summary['empty_results']} documents with unexpectedly empty results")
        
        if summary['documents_attempted'] > summary['documents_processed']:
            print(f"\n⚠️  Gap detected: Attempted {summary['documents_attempted']}, processed {summary['documents_processed']}")
        
        print(f"\nAdaptations made: {summary['adaptations_made']}")
        print(f"Stages skipped: {summary['stages_skipped']}")
        
    else:
        print(f"\nPipeline failed: {results.get('error')}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_adaptive_pipeline())