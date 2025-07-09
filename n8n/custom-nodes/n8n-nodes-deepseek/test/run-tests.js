#!/usr/bin/env node

/**
 * DeepSeek Node Test Suite
 * Using shared test utilities
 */

const path = require('path');
const UnifiedTestRunner = require('../../test-utils/common/test-runner');

// Create test runner instance
const runner = new UnifiedTestRunner('DeepSeek Node', {
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
    name: 'DeepSeek Configuration',
    file: path.join(__dirname, 'unit', 'test-config.js'),
    description: 'Validates DeepSeek node configuration'
  },
  {
    name: 'Ollama Mock API',
    file: path.join(__dirname, 'unit', 'test-ollama-mock.js'),
    description: 'Tests node behavior with mocked Ollama responses'
  },
  {
    name: 'API Integration',
    file: path.join(__dirname, 'integration', 'test-ollama-api.js'),
    description: 'Tests connection to Ollama API'
  }
]);

// Run all tests
runner.runAll().then(success => {
  // Export results
  const resultsPath = path.join(__dirname, '..', 'test-results.json');
  runner.exportResults(resultsPath);
  
  process.exit(success ? 0 : 1);
});