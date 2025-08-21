/**
 * Document formatting utilities for legal document context
 */

import type { CourtDocument } from '@/types/court-documents';

/**
 * Formats a single document with structured metadata for AI processing
 */
function formatSingleDocument(doc: CourtDocument, index: number, total: number): string {
  // Extract metadata with fallbacks
  const docId = doc.id;
  const citeKey = `[DOC${index}]`;
  
  // Use citation_components if available, otherwise fall back to direct fields
  const components = (doc as any).citation_components;
  const caseName = components?.case_name || doc.case || `Document ${doc.id}`;
  const caseNumber = doc.case || 'N/A';
  const judgeName = components?.judge || doc.judge || 'Unknown';
  const court = components?.court || doc.court || 'Unknown';
  const dateFiled = components?.date_filed || doc.date_filed || 'N/A';
  const docType = components?.document_type || 
                  (doc as any).document_type_extracted || 
                  doc.type || 
                  'Legal Document';
  
  // Format the court name if it's a code
  const courtFormatted = formatCourtName(court);
  
  // Build the formatted document section
  const sections = [
    `---Document ${index} of ${total}---`,
    `DOC_ID: ${docId}`,
    `CITE_KEY: ${citeKey}`,
    `CASE: ${caseName}`,
    `CASE_NO: ${caseNumber}`,
    `JUDGE: ${judgeName}`,
    `COURT: ${courtFormatted}`,
    `DATE: ${dateFiled}`,
    `TYPE: ${docType}`,
    '',
    'FULL_TEXT:',
    doc.text || doc.preview || 'No text available',
    `---End Document ${index}---`
  ];
  
  return sections.join('\n');
}

/**
 * Formats court codes to readable names
 */
function formatCourtName(court: string): string {
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
  
  return courtMap[court?.toLowerCase()] || court || 'Unknown';
}

/**
 * Formats multiple court documents for inclusion in AI context
 * @param documents Array of court documents to format
 * @returns Formatted string with all documents and citation instructions
 */
export function formatDocumentContext(documents: CourtDocument[]): string {
  if (!documents || documents.length === 0) {
    return '';
  }
  
  const sections: string[] = [
    '===LEGAL DOCUMENTS START===',
  ];
  
  // Format each document with its index
  documents.forEach((doc, index) => {
    sections.push(formatSingleDocument(doc, index + 1, documents.length));
    if (index < documents.length - 1) {
      sections.push(''); // Empty line between documents
    }
  });
  
  // Add footer with citation instructions
  sections.push(
    '===LEGAL DOCUMENTS END===',
    '',
    `CITATION FORMAT: Reference documents using [DOC1], [DOC2], etc. up to [DOC${documents.length}]`,
    `IMPORTANT: When citing, use the exact format [DOCN] where N is the document number.`
  );
  
  return sections.join('\n');
}

/**
 * Extracts citation references from AI response text
 * @param text AI response text that may contain [DOC1], [DOC2] style citations
 * @returns Array of document IDs that were cited
 */
export function extractCitedDocuments(text: string): number[] {
  const pattern = /\[DOC(\d+)\]/g;
  const matches = text.matchAll(pattern);
  const docNumbers = new Set<number>();
  
  for (const match of matches) {
    const docNum = parseInt(match[1], 10);
    if (!isNaN(docNum) && docNum > 0) {
      docNumbers.add(docNum);
    }
  }
  
  return Array.from(docNumbers).sort((a, b) => a - b);
}

/**
 * Maps citation keys back to document IDs
 * @param citationKey Citation key like "[DOC1]"
 * @param documents Original documents array
 * @returns Document ID or null if not found
 */
export function getCitedDocumentId(citationKey: string, documents: CourtDocument[]): number | null {
  const match = citationKey.match(/\[DOC(\d+)\]/);
  if (!match) return null;
  
  const index = parseInt(match[1], 10) - 1; // Convert to 0-based index
  if (index >= 0 && index < documents.length) {
    return documents[index].id;
  }
  
  return null;
}