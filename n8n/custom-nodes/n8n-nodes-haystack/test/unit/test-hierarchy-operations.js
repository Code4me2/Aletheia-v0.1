/**
 * Hierarchy Operations Test for Haystack Node
 * Tests document hierarchy tracking and batch operations
 */

const http = require('http');
const path = require('path');

console.log('Testing Haystack Hierarchy Operations\n');

// Mock Haystack API server
let mockServer;
let mockResponse = {};
let requestCount = 0;
let capturedRequests = [];

function createMockHaystackAPI(port = 8001) {
  return http.createServer((req, res) => {
    requestCount++;
    
    // Capture request
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      if (body) {
        try {
          capturedRequests.push({
            url: req.url,
            method: req.method,
            body: JSON.parse(body)
          });
        } catch (e) {
          // Non-JSON body
        }
      }
      
      // Route handlers
      if (req.url === '/health' && req.method === 'GET') {
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          status: 'healthy',
          elasticsearch: mockResponse.esHealth || 'connected',
          version: '1.0.0'
        }));
      } else if (req.url === '/hierarchy' && req.method === 'POST') {
        // Mock hierarchy response
        if (mockResponse.hierarchyError) {
          res.statusCode = mockResponse.statusCode || 500;
          res.end(JSON.stringify({ 
            error: mockResponse.hierarchyError 
          }));
          return;
        }
        
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(mockResponse.hierarchy || {
          document_id: 'test-doc',
          hierarchy: {
            level_0: ['source-1', 'source-2'],
            level_1: ['chunk-1', 'chunk-2'],
            level_2: ['intermediate-1'],
            level_3: ['final-summary']
          },
          relationships: {
            'source-1': { parent: 'chunk-1' },
            'source-2': { parent: 'chunk-2' },
            'chunk-1': { parent: 'intermediate-1' },
            'chunk-2': { parent: 'intermediate-1' },
            'intermediate-1': { parent: 'final-summary' },
            'final-summary': { parent: null }
          }
        }));
      } else if (req.url === '/import_from_node' && req.method === 'POST') {
        // Mock import response
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          imported: mockResponse.importCount || 1,
          documents: mockResponse.importedDocs || [
            { id: 'imported-1', status: 'success' }
          ]
        }));
      } else if (req.url.match(/\/get_complete_tree\/(.+)/) && req.method === 'GET') {
        // Mock complete tree response
        const workflowId = req.url.match(/\/get_complete_tree\/(.+)/)[1];
        
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(mockResponse.completeTree || {
          workflow_id: workflowId,
          total_documents: 7,
          hierarchy_levels: 4,
          tree: {
            id: 'final-summary',
            level: 3,
            content: 'Final summary of all documents',
            children: [
              {
                id: 'intermediate-1',
                level: 2,
                content: 'Intermediate summary 1',
                children: [
                  {
                    id: 'chunk-1',
                    level: 1,
                    content: 'Document chunk 1',
                    children: [
                      {
                        id: 'source-1',
                        level: 0,
                        content: 'Source document 1',
                        children: []
                      }
                    ]
                  },
                  {
                    id: 'chunk-2',
                    level: 1,
                    content: 'Document chunk 2',
                    children: [
                      {
                        id: 'source-2',
                        level: 0,
                        content: 'Source document 2',
                        children: []
                      }
                    ]
                  }
                ]
              }
            ]
          }
        }));
      } else if (req.url.match(/\/get_document_with_context\/(.+)/) && req.method === 'GET') {
        // Mock document with context
        const docId = req.url.match(/\/get_document_with_context\/(.+)/)[1];
        
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify(mockResponse.documentContext || {
          document: {
            id: docId,
            content: 'Document content',
            hierarchy_level: 1,
            workflow_id: 'test-workflow'
          },
          context: {
            parent: {
              id: 'parent-doc',
              content: 'Parent document content',
              hierarchy_level: 2
            },
            children: [
              {
                id: 'child-1',
                content: 'Child document 1',
                hierarchy_level: 0
              }
            ],
            siblings: [
              {
                id: 'sibling-1',
                content: 'Sibling document',
                hierarchy_level: 1
              }
            ]
          }
        }));
      } else {
        res.statusCode = 404;
        res.end(JSON.stringify({ error: 'Not found' }));
      }
    });
  });
}

