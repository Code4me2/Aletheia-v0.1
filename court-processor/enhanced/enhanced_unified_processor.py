"""
Enhanced Unified Document Processor

Extends the existing UnifiedDocumentProcessor with improved error handling,
comprehensive logging, configuration management, and performance monitoring.
"""
import asyncio
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import sys
import os

# Add services to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))

from .config import get_settings, Environment
from .utils.logging import get_logger, ProcessingLogger, log_processing_time
from .utils.monitoring import get_monitor, monitor_operation
from .utils.validation import DocumentValidator, APIRequestValidator, ValidationResult

# Import existing services
try:
    from services.unified_document_processor import (
        UnifiedDocumentProcessor, 
        DeduplicationManager,
        UnstructuredProcessor
    )
    from services.courtlistener_service import CourtListenerService
    from services.flp_integration import FLPIntegration
except ImportError as e:
    # Graceful fallback for development
    print(f"Warning: Could not import existing services: {e}")
    UnifiedDocumentProcessor = object
    DeduplicationManager = object
    UnstructuredProcessor = object
    CourtListenerService = object
    FLPIntegration = object


class EnhancedDeduplicationManager(DeduplicationManager):
    """Enhanced deduplication with performance monitoring"""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger("deduplication")
        self.monitor = get_monitor()
        self._cache_hits = 0
        self._cache_misses = 0
    
    @monitor_operation("deduplication_check")
    def is_duplicate(self, document: Dict) -> bool:
        """Check if document is duplicate with monitoring"""
        try:
            result = super().is_duplicate(document)
            if result:
                self._cache_hits += 1
                self.logger.debug("Document is duplicate", extra={'document_id': document.get('id')})
            else:
                self._cache_misses += 1
            return result
        except Exception as e:
            self.logger.error(f"Deduplication check failed: {str(e)}")
            # Return False to allow processing in case of deduplication failure
            return False
    
    @monitor_operation("deduplication_mark")
    def mark_processed(self, document: Dict):
        """Mark document as processed with monitoring"""
        try:
            super().mark_processed(document)
            self.logger.debug("Document marked as processed", extra={'document_id': document.get('id')})
        except Exception as e:
            self.logger.error(f"Failed to mark document as processed: {str(e)}")
    
    @property
    def cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self._cache_hits + self._cache_misses
        return self._cache_hits / total if total > 0 else 0.0


