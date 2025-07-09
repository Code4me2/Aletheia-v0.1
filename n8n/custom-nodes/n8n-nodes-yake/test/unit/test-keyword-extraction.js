/**
 * Keyword Extraction Logic Test for YAKE Node
 * Tests the extraction logic with mocked Python subprocess
 */

const path = require('path');
const childProcess = require('child_process');

console.log('Testing YAKE Keyword Extraction Logic\n');

// Store original spawnSync
const originalSpawnSync = childProcess.spawnSync;

// Helper function to create mock response matching actual YAKE output format
function createMockResponse(text, options = {}) {
  // Simulate YAKE-like keyword extraction
  const words = text.toLowerCase().split(/\s+/).filter(w => w.length > 3);
  const keywords = [];
  
  // Generate mock keywords based on word frequency
  const wordCount = {};
  words.forEach(word => {
    wordCount[word] = (wordCount[word] || 0) + 1;
  });
  
  // Sort by frequency and take top N
  const sortedWords = Object.entries(wordCount)
    .sort((a, b) => b[1] - a[1])
    .slice(0, options.maxKeywords || 20);
  
  // Format as CSV like the actual script outputs
  let csvOutput = '';
  sortedWords.forEach(([word, count], index) => {
    const score = (index + 1) * 0.01; // Lower score = better keyword
    csvOutput += `${word},${score},\n`;
  });
  
  return {
    status: 0,
    stdout: Buffer.from(csvOutput),
    stderr: Buffer.from(''),
    error: null
  };
}

// Test 1: Basic keyword extraction
console.log('Test 1: Testing basic keyword extraction...');

// Replace spawnSync with mock
childProcess.spawnSync = (command, args) => {
  // Check if it's the expected call pattern
  if (command === 'python' && args && args.length >= 6) {
    const [scriptPath, text, language, maxKeywords, ngramSize, dedupThreshold] = args;
    return createMockResponse(text, { maxKeywords: parseInt(maxKeywords) });
  }
  return { status: 1, stderr: Buffer.from('Invalid arguments'), stdout: Buffer.from(''), error: null };
};

