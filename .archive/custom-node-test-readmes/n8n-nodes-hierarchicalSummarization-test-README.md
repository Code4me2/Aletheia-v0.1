# Testing the Hierarchical Summarization Node

This directory contains comprehensive tests for the Hierarchical Summarization node.

## Test Structure

```
test/
├── fixtures/          # Test documents (.txt files)
├── unit/             # Unit tests for helper functions
├── integration/      # Integration tests for database operations
├── verify-node.js    # Complete node verification script
└── README.md         # This file
```

## Running Tests

### Prerequisites

1. **PostgreSQL Database**: Tests require a running PostgreSQL instance
2. **Node.js**: Version 18.10 or higher
3. **Dependencies**: Run `npm install` in the parent directory

### Environment Variables

Configure database connection for tests:

```bash
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=postgres
export TEST_DB_USER=postgres
export TEST_DB_PASSWORD=postgres
```

### Test Commands

```bash
# Run all tests
npm test

# Run unit tests only
npm run test:unit

# Run integration tests only
npm run test:integration

# Run verification script (comprehensive test)
npm run test:verify
```

## Test Descriptions

### Unit Tests (`test/unit/helpers.test.js`)

Tests individual helper functions in isolation:
- `estimateTokenCount`: Token counting accuracy
- `splitIntoSentences`: Sentence boundary detection
- `chunkDocument`: Document chunking logic

### Integration Tests (`test/integration/database.test.js`)

Tests database operations:
- Schema creation
- Document insertion and retrieval
- Parent-child relationship management
- Processing status tracking

### Verification Script (`test/verify-node.js`)

Comprehensive end-to-end testing:
1. **Node Structure**: Validates node configuration
2. **Database Connection**: Tests PostgreSQL connectivity
3. **File Reading**: Verifies fixture file access
4. **Helper Functions**: Quick validation of core logic
5. **End-to-End**: Simulates complete document processing

## Test Fixtures

The `fixtures/` directory contains sample documents:
- `doc1.txt`: Standard multi-paragraph document
- `doc2.txt`: Lorem ipsum placeholder text
- `doc3.txt`: Short document for edge case testing

## Expected Test Output

When all tests pass:

```
========================================
Hierarchical Summarization Node Tests
========================================

🔧 Testing Node Structure...
✅ Node structure is valid

📊 Testing Database Connection...
✅ Database connection successful
✅ Required tables exist

📁 Testing File Reading...
✅ Found 3 test files

🧮 Testing Helper Functions...
✅ Token estimation works correctly
✅ Sentence splitting works correctly

🚀 Testing End-to-End Functionality...
✅ End-to-end test completed successfully

========================================
Test Results: 5 passed, 0 failed
========================================

🎉 All tests passed! The node is ready to use.
```

## Troubleshooting

### Database Connection Failed

If you see database connection errors:
1. Ensure PostgreSQL is running
2. Check environment variables
3. Verify database credentials
4. Ensure the database exists

### Tests Time Out

Integration tests have a 10-second timeout. If tests are timing out:
1. Check database performance
2. Ensure network connectivity
3. Consider increasing timeout in `package.json`

### Missing Dependencies

If you see module not found errors:
1. Run `npm install` in the parent directory
2. Ensure all dependencies are installed
3. Check that the node is built (`npm run build`)

## Adding New Tests

To add new tests:

1. **Unit Tests**: Add to `test/unit/` with `.test.js` extension
2. **Integration Tests**: Add to `test/integration/` with `.test.js` extension
3. **Fixtures**: Add `.txt` files to `test/fixtures/`

Follow the existing test patterns for consistency.