// Court Processor API response types
export interface CourtDocument {
  id: number;
  case?: string;           // Simplified API uses 'case' not 'case_number'
  type: string;
  judge: string;
  court?: string;          // Optional - not always provided by API
  date_filed?: string;
  text?: string;
  text_length: number;
  preview?: string;
}

export interface SearchResponse {
  total: number;
  returned: number;
  offset: number;
  limit: number;
  documents: CourtDocument[];
}

export interface BulkJudgeResponse {
  judge: string;
  total_documents: number;
  total_text_characters?: number;
  documents: CourtDocument[];
}

export interface DocumentSelection {
  documentId: number;
  documentTitle: string;
  judge: string;
  court: string;
  textLength: number;
  selectedAt: Date;
}

export interface ChatSessionWithDocuments {
  id: string;
  documents: DocumentSelection[];
  contextSize: number;
}