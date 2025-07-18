# Testing Infrastructure Requirements

## Overview

This document outlines the infrastructure requirements to support the comprehensive testing strategy for the unified court document processing pipeline.

## Current Testing Infrastructure

### **Existing Test Files (21 total)**
```
court-processor/
├── test_smoke.py                    # Basic smoke tests
├── test_flp_integration.py         # FLP component testing
├── test_unified_pipeline.py        # Comprehensive pipeline tests
├── test_full_pipeline.py           # Complete FLP pipeline tests
├── test_api_v4.py                  # CourtListener API tests
├── test_pdf_processing.py          # PDF processing tests
├── test_recap_integration.py       # RECAP integration tests
├── test_courtlistener_auth.py      # Authentication tests
├── test_all_search_methods.py      # Search functionality tests
├── test_working_endpoints.py       # Endpoint validation tests
├── test_pdf_access.py              # PDF access tests
├── test_pdf_download.py            # PDF download tests
├── test_pipeline_simple.py         # Simple pipeline tests
├── test_flp_tools_fixed.py         # FLP tools tests
├── test_recap_live.py              # Live RECAP tests
├── test_recap_simple.py            # Simple RECAP tests
├── test_text_extraction.py         # Text extraction tests
├── courtlistener_integration/
│   ├── test_haystack_integration.py
│   ├── test_known_courts.py
│   └── test_recap_api.py
├── scripts/test_processor.py
└── examples/test_legal_enhancements.py
```

### **Test Data Organization**
```
test_data/
├── courtlistener_free/
│   └── courtlistener_free_data.json
├── ip_cases/
│   └── ip_cases_2025-07-16.json
├── opinions_sample.json
├── recap/
│   └── sample_fetched_data.json
├── recap_real/
│   └── recap_real_data.json
└── recap_real_paginated/
    └── recap_paginated_data.json
```

## Required Infrastructure Components

### **1. Test Environment Setup**

#### **Docker Test Environment**
```yaml
# docker-compose.test.yml
version: '3.8'
services:
  test-db:
    image: postgres:15
    environment:
      POSTGRES_DB: test_aletheia
      POSTGRES_USER: test_user
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5432"
    volumes:
      - test_db_data:/var/lib/postgresql/data
      - ./scripts/test_db_init.sql:/docker-entrypoint-initdb.d/init.sql
  
  test-redis:
    image: redis:7
    ports:
      - "6380:6379"
  
  test-elasticsearch:
    image: elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9201:9200"
    volumes:
      - test_es_data:/usr/share/elasticsearch/data
  
  mock-doctor:
    image: mock-server:latest
    ports:
      - "5051:5050"
    volumes:
      - ./test_mocks/doctor_responses.json:/app/responses.json
  
  mock-courtlistener:
    image: mock-server:latest
    ports:
      - "8081:8080"
    volumes:
      - ./test_mocks/courtlistener_responses.json:/app/responses.json

volumes:
  test_db_data:
  test_es_data:
```

#### **Test Database Schema**
```sql
-- scripts/test_db_init.sql
CREATE SCHEMA IF NOT EXISTS test_court_data;
CREATE SCHEMA IF NOT EXISTS test_public;

-- Create test tables with same structure as production
CREATE TABLE test_court_data.opinions_unified (
    id SERIAL PRIMARY KEY,
    cl_id INTEGER,
    court_id VARCHAR(50),
    case_name TEXT,
    -- ... (same as production schema)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create test indexes
CREATE INDEX idx_test_opinions_court_id ON test_court_data.opinions_unified(court_id);
CREATE INDEX idx_test_opinions_cl_id ON test_court_data.opinions_unified(cl_id);
```

### **2. Test Configuration Management**

