#!/usr/bin/env python3
"""
Simple Document Type Detection for Court Documents
Based on content characteristics, not just metadata labels
"""

from typing import Dict, Any, List, Tuple
import re
import json

class DocumentTypeDetector:
    """Detect actual document type based on content and structure"""
    
    def __init__(self):
        # Define characteristics of each document type
        self.patterns = {
            'opinion': {
                'min_length': 5000,
                'required_patterns': [
                    r'(opinion|judgment|decision)',
                    r'(court|district|circuit)',
                    r'(judge|justice)'
                ],
                'section_markers': [
                    r'I+\.\s+[A-Z]',  # I. BACKGROUND
                    r'CONCLUSION',
                    r'DISCUSSION',
                    r'ANALYSIS'
                ],
                'citation_threshold': 5  # Expect at least 5 citations
            },
            'order': {
                'min_length': 1000,
                'required_patterns': [
                    r'(ORDER|ORDERED)',
                    r'(IT IS HEREBY|IT IS SO)'
                ],
                'section_markers': [],
                'citation_threshold': 1
            },
            'docket': {
                'min_length': 0,
                'required_patterns': [
                    r'(docket|case number)',
                    r'(filed|entered)'
                ],
                'metadata_fields': ['docket_id', 'recap_documents', 'assigned_to'],
                'citation_threshold': 0
            },
            'brief': {
                'min_length': 3000,
                'required_patterns': [
                    r'(plaintiff|defendant|appellant|appellee)',
                    r'(motion|brief|memorandum)'
                ],
                'section_markers': [
                    r'ARGUMENT',
                    r'STATEMENT OF THE CASE'
                ],
                'citation_threshold': 10
            }
        }
    
    def detect_type(self, document: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Detect document type based on content analysis
        
        Returns:
            - detected_type: Best guess at document type
            - confidence: 0-1 confidence score
            - characteristics: What was found
        """
        content = document.get('content', '')
        metadata = document.get('metadata', {})
        
        # Parse metadata if string
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Track scores for each type
        scores = {}
        characteristics = {
            'content_length': len(content),
            'has_citations': False,
            'citation_count': 0,
            'has_structure': False,
            'metadata_type': document.get('document_type', 'unknown')
        }
        
        # Check each document type
        for doc_type, criteria in self.patterns.items():
            score = 0.0
            max_score = 0.0
            
            # Length check
            max_score += 1
            if len(content) >= criteria['min_length']:
                score += 1
            elif criteria['min_length'] > 0:
                # Partial credit based on how close
                score += len(content) / criteria['min_length']
            
            # Pattern matching
            if 'required_patterns' in criteria:
                for pattern in criteria['required_patterns']:
                    max_score += 1
                    if re.search(pattern, content, re.IGNORECASE):
                        score += 1
            
            # Section markers (indicates structured document)
            if 'section_markers' in criteria and criteria['section_markers']:
                max_score += 1
                sections_found = sum(1 for marker in criteria['section_markers'] 
                                   if re.search(marker, content))
                if sections_found > 0:
                    score += min(1.0, sections_found / len(criteria['section_markers']))
                    characteristics['has_structure'] = True
            
            # Citation check
            if criteria['citation_threshold'] > 0:
                max_score += 1
                # Simple citation pattern
                citations = re.findall(r'\d+\s+[A-Z][a-z]+\.?\s*\d+d?\s+\d+', content)
                characteristics['citation_count'] = len(citations)
                characteristics['has_citations'] = len(citations) > 0
                
                if len(citations) >= criteria['citation_threshold']:
                    score += 1
                elif criteria['citation_threshold'] > 0:
                    score += len(citations) / criteria['citation_threshold']
            
            # Metadata field check (for dockets)
            if 'metadata_fields' in criteria:
                max_score += 1
                fields_present = sum(1 for field in criteria['metadata_fields'] 
                                   if metadata.get(field))
                if fields_present > 0:
                    score += fields_present / len(criteria['metadata_fields'])
            
            # Calculate confidence
            confidence = score / max_score if max_score > 0 else 0
            scores[doc_type] = confidence
        
        # Find best match
        best_type = max(scores, key=scores.get)
        best_confidence = scores[best_type]
        
        # If confidence is too low, check metadata hint
        if best_confidence < 0.3 and document.get('document_type'):
            best_type = document['document_type']
            best_confidence = 0.3  # Low confidence fallback
        
        return best_type, best_confidence, characteristics
    
    def get_processing_strategy(self, detected_type: str) -> Dict[str, Any]:
        """Get recommended processing strategy for document type"""
        
        strategies = {
            'opinion': {
                'stages': ['all'],  # Run all pipeline stages
                'judge_extraction': 'content',
                'quality_threshold': 0.7,
                'index_priority': 'high'
            },
            'order': {
                'stages': ['court', 'judge', 'keyword', 'storage'],
                'judge_extraction': 'content_and_metadata',
                'quality_threshold': 0.5,
                'index_priority': 'medium'
            },
            'docket': {
                'stages': ['court', 'judge_metadata', 'party_extraction', 'storage'],
                'judge_extraction': 'metadata_only',
                'quality_threshold': 0.4,
                'index_priority': 'low'
            },
            'brief': {
                'stages': ['court', 'citation', 'party', 'argument_extraction', 'storage'],
                'judge_extraction': 'metadata',
                'quality_threshold': 0.6,
                'index_priority': 'medium'
            },
            'unknown': {
                'stages': ['court', 'basic_extraction', 'storage'],
                'judge_extraction': 'metadata',
                'quality_threshold': 0.3,
                'index_priority': 'low'
            }
        }
        
        return strategies.get(detected_type, strategies['unknown'])


# Example usage
if __name__ == "__main__":
    detector = DocumentTypeDetector()
    
    # Test with different document types
    test_docs = [
        {
            'content': 'UNITED STATES DISTRICT COURT\n\nOPINION AND ORDER\n\n' + 
                      'This matter comes before the court...' * 1000,
            'document_type': 'opinion'
        },
        {
            'content': 'Case: Smith v. Jones\nDocket Number: 2:24-cv-00123\nFiled: 2024-01-01',
            'document_type': 'docket',
            'metadata': {'assigned_to': 'Judge Smith', 'recap_documents': []}
        },
        {
            'content': 'IT IS HEREBY ORDERED that the motion is GRANTED.',
            'document_type': 'order'
        }
    ]
    
    for doc in test_docs:
        doc_type, confidence, chars = detector.detect_type(doc)
        strategy = detector.get_processing_strategy(doc_type)
        
        print(f"\nDocument: {doc.get('document_type', 'unknown')}")
        print(f"Detected: {doc_type} (confidence: {confidence:.2f})")
        print(f"Characteristics: {chars}")
        print(f"Strategy: {strategy['stages']}")
        print(f"Judge extraction: {strategy['judge_extraction']}")