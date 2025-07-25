import { z } from 'zod';

// Chat API request schema
export const ChatRequestSchema = z.object({
  message: z.string().min(1).max(10000),
  tools: z.array(z.string()).optional().default([]),
  sessionKey: z.string().optional(),
  sessionId: z.string().optional(),
  userId: z.string().optional()
});

// Type exports
export type ChatRequest = z.infer<typeof ChatRequestSchema>;