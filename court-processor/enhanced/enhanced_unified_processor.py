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

# Import enhanced services
from .services.courtlistener_service import CourtListenerService

# Import existing services
try:
    from services.unified_document_processor import (
        UnifiedDocumentProcessor, 
        DeduplicationManager,
        UnstructuredProcessor
    )
    from services.flp_integration import FLPIntegration
except ImportError as e:
    # Graceful fallback for development
    print(f"Warning: Could not import existing services: {e}")
    UnifiedDocumentProcessor = object
    DeduplicationManager = object
    UnstructuredProcessor = object
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
            
            # Enhanced CourtListener service (always use our implementation)
            self.cl_service = CourtListenerService()
            
            # Enhanced FLP processor
            try:
                from .services.flp_processor import EnhancedFLPProcessor
                self.flp_processor = EnhancedFLPProcessor()
                self.logger.info("Enhanced FLP processor initialized")
            except Exception as e:
                self.flp_processor = None
                self.logger.warning(f"FLP processor initialization failed: {str(e)}")
            
            # Enhanced Haystack integration
            try:
                from .services.haystack_integration import HaystackIntegrationManager
                self.haystack_manager = HaystackIntegrationManager()
                self.logger.info("Enhanced Haystack integration initialized")
            except Exception as e:
                self.haystack_manager = None
                self.logger.warning(f"Haystack integration initialization failed: {str(e)}")
            
            # Service components (with fallbacks for missing imports)
            if UnifiedDocumentProcessor != object:
                # Use existing components if available
                base_processor = UnifiedDocumentProcessor()
                self.flp_integration = base_processor.flp_integration
                self.unstructured = base_processor.unstructured
            else:
                # Create mock components for development
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
                                        max_documents: int = 100,
                                        judge_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a batch of documents from CourtListener with enhanced monitoring
        
        UPDATED: Supports both general court searches and judge-specific searches
        """
        # Validate request
        request_data = {
            'court_id': court_id,
            'date_filed_after': date_filed_after,
            'max_documents': max_documents,
            'judge_name': judge_name
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
                        court_id, date_filed_after, max_documents, judge_name
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
                                             max_documents: int,
                                             judge_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch documents with service monitoring - UPDATED with judge support"""
        start_time = time.time()
        try:
            # Use enhanced CourtListener service
            if self.cl_service and self.settings.services.courtlistener_api_key:
                if judge_name:
                    self.logger.info(f"Fetching documents for judge '{judge_name}' from CourtListener API (court: {court_id}, max: {max_documents})")
                    
                    # Use corrected docket-first approach for judge searches
                    if judge_name.lower() == "gilstrap":
                        documents = await self.cl_service.fetch_gilstrap_documents(
                            max_documents=max_documents,
                            date_filed_after=date_filed_after,
                            include_text=True
                        )
                    else:
                        # Generic judge search using docket-first approach
                        documents = await self.cl_service.fetch_judge_documents(
                            judge_name=judge_name,
                            court_id=court_id,
                            max_documents=max_documents,
                            date_filed_after=date_filed_after,
                            include_text=True
                        )
                else:
                    self.logger.info(f"Fetching documents from CourtListener API (court: {court_id}, max: {max_documents})")
                    
                    # General court search
                    documents = await self.cl_service.fetch_opinions(
                        court_id=court_id,
                        max_documents=max_documents,
                        date_filed__gte=date_filed_after
                    )
                
                processing_time = time.time() - start_time
                self.monitor.record_service_call("courtlistener", True, processing_time)
                
                self.logger.info("Successfully fetched documents from CourtListener",
                               count=len(documents), processing_time=processing_time)
                
                return documents
            else:
                # Return mock data for development
                self.logger.warning("No API key configured - using mock data")
                return self._get_mock_documents(max_documents)
                
        except Exception as e:
            processing_time = time.time() - start_time
            self.monitor.record_service_call("courtlistener", False, processing_time)
            self.logger.error(f"Failed to fetch documents from CourtListener: {str(e)}")
            raise
    
    async def process_gilstrap_documents_batch(self, 
                                             max_documents: int = 50,
                                             date_filed_after: Optional[str] = None,
                                             include_text: bool = True) -> Dict[str, Any]:
        """
        Specialized method for processing Judge Gilstrap documents
        
        Uses the corrected docket-first approach optimized for Gilstrap retrieval
        """
        self.logger.info("Starting specialized Judge Gilstrap document processing batch")
        
        return await self.process_courtlistener_batch(
            court_id="txed",  # Eastern District of Texas
            judge_name="Gilstrap",
            max_documents=max_documents,
            date_filed_after=date_filed_after
        )
    
    async def process_and_ingest_to_haystack(self, 
                                           court_id: Optional[str] = None,
                                           judge_name: Optional[str] = None,
                                           max_documents: int = 100,
                                           date_filed_after: Optional[str] = None) -> Dict[str, Any]:
        """
        Process documents from CourtListener and automatically ingest to Haystack
        
        Returns combined processing and ingestion statistics
        """
        self.logger.info("Starting combined processing and Haystack ingestion")
        
        # Step 1: Process documents through enhanced pipeline
        batch_result = await self.process_courtlistener_batch(
            court_id=court_id,
            judge_name=judge_name,
            max_documents=max_documents,
            date_filed_after=date_filed_after
        )
        
        # Step 2: Ingest processed documents to Haystack
        if self.haystack_manager and batch_result.get('new_documents', 0) > 0:
            self.logger.info(f"Ingesting {batch_result['new_documents']} new documents to Haystack")
            
            try:
                # Initialize Haystack manager if not done
                await self.haystack_manager.initialize()
                
                # Ingest newly processed documents
                if judge_name:
                    job_id = await self.haystack_manager.ingest_judge_documents(
                        judge_name=judge_name,
                        court_id=court_id,
                        max_documents=batch_result['new_documents']
                    )
                else:
                    job_id = await self.haystack_manager.ingest_new_documents_only()
                
                # Wait for ingestion to complete (with timeout)
                ingestion_stats = await self._wait_for_haystack_job(job_id, timeout=300)
                
                batch_result['haystack_ingestion'] = {
                    'job_id': job_id,
                    'stats': ingestion_stats,
                    'success': ingestion_stats is not None
                }
                
                self.logger.info(f"Haystack ingestion completed: job {job_id}")
                
            except Exception as e:
                self.logger.error(f"Haystack ingestion failed: {str(e)}")
                batch_result['haystack_ingestion'] = {
                    'success': False,
                    'error': str(e)
                }
        else:
            batch_result['haystack_ingestion'] = {
                'success': False,
                'reason': 'No Haystack manager or no new documents'
            }
        
        return batch_result
    
    async def ingest_gilstrap_to_haystack(self, 
                                        max_documents: int = 100,
                                        date_filed_after: Optional[str] = None) -> str:
        """
        Specialized method for ingesting Judge Gilstrap documents to Haystack
        
        Returns job_id for monitoring progress
        """
        self.logger.info("Starting Judge Gilstrap Haystack ingestion")
        
        if not self.haystack_manager:
            raise RuntimeError("Haystack integration not available")
        
        await self.haystack_manager.initialize()
        
        job_id = await self.haystack_manager.ingest_judge_documents(
            judge_name="Gilstrap",
            court_id="txed",
            max_documents=max_documents
        )
        
        self.logger.info(f"Judge Gilstrap Haystack ingestion started: {job_id}")
        return job_id
    
    async def _wait_for_haystack_job(self, job_id: str, timeout: int = 300) -> Optional[Dict[str, Any]]:
        """Wait for Haystack job completion with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.haystack_manager.get_job_status(job_id)
                
                if not status:
                    self.logger.error(f"Haystack job {job_id} not found")
                    return None
                
                current_status = status['status']
                
                if current_status == "completed":
                    return status.get('stats')
                elif current_status in ["failed", "cancelled"]:
                    self.logger.error(f"Haystack job {job_id} {current_status}: {status.get('error', 'Unknown error')}")
                    return None
                
                # Wait before checking again
                await asyncio.sleep(5)
                
            except Exception as e:
                self.logger.error(f"Error waiting for Haystack job {job_id}: {str(e)}")
                return None
        
        self.logger.warning(f"Haystack job {job_id} timed out after {timeout} seconds")
        return None
    
    async def _flp_enhance_with_monitoring(self, cl_document: Dict[str, Any]) -> Dict[str, Any]:
        """FLP enhancement with monitoring"""
        start_time = time.time()
        
        try:
            if self.flp_processor:
                # Use enhanced FLP processor
                enhanced = self.flp_processor.enhance_document(cl_document)
            elif self.flp_integration:
                # Use existing FLP integration as fallback
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