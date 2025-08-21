import { CourtDocument, SearchResponse, BulkJudgeResponse } from '@/types/court-documents';

class CourtAPIClient {
  private baseUrl: string;
  private clientUrl: string;

  constructor() {
    // Use server URL for SSR, client URL for browser
    this.baseUrl = process.env.COURT_API_BASE_URL || 'http://court-processor:8104';
    this.clientUrl = process.env.NEXT_PUBLIC_COURT_API_URL || 'http://localhost:8104';
    
    // Validate environment variables in production
    if (typeof window !== 'undefined' && 
        this.clientUrl === 'http://localhost:8104' && 
        window.location.hostname !== 'localhost') {
      console.error(
        'Court API URL not configured. Document selection will not work.',
        'Please rebuild the application with NEXT_PUBLIC_COURT_API_URL environment variable set.'
      );
    }
  }

  private getUrl(): string {
    // In browser, check if we're in production with localhost fallback
    if (typeof window !== 'undefined') {
      if (this.clientUrl === 'http://localhost:8104' && window.location.hostname !== 'localhost') {
        throw new Error(
          'Court API not configured. Please contact your administrator to enable document selection.'
        );
      }
      return this.clientUrl;
    }
    return this.baseUrl;
  }

  async searchDocuments(params: {
    judge?: string;
    type?: string;
    min_length?: number;
    limit?: number;
    offset?: number;
  }): Promise<SearchResponse> {
    const searchParams = new URLSearchParams();
    
    // Map parameters to Court Processor API format
    if (params.judge) searchParams.append('judge', params.judge);
    if (params.type) searchParams.append('type', params.type);
    if (params.min_length) searchParams.append('min_length', params.min_length.toString());
    searchParams.append('limit', (params.limit || 50).toString());
    searchParams.append('offset', (params.offset || 0).toString());

    const response = await fetch(`${this.getUrl()}/search?${searchParams}`);
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getDocumentText(id: number): Promise<string> {
    const response = await fetch(`${this.getUrl()}/text/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch document text: ${response.statusText}`);
    }
    return response.text();
  }

  async getDocument(id: number): Promise<CourtDocument> {
    const response = await fetch(`${this.getUrl()}/documents/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch document: ${response.statusText}`);
    }
    return response.json();
  }

  async getBulkByJudge(judgeName: string, includeText = false): Promise<BulkJudgeResponse> {
    const url = `${this.getUrl()}/bulk/judge/${encodeURIComponent(judgeName)}?include_text=${includeText}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Bulk fetch failed: ${response.statusText}`);
    }
    return response.json();
  }

  async listDocuments(limit = 20): Promise<CourtDocument[]> {
    const response = await fetch(`${this.getUrl()}/list?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`List failed: ${response.statusText}`);
    }
    return response.json();
  }
}

export const courtAPI = new CourtAPIClient();