#### **Central Test Configuration (conftest.py)**
```python
import pytest
import asyncio
import psycopg2
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock
import tempfile
import os

from services.unified_document_processor import UnifiedDocumentProcessor
from services.courtlistener_service import CourtListenerService
from services.flp_integration import FLPIntegration

# Test configuration
TEST_DATABASE_URL = "postgresql://test_user:test_password@localhost:5433/test_aletheia"
TEST_REDIS_URL = "redis://localhost:6380"
TEST_ELASTICSEARCH_URL = "http://localhost:9201"

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_database():
    """Test database connection"""
    conn = psycopg2.connect(TEST_DATABASE_URL)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.fixture(scope="function")
async def clean_database(test_database):
    """Clean database between tests"""
    cursor = test_database.cursor()
    cursor.execute("TRUNCATE test_court_data.opinions_unified CASCADE")
    yield test_database
    cursor.execute("TRUNCATE test_court_data.opinions_unified CASCADE")
    cursor.close()

@pytest.fixture
def test_data_dir():
    """Test data directory"""
    return Path(__file__).parent / "test_data"

@pytest.fixture
def sample_courtlistener_data(test_data_dir):
    """Sample CourtListener data"""
    with open(test_data_dir / "courtlistener_free" / "courtlistener_free_data.json") as f:
        return json.load(f)

@pytest.fixture
def sample_ip_cases(test_data_dir):
    """Sample IP cases data"""
    with open(test_data_dir / "ip_cases" / "ip_cases_2025-07-16.json") as f:
        return json.load(f)

@pytest.fixture
def mock_services():
    """Mock external services"""
    return {
        'doctor': AsyncMock(),
        'courtlistener': AsyncMock(),
        'haystack': AsyncMock(),
        'unstructured': AsyncMock()
    }

@pytest.fixture
async def unified_processor(mock_services):
    """Unified processor with mocked dependencies"""
    processor = UnifiedDocumentProcessor()
    processor.doc_processor = mock_services['doctor']
    processor.cl_service = mock_services['courtlistener']
    processor.haystack_service = mock_services['haystack']
    processor.unstructured = mock_services['unstructured']
    return processor

@pytest.fixture
def temp_pdf_file():
    """Temporary PDF file for testing"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        # Create minimal PDF content
        tmp.write(b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n')
        tmp.flush()
        yield tmp.name
    os.unlink(tmp.name)

@pytest.fixture
def mock_flp_response():
    """Mock FLP enhancement response"""
    return {
        'citations': [
            {
                'citation_string': '123 F.3d 456',
                'reporter': 'F.3d',
                'volume': '123',
                'page': '456',
                'year': '2020'
            }
        ],
        'court_info': {
            'id': 'ca9',
            'name': 'United States Court of Appeals for the Ninth Circuit',
            'jurisdiction': 'Federal'
        },
        'judge_info': {
            'name': 'John Smith',
            'title': 'Circuit Judge'
        }
    }
```

#### **pytest.ini Configuration**
```ini
[pytest]
# Test discovery
testpaths = court-processor
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# Test execution
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --asyncio-mode=auto
    --cov=services
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=80
    --junit-xml=test-results.xml

# Markers
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (>30 seconds)
    requires_api: Tests requiring external API access
    requires_db: Tests requiring database access
    requires_docker: Tests requiring Docker services

# Async configuration
asyncio_mode = auto

# Test timeouts
timeout = 300
timeout_method = thread

# Parallel execution
-n auto
```

### **3. Mock Services Infrastructure**

#### **Mock Doctor Service**
```python
# test_mocks/mock_doctor.py
from fastapi import FastAPI
from pydantic import BaseModel
import json

app = FastAPI()

class MockDocumentResponse(BaseModel):
    content: str
    page_count: int
    extraction_method: str

@app.post("/extract/doc/text/")
async def mock_extract_text(file: bytes = None):
    """Mock Doctor text extraction"""
    return MockDocumentResponse(
        content="Mock extracted text from PDF document",
        page_count=3,
        extraction_method="mock_extraction"
    )

@app.post("/convert/pdf/thumbnails/")
async def mock_generate_thumbnail(file: bytes = None):
    """Mock thumbnail generation"""
    return b"mock_thumbnail_data"

@app.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "mock-doctor"}
```

#### **Mock CourtListener Service**
```python
# test_mocks/mock_courtlistener.py
from fastapi import FastAPI
from typing import Optional
import json

app = FastAPI()

# Load mock data
with open('/app/test_data/courtlistener_responses.json') as f:
    MOCK_RESPONSES = json.load(f)

@app.get("/api/rest/v4/opinions/")
async def mock_opinions(
    court_id: Optional[str] = None,
    date_filed_after: Optional[str] = None,
    page: int = 1
):
    """Mock CourtListener opinions endpoint"""
    return MOCK_RESPONSES.get('opinions', {
        'count': 0,
        'next': None,
        'previous': None,
        'results': []
    })

@app.get("/api/rest/v4/dockets/")
async def mock_dockets(
    court_id: Optional[str] = None,
    date_filed_after: Optional[str] = None
):
    """Mock CourtListener dockets endpoint"""
    return MOCK_RESPONSES.get('dockets', {
        'count': 0,
        'next': None,
        'previous': None,
        'results': []
    })
```

