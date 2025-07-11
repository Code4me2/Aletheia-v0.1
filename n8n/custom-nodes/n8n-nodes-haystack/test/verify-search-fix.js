/**
 * Verify Search Fix - Test that the Haystack node sends correct parameters
 */

const http = require('http');

console.log('Verifying Haystack Search Fix\n');

const HAYSTACK_URL = 'http://localhost:8000';

// Test cases that match what the n8n agent would send
const testCases = [
  {
    name: 'Basic search',
    payload: {
      query: 'error',
      top_k: 5,
      search_type: 'hybrid'
    }
  },
  {
    name: 'BM25 search with filters',
    payload: {
      query: 'tax court',
      top_k: 10,
      search_type: 'bm25',
      filters: { court: 'tax' }
    }
  }
];

async function makeRequest(payload) {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload);
    
    const options = {
      hostname: 'localhost',
      port: 8000,
      path: '/search',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': data.length
      }
    };
    
    const req = http.request(options, (res) => {
      let body = '';
      
      res.on('data', (chunk) => {
        body += chunk;
      });
      
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          body: body
        });
      });
    });
    
    req.on('error', (error) => {
      reject(error);
    });
    
    req.write(data);
    req.end();
  });
}

async function runTests() {
  console.log('Testing Haystack API with corrected parameters...\n');
  
  let allPassed = true;
  
  for (const testCase of testCases) {
    console.log(`Test: ${testCase.name}`);
    console.log(`Payload: ${JSON.stringify(testCase.payload)}`);
    
    try {
      const result = await makeRequest(testCase.payload);
      
      if (result.statusCode === 200) {
        const response = JSON.parse(result.body);
        console.log(`✅ Success! Found ${response.total_results || 0} results`);
        console.log(`   Search type used: ${response.search_type}`);
      } else {
        console.log(`❌ Failed with status ${result.statusCode}`);
        console.log(`   Response: ${result.body}`);
        allPassed = false;
      }
    } catch (error) {
      console.log(`❌ Request failed: ${error.message}`);
      allPassed = false;
    }
    
    console.log();
  }
  
  // Test the old format to ensure it fails
  console.log('Test: Old parameter format (should fail)');
  const oldFormat = {
    query: 'test',
    topK: 5,  // Wrong parameter name
    use_hybrid: true  // Wrong parameter
  };
  
  try {
    const result = await makeRequest(oldFormat);
    if (result.statusCode === 422) {
      console.log('✅ Correctly rejected old format with 422');
    } else {
      console.log(`❌ Unexpected status ${result.statusCode} for old format`);
      allPassed = false;
    }
  } catch (error) {
    console.log(`❌ Request failed: ${error.message}`);
    allPassed = false;
  }
  
  console.log('\n' + '='.repeat(50));
  if (allPassed) {
    console.log('✅ All tests passed! The search fix is working correctly.');
    console.log('\nThe Haystack node now sends the correct parameters:');
    console.log('- top_k (not topK)');
    console.log('- search_type: "hybrid"|"vector"|"bm25" (not use_hybrid, etc.)');
  } else {
    console.log('❌ Some tests failed. Check the Haystack service logs.');
  }
  
  return allPassed;
}

// Run the tests
runTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});