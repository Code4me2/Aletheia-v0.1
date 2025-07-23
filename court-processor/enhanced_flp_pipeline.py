#!/usr/bin/env python3
"""
Enhanced FLP Pipeline with Robust Field Mapping

This module extends the robust pipeline to properly handle:
1. CourtListener API URL formats for courts
2. Different judge field names across document types
3. Integration of all FLP tools
4. PDF handling when available
"""

import re
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class EnhancedFLPFieldMapper:
    """
    Robust field mapping for different CourtListener data formats
    """
    
    # Court URL pattern for CourtListener API
    COURT_URL_PATTERN = re.compile(r'/api/rest/v4/courts/([^/]+)/')
    
    # Judge field mappings by document source
    JUDGE_FIELD_MAPPINGS = {
        'recap_docket': ['assigned_to_str', 'assigned_to', 'referred_to_str', 'referred_to'],
        'recap_document': ['assigned_to_str', 'assigned_to'],
        'opinion': ['author_str', 'author', 'joined_by_str'],
        'cluster': ['judges', 'panel'],
        'search_result': ['assignedTo', 'judge']
    }
    
    # Court field mappings
    COURT_FIELD_MAPPINGS = {
        'recap': ['court', 'court_id', 'court_citation_string'],
        'opinion': ['court', 'court_id'],
        'cluster': ['court', 'court_id', 'court_citation_string'],
        'search': ['court', 'court_id']
    }
    
    @classmethod
    def extract_court_from_metadata(cls, metadata: Dict[str, Any], doc_type: str = 'unknown') -> Optional[str]:
        """
        Extract court ID from various metadata formats
        
        Handles:
        - Direct court IDs (e.g., 'txed')
        - API URLs (e.g., 'https://www.courtlistener.com/api/rest/v4/courts/txed/')
        - Nested court objects
        """
        if not metadata:
            return None
        
        # Get field mappings for document type
        field_mappings = cls.COURT_FIELD_MAPPINGS.get(
            'recap' if doc_type in ['docket', 'recap_document'] else doc_type,
            ['court', 'court_id']
        )
        
        for field in field_mappings:
            court_value = metadata.get(field)
            
            if not court_value:
                continue
            
            # Handle string values
            if isinstance(court_value, str):
                # Check if it's a CourtListener API URL
                url_match = cls.COURT_URL_PATTERN.search(court_value)
                if url_match:
                    court_id = url_match.group(1)
                    logger.info(f"Extracted court ID '{court_id}' from URL: {court_value}")
                    return court_id
                
                # Direct court ID
                if len(court_value) <= 20 and not court_value.startswith('http'):
                    return court_value
            
            # Handle dict values (nested court object)
            elif isinstance(court_value, dict):
                # Try to get ID from nested object
                court_id = court_value.get('id') or court_value.get('court_id')
                if court_id:
                    return court_id
        
        return None
    
    @classmethod
    def extract_judge_from_metadata(cls, metadata: Dict[str, Any], doc_type: str = 'unknown') -> Optional[str]:
        """
        Extract judge name from various metadata formats
        
        Handles different field names across document types
        """
        if not metadata:
            return None
        
        # Determine source type
        source_type = 'recap_docket'
        if doc_type == 'opinion':
            source_type = 'opinion'
        elif 'cluster' in str(metadata):
            source_type = 'cluster'
        elif 'assignedTo' in metadata:
            source_type = 'search_result'
        
        # Get field mappings
        field_mappings = cls.JUDGE_FIELD_MAPPINGS.get(source_type, [])
        
        for field in field_mappings:
            judge_value = metadata.get(field)
            
            if not judge_value:
                continue
            
            # Handle string values
            if isinstance(judge_value, str):
                # Skip URLs
                if judge_value.startswith('http'):
                    continue
                
                # Clean up judge name
                judge_name = judge_value.strip()
                if judge_name and len(judge_name) > 2:
                    logger.info(f"Extracted judge '{judge_name}' from field '{field}'")
                    return judge_name
            
            # Handle list values (panel of judges)
            elif isinstance(judge_value, list) and judge_value:
                # Return first judge
                first_judge = str(judge_value[0]).strip()
                if first_judge and not first_judge.startswith('http'):
                    logger.info(f"Extracted first judge '{first_judge}' from panel in field '{field}'")
                    return first_judge
        
        return None
    
    @classmethod
    def extract_case_info(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract comprehensive case information from metadata
        """
        case_info = {}
        
        # Case name variations
        case_name_fields = ['case_name', 'caseName', 'case_name_full', 'short_description']
        for field in case_name_fields:
            if metadata.get(field):
                case_info['case_name'] = metadata[field]
                break
        
        # Docket number variations
        docket_fields = ['docket_number', 'docketNumber', 'docket']
        for field in docket_fields:
            if metadata.get(field):
                case_info['docket_number'] = metadata[field]
                break
        
        # Date filed variations
        date_fields = ['date_filed', 'dateFiled', 'filed_date']
        for field in date_fields:
            if metadata.get(field):
                case_info['date_filed'] = metadata[field]
                break
        
        # Nature of suit
        case_info['nature_of_suit'] = metadata.get('nature_of_suit') or metadata.get('natureOfSuit')
        
        # Cause
        case_info['cause'] = metadata.get('cause')
        
        # Jurisdiction type
        case_info['jurisdiction_type'] = metadata.get('jurisdiction_type')
        
        return case_info
    
    @classmethod
    def normalize_document_data(cls, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize document data to consistent format
        """
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Detect document type
        doc_type = document.get('document_type', 'unknown')
        
        # Extract normalized fields
        normalized = {
            'original_metadata': metadata,
            'document_type': doc_type,
            'court_id': cls.extract_court_from_metadata(metadata, doc_type),
            'judge_name': cls.extract_judge_from_metadata(metadata, doc_type),
            'case_info': cls.extract_case_info(metadata)
        }
        
        # Add source-specific info
        if 'recap' in metadata.get('source', '').lower():
            normalized['is_recap'] = True
            normalized['recap_id'] = metadata.get('recap_id') or metadata.get('id')
        
        # PDF information
        normalized['has_pdf'] = bool(
            metadata.get('filepath_local') or 
            metadata.get('pdf_url') or
            metadata.get('absolute_url')
        )
        
        return normalized


class EnhancedCourtResolver:
    """
    Enhanced court resolution with CourtListener URL support
    """
    
    @staticmethod
    def resolve_court_enhanced(court_string: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced court resolution that handles URLs and metadata
        """
        # First try the field mapper
        court_id = EnhancedFLPFieldMapper.extract_court_from_metadata(
            metadata, 
            metadata.get('type', 'unknown')
        )
        
        if court_id:
            # Import courts DB only when needed
            from courts_db import courts
            
            # Look up court details
            # courts is a list, not a dict, so we need to search
            court_data = None
            for court in courts:
                if isinstance(court, dict) and court.get('id') == court_id:
                    court_data = court
                    break
            if court_data:
                return {
                    'resolved': True,
                    'court_id': court_id,
                    'court_name': court_data.get('name', ''),
                    'court_citation_string': court_data.get('citation_string', ''),
                    'court_level': court_data.get('level', ''),
                    'court_type': court_data.get('type', ''),
                    'extracted_from': 'metadata_url',
                    'confidence': 'high'
                }
        
        # Fall back to standard resolution
        from courts_db import find_court
        
        court_ids = find_court(court_string)
        if court_ids:
            court_id = court_ids[0]
            # courts is a list, not a dict, so we need to search
            court_data = None
            for court in courts:
                if isinstance(court, dict) and court.get('id') == court_id:
                    court_data = court
                    break
            
            return {
                'resolved': True,
                'court_id': court_id,
                'court_name': court_data.get('name', ''),
                'court_citation_string': court_data.get('citation_string', ''),
                'court_level': court_data.get('level', ''),
                'court_type': court_data.get('type', ''),
                'extracted_from': 'text_search',
                'confidence': 'medium'
            }
        
        return {
            'resolved': False,
            'error': 'Could not resolve court',
            'attempted_string': court_string
        }


def enhance_pipeline_with_flp(pipeline_instance):
    """
    Monkey-patch the existing pipeline with enhanced FLP handling
    
    This function adds enhanced methods to an existing pipeline instance
    """
    
    # Save original methods
    original_enhance_court = pipeline_instance._enhance_court_info_validated
    original_enhance_judge = pipeline_instance._enhance_judge_info_validated
    
    def _enhance_court_info_validated_enhanced(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced court resolution with URL support"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Try enhanced resolution first
        court_result = EnhancedCourtResolver.resolve_court_enhanced(
            document.get('court', ''),
            metadata
        )
        
        if court_result['resolved']:
            return court_result
        
        # Fall back to original method
        return original_enhance_court(document)
    
    def _enhance_judge_info_validated_enhanced(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced judge extraction with field mapping"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Try enhanced extraction first
        doc_type = document.get('detected_type', 'unknown')
        judge_name = EnhancedFLPFieldMapper.extract_judge_from_metadata(metadata, doc_type)
        
        if judge_name:
            # Could integrate judge-pics here if available
            return {
                'enhanced': True,
                'judge_name': judge_name,
                'judge_name_found': judge_name,
                'extracted_from': 'enhanced_metadata',
                'confidence': 'high'
            }
        
        # Fall back to original method
        return original_enhance_judge(document)
    
    # Apply patches
    pipeline_instance._enhance_court_info_validated = _enhance_court_info_validated_enhanced.__get__(
        pipeline_instance, pipeline_instance.__class__
    )
    pipeline_instance._enhance_judge_info_validated = _enhance_judge_info_validated_enhanced.__get__(
        pipeline_instance, pipeline_instance.__class__
    )
    
    logger.info("Pipeline enhanced with robust FLP field mapping")
    
    return pipeline_instance


# Integration with Doctor service (when PDFs are available)
class DoctorIntegration:
    """
    Integration with Doctor service for PDF processing
    """
    
    @staticmethod
    async def extract_text_from_pdf(pdf_url: str, doctor_url: str = "http://doctor:5050") -> Dict[str, Any]:
        """
        Extract text from PDF using Doctor service
        """
        import aiohttp
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{doctor_url}/extract",
                    json={"url": pdf_url}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            'success': True,
                            'text': data.get('content', ''),
                            'page_count': data.get('page_count', 0),
                            'metadata': data.get('metadata', {})
                        }
                    else:
                        return {
                            'success': False,
                            'error': f'Doctor returned {response.status}'
                        }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


if __name__ == "__main__":
    # Test the field mapper
    test_metadata = {
        'court': 'https://www.courtlistener.com/api/rest/v4/courts/txed/',
        'assigned_to_str': 'Judge Rodney Gilstrap'
    }
    
    print("Testing enhanced field mapper:")
    print(f"Court: {EnhancedFLPFieldMapper.extract_court_from_metadata(test_metadata, 'docket')}")
    print(f"Judge: {EnhancedFLPFieldMapper.extract_judge_from_metadata(test_metadata, 'docket')}")