#!/usr/bin/env node

// Test runner for BitNet node
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

console.log('================================');
console.log('   BitNet Node Test Suite');
console.log('================================\n');

const tests = [
    {
        name: 'Environment Variable Loading',
        file: 'test-env.js',
        description: 'Verifies that environment variables are loaded correctly'
    },
    {
        name: 'Node Functionality',
        file: 'test-node-functionality.js', 
        description: 'Tests compilation, module loading, and path verification'
    }
];

let currentTest = 0;
let passedTests = 0;
let failedTests = 0;

function runTest(index) {
    if (index >= tests.length) {
        // All tests completed
        console.log('\n================================');
        console.log('   Test Summary');
        console.log('================================');
        console.log(`Total tests: ${tests.length}`);
        console.log(`Passed: ${passedTests}`);
        console.log(`Failed: ${failedTests}`);
        console.log('================================\n');
        
        process.exit(failedTests > 0 ? 1 : 0);
        return;
    }

    const test = tests[index];
    console.log(`\n[${index + 1}/${tests.length}] Running: ${test.name}`);
    console.log(`Description: ${test.description}`);
    console.log('----------------------------------------');

    const testPath = path.join(__dirname, test.file);
    
    if (!fs.existsSync(testPath)) {
        console.error(`ERROR: Test file not found: ${testPath}`);
        failedTests++;
        runTest(index + 1);
        return;
    }

    const child = spawn('node', [testPath], {
        stdio: 'inherit',
        cwd: __dirname
    });

    child.on('exit', (code) => {
        if (code === 0) {
            console.log(`\n✓ ${test.name} - PASSED`);
            passedTests++;
        } else {
            console.log(`\n✗ ${test.name} - FAILED (exit code: ${code})`);
            failedTests++;
        }
        
        // Run next test
        runTest(index + 1);
    });

    child.on('error', (error) => {
        console.error(`\n✗ ${test.name} - ERROR: ${error.message}`);
        failedTests++;
        runTest(index + 1);
    });
}

// Start running tests
runTest(0);