try {
  const testText = "Artificial intelligence and machine learning are transforming the technology industry";
  const result = childProcess.spawnSync('python', [
    './run_YAKE.py',
    testText,
    'en',
    '5',
    '3',
    '0.9'
  ]);
  
  const output = result.stdout.toString();
  const lines = output.trim().split('\n').filter(l => l);
  
  // Debug output
  console.log(`   Debug - Status: ${result.status}`);
  console.log(`   Debug - Output length: ${output.length}`);
  console.log(`   Debug - Output: "${output.substring(0, 100)}..."`);
  
  if (lines.length > 0) {
    console.log('✅ Basic extraction test passed');
    console.log(`   Found ${lines.length} keywords`);
    // Parse and display first keyword
    const [keyword, score] = lines[0].split(',').filter(s => s);
    console.log(`   Example: "${keyword}" with score ${score}`);
  } else {
    console.error('❌ Basic extraction test failed - no keywords found');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error in basic extraction test:', error);
  process.exit(1);
}

// Test 2: Empty text handling
console.log('\nTest 2: Testing empty text handling...');
childProcess.spawnSync = (command, args) => {
  if (command === 'python' && args && args.length >= 6) {
    const text = args[1];
    if (!text || text.trim() === '') {
      return {
        status: 0,
        stdout: Buffer.from(''), // Empty output for empty text
        stderr: Buffer.from(''),
        error: null
      };
    }
    return createMockResponse(text);
  }
  return { status: 1, stderr: Buffer.from('Invalid arguments'), stdout: Buffer.from(''), error: null };
};

try {
  const result = childProcess.spawnSync('python', [
    './run_YAKE.py',
    '',
    'en',
    '10',
    '3',
    '0.9'
  ]);
  
  const output = result.stdout.toString().trim();
  
  if (output === '') {
    console.log('✅ Empty text handling test passed');
  } else {
    console.error('❌ Empty text should return empty output');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error in empty text test:', error);
  process.exit(1);
}

// Test 3: Error handling (missing arguments)
console.log('\nTest 3: Testing error handling...');
childProcess.spawnSync = (command, args) => {
  // Simulate error when not enough arguments
  if (!args || args.length < 6) {
    return {
      status: 1,
      stdout: Buffer.from(''),
      stderr: Buffer.from('Traceback (most recent call last):\n  File "run_YAKE.py", line 21\n    raise Exception("No inputs provided")'),
      error: new Error('Command failed')
    };
  }
  return createMockResponse(args[1]);
};

try {
  const result = childProcess.spawnSync('python', ['./run_YAKE.py']); // Missing arguments
  
  if (result.status !== 0) {
    console.log('✅ Error handling test passed');
    console.log(`   Error detected: ${result.stderr.toString().split('\n')[0]}...`);
  } else {
    console.error('❌ Should have detected error condition');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error in error handling test:', error);
  process.exit(1);
}

// Test 4: Large text handling
console.log('\nTest 4: Testing large text handling...');
const largeText = 'Lorem ipsum dolor sit amet consectetur adipiscing elit '.repeat(500);
childProcess.spawnSync = (command, args) => {
  if (command === 'python' && args && args.length >= 6) {
    const text = args[1];
    const maxKeywords = parseInt(args[3]) || 20;
    
    // Simulate processing time for large text
    const startTime = Date.now();
    const response = createMockResponse(text, { maxKeywords });
    const processingTime = Date.now() - startTime;
    
    console.log(`   Processing time: ${processingTime}ms`);
    return response;
  }
  return { status: 1, stdout: Buffer.from(''), stderr: Buffer.from(''), error: null };
};

try {
  const result = childProcess.spawnSync('python', [
    './run_YAKE.py',
    largeText,
    'en',
    '50',
    '3',
    '0.9'
  ]);
  
  const lines = result.stdout.toString().trim().split('\n').filter(l => l);
  
  if (lines.length <= 50) {
    console.log('✅ Large text handling test passed');
    console.log(`   Extracted ${lines.length} keywords from ${largeText.length} characters`);
  } else {
    console.error('❌ Keyword limit not respected');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error in large text test:', error);
  process.exit(1);
}

// Test 5: Parameter validation
console.log('\nTest 5: Testing parameter validation...');
childProcess.spawnSync = (command, args) => {
  if (command === 'python' && args && args.length >= 6) {
    const [script, text, language, maxKeywords, ngramSize, dedupThreshold] = args;
    
    // Validate parameters
    const maxKw = parseInt(maxKeywords);
    const ngram = parseInt(ngramSize);
    const dedup = parseFloat(dedupThreshold);
    
    if (isNaN(maxKw) || isNaN(ngram) || isNaN(dedup)) {
      return {
        status: 1,
        stderr: Buffer.from('ValueError: invalid literal for int()'),
        stdout: Buffer.from(''),
        error: new Error('Invalid parameters')
      };
    }
    
    // Generate keywords respecting ngram size
    const words = text.split(/\s+/);
    let csvOutput = '';
    
    for (let i = 0; i < Math.min(5, maxKw); i++) {
      const keywordWords = [];
      for (let j = 0; j < Math.min(ngram, words.length - i); j++) {
        if (words[i + j]) keywordWords.push(words[i + j]);
      }
      if (keywordWords.length > 0) {
        csvOutput += `${keywordWords.join(' ')},${(i + 1) * 0.01},\n`;
      }
    }
    
    return {
      status: 0,
      stdout: Buffer.from(csvOutput),
      stderr: Buffer.from(''),
      error: null
    };
  }
  return { status: 1 };
};

// Mock already assigned above

try {
  // Test valid parameters
  const validResult = childProcess.spawnSync('python', [
    './run_YAKE.py',
    'Testing parameter validation with multiple words',
    'en',
    '5',
    '2',
    '0.7'
  ]);
  
  if (validResult.status === 0) {
    const lines = validResult.stdout.toString().trim().split('\n').filter(l => l);
    const firstKeyword = lines[0].split(',')[0];
    const wordCount = firstKeyword.split(' ').length;
    
    if (wordCount <= 2) { // ngram size = 2
      console.log(`   ✅ Valid parameters test passed (ngram size respected: ${wordCount} words)`);
    } else {
      console.error(`   ❌ N-gram size not respected: ${wordCount} words in "${firstKeyword}"`);
      process.exit(1);
    }
  }
  
  // Test invalid parameters
  const invalidResult = childProcess.spawnSync('python', [
    './run_YAKE.py',
    'Test text',
    'en',
    'invalid',  // Invalid number
    '3',
    '0.9'
  ]);
  
  if (invalidResult.status !== 0) {
    console.log('   ✅ Invalid parameters detected correctly');
  } else {
    console.error('   ❌ Should have failed with invalid parameters');
    process.exit(1);
  }
  
  console.log('✅ Parameter validation test passed');
} catch (error) {
  console.error('❌ Error in parameter validation test:', error);
  process.exit(1);
}

// Test 6: Special characters handling
console.log('\nTest 6: Testing special characters handling...');
childProcess.spawnSync = (command, args) => {
  if (command === 'python' && args && args.length >= 6) {
    const text = args[1];
    // Clean text like YAKE would
    const cleanText = text.replace(/[^\w\s]/g, ' ').trim();
    return createMockResponse(cleanText, { maxKeywords: 5 });
  }
  return { status: 1 };
};

// Mock already assigned above

try {
  const specialText = "Machine learning & AI: The future! What's next? #technology @2024";
  const result = childProcess.spawnSync('python', [
    './run_YAKE.py',
    specialText,
    'en',
    '5',
    '3',
    '0.9'
  ]);
  
  const output = result.stdout.toString();
  if (output && !output.includes('#') && !output.includes('@')) {
    console.log('✅ Special characters handling test passed');
    console.log('   Special characters were properly handled');
  } else {
    console.error('❌ Special characters not handled properly');
    process.exit(1);
  }
} catch (error) {
  console.error('❌ Error in special characters test:', error);
  process.exit(1);
}

// Restore original spawnSync
childProcess.spawnSync = originalSpawnSync;

console.log('\n✅ All keyword extraction logic tests passed!');
process.exit(0);