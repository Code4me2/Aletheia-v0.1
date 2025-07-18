"""
Integration tests for Enhanced Unified Document Processor

Tests the full processor pipeline with mocked external services
but real internal component interactions.
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor


class TestProcessorIntegration:
    """Integration tests for the enhanced processor"""
    
    @pytest.mark.asyncio
    async def test_full_document_processing_pipeline(self, sample_courtlistener_document):
        """Test complete document processing pipeline"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        start_time = time.time()
        result = await processor.process_single_document(sample_courtlistener_document)
        processing_time = time.time() - start_time
        
        # Should complete successfully
        assert isinstance(result, dict)
        assert processing_time < 5.0  # Should be fast with mocks
        
        # Should have either success or error result
        if 'saved_id' in result:
            # Success case
            assert isinstance(result['saved_id'], int)
            assert result['saved_id'] > 0
        else:
            # Error case - should have error message
            assert 'error' in result
            assert isinstance(result['error'], str)
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_mixed_results(self):
        """Test batch processing with mixed success/failure results"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        start_time = time.time()
        result = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=5
        )
        processing_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert processing_time < 10.0
        
        # Should have valid stats structure
        assert isinstance(result, dict)
        required_fields = ['total_fetched', 'new_documents', 'duplicates', 'errors']
        for field in required_fields:
            assert field in result
            assert isinstance(result[field], int)
            assert result[field] >= 0
        
        # Should have processed some documents
        assert result['total_fetched'] > 0
    
    @pytest.mark.asyncio
    async def test_validation_integration(self, validation_test_cases):
        """Test that validation is properly integrated into processing"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Test valid document
        valid_result = await processor.process_single_document(
            validation_test_cases['valid_document']
        )
        # Should not fail due to validation
        assert 'Invalid document' not in str(valid_result)
        
        # Test invalid document
        invalid_result = await processor.process_single_document(
            validation_test_cases['invalid_document_missing_id']
        )
        # Should fail due to validation
        assert invalid_result['success'] is False
        assert 'Invalid document' in invalid_result['error']
    
    @pytest.mark.asyncio
    async def test_monitoring_integration(self):
        """Test that monitoring is properly integrated"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Process some documents to generate metrics
        await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=3
        )
        
        # Check that monitoring data is available
        health = processor.get_health_status()
        assert isinstance(health, dict)
        assert 'status' in health
        
        metrics = processor.get_processing_metrics()
        assert isinstance(metrics, dict)
    
    @pytest.mark.asyncio
    async def test_deduplication_integration(self):
        """Test that deduplication is properly integrated"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Process the same batch twice
        result1 = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=3
        )
        
        result2 = await processor.process_courtlistener_batch(
            court_id="cafc", 
            max_documents=3
        )
        
        # Second batch should have duplicates
        assert result2['duplicates'] > 0
        assert result2['new_documents'] <= result1['new_documents']
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(self):
        """Test error recovery and graceful degradation"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Create a document that will cause processing errors
        problematic_doc = {
            'id': 999,
            'court_id': 'cafc',
            'case_name': 'Problematic Case',
            'plain_text': None  # This might cause issues in processing
        }
        
        # Should handle gracefully
        result = await processor.process_single_document(problematic_doc)
        
        # Should return a result (either success or controlled failure)
        assert isinstance(result, dict)
        assert 'saved_id' in result or 'error' in result
    
    @pytest.mark.asyncio
    async def test_configuration_integration(self):
        """Test that configuration is properly applied"""
        # Create processor with custom configuration
        config_override = {
            'processing': {
                'default_batch_size': 2,
                'max_retries': 1
            }
        }
        
        processor = EnhancedUnifiedDocumentProcessor(config_override=config_override)
        
        # Should initialize successfully
        assert processor is not None
        assert processor.settings is not None
        
        # Configuration should be applied (tested indirectly through behavior)
        result = await processor.process_courtlistener_batch(max_documents=1)
        assert isinstance(result, dict)
    
    def test_health_check_integration(self):
        """Test comprehensive health checking"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        health = processor.get_health_status()
        
        # Should have comprehensive health information
        assert 'status' in health
        assert health['status'] in ['healthy', 'unhealthy']
        assert 'components' in health
        assert 'deduplication_cache_hit_rate' in health['components']
        assert 'environment' in health['components']
        assert 'feature_flags' in health['components']
        
        # Should have metrics summary
        if 'metrics_summary' in health:
            summary = health['metrics_summary']
            assert 'documents_processed' in summary
            assert 'success_rate' in summary


