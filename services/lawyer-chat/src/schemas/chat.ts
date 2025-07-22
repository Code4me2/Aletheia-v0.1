import { z } from 'zod';

// Base schemas
export const ChatMessageSchema = z.object({
  id: z.string(),
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  references: z.array(z.string()).optional(),
  createdAt: z.string().or(z.date()),
  updatedAt: z.string().or(z.date()).optional()
});

export const ChatSchema = z.object({
  id: z.string(),
  title: z.string(),
  preview: z.string().optional(),
  createdAt: z.string().or(z.date()),
  updatedAt: z.string().or(z.date()),
  messages: z.array(ChatMessageSchema).optional()
});

// API Response schemas
export const CreateChatResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  preview: z.string().optional(),
  createdAt: z.string().or(z.date()),
  updatedAt: z.string().or(z.date())
});

export const GetChatResponseSchema = ChatSchema.extend({
  messages: z.array(ChatMessageSchema)
});

export const SaveMessageResponseSchema = z.object({
  id: z.string(),
  role: z.enum(['user', 'assistant', 'system']),
  content: z.string(),
  references: z.array(z.string()).optional(),
  chatId: z.string(),
  createdAt: z.string().or(z.date())
});

export const CreateChatWithMessageResponseSchema = z.object({
  chat: ChatSchema,
  message: ChatMessageSchema
});

export const StreamChunkSchema = z.object({
  type: z.enum(['text', 'sources', 'analytics', 'done']),
  text: z.string().optional(),
  sources: z.array(z.string()).optional(),
  analytics: z.any().optional(),
  data: z.any().optional()
});

// Type exports
export type ChatMessage = z.infer<typeof ChatMessageSchema>;
export type Chat = z.infer<typeof ChatSchema>;
export type CreateChatResponse = z.infer<typeof CreateChatResponseSchema>;
export type GetChatResponse = z.infer<typeof GetChatResponseSchema>;
export type SaveMessageResponse = z.infer<typeof SaveMessageResponseSchema>;
export type CreateChatWithMessageResponse = z.infer<typeof CreateChatWithMessageResponseSchema>;
export type StreamChunk = z.infer<typeof StreamChunkSchema>;