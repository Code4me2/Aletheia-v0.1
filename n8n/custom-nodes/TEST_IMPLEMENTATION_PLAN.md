# Test Suite Implementation Plan for n8n Custom Nodes

## Overview
This plan outlines the implementation of comprehensive test suites for all custom n8n nodes (excluding BitNet). The goal is to ensure robust testing coverage using both n8n-specific testing and core technology testing where appropriate.

## Node Testing Status

| Node | Current Status | Priority | Effort |
|------|---------------|----------|--------|
| YAKE | ❌ No tests | High | Medium |
| Hierarchical Summarization | ✅ Has tests (Mocha) | Medium | Low (migration) |
| DeepSeek | ✅ Has tests (unified) | Low | Low (enhancement) |
| Haystack | ✅ Has tests (unified) | Low | Low (enhancement) |

## Implementation Strategy

### Phase 1: YAKE Node Test Suite (Priority: High)

#### 1.1 Create Test Infrastructure
```bash
n8n-nodes-yake/
├── test/
│   ├── run-tests.js          # Main test runner
│   ├── unit/
│   │   ├── test-node-structure.js
│   │   ├── test-config.js
│   │   └── test-keyword-extraction.js
│   ├── integration/
│   │   ├── test-python-integration.js
│   │   └── test-yake-processing.js
│   └── fixtures/
│       ├── sample-texts.json
│       └── expected-results.json
```

#### 1.2 Unit Tests for YAKE
- **Node Structure Validation**
  - Verify node exports correct interface
  - Validate property definitions
  - Check default values
  
- **Configuration Tests**
  - Parameter validation (language, ngram_size, etc.)
  - Error handling for invalid configs
  
- **Keyword Processing Logic**
  - Mock Python subprocess calls
  - Test input sanitization
  - Verify output parsing

#### 1.3 Integration Tests for YAKE
- **Python Integration**
  - Verify Python installation
  - Test YAKE package availability
  - Handle missing dependencies gracefully
  
- **End-to-End Processing**
  - Test with various text samples
  - Verify keyword extraction accuracy
  - Performance benchmarking

#### 1.4 Implementation Code
```javascript
// test/run-tests.js
const UnifiedTestRunner = require('../../test-utils/UnifiedTestRunner');
const path = require('path');

const runner = new UnifiedTestRunner({
    nodePackagePath: path.resolve(__dirname, '..'),
    nodeName: 'YAKE Keyword Extraction',
    testCategories: {
        structure: true,
        config: true,
        integration: true
    }
});

runner.run();
```

### Phase 2: Migrate Hierarchical Summarization Tests (Priority: Medium)

#### 2.1 Migration Strategy
- Keep existing comprehensive tests
- Wrap in unified test runner format
- Add shared utility integration

#### 2.2 Test Structure Update
```javascript
// test/run-tests.js (new)
const UnifiedTestRunner = require('../../test-utils/UnifiedTestRunner');
const MochaAdapter = require('../../test-utils/MochaAdapter');

const runner = new UnifiedTestRunner({
    nodePackagePath: path.resolve(__dirname, '..'),
    nodeName: 'Hierarchical Summarization',
    testCategories: {
        structure: true,
        config: true,
        database: true,
        aiConnection: true,
        resilience: true
    },
    customTests: [
        './test/unit/*.test.js',
        './test/integration/*.test.js'
    ],
    adapter: new MochaAdapter()
});
```

#### 2.3 Add New Test Categories
- **Resilience Testing**
  - Circuit breaker functionality
  - Retry logic validation
  - Rate limiting tests
  
- **Database Migration Tests**
  - Schema update verification
  - Backward compatibility

### Phase 3: Enhance Existing Test Suites (Priority: Low)

#### 3.1 DeepSeek Node Enhancements
- **Mock Ollama Server Tests**
  ```javascript
  // test/mocks/ollama-mock-server.js
  const express = require('express');
  const app = express();
  
  app.post('/api/generate', (req, res) => {
      // Mock responses for different scenarios
  });
  ```

