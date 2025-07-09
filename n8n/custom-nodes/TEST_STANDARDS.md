# n8n Custom Nodes Test Standards

## Overview
This document defines the testing standards and conventions for all n8n custom nodes in the Aletheia project. Following these standards ensures consistency, maintainability, and comprehensive test coverage.

## Test Structure

### Directory Organization
```
node-name/
├── test/
│   ├── run-tests.js              # Main test runner
│   ├── unit/                     # Unit tests (no external dependencies)
│   │   ├── test-node-structure.js    # Node validation
│   │   ├── test-config.js            # Configuration tests
│   │   └── test-{feature}.js         # Feature-specific tests
│   ├── integration/              # Integration tests (external dependencies)
│   │   └── test-{integration}.js     # External service tests
│   └── fixtures/                 # Test data (if needed)
│       ├── sample-data.json
│       └── expected-results.json
├── test-results.json            # Test execution results
└── TEST_DOCUMENTATION.md        # Node-specific test documentation
```

## Naming Conventions

### File Names
- Test files: `test-{category}.js` (hyphen-separated, lowercase)
- Main runner: `run-tests.js`
- Documentation: `TEST_DOCUMENTATION.md` (uppercase)

### Test Categories
1. **node-structure** - Validates compilation and n8n interface
2. **config** - Tests parameters and defaults
3. **{feature}** - Feature-specific logic (e.g., keyword-extraction, api-calls)
4. **{service}-integration** - External service tests (e.g., python-integration, ollama-api)

### Test Descriptions
```javascript
// Test suite descriptions - Start with action verb
'Testing {Node Name} {Feature}'
'Validating {Node Name} Configuration'

// Individual test descriptions - Clear and specific
'Test 1: Testing basic {operation}...'
'Test 2: Testing error handling...'
'Test 3: Testing edge cases...'
```

## Test Implementation Standards

### 1. Test Runner Pattern
All nodes must use the shared `UnifiedTestRunner`:

```javascript
#!/usr/bin/env node

const path = require('path');
const UnifiedTestRunner = require('../../test-utils/common/test-runner');

const runner = new UnifiedTestRunner('{Node Name}', {
  showOutput: true,
  stopOnFail: false
});

runner.addTestGroup([
  {
    name: 'Node Structure Validation',
    file: path.join(__dirname, 'unit', 'test-node-structure.js'),
    description: 'Validates node compilation and structure'
  },
  // ... more tests
]);

runner.runAll().then(success => {
  const resultsPath = path.join(__dirname, '..', 'test-results.json');
  runner.exportResults(resultsPath);
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});
```

### 2. Unit Test Standards

#### Node Structure Test
Every node MUST have a structure test:

```javascript
const NodeValidator = require('../../../test-utils/common/node-validator');

console.log('Testing {Node Name} Structure\n');

// Test 1: Validate package.json
const packageResults = NodeValidator.validatePackageJson(packagePath);
NodeValidator.printResults(packageResults, 'Package.json Validation');

// Test 2: Validate file structure
const fileResults = NodeValidator.validateNodeFiles(nodeDir);
NodeValidator.printResults(fileResults, 'File Structure Validation');

// Test 3: Load and validate compiled node
const loadResults = NodeValidator.validateNodeLoading(nodePath);

// Test 4: Validate node structure
const structureResults = NodeValidator.validateNodeStructure(loadResults.nodeClass);

// Test 5: Validate node-specific properties
// Custom validation for node-specific requirements
```

#### Configuration Test
Test all configurable parameters:

```javascript
console.log('Testing {Node Name} Configuration\n');

// Test 1: Validate default values
// Test 2: Validate parameter types
// Test 3: Validate constraints (min/max, options)
// Test 4: Validate display properties
// Test 5: Check dependencies/requirements
```

#### Logic Tests
Mock external dependencies:

```javascript
// Store original functions
const originalFunction = module.function;

// Replace with mock
module.function = mockFunction;

// Run tests
try {
  // Test implementation
} finally {
  // Always restore original
  module.function = originalFunction;
}
```

### 3. Integration Test Standards

Integration tests should:
- Check for dependency availability first
- Exit with success (0) if dependencies are missing
- Provide clear instructions for setup
- Test actual external service interaction

```javascript
console.log('Testing {Service} Integration\n');

// Check dependency availability
if (!dependencyAvailable) {
  console.log('⚠️  {Dependency} not found. Skipping integration tests.');
  console.log('   Install with: {installation command}');
  process.exit(0); // Success - these are optional
}

// Run integration tests
```

