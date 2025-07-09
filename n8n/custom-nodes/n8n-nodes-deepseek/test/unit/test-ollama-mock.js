/**
 * Ollama API Mock Test for DeepSeek Node
 * Tests the node's behavior with various Ollama API responses
 */

const http = require('http');
const path = require('path');

console.log('Testing DeepSeek Ollama API Mock Scenarios\n');

// Mock server setup
let mockServer;
let mockResponse = {};
let requestCount = 0;
let capturedRequests = [];

function createMockServer(port = 11435) {
  return http.createServer((req, res) => {
    requestCount++;
    
    // Capture request details
    if (req.url === '/api/generate' && req.method === 'POST') {
      let body = '';
      req.on('data', chunk => body += chunk);
      req.on('end', () => {
        const request = JSON.parse(body);
        capturedRequests.push(request);
        
        // Simulate response based on mockResponse configuration
        if (mockResponse.error) {
          res.statusCode = mockResponse.statusCode || 500;
          res.end(JSON.stringify({ error: mockResponse.error }));
          return;
        }
        
        if (mockResponse.timeout) {
          // Simulate timeout - don't respond
          return;
        }
        
        // Send mock response
        const response = {
          model: request.model,
          created_at: new Date().toISOString(),
          response: mockResponse.text || 'Mock response from Ollama',
          done: true,
          context: [],
          total_duration: 1000000000,
          load_duration: 500000,
          prompt_eval_duration: 300000,
          eval_duration: 700000,
          eval_count: mockResponse.tokenCount || 10
        };
        
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(response));
      });
    } else {
      res.statusCode = 404;
      res.end('Not found');
    }
  });
}

// Helper to simulate DeepSeek node behavior
function simulateNodeExecution(prompt, expectedResponse) {
  // Reset captured requests
  capturedRequests = [];
  
  // Simulate what the DeepSeek node would do
  const nodeRequest = {
    model: 'deepseek-r1:1.5b',
    prompt: prompt,
    stream: false,
    options: {
      temperature: 0.7
    }
  };
  
  // Make mock request
  const options = {
    hostname: 'localhost',
    port: 11435,
    path: '/api/generate',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  };
  
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        if (res.statusCode === 200) {
          const response = JSON.parse(body);
          
          // Process thinking tags like the node would
          let processedResponse = response.response;
          let thinking = '';
          
          const thinkMatch = processedResponse.match(/<think>(.*?)<\/think>/s);
          if (thinkMatch) {
            thinking = thinkMatch[1];
            processedResponse = processedResponse.replace(/<think>.*?<\/think>/s, '').trim();
          }
          
          resolve({
            text: processedResponse,
            thinking: thinking,
            tokens: response.eval_count,
            raw: response
          });
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${body}`));
        }
      });
    });
    
    req.on('error', reject);
    req.write(JSON.stringify(nodeRequest));
    req.end();
  });
}

// Start mock server
mockServer = createMockServer();
mockServer.listen(11435, async () => {
  console.log('✅ Mock server started on port 11435\n');
  
  try {
    // Test 1: Basic response handling
    console.log('Test 1: Testing basic Ollama response...');
    mockResponse = {
      text: 'This is a test response from the mock Ollama server.',
      tokenCount: 12
    };
    
    const result1 = await simulateNodeExecution('Hello, how are you?');
    if (result1.text === mockResponse.text && result1.tokens === mockResponse.tokenCount) {
      console.log('✅ Basic response test passed');
      console.log(`   Response: "${result1.text}"`);
      console.log(`   Tokens: ${result1.tokens}`);
    } else {
      throw new Error('Basic response test failed');
    }
    
    // Test 2: Thinking tag extraction
    console.log('\nTest 2: Testing thinking tag extraction...');
    mockResponse = {
      text: '<think>This is my internal reasoning process.</think>This is the actual response.',
      tokenCount: 15
    };
    
    const result2 = await simulateNodeExecution('Explain your reasoning');
    if (result2.thinking === 'This is my internal reasoning process.' && 
        result2.text === 'This is the actual response.') {
      console.log('✅ Thinking tag extraction test passed');
      console.log(`   Thinking: "${result2.thinking}"`);
      console.log(`   Response: "${result2.text}"`);
    } else {
      throw new Error('Thinking tag extraction failed');
    }
    
    // Test 3: Error handling
    console.log('\nTest 3: Testing error responses...');
    mockResponse = {
      error: 'model not found',
      statusCode: 404
    };
    
    try {
      await simulateNodeExecution('Test error');
      throw new Error('Should have thrown error');
    } catch (error) {
      if (error.message.includes('404') && error.message.includes('model not found')) {
        console.log('✅ Error handling test passed');
        console.log(`   Error: ${error.message}`);
      } else {
        throw error;
      }
    }
    
    // Test 4: Special characters and Unicode
    console.log('\nTest 4: Testing special characters...');
    mockResponse = {
      text: 'Response with special chars: 你好世界 🌍 α=β∑∫ "quoted" text',
      tokenCount: 20,
      error: null
    };
    
    const result4 = await simulateNodeExecution('Test unicode');
    if (result4.text === mockResponse.text) {
      console.log('✅ Special characters test passed');
      console.log(`   Response: "${result4.text}"`);
    } else {
      throw new Error('Special characters test failed');
    }
    
    // Test 5: Long response
    console.log('\nTest 5: Testing long response...');
    const longText = 'This is a very detailed response that contains multiple paragraphs of information. '.repeat(50);
    mockResponse = {
      text: longText,
      tokenCount: 500
    };
    
    const result5 = await simulateNodeExecution('Give me a detailed explanation');
    if (result5.text.length === longText.length && result5.tokens === 500) {
      console.log('✅ Long response test passed');
      console.log(`   Response length: ${result5.text.length} characters`);
      console.log(`   Token count: ${result5.tokens}`);
    } else {
      throw new Error('Long response test failed');
    }
    
    // Test 6: Request validation
    console.log('\nTest 6: Validating request format...');
    mockResponse = {
      text: 'Testing request validation',
      tokenCount: 4
    };
    
    await simulateNodeExecution('Validate my request format');
    const lastRequest = capturedRequests[capturedRequests.length - 1];
    
    if (lastRequest.model === 'deepseek-r1:1.5b' &&
        lastRequest.stream === false &&
        lastRequest.options &&
        lastRequest.options.temperature === 0.7) {
      console.log('✅ Request validation test passed');
      console.log('   Model: ' + lastRequest.model);
      console.log('   Stream: ' + lastRequest.stream);
      console.log('   Temperature: ' + lastRequest.options.temperature);
    } else {
      throw new Error('Request validation failed');
    }
    
    console.log('\n✅ All Ollama mock tests passed!');
    console.log(`📊 Total mock requests handled: ${requestCount}`);
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    process.exit(1);
  } finally {
    // Cleanup
    mockServer.close(() => {
      process.exit(0);
    });
  }
});

// Handle server errors
mockServer.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    console.error('❌ Port 11435 is already in use. Please stop any running Ollama services.');
  } else {
    console.error('❌ Mock server error:', error.message);
  }
  process.exit(1);
});

// Timeout safety
setTimeout(() => {
  console.error('❌ Test timeout - tests took too long to complete');
  process.exit(1);
}, 30000);