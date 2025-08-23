// Global test setup
global.console = {
  ...console,
  // Suppress console logs during tests unless explicitly needed
  log: jest.fn(),
  debug: jest.fn(),
  info: jest.fn(),
  // Keep warnings and errors visible
  warn: console.warn,
  error: console.error,
};

// Set test environment variables
process.env.NODE_ENV = 'test';
process.env.DB_NAME = 'test_db';
process.env.DB_USER = 'test_user';
process.env.DB_PASSWORD = 'test_password';
process.env.N8N_ENCRYPTION_KEY = 'test_encryption_key';

// Mock timers for consistent test results
beforeEach(() => {
  jest.clearAllMocks();
  jest.restoreAllMocks();
});

// Cleanup after tests
afterEach(() => {
  jest.clearAllTimers();
});