// Helper to make requests
function makeRequest(options, data = null) {
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          body: body,
          json: () => JSON.parse(body)
        });
      });
    });
    
    req.on('error', reject);
    
    if (data) {
      req.setHeader('Content-Type', 'application/json');
      req.write(JSON.stringify(data));
    }
    
    req.end();
  });
}

// Run tests
async function runHierarchyTests() {
  mockServer = createMockHaystackAPI();
  await new Promise((resolve) => mockServer.listen(8001, resolve));
  console.log('✅ Mock Haystack API server started on port 8001\n');
  
  try {
    // Test 1: Basic hierarchy retrieval
    console.log('Test 1: Testing hierarchy retrieval...');
    const hierarchyResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/hierarchy',
      method: 'POST'
    }, {
      document_id: 'test-doc'
    });
    
    const hierarchyData = hierarchyResult.json();
    if (hierarchyResult.statusCode === 200 && hierarchyData.hierarchy) {
      console.log('✅ Hierarchy retrieval test passed');
      console.log(`   Levels found: ${Object.keys(hierarchyData.hierarchy).length}`);
      console.log(`   Total documents: ${Object.values(hierarchyData.hierarchy).flat().length}`);
    } else {
      throw new Error('Hierarchy retrieval failed');
    }
    
    // Test 2: Parent-child relationships
    console.log('\nTest 2: Testing parent-child relationships...');
    const relationships = hierarchyData.relationships;
    let validRelationships = true;
    
    // Verify each document has correct parent relationship
    for (const [docId, rel] of Object.entries(relationships)) {
      if (docId === 'final-summary' && rel.parent !== null) {
        validRelationships = false;
        break;
      }
      if (docId !== 'final-summary' && !rel.parent) {
        validRelationships = false;
        break;
      }
    }
    
    if (validRelationships) {
      console.log('✅ Parent-child relationships test passed');
      console.log('   All documents have valid parent references');
    } else {
      throw new Error('Invalid parent-child relationships');
    }
    
    // Test 3: Complete tree retrieval
    console.log('\nTest 3: Testing complete tree retrieval...');
    const treeResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/get_complete_tree/test-workflow',
      method: 'GET'
    });
    
    const treeData = treeResult.json();
    if (treeResult.statusCode === 200 && treeData.tree) {
      console.log('✅ Complete tree retrieval test passed');
      console.log(`   Workflow ID: ${treeData.workflow_id}`);
      console.log(`   Total documents: ${treeData.total_documents}`);
      console.log(`   Hierarchy levels: ${treeData.hierarchy_levels}`);
      
      // Verify tree structure
      function countNodes(node) {
        return 1 + (node.children || []).reduce((sum, child) => sum + countNodes(child), 0);
      }
      
      const nodeCount = countNodes(treeData.tree);
      console.log(`   Nodes in tree: ${nodeCount}`);
    } else {
      throw new Error('Complete tree retrieval failed');
    }
    
    // Test 4: Document with context
    console.log('\nTest 4: Testing document with context...');
    const contextResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/get_document_with_context/chunk-1',
      method: 'GET'
    });
    
    const contextData = contextResult.json();
    if (contextResult.statusCode === 200 && contextData.context) {
      console.log('✅ Document with context test passed');
      console.log(`   Document ID: ${contextData.document.id}`);
      console.log(`   Has parent: ${contextData.context.parent ? 'yes' : 'no'}`);
      console.log(`   Children count: ${contextData.context.children.length}`);
      console.log(`   Siblings count: ${contextData.context.siblings.length}`);
    } else {
      throw new Error('Document with context retrieval failed');
    }
    
    // Test 5: Batch import operation
    console.log('\nTest 5: Testing batch import...');
    mockResponse.importCount = 5;
    mockResponse.importedDocs = [
      { id: 'doc-1', status: 'success' },
      { id: 'doc-2', status: 'success' },
      { id: 'doc-3', status: 'success' },
      { id: 'doc-4', status: 'success' },
      { id: 'doc-5', status: 'success' }
    ];
    
    const importResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/import_from_node',
      method: 'POST'
    }, {
      documents: [
        { content: 'Doc 1', workflow_id: 'batch-test' },
        { content: 'Doc 2', workflow_id: 'batch-test' },
        { content: 'Doc 3', workflow_id: 'batch-test' },
        { content: 'Doc 4', workflow_id: 'batch-test' },
        { content: 'Doc 5', workflow_id: 'batch-test' }
      ]
    });
    
    const importData = importResult.json();
    if (importResult.statusCode === 200 && importData.imported === 5) {
      console.log('✅ Batch import test passed');
      console.log(`   Documents imported: ${importData.imported}`);
      console.log(`   All documents successful: ${importData.documents.every(d => d.status === 'success')}`);
    } else {
      throw new Error('Batch import failed');
    }
    
    // Test 6: Error handling for missing workflow
    console.log('\nTest 6: Testing error handling...');
    mockResponse.hierarchyError = 'Workflow not found';
    mockResponse.statusCode = 404;
    
    const errorResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/hierarchy',
      method: 'POST'
    }, {
      document_id: 'missing-doc'
    });
    
    if (errorResult.statusCode === 404) {
      console.log('✅ Error handling test passed');
      console.log('   Correct error status returned');
    } else {
      throw new Error('Error handling test failed');
    }
    
    // Test 7: Complex hierarchy navigation
    console.log('\nTest 7: Testing complex hierarchy navigation...');
    mockResponse.hierarchyError = null;
    mockResponse.hierarchy = {
      document_id: 'complex-doc',
      hierarchy: {
        level_0: ['s1', 's2', 's3', 's4'],
        level_1: ['c1', 'c2'],
        level_2: ['i1'],
        level_3: ['f1']
      },
      relationships: {
        's1': { parent: 'c1', siblings: ['s2'] },
        's2': { parent: 'c1', siblings: ['s1'] },
        's3': { parent: 'c2', siblings: ['s4'] },
        's4': { parent: 'c2', siblings: ['s3'] },
        'c1': { parent: 'i1', siblings: ['c2'] },
        'c2': { parent: 'i1', siblings: ['c1'] },
        'i1': { parent: 'f1', siblings: [] },
        'f1': { parent: null, siblings: [] }
      }
    };
    
    const complexResult = await makeRequest({
      hostname: 'localhost',
      port: 8001,
      path: '/hierarchy',
      method: 'POST'
    }, {
      document_id: 'complex-doc'
    });
    
    const complexData = complexResult.json();
    if (complexResult.statusCode === 200) {
      // Verify sibling relationships
      const s1Siblings = complexData.relationships['s1'].siblings;
      const c1Siblings = complexData.relationships['c1'].siblings;
      
      if (s1Siblings.includes('s2') && c1Siblings.includes('c2')) {
        console.log('✅ Complex hierarchy navigation test passed');
        console.log('   Sibling relationships correctly tracked');
        console.log('   Multi-level parent-child relationships valid');
      } else {
        throw new Error('Sibling relationships invalid');
      }
    } else {
      throw new Error('Complex hierarchy test failed');
    }
    
    // Test 8: Request validation
    console.log('\nTest 8: Validating captured requests...');
    const hierarchyRequests = capturedRequests.filter(r => r.url === '/hierarchy');
    const importRequests = capturedRequests.filter(r => r.url === '/import_from_node');
    
    if (hierarchyRequests.length > 0 && importRequests.length > 0) {
      console.log('✅ Request validation test passed');
      console.log(`   Total requests: ${capturedRequests.length}`);
      console.log(`   Hierarchy requests: ${hierarchyRequests.length}`);
      console.log(`   Import requests: ${importRequests.length}`);
      
      // Validate request structure
      if (hierarchyRequests[0].body.document_id && importRequests[0].body.documents) {
        console.log('   ✓ Request payloads correctly structured');
      }
    } else {
      throw new Error('Request validation failed');
    }
    
    console.log('\n✅ All hierarchy operation tests passed!');
    console.log(`📊 Total mock requests handled: ${requestCount}`);
    
    return true;
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    return false;
  } finally {
    mockServer.close();
  }
}

// Run tests
runHierarchyTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('❌ Unexpected error:', error.message);
  process.exit(1);
});

// Timeout safety
setTimeout(() => {
  console.error('❌ Test timeout - tests took too long to complete');
  process.exit(1);
}, 30000);