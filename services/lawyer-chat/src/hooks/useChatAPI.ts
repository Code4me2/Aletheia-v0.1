import { useSession } from 'next-auth/react';
import { api } from '@/utils/api';
import { getApiEndpoint } from '@/lib/api-config';
import { createLogger } from '@/utils/logger';
import { cleanAIResponse, detectTruncatedResponse } from '@/utils/textFilters';
import { extractCitationMarkers } from '@/utils/citationExtractor';
import { mockAnalyticsData } from '@/utils/mockAnalytics';
import { getErrorMessage } from '@/utils/errors';
import { 
  CreateChatResponseSchema, 
  GetChatResponseSchema, 
  SaveMessageResponseSchema,
  CreateChatWithMessageResponseSchema,
  StreamChunkSchema 
} from '@/schemas/chat';
import type { ChatMessage, AnalyticsData } from '@/types';
import type { Message } from '@/types/chat';

const logger = createLogger('chat-api');

interface UseChatAPIProps {
  currentChatId: string | null;
  setCurrentChatId: (id: string | null) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setIsLoading: (loading: boolean) => void;
  setSelectedTools: (tools: string[]) => void;
  setIsCreatingChat: (creating: boolean) => void;
}

export function useChatAPI({
  currentChatId,
  setCurrentChatId,
  setMessages,
  setIsLoading,
  setSelectedTools,
  setIsCreatingChat
}: UseChatAPIProps) {
  const { data: session } = useSession();

  const fetchChatHistory = async () => {
    try {
      const response = await api.get(getApiEndpoint('/chats'));
      if (response.ok) {
        // Chat history is now managed by TaskBar component
        // Consume response body to release memory
        await response.text();
      }
    } catch (error) {
      logger.error('Error fetching chat history', getErrorMessage(error));
    }
  };

  const createNewChat = async () => {
    if (!session?.user) return null;
    
    try {
      setIsCreatingChat(true);
      const response = await api.post(getApiEndpoint('/chats'), { title: 'New Chat' });
      
      if (response.ok) {
        const json = await response.json();
        const newChat = CreateChatResponseSchema.parse(json);
        setCurrentChatId(newChat.id);
        setMessages([]);
        await fetchChatHistory();
        return newChat.id;
      }
    } catch (error) {
      logger.error('Error creating chat', getErrorMessage(error));
    } finally {
      setIsCreatingChat(false);
    }
    return null;
  };

  const handleNewChat = () => {
    // Clear current chat state
    setCurrentChatId(null);
    setMessages([]);
    // Clear URL parameter
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.delete('chat');
      window.history.replaceState({}, '', url);
    }
  };

  const selectChat = async (chatId: string) => {
    try {
      const response = await api.get(getApiEndpoint(`/chats/${chatId}`));
      if (response.ok) {
        const json = await response.json();
        const chat = GetChatResponseSchema.parse(json);
        setCurrentChatId(chatId);
        
        // Convert database messages to frontend format
        const convertedMessages = chat.messages.map((msg) => ({
          id: Date.now() + Math.random(),
          sender: msg.role as 'user' | 'assistant',
          text: msg.content,
          references: msg.references || [],
          timestamp: new Date(msg.createdAt)
        }));
        
        setMessages(convertedMessages);
      }
    } catch (error) {
      logger.error('Error fetching chat', getErrorMessage(error), { chatId });
    }
  };

  const saveMessage = async (role: string, content: string, references: string[] = [], chatId?: string) => {
    const chatIdToUse = chatId || currentChatId;
    if (!session?.user || !chatIdToUse) return false;
    
    try {
      const response = await api.post(getApiEndpoint(`/chats/${chatIdToUse}/messages`), { role, content, references });
      if (!response.ok) {
        logger.error('Failed to save message', { status: response.status });
        return false;
      }
      
      // Update chat history to reflect new message
      await fetchChatHistory();
      return true;
    } catch (error) {
      logger.error('Error saving message', getErrorMessage(error), { chatId: chatIdToUse, role, content: content.substring(0, 50) });
      return false;
    }
  };

  const sendMessage = async (inputText: string, selectedTools: string[], messages: Message[], isCreatingChat: boolean, documentContext?: any[]) => {
    if (!inputText.trim() || isCreatingChat) return;

    let chatIdToUse = currentChatId;
    const messageText = inputText;
    
    const userMessage: Message = {
      id: Date.now(),
      sender: 'user',
      text: messageText,
      timestamp: new Date(),
      documentContext: documentContext // Store documents with user message
    };

    setMessages(prev => [...prev, userMessage]);
    
    // Create new chat with first message atomically if needed
    if (!chatIdToUse && messages.length === 0) {
      try {
        setIsCreatingChat(true);
        const response = await api.post(getApiEndpoint('/chats/with-message'), {
          message: messageText,
          title: 'New Chat'
        });
        
        if (!response.ok) {
          logger.error('Failed to create chat', { status: response.status });
          return;
        }
        
        const json = await response.json();
        const result = CreateChatWithMessageResponseSchema.parse(json);
        chatIdToUse = result.chat.id;
        setCurrentChatId(chatIdToUse);
        
        await fetchChatHistory();
      } catch (error) {
        logger.error('Failed to create chat with message', getErrorMessage(error));
        return;
      } finally {
        setIsCreatingChat(false);
      }
    } else if (chatIdToUse) {
      // Save user message to existing chat
      await saveMessage('user', messageText, [], chatIdToUse);
    }
    
    setIsLoading(true);

    // Create empty assistant message for streaming
    const assistantId = Date.now() + 1;
    const assistantMessage: Message = {
      id: assistantId,
      sender: 'assistant',
      text: '',
      references: [],
      analytics: undefined,
      timestamp: new Date(),
      citedDocumentIds: [] // Will be populated as citations are found
    };
    
    // Add mock analytics data if analytics tool is selected (for testing)
    const hasAnalyticsTool = selectedTools.includes('analytics');

    setMessages(prev => [...prev, assistantMessage]);

    try {
      // Call the API endpoint
      const response = await api.post(getApiEndpoint('/chat'), {
        message: inputText,
        tools: selectedTools,
        sessionKey: chatIdToUse || `temp-${Date.now()}-${Math.random().toString(36).substring(2, 11)}`,
        sessionId: session?.user?.email || 'anonymous',
        userId: session?.user?.email,
        documentContext: documentContext // Include document context if provided
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Handle streaming response
      if (response.headers.get('content-type')?.includes('text/event-stream')) {
        await handleStreamingResponse(response, assistantId, chatIdToUse, hasAnalyticsTool, documentContext);
      } else {
        // Handle regular JSON response
        await handleJsonResponse(response, assistantId, chatIdToUse, hasAnalyticsTool, documentContext);
      }
    } catch (error) {
      logger.error('Error sending message', getErrorMessage(error));
      
      // Update assistant message with error
      setMessages(prev => 
        prev.map(msg => 
          msg.id === assistantId 
            ? { 
                ...msg, 
                text: 'I apologize, but I encountered an error processing your request. Please try again later or contact support if the issue persists.' 
              }
            : msg
        )
      );
    } finally {
      setIsLoading(false);
      setSelectedTools([]);
    }
  };

  const handleStreamingResponse = async (
    response: Response, 
    assistantId: number, 
    chatIdToUse: string | null,
    hasAnalyticsTool: boolean,
    documentContext?: any[]
  ) => {
    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    if (reader) {
      let accumulatedText = '';
      let buffer = '';
      let sources: string[] = [];
      let analytics: AnalyticsData | undefined = undefined;
      let lastSaveTime = Date.now();
      let messageId: string | null = null;
      let saveInProgress = false;
      let currentStage: string | null = null;
      let startTime = Date.now();
      
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
        
        const chunk = decoder.decode(value);
        buffer += chunk;
        
        // Split by newlines and process each line
        const lines = buffer.split('\n');
        buffer = lines[lines.length - 1]; // Keep incomplete line in buffer
        
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          
          if (line.startsWith('data: ')) {
            try {
              const parsed = JSON.parse(line.slice(6));
              // Handle both old and new event types
              const data = parsed.type ? parsed : StreamChunkSchema.parse(parsed);
              
              // Handle progress events (new)
              if (data.type === 'status' || data.type === 'progress') {
                currentStage = data.stage || currentStage;
                const elapsedTime = Date.now() - startTime;
                
                // Update message with progress info
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantId 
                      ? { 
                          ...msg, 
                          streamProgress: {
                            stage: data.stage,
                            message: data.message,
                            percent: data.percent,
                            elapsedTime
                          }
                        }
                      : msg
                  )
                );
              } else if (data.type === 'text' && data.text) {
                // Append chunk directly to accumulated text
                accumulatedText += data.text;
                
                // Clean the accumulated text to remove duplicate "CITATIONS" entries
                const cleanedText = cleanAIResponse(accumulatedText);
                
                // Check if response appears to be truncated/restarting
                if (detectTruncatedResponse(cleanedText)) {
                  logger.warn('Detected truncated or restarting response');
                }
                
                // Extract citations if we have document context
                let citedDocumentIds: string[] = [];
                if (documentContext && documentContext.length > 0) {
                  citedDocumentIds = extractCitationMarkers(cleanedText);
                }
                
                // Update message with cleaned text and citations
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, text: cleanedText, citedDocumentIds }
                      : msg
                  )
                );
                
                // Save message immediately on first chunk, then update every 2 seconds
                const now = Date.now();
                if ((!messageId || now - lastSaveTime > 2000) && !saveInProgress) {
                  try {
                    if (!messageId && chatIdToUse) {
                      // First save - create the message with retry
                      saveInProgress = true;
                      try {
                        const response = await api.post(getApiEndpoint(`/chats/${chatIdToUse}/messages`), {
                          role: 'assistant',
                          content: cleanedText,
                          references: sources
                        });
                        
                        if (response.ok) {
                          const json = await response.json();
                          const savedMessage = SaveMessageResponseSchema.parse(json);
                          messageId = savedMessage.id;
                        } else {
                          logger.error('Failed to save streaming message', { status: response.status });
                        }
                      } catch (error) {
                        logger.error('Failed to save streaming message', getErrorMessage(error));
                      } finally {
                        saveInProgress = false;
                      }
                    } else if (messageId && chatIdToUse) {
                      // Update existing message
                      await api.patch(getApiEndpoint(`/chats/${chatIdToUse}/messages/${messageId}`), {
                        content: accumulatedText,
                        references: sources
                      });
                    }
                    lastSaveTime = now;
                  } catch (error) {
                    logger.error('Error saving streaming message', getErrorMessage(error));
                  }
                }
              } else if (data.type === 'sources') {
                sources = data.sources || [];
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, references: sources }
                      : msg
                  )
                );
              } else if (data.type === 'analytics') {
                analytics = data.analytics || data.data;
                setMessages(prev => 
                  prev.map(msg => 
                    msg.id === assistantId 
                      ? { ...msg, analytics: analytics }
                      : msg
                  )
                );
              } else if (data.type === 'done') {
                // Add mock analytics if analytics tool was used (for testing)
                if (hasAnalyticsTool && !analytics) {
                  analytics = mockAnalyticsData;
                  setMessages(prev => 
                    prev.map(msg => 
                      msg.id === assistantId 
                        ? { ...msg, analytics: analytics }
                        : msg
                    )
                  );
                }
                // Final save/update with complete content
                try {
                  if (messageId && chatIdToUse) {
                    // Update existing message with final content
                    const response = await api.patch(getApiEndpoint(`/chats/${chatIdToUse}/messages/${messageId}`), {
                      content: cleanAIResponse(accumulatedText),
                      references: sources
                    });
                    if (!response.ok) {
                      logger.warn('Failed to update message', { status: response.status });
                    }
                  } else if (chatIdToUse) {
                    // Create message if not already saved
                    await saveMessage('assistant', cleanAIResponse(accumulatedText), sources, chatIdToUse);
                  }
                } catch (error) {
                  logger.error('Error saving final message', getErrorMessage(error));
                  // Silently handle the error
                }
              }
            } catch (e) {
              logger.error('Error parsing SSE data', getErrorMessage(e), { line });
            }
          }
        }
      }
      } catch (error) {
        logger.error('Stream processing error', getErrorMessage(error));
        // Update the assistant message with error state
        setMessages(prev => 
          prev.map(msg => 
            msg.id === assistantId 
              ? { ...msg, text: msg.text || 'An error occurred while processing the response.' }
              : msg
          )
        );
      } finally {
        // Clean up the reader
        try {
          await reader.cancel();
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    }
  };

  const handleJsonResponse = async (
    response: Response, 
    assistantId: number, 
    chatIdToUse: string | null,
    hasAnalyticsTool: boolean,
    documentContext?: any[]
  ) => {
    const data = await response.json();
    
    // Update assistant message with response
    const assistantText = data.message || data.response || 'I received your message. Processing...';
    const assistantReferences = data.references || [];
    const assistantAnalytics = data.analytics || (hasAnalyticsTool ? mockAnalyticsData : undefined);
    
    setMessages(prev => 
      prev.map(msg => 
        msg.id === assistantId 
          ? { 
              ...msg, 
              text: assistantText, 
              references: assistantReferences,
              analytics: assistantAnalytics
            }
          : msg
      )
    );
    
    // Save assistant message to database
    if (chatIdToUse) {
      await saveMessage('assistant', assistantText, assistantReferences, chatIdToUse);
    }
  };

  return {
    fetchChatHistory,
    createNewChat,
    handleNewChat,
    selectChat,
    saveMessage,
    sendMessage
  };
}