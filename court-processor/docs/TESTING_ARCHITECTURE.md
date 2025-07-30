# Court Processor Testing Architecture

## Current State Analysis

### The Problem
We have been creating ad-hoc test files for days, resulting in:
- Multiple redundant test files (cleaned up 23 files, but still disorganized)
- No clear testing strategy
- Repeated testing of the same components
- No end-to-end validation
- Circular debugging of the same issues

### Existing Test Files
1. `test_enhanced_pipeline.py` - Tests document type awareness
2. `test_robust_pipeline.py` - Tests the robust pipeline
3. `test_maximum_pipeline.py` - Analysis script
4. `run_pipeline_test.py` - Basic runner
5. Various scripts in different directories

## Proposed Unified Testing Suite

### Testing Levels

#### 1. Unit Tests (Component Level)
Test individual components in isolation:
- Document type detection
- Court resolution
- Judge extraction  
- Citation extraction
- Reporter normalization
- Keyword extraction
- Each FLP tool integration

#### 2. Integration Tests (Service Level)
Test service interactions:
- CourtListener API → Database
- Database → Pipeline
- Pipeline → Haystack
- Pipeline → PostgreSQL storage

#### 3. End-to-End Tests (Full Flow)
Complete workflow tests:
- CourtListener fetch → Process → Store → Index → Verify

#### 4. Performance Tests
- Batch processing speed
- Memory usage
- API rate limit handling

## Proposed Structure

```
court-processor/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures and configuration
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_document_detection.py
│   │   ├── test_court_resolution.py
│   │   ├── test_judge_extraction.py
│   │   ├── test_citation_extraction.py
│   │   ├── test_flp_tools.py
│   │   └── test_validators.py
│   ├── integration/
│   │   ├── __init__.py
│   │   ├── test_courtlistener_service.py
│   │   ├── test_database_operations.py
│   │   ├── test_pipeline_stages.py
│   │   └── test_haystack_integration.py
│   ├── e2e/
│   │   ├── __init__.py
│   │   ├── test_full_pipeline.py
│   │   ├── test_courtlistener_to_haystack.py
│   │   └── test_real_data_scenarios.py
│   └── performance/
│       ├── __init__.py
│       └── test_batch_processing.py
├── test_suite.py                # Main test runner
└── pytest.ini                   # Pytest configuration
```

## Test Data Strategy

### 1. Fixtures
- Sample documents of each type (opinion, docket, order)
- Mock CourtListener responses
- Known good/bad examples for validation

### 2. Test Database
- Isolated test database
- Pre-populated with test data
- Reset between test runs

### 3. Mock Services
- Mock CourtListener API for offline testing
- Mock Haystack for unit tests
- Real services for integration tests

## Key Test Scenarios

### Scenario 1: CourtListener to Pipeline
```python
async def test_courtlistener_fetch_and_process():
    # 1. Fetch documents from CourtListener
    # 2. Store in database
    # 3. Process through pipeline
    # 4. Verify all stages completed
```

### Scenario 2: Document Type Handling
```python
async def test_document_type_specific_processing():
    # 1. Process opinion document
    # 2. Process docket document
    # 3. Verify type-specific extraction worked
```

### Scenario 3: Error Recovery
```python
async def test_pipeline_error_handling():
    # 1. Introduce failures at each stage
    # 2. Verify graceful handling
    # 3. Verify error reporting
```

## Testing Commands

### Run All Tests
```bash
docker-compose exec court-processor python -m pytest tests/
```

### Run Specific Level
```bash
# Unit tests only
docker-compose exec court-processor python -m pytest tests/unit/

# Integration tests
docker-compose exec court-processor python -m pytest tests/integration/

# End-to-end tests
docker-compose exec court-processor python -m pytest tests/e2e/
```

### Run with Coverage
```bash
docker-compose exec court-processor python -m pytest --cov=. --cov-report=html tests/
```

## Implementation Plan

1. **Phase 1: Structure Setup**
   - Create directory structure
   - Set up pytest configuration
   - Create shared fixtures

2. **Phase 2: Unit Tests**
   - Test each component in isolation
   - Mock all external dependencies
   - Focus on edge cases

3. **Phase 3: Integration Tests**
   - Test service interactions
   - Use test database
   - Verify data flow

4. **Phase 4: End-to-End Tests**
   - Full pipeline validation
   - Real CourtListener API (with test data)
   - Complete verification

## Success Criteria

1. **Coverage**: >80% code coverage
2. **Speed**: Unit tests < 5 seconds, Integration < 30 seconds
3. **Reliability**: No flaky tests
4. **Clarity**: Clear test names and documentation
5. **Maintenance**: Easy to add new tests

## Next Steps

1. Delete remaining redundant test files
2. Create the test directory structure
3. Implement shared fixtures and configuration
4. Migrate existing useful tests to new structure
5. Fill gaps with missing tests
6. Create CI/CD integration

This approach will give us:
- Clear understanding of what's tested
- Confidence in the pipeline
- Fast feedback on changes
- Easy debugging when issues arise
- No more circular testing of the same issues