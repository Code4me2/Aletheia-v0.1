"""
Unit tests for validation utilities
"""
import pytest
from pathlib import Path
import tempfile
import os

from enhanced.utils.validation import DocumentValidator, APIRequestValidator, ValidationResult


class TestValidationResult:
    """Test ValidationResult class"""
    
    def test_initialization(self):
        """Test ValidationResult initialization"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.has_errors is False
        assert result.has_warnings is False
    
    def test_add_error(self):
        """Test adding errors"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_error("Test error")
        
        assert result.is_valid is False
        assert result.has_errors is True
        assert "Test error" in result.errors
    
    def test_add_warning(self):
        """Test adding warnings"""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        result.add_warning("Test warning")
        
        assert result.is_valid is True  # Warnings don't affect validity
        assert result.has_warnings is True
        assert "Test warning" in result.warnings


class TestDocumentValidator:
    """Test DocumentValidator class"""
    
    def test_initialization(self):
        """Test validator initialization"""
        validator = DocumentValidator()
        assert validator is not None
        assert hasattr(validator, 'COURT_ID_PATTERN')
        assert hasattr(validator, 'KNOWN_COURTS')
    
    def test_validate_valid_courtlistener_document(self, sample_courtlistener_document):
        """Test validation of valid CourtListener document"""
        validator = DocumentValidator()
        result = validator.validate_courtlistener_document(sample_courtlistener_document)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_courtlistener_document_missing_required_fields(self):
        """Test validation with missing required fields"""
        validator = DocumentValidator()
        invalid_doc = {'case_name': 'Test Case'}  # Missing id and court_id
        
        result = validator.validate_courtlistener_document(invalid_doc)
        
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Should have errors for missing id and court_id
        assert any('id' in error for error in result.errors)
        assert any('court_id' in error for error in result.errors)
    
    def test_validate_courtlistener_document_invalid_court_id(self):
        """Test validation with invalid court ID"""
        validator = DocumentValidator()
        doc = {
            'id': 123,
            'court_id': 'invalid_court_format',
            'case_name': 'Test Case'
        }
        
        result = validator.validate_courtlistener_document(doc)
        
        assert result.is_valid is False
        assert any('Invalid court ID format' in error for error in result.errors)
    
    def test_validate_courtlistener_document_unknown_court(self):
        """Test validation with unknown but valid format court ID"""
        validator = DocumentValidator()
        doc = {
            'id': 123,
            'court_id': 'xyz1',  # Valid format but unknown court
            'case_name': 'Test Case'
        }
        
        result = validator.validate_courtlistener_document(doc)
        
        # Should be valid but have warnings
        assert result.is_valid is True
        assert result.has_warnings is True
        assert any('Unknown court ID' in warning for warning in result.warnings)
    
    def test_validate_courtlistener_document_invalid_date(self):
        """Test validation with invalid date format"""
        validator = DocumentValidator()
        doc = {
            'id': 123,
            'court_id': 'cafc',
            'case_name': 'Test Case',
            'date_filed': 'not-a-date'
        }
        
        result = validator.validate_courtlistener_document(doc)
        
        assert result.is_valid is False
        assert any('Invalid date format' in error for error in result.errors)
    
    def test_validate_processing_request_valid(self):
        """Test validation of valid processing request"""
        validator = DocumentValidator()
        request = {
            'court_id': 'cafc',
            'date_filed_after': '2024-01-01',
            'max_documents': 100
        }
        
        result = validator.validate_processing_request(request)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_processing_request_invalid_max_documents(self):
        """Test validation with invalid max_documents"""
        validator = DocumentValidator()
        request = {
            'court_id': 'cafc',
            'max_documents': -1  # Invalid
        }
        
        result = validator.validate_processing_request(request)
        
        assert result.is_valid is False
        assert any('must be positive' in error for error in result.errors)
    
    def test_validate_processing_request_large_max_documents(self):
        """Test validation with very large max_documents"""
        validator = DocumentValidator()
        request = {
            'court_id': 'cafc',
            'max_documents': 15000  # Very large
        }
        
        result = validator.validate_processing_request(request)
        
        # Should be valid but have warning
        assert result.is_valid is True
        assert result.has_warnings is True
        assert any('very large' in warning for warning in result.warnings)
    
    def test_validate_pdf_file_nonexistent(self):
        """Test PDF validation with nonexistent file"""
        validator = DocumentValidator()
        result = validator.validate_pdf_file("/nonexistent/file.pdf")
        
        assert result.is_valid is False
        assert any('does not exist' in error for error in result.errors)
    
    def test_validate_pdf_file_wrong_extension(self):
        """Test PDF validation with wrong file extension"""
        validator = DocumentValidator()
        
        # Create temporary text file
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as tmp:
            tmp.write(b'test content')
            temp_path = tmp.name
        
        try:
            result = validator.validate_pdf_file(temp_path)
            
            assert result.is_valid is False
            assert any('not a PDF' in error for error in result.errors)
        finally:
            os.unlink(temp_path)
    
    def test_validate_pdf_file_empty(self):
        """Test PDF validation with empty file"""
        validator = DocumentValidator()
        
        # Create empty PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            temp_path = tmp.name  # Empty file
        
        try:
            result = validator.validate_pdf_file(temp_path)
            
            assert result.is_valid is False
            assert any('empty' in error for error in result.errors)
        finally:
            os.unlink(temp_path)
    
    def test_validate_pdf_file_invalid_format(self):
        """Test PDF validation with invalid PDF format"""
        validator = DocumentValidator()
        
        # Create file with wrong magic bytes
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(b'Not a PDF file')
            temp_path = tmp.name
        
        try:
            result = validator.validate_pdf_file(temp_path)
            
            assert result.is_valid is False
            assert any('not appear to be a valid PDF' in error for error in result.errors)
        finally:
            os.unlink(temp_path)
    
    def test_validate_citation_data_valid(self, mock_citations):
        """Test validation of valid citation data"""
        validator = DocumentValidator()
        result = validator.validate_citation_data(mock_citations)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_citation_data_invalid_format(self):
        """Test validation of invalid citation data"""
        validator = DocumentValidator()
        invalid_citations = [
            {'citation_string': ''},  # Empty citation string
            {},  # Missing citation string
            'not a dict'  # Not a dictionary
        ]
        
        result = validator.validate_citation_data(invalid_citations)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_validate_citation_data_too_many(self):
        """Test validation with too many citations"""
        validator = DocumentValidator()
        # Create 150 citations (more than reasonable)
        many_citations = [
            {'citation_string': f'Citation {i}'} for i in range(150)
        ]
        
        result = validator.validate_citation_data(many_citations)
        
        # Should be valid but have warning
        assert result.is_valid is True
        assert result.has_warnings is True
        assert any('unusually high number' in warning for warning in result.warnings)
    
    def test_validate_flp_enhancement_result_valid(self, mock_flp_enhancement_result):
        """Test validation of valid FLP enhancement result"""
        validator = DocumentValidator()
        result = validator.validate_flp_enhancement_result(mock_flp_enhancement_result)
        
        assert result.is_valid is True
    
    def test_validate_flp_enhancement_result_invalid_citations(self):
        """Test validation with invalid citations in FLP result"""
        validator = DocumentValidator()
        invalid_result = {
            'citations': [
                {'citation_string': ''},  # Invalid citation
            ],
            'court_info': {'id': 'cafc'},
            'judge_info': {'name': 'Test Judge'}
        }
        
        result = validator.validate_flp_enhancement_result(invalid_result)
        
        assert result.is_valid is False
        assert len(result.errors) > 0
    
    def test_date_string_validation(self):
        """Test internal date string validation method"""
        validator = DocumentValidator()
        
        # Valid dates
        assert validator._validate_date_string('2024-01-15') is True
        assert validator._validate_date_string('2024-01-15T10:30:00') is True
        assert validator._validate_date_string('2024-01-15T10:30:00Z') is True
        assert validator._validate_date_string('2024-01-15 10:30:00') is True
        
        # Invalid dates
        assert validator._validate_date_string('not-a-date') is False
        assert validator._validate_date_string('2024-13-01') is False  # Invalid month
        assert validator._validate_date_string('') is False
        assert validator._validate_date_string(None) is False