### **4. Test Data Management**

#### **Test Data Factory**
```python
# test_factories/document_factory.py
import factory
from datetime import datetime
from faker import Faker

fake = Faker()

class CourtListenerDocumentFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n)
    court_id = factory.Faker('random_element', elements=['ca9', 'cafc', 'txed', 'nysd'])
    case_name = factory.LazyAttribute(lambda obj: f"{fake.company()} v. {fake.company()}")
    docket_number = factory.LazyAttribute(lambda obj: f"{fake.random_int(10, 99)}-{fake.random_int(1000, 9999)}")
    date_filed = factory.LazyAttribute(lambda obj: fake.date_between(start_date='-2y', end_date='today').isoformat())
    author_str = factory.LazyAttribute(lambda obj: f"{fake.first_name()} {fake.last_name()}")
    plain_text = factory.LazyAttribute(lambda obj: fake.text(max_nb_chars=2000))
    type = factory.Faker('random_element', elements=['opinion', 'order', 'transcript'])
    
class IPCaseFactory(CourtListenerDocumentFactory):
    court_id = factory.Faker('random_element', elements=['cafc', 'txed', 'deld'])
    case_name = factory.LazyAttribute(lambda obj: f"{fake.company()} v. {fake.company()}")
    plain_text = factory.LazyAttribute(lambda obj: f"Patent infringement case involving {fake.word()}. {fake.text(max_nb_chars=1500)}")

class RECAPDocumentFactory(factory.Factory):
    class Meta:
        model = dict
    
    id = factory.Sequence(lambda n: n)
    docket_id = factory.Sequence(lambda n: n)
    document_number = factory.Faker('random_int', min=1, max=999)
    attachment_number = factory.Faker('random_int', min=1, max=50)
    pacer_doc_id = factory.LazyAttribute(lambda obj: f"{fake.random_int(100000, 999999)}")
    is_available = True
    page_count = factory.Faker('random_int', min=1, max=100)
    file_size = factory.Faker('random_int', min=1024, max=10485760)
```

#### **Test Data Fixtures**
```python
# test_fixtures/data_fixtures.py
import pytest
from test_factories.document_factory import (
    CourtListenerDocumentFactory,
    IPCaseFactory,
    RECAPDocumentFactory
)

@pytest.fixture
def sample_courtlistener_docs():
    """Generate sample CourtListener documents"""
    return CourtListenerDocumentFactory.create_batch(10)

@pytest.fixture
def sample_ip_cases():
    """Generate sample IP cases"""
    return IPCaseFactory.create_batch(5)

@pytest.fixture
def sample_recap_docs():
    """Generate sample RECAP documents"""
    return RECAPDocumentFactory.create_batch(8)

@pytest.fixture
def mixed_document_batch():
    """Generate mixed document types"""
    return {
        'opinions': CourtListenerDocumentFactory.create_batch(5),
        'ip_cases': IPCaseFactory.create_batch(3),
        'recap_docs': RECAPDocumentFactory.create_batch(2)
    }
```

### **5. CI/CD Integration**

#### **GitHub Actions Workflow**
```yaml
# .github/workflows/test.yml
name: Test Suite

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.9", "3.10", "3.11"]
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: test_aletheia
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_password
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5433:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6380:6379
      
      elasticsearch:
        image: elasticsearch:8.0.0
        env:
          discovery.type: single-node
          xpack.security.enabled: false
        ports:
          - 9201:9200
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r court-processor/requirements.txt
        pip install -r court-processor/requirements-test.txt
    
    - name: Run unit tests
      run: |
        cd court-processor
        pytest tests/unit/ -v --cov=services --cov-report=xml
    
    - name: Run integration tests
      run: |
        cd court-processor
        pytest tests/integration/ -v --cov=services --cov-append --cov-report=xml
    
    - name: Run end-to-end tests
      run: |
        cd court-processor
        pytest tests/e2e/ -v --cov=services --cov-append --cov-report=xml
      env:
        TEST_DATABASE_URL: postgresql://test_user:test_password@localhost:5433/test_aletheia
        TEST_REDIS_URL: redis://localhost:6380
        TEST_ELASTICSEARCH_URL: http://localhost:9201
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./court-processor/coverage.xml
        flags: unittests
        name: codecov-umbrella
```

