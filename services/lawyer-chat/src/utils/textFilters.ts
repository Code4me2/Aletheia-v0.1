/**
 * Text filtering utilities for cleaning AI responses
 */

import { preprocessAIResponse } from './markdownFormatter';

/**
 * Removes standalone "CITATIONS" text that might be accidentally included in AI responses
 * This is a temporary fix - the root cause should be addressed in the n8n workflow
 */
export function cleanAIResponse(text: string): string {
  // Remove standalone "CITATIONS" on its own line
  let cleaned = text.replace(/^CITATIONS\s*$/gm, '');
  
  // Remove "CITATIONS" at the end of the text
  cleaned = cleaned.replace(/\nCITATIONS\s*$/, '');
  
  // Remove multiple consecutive "CITATIONS"
  cleaned = cleaned.replace(/(CITATIONS\s*\n*)+/g, '');
  
  // Clean up any resulting extra newlines
  cleaned = cleaned.replace(/\n{3,}/g, '\n\n');
  
  cleaned = cleaned.trim();
  
  // Apply markdown formatting to ensure consistent structure
  cleaned = preprocessAIResponse(cleaned);
  
  return cleaned;
}

/**
 * Detects if the response appears to be cut off or restarting
 * This can happen if the n8n workflow has issues
 */
export function detectTruncatedResponse(text: string): boolean {
  // Check for patterns that indicate a restart
  const restartPatterns = [
    /The Indus Valley Civilization[^]*The Indus Valley Civilization/,
    /Origins and Development[^]*Origins and Development/,
    /A Detailed History[^]*A Detailed History/
  ];
  
  return restartPatterns.some(pattern => pattern.test(text));
}