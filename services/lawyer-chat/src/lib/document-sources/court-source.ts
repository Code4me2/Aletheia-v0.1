import { DocumentSource, DocumentSearchParams } from './types';
import { CourtDocument, SearchResponse, BulkJudgeResponse } from '@/types/court-documents';
import { courtAPI } from '@/lib/court-api';

/**
 * Court Document Source Adapter
 * 
 * Wraps the existing court-processor API to implement the DocumentSource interface.
 * This preserves all existing functionality while enabling the adapter pattern.
 */
export class CourtDocumentSource implements DocumentSource {
  readonly sourceId = 'court';
  readonly sourceName = 'Court Opinions';
  readonly description = 'Federal court opinions and legal documents from RECAP';

  async searchDocuments(params: DocumentSearchParams): Promise<SearchResponse> {
    // Map generic params to court-specific API params
    const courtParams = {
      judge: params.category,  // category maps to judge for court docs
      type: params.type,
      min_length: params.min_length,
      limit: params.limit || 50,
      offset: params.offset || 0
    };
    
    // Filter out undefined values
    const cleanParams = Object.fromEntries(
      Object.entries(courtParams).filter(([_, v]) => v !== undefined)
    );
    
    return courtAPI.searchDocuments(cleanParams);
  }

  async getDocumentText(id: number | string): Promise<string> {
    const docId = typeof id === 'string' ? parseInt(id, 10) : id;
    return courtAPI.getDocumentText(docId);
  }

  async getDocument(id: number | string): Promise<CourtDocument> {
    const docId = typeof id === 'string' ? parseInt(id, 10) : id;
    return courtAPI.getDocument(docId);
  }

  async listDocuments(limit = 20): Promise<CourtDocument[]> {
    return courtAPI.listDocuments(limit);
  }

  async getBulkByCategory(judgeName: string, includeText = false): Promise<BulkJudgeResponse> {
    return courtAPI.getBulkByJudge(judgeName, includeText);
  }

  async isAvailable(): Promise<boolean> {
    try {
      // Check if court-processor API is reachable
      await courtAPI.listDocuments(1);
      return true;
    } catch {
      return false;
    }
  }
}

// Export singleton instance for backward compatibility
export const courtDocumentSource = new CourtDocumentSource();