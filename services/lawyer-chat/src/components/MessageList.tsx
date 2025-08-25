import React, { useRef, useEffect, useMemo } from 'react';
import SafeMarkdown from '@/components/SafeMarkdown';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import AnalyticsDropdown from '@/components/AnalyticsDropdown';
import { StreamProgressCompact } from '@/components/StreamProgress';
import { hasCitations } from '@/utils/citationExtractor';
import type { Message } from '@/types/chat';

interface MessageListProps {
  messages: Message[];
  isDarkMode: boolean;
  isLoading: boolean;
  assistantWidth: string;
  onCitationClick: (messageId?: number) => void;
}

export default function MessageList({ 
  messages, 
  isDarkMode, 
  isLoading, 
  assistantWidth,
  onCitationClick 
}: MessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <>
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.sender === 'user' ? 'justify-center' : 'justify-center'}`}
        >
          <div className={`${message.sender === 'user' ? 'order-2' : 'order-1'}`} style={{
            width: assistantWidth, // Both use same width for alignment
            marginRight: '0'
          }}>
            {/* Message bubble */}
            <div className={message.sender === 'user' ? 'flex justify-end' : ''}>
              <div
                className={`${
                  message.sender === 'user'
                    ? 'rounded-3xl shadow-sm text-white inline-block'
                    : isDarkMode ? 'text-gray-100' : 'text-gray-900'
                }`}
                style={{
                  padding: message.sender === 'user' 
                    ? '12px 28px' // Reduced vertical, increased horizontal for oval effect
                    : '0',
                  backgroundColor: message.sender === 'user' 
                    ? (isDarkMode ? '#2a2b2f' : '#226EA7')
                    : undefined,
                  maxWidth: message.sender === 'user' ? '80%' : undefined // Prevent user message from being too wide
                }}
              >
              <div>
                <div className="relative">
                  {message.sender === 'user' ? (
                    <p className="text-sm leading-relaxed" dir="ltr">{message.text}</p>
                  ) : (
                    <div className="text-sm leading-relaxed" style={{
                      padding: '12.48px 14.144px', // Restored original padding
                      direction: 'ltr',
                      unicodeBidi: 'embed',
                      textAlign: 'left',
                      minHeight: '1.5em' // Prevent layout shift during streaming
                    }}>
                      {message.text === '' && isLoading && message.id === messages[messages.length - 1].id ? (
                        message.streamProgress ? (
                          <StreamProgressCompact
                            stage={message.streamProgress.stage as any}
                            message={message.streamProgress.message}
                            isDarkMode={isDarkMode}
                          />
                        ) : (
                          <div className={`loading-dots ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        )
                      ) : (
                      <div dir="ltr" style={{ unicodeBidi: 'plaintext' }}>
                        <SafeMarkdown 
                          content={message.text}
                          className="max-w-none markdown-content"
                          citedDocumentIds={message.citedDocumentIds}
                          onCitationClick={() => {
                            // Pass the message ID to the parent handler
                            onCitationClick(message.id);
                          }}
                        />
                      </div>
                      )}
                    </div>
                  )}
                  
                  {/* Citation and Analytics Buttons - Show after response is complete */}
                  {message.sender === 'assistant' && message.text && !(isLoading && message.id === messages[messages.length - 1].id) && (
                    <div className={`mt-3 w-full flex items-center gap-2`} key={`buttons-${message.id}`}>
                      {/* Only show citations button if response contains citation markers */}
                      {hasCitations(message.text) && (
                        <button
                          onClick={() => onCitationClick(message.id)}
                          className={`flex-1 px-4 py-2 rounded-lg transition-all duration-200 transform active:scale-95 ${
                            isDarkMode 
                              ? 'bg-[#25262b] text-[#d1d1d1] hover:bg-[#404147] active:bg-[#505157]' 
                              : 'bg-[#E1C88E] text-[#004A84] hover:bg-[#C8A665] active:bg-[#B59552]'
                          }`}
                          style={{
                            fontSize: '1.092rem', // 1.3x of text-sm (0.875rem × 1.3 = 1.1375rem)
                            fontWeight: '600',
                            letterSpacing: '0.05em'
                          }}
                        >
                          CITATIONS
                        </button>
                      )}
                      
                      {/* Analytics Button - Show only if analytics data exists */}
                      {message.analytics && (
                        <ErrorBoundary
                          level="component"
                          isolate
                          fallback={
                            <div className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                              Analytics unavailable
                            </div>
                          }
                        >
                          <AnalyticsDropdown 
                            data={message.analytics}
                          />
                        </ErrorBoundary>
                      )}
                    </div>
                  )}
                </div>
              </div>
              </div>
            </div>
          </div>
        </div>
      ))}
      
      <div ref={messagesEndRef} />
    </>
  );
}