"""
Tests for the Unified Document Processing Pipeline
"""
import asyncio
import pytest
import json
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import (
    UnifiedDocumentProcessor,
    DeduplicationManager,
    UnstructuredProcessor
)


class TestDeduplicationManager:
    """Test deduplication functionality"""
    
    def test_hash_generation(self):
        """Test document hash generation"""
        dedup = DeduplicationManager()
        
        doc1 = {
            'court_id': 'ca9',
            'docket_number': '12-34567',
            'case_name': 'Test v. Case',
            'date_filed': '2024-01-01',
            'author_str': 'Judge Smith',
            'plain_text': 'This is test content for the opinion.'
        }
        
        doc2 = doc1.copy()
        doc2['plain_text'] = 'Different content but same metadata'
        
        doc3 = doc1.copy()
        doc3['docket_number'] = '12-34568'
        
        # Same document should produce same hash
        hash1 = dedup.generate_hash(doc1)
        hash1_again = dedup.generate_hash(doc1)
        assert hash1 == hash1_again
        
        # Different content should produce different hash
        hash2 = dedup.generate_hash(doc2)
        assert hash1 != hash2
        
        # Different docket should produce different hash
        hash3 = dedup.generate_hash(doc3)
        assert hash1 != hash3
    
    def test_duplicate_detection(self):
        """Test duplicate detection"""
        dedup = DeduplicationManager()
        
        doc = {
            'court_id': 'ca9',
            'docket_number': '12-34567',
            'case_name': 'Test v. Case',
            'date_filed': '2024-01-01'
        }
        
        # First time should not be duplicate
        assert not dedup.is_duplicate(doc)
        
        # Mark as processed
        dedup.mark_processed(doc)
        
        # Now should be duplicate
        assert dedup.is_duplicate(doc)


class TestUnstructuredProcessor:
    """Test unstructured.io processing"""
    
    @pytest.mark.asyncio
    async def test_process_local_file(self):
        """Test local file processing"""
        processor = UnstructuredProcessor()
        
        # Create test file
        test_content = """
        UNITED STATES COURT OF APPEALS
        
        Case No. 12-34567
        
        PLAINTIFF v. DEFENDANT
        
        This is a test opinion with multiple paragraphs.
        
        The court finds that the plaintiff has standing.
        
        AFFIRMED.
        """
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(test_content)
            f.flush()
            
            result = await processor.process_local_file(f.name)
            
            os.unlink(f.name)
        
        assert 'full_text' in result
        assert 'structured_elements' in result
        assert 'processing_timestamp' in result
        assert 'UNITED STATES COURT OF APPEALS' in result['full_text']


