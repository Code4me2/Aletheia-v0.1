# Test Suite Implementation Plan v2 for n8n Custom Nodes (TypeScript-First)

## Overview
This revised plan provides a realistic, TypeScript-first approach to implementing comprehensive test suites for all custom n8n nodes (excluding BitNet). The plan addresses infrastructure gaps, reduces external dependencies, and provides a more achievable timeline.

## Current State Analysis

| Node | Test Status | Language | External Dependencies |
|------|------------|----------|----------------------|
| YAKE | ❌ No tests | TypeScript | Python subprocess |
| Hierarchical Summarization | ✅ Has Mocha tests | TypeScript | PostgreSQL, AI service |
| DeepSeek | ✅ Has basic tests | TypeScript | Ollama API |
| Haystack | ✅ Has basic tests | TypeScript | Elasticsearch |

## Revised Implementation Strategy

### Phase 0: Foundation Setup (Week 1-2) - **CRITICAL**

#### Create Shared Test Infrastructure
```typescript
// test-utils/src/index.ts
export { TestRunner } from './TestRunner';
export { NodeTestHelper } from './NodeTestHelper';
export { MockFactory } from './mocks/MockFactory';
export * from './types';
```

#### TypeScript Test Type Definitions
```typescript
// test-utils/src/types/index.ts
import { IExecuteFunctions, INodeExecutionData, INodeType } from 'n8n-workflow';

export interface TestContext {
  execute: IExecuteFunctions;
  node: INodeType;
  inputData: INodeExecutionData[];
}

export interface TestSuite {
  name: string;
  tests: TestCase[];
  beforeAll?: () => Promise<void>;
  afterAll?: () => Promise<void>;
}

export interface TestCase {
  name: string;
  run: (context: TestContext) => Promise<void>;
  timeout?: number;
}

export interface MockConfig {
  pythonProcess?: MockPythonConfig;
  httpRequest?: MockHttpConfig;
  database?: MockDatabaseConfig;
}
```

#### Core Test Runner Implementation
```typescript
// test-utils/src/TestRunner.ts
import { INodeType, INodeTypeDescription } from 'n8n-workflow';
import { TestSuite, TestContext } from './types';

export class TestRunner {
  private suites: TestSuite[] = [];
  private mockConfig: MockConfig;

  constructor(private nodeType: INodeType) {
    this.mockConfig = {};
  }

  addSuite(suite: TestSuite): void {
    this.suites.push(suite);
  }

  configureMocks(config: MockConfig): void {
    this.mockConfig = config;
  }

  async run(): Promise<TestResults> {
    const results: TestResults = {
      total: 0,
      passed: 0,
      failed: 0,
      skipped: 0,
      failures: []
    };

    for (const suite of this.suites) {
      console.log(`\n📦 Running suite: ${suite.name}`);
      
      if (suite.beforeAll) {
        await suite.beforeAll();
      }

      for (const test of suite.tests) {
        results.total++;
        try {
          const context = this.createTestContext();
          await this.runWithTimeout(test.run(context), test.timeout || 5000);
          results.passed++;
          console.log(`  ✅ ${test.name}`);
        } catch (error) {
          results.failed++;
          results.failures.push({
            suite: suite.name,
            test: test.name,
            error: error as Error
          });
          console.log(`  ❌ ${test.name}`);
          console.log(`     ${error}`);
        }
      }

      if (suite.afterAll) {
        await suite.afterAll();
      }
    }

    return results;
  }

  private createTestContext(): TestContext {
    // Implementation creates mock execution context
    return new MockExecuteFunctions(this.mockConfig) as TestContext;
  }

  private async runWithTimeout(promise: Promise<void>, timeout: number): Promise<void> {
    return Promise.race([
      promise,
      new Promise<void>((_, reject) => 
        setTimeout(() => reject(new Error(`Test timeout after ${timeout}ms`)), timeout)
      )
    ]);
  }
}

interface TestResults {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  failures: Array<{
    suite: string;
    test: string;
    error: Error;
  }>;
}
```

### Phase 1: YAKE Node Tests - TypeScript Implementation (Week 3-4)

