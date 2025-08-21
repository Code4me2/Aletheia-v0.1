/**
 * Citation extraction and mapping utilities for legal document citations
 */

import type { CourtDocument } from '@/types/court-documents';
import type { Citation } from '@/types';

/**
 * Extracts citation markers from AI response text
 * @param text AI response text containing [DOC1], [DOC2] style citations
 * @returns Array of unique citation markers found (e.g., ['DOC1', 'DOC2'])
 */
export function extractCitationMarkers(text: string): string[] {
  const pattern = /\[DOC(\d+)\]/g;
  const citations = new Set<string>();
  let match;
  
  while ((match = pattern.exec(text)) !== null) {
    citations.add(`DOC${match[1]}`);
  }
  
  return Array.from(citations).sort((a, b) => {
    const numA = parseInt(a.replace('DOC', ''));
    const numB = parseInt(b.replace('DOC', ''));
    return numA - numB;
  });
}

/**
 * Maps a citation marker to its corresponding document
 * @param citationMarker Citation marker like "DOC1"
 * @param documents Array of documents that were sent as context
 * @returns The corresponding document or null if not found
 */
export function mapCitationToDocument(
  citationMarker: string,
  documents: CourtDocument[]
): CourtDocument | null {
  const match = citationMarker.match(/DOC(\d+)/);
  if (!match) return null;
  
  const index = parseInt(match[1]) - 1; // Convert to 0-based index
  return documents[index] || null;
}

/**
 * Converts a CourtDocument to a Citation object for display
 * @param doc The court document to convert
 * @param citationKey The citation key used (e.g., "DOC1")
 * @returns Citation object for the citation panel
 */
export function documentToCitation(
  doc: CourtDocument,
  citationKey: string
): Citation {
  // Use enhanced title if available, otherwise construct from components
  const title = doc.formatted_title_short || 
                doc.formatted_title ||
                `${doc.case || `Document ${doc.id}`}`;
  
  return {
    id: `${doc.id}-${citationKey}`,
    title: title,
    source: `Judge ${doc.judge}`,
    court: formatCourtName(doc.court),
    date: doc.date_filed,
    caseNumber: doc.case,
    content: doc.text || doc.preview || 'No text available',
    excerpt: doc.preview
  };
}

/**
 * Formats court codes to readable names
 */
function formatCourtName(court?: string): string {
  if (!court) return 'Unknown Court';
  
  const courtMap: Record<string, string> = {
    'txed': 'E.D. Tex.',
    'txwd': 'W.D. Tex.',
    'txnd': 'N.D. Tex.',
    'txsd': 'S.D. Tex.',
    'cacd': 'C.D. Cal.',
    'cand': 'N.D. Cal.',
    'nysd': 'S.D.N.Y.',
    'nyed': 'E.D.N.Y.',
  };
  
  return courtMap[court.toLowerCase()] || court;
}

/**
 * Processes AI response text to extract all cited documents
 * @param responseText The AI's response text
 * @param contextDocuments Documents that were sent with the query
 * @returns Array of Citation objects for all cited documents
 */
export function extractCitationsFromResponse(
  responseText: string,
  contextDocuments: CourtDocument[]
): Citation[] {
  const markers = extractCitationMarkers(responseText);
  const citations: Citation[] = [];
  
  for (const marker of markers) {
    const doc = mapCitationToDocument(marker, contextDocuments);
    if (doc) {
      citations.push(documentToCitation(doc, marker));
    }
  }
  
  return citations;
}


/**
 * Checks if a message contains any citations
 * @param text The message text to check
 * @returns True if the text contains citation markers
 */
export function hasCitations(text: string): boolean {
  return /\[DOC\d+\]/g.test(text);
}