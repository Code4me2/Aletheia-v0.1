"""
Data validation utilities for enhanced court document processor

Provides comprehensive validation for documents, API requests, and configuration.
"""
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ValidationResult:
    """Result of validation operation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def add_error(self, message: str):
        """Add validation error"""
        self.errors.append(message)
        self.is_valid = False
    
    def add_warning(self, message: str):
        """Add validation warning"""
        self.warnings.append(message)
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors"""
        return len(self.errors) > 0
    
    @property
    def has_warnings(self) -> bool:
        """Check if validation has warnings"""
        return len(self.warnings) > 0


class DocumentValidator:
    """Validator for court documents and related data"""
    
    # Court ID patterns
    COURT_ID_PATTERN = re.compile(r'^[a-z]{2,6}[0-9]?$')
    
    # Docket number patterns
    DOCKET_PATTERNS = [
        re.compile(r'^\d{1,2}-\d{3,6}$'),  # Standard format: 20-12345
        re.compile(r'^\d{4}-\d{3,6}$'),   # Year format: 2020-12345
        re.compile(r'^[A-Z]+-\d{2,6}$'),  # Letter prefix: CV-12345
    ]
    
    # Known courts for validation
    KNOWN_COURTS = {
        'cafc', 'ca1', 'ca2', 'ca3', 'ca4', 'ca5', 'ca6', 'ca7', 'ca8', 'ca9', 'ca10', 'ca11', 'cadc',
        'txed', 'txnd', 'txsd', 'txwd', 'nysd', 'nynd', 'nyed', 'nywd', 'cand', 'cacd', 'caed', 'casd',
        'deld', 'njd', 'ilnd', 'ilcd', 'ilsd', 'vaed', 'vawd', 'mdmd', 'paed', 'pamd', 'pawd'
    }
    
    def validate_courtlistener_document(self, document: Dict[str, Any]) -> ValidationResult:
        """Validate CourtListener document structure"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Required fields
        required_fields = ['id', 'court_id', 'case_name']
        for field in required_fields:
            if field not in document:
                result.add_error(f"Missing required field: {field}")
            elif not document[field]:
                result.add_error(f"Empty required field: {field}")
        
        # Validate document ID
        if 'id' in document:
            if not isinstance(document['id'], int) or document['id'] <= 0:
                result.add_error("Document ID must be a positive integer")
        
        # Validate court ID
        if 'court_id' in document:
            court_id = document['court_id']
            if not isinstance(court_id, str):
                result.add_error("Court ID must be a string")
            elif not self.COURT_ID_PATTERN.match(court_id):
                result.add_error(f"Invalid court ID format: {court_id}")
            elif court_id not in self.KNOWN_COURTS:
                result.add_warning(f"Unknown court ID: {court_id}")
        
        # Validate case name
        if 'case_name' in document:
            case_name = document['case_name']
            if not isinstance(case_name, str):
                result.add_error("Case name must be a string")
            elif len(case_name.strip()) < 3:
                result.add_error("Case name too short")
            elif len(case_name) > 500:
                result.add_warning("Case name unusually long")
        
        # Validate docket number
        if 'docket_number' in document and document['docket_number']:
            docket = document['docket_number']
            if not isinstance(docket, str):
                result.add_error("Docket number must be a string")
            elif not any(pattern.match(docket) for pattern in self.DOCKET_PATTERNS):
                result.add_warning(f"Unusual docket number format: {docket}")
        
        # Validate date fields
        date_fields = ['date_filed', 'date_created', 'date_modified']
        for field in date_fields:
            if field in document and document[field]:
                if not self._validate_date_string(document[field]):
                    result.add_error(f"Invalid date format in {field}: {document[field]}")
        
        # Validate content fields
        content_fields = ['plain_text', 'html', 'html_lawbox', 'html_columbia']
        has_content = any(document.get(field) for field in content_fields)
        if not has_content and not document.get('pdf_url'):
            result.add_warning("Document has no text content or PDF URL")
        
        # Validate text content
        if 'plain_text' in document and document['plain_text']:
            text = document['plain_text']
            if len(text) < 10:
                result.add_warning("Document text unusually short")
            elif len(text) > 1000000:  # 1MB
                result.add_warning("Document text unusually long")
        
        return result
    
    def validate_processing_request(self, request: Dict[str, Any]) -> ValidationResult:
        """Validate processing request parameters"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate court_id if provided
        if 'court_id' in request and request['court_id']:
            court_id = request['court_id']
            if not isinstance(court_id, str):
                result.add_error("court_id must be a string")
            elif court_id not in self.KNOWN_COURTS:
                result.add_warning(f"Unknown court_id: {court_id}")
        
        # Validate date ranges
        if 'date_filed_after' in request and request['date_filed_after']:
            if not self._validate_date_string(request['date_filed_after']):
                result.add_error("Invalid date_filed_after format")
        
        if 'date_filed_before' in request and request['date_filed_before']:
            if not self._validate_date_string(request['date_filed_before']):
                result.add_error("Invalid date_filed_before format")
        
        # Validate numeric parameters
        if 'max_documents' in request:
            max_docs = request['max_documents']
            if not isinstance(max_docs, int):
                result.add_error("max_documents must be an integer")
            elif max_docs <= 0:
                result.add_error("max_documents must be positive")
            elif max_docs > 10000:
                result.add_warning("max_documents is very large, may cause performance issues")
        
        return result
    
    def validate_pdf_file(self, file_path: Union[str, Path]) -> ValidationResult:
        """Validate PDF file"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        file_path = Path(file_path)
        
        # Check file exists
        if not file_path.exists():
            result.add_error(f"File does not exist: {file_path}")
            return result
        
        # Check file extension
        if file_path.suffix.lower() != '.pdf':
            result.add_error(f"File is not a PDF: {file_path}")
        
        # Check file size
        file_size = file_path.stat().st_size
        if file_size == 0:
            result.add_error("PDF file is empty")
        elif file_size > 100 * 1024 * 1024:  # 100MB
            result.add_warning("PDF file is very large")
        
        # Basic PDF validation (check magic bytes)
        try:
            with open(file_path, 'rb') as f:
                header = f.read(8)
                if not header.startswith(b'%PDF-'):
                    result.add_error("File does not appear to be a valid PDF")
        except Exception as e:
            result.add_error(f"Cannot read PDF file: {str(e)}")
        
        return result
    
    def validate_citation_data(self, citations: List[Dict[str, Any]]) -> ValidationResult:
        """Validate citation extraction results"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if not isinstance(citations, list):
            result.add_error("Citations must be a list")
            return result
        
        for i, citation in enumerate(citations):
            if not isinstance(citation, dict):
                result.add_error(f"Citation {i} must be a dictionary")
                continue
            
            # Check for required citation fields
            if 'citation_string' not in citation:
                result.add_error(f"Citation {i} missing citation_string")
            
            # Validate citation format
            if 'citation_string' in citation:
                cite_str = citation['citation_string']
                if not isinstance(cite_str, str) or len(cite_str.strip()) < 5:
                    result.add_error(f"Citation {i} has invalid citation_string")
        
        # Check for reasonable number of citations
        if len(citations) > 100:
            result.add_warning("Document has unusually high number of citations")
        
        return result
    
    def validate_flp_enhancement_result(self, result: Dict[str, Any]) -> ValidationResult:
        """Validate FLP enhancement results"""
        validation_result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Validate citations
        if 'citations' in result:
            citation_validation = self.validate_citation_data(result['citations'])
            validation_result.errors.extend(citation_validation.errors)
            validation_result.warnings.extend(citation_validation.warnings)
            if not citation_validation.is_valid:
                validation_result.is_valid = False
        
        # Validate court info
        if 'court_info' in result and result['court_info']:
            court_info = result['court_info']
            if not isinstance(court_info, dict):
                validation_result.add_error("court_info must be a dictionary")
            elif 'id' in court_info and court_info['id'] not in self.KNOWN_COURTS:
                validation_result.add_warning(f"Unknown court ID in court_info: {court_info['id']}")
        
        # Validate judge info
        if 'judge_info' in result and result['judge_info']:
            judge_info = result['judge_info']
            if not isinstance(judge_info, dict):
                validation_result.add_error("judge_info must be a dictionary")
        
        return validation_result
    
    def _validate_date_string(self, date_str: str) -> bool:
        """Validate date string format"""
        if not isinstance(date_str, str):
            return False
        
        # Try common date formats
        formats = [
            '%Y-%m-%d',           # 2024-01-15
            '%Y-%m-%dT%H:%M:%S',  # 2024-01-15T10:30:00
            '%Y-%m-%dT%H:%M:%SZ', # 2024-01-15T10:30:00Z
            '%Y-%m-%d %H:%M:%S',  # 2024-01-15 10:30:00
        ]
        
        for fmt in formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        
        return False


class APIRequestValidator:
    """Validator for API requests"""
    
    def validate_batch_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate batch processing request"""
        validator = DocumentValidator()
        return validator.validate_processing_request(data)
    
    def validate_single_document_request(self, data: Dict[str, Any]) -> ValidationResult:
        """Validate single document processing request"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        if 'cl_document' not in data:
            result.add_error("Missing cl_document in request")
            return result
        
        # Validate the document itself
        validator = DocumentValidator()
        doc_validation = validator.validate_courtlistener_document(data['cl_document'])
        result.errors.extend(doc_validation.errors)
        result.warnings.extend(doc_validation.warnings)
        if not doc_validation.is_valid:
            result.is_valid = False
        
        return result