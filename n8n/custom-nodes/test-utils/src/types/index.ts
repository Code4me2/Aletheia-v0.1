import { 
  IExecuteFunctions, 
  INodeExecutionData, 
  INodeType,
  INodeTypeDescription,
  IDataObject,
  INodeParameters,
  ICredentialDataDecryptedObject,
  IWorkflowDataProxyData
} from 'n8n-workflow';

/**
 * Test context provided to each test case
 */
export interface TestContext {
  /**
   * Mock execution functions
   */
  execute: IExecuteFunctions;
  
  /**
   * The node instance being tested
   */
  node: INodeType;
  
  /**
   * Set input data for the test
   */
  setInputData(data: INodeExecutionData[]): void;
  
  /**
   * Set node parameters
   */
  setNodeParameter(name: string, value: any): void;
  
  /**
   * Configure mock responses
   */
  configureMock(mockType: string, mockInstance: any): void;
  
  /**
   * Get the last execution result
   */
  getLastResult(): INodeExecutionData[][];
}

/**
 * Definition of a test suite
 */
export interface TestSuite {
  /**
   * Name of the test suite
   */
  name: string;
  
  /**
   * Individual test cases
   */
  tests: TestCase[];
  
  /**
   * Setup function run before all tests
   */
  beforeAll?: () => Promise<void> | void;
  
  /**
   * Cleanup function run after all tests
   */
  afterAll?: () => Promise<void> | void;
  
  /**
   * Setup function run before each test
   */
  beforeEach?: () => Promise<void> | void;
  
  /**
   * Cleanup function run after each test
   */
  afterEach?: () => Promise<void> | void;
}

/**
 * Individual test case
 */
export interface TestCase {
  /**
   * Test name/description
   */
  name: string;
  
  /**
   * Test implementation
   */
  run: (context: TestContext) => Promise<void> | void;
  
  /**
   * Test timeout in milliseconds
   */
  timeout?: number;
  
  /**
   * Skip this test
   */
  skip?: boolean;
  
  /**
   * Only run this test (for debugging)
   */
  only?: boolean;
}

/**
 * Test execution results
 */
export interface TestResults {
  /**
   * Total number of tests
   */
  total: number;
  
  /**
   * Number of passed tests
   */
  passed: number;
  
  /**
   * Number of failed tests
   */
  failed: number;
  
  /**
   * Number of skipped tests
   */
  skipped: number;
  
  /**
   * Detailed failure information
   */
  failures: TestFailure[];
  
  /**
   * Execution time in milliseconds
   */
  duration: number;
}

/**
 * Test failure details
 */
export interface TestFailure {
  suite: string;
  test: string;
  error: Error;
  stack?: string;
}

/**
 * Mock configuration options
 */
export interface MockConfig {
  /**
   * Python subprocess mock configuration
   */
  pythonProcess?: MockPythonConfig;
  
  /**
   * HTTP request mock configuration
   */
  httpRequest?: MockHttpConfig;
  
  /**
   * Database mock configuration
   */
  database?: MockDatabaseConfig;
  
  /**
   * File system mock configuration
   */
  fileSystem?: MockFileSystemConfig;
}

/**
 * Python subprocess mock configuration
 */
export interface MockPythonConfig {
  /**
   * Python executable path
   */
  executable: string;
  
  /**
   * Whether to mock responses
   */
  mockResponses: boolean;
  
  /**
   * Whether to throw if Python is missing
   */
  throwOnMissingPython: boolean;
  
  /**
   * Custom response handler
   */
  responseHandler?: (command: string, args: string[]) => any;
}

/**
 * HTTP request mock configuration
 */
export interface MockHttpConfig {
  /**
   * Base URL for requests
   */
  baseUrl?: string;
  
  /**
   * Response mappings
   */
  responses: Map<string, MockHttpResponse>;
  
  /**
   * Default response for unmapped requests
   */
  defaultResponse?: MockHttpResponse;
}

/**
 * Mock HTTP response
 */
export interface MockHttpResponse {
  status: number;
  data: any;
  headers?: Record<string, string>;
  delay?: number;
}

/**
 * Database mock configuration
 */
export interface MockDatabaseConfig {
  /**
   * Database type
   */
  type: 'postgres' | 'mysql' | 'sqlite';
  
  /**
   * Initial data seed
   */
  seed?: Record<string, any[]>;
  
  /**
   * Whether to simulate errors
   */
  simulateErrors?: boolean;
}

/**
 * File system mock configuration
 */
export interface MockFileSystemConfig {
  /**
   * Virtual file system structure
   */
  files: Record<string, string | Buffer>;
  
  /**
   * Whether to allow writes
   */
  allowWrites: boolean;
}

/**
 * Helper type for node parameter values
 */
export type NodeParameterValue = string | number | boolean | IDataObject | IDataObject[] | undefined;

/**
 * Mock execution function builder options
 */
export interface MockExecuteFunctionsOptions {
  /**
   * Node instance
   */
  node: INodeType;
  
  /**
   * Node parameters
   */
  parameters?: INodeParameters;
  
  /**
   * Input data
   */
  inputData?: INodeExecutionData[];
  
  /**
   * Workflow data
   */
  workflowData?: IWorkflowDataProxyData;
  
  /**
   * Credentials
   */
  credentials?: ICredentialDataDecryptedObject;
  
  /**
   * Mock configuration
   */
  mocks?: MockConfig;
}