class EnhancedUnifiedDocumentProcessor:
    """
    Enhanced version of UnifiedDocumentProcessor with improved:
    - Error handling and recovery
    - Comprehensive logging and monitoring
    - Configuration management
    - Data validation
    - Performance optimization
    """
    
    def __init__(self, config_override: Optional[Dict[str, Any]] = None):
        """Initialize enhanced processor"""
        # Load configuration
        self.settings = get_settings()
        self.environment = Environment()
        
        # Apply configuration overrides
        if config_override:
            # TODO: Implement configuration override logic
            pass
        
        # Setup logging
        self.logger = get_logger("enhanced_processor")
        self.processing_logger = ProcessingLogger("document_processing")
        
        # Initialize monitoring
        self.monitor = get_monitor()
        
        # Initialize validators
        self.document_validator = DocumentValidator()
        self.api_validator = APIRequestValidator()
        
        # Initialize components
        self._initialize_components()
        
        self.logger.info("Enhanced Unified Document Processor initialized")
    
    def _initialize_components(self):
        """Initialize processing components"""
        try:
            # Enhanced deduplication manager
            self.dedup_manager = EnhancedDeduplicationManager()
            
            # Service components (with fallbacks for missing imports)
            if UnifiedDocumentProcessor != object:
                # Use existing components if available
                base_processor = UnifiedDocumentProcessor()
                self.cl_service = base_processor.cl_service
                self.flp_integration = base_processor.flp_integration
                self.unstructured = base_processor.unstructured
            else:
                # Create mock components for development
                self.cl_service = None
                self.flp_integration = None
                self.unstructured = None
                self.logger.warning("Using mock components - some services not available")
            
            self.logger.info("Components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize components: {str(e)}")
            raise
    
    async def process_courtlistener_batch(self, 
                                        court_id: Optional[str] = None,
                                        date_filed_after: Optional[str] = None,
                                        max_documents: int = 100) -> Dict[str, Any]:
        """
        Process a batch of documents from CourtListener with enhanced monitoring
        """
        # Validate request
        request_data = {
            'court_id': court_id,
            'date_filed_after': date_filed_after,
            'max_documents': max_documents
        }
        
        validation_result = self.api_validator.validate_batch_request(request_data)
        if not validation_result.is_valid:
            raise ValueError(f"Invalid batch request: {validation_result.errors}")
        
        if validation_result.has_warnings:
            for warning in validation_result.warnings:
                self.logger.warning(f"Batch request warning: {warning}")
        
        # Initialize processing
        batch_id = f"batch_{int(time.time())}"
        self.processing_logger.start_batch_processing(batch_id, max_documents)
        
        stats = {
            'total_fetched': 0,
            'new_documents': 0,
            'duplicates': 0,
            'errors': 0,
            'processing_time': time.time()
        }
        
        try:
            with log_processing_time(self.logger, "batch_processing", batch_id=batch_id):
                # Fetch documents from CourtListener
                if self.cl_service:
                    cl_documents = await self._fetch_documents_with_monitoring(
                        court_id, date_filed_after, max_documents
                    )
                else:
                    # Use mock data for development
                    cl_documents = self._get_mock_documents(max_documents)
                
                stats['total_fetched'] = len(cl_documents)
                self.logger.info(f"Fetched {len(cl_documents)} documents from CourtListener")
                
                # Process each document
                for i, cl_doc in enumerate(cl_documents):
                    try:
                        # Update progress
                        if i % 10 == 0:
                            self.logger.info(f"Processing document {i+1}/{len(cl_documents)}")
                        
                        # Check for duplicates
                        if self.dedup_manager.is_duplicate(cl_doc):
                            stats['duplicates'] += 1
                            self.monitor.record_document_processing(True, 0.0, is_duplicate=True)
                            continue
                        
                        # Process document
                        result = await self.process_single_document(cl_doc)
                        
                        if result.get('saved_id'):
                            stats['new_documents'] += 1
                            self.dedup_manager.mark_processed(cl_doc)
                        else:
                            stats['errors'] += 1
                            
                    except Exception as e:
                        stats['errors'] += 1
                        self.logger.error(f"Error processing document {i}: {str(e)}")
                        self.monitor.record_error(e)
                        
                        # Continue with next document
                        continue
                
                # Calculate final stats
                stats['processing_time'] = time.time() - stats['processing_time']
                
                self.processing_logger.complete_processing(
                    success=stats['errors'] < stats['total_fetched'] / 2,  # Success if <50% errors
                    duration=stats['processing_time'],
                    results=stats
                )
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Batch processing failed: {str(e)}")
            self.monitor.record_error(e)
            stats['error'] = str(e)
            return stats
    
    async def process_single_document(self, cl_document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single document with enhanced validation and monitoring
        """
        # Validate document
        validation_result = self.document_validator.validate_courtlistener_document(cl_document)
        if not validation_result.is_valid:
            error_msg = f"Invalid document: {validation_result.errors}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        if validation_result.has_warnings:
            for warning in validation_result.warnings:
                self.logger.warning(f"Document validation warning: {warning}")
        
        # Initialize processing
        document_id = str(cl_document.get('id', 'unknown'))
        self.processing_logger.start_document_processing(
            document_id, 
            cl_document.get('type', 'unknown')
        )
        
        start_time = time.time()
        
        try:
            with log_processing_time(self.logger, "document_processing", document_id=document_id):
                # Step 1: FLP Enhancement
                enhanced_doc = await self._flp_enhance_with_monitoring(cl_document)
                
                # Step 2: Unstructured.io Processing
                if enhanced_doc.get('plain_text') or enhanced_doc.get('pdf_url'):
                    structured_data = await self._unstructured_process_with_monitoring(enhanced_doc)
                    enhanced_doc['structured_elements'] = structured_data
                
                # Step 3: Save to database
                saved_id = await self._save_to_database_with_monitoring(enhanced_doc)
                enhanced_doc['saved_id'] = saved_id
                
                # Record success metrics
                processing_time = time.time() - start_time
                citations_count = len(enhanced_doc.get('citations', []))
                
                self.monitor.record_document_processing(
                    success=True, 
                    duration=processing_time, 
                    citations=citations_count
                )
                
                self.processing_logger.complete_processing(
                    success=True,
                    duration=processing_time,
                    results={'citations_found': citations_count, 'saved_id': saved_id}
                )
                
                return enhanced_doc
                
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Document processing failed: {str(e)}")
            
            self.monitor.record_document_processing(
                success=False, 
                duration=processing_time
            )
            self.monitor.record_error(e)
            
            self.processing_logger.log_processing_error(
                "document_processing", 
                e, 
                {'document_id': document_id}
            )
            
            return {'success': False, 'error': str(e), 'cl_id': cl_document.get('id')}
    
    async def _fetch_documents_with_monitoring(self, court_id: Optional[str], 
                                             date_filed_after: Optional[str], 
                                             max_documents: int) -> List[Dict[str, Any]]:
        """Fetch documents with service monitoring"""
        try:
            if self.cl_service:
                return await self.cl_service.fetch_opinions(
                    court_id=court_id,
                    date_filed_after=date_filed_after,
                    max_results=max_documents
                )
            else:
                # Return mock data for development
                return self._get_mock_documents(max_documents)
        except Exception as e:
            self.monitor.record_service_call("courtlistener", False, 0.0)
            raise
    
    async def _flp_enhance_with_monitoring(self, cl_document: Dict[str, Any]) -> Dict[str, Any]:
        """FLP enhancement with monitoring"""
        start_time = time.time()
        
        try:
            if self.flp_integration:
                # Use existing FLP integration
                enhanced = cl_document.copy()
                # TODO: Call actual FLP integration methods
                enhanced['citations'] = []
                enhanced['court_info'] = {}
                enhanced['flp_processing_timestamp'] = time.time()
            else:
                # Mock enhancement for development
                enhanced = cl_document.copy()
                enhanced['citations'] = [
                    {'citation_string': 'Mock citation', 'type': 'CaseCitation'}
                ]
                enhanced['court_info'] = {'id': cl_document.get('court_id'), 'standardized': False}
                enhanced['flp_processing_timestamp'] = time.time()
            
            duration = time.time() - start_time
            self.monitor.record_service_call("flp_integration", True, duration)
            
            # Validate enhancement results
            validation_result = self.document_validator.validate_flp_enhancement_result(enhanced)
            if validation_result.has_warnings:
                for warning in validation_result.warnings:
                    self.logger.warning(f"FLP enhancement warning: {warning}")
            
            return enhanced
            
        except Exception as e:
            duration = time.time() - start_time
            self.monitor.record_service_call("flp_integration", False, duration)
            self.logger.error(f"FLP enhancement failed: {str(e)}")
            
            # Return document with minimal enhancement
            enhanced = cl_document.copy()
            enhanced['flp_error'] = str(e)
            return enhanced
    
    async def _unstructured_process_with_monitoring(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Unstructured.io processing with monitoring"""
        start_time = time.time()
        
        try:
            if self.unstructured:
                # Use existing unstructured processor
                # TODO: Call actual unstructured processing
                result = {
                    'full_text': document.get('plain_text', ''),
                    'structured_elements': [],
                    'processing_timestamp': time.time()
                }
            else:
                # Mock processing for development
                result = {
                    'full_text': document.get('plain_text', 'Mock processed text'),
                    'structured_elements': [
                        {'type': 'Title', 'text': 'Mock Document Title'},
                        {'type': 'NarrativeText', 'text': 'Mock document content'}
                    ],
                    'processing_timestamp': time.time()
                }
            
            duration = time.time() - start_time
            self.monitor.record_service_call("unstructured", True, duration)
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            self.monitor.record_service_call("unstructured", False, duration)
            self.logger.error(f"Unstructured processing failed: {str(e)}")
            
            # Return minimal processing result
            return {
                'error': str(e),
                'processing_timestamp': time.time()
            }
    
    async def _save_to_database_with_monitoring(self, document: Dict[str, Any]) -> Optional[int]:
        """Save to database with monitoring"""
        start_time = time.time()
        
        try:
            # TODO: Implement actual database saving
            # For now, return mock saved ID
            saved_id = int(time.time())
            
            duration = time.time() - start_time
            self.monitor.record_service_call("database", True, duration)
            
            self.logger.info(f"Document saved with ID: {saved_id}")
            return saved_id
            
        except Exception as e:
            duration = time.time() - start_time
            self.monitor.record_service_call("database", False, duration)
            self.logger.error(f"Database save failed: {str(e)}")
            return None
    
    def _get_mock_documents(self, count: int) -> List[Dict[str, Any]]:
        """Generate mock documents for development"""
        documents = []
        for i in range(min(count, 10)):  # Limit to 10 for development
            documents.append({
                'id': 1000 + i,
                'court_id': 'cafc',
                'case_name': f'Mock Case {i+1} v. Test Case {i+1}',
                'docket_number': f'20-{1000+i}',
                'date_filed': '2024-01-15',
                'author_str': 'Mock Judge',
                'plain_text': f'This is mock document {i+1} content for testing.',
                'type': 'opinion'
            })
        return documents
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status"""
        base_health = self.monitor.get_health_status()
        
        # Add component-specific health checks
        component_health = {
            'deduplication_cache_hit_rate': self.dedup_manager.cache_hit_rate,
            'environment': self.environment.env_type.value,
            'feature_flags': self.environment.get_feature_flags(),
        }
        
        base_health['components'] = component_health
        return base_health
    
    def get_processing_metrics(self) -> Dict[str, Any]:
        """Get detailed processing metrics"""
        return self.monitor.get_metrics()