### **6. Performance Testing Infrastructure**

#### **Load Testing Setup**
```python
# performance_tests/locustfile.py
from locust import HttpUser, task, between
import json

class CourtProcessorUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Setup test data"""
        self.test_document = {
            "cl_document": {
                "id": 123456,
                "court_id": "ca9",
                "case_name": "Test v. Case",
                "plain_text": "This is a test document for load testing."
            }
        }
    
    @task(3)
    def process_single_document(self):
        """Test single document processing"""
        self.client.post("/process/single", json=self.test_document)
    
    @task(1)
    def process_batch(self):
        """Test batch processing"""
        self.client.post("/process/batch", json={
            "court_id": "ca9",
            "max_documents": 10
        })
    
    @task(2)
    def search_documents(self):
        """Test search functionality"""
        self.client.post("/search", json={
            "query": "patent infringement",
            "filters": {"court_id": "cafc"}
        })
    
    @task(1)
    def health_check(self):
        """Test health endpoint"""
        self.client.get("/health")
```

#### **Performance Benchmarks**
```python
# performance_tests/benchmarks.py
import pytest
import asyncio
import time
from services.unified_document_processor import UnifiedDocumentProcessor

class TestPerformanceBenchmarks:
    
    @pytest.mark.benchmark
    async def test_document_processing_speed(self, benchmark):
        """Benchmark document processing speed"""
        processor = UnifiedDocumentProcessor()
        
        test_doc = {
            "id": 12345,
            "court_id": "ca9",
            "plain_text": "Test document" * 1000
        }
        
        result = await benchmark(processor.process_single_document, test_doc)
        assert result['saved_id'] is not None
    
    @pytest.mark.benchmark
    async def test_batch_processing_throughput(self, benchmark):
        """Benchmark batch processing throughput"""
        processor = UnifiedDocumentProcessor()
        
        async def process_batch():
            return await processor.process_courtlistener_batch(
                max_documents=100
            )
        
        result = await benchmark(process_batch)
        assert result['new_documents'] > 0
```

### **7. Security Testing Infrastructure**

#### **Security Test Configuration**
```python
# security_tests/test_security.py
import pytest
from fastapi.testclient import TestClient
from unified_api import app

client = TestClient(app)

class TestSecurity:
    
    def test_api_authentication(self):
        """Test API authentication requirements"""
        response = client.post("/process/batch", json={})
        assert response.status_code == 401
    
    def test_input_validation(self):
        """Test input validation"""
        malicious_input = {
            "court_id": "'; DROP TABLE opinions; --",
            "max_documents": -1
        }
        response = client.post("/process/batch", json=malicious_input)
        assert response.status_code == 422
    
    def test_rate_limiting(self):
        """Test rate limiting"""
        for i in range(100):
            response = client.get("/health")
            if response.status_code == 429:
                break
        else:
            pytest.fail("Rate limiting not working")
```

### **8. Test Reporting and Monitoring**

#### **Test Results Dashboard**
```python
# test_reporting/dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

def load_test_results():
    """Load test results from various sources"""
    # Load JUnit XML, coverage reports, performance data
    pass

def create_dashboard():
    """Create test results dashboard"""
    st.title("Court Processor Test Dashboard")
    
    # Test coverage metrics
    st.header("Test Coverage")
    # Coverage charts
    
    # Performance metrics
    st.header("Performance Metrics")
    # Performance charts
    
    # Test reliability
    st.header("Test Reliability")
    # Flaky test tracking
```

## Resource Requirements

### **Hardware Requirements**
- **CPU**: 4+ cores for parallel test execution
- **Memory**: 8GB+ RAM for database and services
- **Storage**: 50GB+ for test data and artifacts
- **Network**: Stable internet for external API testing

### **Software Requirements**
- **Python**: 3.9+ with async support
- **PostgreSQL**: 15+ for test database
- **Redis**: 7+ for caching tests
- **Elasticsearch**: 8.0+ for search tests
- **Docker**: For containerized testing

### **Cloud Infrastructure** (Optional)
- **CI/CD**: GitHub Actions or equivalent
- **Test Database**: Managed PostgreSQL instance
- **Artifact Storage**: S3 or equivalent for test artifacts
- **Monitoring**: Application monitoring for test environments

This comprehensive testing infrastructure ensures robust, reliable, and maintainable testing for the unified court document processing pipeline.