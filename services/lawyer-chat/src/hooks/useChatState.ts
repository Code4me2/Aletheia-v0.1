import { useState, useEffect } from 'react';
import type { Citation } from '@/types';
import type { Message } from '@/types/chat';

export type { Message };

interface UseChatStateReturn {
  messages: Message[];
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  inputText: string;
  setInputText: React.Dispatch<React.SetStateAction<string>>;
  isLoading: boolean;
  setIsLoading: React.Dispatch<React.SetStateAction<boolean>>;
  selectedTools: string[];
  setSelectedTools: React.Dispatch<React.SetStateAction<string[]>>;
  showToolsDropdown: boolean;
  setShowToolsDropdown: React.Dispatch<React.SetStateAction<boolean>>;
  currentChatId: string | null;
  setCurrentChatId: React.Dispatch<React.SetStateAction<string | null>>;
  isCreatingChat: boolean;
  setIsCreatingChat: React.Dispatch<React.SetStateAction<boolean>>;
  showCitationPanel: boolean;
  setShowCitationPanel: React.Dispatch<React.SetStateAction<boolean>>;
  selectedCitation: Citation | null;
  setSelectedCitation: React.Dispatch<React.SetStateAction<Citation | null>>;
  isCitationOnRight: boolean;
  setIsCitationOnRight: React.Dispatch<React.SetStateAction<boolean>>;
  hasMessages: boolean;
}

export function useChatState(): UseChatStateReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTools, setSelectedTools] = useState<string[]>([]);
  const [showToolsDropdown, setShowToolsDropdown] = useState(false);
  const [currentChatId, setCurrentChatId] = useState<string | null>(null);
  const [isCreatingChat, setIsCreatingChat] = useState(false);
  const [showCitationPanel, setShowCitationPanel] = useState(false);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [isCitationOnRight, setIsCitationOnRight] = useState(true);

  const hasMessages = messages.length > 0;

  // Close tools dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.tools-dropdown-container')) {
        setShowToolsDropdown(false);
      }
    };

    if (showToolsDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showToolsDropdown]);

  // NOTE: URL parameter checking is handled in the parent component
  // since it needs access to selectChat function
  
  // Update URL when chat changes
  useEffect(() => {
    // Add SSR guard
    if (typeof window === 'undefined') return;
    
    if (currentChatId) {
      const url = new URL(window.location.href);
      url.searchParams.set('chat', currentChatId);
      window.history.replaceState({}, '', url);
    } else {
      // Remove chat parameter when no chat is selected
      const url = new URL(window.location.href);
      url.searchParams.delete('chat');
      window.history.replaceState({}, '', url);
    }
  }, [currentChatId]);

  return {
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
  };
}