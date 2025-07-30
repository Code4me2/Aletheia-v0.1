#!/usr/bin/env python3
"""
Eleven Stage Pipeline - Adaptive Version
Implements document-type-aware processing based on ADAPTIVE_PIPELINE_IMPLEMENTATION.md

Key improvements:
1. Handles missing cl_id gracefully
2. Skips inappropriate stages based on document type
3. Extracts judges from metadata for dockets
4. Uses document-type-specific quality metrics
"""

import asyncio
import logging
import json
import hashlib
import re
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import aiohttp
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import AsIs

# Import our services
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.database import get_db_connection
from services.service_config import SERVICES, IS_DOCKER

# Import FLP components
from courts_db import find_court, courts
from eyecite import get_citations
from reporters_db import REPORTERS

# Import our custom components
from pipeline_exceptions import *
from pipeline_validators import *
from error_reporter import ErrorCollector

# Import existing pipeline to extend
from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AdaptiveElevenStagePipeline(RobustElevenStagePipeline):
    """Adaptive version of the eleven stage pipeline with document-type awareness"""
    
    def __init__(self):
        """Initialize adaptive pipeline with additional tracking"""
        super().__init__()
        
        # Additional stats for adaptive processing
        self.stats['stages_skipped'] = 0
        self.stats['judges_from_metadata'] = 0
        self.stats['adaptive_quality_scores'] = 0
        
    def _get_document_category(self, document: Dict[str, Any]) -> str:
        """Categorize document for appropriate processing"""
        doc_type = document.get('document_type', '')
        content_len = len(document.get('content', ''))
        
        if doc_type == 'opinion' and content_len > 5000:
            return 'full_opinion'
        elif doc_type in ['docket', 'recap_docket', 'civil_case']:
            return 'metadata_document'
        elif doc_type == 'order' and content_len > 1000:
            return 'order'
        else:
            return 'unknown'
    
    def _extract_cl_id(self, document: Dict[str, Any]) -> str:
        """Extract cl_id with fallback to document ID"""
        # Check top-level cl_id
        cl_id = document.get('cl_id')
        
        # Check metadata if not at top level
        if not cl_id:
            metadata = document.get('metadata', {})
            if isinstance(metadata, str):
                try:
                    metadata = json.loads(metadata)
                except:
                    metadata = {}
            cl_id = metadata.get('cl_id')
        
        # Fallback to document ID
        if not cl_id:
            cl_id = str(document.get('id', ''))
            
        # Generate one if both are missing
        if not cl_id:
            cl_id = f"gen_{document.get('case_number', 'unknown')}_{datetime.now().timestamp()}"
            document['cl_id'] = cl_id
            logger.warning(f"Generated cl_id for document: {cl_id}")
        
        return cl_id
    
    async def _process_single_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process a single document with adaptive stages based on type"""
        
        # Ensure cl_id exists
        doc_id = self._extract_cl_id(doc)
        doc['id'] = doc_id  # Ensure id field matches cl_id
        
        # Detect document category
        doc_category = self._get_document_category(doc)
        doc['detected_category'] = doc_category
        
        logger.info(f"\nProcessing {doc_category} document {idx + 1}: {doc_id}")
        
        # Process stages adaptively
        
        # STAGE 2: Court Resolution - Always run
        doc = self._enhance_court_info_validated(doc)
        
        # STAGE 3: Citation Extraction - Skip for metadata-only documents
        if doc_category in ['metadata_document']:
            logger.info(f"Skipping citation extraction for {doc.get('document_type')}")
            doc['citations_extracted'] = []
            doc['citations_validated'] = []
            doc['citation_extraction_skipped'] = True
            self.stats['stages_skipped'] += 1
        else:
            doc = self._extract_citations_validated(doc)
        
        # STAGE 4: Reporter Normalization - Only if citations exist
        if doc.get('citations_extracted'):
            doc = self._normalize_reporters_validated(doc)
        else:
            doc['reporter_normalization'] = {'skipped': True, 'reason': 'no_citations'}
            self.stats['stages_skipped'] += 1
        
        # STAGE 5: Judge Enhancement - Use metadata for dockets
        doc = self._enhance_judge_adaptive(doc)
        
        # STAGE 6: Document Structure - Skip for metadata-only
        if doc_category in ['metadata_document']:
            doc['structured_elements'] = {'skipped': True, 'reason': 'metadata_only'}
            self.stats['stages_skipped'] += 1
        else:
            doc['structured_elements'] = self._analyze_structure(doc)
        
        # STAGE 7: Keyword Extraction - Only for substantial content
        if len(doc.get('content', '')) < 1000:
            doc['keyword_extraction'] = {'skipped': True, 'reason': 'insufficient_content'}
            self.stats['stages_skipped'] += 1
        else:
            doc['keyword_extraction'] = self._extract_legal_keywords(doc)
        
        # STAGE 8: Metadata Assembly - Always run
        doc = self._assemble_metadata_validated(doc)
        
        return doc
    
    def _enhance_judge_adaptive(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract judge from appropriate source based on document type"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        category = document.get('detected_category', self._get_document_category(document))
        judge_name = None
        extraction_source = None
        
        # For dockets and civil cases, check metadata first
        if category == 'metadata_document':
            judge_name = (
                metadata.get('assigned_to') or
                metadata.get('assigned_to_str') or
                metadata.get('judge')
            )
            
            if judge_name:
                # Clean up if it's a URL
                if 'courtlistener.com' in str(judge_name):
                    parts = judge_name.strip('/').split('/')
                    judge_name = parts[-1].replace('-', ' ').title() if parts else judge_name
                
                extraction_source = 'metadata'
                self.stats['judges_from_metadata'] += 1
                
                document['judge_enhanced'] = True
                document['judge_name'] = judge_name
                document['judge_source'] = extraction_source
                document['judge_enhancement'] = {
                    'judge_name': judge_name,
                    'extraction_source': extraction_source,
                    'extraction_method': 'metadata_assigned_to',
                    'enhanced': True
                }
                
                logger.info(f"Extracted judge from metadata: {judge_name}")
                self.stats['judges_enhanced'] += 1
                return document
        
        # Fall back to standard judge enhancement for opinions
        return self._enhance_judge_info_validated(document)
    
    def _calculate_document_quality(self, document: Dict[str, Any]) -> float:
        """Calculate quality score based on document type"""
        category = document.get('detected_category', self._get_document_category(document))
        
        if category == 'full_opinion':
            # Traditional scoring for opinions
            score = 0.0
            
            # Court resolution (20%)
            if document.get('court_enhanced'):
                score += 20.0
            
            # Citations (30%)
            citation_count = len(document.get('citations_extracted', []))
            if citation_count > 0:
                score += min(30.0, citation_count * 2)
            
            # Judge information (20%)
            if document.get('judge_enhanced'):
                score += 20.0
            
            # Structure analysis (15%)
            if document.get('structured_elements'):
                score += 15.0
            
            # Keywords (15%)
            if len(document.get('keyword_extraction', {}).get('keywords', [])) > 0:
                score += 15.0
                
        elif category == 'metadata_document':
            # Adjusted scoring for dockets
            score = 0.0
            
            # Court resolution (40%)
            if document.get('court_enhanced'):
                score += 40.0
            
            # Judge identification (40%)
            if document.get('judge_enhanced') or document.get('judge_name'):
                score += 40.0
            
            # Metadata completeness (20%)
            metadata = document.get('metadata', {})
            key_fields = ['case_name', 'date_filed', 'nature_of_suit', 'docket_number']
            present = sum(1 for field in key_fields if metadata.get(field))
            score += (present / len(key_fields)) * 20.0
            
        else:
            # Default scoring
            score = 50.0
        
        self.stats['adaptive_quality_scores'] += 1
        return score
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Override to use adaptive quality calculation"""
        # Start with base metrics
        metrics = super()._calculate_quality_metrics()
        
        # Add adaptive processing metrics
        metrics['adaptive_processing'] = {
            'stages_skipped': self.stats['stages_skipped'],
            'judges_from_metadata': self.stats['judges_from_metadata'],
            'adaptive_quality_scores': self.stats['adaptive_quality_scores']
        }
        
        return metrics
    
    async def process_batch(self, 
                           limit: int = 100,
                           source_table: str = 'public.court_documents',
                           only_unprocessed: bool = False,
                           extract_pdfs: bool = False,
                           force_reprocess: bool = False,
                           validate_strict: bool = False) -> Dict[str, Any]:
        """Process documents with adaptive pipeline"""
        
        # Log adaptive processing
        logger.info("Starting ADAPTIVE pipeline processing")
        logger.info(f"Document-type aware processing enabled")
        logger.info(f"Metadata judge extraction enabled")
        logger.info(f"Conditional stage execution enabled")
        
        # Run standard processing with our overrides
        result = await super().process_batch(
            limit=limit,
            source_table=source_table,
            only_unprocessed=only_unprocessed,
            extract_pdfs=extract_pdfs,
            force_reprocess=force_reprocess,
            validate_strict=validate_strict
        )
        
        # Add adaptive processing summary
        if result['success']:
            logger.info("\n" + "=" * 60)
            logger.info("ADAPTIVE PROCESSING SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Stages intelligently skipped: {self.stats['stages_skipped']}")
            logger.info(f"Judges extracted from metadata: {self.stats['judges_from_metadata']}")
            logger.info(f"Documents with adaptive quality scores: {self.stats['adaptive_quality_scores']}")
            
            # Show processing breakdown by type
            doc_type_counts = {}
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        CASE 
                            WHEN document_type = 'opinion' AND LENGTH(content) > 5000 THEN 'full_opinion'
                            WHEN document_type IN ('docket', 'recap_docket', 'civil_case') THEN 'metadata_document'
                            WHEN document_type = 'order' AND LENGTH(content) > 1000 THEN 'order'
                            ELSE 'unknown'
                        END as category,
                        COUNT(*) as count
                    FROM (
                        SELECT document_type, content
                        FROM public.court_documents
                        ORDER BY created_at DESC
                        LIMIT %s
                    ) recent_docs
                    GROUP BY category
                """, (limit,))
                
                for row in cursor.fetchall():
                    doc_type_counts[row[0]] = row[1]
            
            logger.info("\nDocument Categories Processed:")
            for category, count in doc_type_counts.items():
                logger.info(f"  {category}: {count}")
        
        return result
    
    def _verify_pipeline_results(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Override to include adaptive processing verification"""
        verification = super()._verify_pipeline_results(documents)
        
        # Add adaptive processing checks
        metadata_docs = sum(1 for doc in documents if doc.get('detected_category') == 'metadata_document')
        skipped_citations = sum(1 for doc in documents if doc.get('citation_extraction_skipped'))
        judges_from_meta = sum(1 for doc in documents if doc.get('judge_source') == 'metadata')
        
        verification['adaptive_processing'] = {
            'metadata_documents': metadata_docs,
            'citation_extraction_skipped': skipped_citations,
            'judges_from_metadata': judges_from_meta,
            'efficiency_gain': f"{(skipped_citations / len(documents) * 100):.1f}%" if documents else "0%"
        }
        
        return verification


async def run_adaptive_pipeline(limit: int = 30):
    """Run the adaptive pipeline"""
    pipeline = AdaptiveElevenStagePipeline()
    
    try:
        results = await pipeline.process_batch(
            limit=limit,
            force_reprocess=True,
            validate_strict=False
        )
        
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'error_type': type(e).__name__
        }


if __name__ == "__main__":
    # Run adaptive pipeline
    asyncio.run(run_adaptive_pipeline(30))