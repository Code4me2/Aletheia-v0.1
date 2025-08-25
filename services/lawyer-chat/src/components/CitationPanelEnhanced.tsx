'use client';

import { useState, useEffect } from 'react';
import { X, ArrowLeft, FileText, ExternalLink, Loader2 } from 'lucide-react';
import { useSidebarStore } from '@/store/sidebar';
import { getDocumentSource } from '@/lib/document-sources/registry';
import { extractCitationMarkers, mapCitationToDocument, documentToCitation } from '@/utils/citationExtractor';
import type { Citation } from '@/types';
import type { CourtDocument } from '@/types/court-documents';

interface CitationPanelEnhancedProps {
  responseText: string;
  documentContext: CourtDocument[];
  onClose: () => void;
}

type ViewMode = 'list' | 'fulltext';

export default function CitationPanelEnhanced({ 
  responseText, 
  documentContext, 
  onClose 
}: CitationPanelEnhancedProps) {
  const { isDarkMode } = useSidebarStore();
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [citations, setCitations] = useState<Citation[]>([]);
  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<CourtDocument | null>(null);
  const [loadingFullText, setLoadingFullText] = useState(false);
  const [fullText, setFullText] = useState<string>('');

  // Extract citations when component mounts or responseText changes
  useEffect(() => {
    const markers = extractCitationMarkers(responseText);
    const extractedCitations: Citation[] = [];
    
    for (const marker of markers) {
      const doc = mapCitationToDocument(marker, documentContext);
      if (doc) {
        extractedCitations.push(documentToCitation(doc, marker));
      }
    }
    
    setCitations(extractedCitations);
  }, [responseText, documentContext]);

  // Handle clicking on a citation to view full text
  const handleCitationClick = async (citation: Citation, doc: CourtDocument) => {
    setSelectedCitation(citation);
    setSelectedDocument(doc);
    setLoadingFullText(true);
    
    try {
      // Check if we already have the full text
      if (doc.text) {
        setFullText(doc.text);
      } else {
        // Fetch full text from court-processor API
        const source = getDocumentSource('court');
        const text = await source.getDocumentText(doc.id);
        setFullText(text);
      }
      setViewMode('fulltext');
    } catch (error) {
      console.error('Failed to load document text:', error);
      setFullText('Failed to load document text. Please try again.');
    } finally {
      setLoadingFullText(false);
    }
  };

  const handleBack = () => {
    setViewMode('list');
    setSelectedCitation(null);
    setSelectedDocument(null);
    setFullText('');
  };

  // Handle clicking outside the panel when in fulltext view
  const handleOutsideClick = (e: React.MouseEvent) => {
    if (viewMode === 'fulltext' && e.target === e.currentTarget) {
      handleBack();
    }
  };

  return (
    <div className={`h-full flex flex-col ${
      isDarkMode ? 'bg-[#25262b]' : 'bg-white'
    }`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${
        isDarkMode ? 'border-gray-700' : 'border-gray-200'
      }`}>
        <div className="flex items-center gap-3">
          {viewMode === 'fulltext' && (
            <button
              onClick={handleBack}
              className={`p-1.5 rounded-lg transition-colors ${
                isDarkMode 
                  ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
                  : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
              }`}
              title="Back to citations"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
          )}
          <h3 className={`text-lg font-semibold ${
            isDarkMode ? 'text-white' : 'text-gray-900'
          }`}>
            {viewMode === 'list' 
              ? `Citations (${citations.length})`
              : 'Document View'
            }
          </h3>
        </div>
        <button
          onClick={onClose}
          className={`p-2 rounded-lg transition-colors ${
            isDarkMode 
              ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
              : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
          }`}
          title="Close panel"
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto" onClick={handleOutsideClick}>
        {viewMode === 'list' ? (
          // Citation List View
          <div className="p-4 space-y-3">
            {citations.length === 0 ? (
              <div className={`text-center py-8 ${
                isDarkMode ? 'text-gray-400' : 'text-gray-500'
              }`}>
                <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>No citations found in this response</p>
              </div>
            ) : (
              citations.map((citation, index) => {
                // Find the corresponding document
                const citationKey = citation.id.split('-').pop(); // Get DOC1, DOC2, etc.
                const docIndex = parseInt(citationKey?.replace('DOC', '') || '0') - 1;
                const doc = documentContext[docIndex];
                
                return (
                  <div
                    key={citation.id}
                    onClick={() => doc && handleCitationClick(citation, doc)}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      isDarkMode 
                        ? 'border-gray-700 hover:bg-gray-800 hover:border-gray-600' 
                        : 'border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className={`text-xs font-medium px-2 py-0.5 rounded ${
                            isDarkMode 
                              ? 'bg-blue-900/50 text-blue-300' 
                              : 'bg-blue-100 text-blue-700'
                          }`}>
                            [{citationKey}]
                          </span>
                          <h4 className={`font-medium text-sm truncate ${
                            isDarkMode ? 'text-gray-100' : 'text-gray-900'
                          }`}>
                            {citation.title}
                          </h4>
                        </div>
                        
                        <div className={`text-xs space-y-1 ${
                          isDarkMode ? 'text-gray-400' : 'text-gray-600'
                        }`}>
                          {citation.court && (
                            <div>Court: {citation.court}</div>
                          )}
                          {citation.date && (
                            <div>Date: {citation.date}</div>
                          )}
                          {citation.source && (
                            <div>Judge: {citation.source.replace('Judge ', '')}</div>
                          )}
                        </div>
                        
                        {citation.excerpt && (
                          <p className={`text-xs mt-2 line-clamp-2 ${
                            isDarkMode ? 'text-gray-500' : 'text-gray-500'
                          }`}>
                            {citation.excerpt}
                          </p>
                        )}
                      </div>
                      
                      <ExternalLink className={`w-4 h-4 flex-shrink-0 ${
                        isDarkMode ? 'text-gray-500' : 'text-gray-400'
                      }`} />
                    </div>
                  </div>
                );
              })
            )}
          </div>
        ) : (
          // Full Text View
          <div className="relative h-full">
            {loadingFullText ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center">
                  <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" />
                  <p className={isDarkMode ? 'text-gray-400' : 'text-gray-600'}>
                    Loading document...
                  </p>
                </div>
              </div>
            ) : (
              <div className="p-6">
                {/* Document Header */}
                {selectedCitation && (
                  <div className="mb-6">
                    <h2 className={`text-xl font-bold mb-3 ${
                      isDarkMode ? 'text-gray-100' : 'text-gray-900'
                    }`}>
                      {selectedCitation.title}
                    </h2>
                    
                    <div className={`grid grid-cols-2 gap-4 text-sm ${
                      isDarkMode ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {selectedCitation.court && (
                        <div>
                          <span className="font-medium">Court:</span> {selectedCitation.court}
                        </div>
                      )}
                      {selectedCitation.date && (
                        <div>
                          <span className="font-medium">Date:</span> {selectedCitation.date}
                        </div>
                      )}
                      {selectedCitation.caseNumber && (
                        <div>
                          <span className="font-medium">Case:</span> {selectedCitation.caseNumber}
                        </div>
                      )}
                      {selectedDocument && (
                        <div>
                          <span className="font-medium">Document ID:</span> {selectedDocument.id}
                        </div>
                      )}
                    </div>
                    
                    <div className={`mt-4 border-t ${
                      isDarkMode ? 'border-gray-700' : 'border-gray-300'
                    }`} />
                  </div>
                )}
                
                {/* Document Text */}
                <div className={`whitespace-pre-wrap leading-relaxed text-sm ${
                  isDarkMode ? 'text-gray-300' : 'text-gray-700'
                }`}>
                  {fullText || 'No text available'}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}