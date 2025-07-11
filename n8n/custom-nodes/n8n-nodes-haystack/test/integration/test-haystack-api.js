/**
 * Haystack API Integration Test
 * Tests connection to Haystack service and Elasticsearch
 */

const ApiTester = require('../../../test-utils/common/api-tester');

console.log('Testing Haystack API Integration\n');

// Service URLs
const HAYSTACK_URL = process.env.HAYSTACK_API_URL || 'http://localhost:8000';
const ELASTICSEARCH_URL = process.env.ELASTICSEARCH_URL || 'http://localhost:9200';

console.log(`Haystack API URL: ${HAYSTACK_URL}`);
console.log(`Elasticsearch URL: ${ELASTICSEARCH_URL}\n`);

async function runTests() {
  let elasticsearchAvailable = false;
  let haystackAvailable = false;

  // Test 1: Elasticsearch connectivity
  console.log('Test 1: Testing Elasticsearch connectivity...');
  const esConnResult = await ApiTester.testConnection(ELASTICSEARCH_URL, {
    retries: 3,
    retryDelay: 2000,
    timeout: 5000
  });
  
  ApiTester.printResults(esConnResult, 'Elasticsearch Connection');
  
  if (esConnResult.connected) {
    elasticsearchAvailable = true;
    
    // Check Elasticsearch health
    const esHealthResult = await ApiTester.testHealthEndpoint(`${ELASTICSEARCH_URL}/_cluster/health`, {
      expectedStatus: 200
    });
    
    if (esHealthResult.success) {
      try {
        const health = JSON.parse(esHealthResult.body);
        console.log('  Cluster name:', health.cluster_name);
        console.log('  Status:', health.status);
        console.log('  Number of nodes:', health.number_of_nodes);
      } catch (e) {
        console.log('  Health info available but not parseable');
      }
    }
  } else {
    console.error('\n⚠️  Elasticsearch not available');
    console.log('  Haystack requires Elasticsearch to function properly');
  }

  // Test 2: Haystack API connectivity
  console.log('\n\nTest 2: Testing Haystack API connectivity...');
  const haystackConnResult = await ApiTester.testConnection(HAYSTACK_URL, {
    retries: 3,
    retryDelay: 2000,
    timeout: 5000
  });
  
  ApiTester.printResults(haystackConnResult, 'Haystack API Connection');
  
  if (!haystackConnResult.connected) {
    console.error('\n❌ Cannot connect to Haystack API');
    console.log('💡 Make sure Haystack service is running:');
    console.log('   cd n8n && ./start_haystack_services.sh');
    return false;
  }
  
  haystackAvailable = true;

  // Test 3: Haystack health endpoint
  console.log('\n\nTest 3: Testing Haystack health endpoint...');
  const healthResult = await ApiTester.testHealthEndpoint(`${HAYSTACK_URL}/health`);
  
  if (healthResult.success) {
    console.log('✅ Haystack health endpoint responding');
    try {
      const healthData = JSON.parse(healthResult.body);
      console.log('  Status:', healthData.status || 'Unknown');
      console.log('  Elasticsearch:', healthData.elasticsearch_connected ? 'Connected' : 'Not connected');
      if (healthData.indices) {
        console.log('  Indices:', Object.keys(healthData.indices).join(', '));
      }
    } catch (e) {
      console.log('  Health data available but format unexpected');
    }
  } else {
    console.log('❌ Health endpoint failed:', healthResult.error);
  }

  // Test 4: API documentation
  console.log('\n\nTest 4: Checking API documentation...');
  const docsResult = await ApiTester.testHealthEndpoint(`${HAYSTACK_URL}/docs`, {
    expectedStatus: 200
  });
  
  if (docsResult.success) {
    console.log('✅ API documentation available at:', `${HAYSTACK_URL}/docs`);
  } else {
    console.log('⚠️  API documentation not accessible');
  }

  // Test 5: Test available endpoints
  console.log('\n\nTest 5: Testing Haystack endpoints...');
  
  const endpoints = [
    {
      name: 'Import endpoint',
      type: 'chat',
      url: `${HAYSTACK_URL}/import_from_node`,
      payload: {
        documents: [{
          content: "Test document",
          metadata: { title: "Test" }
        }],
        workflowId: "test-workflow"
      },
      options: {
        validateResponse: (res) => res && (res.success || res.status === 'success')
      }
    },
    {
      name: 'Search endpoint',
      type: 'chat', 
      url: `${HAYSTACK_URL}/search`,
      payload: {
        query: "test",
        top_k: 5,
        search_type: "hybrid"
      },
      options: {
        validateResponse: (res) => res && (res.documents !== undefined || res.results !== undefined)
      }
    },
    {
      name: 'Hierarchy endpoint',
      type: 'chat',
      url: `${HAYSTACK_URL}/hierarchy`,
      payload: {
        document_id: "test-doc-id"
      },
      options: {
        validateResponse: (res) => res !== null
      }
    }
  ];

  const endpointResults = await ApiTester.runEndpointTests(endpoints);
  ApiTester.printResults(endpointResults, 'Endpoint Tests');

  // Test 6: Check for missing batch_hierarchy endpoint
  console.log('\n\nTest 6: Checking batch_hierarchy endpoint...');
  const batchResult = await ApiTester.testChatEndpoint(
    `${HAYSTACK_URL}/batch_hierarchy`,
    { document_ids: ["test1", "test2"] },
    { timeout: 5000 }
  );
  
  if (batchResult.statusCode === 404 || batchResult.statusCode === 405) {
    console.log('⚠️  Expected: batch_hierarchy endpoint not implemented');
    console.log('  This is a known issue - operation exists in node but not in service');
  } else if (batchResult.success) {
    console.log('✅ Unexpected: batch_hierarchy endpoint is now implemented!');
  }

  // Test 7: Index information
  if (elasticsearchAvailable) {
    console.log('\n\nTest 7: Checking Elasticsearch indices...');
    const indicesResult = await ApiTester.makeRequest(`${ELASTICSEARCH_URL}/_cat/indices?format=json`);
    
    if (indicesResult.statusCode === 200) {
      try {
        const indices = JSON.parse(indicesResult.body);
        const haystackIndices = indices.filter(idx => 
          idx.index.includes('haystack') || 
          idx.index.includes('document') ||
          idx.index.includes('hierarchical')
        );
        
        if (haystackIndices.length > 0) {
          console.log('✅ Found Haystack-related indices:');
          haystackIndices.forEach(idx => {
            console.log(`  - ${idx.index}: ${idx['docs.count']} docs, ${idx['store.size']}`);
          });
        } else {
          console.log('⚠️  No Haystack indices found yet');
          console.log('  Indices will be created when documents are imported');
        }
      } catch (e) {
        console.log('⚠️  Could not parse indices information');
      }
    }
  }

  return haystackAvailable && elasticsearchAvailable;
}

// Run tests
runTests().then(success => {
  console.log('\n' + '='.repeat(50));
  if (success) {
    console.log('✅ Haystack API integration test passed');
    console.log('\n💡 Haystack is ready to use');
    console.log('   - Import documents via n8n workflows');
    console.log('   - Search using BM25, vector, or hybrid search');
    console.log('   - View API docs at:', `${HAYSTACK_URL}/docs`);
    process.exit(0);
  } else {
    console.log('❌ Haystack API integration test failed');
    console.log('\n💡 To fix:');
    console.log('   1. Start services: cd n8n && ./start_haystack_services.sh');
    console.log('   2. Wait for Elasticsearch to initialize (~30 seconds)');
    console.log('   3. Check logs: docker-compose -f docker-compose.haystack.yml logs');
    process.exit(1);
  }
}).catch(error => {
  console.error('❌ Unexpected error:', error.message);
  process.exit(1);
});