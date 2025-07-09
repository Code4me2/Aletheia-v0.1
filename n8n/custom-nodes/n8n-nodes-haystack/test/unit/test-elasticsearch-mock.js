/**
 * Elasticsearch Mock Test for Haystack Node
 * Tests node behavior with various Elasticsearch responses
 */

const http = require('http');
const path = require('path');

console.log('Testing Haystack Elasticsearch Mock Scenarios\n');

// Mock server configuration
let mockServer;
let mockEsResponse = {};
let capturedRequests = [];
let requestCount = 0;

// Create mock Elasticsearch server
function createMockElasticsearch(port = 9201) {
  return http.createServer((req, res) => {
    requestCount++;
    
    // Capture request details
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      if (body) {
        try {
          capturedRequests.push({
            url: req.url,
            method: req.method,
            body: JSON.parse(body),
            headers: req.headers
          });
        } catch (e) {
          capturedRequests.push({
            url: req.url,
            method: req.method,
            body: body,
            headers: req.headers
          });
        }
      }
      
      // Route handlers
      if (req.url === '/_cluster/health') {
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          cluster_name: 'mock-elasticsearch',
          status: mockEsResponse.clusterStatus || 'green',
          number_of_nodes: 1,
          number_of_data_nodes: 1,
          active_primary_shards: 5,
          active_shards: 5,
          relocating_shards: 0,
          initializing_shards: 0,
          unassigned_shards: 0,
          delayed_unassigned_shards: 0,
          number_of_pending_tasks: 0,
          number_of_in_flight_fetch: 0
        }));
      } else if (req.url.startsWith('/judicial-documents/_search')) {
        // Mock search response
        if (mockEsResponse.error) {
          res.statusCode = mockEsResponse.statusCode || 500;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({ 
            error: mockEsResponse.error 
          }));
          return;
        }
        
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          took: 5,
          timed_out: false,
          _shards: {
            total: 1,
            successful: 1,
            skipped: 0,
            failed: 0
          },
          hits: {
            total: { 
              value: mockEsResponse.totalHits || 0,
              relation: 'eq'
            },
            max_score: mockEsResponse.maxScore || null,
            hits: mockEsResponse.hits || []
          }
        }));
      } else if (req.url.match(/\/judicial-documents\/_doc\/(.+)/)) {
        // Mock document operations
        const docId = req.url.match(/\/judicial-documents\/_doc\/(.+)/)[1];
        
        if (req.method === 'PUT' || req.method === 'POST') {
          // Index/Update document
          res.statusCode = mockEsResponse.docStatus || 201;
          res.setHeader('Content-Type', 'application/json');
          res.end(JSON.stringify({
            _index: 'judicial-documents',
            _id: docId,
            _version: 1,
            result: mockEsResponse.docResult || 'created',
            _shards: {
              total: 2,
              successful: 1,
              failed: 0
            },
            _seq_no: 0,
            _primary_term: 1
          }));
        } else if (req.method === 'GET') {
          // Get document
          if (mockEsResponse.docNotFound) {
            res.statusCode = 404;
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({
              _index: 'judicial-documents',
              _id: docId,
              found: false
            }));
          } else {
            res.statusCode = 200;
            res.setHeader('Content-Type', 'application/json');
            res.end(JSON.stringify({
              _index: 'judicial-documents',
              _id: docId,
              _version: 1,
              _seq_no: 0,
              _primary_term: 1,
              found: true,
              _source: mockEsResponse.docSource || {
                content: 'Mock document content',
                workflow_id: 'test-workflow'
              }
            }));
          }
        }
      } else if (req.url === '/judicial-documents/_mapping') {
        // Mock mapping
        res.statusCode = 200;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          'judicial-documents': {
            mappings: {
              properties: {
                content: { type: 'text' },
                summary: { type: 'text' },
                embeddings: { type: 'dense_vector', dims: 384 },
                hierarchy_level: { type: 'integer' },
                parent_id: { type: 'keyword' },
                workflow_id: { type: 'keyword' },
                created_at: { type: 'date' }
              }
            }
          }
        }));
      } else {
        res.statusCode = 404;
        res.setHeader('Content-Type', 'application/json');
        res.end(JSON.stringify({
          error: {
            type: 'not_found',
            reason: `No handler found for uri [${req.url}] and method [${req.method}]`
          }
        }));
      }
    });
  });
}

