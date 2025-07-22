/**
 * Types specific to the chat module
 */

export interface ChatSettings {
  maxMessageLength: number;
  showTimestamps: boolean;
  enableMarkdown: boolean;
  persistHistory: boolean;
}

export interface ChatHistory {
  conversations: Conversation[];
  currentConversationId: string | null;
}

export interface Conversation {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: import('@/types/api.types').ChatMessage[];
}

export interface ChatUIState {
  isTyping: boolean;
  showHistory: boolean;
  showSettings: boolean;
  selectedConversationId: string | null;
}