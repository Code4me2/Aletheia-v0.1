// Court Processor API response types
export interface CourtDocument {
  id: number;
  case?: string;           // Simplified API uses 'case' not 'case_number' - kept for backwards compatibility
  type: string;
  judge: string;
  court?: string;          // Optional - not always provided by API
  date_filed?: string;
  text?: string;
  text_length: number;
  preview?: string;
  // Enhanced title fields (added in API v2)
  formatted_title?: string;           // Full legal citation format
  formatted_title_short?: string;     // Abbreviated format for UI
  document_type_extracted?: string;   // Document type extracted from content
  citation_components?: {
    case_name?: string;
    document_type?: string;
    judge?: string;
    date_filed?: string;
    court?: string;
  };
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