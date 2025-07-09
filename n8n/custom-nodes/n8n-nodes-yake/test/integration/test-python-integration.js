/**
 * Python Integration Test for YAKE Node
 * Tests actual Python YAKE integration
 * Requires: Python 3 + YAKE package installed
 */

const path = require('path');
const { spawnSync } = require('child_process');
const fs = require('fs');

console.log('Testing YAKE Python Integration\n');

// Check Python availability
console.log('Test 1: Checking Python availability...');
const pythonCheck = spawnSync('python3', ['--version']);

if (pythonCheck.error || pythonCheck.status !== 0) {
  console.log('⚠️  Python 3 not found. Skipping integration tests.');
  console.log('   Install Python 3 to run these tests');
  process.exit(0); // Exit with success - these tests are optional
}

console.log(`✅ Python found: ${pythonCheck.stdout.toString().trim()}`);

// Check YAKE package
console.log('\nTest 2: Checking YAKE package installation...');
const yakeCheck = spawnSync('python3', ['-c', 'import yake; print(yake.__version__)']);

if (yakeCheck.error || yakeCheck.status !== 0) {
  console.log('⚠️  YAKE package not installed.');
  console.log('   Install with: pip install yake');
  process.exit(0); // Exit with success - these tests are optional
}

console.log(`✅ YAKE package found: version ${yakeCheck.stdout.toString().trim()}`);

// Check run_YAKE.py exists
console.log('\nTest 3: Checking run_YAKE.py script...');
const scriptPath = path.join(__dirname, '..', '..', 'run_YAKE.py');

if (!fs.existsSync(scriptPath)) {
  console.error('❌ run_YAKE.py not found at:', scriptPath);
  process.exit(1);
}

console.log('✅ run_YAKE.py found');

// Test actual keyword extraction
console.log('\nTest 4: Testing actual YAKE keyword extraction...');
const testText = "Natural language processing is a subfield of artificial intelligence that focuses on the interaction between computers and humans through natural language. The ultimate objective of NLP is to read, decipher, understand, and make sense of human language in a valuable way.";

const extractionResult = spawnSync('python3', [
  scriptPath,
  '--text', testText,
  '--language', 'en',
  '--max-keywords', '10',
  '--ngram-size', '3'
]);

if (extractionResult.error) {
  console.error('❌ Error running YAKE:', extractionResult.error);
  process.exit(1);
}

if (extractionResult.status !== 0) {
  console.error('❌ YAKE script failed:', extractionResult.stderr.toString());
  process.exit(1);
}

try {
  const keywords = JSON.parse(extractionResult.stdout.toString());
  
  if (!Array.isArray(keywords)) {
    console.error('❌ Expected array of keywords, got:', typeof keywords);
    process.exit(1);
  }
  
  console.log('✅ Extraction successful');
  console.log(`   Found ${keywords.length} keywords:`);
  keywords.slice(0, 5).forEach(kw => {
    console.log(`   - "${kw.keyword}" (score: ${kw.score.toFixed(4)})`);
  });
  
  // Validate keyword structure
  const validStructure = keywords.every(kw => 
    typeof kw.keyword === 'string' && 
    typeof kw.score === 'number' &&
    kw.keyword.length > 0
  );
  
  if (!validStructure) {
    console.error('❌ Invalid keyword structure');
    process.exit(1);
  }
  
} catch (error) {
  console.error('❌ Failed to parse YAKE output:', error);
  console.error('   Output:', extractionResult.stdout.toString());
  process.exit(1);
}

// Test different languages
console.log('\nTest 5: Testing different language support...');
const languageTests = [
  { lang: 'en', text: 'Machine learning algorithms' },
  { lang: 'es', text: 'Los algoritmos de aprendizaje automático' },
  { lang: 'fr', text: 'Les algorithmes d\'apprentissage automatique' },
  { lang: 'pt', text: 'Algoritmos de aprendizado de máquina' }
];

let langTestsPassed = true;
languageTests.forEach(({ lang, text }) => {
  const result = spawnSync('python3', [
    scriptPath,
    '--text', text,
    '--language', lang,
    '--max-keywords', '3'
  ]);
  
  if (result.status === 0) {
    try {
      const keywords = JSON.parse(result.stdout.toString());
      console.log(`   ✅ ${lang}: Found ${keywords.length} keywords`);
    } catch (e) {
      console.error(`   ❌ ${lang}: Failed to parse output`);
      langTestsPassed = false;
    }
  } else {
    console.error(`   ❌ ${lang}: Extraction failed`);
    langTestsPassed = false;
  }
});

if (!langTestsPassed) {
  process.exit(1);
}

// Test edge cases
console.log('\nTest 6: Testing edge cases...');

// Empty text
const emptyResult = spawnSync('python3', [
  scriptPath,
  '--text', '',
  '--language', 'en'
]);

if (emptyResult.status === 0) {
  const keywords = JSON.parse(emptyResult.stdout.toString());
  if (keywords.length === 0) {
    console.log('   ✅ Empty text handled correctly');
  } else {
    console.error('   ❌ Empty text should return no keywords');
    process.exit(1);
  }
}

// Very long text
const longText = 'This is a test sentence. '.repeat(500);
const longResult = spawnSync('python3', [
  scriptPath,
  '--text', longText,
  '--language', 'en',
  '--max-keywords', '20'
]);

if (longResult.status === 0) {
  const keywords = JSON.parse(longResult.stdout.toString());
  console.log(`   ✅ Long text (${longText.length} chars): ${keywords.length} keywords`);
} else {
  console.error('   ❌ Failed to process long text');
  process.exit(1);
}

// Test n-gram sizes
console.log('\nTest 7: Testing different n-gram sizes...');
const ngramSizes = [1, 2, 3, 4, 5];
let ngramTestsPassed = true;

ngramSizes.forEach(size => {
  const result = spawnSync('python3', [
    scriptPath,
    '--text', 'Testing different ngram sizes for keyword extraction',
    '--language', 'en',
    '--ngram-size', size.toString(),
    '--max-keywords', '5'
  ]);
  
  if (result.status === 0) {
    const keywords = JSON.parse(result.stdout.toString());
    const maxWordsInKeyword = Math.max(...keywords.map(k => k.keyword.split(' ').length));
    
    if (maxWordsInKeyword <= size) {
      console.log(`   ✅ N-gram size ${size}: Max words per keyword = ${maxWordsInKeyword}`);
    } else {
      console.error(`   ❌ N-gram size ${size}: Found keyword with ${maxWordsInKeyword} words`);
      ngramTestsPassed = false;
    }
  } else {
    console.error(`   ❌ N-gram size ${size}: Extraction failed`);
    ngramTestsPassed = false;
  }
});

if (!ngramTestsPassed) {
  process.exit(1);
}

// Performance test
console.log('\nTest 8: Performance test...');
const perfText = fs.readFileSync(__filename, 'utf8'); // Use this file as test text
const startTime = Date.now();

const perfResult = spawnSync('python3', [
  scriptPath,
  '--text', perfText,
  '--language', 'en',
  '--max-keywords', '50'
]);

const duration = Date.now() - startTime;

if (perfResult.status === 0) {
  const keywords = JSON.parse(perfResult.stdout.toString());
  console.log(`   ✅ Processed ${perfText.length} characters in ${duration}ms`);
  console.log(`   Extracted ${keywords.length} keywords`);
  
  if (duration > 5000) {
    console.warn('   ⚠️  Processing took longer than 5 seconds');
  }
} else {
  console.error('   ❌ Performance test failed');
  process.exit(1);
}

console.log('\n✅ All Python integration tests passed!');
process.exit(0);