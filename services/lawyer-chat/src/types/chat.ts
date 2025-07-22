import type { AnalyticsData } from '@/types';

export interface Message {
  id: number;
  sender: 'user' | 'assistant';
  text: string;
  references?: string[];
  analytics?: AnalyticsData;
  timestamp: Date;
}