"""
Validation framework for the court processor pipeline

Provides systematic validation for all data types and structures used in the pipeline.
Each validator returns a tuple of (is_valid, error_message, cleaned_data)
"""

import re
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from courts_db import courts
from reporters_db import REPORTERS

# Create lookup sets for performance
VALID_COURT_IDS = {court['id'] for court in courts if isinstance(court, dict)}
VALID_REPORTERS = set(REPORTERS.keys())


class ValidationResult:
    """Structured validation result"""
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None, cleaned_data: Any = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.cleaned_data = cleaned_data
    
    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        self.warnings.append(warning)
    
    def to_dict(self):
        return {
            'is_valid': self.is_valid,
            'errors': self.errors,
            'warnings': self.warnings,
            'has_warnings': len(self.warnings) > 0
        }


class DocumentValidator:
    """Validates document structure and content"""
    
    @staticmethod
    def validate_document(doc: Dict[str, Any]) -> ValidationResult:
        """Validate a document has required fields and structure"""
        result = ValidationResult(is_valid=True, cleaned_data=doc.copy())
        
        # Required fields
        if not doc.get('id'):
            result.add_error("Document missing required 'id' field")
        
        if not doc.get('content'):
            result.add_error("Document missing required 'content' field")
        elif not isinstance(doc['content'], str):
            result.add_error(f"Document content must be string, got {type(doc['content']).__name__}")
        elif len(doc['content'].strip()) < 100:
            result.add_warning("Document content is very short (< 100 characters)")
        
        # Metadata validation
        metadata = doc.get('metadata', {})
        if metadata and not isinstance(metadata, dict):
            result.add_error(f"Document metadata must be dict, got {type(metadata).__name__}")
            result.cleaned_data['metadata'] = {}
        
        # Case number format validation (if present)
        case_number = doc.get('case_number')
        if case_number:
            if not isinstance(case_number, str):
                result.add_warning(f"Case number should be string, got {type(case_number).__name__}")
            elif not re.match(r'^[\w:,-]+$', case_number):
                result.add_warning(f"Case number has unusual format: {case_number}")
        
        return result


class CourtValidator:
    """Validates court information"""
    
    @staticmethod
    def validate_court_id(court_id: str) -> ValidationResult:
        """Validate a court ID exists in courts database"""
        result = ValidationResult(is_valid=True, cleaned_data=court_id)
        
        if not court_id:
            result.add_error("Court ID is empty")
            return result
        
        if not isinstance(court_id, str):
            result.add_error(f"Court ID must be string, got {type(court_id).__name__}")
            return result
        
        if court_id not in VALID_COURT_IDS:
            result.add_error(f"Court ID '{court_id}' not found in courts database")
            # Suggest similar courts
            similar = [cid for cid in VALID_COURT_IDS if cid.startswith(court_id[:2])]
            if similar:
                result.add_warning(f"Similar court IDs: {', '.join(similar[:3])}")
        
        return result
    
    @staticmethod
    def validate_court_enhancement(enhancement: Dict[str, Any]) -> ValidationResult:
        """Validate court enhancement result"""
        result = ValidationResult(is_valid=True, cleaned_data=enhancement)
        
        if not isinstance(enhancement, dict):
            result.add_error("Court enhancement must be a dictionary")
            return result
        
        if enhancement.get('resolved'):
            # Validate resolved court
            court_id = enhancement.get('court_id')
            if not court_id:
                result.add_error("Resolved court missing court_id")
            else:
                court_validation = CourtValidator.validate_court_id(court_id)
                if not court_validation.is_valid:
                    result.errors.extend(court_validation.errors)
        else:
            # Validate unresolved court has reason
            if not enhancement.get('reason'):
                result.add_warning("Unresolved court should include reason")
        
        return result


