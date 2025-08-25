import { CourtDocument, SearchResponse, BulkJudgeResponse } from '@/types/court-documents';

/**
 * Document Source Interface
 * 
 * Defines the contract for any document provider (court docs, contracts, policies, etc.)
 * All sources must adapt their data to the CourtDocument format for consistency.
 */
export interface DocumentSource {
  // Source identifier (e.g., 'court', 'contracts', 'policies')
  readonly sourceId: string;
  
  // Human-readable source name for UI
  readonly sourceName: string;
  
  // Optional source description
  readonly description?: string;

  // Search documents with flexible parameters
  searchDocuments(params: DocumentSearchParams): Promise<SearchResponse>;
  
  // Get plain text content for a document
  getDocumentText(id: number | string): Promise<string>;
  
  // Get full document with metadata
  getDocument(id: number | string): Promise<CourtDocument>;
  
  // List available documents (for browsing)
  listDocuments(limit?: number): Promise<CourtDocument[]>;
  
  // Optional: Bulk fetch by category (like judge for court docs)
  getBulkByCategory?(category: string, includeText?: boolean): Promise<BulkJudgeResponse>;
  
  // Check if source is available/configured
  isAvailable(): Promise<boolean>;
}

/**
 * Common search parameters that all sources should support
 */
export interface DocumentSearchParams {
  // Free text search query
  query?: string;
  
  // Document type filter
  type?: string;
  
  // Category filter (judge for court, department for contracts, etc.)
  category?: string;
  
  // Minimum text length filter
  min_length?: number;
  
  // Maximum text length filter
  max_length?: number;
  
  // Pagination
  limit?: number;
  offset?: number;
  
  // Date range filters
  date_from?: string;
  date_to?: string;
  
  // Additional source-specific filters
  [key: string]: any;
}

/**
 * Configuration for document sources
 */
export interface DocumentSourceConfig {
  // Base URL for API calls (if applicable)
  baseUrl?: string;
  
  // API key or auth token (if needed)
  apiKey?: string;
  
  // Additional source-specific config
  [key: string]: any;
}