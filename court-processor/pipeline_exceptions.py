"""
Custom exception hierarchy for the court processor pipeline

This provides specific, meaningful exceptions for different types of failures,
enabling proper error handling and reporting throughout the pipeline.
"""

class PipelineError(Exception):
    """Base exception for all pipeline errors"""
    def __init__(self, message, stage=None, document_id=None, details=None):
        self.stage = stage
        self.document_id = document_id
        self.details = details or {}
        super().__init__(message)
    
    def to_dict(self):
        """Convert exception to dictionary for logging/reporting"""
        return {
            'error_type': self.__class__.__name__,
            'message': str(self),
            'stage': self.stage,
            'document_id': self.document_id,
            'details': self.details
        }


# Data Quality Exceptions
class ValidationError(PipelineError):
    """Raised when data validation fails"""
    pass


class MissingDataError(ValidationError):
    """Raised when required data is missing"""
    pass


class InvalidDataFormatError(ValidationError):
    """Raised when data is in wrong format"""
    pass


# Processing Exceptions
class ProcessingError(PipelineError):
    """Base class for processing errors"""
    pass


class DocumentRetrievalError(ProcessingError):
    """Raised when document retrieval fails"""
    pass


class EnhancementError(ProcessingError):
    """Base class for enhancement failures"""
    pass


class CourtResolutionError(EnhancementError):
    """Raised when court resolution fails"""
    pass


class CitationExtractionError(EnhancementError):
    """Raised when citation extraction fails"""
    pass


class JudgeEnhancementError(EnhancementError):
    """Raised when judge enhancement fails"""
    pass


class ReporterNormalizationError(EnhancementError):
    """Raised when reporter normalization fails"""
    pass


# Storage Exceptions
class StorageError(PipelineError):
    """Base class for storage errors"""
    pass


class DatabaseConnectionError(StorageError):
    """Raised when database connection fails"""
    pass


class DuplicateDocumentError(StorageError):
    """Raised when attempting to store duplicate document"""
    def __init__(self, message, document_id, existing_id=None):
        super().__init__(message, document_id=document_id)
        self.existing_id = existing_id


# External Service Exceptions
class ExternalServiceError(PipelineError):
    """Base class for external service errors"""
    pass


class HaystackError(ExternalServiceError):
    """Raised when Haystack indexing fails"""
    pass


class CourtListenerAPIError(ExternalServiceError):
    """Raised when CourtListener API calls fail"""
    pass


# Configuration Exceptions
class ConfigurationError(PipelineError):
    """Raised when pipeline configuration is invalid"""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing"""
    pass


# Utility functions for error handling
def handle_enhancement_error(func):
    """Decorator for consistent enhancement error handling"""
    def wrapper(self, document, *args, **kwargs):
        try:
            return func(self, document, *args, **kwargs)
        except Exception as e:
            doc_id = document.get('id', 'unknown')
            stage = func.__name__
            
            if isinstance(e, PipelineError):
                # Re-raise pipeline errors with additional context
                e.stage = stage
                e.document_id = doc_id
                raise
            else:
                # Wrap unexpected errors
                raise EnhancementError(
                    f"Unexpected error in {stage}: {str(e)}",
                    stage=stage,
                    document_id=doc_id,
                    details={'original_error': type(e).__name__}
                )
    return wrapper


def safe_get(data, key, default=None, expected_type=None):
    """
    Safely get a value from a dictionary with optional type checking
    
    Args:
        data: Dictionary to get value from
        key: Key to retrieve
        default: Default value if key not found or type check fails
        expected_type: Expected type of the value (optional)
    
    Returns:
        The value if found and valid, otherwise default
    
    Raises:
        InvalidDataFormatError: If strict type checking is needed
    """
    if not isinstance(data, dict):
        return default
    
    value = data.get(key, default)
    
    if expected_type and value is not None and not isinstance(value, expected_type):
        # For now, return default. Could raise exception if strict mode needed
        return default
    
    return value