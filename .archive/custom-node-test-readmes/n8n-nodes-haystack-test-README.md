# Haystack Node Tests

This directory contains the test suite for the Haystack Search n8n custom node, using the shared test utilities.

## Test Structure

```
test/
├── run-tests.js          # Main test runner
├── unit/                 # Unit tests
│   ├── test-node-structure.js  # Node compilation and structure
│   └── test-config.js    # Haystack configuration validation
└── integration/          # Integration tests
    └── test-haystack-api.js # Haystack API and Elasticsearch connectivity
```

## Running Tests

### Run All Tests
```bash
npm test
# or
node test/run-tests.js
```

### Run Specific Test
```bash
# Unit tests
node test/unit/test-node-structure.js
node test/unit/test-config.js

# Integration test (requires services)
node test/integration/test-haystack-api.js
```

## Test Descriptions

### Unit Tests

1. **Node Structure** (`test-node-structure.js`)
   - Validates `package.json` configuration
   - Checks required files exist
   - Loads and validates compiled node
   - Verifies n8n interface implementation
   - Validates all 8 operations are defined
   - Warns about batch_hierarchy implementation issue

2. **Configuration** (`test-config.js`)
   - Validates Haystack API configuration
   - Checks Docker Compose setup
   - Verifies service implementation file
   - Tests for implemented endpoints
   - Checks environment variables

### Integration Tests

1. **Haystack API** (`test-haystack-api.js`)
   - Tests Elasticsearch connectivity
   - Tests Haystack API service
   - Verifies health endpoints
   - Tests document operations
   - Checks search functionality
   - Validates hierarchy endpoints
   - Confirms batch_hierarchy is missing

## Prerequisites

### For Unit Tests
- Node must be built (`npm run build`)
- No external services required

### For Integration Tests
- Elasticsearch must be running (port 9200)
- Haystack API service must be running (port 8000)
- Both services started via Docker Compose

## Setup Instructions

1. **Start Haystack Services**
   ```bash
   cd n8n
   ./start_haystack_services.sh
   ```
   
   Or manually:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.haystack.yml up -d
   ```

2. **Wait for Services**
   - Elasticsearch takes ~30 seconds to initialize
   - Check status: `curl http://localhost:9200/_cluster/health`

3. **Build the Node**
   ```bash
   npm run build
   ```

4. **Run Tests**
   ```bash
   npm test
   ```

## Known Issues

### batch_hierarchy Operation
- The node defines 8 operations
- The service implements only 7 endpoints
- `batch_hierarchy` operation will fail with 404
- This is a known issue documented in CLAUDE.md

## Test Results

Test results are exported to `test-results.json` containing:
- Timestamp
- Summary (passed/failed counts)
- Individual test results
- Test descriptions

## Troubleshooting

### Node Won't Load
- Run `npm run build` to compile TypeScript
- Check for TypeScript errors
- Verify `dist/` directory exists

### Elasticsearch Connection Fails
- Check Docker containers: `docker ps`
- Verify port 9200 is accessible
- Check logs: `docker logs elasticsearch`
- Wait for green/yellow status

### Haystack API Connection Fails
- Ensure haystack_api container is running
- Check port 8000 is accessible
- View logs: `docker logs haystack_api`
- Verify haystack_service.py is running

### Search Returns No Results
- Ensure documents have been imported first
- Check Elasticsearch indices exist
- Verify index mapping is correct

## Service Architecture

The Haystack integration consists of:

1. **Elasticsearch** (Port 9200)
   - Document storage
   - BM25 search
   - Vector search capabilities

2. **Haystack API** (Port 8000)
   - FastAPI service
   - Document processing
   - Search orchestration
   - Hierarchy management

3. **n8n Node**
   - 8 defined operations
   - Connects workflows to Haystack
   - Handles document import/search

## API Documentation

When services are running, view interactive API docs at:
- http://localhost:8000/docs (Swagger UI)
- http://localhost:8000/redoc (ReDoc)

## Environment Variables

Optional configuration:
```bash
# Custom Elasticsearch URL
export ELASTICSEARCH_URL=http://elasticsearch:9200

# Custom Haystack API URL  
export HAYSTACK_API_URL=http://haystack:8000
```