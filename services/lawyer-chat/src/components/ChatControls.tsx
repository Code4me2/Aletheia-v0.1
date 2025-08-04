import React from 'react';
import DownloadButton from '@/components/DownloadButton';
import type { Message } from '@/types/chat';

interface ChatControlsProps {
  messages: Message[];
  onDownloadPDF: () => void;
  onDownloadText: () => void;
  isDarkMode: boolean;
}

export default function ChatControls({
  messages,
  onDownloadPDF,
  onDownloadText,
  isDarkMode
}: ChatControlsProps) {
  return (
    <div className="flex items-center gap-2 relative z-50">
      {messages.length > 0 && (
        <DownloadButton 
          onDownloadPDF={onDownloadPDF}
          onDownloadText={onDownloadText}
          label="Download Chat"
          compact
        />
      )}
    </div>
  );
}