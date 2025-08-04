#!/usr/bin/env python3
"""
Simple adapter to make the existing pipeline more modular
Minimal changes to existing code - just adds smart stage selection
"""

from typing import Dict, Any, List, Optional
import logging
from document_type_detector import DocumentTypeDetector

class PipelineAdapter:
    """Adapts pipeline processing based on document type"""
    
    def __init__(self):
        self.detector = DocumentTypeDetector()
        self.logger = logging.getLogger(__name__)
    
    def should_run_stage(self, stage_name: str, document: Dict[str, Any]) -> bool:
        """Determine if a stage should run for this document"""
        
        # Detect document type
        doc_type, confidence, _ = self.detector.detect_type(document)
        
        # Define which stages run for each document type
        stage_matrix = {
            'opinion': {
                'citation_extraction': True,
                'citation_validation': True,
                'reporter_normalization': True,
                'judge_extraction': True,
                'document_structure': True,
                'keyword_extraction': True,
            },
            'order': {
                'citation_extraction': False,  # Orders rarely have citations
                'citation_validation': False,
                'reporter_normalization': False,
                'judge_extraction': True,
                'document_structure': False,
                'keyword_extraction': True,
            },
            'docket': {
                'citation_extraction': False,  # No citations in metadata
                'citation_validation': False,
                'reporter_normalization': False,
                'judge_extraction': True,  # But from metadata!
                'document_structure': False,  # No structure to analyze
                'keyword_extraction': False,  # Limited value
            },
            'brief': {
                'citation_extraction': True,
                'citation_validation': True,
                'reporter_normalization': True,
                'judge_extraction': False,  # Briefs don't have judges
                'document_structure': True,
                'keyword_extraction': True,
            }
        }
        
        # Default to running all stages if unknown
        stages = stage_matrix.get(doc_type, {})
        return stages.get(stage_name, True)
    
    def get_judge_extraction_method(self, document: Dict[str, Any]) -> str:
        """Determine how to extract judge for this document"""
        
        doc_type, _, _ = self.detector.detect_type(document)
        strategy = self.detector.get_processing_strategy(doc_type)
        return strategy['judge_extraction']
    
    def adapt_quality_metrics(self, document: Dict[str, Any], raw_metrics: Dict[str, float]) -> Dict[str, float]:
        """Adjust quality metrics based on document type"""
        
        doc_type, confidence, characteristics = self.detector.detect_type(document)
        
        if doc_type == 'docket':
            # Dockets shouldn't be penalized for lack of citations
            adapted_metrics = {
                'completeness': self._calculate_docket_completeness(document, raw_metrics),
                'quality': self._calculate_docket_quality(document, raw_metrics),
                'confidence': confidence
            }
        elif doc_type == 'order':
            # Orders have different expectations
            adapted_metrics = {
                'completeness': self._calculate_order_completeness(document, raw_metrics),
                'quality': raw_metrics.get('quality', 50.0),
                'confidence': confidence
            }
        else:
            # Opinions and others use standard metrics
            adapted_metrics = {
                'completeness': raw_metrics.get('completeness', 0.0),
                'quality': raw_metrics.get('quality', 0.0),
                'confidence': confidence
            }
        
        return adapted_metrics
    
    def _calculate_docket_completeness(self, document: Dict[str, Any], raw_metrics: Dict[str, float]) -> float:
        """Calculate completeness for docket documents"""
        score = 0.0
        
        # Check for essential docket fields
        if raw_metrics.get('court_resolved'):
            score += 40.0
        if raw_metrics.get('judge_found'):
            score += 30.0
        if document.get('metadata', {}).get('parties'):
            score += 20.0
        if document.get('metadata', {}).get('date_filed'):
            score += 10.0
            
        return min(100.0, score)
    
    def _calculate_docket_quality(self, document: Dict[str, Any], raw_metrics: Dict[str, float]) -> float:
        """Calculate quality for docket documents"""
        # For dockets, quality is about metadata completeness
        metadata = document.get('metadata', {})
        
        important_fields = [
            'court_id', 'assigned_to', 'date_filed', 
            'case_name', 'docket_number', 'nature_of_suit'
        ]
        
        present_fields = sum(1 for field in important_fields if metadata.get(field))
        return (present_fields / len(important_fields)) * 100.0
    
    def _calculate_order_completeness(self, document: Dict[str, Any], raw_metrics: Dict[str, float]) -> float:
        """Calculate completeness for order documents"""
        score = 0.0
        
        if raw_metrics.get('court_resolved'):
            score += 35.0
        if raw_metrics.get('judge_found'):
            score += 35.0
        if raw_metrics.get('order_type_identified'):  # Would need to add this
            score += 20.0
        if len(document.get('content', '')) > 500:
            score += 10.0
            
        return min(100.0, score)

# Integration example for existing pipeline
def integrate_with_pipeline(pipeline_instance, adapter: PipelineAdapter):
    """
    Monkey-patch or wrap existing pipeline methods
    This is a non-invasive way to add adaptive behavior
    """
    
    # Save original methods
    original_stage3 = pipeline_instance.stage_3_citation_extraction
    original_stage6 = pipeline_instance.stage_6_judge_enhancement
    
    # Create wrapped versions
    async def adaptive_stage3(document):
        if adapter.should_run_stage('citation_extraction', document):
            return await original_stage3(document)
        else:
            # Skip but return valid result
            return {
                'citations_extracted': [],
                'skipped': True,
                'reason': 'Not applicable for document type'
            }
    
    async def adaptive_stage6(document):
        method = adapter.get_judge_extraction_method(document)
        
        if method == 'metadata_only':
            # Extract from metadata instead of content
            metadata = document.get('metadata', {})
            judge = metadata.get('assigned_to') or metadata.get('judge')
            
            if judge:
                return {
                    'judge_found': True,
                    'judge_name': judge,
                    'source': 'metadata',
                    'enhanced': True
                }
        
        # Otherwise use original method
        return await original_stage6(document)
    
    # Replace methods
    pipeline_instance.stage_3_citation_extraction = adaptive_stage3
    pipeline_instance.stage_6_judge_enhancement = adaptive_stage6
    
    return pipeline_instance


if __name__ == "__main__":
    # Example of how to use
    adapter = PipelineAdapter()
    
    # Test document
    docket = {
        'document_type': 'docket',
        'content': 'Case: Smith v. Jones\nDocket: 2:24-cv-00123',
        'metadata': {'assigned_to': 'Judge Smith'}
    }
    
    print(f"Should extract citations from docket: {adapter.should_run_stage('citation_extraction', docket)}")
    print(f"Judge extraction method: {adapter.get_judge_extraction_method(docket)}")
    
    # Test metrics adaptation
    raw_metrics = {
        'court_resolved': True,
        'judge_found': True,
        'citations_found': False  # This would normally hurt the score
    }
    
    adapted = adapter.adapt_quality_metrics(docket, raw_metrics)
    print(f"Adapted metrics for docket: {adapted}")