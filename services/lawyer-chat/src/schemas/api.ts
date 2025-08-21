import { z } from 'zod';

// Document schema for court documents
export const DocumentSchema = z.object({
  id: z.number(),
  case: z.string().optional(),
  type: z.string(),
  judge: z.string(),
  court: z.string().optional(),  // Make court optional since API doesn't always provide it
  text: z.string().optional(),
  text_length: z.number(),
  preview: z.string().optional()
});

// Chat API request schema
export const ChatRequestSchema = z.object({
  message: z.string().min(1).max(10000),
  tools: z.array(z.string()).optional().default([]),
  sessionKey: z.string().optional(),
  sessionId: z.string().optional(),
  userId: z.string().optional(),
  documentContext: z.array(DocumentSchema).optional()
});

// Type exports
export type ChatRequest = z.infer<typeof ChatRequestSchema>;
export type Document = z.infer<typeof DocumentSchema>;