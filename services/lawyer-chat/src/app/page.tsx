'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import DarkModeToggle from '@/components/DarkModeToggle';
import TaskBar from '@/components/TaskBar';
import CitationPanel from '@/components/CitationPanel';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import AuthGuard from '@/components/AuthGuard';
import MessageList from '@/components/MessageList';
import ChatInput from '@/components/ChatInput';
import ChatControls from '@/components/ChatControls';
import { useSidebarStore } from '@/store/sidebar';
import { useChatState } from '@/hooks/useChatState';
import { useChatAPI } from '@/hooks/useChatAPI';
import { getRandomMockCitation } from '@/utils/mockCitations';
import { useCsrfStore } from '@/store/csrf';
import { PDFGenerator, generateChatText, downloadBlob, downloadText } from '@/utils/pdfGenerator';
import type { Citation } from '@/types';

function LawyerChatContent() {
  const { data: session } = useSession();
  const {
    messages,
    setMessages,
    inputText,
    setInputText,
    isLoading,
    setIsLoading,
    selectedTools,
    setSelectedTools,
    showToolsDropdown,
    setShowToolsDropdown,
    currentChatId,
    setCurrentChatId,
    isCreatingChat,
    setIsCreatingChat,
    showCitationPanel,
    setShowCitationPanel,
    selectedCitation,
    setSelectedCitation,
    isCitationOnRight,
    setIsCitationOnRight,
    hasMessages
  } = useChatState();
  
  const [windowWidth, setWindowWidth] = useState(1440); // Default value for SSR
  const { isDarkMode, isTaskBarExpanded } = useSidebarStore();
  const { fetchCsrfToken } = useCsrfStore();
  
  const {
    fetchChatHistory,
    createNewChat,
    handleNewChat,
    selectChat,
    saveMessage,
    sendMessage
  } = useChatAPI({
    currentChatId,
    setCurrentChatId,
    setMessages,
    setIsLoading,
    setSelectedTools,
    setIsCreatingChat
  });

  // Fetch CSRF token on mount
  useEffect(() => {
    fetchCsrfToken();
  }, [fetchCsrfToken]);

  // Track window resize and set initial width after hydration
  useEffect(() => {
    // Add SSR guard
    if (typeof window === 'undefined') return;
    
    // Set initial width after component mounts (client-side only)
    setWindowWidth(window.innerWidth);
    
    const handleResize = () => {
      setWindowWidth(window.innerWidth);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // Calculate dynamic sizing based on window width and panel states
  const calculateResponsiveSizing = () => {
    // Ensure windowWidth is valid
    const safeWindowWidth = Math.max(320, windowWidth || 1440); // Minimum 320px width
    
    // Calculate available width
    const taskBarWidth = isTaskBarExpanded ? 280 : 56;
    const citationWidth = showCitationPanel ? 400 : 0;
    const availableWidth = Math.max(100, safeWindowWidth - taskBarWidth - citationWidth); // Ensure positive
    
    // Calculate proportional values based on available space
    // Base values for full desktop (1920px)
    const baseWidth = 1920;
    const baseAvailable = baseWidth - 56; // Base with collapsed taskbar
    const spaceRatio = Math.max(0.1, Math.min(2, availableWidth / baseAvailable)); // Clamp between 0.1 and 2
    
    // Proportional padding calculation
    const baseMsgPadding = 95; // ~2.5cm in pixels
    const baseInputPadding = 113; // ~3cm in pixels
    
    // Scale padding proportionally but with minimum values
    let messagePadding = Math.max(19, Math.min(baseMsgPadding, baseMsgPadding * spaceRatio)); // Min 0.5cm, max 2.5cm
    let inputPadding = Math.max(38, Math.min(baseInputPadding, baseInputPadding * spaceRatio)); // Min 1cm, max 3cm
    
    // Input box sizing
    const baseInputHeight = 125;
    const baseMaxHeight = 260;
    let inputHeight = Math.max(80, Math.min(baseInputHeight, baseInputHeight * Math.sqrt(spaceRatio))); // Use sqrt for less aggressive scaling
    let maxInputHeight = Math.max(160, Math.min(baseMaxHeight, baseMaxHeight * Math.sqrt(spaceRatio)));
    
    // Font size scaling
    const baseFontSize = 18; // text-lg is ~18px
    let fontSize = Math.max(14, Math.min(baseFontSize, baseFontSize * Math.sqrt(spaceRatio)));
    
    // Max width calculation for input area
    let maxWidth = availableWidth > 1200 ? '57.6rem' : availableWidth > 800 ? '48rem' : '100%';
    
    // Assistant message width calculation (1.3x larger, responsive)
    const baseAssistantWidth = 672; // 42rem in pixels (max-w-2xl)
    const assistantWidth = baseAssistantWidth * 1.3; // 1.3x larger
    let responsiveAssistantWidth = Math.min(assistantWidth, availableWidth - 80); // Leave 40px margin on each side
    
    // Ensure minimum width for readability
    responsiveAssistantWidth = Math.max(320, responsiveAssistantWidth);
    
    // Special handling for very small spaces
    if (availableWidth < 500) {
      messagePadding = 19; // 0.5cm
      inputPadding = 19; // 0.5cm
      inputHeight = 80;
      maxInputHeight = 160;
      fontSize = 14;
      maxWidth = '100%';
    }
    
    // Calculate dynamic button sizing and positioning
    const baseButtonSize = 32; // Base button size at full scale
    const baseIconSize = 24; // Base icon size
    const buttonSize = Math.max(24, Math.min(baseButtonSize, baseButtonSize * Math.sqrt(spaceRatio)));
    const iconSize = Math.max(16, Math.min(baseIconSize, baseIconSize * Math.sqrt(spaceRatio)));
    const sendButtonSize = buttonSize * 1.3; // Send button 1.3x larger
    const sendIconSize = Math.round(iconSize * 1.3); // Scale icon proportionally
    const buttonPadding = Math.max(12, 16 * spaceRatio); // Dynamic padding from edges
    const sendButtonBottom = buttonPadding * 1.5; // Send button slightly higher for visual balance
    
    // Validate all values before returning
    const validateNumber = (value: number, fallback: number): number => {
      return isNaN(value) || !isFinite(value) ? fallback : value;
    };
    
    return {
      messagePadding: `${validateNumber(messagePadding, 19)}px`,
      inputPadding: `${validateNumber(inputPadding, 38)}px`,
      inputHeight: `${validateNumber(inputHeight, 80)}px`,
      maxInputHeight: `${validateNumber(maxInputHeight, 160)}px`,
      fontSize: `${validateNumber(fontSize, 14)}px`,
      maxWidth,
      assistantWidth: `${validateNumber(responsiveAssistantWidth, 320)}px`,
      buttonSize: `${validateNumber(buttonSize, 24)}px`,
      iconSize: Math.round(validateNumber(iconSize, 16)),
      sendButtonSize: `${validateNumber(sendButtonSize, 32)}px`,
      sendIconSize: Math.round(validateNumber(sendIconSize, 20)),
      buttonPadding: `${validateNumber(buttonPadding, 12)}px`,
      sendButtonBottom: `${validateNumber(sendButtonBottom, 18)}px`
    };
  };

  const { messagePadding, inputPadding, inputHeight, maxInputHeight, fontSize, maxWidth, assistantWidth, buttonSize, iconSize, sendButtonSize, sendIconSize, buttonPadding, sendButtonBottom } = calculateResponsiveSizing();

  // Check URL parameter for chat ID on mount
  useEffect(() => {
    // Add SSR guard
    if (typeof window === 'undefined') return;
    
    const params = new URLSearchParams(window.location.search);
    const chatId = params.get('chat');
    if (chatId && !currentChatId) {
      selectChat(chatId);
    }
  }, [currentChatId, selectChat]); // Added dependencies

  // Fetch chat history on mount for logged-in users
  useEffect(() => {
    if (session?.user) {
      fetchChatHistory();
    }
  }, [session, fetchChatHistory]);

  const handleSend = async () => {
    if (!inputText.trim()) return;
    
    const messageToSend = inputText;
    setInputText(''); // Clear immediately before sending
    
    await sendMessage(messageToSend, selectedTools, messages, isCreatingChat);
  };

  const handleCitationClick = () => {
    // Get a mock citation for now
    const mockCitation = getRandomMockCitation();
    setSelectedCitation(mockCitation);
    setShowCitationPanel(true);
  };

  const closeCitationPanel = () => {
    setShowCitationPanel(false);
    setSelectedCitation(null);
  };

  // Download functions
  const handleDownloadChatPDF = async () => {
    const pdfGenerator = new PDFGenerator();
    const chatMessages = messages.map(msg => ({
      role: msg.sender,
      content: msg.text,
      timestamp: msg.timestamp
    }));
    
    const blob = pdfGenerator.generateChatPDF(chatMessages, {
      title: 'Legal Research Chat History',
      includeTimestamp: true,
      includeMetadata: true
    });
    
    const filename = `legal-chat-${new Date().toISOString().split('T')[0]}.pdf`;
    downloadBlob(blob, filename);
  };

  const handleDownloadChatText = () => {
    const chatMessages = messages.map(msg => ({
      role: msg.sender,
      content: msg.text,
      timestamp: msg.timestamp
    }));
    
    const text = generateChatText(chatMessages);
    const filename = `legal-chat-${new Date().toISOString().split('T')[0]}.txt`;
    downloadText(text, filename);
  };


  return (
    <div className="flex h-screen">
      {/* Universal TaskBar - Always visible for all users */}
      <TaskBar 
        onChatSelect={selectChat}
        onNewChat={handleNewChat}
      />

      {/* Main Content Container - Adjust margin for taskbar only */}
      <div className={`flex-1 flex transition-all duration-300 ${isTaskBarExpanded ? 'ml-[280px]' : 'ml-[56px]'}`}>
        {/* Citation Panel (when on left) */}
        {showCitationPanel && selectedCitation && !isCitationOnRight && (
          <div className="flex-1 h-full">
            <ErrorBoundary
              level="component"
              isolate
              fallback={
                <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                  <div className="text-center">
                    <p className="text-gray-500 dark:text-gray-400">Unable to display citation</p>
                    <button
                      onClick={closeCitationPanel}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
                    >
                      Close panel
                    </button>
                  </div>
                </div>
              }
            >
              <CitationPanel
                citation={selectedCitation}
                onClose={closeCitationPanel}
                onSwap={() => setIsCitationOnRight(!isCitationOnRight)}
                isCitationOnRight={isCitationOnRight}
              />
            </ErrorBoundary>
          </div>
        )}
        
        {/* Chat Section */}
        <div className={`flex-1 flex flex-col transition-all duration-300 ${showCitationPanel ? 'w-1/2' : 'w-full'}`}>
        {/* Header */}
        <div className={`px-6 py-4 relative z-10`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              {!isTaskBarExpanded && (
                <div className="flex items-center gap-2">
                  <a
                    href="http://localhost:8085"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="transition-transform hover:scale-110"
                    title="Open Court Processor"
                  >
                    <img 
                      src="/chat/logo.png" 
                      alt="Logo" 
                      className="h-7 w-7 object-contain cursor-pointer"
                    />
                  </a>
                  <h1 className={`text-xl font-semibold ${isDarkMode ? 'text-white' : ''}`} style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}>Aletheia-v0.1</h1>
                </div>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              <ChatControls
                messages={messages}
                onDownloadPDF={handleDownloadChatPDF}
                onDownloadText={handleDownloadChatText}
                isDarkMode={isDarkMode}
              />
              <DarkModeToggle />
            </div>
          </div>
        </div>

        {/* Messages Window */}
        <div className="flex-1 overflow-x-hidden py-4 space-y-6 hide-scrollbar relative" style={{
          overflowY: messages.length === 0 ? 'hidden' : 'auto',
          paddingLeft: messagePadding,
          paddingRight: messagePadding
        }}>
          {/* Welcome Message - Only show when no messages */}
          {messages.length === 0 && (
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <div className="w-full mx-auto" style={{
                maxWidth: maxWidth,
                paddingLeft: inputPadding,
                paddingRight: inputPadding,
              }}>
                <h2 className="font-medium text-center" style={{ 
                  color: isDarkMode ? '#9CA3AF' : '#E1C88E',
                  fontSize: '2.52rem', // 3.6rem (text-6xl) * 0.7
                  marginBottom: '1rem'
                }}>Judicial Access Project</h2>
                <p className="text-center" style={{
                  color: isDarkMode ? '#6B7280' : '#9CA3AF',
                  fontSize: '1.125rem', // text-lg
                  marginBottom: 'calc(125px + 2cm + 3cm)' // Input height (125px) + 2cm gap + 3cm additional
                }}>Bridge the vast landscape of judicial transcript data with targeted AI retrieval and citation</p>
              </div>
            </div>
          )}
          
          <MessageList 
            messages={messages}
            isDarkMode={isDarkMode}
            isLoading={isLoading}
            assistantWidth={assistantWidth}
            onCitationClick={handleCitationClick}
          />
        </div>

        {/* Input Area */}
        <div className={`transition-all duration-500 ${
          hasMessages 
            ? 'px-6 py-4 flex justify-center' 
            : 'absolute inset-0 flex items-center justify-center'
        }`} style={{
          left: hasMessages ? 'auto' : isTaskBarExpanded ? '280px' : '56px',
          right: hasMessages ? 'auto' : '0'
        }}>
          <div style={{
            width: assistantWidth,
            paddingLeft: messagePadding,
            paddingRight: messagePadding,
          }}>
            <ChatInput
              inputText={inputText}
              setInputText={setInputText}
              onSend={handleSend}
              isLoading={isLoading}
              isDarkMode={isDarkMode}
              selectedTools={selectedTools}
              setSelectedTools={setSelectedTools}
              showToolsDropdown={showToolsDropdown}
              setShowToolsDropdown={setShowToolsDropdown}
              inputHeight={inputHeight}
              maxInputHeight={maxInputHeight}
              fontSize={fontSize}
              buttonSize={buttonSize}
              iconSize={iconSize}
              sendButtonSize={sendButtonSize}
              sendIconSize={sendIconSize}
              buttonPadding={buttonPadding}
              sendButtonBottom={sendButtonBottom}
            />
          </div>
        </div>
        </div>
        
        {/* Citation Panel (when on right) */}
        {showCitationPanel && selectedCitation && isCitationOnRight && (
          <div className="flex-1 h-full">
            <ErrorBoundary
              level="component"
              isolate
              fallback={
                <div className="h-full flex items-center justify-center bg-gray-50 dark:bg-gray-900">
                  <div className="text-center">
                    <p className="text-gray-500 dark:text-gray-400">Unable to display citation</p>
                    <button
                      onClick={closeCitationPanel}
                      className="mt-2 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400"
                    >
                      Close panel
                    </button>
                  </div>
                </div>
              }
            >
              <CitationPanel
                citation={selectedCitation}
                onClose={closeCitationPanel}
                onSwap={() => setIsCitationOnRight(!isCitationOnRight)}
                isCitationOnRight={isCitationOnRight}
              />
            </ErrorBoundary>
          </div>
        )}
      </div>
    </div>
  );
}

// Export with error boundary and auth guard wrapper
export default function LawyerChat() {
  return (
    <ErrorBoundary level="page">
      <AuthGuard>
        <LawyerChatContent />
      </AuthGuard>
    </ErrorBoundary>
  );
}