class CitationValidator:
    """Validates legal citations"""
    
    @staticmethod
    def validate_citation(citation: Dict[str, Any]) -> ValidationResult:
        """Validate a single citation"""
        result = ValidationResult(is_valid=True, cleaned_data=citation)
        
        # Check required fields
        if not citation.get('text'):
            result.add_error("Citation missing 'text' field")
        
        # Validate reporter if present
        reporter = citation.get('reporter')
        if reporter and reporter not in VALID_REPORTERS:
            # Check if it's a valid variation
            base_reporters = ['F.', 'F. Supp.', 'U.S.', 'S. Ct.']
            if not any(reporter.startswith(base) for base in base_reporters):
                result.add_warning(f"Unknown reporter: {reporter}")
        
        # Validate volume and page numbers
        volume = citation.get('volume')
        if volume:
            try:
                vol_num = int(volume)
                if vol_num < 1 or vol_num > 9999:
                    result.add_warning(f"Unusual volume number: {volume}")
            except (ValueError, TypeError):
                result.add_error(f"Invalid volume number: {volume}")
        
        page = citation.get('page')
        if page:
            try:
                page_num = int(page)
                if page_num < 1 or page_num > 99999:
                    result.add_warning(f"Unusual page number: {page}")
            except (ValueError, TypeError):
                result.add_error(f"Invalid page number: {page}")
        
        return result
    
    @staticmethod
    def validate_citations_list(citations: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a list of citations"""
        result = ValidationResult(is_valid=True, cleaned_data=[])
        
        if not isinstance(citations, list):
            result.add_error("Citations must be a list")
            return result
        
        valid_citations = []
        for i, citation in enumerate(citations):
            cite_result = CitationValidator.validate_citation(citation)
            if cite_result.is_valid:
                valid_citations.append(cite_result.cleaned_data)
            else:
                for error in cite_result.errors:
                    result.add_error(f"Citation {i}: {error}")
                for warning in cite_result.warnings:
                    result.add_warning(f"Citation {i}: {warning}")
        
        result.cleaned_data = valid_citations
        return result


class JudgeValidator:
    """Validates judge information"""
    
    # Common judge name patterns
    JUDGE_NAME_PATTERN = re.compile(
        r'^[A-Z][a-z]+(?:\s+[A-Z]\.?)?(?:\s+[A-Z][a-z]+)+$'
    )
    
    @staticmethod
    def validate_judge_name(name: str) -> ValidationResult:
        """Validate judge name format"""
        result = ValidationResult(is_valid=True, cleaned_data=name)
        
        if not name:
            result.add_error("Judge name is empty")
            return result
        
        if not isinstance(name, str):
            result.add_error(f"Judge name must be string, got {type(name).__name__}")
            return result
        
        # Clean and validate
        cleaned_name = name.strip()
        
        # Check for common issues
        if len(cleaned_name) < 3:
            result.add_error("Judge name too short")
        elif len(cleaned_name) > 100:
            result.add_error("Judge name too long")
        elif cleaned_name.isupper():
            result.add_warning("Judge name is all uppercase")
            result.cleaned_data = cleaned_name.title()
        elif cleaned_name.islower():
            result.add_warning("Judge name is all lowercase")
            result.cleaned_data = cleaned_name.title()
        elif not JudgeValidator.JUDGE_NAME_PATTERN.match(cleaned_name):
            result.add_warning(f"Judge name has unusual format: {cleaned_name}")
        
        # Check for placeholder values
        if cleaned_name.lower() in ['unknown', 'n/a', 'none', 'tbd']:
            result.add_error(f"Judge name appears to be placeholder: {cleaned_name}")
        
        return result
    
    @staticmethod
    def validate_judge_enhancement(enhancement: Dict[str, Any]) -> ValidationResult:
        """Validate judge enhancement result"""
        result = ValidationResult(is_valid=True, cleaned_data=enhancement)
        
        if not isinstance(enhancement, dict):
            result.add_error("Judge enhancement must be a dictionary")
            return result
        
        # Validate judge name if present
        judge_name = enhancement.get('full_name') or enhancement.get('judge_name_found')
        if judge_name:
            name_result = JudgeValidator.validate_judge_name(judge_name)
            if not name_result.is_valid:
                result.errors.extend(name_result.errors)
            result.warnings.extend(name_result.warnings)
        
        return result


class ReporterValidator:
    """Validates reporter information"""
    
    @staticmethod
    def validate_reporter_normalization(normalization: Dict[str, Any]) -> ValidationResult:
        """Validate reporter normalization result"""
        result = ValidationResult(is_valid=True, cleaned_data=normalization)
        
        if not isinstance(normalization, dict):
            result.add_error("Reporter normalization must be a dictionary")
            return result
        
        # Check normalized reporters
        normalized_list = normalization.get('normalized_reporters', [])
        if not isinstance(normalized_list, list):
            result.add_error("Normalized reporters must be a list")
            return result
        
        # Validate each normalization
        for i, norm in enumerate(normalized_list):
            if not isinstance(norm, dict):
                result.add_error(f"Normalization {i}: must be a dictionary")
                continue
            
            original = norm.get('original')
            edition = norm.get('edition')
            
            if not original:
                result.add_warning(f"Normalization {i}: missing original reporter")
            
            if edition and edition != original:
                # This is a successful normalization
                if edition not in VALID_REPORTERS and not any(edition.startswith(base) for base in ['F.', 'F. Supp.']):
                    result.add_warning(f"Normalization {i}: unknown edition '{edition}'")
        
        return result


class PipelineValidator:
    """Main validator orchestrating all validations"""
    
    @staticmethod
    def validate_processing_result(doc: Dict[str, Any]) -> ValidationResult:
        """Validate a fully processed document"""
        result = ValidationResult(is_valid=True, cleaned_data=doc)
        
        # Validate base document
        doc_result = DocumentValidator.validate_document(doc)
        if not doc_result.is_valid:
            result.errors.extend(doc_result.errors)
        result.warnings.extend(doc_result.warnings)
        
        # Validate court enhancement
        if 'court_enhancement' in doc:
            court_result = CourtValidator.validate_court_enhancement(doc['court_enhancement'])
            if not court_result.is_valid:
                result.errors.extend([f"Court: {e}" for e in court_result.errors])
            result.warnings.extend([f"Court: {w}" for w in court_result.warnings])
        
        # Validate citations
        if 'citations_extracted' in doc and 'citations' in doc['citations_extracted']:
            citations_result = CitationValidator.validate_citations_list(
                doc['citations_extracted']['citations']
            )
            if not citations_result.is_valid:
                result.errors.extend([f"Citations: {e}" for e in citations_result.errors])
            result.warnings.extend([f"Citations: {w}" for w in citations_result.warnings])
        
        # Validate judge enhancement
        if 'judge_enhancement' in doc:
            judge_result = JudgeValidator.validate_judge_enhancement(doc['judge_enhancement'])
            if not judge_result.is_valid:
                result.errors.extend([f"Judge: {e}" for e in judge_result.errors])
            result.warnings.extend([f"Judge: {w}" for w in judge_result.warnings])
        
        # Validate reporter normalization
        if 'reporters_normalized' in doc:
            reporter_result = ReporterValidator.validate_reporter_normalization(
                doc['reporters_normalized']
            )
            if not reporter_result.is_valid:
                result.errors.extend([f"Reporters: {e}" for e in reporter_result.errors])
            result.warnings.extend([f"Reporters: {w}" for w in reporter_result.warnings])
        
        return result