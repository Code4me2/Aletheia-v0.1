#!/usr/bin/env node

/**
 * YAKE Node Test Suite
 * Using shared test utilities following the existing pattern
 */

const path = require('path');
const UnifiedTestRunner = require('../../test-utils/common/test-runner');

// Create test runner instance
const runner = new UnifiedTestRunner('YAKE Keyword Extraction Node', {
  showOutput: true,
  stopOnFail: false
});

// Add test files
runner.addTestGroup([
  {
    name: 'Node Structure Validation',
    file: path.join(__dirname, 'unit', 'test-node-structure.js'),
    description: 'Validates node compilation and structure'
  },
  {
    name: 'YAKE Configuration',
    file: path.join(__dirname, 'unit', 'test-config.js'),
    description: 'Validates YAKE node configuration and parameters'
  },
  {
    name: 'Keyword Extraction Logic',
    file: path.join(__dirname, 'unit', 'test-keyword-extraction.js'),
    description: 'Tests keyword extraction with mocked Python subprocess'
  },
  {
    name: 'Python Integration',
    file: path.join(__dirname, 'integration', 'test-python-integration.js'),
    description: 'Tests actual Python YAKE integration (requires Python + YAKE)'
  }
]);

// Run all tests
runner.runAll().then(success => {
  // Export results
  const resultsPath = path.join(__dirname, '..', 'test-results.json');
  runner.exportResults(resultsPath);
  
  // Exit with appropriate code
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});