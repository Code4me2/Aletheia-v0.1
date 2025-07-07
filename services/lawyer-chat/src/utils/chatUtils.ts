import type { ChatMessage } from '@/types';

/**
 * Generate a smart title for a chat based on its messages
 * @param messages - Array of chat messages
 * @returns A descriptive title for the chat
 */
export function generateChatTitle(messages: ChatMessage[]): string {
  if (!messages || messages.length === 0) {
    return 'New Chat';
  }

  // Find the first user message and first assistant response
  const firstUserMessage = messages.find(m => m.role === 'user');
  const firstAssistantMessage = messages.find(m => m.role === 'assistant');

  // If we have both, generate a smart title based on content
  if (firstUserMessage && firstAssistantMessage) {
    const userContent = firstUserMessage.content.toLowerCase();
    const assistantContent = firstAssistantMessage.content;

    // Check for common topics and generate appropriate titles
    if (userContent.includes('federalism')) {
      return 'Explaining Federalism';
    } else if (userContent.includes('periodic') && userContent.includes('table')) {
      return 'Periodic Table Elements';
    } else if (userContent.includes('elements') && (userContent.includes('list') || userContent.includes('properties'))) {
      return 'Chemical Elements Discussion';
    } else if (userContent.includes('capabilities') || userContent.includes('can you')) {
      return 'AI Capabilities Overview';
    }

    // Try to extract a meaningful title from the assistant's response
    // This is similar to what the backend does
    let smartTitle = '';
    
    // Try to extract first sentence or meaningful phrase
    const firstSentence = assistantContent.match(/^[^.!?]+[.!?]/);
    if (firstSentence) {
      smartTitle = firstSentence[0].trim();
    } else {
      // If no sentence found, take first few words
      const words = assistantContent.split(' ').slice(0, 8);
      smartTitle = words.join(' ');
    }
    
    // Remove markdown formatting
    smartTitle = smartTitle.replace(/[*_#`\[\]()]/g, '');
    
    // Limit length and add ellipsis if needed
    if (smartTitle.length > 60) {
      smartTitle = smartTitle.substring(0, 57) + '...';
    }

    return smartTitle;
  }

  // Fallback to first user message if no assistant response yet
  if (firstUserMessage) {
    const content = firstUserMessage.content;
    if (content.length > 50) {
      return content.substring(0, 47) + '...';
    }
    return content;
  }

  return 'New Chat';
}

/**
 * Check if a chat is valid (has at least one user message and one assistant response)
 * @param messages - Array of chat messages
 * @returns True if the chat is valid, false otherwise
 */
export function isValidChat(messages: ChatMessage[]): boolean {
  if (!messages || messages.length === 0) {
    return false;
  }
  
  const hasUserMessage = messages.some(m => m.role === 'user');
  const hasAssistantMessage = messages.some(m => m.role === 'assistant');
  
  return hasUserMessage && hasAssistantMessage;
}