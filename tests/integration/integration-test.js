#!/usr/bin/env node
/**
 * Basic integration test for Data Compose
 */

const http = require('http');

const tests = [
  {
    name: 'Web server responds',
    url: 'http://localhost:8080',
    expectedStatus: 200,
    checkContent: (body) => body.includes('Data Compose')
  },
  {
    name: 'n8n health check',
    url: 'http://localhost:8080/n8n/healthz',
    expectedStatus: 200,
    checkContent: (body) => body.includes('"status":"ok"')
  },
  {
    name: 'Static CSS loads',
    url: 'http://localhost:8080/css/app.css',
    expectedStatus: 200,
    checkContent: (body) => body.includes('--primary-color')
  },
  {
    name: 'JavaScript config loads',
    url: 'http://localhost:8080/js/config.js',
    expectedStatus: 200,
    checkContent: (body) => body.includes('CONFIG')
  }
];

async function runTest(test) {
  return new Promise((resolve) => {
    http.get(test.url, (res) => {
      let body = '';
      res.on('data', (chunk) => body += chunk);
      res.on('end', () => {
        const passed = res.statusCode === test.expectedStatus && 
                      (!test.checkContent || test.checkContent(body));
        
        console.log(`${passed ? '✅' : '❌'} ${test.name} - Status: ${res.statusCode}`);
        if (!passed && test.checkContent) {
          console.log(`   Content check failed`);
        }
        resolve(passed);
      });
    }).on('error', (err) => {
      console.log(`❌ ${test.name} - Error: ${err.message}`);
      resolve(false);
    });
  });
}

async function runAllTests() {
  console.log('🧪 Running integration tests...\n');
  
  let allPassed = true;
  for (const test of tests) {
    const passed = await runTest(test);
    if (!passed) allPassed = false;
  }
  
  console.log('\n' + (allPassed ? '✅ All tests passed!' : '❌ Some tests failed'));
  process.exit(allPassed ? 0 : 1);
}

runAllTests().catch(console.error);