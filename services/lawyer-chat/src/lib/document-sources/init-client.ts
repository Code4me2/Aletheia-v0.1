/**
 * Client-side initialization for document sources
 * This runs in the browser to register available document sources
 */

import { documentSourceRegistry } from './registry';
import { transcriptSource } from './transcript-source';

// Flag to ensure initialization only happens once
let initialized = false;

/**
 * Initialize document sources for the lawyer-chat app
 * Call this once during app initialization
 */
export function initializeDocumentSources() {
  if (initialized) return;
  
  // Register transcript source (placeholder for now)
  documentSourceRegistry.register(transcriptSource);
  
  // Log available sources in development
  if (process.env.NODE_ENV === 'development') {
    console.info('Document sources initialized:', {
      court: 'Court opinions (default)',
      transcripts: 'Transcripts (placeholder)'
    });
  }
  
  initialized = true;
}