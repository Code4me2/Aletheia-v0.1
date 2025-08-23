# BitNet Node Tests

This directory contains the test suite for the BitNet n8n custom node, using the shared test utilities.

## Test Structure

```
test/
├── run-tests.js          # Main test runner
├── unit/                 # Unit tests
│   ├── test-env.js       # Environment configuration validation
│   ├── test-node-structure.js  # Node compilation and structure
│   ├── test-paths.js     # File path validation
│   └── test-server-wrapper.js  # Server wrapper functionality
└── integration/          # Integration tests
    └── test-api.js       # API connectivity tests
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
# Unit tests only
node test/unit/test-env.js
node test/unit/test-node-structure.js

# Integration test (requires running BitNet server)
node test/integration/test-api.js
```

## Test Descriptions

### Unit Tests

1. **Environment Configuration** (`test-env.js`)
   - Validates `.env.bitnet` file exists and loads correctly
   - Checks all required environment variables are set
   - Validates environment variable types and formats
   - Creates example env file if missing

2. **Node Structure** (`test-node-structure.js`)
   - Validates `package.json` configuration
   - Checks required files exist (tsconfig, dist, etc.)
   - Loads and validates compiled node
   - Verifies node implements required n8n interface

3. **File Paths** (`test-paths.js`)
   - Verifies BitNet installation directory exists
   - Checks for server binary in expected locations
   - Validates model file exists and has correct size
   - Reports on additional BitNet files

4. **Server Wrapper** (`test-server-wrapper.js`)
   - Tests BitNetServerWrapper class instantiation
   - Validates configuration loading
   - Tests wrapper methods (getServerUrl, etc.)
   - Validates configuration values

### Integration Tests

1. **API Connectivity** (`test-api.js`)
   - Tests connection to BitNet server
   - Tries multiple endpoint formats
   - Validates response structure
   - Measures performance consistency

## Prerequisites

### For Unit Tests
- BitNet node must be built (`npm run build`)
- `.env.bitnet` file must exist with valid configuration

### For Integration Tests
- BitNet server must be running
- Server must be accessible at configured URL
- Valid model must be loaded

## Environment Setup

Create `.env.bitnet` file:
```env
# BitNet installation directory
BITNET_INSTALLATION_PATH=/path/to/bitnet

# Model file path (relative to installation)
BITNET_MODEL_PATH=models/model.gguf

# Server configuration
BITNET_SERVER_HOST=localhost
BITNET_SERVER_PORT=8080

# Optional: External server URL
BITNET_EXTERNAL_SERVER_URL=http://localhost:8080

# Server parameters
BITNET_CONTEXT_SIZE=512
BITNET_CPU_THREADS=4
BITNET_GPU_LAYERS=0
```

## Test Results

Test results are automatically exported to `test-results.json` after each run, containing:
- Timestamp
- Summary (passed/failed counts)
- Individual test results
- Test descriptions

## Troubleshooting

### Environment Loading Fails
- Check `.env.bitnet` exists in the node directory
- Verify all required variables are set
- Run `node test/unit/test-env.js` for detailed diagnostics

### Node Loading Fails
- Run `npm run build` to compile the node
- Check for TypeScript errors
- Verify `dist/` directory exists

### API Tests Fail
- Ensure BitNet server is running
- Check server is accessible at configured URL
- Try different endpoint formats
- Check firewall/network settings

### Path Validation Fails
- Verify BitNet is installed at configured path
- Check model file exists
- Ensure paths use correct separators for your OS

## Migrating from Old Tests

The tests have been migrated to use shared utilities from `test-utils/`:
- Old custom test runner → `UnifiedTestRunner`
- Manual env loading → `EnvLoader` utility
- Custom validation → `NodeValidator` utility
- Manual API testing → `ApiTester` utility

Old test files in `tests/` directory are preserved but deprecated.