class TestAPIRequestValidator:
    """Test APIRequestValidator class"""
    
    def test_initialization(self):
        """Test API validator initialization"""
        validator = APIRequestValidator()
        assert validator is not None
    
    def test_validate_batch_request_valid(self):
        """Test validation of valid batch request"""
        validator = APIRequestValidator()
        request = {
            'court_id': 'cafc',
            'date_filed_after': '2024-01-01',
            'max_documents': 100
        }
        
        result = validator.validate_batch_request(request)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_single_document_request_valid(self, sample_courtlistener_document):
        """Test validation of valid single document request"""
        validator = APIRequestValidator()
        request = {
            'cl_document': sample_courtlistener_document
        }
        
        result = validator.validate_single_document_request(request)
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validate_single_document_request_missing_document(self):
        """Test validation with missing cl_document"""
        validator = APIRequestValidator()
        request = {}  # Missing cl_document
        
        result = validator.validate_single_document_request(request)
        
        assert result.is_valid is False
        assert any('Missing cl_document' in error for error in result.errors)
    
    def test_validate_single_document_request_invalid_document(self):
        """Test validation with invalid document in request"""
        validator = APIRequestValidator()
        request = {
            'cl_document': {'case_name': 'Test'}  # Missing required fields
        }
        
        result = validator.validate_single_document_request(request)
        
        assert result.is_valid is False
        assert len(result.errors) > 0