#!/usr/bin/env python3
"""
Modular Pipeline Design - Document Type Specific Processing
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class DocumentProcessor(ABC):
    """Base class for document-specific processors"""
    
    @abstractmethod
    def can_process(self, document: Dict[str, Any]) -> bool:
        """Check if this processor can handle the document"""
        pass
    
    @abstractmethod
    def get_stages(self) -> List[str]:
        """Return list of stages applicable to this document type"""
        pass
    
    @abstractmethod
    def extract_judge(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract judge information based on document type"""
        pass


class OpinionProcessor(DocumentProcessor):
    """Process full-text opinion documents"""
    
    def can_process(self, document: Dict[str, Any]) -> bool:
        return (document.get('document_type') == 'opinion' and 
                len(document.get('content', '')) > 5000)
    
    def get_stages(self) -> List[str]:
        # All stages make sense for opinions
        return [
            'court_resolution',
            'citation_extraction',  # ✅ Lots of citations
            'citation_validation', 
            'reporter_normalization',
            'judge_extraction',     # ✅ Extract from text
            'document_structure',   # ✅ Rich structure
            'keyword_extraction',   # ✅ Legal concepts
            'metadata_assembly',
            'storage',
            'indexing',
            'verification'
        ]
    
    def extract_judge(self, document: Dict[str, Any]) -> Dict[str, Any]:
        # Extract from document text patterns
        content = document.get('content', '')
        # Look for "Before:", "Judge:", signature lines, etc.
        return self._extract_from_content(content)


class DocketProcessor(DocumentProcessor):
    """Process docket metadata documents"""
    
    def can_process(self, document: Dict[str, Any]) -> bool:
        return document.get('document_type') in ['docket', 'recap_docket']
    
    def get_stages(self) -> List[str]:
        # Skip text-heavy stages
        return [
            'court_resolution',
            # 'citation_extraction',  # ❌ No citations in metadata
            # 'citation_validation',  # ❌ Skip
            # 'reporter_normalization', # ❌ Skip
            'judge_extraction',       # ✅ From metadata.assigned_to
            # 'document_structure',   # ❌ No structure to analyze
            'keyword_extraction',     # ⚠️ Limited value
            'metadata_assembly',
            'storage',
            'indexing',
            'verification'
        ]
    
    def extract_judge(self, document: Dict[str, Any]) -> Dict[str, Any]:
        # Extract from metadata fields
        metadata = document.get('metadata', {})
        judge_name = metadata.get('assigned_to') or metadata.get('assigned_to_str')
        
        if judge_name:
            # Clean up URLs and extract name
            if 'courtlistener.com' in str(judge_name):
                judge_name = judge_name.split('/')[-2].replace('-', ' ').title()
            
            return {
                'enhanced': True,
                'full_name': judge_name,
                'source': 'metadata.assigned_to'
            }
        return {'enhanced': False}


class CivilCaseProcessor(DocumentProcessor):
    """Process minimal civil case documents"""
    
    def can_process(self, document: Dict[str, Any]) -> bool:
        return (document.get('document_type') == 'civil_case' and
                len(document.get('content', '')) < 1000)
    
    def get_stages(self) -> List[str]:
        # Very limited processing
        return [
            'court_resolution',
            'judge_extraction',      # ✅ From metadata
            'metadata_assembly',
            'storage',
            'verification'
        ]
    
    def extract_judge(self, document: Dict[str, Any]) -> Dict[str, Any]:
        # Similar to docket processor
        return DocketProcessor().extract_judge(document)


class ModularPipeline:
    """Main pipeline that delegates to appropriate processors"""
    
    def __init__(self):
        self.processors = [
            OpinionProcessor(),
            DocketProcessor(),
            CivilCaseProcessor()
        ]
    
    def process_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Process document with appropriate processor"""
        
        # Ensure cl_id exists
        if not document.get('cl_id'):
            document['cl_id'] = document.get('id', '')
            
        # Find appropriate processor
        for processor in self.processors:
            if processor.can_process(document):
                stages = processor.get_stages()
                
                # Run only applicable stages
                results = {}
                for stage in stages:
                    if stage == 'judge_extraction':
                        results['judge'] = processor.extract_judge(document)
                    else:
                        # Run other stages
                        results[stage] = self._run_stage(stage, document)
                
                return results
        
        # Default processing if no processor matches
        return self._default_processing(document)
    
    def get_quality_metrics(self, document: Dict[str, Any], results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate quality metrics based on document type"""
        
        if document.get('document_type') == 'opinion':
            # Full metrics for opinions
            return {
                'completeness': self._calculate_opinion_completeness(results),
                'quality': self._calculate_opinion_quality(results)
            }
        elif document.get('document_type') in ['docket', 'recap_docket']:
            # Adjusted metrics for dockets
            return {
                'completeness': self._calculate_docket_completeness(results),
                'quality': self._calculate_docket_quality(results)
            }
        else:
            # Minimal metrics
            return {
                'completeness': 50.0 if results.get('court_resolved') else 0.0,
                'quality': 50.0
            }


# Example usage
if __name__ == "__main__":
    pipeline = ModularPipeline()
    
    # Opinion document
    opinion = {
        'id': '123',
        'document_type': 'opinion',
        'content': 'Full legal opinion text...' * 1000,
        'metadata': {}
    }
    
    # Docket document
    docket = {
        'id': '456',
        'document_type': 'docket',
        'content': 'Case: Smith v. Jones...',
        'metadata': {
            'assigned_to': 'https://www.courtlistener.com/api/rest/v4/people/rodney-gilstrap/'
        }
    }
    
    # Process with appropriate strategies
    opinion_results = pipeline.process_document(opinion)
    docket_results = pipeline.process_document(docket)
    
    print(f"Opinion stages: {len(opinion_results)} stages run")
    print(f"Docket stages: {len(docket_results)} stages run")
    print(f"Docket judge: {docket_results.get('judge', {}).get('full_name', 'Not found')}")