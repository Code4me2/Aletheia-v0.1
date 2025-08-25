import { DocumentSource, DocumentSearchParams } from './types';
import { CourtDocument, SearchResponse } from '@/types/court-documents';

/**
 * Transcript Document Source
 * 
 * Placeholder implementation for transcript documents.
 * Replace the mock data and methods with actual API calls when ready.
 */
export class TranscriptSource implements DocumentSource {
  readonly sourceId = 'transcripts';
  readonly sourceName = 'Transcripts';
  readonly description = 'Court hearing and deposition transcripts';

  // Empty mock data - ready for real transcript API integration
  private mockTranscripts: CourtDocument[] = [];

  async searchDocuments(params: DocumentSearchParams): Promise<SearchResponse> {
    // When implementing real API:
    // const response = await fetch(`${TRANSCRIPT_API_URL}/search`, {...});
    // return response.json();
    
    return {
      total: 0,
      returned: 0,
      offset: params.offset || 0,
      limit: params.limit || 50,
      documents: []
    };
  }

  async getDocumentText(id: number | string): Promise<string> {
    // When implementing real API:
    // const response = await fetch(`${TRANSCRIPT_API_URL}/text/${id}`);
    // return response.text();
    
    throw new Error(`Transcript ${id} not found`);
  }

  async getDocument(id: number | string): Promise<CourtDocument> {
    // When implementing real API:
    // const response = await fetch(`${TRANSCRIPT_API_URL}/documents/${id}`);
    // return response.json();
    
    throw new Error(`Transcript ${id} not found`);
  }

  async listDocuments(limit = 20): Promise<CourtDocument[]> {
    // When implementing real API:
    // const response = await fetch(`${TRANSCRIPT_API_URL}/list?limit=${limit}`);
    // return response.json();
    
    return [];
  }

  async isAvailable(): Promise<boolean> {
    // When implementing real API:
    // try {
    //   const response = await fetch(`${TRANSCRIPT_API_URL}/health`);
    //   return response.ok;
    // } catch {
    //   return false;
    // }
    
    return true; // Always available as placeholder
  }
}

// Export singleton instance
export const transcriptSource = new TranscriptSource();