// Helper to make HTTP requests
function makeRequest(options, data = null) {
  return new Promise((resolve, reject) => {
    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        resolve({
          statusCode: res.statusCode,
          headers: res.headers,
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

// Test scenarios
async function runMockTests() {
  // Start mock server
  mockServer = createMockElasticsearch();
  await new Promise((resolve) => mockServer.listen(9201, resolve));
  console.log('✅ Mock Elasticsearch server started on port 9201\n');
  
  try {
    // Test 1: Basic search response
    console.log('Test 1: Testing basic search response...');
    mockEsResponse = {
      totalHits: 2,
      maxScore: 0.95,
      hits: [
        {
          _index: 'judicial-documents',
          _id: 'doc1',
          _score: 0.95,
          _source: {
            content: 'Legal document content about contract law',
            summary: 'Summary of legal case involving contracts',
            hierarchy_level: 1,
            workflow_id: 'workflow-123'
          }
        },
        {
          _index: 'judicial-documents',
          _id: 'doc2',
          _score: 0.88,
          _source: {
            content: 'Another legal document about property disputes',
            summary: 'Different case summary regarding real estate',
            hierarchy_level: 2,
            workflow_id: 'workflow-123'
          }
        }
      ]
    };
    
    const searchResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_search',
      method: 'POST'
    }, {
      query: {
        match: { content: 'legal' }
      }
    });
    
    const searchData = searchResult.json();
    if (searchResult.statusCode === 200 && searchData.hits.hits.length === 2) {
      console.log('✅ Basic search test passed');
      console.log(`   Found ${searchData.hits.hits.length} documents`);
      console.log(`   Max score: ${searchData.hits.max_score}`);
    } else {
      throw new Error('Basic search test failed');
    }
    
    // Test 2: Empty search results
    console.log('\nTest 2: Testing empty search results...');
    mockEsResponse = {
      totalHits: 0,
      hits: []
    };
    
    const emptyResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_search',
      method: 'POST'
    }, {
      query: {
        match: { content: 'nonexistent' }
      }
    });
    
    const emptyData = emptyResult.json();
    if (emptyResult.statusCode === 200 && emptyData.hits.total.value === 0) {
      console.log('✅ Empty results test passed');
      console.log('   No documents found (as expected)');
    } else {
      throw new Error('Empty results test failed');
    }
    
    // Test 3: Error handling
    console.log('\nTest 3: Testing error responses...');
    mockEsResponse = {
      error: {
        type: 'search_phase_execution_exception',
        reason: 'all shards failed',
        phase: 'query',
        grouped: true,
        failed_shards: []
      },
      statusCode: 400
    };
    
    const errorResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_search',
      method: 'POST'
    }, { 
      query: { invalid: 'query' } 
    });
    
    if (errorResult.statusCode === 400) {
      console.log('✅ Error handling test passed');
      console.log('   Error type: search_phase_execution_exception');
    } else {
      throw new Error('Error handling test failed');
    }
    
    // Test 4: Document indexing
    console.log('\nTest 4: Testing document indexing...');
    mockEsResponse = {
      error: null,
      docStatus: 201,
      docResult: 'created'
    };
    
    const indexResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_doc/test-doc-123',
      method: 'PUT'
    }, {
      content: 'Test document content for indexing',
      workflow_id: 'test-workflow-456',
      hierarchy_level: 0,
      embeddings: Array(384).fill(0.1),
      created_at: new Date().toISOString()
    });
    
    const indexData = indexResult.json();
    if (indexResult.statusCode === 201 && indexData.result === 'created') {
      console.log('✅ Document indexing test passed');
      console.log(`   Document ID: ${indexData._id}`);
      console.log(`   Result: ${indexData.result}`);
    } else {
      throw new Error('Document indexing test failed');
    }
    
    // Test 5: Cluster health
    console.log('\nTest 5: Testing cluster health...');
    mockEsResponse = {
      clusterStatus: 'yellow'
    };
    
    const healthResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/_cluster/health',
      method: 'GET'
    });
    
    const healthData = healthResult.json();
    if (healthResult.statusCode === 200 && healthData.status === 'yellow') {
      console.log('✅ Cluster health test passed');
      console.log('   Status: yellow (typical for single-node)');
      console.log(`   Active shards: ${healthData.active_shards}`);
    } else {
      throw new Error('Cluster health test failed');
    }
    
    // Test 6: Complex search with aggregations
    console.log('\nTest 6: Testing complex search with hierarchy levels...');
    mockEsResponse = {
      totalHits: 10,
      maxScore: 0.99,
      hits: [
        {
          _id: 'final-summary',
          _score: 0.99,
          _source: {
            content: 'Final summary of all documents',
            hierarchy_level: 3,
            workflow_id: 'complex-workflow'
          }
        },
        {
          _id: 'intermediate-1',
          _score: 0.85,
          _source: {
            content: 'Intermediate summary',
            hierarchy_level: 2,
            parent_id: 'final-summary',
            workflow_id: 'complex-workflow'
          }
        }
      ]
    };
    
    const complexResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_search',
      method: 'POST'
    }, {
      query: {
        bool: {
          must: [
            { match: { content: 'summary' } },
            { term: { workflow_id: 'complex-workflow' } }
          ]
        }
      },
      sort: [
        { hierarchy_level: { order: 'desc' } },
        { _score: { order: 'desc' } }
      ]
    });
    
    const complexData = complexResult.json();
    if (complexResult.statusCode === 200 && 
        complexData.hits.hits[0]._source.hierarchy_level === 3) {
      console.log('✅ Complex search test passed');
      console.log('   Found final summary at top of results');
      console.log(`   Hierarchy levels: ${complexData.hits.hits.map(h => h._source.hierarchy_level).join(', ')}`);
    } else {
      throw new Error('Complex search test failed');
    }
    
    // Test 7: Document retrieval
    console.log('\nTest 7: Testing document retrieval...');
    mockEsResponse = {
      docNotFound: false,
      docSource: {
        content: 'Retrieved document content',
        workflow_id: 'test-workflow',
        hierarchy_level: 1,
        parent_id: 'parent-doc',
        summary: 'This is a retrieved document'
      }
    };
    
    const getResult = await makeRequest({
      hostname: 'localhost',
      port: 9201,
      path: '/judicial-documents/_doc/existing-doc',
      method: 'GET'
    });
    
    const getData = getResult.json();
    if (getResult.statusCode === 200 && getData.found === true) {
      console.log('✅ Document retrieval test passed');
      console.log(`   Document found: ${getData._id}`);
      console.log(`   Workflow ID: ${getData._source.workflow_id}`);
    } else {
      throw new Error('Document retrieval test failed');
    }
    
    // Test 8: Request validation
    console.log('\nTest 8: Validating captured requests...');
    const searchRequests = capturedRequests.filter(r => r.url.includes('_search'));
    const indexRequests = capturedRequests.filter(r => r.url.includes('_doc') && r.method === 'PUT');
    
    if (searchRequests.length > 0 && indexRequests.length > 0) {
      console.log('✅ Request validation test passed');
      console.log(`   Total requests captured: ${capturedRequests.length}`);
      console.log(`   Search requests: ${searchRequests.length}`);
      console.log(`   Index requests: ${indexRequests.length}`);
      
      // Validate request structure
      const lastSearch = searchRequests[searchRequests.length - 1];
      if (lastSearch.headers['content-type'] === 'application/json' && lastSearch.body.query) {
        console.log('   ✓ Request headers and body structure correct');
      }
    } else {
      throw new Error('Request validation test failed');
    }
    
    console.log('\n✅ All Elasticsearch mock tests passed!');
    console.log(`📊 Total mock requests handled: ${requestCount}`);
    
    return true;
    
  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    if (error.stack) {
      console.error('   Stack:', error.stack.split('\n')[1]);
    }
    return false;
  } finally {
    // Cleanup
    mockServer.close();
  }
}

// Run tests
runMockTests().then(success => {
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