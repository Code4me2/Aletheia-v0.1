import type { AnalyticsData } from '@/types';
import type { CourtDocument } from './court-documents';

export interface Message {
  id: number;
  sender: 'user' | 'assistant';
  text: string;
  references?: string[];
  analytics?: AnalyticsData;
  timestamp: Date;
  documentContext?: CourtDocument[];
  citations?: CourtDocument[];
}