'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Menu, Plus, LogOut, User, Search, Trash2, Settings } from 'lucide-react';
import { useSidebarStore } from '@/store/sidebar';
import { useSession, signIn, signOut } from 'next-auth/react';
import { isToday, isYesterday, isThisWeek, isThisMonth } from 'date-fns';
import { api } from '@/utils/api';
import { createLogger } from '@/utils/logger';
import { generateChatTitle } from '@/utils/chatUtils';
import type { Chat } from '@/types';
import { ErrorBoundary } from './ErrorBoundary';

const logger = createLogger('taskbar');

interface TaskBarProps {
  onChatSelect?: (chatId: string) => void;
  onNewChat?: () => void;
}

function TaskBarContent({ onChatSelect, onNewChat }: TaskBarProps) {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [chatSearchQuery, setChatSearchQuery] = useState('');
  const [chatHistory, setChatHistory] = useState<Chat[]>([]);
  const [deleteConfirmation, setDeleteConfirmation] = useState<{ chatId: string; title: string } | null>(null);
  const [showTrashIcon, setShowTrashIcon] = useState<string | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const searchTimeoutRef = useRef<number | undefined>(undefined);
  const taskBarRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const { isDarkMode, isTaskBarExpanded, toggleTaskBar, setTaskBarExpanded } = useSidebarStore();
  const { data: session } = useSession();

  // Click outside detection for user menu and trash icon
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (userMenuRef.current && !userMenuRef.current.contains(event.target as Node)) {
        setShowUserMenu(false);
      }
      // Hide trash icon when clicking outside
      const target = event.target as HTMLElement;
      if (!target.closest('.chat-item-container')) {
        setShowTrashIcon(null);
      }
    };

    if (showUserMenu || showTrashIcon) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showUserMenu, showTrashIcon]);

  const fetchChatHistory = useCallback(async (searchTerm = '') => {
    try {
      setIsSearching(true);
      const url = searchTerm 
        ? `/api/chats?search=${encodeURIComponent(searchTerm)}`
        : '/api/chats';
      
      const response = await api.get(url);
      if (response.ok) {
        const data = await response.json();
        // Handle both old format (array) and new format (object with chats array)
        if (Array.isArray(data)) {
          setChatHistory(data);
        } else if (data.chats) {
          setChatHistory(data.chats);
        }
      }
    } catch (error) {
      logger.error('Error fetching chat history', error);
    } finally {
      setIsSearching(false);
    }
  }, []);

  // Fetch chat history for signed-in users
  useEffect(() => {
    if (session?.user) {
      fetchChatHistory();
    }
  }, [session, fetchChatHistory]);

  // Debounced search handler
  const handleSearch = useCallback((query: string) => {
    setChatSearchQuery(query);
    
    // Clear existing timeout
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    
    // Set new timeout for debounced search
    searchTimeoutRef.current = window.setTimeout(() => {
      fetchChatHistory(query);
    }, 300); // 300ms debounce
  }, [fetchChatHistory]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current);
      }
    };
  }, []);

  const handleDeleteChat = async (chatId: string) => {
    try {
      // Optimistically remove from UI for immediate feedback
      const previousHistory = chatHistory;
      setChatHistory(prev => prev.filter(chat => chat.id !== chatId));
      setDeleteConfirmation(null);
      
      // Make backend API call to permanently delete the chat
      const response = await api.delete(`/api/chats/${chatId}`);
      if (!response.ok) {
        // Revert on error
        logger.error('Failed to delete chat from backend', { chatId, status: response.status });
        setChatHistory(previousHistory);
        // Optionally show an error message to the user
        alert('Failed to delete chat. Please try again.');
      }
    } catch (error) {
      logger.error('Error deleting chat', error);
      // Refresh chat history on error, maintaining search
      fetchChatHistory(chatSearchQuery);
    }
  };

  // Get user initials
  const getUserInitials = () => {
    if (!session?.user?.name && !session?.user?.email) return '?';
    const name = session.user.name || session.user.email || '';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  };

  // Group chats by time periods
  const groupChatsByTimePeriod = (chats: Chat[]) => {
    const groups: { [key: string]: Chat[] } = {
      'Recents': [],
      'Yesterday': [],
      'Older': []
    };

    chats.forEach(chat => {
      const chatDate = new Date(chat.updatedAt);
      if (isToday(chatDate)) {
        groups['Recents'].push(chat);
      } else if (isYesterday(chatDate)) {
        groups['Yesterday'].push(chat);
      } else {
        groups['Older'].push(chat);
      }
    });

    // Sort each group by updatedAt descending
    Object.keys(groups).forEach(key => {
      groups[key].sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    });

    // Remove empty groups
    Object.keys(groups).forEach(key => {
      if (groups[key].length === 0) {
        delete groups[key];
      }
    });

    return groups;
  };


  return (
    <>
      {/* Taskbar */}
      <div
        ref={taskBarRef}
        className={`fixed left-0 top-0 h-full z-40 transition-all duration-300 flex flex-col ${
          isDarkMode ? 'bg-[#1a1b1e] border-r border-gray-500' : 'bg-gray-50 border-r border-gray-300'
        }`}
        style={{
          width: isTaskBarExpanded ? '280px' : '56px', // 56px ≈ 1.5cm
        }}
      >
        {/* Fixed Top Section */}
        <div className={`shrink-0 ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} z-10`}>
          {/* Toggle Button and Header */}
          <div className="relative">
            <div className={`flex items-center ${isTaskBarExpanded ? 'px-4 justify-between' : 'px-2 justify-center'} pt-2 pb-4`}>
              {isTaskBarExpanded ? (
                <>
                  {/* Logo and Title on the left */}
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
                        className="h-6 w-6 object-contain cursor-pointer"
                      />
                    </a>
                    <h1 className="text-lg font-semibold" style={{ color: isDarkMode ? '#d1d1d1' : '#004A84' }}>
                      Aletheia-v0.1
                    </h1>
                  </div>
                  {/* Hamburger toggle on the right */}
                  <button
                    onClick={() => toggleTaskBar()}
                    className={`p-2 flex items-center justify-center transition-all duration-300 rounded-lg ${
                      isDarkMode 
                        ? 'hover:bg-[#404147]' 
                        : 'hover:bg-gray-100'
                    }`}
                    style={{ color: isDarkMode ? '#d1d1d1' : '#004A84' }}
                    aria-label="Collapse menu"
                  >
                    <Menu size={24} strokeWidth={2.5} />
                  </button>
                </>
              ) : (
                /* Hamburger toggle centered when collapsed */
                <button
                  onClick={() => toggleTaskBar()}
                  className={`p-2 flex items-center justify-center transition-all duration-300 rounded-lg ${
                    isDarkMode 
                      ? 'hover:bg-[#404147]' 
                      : 'hover:bg-gray-100'
                  }`}
                  style={{ color: isDarkMode ? '#d1d1d1' : '#004A84' }}
                  aria-label="Expand menu"
                >
                  <Menu size={24} strokeWidth={2.5} />
                </button>
              )}
            </div>
            
            {/* Divider line - positioned to align with Aletheia text */}
            <div className={`absolute left-0 right-0 ${isDarkMode ? 'bg-gray-700' : 'bg-gray-300'}`} style={{ 
              height: '1px',
              bottom: '0'
            }}></div>
          </div>

          {/* New Chat Button - Always Circular */}
          <div className={`flex items-center mt-4 ${isTaskBarExpanded ? 'px-4 justify-start' : 'px-2 justify-center'}`}>
          <button
            onClick={() => onNewChat ? onNewChat() : window.location.reload()}
            className="flex-shrink-0 flex items-center justify-center transition-all duration-300 hover:shadow-lg"
            style={{
              backgroundColor: isDarkMode ? 'transparent' : '#C7A562',
              border: isDarkMode ? '2px solid #d1d1d1' : '2px solid #004A84',
              borderRadius: '50%',
              width: '32px',
              height: '32px',
            }}
            onMouseEnter={(e) => {
              if (!isDarkMode) e.currentTarget.style.backgroundColor = '#B59552';
              else e.currentTarget.style.backgroundColor = '#404147';
            }}
            onMouseLeave={(e) => {
              if (!isDarkMode) e.currentTarget.style.backgroundColor = '#C7A562';
              else e.currentTarget.style.backgroundColor = 'transparent';
            }}
            aria-label="New Chat"
          >
            <Plus size={18} strokeWidth={3} style={{ color: isDarkMode ? '#ffffff' : '#004A84' }} />
          </button>
          {isTaskBarExpanded && (
            <span 
              className="ml-3 text-sm font-medium whitespace-nowrap transition-opacity duration-300"
              style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}
            >
              New Chat
            </span>
          )}
          </div>

          {/* Chat History Button/Text */}
          {!isTaskBarExpanded ? (
          // Show button when collapsed
          <div className="flex items-center mt-4 px-2 justify-center">
            <button
              onClick={() => {
                setTaskBarExpanded(true);
              }}
              className="flex-shrink-0 flex items-center justify-center transition-all duration-300 hover:shadow-lg relative"
              style={{
                backgroundColor: isDarkMode ? 'transparent' : '#C7A562',
                border: isDarkMode ? '2px solid #d1d1d1' : '2px solid #004A84',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
              }}
              onMouseEnter={(e) => {
                if (!isDarkMode) e.currentTarget.style.backgroundColor = '#B59552';
                else e.currentTarget.style.backgroundColor = '#404147';
              }}
              onMouseLeave={(e) => {
                if (!isDarkMode) e.currentTarget.style.backgroundColor = '#C7A562';
                else e.currentTarget.style.backgroundColor = 'transparent';
              }}
              aria-label="Chat History"
            >
              {/* Minimal Clock Icon */}
              <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
                {/* Hour hand (12 o'clock) - straight up */}
                <line 
                  x1="16" y1="16" 
                  x2="16" y2="9" 
                  stroke={isDarkMode ? '#ffffff' : '#004A84'} 
                  strokeWidth="3" 
                  strokeLinecap="round"
                />
                {/* Minute hand (4 o'clock) - down-right */}
                <line 
                  x1="16" y1="16" 
                  x2="21" y2="24" 
                  stroke={isDarkMode ? '#ffffff' : '#004A84'} 
                  strokeWidth="3" 
                  strokeLinecap="round"
                />
                {/* Center dot */}
                <circle 
                  cx="16" cy="16" r="1.5" 
                  fill={isDarkMode ? '#ffffff' : '#004A84'} 
                />
              </svg>
            </button>
          </div>
        ) : null}
        </div>

        {/* Scrollable Middle Section - Chat History (when expanded) OR Spacer (when collapsed) */}
        {isTaskBarExpanded ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Search and Header Section */}
            <div className={`shrink-0 ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'}`}>
              {/* Divider line */}
              <div className={`mx-3 mb-4 ${isDarkMode ? 'bg-gray-700' : 'bg-gray-300'}`} style={{ height: '1px' }}></div>
              
              {/* Search Bar - Always visible when expanded */}
              <div className="px-4 mb-4">
                <div className="relative">
                  <Search size={16} className={`absolute left-3 top-2.5 ${
                    isDarkMode ? 'text-gray-400' : 'text-gray-500'
                  }`} />
                  <input
                    type="text"
                    placeholder="Search chats..."
                    value={chatSearchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    className={`w-full pl-9 pr-3 py-2 text-sm rounded-lg focus:outline-none ${
                      isDarkMode 
                        ? 'bg-[#25262b] text-gray-100 placeholder-gray-400' 
                        : 'bg-gray-100 text-gray-900 placeholder-gray-500 focus:ring-2 focus:ring-blue-500'
                    }`}
                  />
                </div>
              </div>

              {/* Chats Header */}
              <div className="px-4 mb-3">
                <span 
                  className="text-sm font-medium"
                  style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}
                >
                  Chats
                </span>
              </div>
            </div>

            {/* Scrollable Content Area */}
            <div className="flex-1 overflow-y-auto px-4 pb-4 hide-scrollbar">
              {!session ? (
                // Message for non-signed-in users
                <div className="text-center py-8">
                  <p className="text-sm font-medium" style={{ color: isDarkMode ? '#9CA3AF' : '#E1C88E' }}>Sign in to save chats</p>
                </div>
              ) : (
                // Show chat history
                <>
                  {isSearching ? (
                    // Loading state with spinner
                    <div className={`text-center py-8 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      <div className="inline-flex items-center gap-2">
                        <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin"></div>
                        <p className="text-sm">Searching...</p>
                      </div>
                    </div>
                  ) : chatHistory.length === 0 ? (
                    // No chats found
                    <div className={`text-center py-4 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                      <p className="text-sm">
                        {chatSearchQuery ? 'No chats found' : 'No chat history yet'}
                      </p>
                    </div>
                  ) : (() => {
                    // Group chats without filtering (already filtered by server)
                    const groupedChats = groupChatsByTimePeriod(chatHistory);

                return (
                  <div className="space-y-4">
                    {Object.entries(groupedChats).map(([period, chats]) => (
                      <div key={period}>
                        <div className={`text-xs font-semibold mb-2 uppercase tracking-wider ${
                          isDarkMode ? 'text-gray-500' : 'text-gray-400'
                        }`}>
                          {period}
                        </div>
                        <div className="space-y-1">
                          {chats
                            .map((chat) => (
                              <div
                                key={chat.id}
                                className="chat-item-container relative"
                              >
                                <button
                                  onClick={() => {
                                    if (onChatSelect) {
                                      onChatSelect(chat.id);
                                    } else {
                                      window.location.href = `/?chat=${chat.id}`;
                                    }
                                  }}
                                  onContextMenu={(e) => {
                                    e.preventDefault();
                                    setShowTrashIcon(chat.id);
                                  }}
                                  className={`w-full text-left p-2 rounded-lg transition-colors ${
                                    isDarkMode 
                                      ? 'hover:bg-[#25262b] text-gray-300' 
                                      : 'hover:bg-gray-100 text-gray-700'
                                  }`}
                                >
                                  <div className={`text-sm font-medium truncate pr-8`}>
                                    {chat.messages && chat.messages.length > 0 
                                      ? generateChatTitle(chat.messages) 
                                      : (chat.title || 'New Chat')}
                                  </div>
                                  {chat.preview && (
                                    <div className={`text-xs mt-0.5 truncate pr-8 ${
                                      isDarkMode ? 'text-gray-500' : 'text-gray-400'
                                    }`}>
                                      {chat.preview}
                                    </div>
                                  )}
                                </button>
                                
                                {/* Trash icon that appears on right-click */}
                                {showTrashIcon === chat.id && (
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      setShowTrashIcon(null);
                                      setDeleteConfirmation({ 
                                        chatId: chat.id, 
                                        title: chat.messages && chat.messages.length > 0 
                                          ? generateChatTitle(chat.messages) 
                                          : (chat.title || 'New Chat')
                                      });
                                    }}
                                    className={`absolute top-2 right-2 p-1 rounded transition-all ${
                                      isDarkMode 
                                        ? 'bg-red-900/20 hover:bg-red-900/40 text-red-400' 
                                        : 'bg-red-100 hover:bg-red-200 text-red-600'
                                    }`}
                                    aria-label="Delete chat"
                                  >
                                    <Trash2 size={16} />
                                  </button>
                                )}
                              </div>
                            ))}
                        </div>
                      </div>
                    ))}
                  </div>
                );
              })()}
                </>
              )}
            </div>
          </div>
        ) : (
          /* Spacer div when collapsed to push user button to bottom */
          <div className="flex-1"></div>
        )}

        {/* Fixed Bottom Section - User Button */}
        <div className={`shrink-0 ${isDarkMode ? 'bg-[#1a1b1e]' : 'bg-gray-50'} z-10`}>
          {/* Divider line */}
          <div className={`mx-3 mb-2 ${isDarkMode ? 'bg-gray-700' : 'bg-gray-300'}`} style={{ height: '1px' }}></div>
          
          <div className={`${isTaskBarExpanded ? 'px-4' : 'px-2'} pb-4`}>
            
            {/* User/Auth Button */}
            <div className={`flex items-center ${isTaskBarExpanded ? 'justify-start' : 'justify-center'} relative`}>
              <div className="relative flex items-center" ref={userMenuRef}>
                <button
                  onClick={() => {
                    if (!isTaskBarExpanded && !session) {
                      // If collapsed and not signed in, go directly to sign-in page
                      signIn();
                    } else {
                      // Otherwise show the menu
                      setShowUserMenu(!showUserMenu);
                    }
                  }}
                  className="flex-shrink-0 flex items-center justify-center transition-all duration-300 hover:shadow-lg"
                  style={{
                    backgroundColor: isDarkMode ? 'transparent' : '#C7A562',
                    border: isDarkMode ? '2px solid #ffffff' : '2px solid #004A84',
                    borderRadius: '50%',
                    width: '32px',
                    height: '32px',
                  }}
                  onMouseEnter={(e) => {
                    if (!isDarkMode) e.currentTarget.style.backgroundColor = '#B59552';
                    else e.currentTarget.style.backgroundColor = '#404147';
                  }}
                  onMouseLeave={(e) => {
                    if (!isDarkMode) e.currentTarget.style.backgroundColor = '#C7A562';
                    else e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                  aria-label={session ? 'User menu' : 'Sign in'}
                >
                  <span className="text-base font-bold" style={{ color: isDarkMode ? '#d1d1d1' : '#004A84', fontStyle: 'normal' }}>
                    {session ? getUserInitials() : '?'}
                  </span>
                </button>
                {isTaskBarExpanded && (
                  <button
                    onClick={() => {
                      if (session) {
                        setShowUserMenu(!showUserMenu);
                      } else {
                        signIn();
                      }
                    }}
                    className="ml-3 text-sm font-medium whitespace-nowrap transition-opacity duration-300 hover:underline cursor-pointer"
                    style={{ color: isDarkMode ? '#ffffff' : '#004A84' }}
                  >
                    {session ? (session.user?.name || session.user?.email || 'User') : 'Sign In'}
                  </button>
                )}

              {/* Dropdown Menu */}
              {showUserMenu && (
                <div 
                  className={`fixed rounded-2xl shadow-lg z-[9999] overflow-hidden ${
                    isDarkMode ? 'bg-[#25262b] border border-gray-700' : 'bg-white border border-gray-200'
                  }`}
                  style={{
                    bottom: '60px',
                    left: isTaskBarExpanded ? '16px' : '64px',
                    minWidth: '200px'
                  }}
                >
                  {session ? (
                    <>
                      <div className={`px-5 py-4 border-b ${isDarkMode ? 'border-gray-700' : 'border-gray-200'}`}>
                        <div className={`text-sm font-medium ${isDarkMode ? 'text-gray-200' : 'text-gray-900'}`}>
                          {session.user?.name || 'User'}
                        </div>
                        <div className={`text-xs mt-1 ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`}>
                          {session.user?.email}
                        </div>
                      </div>
                      <div className="p-2 space-y-1">
                        <a
                          href="http://localhost:8080"
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => setShowUserMenu(false)}
                          className={`w-full flex items-center px-4 py-2 text-sm transition-colors rounded-xl ${
                            isDarkMode 
                              ? 'hover:bg-gray-700 text-gray-300 hover:text-white' 
                              : 'hover:bg-gray-50 text-gray-700 hover:text-gray-900'
                          }`}
                        >
                          <Settings size={16} className="mr-2" />
                          Developer Dashboard
                        </a>
                        <button
                          onClick={() => {
                            setShowUserMenu(false);
                            signOut();
                          }}
                          className={`w-full flex items-center px-4 py-2 text-sm transition-colors rounded-xl ${
                            isDarkMode 
                              ? 'hover:bg-gray-700 text-gray-300 hover:text-white' 
                              : 'hover:bg-gray-50 text-gray-700 hover:text-gray-900'
                          }`}
                        >
                          <LogOut size={16} className="mr-2" />
                          Sign Out
                        </button>
                      </div>
                    </>
                  ) : (
                    <button
                      onClick={() => {
                        setShowUserMenu(false);
                        signIn();
                      }}
                      className={`w-full flex items-center px-4 py-3 text-sm transition-colors ${
                        isDarkMode 
                          ? 'hover:bg-gray-700 text-gray-300 hover:text-white' 
                          : 'hover:bg-gray-50 text-gray-700 hover:text-gray-900'
                      }`}
                    >
                      <User size={16} className="mr-2" />
                      Sign In
                    </button>
                  )}
                </div>
              )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      {deleteConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
          <div className={`mx-4 p-6 rounded-lg shadow-xl max-w-sm w-full ${
            isDarkMode ? 'bg-[#25262b] text-gray-100' : 'bg-white text-gray-900'
          }`}>
            <h3 className="text-lg font-semibold mb-3">Delete Chat?</h3>
            <p className={`mb-5 ${isDarkMode ? 'text-gray-300' : 'text-gray-600'}`}>
              Are you sure you want to delete "{deleteConfirmation.title}"? This action cannot be undone.
            </p>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setDeleteConfirmation(null)}
                className={`px-4 py-2 rounded-lg transition-colors ${
                  isDarkMode 
                    ? 'bg-gray-700 hover:bg-gray-600 text-gray-200' 
                    : 'bg-gray-200 hover:bg-gray-300 text-gray-700'
                }`}
              >
                Cancel
              </button>
              <button
                onClick={() => handleDeleteChat(deleteConfirmation.chatId)}
                className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

    </>
  );
}

export default function TaskBar(props: TaskBarProps) {
  return (
    <ErrorBoundary 
      level="section"
      isolate
      fallback={
        <div className="h-full w-14 bg-gray-100 dark:bg-gray-900 flex items-center justify-center">
          <p className="text-xs text-gray-500 -rotate-90 whitespace-nowrap">Navigation Error</p>
        </div>
      }
    >
      <TaskBarContent {...props} />
    </ErrorBoundary>
  );
}