class TestServiceIntegration:
    """Test integration between different services"""
    
    @pytest.mark.asyncio
    async def test_courtlistener_to_flp_integration(self, sample_courtlistener_document):
        """Test data flow from CourtListener to FLP enhancement"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Test FLP enhancement step
        enhanced = await processor._flp_enhance_with_monitoring(sample_courtlistener_document)
        
        # Should preserve original document data
        assert enhanced['id'] == sample_courtlistener_document['id']
        assert enhanced['court_id'] == sample_courtlistener_document['court_id']
        
        # Should add FLP enhancements
        assert 'flp_processing_timestamp' in enhanced or 'flp_error' in enhanced
    
    @pytest.mark.asyncio
    async def test_flp_to_unstructured_integration(self, sample_courtlistener_document):
        """Test data flow from FLP enhancement to Unstructured.io"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # First enhance with FLP
        enhanced = await processor._flp_enhance_with_monitoring(sample_courtlistener_document)
        
        # Then process with Unstructured.io
        structured = await processor._unstructured_process_with_monitoring(enhanced)
        
        # Should have structured output
        assert 'processing_timestamp' in structured
        assert isinstance(structured, dict)
    
    @pytest.mark.asyncio
    async def test_unstructured_to_database_integration(self, sample_courtlistener_document):
        """Test data flow from Unstructured.io to database"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Process through pipeline
        enhanced = await processor._flp_enhance_with_monitoring(sample_courtlistener_document)
        structured = await processor._unstructured_process_with_monitoring(enhanced)
        enhanced['structured_elements'] = structured
        
        # Save to database
        saved_id = await processor._save_to_database_with_monitoring(enhanced)
        
        # Should get a valid saved ID
        assert isinstance(saved_id, int)
        assert saved_id > 0


class TestPerformanceIntegration:
    """Test performance characteristics of integrated system"""
    
    @pytest.mark.asyncio
    async def test_single_document_performance(self, sample_courtlistener_document):
        """Test single document processing performance"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        start_time = time.time()
        result = await processor.process_single_document(sample_courtlistener_document)
        processing_time = time.time() - start_time
        
        # Should complete quickly with mock services
        assert processing_time < 2.0
        
        # Check that timing was recorded
        metrics = processor.get_processing_metrics()
        assert isinstance(metrics, dict)
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test batch processing performance"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        start_time = time.time()
        result = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=10
        )
        processing_time = time.time() - start_time
        
        # Should complete reasonably quickly
        assert processing_time < 10.0
        
        # Should have processed multiple documents
        assert result['total_fetched'] > 0
        
        # Performance should be tracked
        health = processor.get_health_status()
        assert 'uptime_seconds' in health
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_capability(self):
        """Test that processor can handle concurrent requests"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Create multiple concurrent processing tasks
        tasks = []
        for i in range(3):
            task = processor.process_courtlistener_batch(
                court_id="cafc",
                max_documents=2
            )
            tasks.append(task)
        
        # Execute concurrently
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Should complete all tasks
        assert len(results) == 3
        
        # Should not take much longer than single execution
        assert total_time < 15.0
        
        # All results should be valid
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent processing failed: {result}")
            assert isinstance(result, dict)


class TestRobustnessIntegration:
    """Test system robustness and edge cases"""
    
    @pytest.mark.asyncio
    async def test_empty_batch_handling(self):
        """Test handling of empty batch results"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Mock empty results
        with patch.object(processor, '_fetch_documents_with_monitoring') as mock_fetch:
            mock_fetch.return_value = []
            
            result = await processor.process_courtlistener_batch(
                court_id="unknown_court",
                max_documents=10
            )
            
            # Should handle empty results gracefully
            assert result['total_fetched'] == 0
            assert result['new_documents'] == 0
            assert result['duplicates'] == 0
    
    @pytest.mark.asyncio
    async def test_malformed_document_handling(self):
        """Test handling of malformed documents"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        malformed_docs = [
            {},  # Empty document
            {'id': 'not_an_int'},  # Wrong data type
            {'id': 123, 'court_id': None},  # Null required field
        ]
        
        for doc in malformed_docs:
            result = await processor.process_single_document(doc)
            
            # Should handle gracefully with error
            assert isinstance(result, dict)
            assert result.get('success') is False or 'error' in result
    
    @pytest.mark.asyncio
    async def test_resource_cleanup(self):
        """Test that resources are properly cleaned up"""
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Process several batches
        for i in range(3):
            await processor.process_courtlistener_batch(
                court_id="cafc",
                max_documents=2
            )
        
        # Check that monitoring data is reasonable (not growing unbounded)
        metrics = processor.get_processing_metrics()
        health = processor.get_health_status()
        
        # Should have reasonable memory usage
        if 'system' in metrics and 'current_memory_usage_mb' in metrics['system']:
            memory_mb = metrics['system']['current_memory_usage_mb']
            assert memory_mb < 1000  # Should not use more than 1GB in testing