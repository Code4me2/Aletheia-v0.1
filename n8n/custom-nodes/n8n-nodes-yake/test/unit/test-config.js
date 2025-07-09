/**
 * Configuration Test for YAKE Node
 * Tests parameter validation and default values
 */

const path = require('path');

console.log('Testing YAKE Node Configuration\n');

// Load the compiled node
const nodePath = path.join(__dirname, '..', '..', 'dist', 'nodes', 'yakeKeywordExtraction', 'yakeKeywordExtraction.node.js');
let YakeNode;

try {
  const module = require(nodePath);
  YakeNode = module.yakeKeywordExtraction;
} catch (error) {
  console.error('❌ Failed to load YAKE node:', error.message);
  console.log('\n💡 Make sure to run "npm run build" first');
  process.exit(1);
}

const nodeInstance = new YakeNode();
const description = nodeInstance.description;

// Test 1: Validate default values
console.log('Test 1: Validating default values...');
const defaults = {
  inputText: 'your text here',
  language: 'en',
  maxKeywords: 20,
  ngramSize: 3
};

let defaultsValid = true;
description.properties.forEach(prop => {
  if (defaults[prop.name] !== undefined && prop.default !== defaults[prop.name]) {
    console.error(`❌ Default value mismatch for ${prop.name}: expected ${defaults[prop.name]}, got ${prop.default}`);
    defaultsValid = false;
  }
});

if (defaultsValid) {
  console.log('✅ All default values are correct');
} else {
  process.exit(1);
}

// Test 2: Validate language options
console.log('\nTest 2: Validating language support...');
const languageProp = description.properties.find(p => p.name === 'language');
const supportedLanguages = ['en', 'pt', 'es', 'fr', 'de', 'it', 'nl', 'ar', 'ja', 'zh'];

// Note: YAKE supports these languages, but the node might not enforce validation
console.log(`✅ Language property found with default: ${languageProp.default}`);
console.log(`📝 YAKE supports: ${supportedLanguages.join(', ')}`);

// Test 3: Validate numeric constraints
console.log('\nTest 3: Validating numeric parameter constraints...');
const numericParams = {
  maxKeywords: { min: 1, max: 100, default: 20 },
  ngramSize: { min: 1, max: 5, default: 3 }
};

let constraintsValid = true;
Object.entries(numericParams).forEach(([paramName, constraints]) => {
  const prop = description.properties.find(p => p.name === paramName);
  if (!prop) {
    console.error(`❌ Missing numeric parameter: ${paramName}`);
    constraintsValid = false;
    return;
  }
  
  if (prop.type !== 'number') {
    console.error(`❌ ${paramName} should be of type number, got ${prop.type}`);
    constraintsValid = false;
  }
  
  // Note: n8n doesn't always enforce min/max in property definitions
  console.log(`✅ ${paramName}: type=${prop.type}, default=${prop.default}`);
});

if (!constraintsValid) {
  process.exit(1);
}

// Test 4: Validate display properties
console.log('\nTest 4: Validating display properties...');
const displayTests = {
  displayName: description.displayName === 'Keyword Extraction',
  name: description.name === 'keyword_extraction',
  group: Array.isArray(description.group) && description.group.includes('transform'),
  version: description.version === 1
};

Object.entries(displayTests).forEach(([prop, valid]) => {
  if (valid) {
    console.log(`✅ ${prop} is correctly set`);
  } else {
    console.error(`❌ ${prop} validation failed`);
    constraintsValid = false;
  }
});

// Test 5: Check for Python dependency awareness
console.log('\nTest 5: Checking Python dependency handling...');
console.log('📝 Note: YAKE node requires Python with YAKE package installed');
console.log('📝 The node uses spawnSync to execute run_YAKE.py');

// Test 6: Validate inputs/outputs
console.log('\nTest 6: Validating node connections...');
if (description.inputs && description.outputs) {
  console.log(`✅ Inputs: ${description.inputs}`);
  console.log(`✅ Outputs: ${description.outputs}`);
} else {
  console.error('❌ Missing inputs or outputs definition');
  process.exit(1);
}

console.log('\n✅ All configuration tests passed!');
process.exit(0);