- **Thinking Tag Extraction Tests**
  - Various thinking tag formats
  - Nested tag handling
  - Performance with large responses

#### 3.2 Haystack Node Enhancements
- **Mock Elasticsearch Tests**
  - Search result ranking validation
  - Error handling for ES downtime
  
- **Document Processing Tests**
  - Large document handling
  - Metadata preservation
  - Hierarchy tracking

### Phase 4: Cross-Node Integration Tests

#### 4.1 Workflow Integration Tests
```javascript
// test/workflow-integration/
├── test-deepseek-to-haystack.js
├── test-hierarchical-to-haystack.js
└── test-yake-to-haystack.js
```

#### 4.2 Performance Benchmarks
```javascript
// test/benchmarks/
├── node-performance.js
├── memory-usage.js
└── throughput-tests.js
```

## Testing Infrastructure Improvements

### 1. Shared Mock Services
```javascript
// test-utils/mocks/
├── MockAIService.js      // Generic AI service mock
├── MockDatabase.js       // Database connection mock
├── MockElasticsearch.js  // ES mock
└── MockPythonProcess.js  // Python subprocess mock
```

### 2. Test Data Management
```javascript
// test-utils/data/
├── TextSamples.js        // Various text samples
├── DocumentHierarchies.js // Complex document structures
└── ExpectedResults.js    // Ground truth data
```

### 3. CI/CD Integration
```yaml
# .github/workflows/test-custom-nodes.yml
name: Test Custom Nodes
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
      elasticsearch:
        image: elasticsearch:8.11.0
    steps:
      - uses: actions/checkout@v3
      - name: Setup Node.js
        uses: actions/setup-node@v3
      - name: Setup Python
        uses: actions/setup-python@v4
      - name: Install dependencies
        run: |
          npm install
          pip install yake
      - name: Run all tests
        run: npm run test:all
```

## Implementation Timeline

### Week 1-2: YAKE Test Suite
- Day 1-2: Set up test infrastructure
- Day 3-5: Implement unit tests
- Day 6-8: Implement integration tests
- Day 9-10: Documentation and cleanup

### Week 3: Hierarchical Summarization Migration
- Day 1-2: Create adapter for existing tests
- Day 3-4: Add resilience tests
- Day 5: Integration with unified runner

### Week 4: Enhancement Phase
- Day 1-2: DeepSeek enhancements
- Day 3-4: Haystack enhancements
- Day 5: Cross-node integration tests

### Week 5: Infrastructure and CI/CD
- Day 1-2: Shared mock services
- Day 3-4: CI/CD pipeline setup
- Day 5: Documentation and training

## Success Metrics

1. **Code Coverage**: Minimum 80% for all nodes
2. **Test Execution Time**: < 5 minutes for full suite
3. **Mock Independence**: All tests runnable without external services
4. **Documentation**: Complete test documentation for each node
5. **CI/CD Integration**: All tests running in automated pipeline

## Testing Best Practices

### 1. Test Naming Convention
```javascript
describe('NodeName', () => {
    describe('Operation: operationName', () => {
        it('should handle valid input correctly', () => {});
        it('should throw error for invalid input', () => {});
        it('should handle edge case: description', () => {});
    });
});
```

### 2. Mock Strategy
- Use dependency injection where possible
- Create reusable mock services
- Ensure mocks are realistic

### 3. Performance Testing
- Include performance benchmarks
- Set performance regression thresholds
- Monitor memory usage

### 4. Documentation
- Document test scenarios
- Include examples in test files
- Maintain test data documentation

## Maintenance Plan

1. **Regular Reviews**: Monthly test suite reviews
2. **Coverage Monitoring**: Automated coverage reports
3. **Performance Tracking**: Benchmark result tracking
4. **Dependency Updates**: Quarterly dependency updates
5. **Test Refactoring**: Continuous improvement based on failures

## Conclusion

This comprehensive test plan ensures all custom n8n nodes have robust, maintainable test suites. The phased approach prioritizes nodes without tests while enhancing existing test infrastructure. The unified testing framework promotes consistency and reduces maintenance overhead.