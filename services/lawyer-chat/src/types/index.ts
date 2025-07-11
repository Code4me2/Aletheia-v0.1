// Common type definitions for the Lawyer Chat application

// Chat types
export interface Chat {
  id: string;
  title: string;
  preview?: string;
  createdAt: Date | string;
  updatedAt: Date | string;
  userId: string;
  messages?: ChatMessage[]; // Made optional since API might not always include messages
  _count?: {
    messages: number;
  };
}

export interface ChatMessage {
  id: string;
  chatId: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date | string;
  citations?: Citation[];
  references?: string[];
}

export interface Citation {
  id: string;
  title: string;
  source?: string;
  url?: string;
  excerpt?: string;
  page?: number;
  court?: string;
  date?: string;
  caseNumber?: string;
  content?: string;
}

// Analytics types
export interface AnalyticsData {
  trends?: TrendData[];
  statistics?: Statistics;
  charts?: ChartData[];
  summary?: string;
}

export interface TrendData {
  period: string;
  value: number;
  category: string;
  change?: number;
}

export interface Statistics {
  totalDocuments?: number;
  averageProcessingTime?: string;
  successRate?: string;
  [key: string]: string | number | undefined;
}

export interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'scatter';
  data: {
    labels: string[];
    datasets: ChartDataset[];
  };
}

export interface ChartDataset {
  label: string;
  data: number[];
  backgroundColor?: string | string[];
  borderColor?: string | string[];
}

// User and session types
export interface User {
  id: string;
  email: string;
  name?: string | null;
  role: 'user' | 'admin';
  emailVerified?: Date | null;
  createdAt: Date;
  updatedAt: Date;
}

export interface SessionUser {
  id: string;
  email?: string | null;
  name?: string | null;
  image?: string | null;
  role?: 'user' | 'admin';
}

// API payload types
export interface ChatPayload {
  message: string;
  tools?: string[];
  tool?: string;
  sessionId?: string;
  userId?: string;
  timestamp: string;
}

export interface WebhookPayload {
  message: string;
  tools: string[];
  tool: string;
  sessionId: string;
  userId?: string;
  timestamp: string;
}

// API response types
export interface ChatResponse {
  message?: string;
  response?: string;
  sources?: Citation[];
  references?: Citation[];
  analytics?: AnalyticsData;
}

export interface StreamEvent {
  text?: string;
  sources?: Citation[];
  analytics?: AnalyticsData;
  type: 'text' | 'sources' | 'analytics' | 'done';
}

// Form data types
export interface RegisterFormData {
  email: string;
  password: string;
  confirmPassword: string;
  name: string;
}

export interface LoginFormData {
  email: string;
  password: string;
}

// Audit log types
export interface AuditLog {
  id: string;
  action: string;
  email: string;
  ipAddress?: string;
  userAgent?: string;
  success: boolean;
  errorMessage?: string;
  createdAt: Date;
}

// Error types
export interface ApiError {
  error: string;
  message?: string;
  code?: string;
  details?: string;
}

// Logger context type
export interface LogContext {
  [key: string]: unknown;
}

// Validation types
export interface ValidationResult {
  isValid: boolean;
  sanitized?: string;
  error?: string;
}