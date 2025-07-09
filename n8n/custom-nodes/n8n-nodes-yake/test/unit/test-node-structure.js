/**
 * Node Structure Validation Test for YAKE
 * Using shared NodeValidator utility
 */

const path = require('path');
const NodeValidator = require('../../../test-utils/common/node-validator');

console.log('Testing YAKE Keyword Extraction Node Structure\n');

// Test 1: Validate package.json
console.log('Test 1: Validating package.json configuration...');
const packagePath = path.join(__dirname, '..', '..', 'package.json');
const packageResults = NodeValidator.validatePackageJson(packagePath);
NodeValidator.printResults(packageResults, 'Package.json Validation');

if (!packageResults.valid) {
  process.exit(1);
}

// Test 2: Validate file structure
console.log('\nTest 2: Validating node file structure...');
const nodeDir = path.join(__dirname, '..', '..');
const fileResults = NodeValidator.validateNodeFiles(nodeDir);
NodeValidator.printResults(fileResults, 'File Structure Validation');

if (!fileResults.valid) {
  process.exit(1);
}

// Test 3: Load and validate compiled node
console.log('\nTest 3: Loading and validating compiled YAKE node...');
const nodePath = path.join(__dirname, '..', '..', 'dist', 'nodes', 'yakeKeywordExtraction', 'yakeKeywordExtraction.node.js');
const loadResults = NodeValidator.validateNodeLoading(nodePath);

if (!loadResults.loaded) {
  console.error('❌ Failed to load YAKE node:', loadResults.error);
  console.log('\n💡 Make sure to run "npm run build" first');
  process.exit(1);
}

console.log('✅ YAKE node loaded successfully');
console.log('📦 Module loaded:', !!loadResults.module);
console.log('🔧 Node class found:', !!loadResults.nodeClass);

// Test 4: Validate node structure
console.log('\nTest 4: Validating node class structure...');
const structureResults = NodeValidator.validateNodeStructure(loadResults.nodeClass, {
  checkIcon: false // YAKE may not have icon
});

NodeValidator.printResults(structureResults, 'Node Structure Validation');

if (!structureResults.valid) {
  process.exit(1);
}

// Test 5: Validate YAKE-specific properties
console.log('\nTest 5: Validating YAKE-specific node properties...');
const nodeInstance = new loadResults.nodeClass();
const description = nodeInstance.description;

const yakeTests = {
  valid: true,
  errors: []
};

// Check for required properties
const requiredProperties = ['inputText', 'language', 'maxKeywords', 'ngramSize'];
const propertyNames = description.properties.map(p => p.name);

requiredProperties.forEach(prop => {
  if (!propertyNames.includes(prop)) {
    yakeTests.valid = false;
    yakeTests.errors.push(`Missing required property: ${prop}`);
  }
});

// Check property defaults
const inputTextProp = description.properties.find(p => p.name === 'inputText');
if (inputTextProp && inputTextProp.type !== 'string') {
  yakeTests.valid = false;
  yakeTests.errors.push('inputText should be of type string');
}

const maxKeywordsProp = description.properties.find(p => p.name === 'maxKeywords');
if (maxKeywordsProp && maxKeywordsProp.type !== 'number') {
  yakeTests.valid = false;
  yakeTests.errors.push('maxKeywords should be of type number');
}

NodeValidator.printResults(yakeTests, 'YAKE-specific Properties');

if (!yakeTests.valid) {
  process.exit(1);
}

console.log('\n✅ All structure tests passed!');
process.exit(0);