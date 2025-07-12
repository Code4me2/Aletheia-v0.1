# TypeScript Migration Testing Strategy

## Overview
This document outlines the comprehensive testing approach for the TypeScript migration, ensuring feature parity, performance, and quality throughout the migration process.

## Testing Philosophy

### Core Principles
1. **Feature Parity First**: Every JS feature must work identically in TS
2. **Regression Prevention**: Catch issues before users do
3. **Performance Validation**: No degradation acceptable
4. **Progressive Testing**: Test as we build, not after

### Testing Pyramid
```
         /\
        /E2E\        5% - Critical user journeys
       /------\
      /  Integ  \    20% - Module interactions  
     /------------\
    /     Unit     \  75% - Component logic
   /----------------\
```

## Test Infrastructure

### Technology Stack
```json
{
  "test-runner": "vitest",
  "coverage": "@vitest/coverage-v8",
  "e2e": "playwright",
  "visual": "percy",
  "performance": "lighthouse-ci",
  "mocking": "msw"
}
```

### Directory Structure
```
website/
├── tests/
│   ├── unit/              # Unit tests
│   │   ├── services/      # Service tests
│   │   ├── components/    # Component tests
│   │   └── utils/         # Utility tests
│   ├── integration/       # Integration tests
│   │   ├── modules/       # Module interaction tests
│   │   └── api/           # API integration tests
│   ├── e2e/              # End-to-end tests
│   │   ├── flows/        # User journey tests
│   │   └── smoke/        # Smoke tests
│   ├── visual/           # Visual regression tests
│   ├── performance/      # Performance tests
│   └── fixtures/         # Test data and mocks
├── __mocks__/            # Module mocks
└── test-utils/           # Test helpers
```

## Unit Testing Strategy

### Service Testing
```typescript
// Example: ChatService tests
describe('ChatService', () => {
  let service: ChatService;
  let mockApi: MockApiClient;
  let mockStorage: MockStorageService;
  
  beforeEach(() => {
    mockApi = createMockApiClient();
    mockStorage = createMockStorageService();
    service = new ChatService({ api: mockApi, storage: mockStorage });
  });
  
  describe('sendMessage', () => {
    test('sends message via webhook', async () => {
      const message = 'Test message';
      mockApi.post.mockResolvedValue({ success: true });
      
      await service.sendMessage(message);
      
      expect(mockApi.post).toHaveBeenCalledWith('/webhook/...', {
        action: 'chat',
        message,
        timestamp: expect.any(String)
      });
    });
    
    test('handles network errors gracefully', async () => {
      mockApi.post.mockRejectedValue(new Error('Network error'));
      
      await expect(service.sendMessage('test'))
        .rejects
        .toThrow('Failed to send message');
    });
  });
});
```

### Component Testing
```typescript
// Example: CitationPanel tests
describe('CitationPanel', () => {
  let panel: CitationPanel;
  let container: HTMLElement;
  
  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    panel = new CitationPanel({ container });
  });
  
  afterEach(() => {
    panel.destroy();
    container.remove();
  });
  
  test('renders citations correctly', () => {
    const citations = [
      { id: '1', text: 'Test citation', source: { title: 'Test Case' } }
    ];
    
    panel.render(citations);
    
    expect(container.querySelector('.citation-entry')).toBeTruthy();
    expect(container.textContent).toContain('Test citation');
  });
  
  test('handles click navigation', () => {
    const onNavigate = vi.fn();
    panel.on('navigate', onNavigate);
    
    const citation = container.querySelector('.citation-entry');
    citation.click();
    
    expect(onNavigate).toHaveBeenCalledWith({ citationId: '1' });
  });
});
```

### State Management Testing
```typescript
describe('StateManager', () => {
  let state: StateManager;
  
  beforeEach(() => {
    state = new StateManager();
  });
  
  test('notifies subscribers of state changes', () => {
    const callback = vi.fn();
    state.subscribe('chat.messages', callback);
    
    const messages = [{ id: '1', text: 'Hello' }];
    state.set('chat.messages', messages);
    
    expect(callback).toHaveBeenCalledWith(messages, undefined);
  });
  
  test('handles nested state updates', () => {
    const initial = { user: { name: 'John', age: 30 } };
    state.set('profile', initial);
    
    state.update('profile.user.age', 31);
    
    expect(state.get('profile.user.age')).toBe(31);
    expect(state.get('profile.user.name')).toBe('John');
  });
});
```

## Integration Testing

### Module Integration Tests
```typescript
describe('Chat and Citation Integration', () => {
  let app: App;
  let chatModule: ChatModule;
  let citationModule: CitationModule;
  
  beforeEach(async () => {
    app = new App();
    await app.initialize();
    
    chatModule = app.getModule('chat');
    citationModule = app.getModule('citations');
  });
  
  test('citations appear when message contains references', async () => {
    const mockResponse = {
      message: 'According to <cite id="1">Smith v. Jones</cite>...',
      citations: [{ id: '1', source: { title: 'Smith v. Jones' } }]
    };
    
    // Mock webhook response
    mockWebhookResponse(mockResponse);
    
    // Send message
    await chatModule.sendMessage('Tell me about Smith v. Jones');
    
    // Verify citation panel updates
    const citationState = app.state.get('citations');
    expect(citationState.citations.size).toBe(1);
    expect(citationState.citations.get('1')).toMatchObject({
      source: { title: 'Smith v. Jones' }
    });
  });
});
```