### 4. Mock Standards

#### Mock Naming
- Mock functions: `mock{FunctionName}`
- Mock responses: `createMock{Type}Response`
- Mock data: `mock{DataType}`

#### Mock Implementation
```javascript
// Helper function with clear naming
function createMockResponse(input, options = {}) {
  // Realistic mock implementation
  return {
    status: 0,
    data: processedData,
    error: null
  };
}

// Mock external calls
originalModule.externalCall = (args) => {
  // Validate arguments
  if (!validateArgs(args)) {
    return errorResponse;
  }
  // Return realistic response
  return createMockResponse(args);
};
```

## Output Standards

### Console Output Format
```
Testing {Node Name} {Feature}

Test 1: {Test description}...
   Debug - {Key}: {Value} (if needed)
✅ {Test name} passed
   {Additional details}

Test 2: {Test description}...
❌ {Test name} failed
   Error: {Error details}

✅ All {category} tests passed!
```

### Status Indicators
- `✅` - Test passed
- `❌` - Test failed  
- `⚠️` - Warning/skipped
- `📝` - Information note
- `💡` - Helpful tip
- `📦` - Package/module info
- `🔧` - Configuration/setup

### Exit Codes
- `0` - All tests passed (or optional tests skipped)
- `1` - One or more tests failed
- Non-zero - Specific error conditions

## Test Categories

### Required Tests (Unit)
1. **Structure Validation** - MUST have
2. **Configuration Tests** - MUST have
3. **Core Logic Tests** - MUST have (with mocks)

### Optional Tests (Integration)
1. **External Service Tests** - SHOULD have
2. **Performance Tests** - NICE to have
3. **End-to-End Tests** - NICE to have

## Error Handling

### Test Failures
```javascript
if (!condition) {
  console.error('❌ {Test name} failed');
  console.error('   Expected: {expected}');
  console.error('   Actual: {actual}');
  process.exit(1);
}
```

### Exception Handling
```javascript
try {
  // Test code
} catch (error) {
  console.error('❌ Error in {test name}:', error.message);
  // Include helpful debugging info
  console.error('   Stack:', error.stack.split('\n')[1]);
  process.exit(1);
}
```

## Documentation Requirements

Each node should have a `TEST_DOCUMENTATION.md` file containing:

1. **Overview** - What the tests cover
2. **Test Structure** - Directory layout
3. **Running Tests** - Commands and options
4. **Dependencies** - Required external services
5. **Known Issues** - Any limitations or issues
6. **Examples** - Sample test outputs

## CI/CD Integration

### Package.json Scripts
```json
{
  "scripts": {
    "test": "node test/run-tests.js",
    "test:unit": "node test/run-tests.js",
    "test:integration": "RUN_INTEGRATION_TESTS=true node test/run-tests.js",
    "test:quick": "node test/unit/test-node-structure.js"
  }
}
```

### GitHub Actions
```yaml
- name: Test {Node Name}
  run: |
    cd n8n/custom-nodes/{node-name}
    npm install
    npm run build
    npm run test:unit
```

## Best Practices

### 1. Test Independence
- Each test file should be runnable independently
- Tests should not depend on execution order
- Clean up any created resources

### 2. Mock Quality
- Mocks should behave like real services
- Include realistic delays for performance tests
- Simulate both success and failure scenarios

### 3. Output Clarity
- Use consistent formatting
- Include helpful debug information
- Provide actionable error messages

### 4. Maintainability
- Keep tests simple and focused
- Document complex test logic
- Use descriptive variable names

### 5. Performance
- Unit tests should complete in < 5 seconds
- Integration tests should complete in < 30 seconds
- Use timeouts for external calls

## Examples

### Good Test Output
```
Testing YAKE Keyword Extraction Logic

Test 1: Testing basic keyword extraction...
✅ Basic extraction test passed
   Found 5 keywords
   Example: "artificial" with score 0.01
```

### Good Error Message
```
❌ Configuration test failed
   Property 'maxKeywords' has invalid default
   Expected: number (20)
   Actual: string ("20")
   Fix: Update property type in node description
```

## Conclusion

Following these standards ensures:
- Consistent test implementation across all nodes
- Easy maintenance and updates
- Clear, actionable test output
- Proper CI/CD integration
- Comprehensive test coverage

All new nodes MUST follow these standards. Existing nodes should be updated to match these standards when modified.