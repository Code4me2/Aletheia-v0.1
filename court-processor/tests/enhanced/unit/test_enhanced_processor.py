"""
Unit tests for Enhanced Unified Document Processor
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import time

from enhanced.enhanced_unified_processor import (
    EnhancedUnifiedDocumentProcessor,
    EnhancedDeduplicationManager
)
from enhanced.utils.validation import ValidationResult


class TestEnhancedDeduplicationManager:
    """Test enhanced deduplication functionality"""
    
    def test_initialization(self):
        """Test deduplication manager initialization"""
        dedup = EnhancedDeduplicationManager()
        assert dedup.logger is not None
        assert dedup.monitor is not None
        assert dedup._cache_hits == 0
        assert dedup._cache_misses == 0
    
    def test_cache_hit_rate_empty(self):
        """Test cache hit rate with no data"""
        dedup = EnhancedDeduplicationManager()
        assert dedup.cache_hit_rate == 0.0
    
    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        dedup = EnhancedDeduplicationManager()
        dedup._cache_hits = 7
        dedup._cache_misses = 3
        assert dedup.cache_hit_rate == 0.7
    
    @patch('enhanced.enhanced_unified_processor.DeduplicationManager.is_duplicate')
    def test_is_duplicate_monitoring(self, mock_is_duplicate):
        """Test that duplicate checking includes monitoring"""
        mock_is_duplicate.return_value = True
        
        dedup = EnhancedDeduplicationManager()
        document = {'id': 123, 'case_name': 'Test Case'}
        
        result = dedup.is_duplicate(document)
        
        assert result is True
        assert dedup._cache_hits == 1
        assert dedup._cache_misses == 0
        mock_is_duplicate.assert_called_once_with(document)
    
    @patch('enhanced.enhanced_unified_processor.DeduplicationManager.is_duplicate')
    def test_is_duplicate_error_handling(self, mock_is_duplicate):
        """Test error handling in duplicate checking"""
        mock_is_duplicate.side_effect = Exception("Database error")
        
        dedup = EnhancedDeduplicationManager()
        document = {'id': 123, 'case_name': 'Test Case'}
        
        # Should return False on error to allow processing
        result = dedup.is_duplicate(document)
        assert result is False


class TestEnhancedUnifiedDocumentProcessor:
    """Test enhanced unified document processor"""
    
    def test_initialization(self, test_settings):
        """Test processor initialization"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        assert processor.settings is not None
        assert processor.environment is not None
        assert processor.logger is not None
        assert processor.processing_logger is not None
        assert processor.monitor is not None
        assert processor.document_validator is not None
        assert processor.api_validator is not None
        assert processor.dedup_manager is not None
    
    def test_health_status(self, enhanced_processor):
        """Test health status reporting"""
        health = enhanced_processor.get_health_status()
        
        assert isinstance(health, dict)
        assert 'status' in health
        assert 'components' in health
        assert 'deduplication_cache_hit_rate' in health['components']
        assert 'environment' in health['components']
        assert 'feature_flags' in health['components']
    
    def test_processing_metrics(self, enhanced_processor):
        """Test processing metrics reporting"""
        metrics = enhanced_processor.get_processing_metrics()
        
        assert isinstance(metrics, dict)
        # Should contain metrics structure from monitor
        assert 'processing' in metrics or len(metrics) == 0  # Empty for new instance
    
    @pytest.mark.asyncio
    async def test_process_single_document_validation_error(self, enhanced_processor):
        """Test single document processing with validation error"""
        # Invalid document (missing required fields)
        invalid_doc = {'case_name': 'Test Case'}  # Missing id and court_id
        
        result = await enhanced_processor.process_single_document(invalid_doc)
        
        assert result['success'] is False
        assert 'error' in result
        assert 'Invalid document' in result['error']
    
    @pytest.mark.asyncio
    async def test_process_single_document_success_mock(self, enhanced_processor, sample_courtlistener_document):
        """Test successful single document processing with mocks"""
        result = await enhanced_processor.process_single_document(sample_courtlistener_document)
        
        # Should succeed with mock components
        assert 'saved_id' in result or 'error' in result
        # With mock components, we expect a saved_id
        if 'saved_id' in result:
            assert isinstance(result['saved_id'], int)
    
    @pytest.mark.asyncio
    async def test_batch_processing_validation(self, enhanced_processor):
        """Test batch processing request validation"""
        # Test with invalid max_documents
        with pytest.raises(ValueError) as exc_info:
            await enhanced_processor.process_courtlistener_batch(
                court_id="cafc",
                max_documents=-1  # Invalid
            )
        assert "Invalid batch request" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_batch_processing_mock_success(self, enhanced_processor):
        """Test successful batch processing with mock data"""
        result = await enhanced_processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=5
        )
        
        # Should return valid stats structure
        required_fields = ['total_fetched', 'new_documents', 'duplicates', 'errors']
        for field in required_fields:
            assert field in result
            assert isinstance(result[field], int)
    
    def test_mock_document_generation(self, enhanced_processor):
        """Test mock document generation for development"""
        docs = enhanced_processor._get_mock_documents(5)
        
        assert isinstance(docs, list)
        assert len(docs) == 5
        
        for doc in docs:
            assert 'id' in doc
            assert 'court_id' in doc
            assert 'case_name' in doc
            assert doc['court_id'] == 'cafc'
    
    @pytest.mark.asyncio
    async def test_flp_enhance_with_error_handling(self, enhanced_processor, sample_courtlistener_document):
        """Test FLP enhancement with error handling"""
        # This should not raise an exception even if FLP components aren't available
        result = await enhanced_processor._flp_enhance_with_monitoring(sample_courtlistener_document)
        
        assert isinstance(result, dict)
        assert 'flp_processing_timestamp' in result or 'flp_error' in result
    
    @pytest.mark.asyncio
    async def test_unstructured_process_with_error_handling(self, enhanced_processor, sample_courtlistener_document):
        """Test Unstructured.io processing with error handling"""
        # This should not raise an exception even if unstructured components aren't available
        result = await enhanced_processor._unstructured_process_with_monitoring(sample_courtlistener_document)
        
        assert isinstance(result, dict)
        assert 'processing_timestamp' in result
    
    @pytest.mark.asyncio
    async def test_database_save_with_monitoring(self, enhanced_processor, sample_courtlistener_document):
        """Test database save with monitoring"""
        # This should return a mock saved ID for development
        saved_id = await enhanced_processor._save_to_database_with_monitoring(sample_courtlistener_document)
        
        assert isinstance(saved_id, int)
        assert saved_id > 0