### API Integration Tests
```typescript
describe('Webhook Integration', () => {
  let server: SetupServer;
  
  beforeAll(() => {
    server = setupServer(
      rest.post('/webhook/:id', (req, res, ctx) => {
        return res(ctx.json({ 
          success: true,
          response: 'Mocked response' 
        }));
      })
    );
    server.listen();
  });
  
  afterAll(() => server.close());
  
  test('real webhook communication', async () => {
    const client = new ApiClient({ baseUrl: 'http://localhost:8080' });
    const response = await client.post('/webhook/test', {
      action: 'chat',
      message: 'Hello'
    });
    
    expect(response.success).toBe(true);
  });
});
```

## End-to-End Testing

### Critical User Journeys
```typescript
// playwright/tests/chat-flow.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Chat Flow', () => {
  test('user can send message and view response', async ({ page }) => {
    await page.goto('http://localhost:8080');
    
    // Navigate to chat
    await page.click('text=AI Chat');
    
    // Type message
    await page.fill('#chat-input', 'What is contract law?');
    await page.press('#chat-input', 'Enter');
    
    // Wait for response
    await expect(page.locator('.message.assistant'))
      .toContainText('Contract law', { timeout: 10000 });
    
    // Verify citations if present
    const citationsButton = page.locator('text=View Citations');
    if (await citationsButton.isVisible()) {
      await citationsButton.click();
      await expect(page.locator('.citation-panel')).toBeVisible();
    }
  });
});
```

### Visual Regression Tests
```typescript
// percy/visual-tests.spec.ts
test.describe('Visual Regression', () => {
  test('chat interface appearance', async ({ page }) => {
    await page.goto('http://localhost:8080#chat');
    await page.waitForLoadState('networkidle');
    
    await percySnapshot(page, 'Chat Interface');
  });
  
  test('citation panel appearance', async ({ page }) => {
    await page.goto('http://localhost:8080#chat');
    
    // Load fixture with citations
    await page.evaluate(() => {
      window.app.state.set('chat.messages', [{
        role: 'assistant',
        content: 'Test with <cite id="1">citation</cite>'
      }]);
    });
    
    await page.click('text=View Citations');
    await percySnapshot(page, 'Citation Panel Open');
  });
});
```

## Performance Testing

### Metrics to Track
```typescript
interface PerformanceMetrics {
  // Loading metrics
  firstContentfulPaint: number;
  largestContentfulPaint: number;
  timeToInteractive: number;
  
  // Runtime metrics
  frameRate: number;
  memoryUsage: number;
  renderTime: number;
  
  // Bundle metrics
  bundleSize: number;
  gzipSize: number;
  chunkSizes: Record<string, number>;
}
```

### Performance Test Suite
```typescript
describe('Performance Benchmarks', () => {
  test('initial load performance', async () => {
    const metrics = await measurePageLoad('http://localhost:8080');
    
    expect(metrics.largestContentfulPaint).toBeLessThan(2500);
    expect(metrics.timeToInteractive).toBeLessThan(3500);
  });
  
  test('d3 visualization performance', async () => {
    const page = await browser.newPage();
    await page.goto('http://localhost:8080#hierarchical');
    
    // Load large dataset
    await page.evaluate(() => {
      window.app.modules.get('hierarchical')
        .loadData(generateLargeHierarchy(1000));
    });
    
    // Measure frame rate during interaction
    const fps = await measureFrameRate(page, async () => {
      await page.mouse.wheel({ deltaY: 100 });
      await page.waitForTimeout(1000);
    });
    
    expect(fps).toBeGreaterThan(30);
  });
});
```

### Memory Leak Detection
```typescript
test('no memory leaks in chat module', async () => {
  const page = await browser.newPage();
  await page.goto('http://localhost:8080#chat');
  
  const initialMemory = await page.evaluate(() => performance.memory.usedJSHeapSize);
  
  // Simulate heavy usage
  for (let i = 0; i < 100; i++) {
    await page.fill('#chat-input', `Message ${i}`);
    await page.press('#chat-input', 'Enter');
    await page.waitForTimeout(100);
  }
  
  // Force garbage collection
  await page.evaluate(() => {
    if (window.gc) window.gc();
  });
  
  const finalMemory = await page.evaluate(() => performance.memory.usedJSHeapSize);
  const memoryIncrease = (finalMemory - initialMemory) / 1024 / 1024; // MB
  
  expect(memoryIncrease).toBeLessThan(50); // Max 50MB increase
});
```

## Migration-Specific Testing

