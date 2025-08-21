'use client';

import { useState, useCallback, useRef } from 'react';
import { Send, FileText, Loader2 } from 'lucide-react';
import { DocumentSelector } from '@/components/document-selector/DocumentSelector';
import { courtAPI } from '@/lib/court-api';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  documentIds?: number[];
  timestamp: Date;
}

export function ChatWithDocuments() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [documentContext, setDocumentContext] = useState<string>('');
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleDocumentSelection = useCallback(async (docIds: number[]) => {
    setSelectedDocIds(docIds);
    setIsLoadingContext(true);

    try {
      // Fetch text content for selected documents
      const textPromises = docIds.map(id => courtAPI.getDocumentText(id));
      const texts = await Promise.all(textPromises);
      
      // Create context with document markers
      const context = texts.map((text, i) => {
        // Limit each document to 10KB to stay within token limits
        const truncated = text.substring(0, 10000);
        return `[Document ${docIds[i]}]\n${truncated}\n[End Document ${docIds[i]}]`;
      }).join('\n\n');
      
      setDocumentContext(context);
    } catch (error) {
      console.error('Failed to load document context:', error);
    } finally {
      setIsLoadingContext(false);
    }
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || selectedDocIds.length === 0 || isSending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      documentIds: selectedDocIds,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      // Send to existing n8n webhook with document context
      const webhookUrl = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL || 
                        '/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177';
      
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'chat',
          message: input,
          context: documentContext,
          documentIds: selectedDocIds,
          timestamp: new Date().toISOString()
        })
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || data.message || 'No response received',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      scrollToBottom();
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date()
      }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Panel - Document Selection */}
      <div className="w-1/3 min-w-[300px] max-w-[400px] border-r bg-white overflow-y-auto">
        <DocumentSelector onSelectionComplete={handleDocumentSelection} />
        
        {selectedDocIds.length > 0 && (
          <div className="p-4 bg-green-50 border-t">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-green-600" />
              <span className="text-sm text-green-700 font-medium">
                {selectedDocIds.length} document{selectedDocIds.length !== 1 ? 's' : ''} loaded
              </span>
            </div>
            {isLoadingContext && (
              <div className="flex items-center gap-2 mt-1">
                <Loader2 className="w-3 h-3 animate-spin text-gray-500" />
                <span className="text-xs text-gray-500">Processing documents...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Panel - Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-lg font-medium">Select documents to start</p>
              <p className="text-sm mt-1">Choose court opinions from the left panel</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex",
                msg.role === 'user' ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-2",
                  msg.role === 'user' 
                    ? "bg-blue-500 text-white" 
                    : "bg-white border shadow-sm"
                )}
              >
                <div className="text-sm font-medium mb-1">
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                {msg.documentIds && msg.documentIds.length > 0 && (
                  <div className="text-xs mt-2 opacity-70">
                    Using documents: {msg.documentIds.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isSending && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t bg-white p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder={
                selectedDocIds.length > 0 
                  ? "Ask about the selected documents..." 
                  : "Select documents first to enable chat..."
              }
              disabled={selectedDocIds.length === 0 || isSending}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
            <button
              onClick={sendMessage}
              disabled={selectedDocIds.length === 0 || !input.trim() || isSending}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}