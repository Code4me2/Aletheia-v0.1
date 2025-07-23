# How to Test the Court Processor Pipeline

## Quick Start

### 1. Set CourtListener API Token (Optional but Recommended)

Add to your `.env` file in the project root:
```
COURTLISTENER_API_TOKEN=f751990518aacab953214f2e56ac6ccbff9e2c14
```

Or set temporarily:
```bash
export COURTLISTENER_API_TOKEN=f751990518aacab953214f2e56ac6ccbff9e2c14
```

### 2. Run the Unified Test Suite

```bash
# Run all tests
docker-compose exec court-processor python test_suite.py
```

This will test:
1. CourtListener API connection
2. CourtListener → Database flow
3. Pipeline processing (11 stages)
4. Haystack storage
5. Complete end-to-end flow

### 3. Check Results

Test results are saved to `test_results.json` with detailed information about each test.

## What the Test Suite Does

### Test 1: CourtListener Connection
- Verifies API is accessible
- Tests with a simple query
- Confirms authentication works

### Test 2: CourtListener → Database
- Fetches real documents from CourtListener
- Stores them in PostgreSQL
- Verifies storage succeeded

### Test 3: Pipeline Processing
- Processes documents through all 11 stages
- Verifies court resolution, citation extraction, etc.
- Reports completeness and quality scores

### Test 4: Haystack Integration
- Checks Haystack service health
- Verifies documents are indexed
- Confirms search functionality

### Test 5: End-to-End Flow
- Complete workflow from API to search
- Fetches → Stores → Processes → Indexes
- Verifies entire system integration

## Individual Component Tests

If you need to test specific components:

```bash
# Test enhanced pipeline only
docker-compose exec court-processor python test_enhanced_pipeline.py

# Run basic pipeline
docker-compose exec court-processor python run_pipeline.py 10

# Check CourtListener setup
docker-compose exec court-processor python check_courtlistener_setup.py
```

## Understanding Results

Good test output shows:
- ✅ All 5 tests passed
- Completeness score > 60%
- Quality score > 50%
- Documents successfully indexed to Haystack

Common issues:
- No API token: Works but rate limited
- Haystack not running: Test 4 will fail
- No data in database: Tests 3-5 will have nothing to process

## Next Steps

After tests pass:
1. Run larger batches: `python run_pipeline.py 100`
2. Monitor performance with different document types
3. Check Haystack search functionality
4. Review error reports for any warnings