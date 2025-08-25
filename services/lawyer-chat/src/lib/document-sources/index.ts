/**
 * Document Sources Module
 * 
 * This module implements an adapter pattern for document sources, allowing
 * the lawyer-chat interface to work with different types of documents
 * (court opinions, contracts, policies, etc.) without modifying core functionality.
 * 
 * ## Adding a New Document Source
 * 
 * 1. Create a new class implementing the DocumentSource interface
 * 2. Map your data to the CourtDocument format (for consistency)
 * 3. Register it in your app initialization or component
 * 
 * Example:
 * ```typescript
 * import { DocumentSource } from './types';
 * import { documentSourceRegistry } from './registry';
 * 
 * class MyCustomSource implements DocumentSource {
 *   sourceId = 'custom';
 *   sourceName = 'My Custom Documents';
 *   // ... implement required methods
 * }
 * 
 * // Register the source
 * documentSourceRegistry.register(new MyCustomSource());
 * ```
 * 
 * ## Using Document Sources
 * 
 * ```typescript
 * // In a component
 * const { searchDocuments, switchSource } = useDocumentSelection();
 * 
 * // Switch to a different source
 * switchSource('contracts');
 * 
 * // Search will now use the contracts source
 * searchDocuments({ type: 'nda' });
 * ```
 */

export * from './types';
export * from './registry';
export * from './court-source';
export * from './mock-contract-source';

// For backward compatibility, export court API as default
export { courtDocumentSource as defaultDocumentSource } from './court-source';