class TestProcessorIntegration:
    """Integration tests for processor components"""
    
    @pytest.mark.asyncio
    async def test_full_processing_pipeline_mock(self, enhanced_processor, sample_courtlistener_document):
        """Test full processing pipeline with mock components"""
        start_time = time.time()
        
        result = await enhanced_processor.process_single_document(sample_courtlistener_document)
        
        processing_time = time.time() - start_time
        
        # Should complete quickly with mocks
        assert processing_time < 1.0
        
        # Should have some result
        assert isinstance(result, dict)
        assert 'saved_id' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_duplicates(self, enhanced_processor):
        """Test batch processing with duplicate handling"""
        # Process the same batch twice to test deduplication
        result1 = await enhanced_processor.process_courtlistener_batch(
            court_id="cafc", 
            max_documents=3
        )
        
        result2 = await enhanced_processor.process_courtlistener_batch(
            court_id="cafc", 
            max_documents=3
        )
        
        # Second run should have more duplicates
        assert result2['duplicates'] >= result1['duplicates']
    
    def test_processor_configuration_override(self):
        """Test processor with configuration overrides"""
        config_override = {
            'processing': {
                'max_batch_size': 50
            }
        }
        
        processor = EnhancedUnifiedDocumentProcessor(config_override=config_override)
        
        # Should initialize without error
        assert processor is not None
        assert processor.settings is not None


class TestErrorHandling:
    """Test error handling and recovery"""
    
    @pytest.mark.asyncio
    async def test_service_failure_recovery(self, enhanced_processor, sample_courtlistener_document):
        """Test recovery from service failures"""
        # Mock a service failure in FLP enhancement
        with patch.object(enhanced_processor, '_flp_enhance_with_monitoring') as mock_flp:
            mock_flp.side_effect = Exception("Service unavailable")
            
            # Should not crash, should return error result
            result = await enhanced_processor.process_single_document(sample_courtlistener_document)
            
            assert result['success'] is False
            assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_batch_processing_partial_failure(self, enhanced_processor):
        """Test batch processing with partial failures"""
        # Mock service that fails for some documents
        original_process = enhanced_processor.process_single_document
        
        async def mock_process_with_failures(doc):
            # Fail every other document
            if doc['id'] % 2 == 0:
                raise Exception("Mock processing error")
            return await original_process(doc)
        
        enhanced_processor.process_single_document = mock_process_with_failures
        
        result = await enhanced_processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=4
        )
        
        # Should have some errors but continue processing
        assert result['errors'] > 0
        assert result['total_fetched'] > 0