class TestUnifiedDocumentProcessor:
    """Test the main pipeline"""
    
    @pytest.mark.asyncio
    async def test_flp_enhancement(self):
        """Test FLP enhancement step"""
        processor = UnifiedDocumentProcessor()
        
        # Mock FLP integration
        with patch.object(processor.flp_integration, 'extract_citations', 
                         new_callable=AsyncMock) as mock_citations:
            mock_citations.return_value = [
                {
                    'citation_string': '123 F.3d 456',
                    'reporter': 'F.3d',
                    'volume': '123',
                    'page': '456'
                }
            ]
            
            cl_doc = {
                'id': 12345,
                'court_id': 'ca9',
                'plain_text': 'This cites 123 F.3d 456 for authority.',
                'author_id': 123
            }
            
            enhanced = await processor._flp_enhance(cl_doc)
            
            assert 'citations' in enhanced
            assert len(enhanced['citations']) == 1
            assert enhanced['citations'][0]['citation_string'] == '123 F.3d 456'
            assert 'flp_processing_timestamp' in enhanced
    
    @pytest.mark.asyncio
    async def test_process_single_document(self):
        """Test processing a single document"""
        processor = UnifiedDocumentProcessor()
        
        # Mock all external calls
        with patch.object(processor.flp_integration, 'extract_citations', 
                         new_callable=AsyncMock) as mock_citations, \
             patch.object(processor.unstructured, 'process_local_file',
                         new_callable=AsyncMock) as mock_unstructured, \
             patch.object(processor, '_save_to_postgres',
                         new_callable=AsyncMock) as mock_save:
            
            mock_citations.return_value = []
            mock_unstructured.return_value = {
                'full_text': 'Processed text',
                'structured_elements': [],
                'processing_timestamp': datetime.utcnow().isoformat()
            }
            mock_save.return_value = 12345
            
            cl_doc = {
                'id': 67890,
                'court_id': 'ca9',
                'case_name': 'Test v. Case',
                'plain_text': 'Original text content'
            }
            
            result = await processor.process_single_document(cl_doc)
            
            assert result['saved_id'] == 12345
            assert 'structured_elements' in result
            assert mock_citations.called
            assert mock_save.called
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_duplicates(self):
        """Test batch processing with duplicate handling"""
        processor = UnifiedDocumentProcessor()
        
        # Mock CourtListener service
        with patch.object(processor.cl_service, 'fetch_opinions',
                         new_callable=AsyncMock) as mock_fetch:
            
            # Return 3 documents, middle one is duplicate
            mock_fetch.return_value = [
                {'id': 1, 'court_id': 'ca9', 'case_name': 'Case 1'},
                {'id': 2, 'court_id': 'ca9', 'case_name': 'Case 2'},
                {'id': 3, 'court_id': 'ca9', 'case_name': 'Case 3'}
            ]
            
            # Mark document 2 as already processed
            processor.dedup_manager.mark_processed(
                {'id': 2, 'court_id': 'ca9', 'case_name': 'Case 2'}
            )
            
            # Mock other methods
            with patch.object(processor, 'process_single_document',
                             new_callable=AsyncMock) as mock_process:
                mock_process.return_value = {'saved_id': 123}
                
                stats = await processor.process_courtlistener_batch(
                    max_documents=10
                )
                
                assert stats['total_fetched'] == 3
                assert stats['duplicates'] == 1
                assert stats['new_documents'] == 2
                assert mock_process.call_count == 2  # Only non-duplicates


# Integration test
@pytest.mark.asyncio
async def test_full_pipeline_integration():
    """Test the full pipeline with real components where possible"""
    processor = UnifiedDocumentProcessor()
    
    # Create a test document that looks like CourtListener data
    test_doc = {
        'id': 999999,
        'court_id': 'test',
        'docket_number': 'TEST-2024-001',
        'case_name': 'Integration Test v. Pipeline Test',
        'date_filed': '2024-01-15',
        'author_str': 'Test Judge',
        'plain_text': """
        UNITED STATES COURT OF APPEALS
        FOR THE TEST CIRCUIT
        
        No. TEST-2024-001
        
        INTEGRATION TEST, Plaintiff-Appellant,
        v.
        PIPELINE TEST, Defendant-Appellee.
        
        Appeal from the United States District Court
        
        Before: TEST, DEMO, and EXAMPLE, Circuit Judges.
        
        TEST, Circuit Judge:
        
        This case comes before us on appeal from the district court's
        grant of summary judgment. See Fed. R. Civ. P. 56. We review
        de novo. Smith v. Jones, 123 F.3d 456, 459 (9th Cir. 2020).
        
        For the reasons stated herein, we AFFIRM.
        """,
        'type': 'opinion'
    }
    
    # Mock only external services
    with patch.object(processor, '_save_to_postgres',
                     new_callable=AsyncMock) as mock_save:
        mock_save.return_value = 12345
        
        # Process the document
        result = await processor.process_single_document(test_doc)
        
        # Verify results
        assert result.get('saved_id') == 12345
        assert 'citations' in result
        assert any('123 F.3d 456' in c.get('citation_string', '') 
                  for c in result.get('citations', []))
        assert 'structured_elements' in result
        assert result['structured_elements'].get('full_text')
        
        # Verify all processing timestamps
        assert 'flp_processing_timestamp' in result
        assert result['structured_elements'].get('processing_timestamp')


# Run tests
if __name__ == '__main__':
    # Run specific test
    asyncio.run(test_full_pipeline_integration())
    
    # Or run all tests with pytest
    # pytest.main([__file__, '-v'])