### Feature Parity Tests
```typescript
// Automated comparison between JS and TS versions
describe('Feature Parity Validation', () => {
  const features = [
    { name: 'Chat message sending', selector: '#chat-input' },
    { name: 'Citation panel toggle', selector: '.citation-toggle' },
    { name: 'Hierarchy navigation', selector: '.hierarchy-viz' },
    { name: 'Service health check', selector: '.health-status' }
  ];
  
  test.each(features)('$name works identically', async ({ selector }) => {
    const jsPage = await browser.newPage();
    const tsPage = await browser.newPage();
    
    await jsPage.goto('http://localhost:8080/legacy');
    await tsPage.goto('http://localhost:8080');
    
    const jsElement = await jsPage.$(selector);
    const tsElement = await tsPage.$(selector);
    
    expect(jsElement).toBeTruthy();
    expect(tsElement).toBeTruthy();
    
    // Compare computed styles
    const jsStyles = await jsElement.evaluate(el => 
      window.getComputedStyle(el)
    );
    const tsStyles = await tsElement.evaluate(el => 
      window.getComputedStyle(el)
    );
    
    expect(tsStyles).toMatchObject(jsStyles);
  });
});
```

### Migration Progress Tracking
```typescript
interface MigrationMetrics {
  totalComponents: number;
  migratedComponents: number;
  testCoverage: number;
  typeErrors: number;
  performanceRegression: number;
}

test('migration progress metrics', async () => {
  const metrics = await calculateMigrationMetrics();
  
  expect(metrics.migratedComponents / metrics.totalComponents)
    .toBeGreaterThan(0.95); // 95% complete
  
  expect(metrics.testCoverage).toBeGreaterThan(0.85); // 85% coverage
  
  expect(metrics.typeErrors).toBe(0);
  
  expect(metrics.performanceRegression).toBeLessThan(0.05); // <5% regression
});
```

## Test Data Management

### Fixtures
```typescript
// fixtures/chat-messages.ts
export const chatFixtures = {
  simple: {
    user: 'Hello',
    assistant: 'Hi! How can I help you?'
  },
  withCitations: {
    user: 'Tell me about contract law',
    assistant: 'Contract law governs <cite id="1">agreements</cite>...',
    citations: [{ id: '1', source: { title: 'Black\'s Law Dictionary' } }]
  },
  withMarkdown: {
    user: 'Show me code',
    assistant: '```javascript\nconst example = "code";\n```'
  }
};
```

### Mock Data Generators
```typescript
// test-utils/generators.ts
export function generateHierarchyData(nodeCount: number): HierarchyData {
  // Generate realistic test data
}

export function generateChatHistory(messageCount: number): ChatMessage[] {
  // Generate chat messages with various formats
}
```

## Continuous Integration

### CI Pipeline Configuration
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - run: npm ci
      - run: npm run test:unit
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v3

  integration-tests:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:14
      n8n:
        image: n8nio/n8n
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run test:integration

  e2e-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npx playwright install
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/

  visual-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run test:visual
      env:
        PERCY_TOKEN: ${{ secrets.PERCY_TOKEN }}

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: npm ci
      - run: npm run build
      - run: npm run test:performance
      - uses: GoogleChrome/lighthouse-ci-action@v1
```

## Test Reporting

### Coverage Reports
```typescript
// vitest.config.ts
export default {
  test: {
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      exclude: [
        'node_modules/',
        'tests/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData.ts'
      ],
      thresholds: {
        lines: 85,
        functions: 85,
        branches: 80,
        statements: 85
      }
    }
  }
};
```

### Test Results Dashboard
```typescript
// Custom test reporter
class MigrationTestReporter {
  onTestResult(test: Test, result: TestResult) {
    // Track migration-specific metrics
    this.updateDashboard({
      feature: test.name,
      jsVersion: result.jsPerformance,
      tsVersion: result.tsPerformance,
      parity: result.functionalParity,
      regression: result.regressionFound
    });
  }
}
```

## Testing Best Practices

### Do's
1. **Test behavior, not implementation**
2. **Use realistic test data**
3. **Test error cases thoroughly**
4. **Keep tests focused and atomic**
5. **Use descriptive test names**

### Don'ts
1. **Don't test framework code**
2. **Don't mock everything**
3. **Don't ignore flaky tests**
4. **Don't test private methods directly**
5. **Don't skip difficult tests**

### Test Code Quality
```typescript
// Good test example
test('user sees error message when webhook fails', async () => {
  // Arrange
  mockWebhookError('Network timeout');
  
  // Act
  await userSendsMessage('Hello');
  
  // Assert
  expect(screen.getByRole('alert')).toHaveTextContent(
    'Failed to send message. Please try again.'
  );
});

// Bad test example
test('test1', () => {
  const x = new Thing();
  x._privateMethod();
  expect(x.state).toBe(true);
});
```

## Conclusion

This comprehensive testing strategy ensures the TypeScript migration maintains quality, performance, and feature parity throughout the process. By following these guidelines and implementing the described test suites, we can confidently migrate while minimizing risk and ensuring a smooth transition for users.