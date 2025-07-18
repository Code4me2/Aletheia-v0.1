"""
Test configuration and fixtures for enhanced court document processor
"""
import pytest
import asyncio
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any, List

# Add enhanced module to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'enhanced'))

from enhanced.config.settings import Settings
from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Test settings configuration"""
    settings = Settings()
    settings.environment = "testing"
    settings.debug = True
    
    # Override for testing
    settings.database.host = "localhost"
    settings.database.database = "test_aletheia"
    settings.services.doctor_enabled = False  # Disable for unit testing
    
    return settings


@pytest.fixture
def sample_courtlistener_document():
    """Sample CourtListener document for testing"""
    return {
        'id': 12345,
        'court_id': 'cafc',
        'case_name': 'Test Corp v. Example Inc.',
        'docket_number': '20-1234',
        'date_filed': '2024-01-15',
        'author_str': 'Judge Smith',
        'plain_text': 'This is a test opinion with citations. See Smith v. Jones, 123 F.3d 456 (Fed. Cir. 2020).',
        'type': 'opinion',
        'pdf_url': 'https://example.com/test.pdf'
    }


@pytest.fixture
def sample_ip_case():
    """Sample IP case document"""
    return {
        'id': 67890,
        'court_id': 'txed',
        'case_name': 'Patent Corp v. Infringement LLC',
        'docket_number': '21-5678',
        'date_filed': '2024-02-20',
        'author_str': 'Judge Gilstrap',
        'plain_text': 'Patent infringement case involving claim construction. 35 U.S.C. § 101.',
        'type': 'opinion'
    }


@pytest.fixture
def batch_documents(sample_courtlistener_document, sample_ip_case):
    """Batch of documents for testing"""
    return [sample_courtlistener_document, sample_ip_case]


@pytest.fixture
def mock_citations():
    """Mock citation extraction results"""
    return [
        {
            'citation_string': 'Smith v. Jones, 123 F.3d 456 (Fed. Cir. 2020)',
            'type': 'CaseCitation',
            'reporter': 'F.3d',
            'volume': '123',
            'page': '456',
            'year': '2020'
        },
        {
            'citation_string': '35 U.S.C. § 101',
            'type': 'StatuteCitation',
            'title': '35',
            'section': '101'
        }
    ]


@pytest.fixture
def mock_flp_enhancement_result(mock_citations):
    """Mock FLP enhancement results"""
    return {
        'citations': mock_citations,
        'court_info': {
            'id': 'cafc',
            'name': 'United States Court of Appeals for the Federal Circuit',
            'jurisdiction': 'Federal',
            'standardized': True
        },
        'judge_info': {
            'name': 'Judge Smith',
            'title': 'Circuit Judge'
        },
        'flp_processing_timestamp': '2024-01-15T10:30:00'
    }


@pytest.fixture
def mock_unstructured_result():
    """Mock Unstructured.io processing results"""
    return {
        'full_text': 'Processed document text with structure',
        'structured_elements': [
            {
                'type': 'Title',
                'text': 'Test Case Opinion',
                'metadata': {'level': 1}
            },
            {
                'type': 'NarrativeText',
                'text': 'This is the main content of the opinion.',
                'metadata': {'page': 1}
            }
        ],
        'processing_timestamp': '2024-01-15T10:35:00'
    }


@pytest.fixture
def enhanced_processor(test_settings):
    """Enhanced processor instance for testing"""
    # Create processor with test configuration
    processor = EnhancedUnifiedDocumentProcessor()
    
    # Override settings for testing
    processor.settings = test_settings
    
    return processor


@pytest.fixture
def mock_services():
    """Mock external services"""
    services = {
        'courtlistener': AsyncMock(),
        'doctor': AsyncMock(),
        'flp_integration': AsyncMock(),
        'unstructured': AsyncMock(),
        'database': AsyncMock()
    }
    
    # Configure mock responses
    services['courtlistener'].fetch_opinions.return_value = []
    services['doctor'].extract_text.return_value = {'content': 'extracted text', 'success': True}
    services['flp_integration'].enhance.return_value = {'citations': [], 'success': True}
    services['unstructured'].process.return_value = {'structured_elements': [], 'success': True}
    services['database'].save.return_value = 12345
    
    return services


@pytest.fixture
def temp_pdf_file():
    """Temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Create minimal PDF content
        pdf_content = b'%PDF-1.4\n1 0 obj\n<</Type/Catalog>>\nendobj\nxref\n0 1\n0000000000 65535 f \ntrailer\n<</Size 1/Root 1 0 R>>\nstartxref\n9\n%%EOF'
        tmp.write(pdf_content)
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def test_data_dir():
    """Test data directory"""
    return Path(__file__).parent.parent.parent / "test_data"


@pytest.fixture
def mock_database_connection():
    """Mock database connection"""
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value = cursor
    cursor.fetchone.return_value = [12345]
    return conn


@pytest.fixture
def validation_test_cases():
    """Test cases for validation testing"""
    return {
        'valid_document': {
            'id': 12345,
            'court_id': 'cafc',
            'case_name': 'Valid Test Case',
            'docket_number': '20-1234',
            'date_filed': '2024-01-15'
        },
        'invalid_document_missing_id': {
            'court_id': 'cafc',
            'case_name': 'Missing ID Case'
        },
        'invalid_document_bad_court': {
            'id': 12345,
            'court_id': 'invalid_court',
            'case_name': 'Bad Court Case'
        },
        'invalid_document_bad_date': {
            'id': 12345,
            'court_id': 'cafc',
            'case_name': 'Bad Date Case',
            'date_filed': 'not-a-date'
        }
    }


@pytest.fixture
async def processor_with_mocks(enhanced_processor, mock_services):
    """Enhanced processor with mocked services"""
    # Inject mock services
    enhanced_processor.cl_service = mock_services['courtlistener']
    enhanced_processor.flp_integration = mock_services['flp_integration']
    enhanced_processor.unstructured = mock_services['unstructured']
    
    return enhanced_processor


# Test helpers
def assert_valid_processing_result(result: Dict[str, Any]):
    """Assert that a processing result has expected structure"""
    assert isinstance(result, dict)
    assert 'processing_time' in result or 'saved_id' in result or 'error' in result


def assert_valid_batch_stats(stats: Dict[str, Any]):
    """Assert that batch stats have expected structure"""
    required_fields = ['total_fetched', 'new_documents', 'duplicates', 'errors']
    for field in required_fields:
        assert field in stats
        assert isinstance(stats[field], int)
        assert stats[field] >= 0


def create_mock_response(success: bool = True, **kwargs) -> Dict[str, Any]:
    """Create a mock service response"""
    if success:
        return {'success': True, **kwargs}
    else:
        return {'success': False, 'error': kwargs.get('error', 'Mock error'), **kwargs}