#### 1.1 TypeScript Test Structure
```
n8n-nodes-yake/
├── src/                      # Existing source
├── test/
│   ├── YakeNode.test.ts     # Main test file
│   ├── unit/
│   │   ├── NodeStructure.test.ts
│   │   ├── Configuration.test.ts
│   │   └── KeywordExtraction.test.ts
│   ├── integration/
│   │   ├── PythonProcess.test.ts
│   │   └── E2EWorkflow.test.ts
│   ├── mocks/
│   │   ├── PythonMock.ts
│   │   └── YakeResponses.ts
│   └── fixtures/
│       ├── testTexts.ts
│       └── expectedResults.ts
├── test.tsconfig.json       # Test-specific TS config
└── jest.config.js           # Jest configuration
```

#### 1.2 YAKE Test Implementation
```typescript
// test/YakeNode.test.ts
import { TestRunner } from '../../test-utils';
import { YakeKeywordExtraction } from '../src/nodes/yakeKeywordExtraction/yakeKeywordExtraction.node';
import { unitTests } from './unit';
import { integrationTests } from './integration';

describe('YAKE Keyword Extraction Node', () => {
  const runner = new TestRunner(new YakeKeywordExtraction());

  // Configure mocks
  runner.configureMocks({
    pythonProcess: {
      executable: 'python3',
      mockResponses: true,
      throwOnMissingPython: false
    }
  });

  // Add test suites
  runner.addSuite(unitTests.nodeStructure);
  runner.addSuite(unitTests.configuration);
  runner.addSuite(unitTests.keywordExtraction);

  // Only run integration tests if Python is available
  if (process.env.RUN_INTEGRATION_TESTS === 'true') {
    runner.addSuite(integrationTests.pythonProcess);
    runner.addSuite(integrationTests.e2eWorkflow);
  }

  it('should execute all tests', async () => {
    const results = await runner.run();
    expect(results.failed).toBe(0);
  });
});
```

#### 1.3 Type-Safe Mock Implementation
```typescript
// test/mocks/PythonMock.ts
import { ChildProcess } from 'child_process';
import { EventEmitter } from 'events';

export interface PythonMockOptions {
  shouldFail?: boolean;
  responseDelay?: number;
  customResponse?: YakeResponse;
}

export interface YakeResponse {
  keywords: Array<{
    keyword: string;
    score: number;
  }>;
  processing_time: number;
  language: string;
}

export class PythonProcessMock extends EventEmitter implements Partial<ChildProcess> {
  public stdout: EventEmitter;
  public stderr: EventEmitter;
  public pid: number;

  constructor(private options: PythonMockOptions = {}) {
    super();
    this.stdout = new EventEmitter();
    this.stderr = new EventEmitter();
    this.pid = Math.floor(Math.random() * 10000);
  }

  async simulateResponse(): Promise<void> {
    await this.delay(this.options.responseDelay || 10);

    if (this.options.shouldFail) {
      this.stderr.emit('data', Buffer.from('YAKE module not found'));
      this.emit('exit', 1);
      return;
    }

    const response: YakeResponse = this.options.customResponse || {
      keywords: [
        { keyword: 'artificial intelligence', score: 0.023 },
        { keyword: 'machine learning', score: 0.045 }
      ],
      processing_time: 0.123,
      language: 'en'
    };

    this.stdout.emit('data', Buffer.from(JSON.stringify(response)));
    this.emit('exit', 0);
  }

  kill(): boolean {
    this.emit('exit', 137);
    return true;
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}
```

#### 1.4 Type-Safe Unit Tests
```typescript
// test/unit/KeywordExtraction.test.ts
import { TestSuite } from '../../../test-utils';
import { INodeExecutionData } from 'n8n-workflow';
import { PythonProcessMock, YakeResponse } from '../mocks/PythonMock';

export const keywordExtractionTests: TestSuite = {
  name: 'Keyword Extraction Logic',
  
  tests: [
    {
      name: 'should extract keywords from valid text',
      async run(context) {
        // Arrange
        const inputText = 'Artificial intelligence and machine learning are transforming industries.';
        const mockResponse: YakeResponse = {
          keywords: [
            { keyword: 'artificial intelligence', score: 0.02 },
            { keyword: 'machine learning', score: 0.04 }
          ],
          processing_time: 0.15,
          language: 'en'
        };

        context.configureMock('pythonProcess', new PythonProcessMock({
          customResponse: mockResponse
        }));

        // Act
        const input: INodeExecutionData[] = [{
          json: { text: inputText }
        }];
        
        const output = await context.execute.call(context.node, input);

        // Assert
        expect(output).toHaveLength(1);
        expect(output[0]).toHaveLength(1);
        
        const result = output[0][0].json;
        expect(result.keywords).toEqual(mockResponse.keywords);
        expect(result.metadata).toBeDefined();
        expect(result.metadata.language).toBe('en');
      }
    },

    {
      name: 'should handle empty text gracefully',
      async run(context) {
        const input: INodeExecutionData[] = [{
          json: { text: '' }
        }];

        const output = await context.execute.call(context.node, input);
        
        expect(output[0][0].json.keywords).toEqual([]);
        expect(output[0][0].json.error).toBeUndefined();
      }
    },

    {
      name: 'should validate language parameter',
      async run(context) {
        const supportedLanguages = ['en', 'pt', 'es', 'fr', 'de', 'it', 'nl'];
        const input: INodeExecutionData[] = [{
          json: { text: 'Test text' }
        }];

        // Test unsupported language
        context.setNodeParameter('language', 'unsupported');
        
        await expect(
          context.execute.call(context.node, input)
        ).rejects.toThrow('Unsupported language');
      }
    }
  ]
};
```

