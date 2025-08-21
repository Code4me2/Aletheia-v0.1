import type { AnalyticsData } from '@/types';
import type { CourtDocument } from './court-documents';

export interface StreamProgress {
  stage: string;
  message: string;
  percent?: number;
  elapsedTime?: number;
}

export interface Message {
  id: number;
  sender: 'user' | 'assistant';
  text: string;
  references?: string[];
  analytics?: AnalyticsData;
  timestamp: Date;
  documentContext?: CourtDocument[];  // Documents sent with user message
  citedDocumentIds?: string[];        // Citation markers found in assistant response (e.g., ['DOC1', 'DOC2'])
  streamProgress?: StreamProgress;
}