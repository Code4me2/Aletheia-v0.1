import React, { useRef } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  inputText: string;
  setInputText: (text: string) => void;
  onSend: () => void;
  isLoading: boolean;
  isDarkMode: boolean;
  selectedTools: string[];
  setSelectedTools: (tools: string[]) => void;
  showToolsDropdown: boolean;
  setShowToolsDropdown: (show: boolean) => void;
  inputHeight: string;
  maxInputHeight: string;
  fontSize: string;
  buttonSize: string;
  iconSize: number;
  sendButtonSize: string;
  sendIconSize: number;
  buttonPadding: string;
  sendButtonBottom: string;
}

export default function ChatInput({
  inputText,
  setInputText,
  onSend,
  isLoading,
  isDarkMode,
  selectedTools,
  setSelectedTools,
  showToolsDropdown,
  setShowToolsDropdown,
  inputHeight,
  maxInputHeight,
  fontSize,
  buttonSize,
  iconSize,
  sendButtonSize,
  sendIconSize,
  buttonPadding,
  sendButtonBottom
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        id="chat-input"
        name="chatInput"
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask your legal question..."
        className={`w-full ${isDarkMode ? 'bg-[#25262b] text-gray-100 placeholder-gray-400' : 'bg-gray-100 text-gray-900 placeholder-gray-500'} rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none transition-all duration-500 px-4 py-6 pl-9 pr-9 break-words hide-scrollbar`}
        style={{
          height: inputHeight,
          maxHeight: maxInputHeight,
          fontSize: fontSize,
          overflowY: 'auto',
          overflowX: 'hidden',
          wordWrap: 'break-word',
          overflowWrap: 'break-word',
          whiteSpace: 'pre-wrap'
        }}
        onInput={(e) => {
          const target = e.target as HTMLTextAreaElement;
          target.style.height = inputHeight;
          const scrollHeight = target.scrollHeight;
          const maxHeight = parseInt(maxInputHeight) || 160;
          target.style.height = `${Math.min(scrollHeight, maxHeight)}px`;
        }}
        disabled={false}
      />
      
      {/* Tools Button and Selected Tools */}
      <div className="absolute transition-all duration-500 flex items-center gap-2" style={{ 
        left: buttonPadding, 
        bottom: buttonPadding 
      }}>
        <div className="relative tools-dropdown-container">
          <button
            onClick={() => setShowToolsDropdown(!showToolsDropdown)}
            className={`flex items-center justify-center ${isDarkMode ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'} transition-colors`}
            aria-label="Select tool"
            title="Select tool"
            style={{
              width: buttonSize,
              height: buttonSize
            }}
          >
            {/* Custom Settings/Filter Icon */}
            <svg 
              width={Math.round(iconSize * 1.3)} 
              height={Math.round(iconSize * 1.3)} 
              viewBox="0 0 24 24" 
              fill="none" 
              xmlns="http://www.w3.org/2000/svg"
              className="transition-all"
            >
              {/* Top line with circle on left */}
              <line 
                x1="3" 
                y1="8" 
                x2="21" 
                y2="8" 
                stroke="currentColor" 
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle 
                cx="7" 
                cy="8" 
                r="3" 
                fill={isDarkMode ? '#25262b' : '#ffffff'}
                stroke="currentColor" 
                strokeWidth="2"
              />
              <circle 
                cx="7" 
                cy="8" 
                r="1.5" 
                fill="currentColor"
              />
              
              {/* Bottom line with circle on right */}
              <line 
                x1="3" 
                y1="16" 
                x2="21" 
                y2="16" 
                stroke="currentColor" 
                strokeWidth="2"
                strokeLinecap="round"
              />
              <circle 
                cx="17" 
                cy="16" 
                r="3" 
                fill={isDarkMode ? '#25262b' : '#ffffff'}
                stroke="currentColor" 
                strokeWidth="2"
              />
              <circle 
                cx="17" 
                cy="16" 
                r="1.5" 
                fill="currentColor"
              />
            </svg>
          </button>
          
          {/* Tools Dropdown */}
          {showToolsDropdown && (
            <div 
              className={`absolute bottom-full left-0 mb-2 ${isDarkMode ? 'bg-[#25262b] border border-gray-700' : 'bg-white border border-gray-200'} shadow-lg z-10`}
              style={{
                width: '147px', // 210px * 0.7 = 147px
                height: '135px', // 180px * 0.75 = 135px
                borderRadius: '16px', // Soft edges
                padding: '12px'
              }}
            >
              <div className="space-y-2">
                <button
                  onClick={() => {
                    if (selectedTools.includes('page-turn')) {
                      setSelectedTools(selectedTools.filter(t => t !== 'page-turn'));
                    } else {
                      setSelectedTools([...selectedTools, 'page-turn']);
                    }
                  }}
                  className={`w-full text-left px-4 py-3 text-sm font-semibold transition-all duration-200 rounded-lg ${
                    selectedTools.includes('page-turn')
                      ? isDarkMode ? 'bg-[#404147] text-white' : 'bg-[#E1C88E] text-[#004A84]'
                      : isDarkMode ? 'text-gray-300 hover:bg-[#404147]' : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Page Turn
                </button>
                
                <button
                  onClick={() => {
                    if (selectedTools.includes('analytics')) {
                      setSelectedTools(selectedTools.filter(t => t !== 'analytics'));
                    } else {
                      setSelectedTools([...selectedTools, 'analytics']);
                    }
                  }}
                  className={`w-full text-left px-4 py-3 text-sm font-semibold transition-all duration-200 rounded-lg ${
                    selectedTools.includes('analytics')
                      ? isDarkMode ? 'bg-[#404147] text-white' : 'bg-[#E1C88E] text-[#004A84]'
                      : isDarkMode ? 'text-gray-300 hover:bg-[#404147]' : 'text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  Analytics
                </button>
              </div>
            </div>
          )}
        </div>
        
        {/* Selected Tools Chips */}
        {selectedTools.length > 0 && (
          <div className="flex items-center gap-2">
            {selectedTools.map(tool => (
              <div
                key={tool}
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium transition-all duration-200 ${
                  isDarkMode 
                    ? 'bg-[#404147] text-white' 
                    : 'bg-[#E1C88E] text-[#004A84]'
                }`}
                style={{
                  fontSize: `${Math.max(10, (parseInt(fontSize) || 14) * 0.75)}px`,
                  height: `${Math.max(16, (parseInt(buttonSize) || 24) * 0.8)}px`
                }}
              >
                <span>{tool === 'page-turn' ? 'Page Turn' : 'Analytics'}</span>
                <button
                  onClick={() => setSelectedTools(selectedTools.filter(t => t !== tool))}
                  className={`ml-1 hover:opacity-70 transition-opacity`}
                  aria-label={`Remove ${tool}`}
                >
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor">
                    <path d="M7.41 6l2.29-2.29a1 1 0 0 0-1.41-1.41L6 4.59 3.71 2.29a1 1 0 0 0-1.41 1.41L4.59 6 2.29 8.29a1 1 0 1 0 1.41 1.41L6 7.41l2.29 2.29a1 1 0 0 0 1.41-1.41L7.41 6z"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
      
      {/* Send Button - Inside input box */}
      <button
        onClick={onSend}
        disabled={!inputText.trim()}
        aria-label="Send message"
        title="Send message"
        className={`absolute transition-all duration-300 rounded-lg flex items-center justify-center ${
          inputText.trim() 
            ? 'opacity-100 scale-100' 
            : 'opacity-0 scale-0 pointer-events-none'
        }`}
        style={{ 
          backgroundColor: isDarkMode ? 'transparent' : '#C7A562',
          border: isDarkMode ? '2px solid #d1d1d1' : 'none',
          color: isDarkMode ? '#d1d1d1' : '#004A84',
          right: buttonPadding,
          bottom: sendButtonBottom,
          width: sendButtonSize,
          height: sendButtonSize
        }}
        onMouseEnter={(e) => {
          const target = e.target as HTMLButtonElement;
          if (!target.disabled) {
            if (!isDarkMode) target.style.backgroundColor = '#B59552';
            else target.style.backgroundColor = '#404147';
          }
        }}
        onMouseLeave={(e) => {
          const target = e.target as HTMLButtonElement;
          if (!target.disabled) {
            if (isDarkMode) target.style.backgroundColor = 'transparent';
            else target.style.backgroundColor = '#C7A562';
          }
        }}
      >
        <Send size={sendIconSize} />
      </button>
    </div>
  );
}