### Phase 2: Minimal Migration for Hierarchical Summarization (Week 5)

Instead of full migration, create a TypeScript wrapper:

```typescript
// test/HierarchicalSummarization.wrapper.test.ts
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

describe('Hierarchical Summarization Tests (Mocha Wrapper)', () => {
  it('should run existing Mocha tests', async () => {
    // Run existing tests in subprocess
    const { stdout, stderr } = await execAsync('npm run test:mocha', {
      cwd: __dirname
    });

    if (stderr) {
      console.error(stderr);
    }

    expect(stdout).toContain('passing');
  }, 60000); // 60 second timeout for comprehensive tests
});
```

### Phase 3: Test Infrastructure Patterns (Week 6)

#### 3.1 Database Mock with TypeScript
```typescript
// test-utils/src/mocks/DatabaseMock.ts
import { Client } from 'pg';

export interface MockDatabase {
  query<T = any>(sql: string, params?: any[]): Promise<{ rows: T[] }>;
  connect(): Promise<void>;
  end(): Promise<void>;
}

export class PostgresMock implements MockDatabase {
  private data: Map<string, any[]> = new Map();

  async query<T>(sql: string, params?: any[]): Promise<{ rows: T[] }> {
    // Simple mock implementation
    if (sql.includes('INSERT')) {
      return { rows: [] };
    }
    
    if (sql.includes('SELECT')) {
      const tableName = this.extractTableName(sql);
      return { rows: (this.data.get(tableName) || []) as T[] };
    }

    return { rows: [] };
  }

  async connect(): Promise<void> {
    // Mock connection
  }

  async end(): Promise<void> {
    // Mock cleanup
  }

  // Test helper methods
  seedTable(tableName: string, data: any[]): void {
    this.data.set(tableName, data);
  }

  private extractTableName(sql: string): string {
    const match = sql.match(/FROM\s+(\w+)/i);
    return match ? match[1] : 'unknown';
  }
}
```

#### 3.2 HTTP Mock with TypeScript
```typescript
// test-utils/src/mocks/HttpMock.ts
export interface HttpMockResponse<T = any> {
  status: number;
  data: T;
  headers?: Record<string, string>;
}

export class HttpRequestMock {
  private routes: Map<string, HttpMockResponse> = new Map();

  async request<T>(url: string, options?: any): Promise<HttpMockResponse<T>> {
    const response = this.routes.get(url);
    
    if (!response) {
      return {
        status: 404,
        data: { error: 'Not found' } as T
      };
    }

    return response as HttpMockResponse<T>;
  }

  // Test configuration methods
  whenGet(url: string): HttpMockResponseBuilder {
    return new HttpMockResponseBuilder(this, url, 'GET');
  }

  whenPost(url: string): HttpMockResponseBuilder {
    return new HttpMockResponseBuilder(this, url, 'POST');
  }

  reset(): void {
    this.routes.clear();
  }
}

class HttpMockResponseBuilder {
  constructor(
    private mock: HttpRequestMock,
    private url: string,
    private method: string
  ) {}

  thenReturn(response: HttpMockResponse): void {
    this.mock.routes.set(this.url, response);
  }
}
```

### Phase 4: CI/CD with Test Levels (Week 7)

#### 4.1 Separated Test Scripts
```json
// package.json
{
  "scripts": {
    "test:types": "tsc --noEmit",
    "test:lint": "eslint . --ext .ts",
    "test:unit": "jest --testPathPattern=unit --no-coverage",
    "test:unit:coverage": "jest --testPathPattern=unit --coverage",
    "test:integration": "docker-compose -f docker-compose.test.yml up --abort-on-container-exit",
    "test:all": "npm run test:types && npm run test:lint && npm run test:unit && npm run test:integration",
    "test:quick": "npm run test:types && npm run test:unit"
  }
}
```

