#!/usr/bin/env python3
"""
Comprehensive Field Mapper
Maps all variations of judge and court fields across different document types
"""

import re
import json
from typing import Dict, Any, Optional, List, Tuple
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ComprehensiveFieldMapper:
    """
    Flexible field mapper that captures all available information
    without losing data due to field name variations
    """
    
    # Judge field mappings by document type
    JUDGE_FIELD_HIERARCHY = {
        'docket': [
            'assigned_to',           # Primary judge assignment
            'assigned_to_str',       # String version
            'assigned_to_id',        # Judge ID
            'referred_to',           # Referred judge
            'referred_to_str',       # String version
            'federal_dn_judge_initials_assigned',
            'federal_dn_judge_initials_referred',
            'judge',                 # Generic field
            'judge_name',           # Generic name field
        ],
        'opinion': [
            'author_str',           # Primary author string
            'author',               # Author object/string
            'author_id',            # Author ID
            'joined_by_str',        # Additional judges
            'joined_by',            # Join list
            'per_curiam',           # Per curiam indicator
        ],
        'cluster': [
            'judges',               # Panel of judges
            'panel',                # Panel list
            'panel_str',            # Panel string
        ],
        'search_result': [
            'assignedTo',           # Camel case in search
            'referredTo',           # Camel case referred
            'judge',                # Direct judge field
        ],
        'generic': [
            'judge_name',
            'judge',
            'magistrate_judge',
            'presiding_judge',
        ]
    }
    
    # Court field mappings
    COURT_FIELD_HIERARCHY = {
        'direct': [
            'court',                # Most common field
            'court_id',             # Alternative ID field
            'court_citation_string',
            'court_exact',
            'court_citation',
        ],
        'nested': [
            'court_standardized',   # Object with id, name
            'court_info',           # Generic info object
        ],
        'url_patterns': [
            'absolute_url',         # Contains court ID in path
            'resource_uri',         # API URI with court
            'court_url',            # Direct court URL
            'cluster',              # May be URL string
        ]
    }
    
    @classmethod
    def extract_all_judge_info(cls, document: Dict[str, Any], doc_type: str = None) -> Dict[str, Any]:
        """
        Extract all judge information from document, preserving original fields
        
        Returns:
            Dict with:
            - primary_judge: The main judge name/info
            - all_judges: List of all judges found
            - original_fields: Dict of all original judge-related fields
            - extraction_method: How the judge was found
        """
        result = {
            'primary_judge': None,
            'all_judges': [],
            'original_fields': {},
            'extraction_method': None,
            'judge_ids': []
        }
        
        # Auto-detect document type if not provided
        if not doc_type:
            doc_type = cls._detect_document_type(document)
        
        # Get metadata if it exists
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Check all possible fields based on document type
        field_lists = []
        if doc_type in cls.JUDGE_FIELD_HIERARCHY:
            field_lists.append(cls.JUDGE_FIELD_HIERARCHY[doc_type])
        field_lists.append(cls.JUDGE_FIELD_HIERARCHY['generic'])
        
        # Search in both document root and metadata
        for fields in field_lists:
            for field in fields:
                # Check document root
                if field in document and document[field]:
                    result['original_fields'][field] = document[field]
                    judge_value = document[field]
                    
                    # Extract judge name based on value type
                    judge_name = cls._extract_judge_name(judge_value)
                    if judge_name and judge_name not in result['all_judges']:
                        result['all_judges'].append(judge_name)
                        if not result['primary_judge']:
                            result['primary_judge'] = judge_name
                            result['extraction_method'] = f'document.{field}'
                
                # Check metadata
                if field in metadata and metadata[field]:
                    result['original_fields'][f'metadata.{field}'] = metadata[field]
                    judge_value = metadata[field]
                    
                    judge_name = cls._extract_judge_name(judge_value)
                    if judge_name and judge_name not in result['all_judges']:
                        result['all_judges'].append(judge_name)
                        if not result['primary_judge']:
                            result['primary_judge'] = judge_name
                            result['extraction_method'] = f'metadata.{field}'
        
        # Extract from cluster URL if available
        cluster = metadata.get('cluster') or document.get('cluster')
        if cluster and isinstance(cluster, str) and 'http' in cluster:
            # Try to fetch cluster data or parse URL
            result['original_fields']['cluster_url'] = cluster
        
        return result
    
    @classmethod
    def extract_all_court_info(cls, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract all court information from document, preserving original fields
        
        Returns:
            Dict with:
            - court_id: The standardized court ID
            - court_name: Full court name
            - all_court_fields: All court-related fields found
            - extraction_method: How the court was identified
        """
        result = {
            'court_id': None,
            'court_name': None,
            'court_citation': None,
            'all_court_fields': {},
            'extraction_method': None
        }
        
        # Get metadata
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Check direct fields
        for field in cls.COURT_FIELD_HIERARCHY['direct']:
            # Check document root
            if field in document and document[field]:
                result['all_court_fields'][field] = document[field]
                if not result['court_id']:
                    result['court_id'] = document[field]
                    result['extraction_method'] = f'document.{field}'
            
            # Check metadata
            if field in metadata and metadata[field]:
                result['all_court_fields'][f'metadata.{field}'] = metadata[field]
                if not result['court_id']:
                    result['court_id'] = metadata[field]
                    result['extraction_method'] = f'metadata.{field}'
        
        # Check nested objects
        for field in cls.COURT_FIELD_HIERARCHY['nested']:
            if field in metadata and isinstance(metadata[field], dict):
                result['all_court_fields'][f'metadata.{field}'] = metadata[field]
                if not result['court_id'] and 'id' in metadata[field]:
                    result['court_id'] = metadata[field]['id']
                    result['court_name'] = metadata[field].get('name')
                    result['extraction_method'] = f'metadata.{field}.id'
        
        # Extract from URLs
        for field in cls.COURT_FIELD_HIERARCHY['url_patterns']:
            url_value = metadata.get(field) or document.get(field)
            if url_value and isinstance(url_value, str) and 'court' in url_value:
                court_id = cls._extract_court_from_url(url_value)
                if court_id:
                    result['all_court_fields'][f'{field}_extracted'] = court_id
                    if not result['court_id']:
                        result['court_id'] = court_id
                        result['extraction_method'] = f'{field}_url_parse'
        
        # Store court name if found
        if 'court_name' in metadata:
            result['court_name'] = metadata['court_name']
        elif 'court_name' in document:
            result['court_name'] = document['court_name']
        
        return result
    
    @classmethod
    def create_unified_metadata(cls, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a unified metadata structure that preserves all original fields
        while providing standardized access to key information
        """
        # Detect document type
        doc_type = cls._detect_document_type(document)
        
        # Extract all information
        judge_info = cls.extract_all_judge_info(document, doc_type)
        court_info = cls.extract_all_court_info(document)
        
        # Get original metadata
        original_metadata = document.get('metadata', {})
        if isinstance(original_metadata, str):
            try:
                original_metadata = json.loads(original_metadata)
            except:
                original_metadata = {}
        
        # Create unified structure
        unified = {
            'document_type': doc_type,
            'extracted_data': {
                'judge': judge_info,
                'court': court_info
            },
            'original_metadata': original_metadata,
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        # Add top-level standardized fields for easy access
        if judge_info['primary_judge']:
            unified['judge_name'] = judge_info['primary_judge']
        if court_info['court_id']:
            unified['court_id'] = court_info['court_id']
        if court_info['court_name']:
            unified['court_name'] = court_info['court_name']
        
        return unified
    
    @staticmethod
    def _detect_document_type(document: Dict[str, Any]) -> str:
        """Detect document type from various indicators"""
        # Check explicit type
        doc_type = document.get('document_type', '').lower()
        if 'opinion' in doc_type:
            return 'opinion'
        elif 'docket' in doc_type:
            return 'docket'
        
        # Check metadata
        metadata = document.get('metadata', {})
        if isinstance(metadata, dict):
            if 'docket_id' in metadata or 'assigned_to' in metadata:
                return 'docket'
            elif 'cluster' in metadata or 'author_str' in metadata:
                return 'opinion'
        
        # Check case number pattern
        case_number = document.get('case_number', '')
        if case_number.startswith('OPINION-'):
            return 'opinion'
        elif ':' in case_number and '-cv-' in case_number:
            return 'docket'
        
        return 'unknown'
    
    @staticmethod
    def _extract_judge_name(value: Any) -> Optional[str]:
        """Extract judge name from various value types"""
        if not value:
            return None
        
        if isinstance(value, str):
            # Clean up the string
            name = value.strip()
            # Skip if it's a URL or ID
            if name and not name.startswith('http') and not name.isdigit():
                return name
        elif isinstance(value, dict):
            # Try common name fields
            for field in ['name', 'full_name', 'name_full', 'display_name']:
                if field in value and value[field]:
                    return str(value[field]).strip()
        elif isinstance(value, list) and value:
            # Return first non-empty item
            for item in value:
                name = ComprehensiveFieldMapper._extract_judge_name(item)
                if name:
                    return name
        
        return None
    
    @staticmethod
    def _extract_court_from_url(url: str) -> Optional[str]:
        """Extract court ID from various URL patterns"""
        # Pattern: /api/rest/v4/courts/{court_id}/
        match = re.search(r'/courts/([a-z0-9]+)/', url)
        if match:
            return match.group(1)
        
        # Pattern: /court/{court_id}/
        match = re.search(r'/court/([a-z0-9]+)/', url)
        if match:
            return match.group(1)
        
        return None


# Test the mapper
if __name__ == "__main__":
    from datetime import datetime
    
    # Test with docket data
    test_docket = {
        'case_number': '1:25-cv-08099',
        'document_type': 'docket',
        'metadata': {
            'court': 'ilnd',
            'court_name': 'Northern District of Illinois',
            'assigned_to': 'Franklin U. Valderrama',
            'court_standardized': {
                'id': 'ilnd',
                'name': 'District Court, N.D. Illinois'
            }
        }
    }
    
    print("Testing Comprehensive Field Mapper")
    print("=" * 80)
    
    print("\nDocket test:")
    judge_info = ComprehensiveFieldMapper.extract_all_judge_info(test_docket)
    court_info = ComprehensiveFieldMapper.extract_all_court_info(test_docket)
    
    print(f"Judge found: {judge_info['primary_judge']}")
    print(f"  Method: {judge_info['extraction_method']}")
    print(f"  All fields: {list(judge_info['original_fields'].keys())}")
    
    print(f"\nCourt found: {court_info['court_id']}")
    print(f"  Name: {court_info['court_name']}")
    print(f"  Method: {court_info['extraction_method']}")
    print(f"  All fields: {list(court_info['all_court_fields'].keys())}")
    
    # Test with opinion data
    test_opinion = {
        'case_number': 'OPINION-txed-12345',
        'document_type': 'opinion',
        'cluster': 'https://www.courtlistener.com/api/rest/v4/clusters/12345/',
        'metadata': {
            'author_str': 'RODNEY GILSTRAP',
            'absolute_url': 'https://www.courtlistener.com/api/rest/v4/courts/txed/opinions/12345/'
        }
    }
    
    print("\n\nOpinion test:")
    judge_info = ComprehensiveFieldMapper.extract_all_judge_info(test_opinion)
    court_info = ComprehensiveFieldMapper.extract_all_court_info(test_opinion)
    
    print(f"Judge found: {judge_info['primary_judge']}")
    print(f"  Method: {judge_info['extraction_method']}")
    
    print(f"\nCourt found: {court_info['court_id']}")
    print(f"  Method: {court_info['extraction_method']}")
    
    # Test unified metadata
    print("\n\nUnified metadata:")
    unified = ComprehensiveFieldMapper.create_unified_metadata(test_docket)
    print(json.dumps(unified, indent=2))