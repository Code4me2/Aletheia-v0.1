/**
 * Document Sources Initialization
 * 
 * Optional initialization file for registering additional document sources.
 * Import this in your app's initialization if you want to enable mock/demo sources.
 * 
 * In production, you would register real API clients here.
 */

import { documentSourceRegistry } from './registry';
import { mockContractSource } from './mock-contract-source';

/**
 * Initialize demo document sources
 * 
 * Call this function to enable mock document sources for testing/demo.
 * By default, only the court document source is registered.
 */
export function initializeDemoSources(): void {
  // Register mock contract source for demonstrations
  if (process.env.NEXT_PUBLIC_ENABLE_MOCK_SOURCES === 'true') {
    documentSourceRegistry.register(mockContractSource);
    console.info('Mock document sources registered for demo mode');
  }
}

/**
 * Initialize production document sources
 * 
 * Example of how you might register real document sources in production.
 */
export function initializeProductionSources(): void {
  // Example: Register a real contract management system
  /*
  if (process.env.CONTRACT_API_URL) {
    const contractSource = new ContractAPISource({
      baseUrl: process.env.CONTRACT_API_URL,
      apiKey: process.env.CONTRACT_API_KEY
    });
    documentSourceRegistry.register(contractSource);
  }
  */
  
  // Example: Register a policy document system
  /*
  if (process.env.POLICY_API_URL) {
    const policySource = new PolicyDocumentSource({
      baseUrl: process.env.POLICY_API_URL
    });
    documentSourceRegistry.register(policySource);
  }
  */
}

/**
 * Check and log available document sources
 */
export async function logAvailableSources(): Promise<void> {
  const sources = await documentSourceRegistry.getAvailableSources();
  console.info('Available document sources:', sources.map(s => ({
    id: s.sourceId,
    name: s.sourceName,
    description: s.description
  })));
}