#### 4.2 GitHub Actions Workflow
```yaml
# .github/workflows/test-custom-nodes.yml
name: Test Custom Nodes

on:
  push:
    paths:
      - 'n8n/custom-nodes/**'
      - '.github/workflows/test-custom-nodes.yml'
  pull_request:
    paths:
      - 'n8n/custom-nodes/**'

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: [18.x, 20.x]
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Use Node.js ${{ matrix.node-version }}
        uses: actions/setup-node@v3
        with:
          node-version: ${{ matrix.node-version }}
      
      - name: Cache dependencies
        uses: actions/cache@v3
        with:
          path: ~/.npm
          key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
      
      - name: Install dependencies
        run: |
          cd n8n/custom-nodes
          npm ci
      
      - name: Run TypeScript checks
        run: npm run test:types
      
      - name: Run linting
        run: npm run test:lint
      
      - name: Run unit tests
        run: npm run test:unit:coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage/lcov.info

  integration-tests:
    runs-on: ubuntu-latest
    needs: unit-tests
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install Python dependencies
        run: pip install yake
      
      - name: Run integration tests
        env:
          RUN_INTEGRATION_TESTS: true
          DATABASE_URL: postgres://postgres:test@localhost:5432/test
        run: |
          cd n8n/custom-nodes
          npm run test:integration
```

### Phase 5: Documentation and Training (Week 8)

#### Create Testing Guide
```typescript
// docs/TESTING_GUIDE.md
# TypeScript Testing Guide for n8n Custom Nodes

## Quick Start

### Running Tests
```bash
# Type checking only
npm run test:types

# Unit tests (fast, no external deps)
npm run test:unit

# Integration tests (requires Docker)
npm run test:integration

# Everything
npm run test:all
```

### Writing New Tests

1. **Always use TypeScript** for type safety
2. **Mock external dependencies** in unit tests
3. **Use real services** only in integration tests
4. **Follow the AAA pattern**: Arrange, Act, Assert

### Example Test Structure
```typescript
import { TestSuite } from '@test-utils';
import { MyNode } from '../src/nodes/MyNode/MyNode.node';

export const myNodeTests: TestSuite = {
  name: 'My Node Tests',
  
  beforeAll: async () => {
    // Setup
  },
  
  tests: [
    {
      name: 'should do something',
      async run(context) {
        // Arrange
        const input = [{ json: { data: 'test' } }];
        
        // Act
        const output = await context.execute(input);
        
        // Assert
        expect(output[0][0].json.result).toBe('expected');
      }
    }
  ]
};
```
```

## Realistic Timeline (8-10 weeks)

### Weeks 1-2: Foundation
- Create test-utils package with TypeScript
- Set up Jest with TypeScript support
- Create basic mock implementations

### Weeks 3-4: YAKE Implementation
- Write comprehensive TypeScript tests
- Create Python process mocks
- Document patterns for other nodes

### Week 5: Minimal Migration
- Wrapper for Hierarchical Summarization
- Don't break working tests
- Add TypeScript interfaces where helpful

### Week 6: Infrastructure Patterns
- Complete mock implementations
- Create reusable test helpers
- Document best practices

### Week 7: CI/CD Setup
- Configure GitHub Actions
- Set up test separation
- Add coverage reporting

### Week 8: Documentation
- Complete testing guide
- Add examples for each node type
- Create troubleshooting guide

### Weeks 9-10: Buffer
- Address unexpected issues
- Refine based on feedback
- Polish documentation

## Success Metrics (Revised)

1. **Type Coverage**: 100% of test code is TypeScript
2. **Unit Test Coverage**: 60% minimum (focus on critical paths)
3. **Unit Test Speed**: < 30 seconds
4. **Integration Test Speed**: < 10 minutes
5. **CI Pipeline**: Runs on every PR
6. **Documentation**: Complete TypeScript examples

## Key Principles

1. **TypeScript First**: All new test code in TypeScript
2. **Progressive Enhancement**: Don't break working tests
3. **Mock by Default**: Real services only in integration tests
4. **Fast Feedback**: Unit tests must be quick
5. **Clear Separation**: Unit vs Integration vs E2E

This revised plan provides a more realistic, TypeScript-focused approach that addresses the infrastructure gaps and provides achievable goals.