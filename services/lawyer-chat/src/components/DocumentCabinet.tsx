'use client';

import { useState, useEffect, useCallback } from 'react';
import { ChevronRight, ChevronDown, FileText, X, Loader2, AlertCircle, Gavel, FileAudio, Search } from 'lucide-react';
import { getDocumentSource, documentSourceRegistry } from '@/lib/document-sources/registry';
import { CourtDocument } from '@/types/court-documents';
import { cn } from '@/lib/utils';

interface DocumentCabinetProps {
  onDocumentsSelected: (documents: CourtDocument[]) => void;
  isDarkMode: boolean;
  className?: string;
}

interface JudgeData {
  name: string;
  documents: CourtDocument[];
  isExpanded: boolean;
  isLoading: boolean;
  error?: string;
}

export function DocumentCabinet({ onDocumentsSelected, isDarkMode, className }: DocumentCabinetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [judges, setJudges] = useState<JudgeData[]>([
    { name: 'Gilstrap', documents: [], isExpanded: false, isLoading: false },
    { name: 'Albright', documents: [], isExpanded: false, isLoading: false }
  ]);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<number>>(new Set());
  const [hoveredDocId, setHoveredDocId] = useState<number | null>(null);
  const [loadingDocuments, setLoadingDocuments] = useState<Set<number>>(new Set());

  // Load documents for a judge when their dropdown is expanded
  const loadJudgeDocuments = useCallback(async (judgeName: string) => {
    setJudges(prev => prev.map(j => 
      j.name === judgeName ? { ...j, isLoading: true } : j
    ));

    try {
      const source = getDocumentSource('court');
      const response = await source.searchDocuments({
        category: judgeName,
        type: '020lead',
        limit: 50,
        min_length: 5000
      });

      setJudges(prev => prev.map(j => 
        j.name === judgeName 
          ? { ...j, documents: response.documents, isLoading: false }
          : j
      ));
    } catch (error: any) {
      console.error(`Failed to load documents for ${judgeName}:`, error);
      // Show user-friendly error message
      const errorMessage = error?.message?.includes('Court API not configured')
        ? 'Document selection is not available. Please contact your administrator.'
        : `Failed to load documents for ${judgeName}`;
      
      setJudges(prev => prev.map(j => 
        j.name === judgeName ? { 
          ...j, 
          isLoading: false,
          documents: [],
          error: errorMessage
        } : j
      ));
    }
  }, []);

  // Toggle judge dropdown
  const toggleJudge = useCallback((judgeName: string) => {
    setJudges(prev => prev.map(j => {
      if (j.name === judgeName) {
        const newExpanded = !j.isExpanded;
        // Load documents if expanding and not loaded yet
        if (newExpanded && j.documents.length === 0 && !j.isLoading) {
          loadJudgeDocuments(judgeName);
        }
        return { ...j, isExpanded: newExpanded };
      }
      return j;
    }));
  }, [loadJudgeDocuments]);

  // Toggle document selection
  const toggleDocument = useCallback(async (doc: CourtDocument) => {
    const newSelected = new Set(selectedDocIds);
    
    if (newSelected.has(doc.id)) {
      newSelected.delete(doc.id);
      setSelectedDocIds(newSelected);
    } else {
      // Add to loading state
      setLoadingDocuments(prev => new Set(prev).add(doc.id));
      
      try {
        // Fetch the full document text
        const source = getDocumentSource('court');
        const fullText = await source.getDocumentText(doc.id);
        const fullDoc = { ...doc, text: fullText };
        
        newSelected.add(doc.id);
        setSelectedDocIds(newSelected);
        
        // Update parent with selected documents - use allSettled to handle partial failures
        const results = await Promise.allSettled(
          Array.from(newSelected).map(async (id) => {
            // Find the document in our judges data
            for (const judge of judges) {
              const foundDoc = judge.documents.find(d => d.id === id);
              if (foundDoc) {
                if (id === doc.id) {
                  return fullDoc; // Use the one we just fetched
                }
                // Fetch text for other selected docs if needed
                if (!foundDoc.text) {
                  const source = getDocumentSource('court');
                  const text = await source.getDocumentText(id);
                  return { ...foundDoc, text };
                }
                return foundDoc;
              }
            }
            throw new Error(`Document ${id} not found`);
          })
        );
        
        // Extract successful results
        const selectedDocs = results
          .filter((result): result is PromiseFulfilledResult<CourtDocument> => 
            result.status === 'fulfilled' && result.value !== null
          )
          .map(result => result.value);
        
        // Log any failures for debugging
        const failedDocs = results.filter(r => r.status === 'rejected');
        if (failedDocs.length > 0) {
          console.warn(`Failed to load ${failedDocs.length} document(s):`, failedDocs);
        }
        
        onDocumentsSelected(selectedDocs);
      } catch (error) {
        console.error('Failed to fetch document text:', error);
      } finally {
        setLoadingDocuments(prev => {
          const next = new Set(prev);
          next.delete(doc.id);
          return next;
        });
      }
    }
  }, [selectedDocIds, judges, onDocumentsSelected]);

  // Format case name for display - use enhanced titles if available
  const formatCaseName = (doc: CourtDocument) => {
    // Use the enhanced short title if available
    if ((doc as any).formatted_title_short) {
      return (doc as any).formatted_title_short;
    }
    
    // Fallback to old logic for backwards compatibility
    if (doc.case) {
      // Extract case name from full case string (e.g., "CIVIL ACTION NO. 2:17-CV-00141-JRG" -> show case number)
      const match = doc.case.match(/NO\.\s*([\w:-]+)/i);
      if (match) {
        return `Case ${match[1]}`;
      }
      return doc.case;
    }
    return `Document ${doc.id}`;
  };

  return (
    <>
      {/* Semi-transparent button - top right corner */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "fixed right-4 top-20 z-10",
          "px-4 py-2 rounded-lg",
          "bg-black/20 hover:bg-black/30 backdrop-blur-sm",
          "text-white font-medium text-sm",
          "transition-all duration-300",
          "flex items-center gap-2",
          isOpen && "opacity-0 pointer-events-none",
          className
        )}
      >
        <FileText className="w-4 h-4" />
        <span>Document Context</span>
      </button>

      {/* Sliding cabinet */}
      <div
        className={cn(
          "fixed right-0 top-0 h-full z-50",
          "w-96 max-w-[90vw]",
          "transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full",
          isDarkMode ? "bg-[#25262b] text-white" : "bg-white text-gray-900",
          "shadow-2xl border-l",
          isDarkMode ? "border-gray-700" : "border-gray-200"
        )}
      >
        {/* Header */}
        <div className={cn(
          "flex items-center justify-between p-4 border-b",
          isDarkMode ? "border-gray-700" : "border-gray-200"
        )}>
          <h2 className="text-lg font-semibold">Document Context</h2>
          <button
            onClick={() => setIsOpen(false)}
            className={cn(
              "p-1 rounded transition-colors",
              isDarkMode ? "hover:bg-gray-700" : "hover:bg-gray-200"
            )}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className={cn(
          "p-4 border-b",
          isDarkMode ? "border-gray-700" : "border-gray-200"
        )}>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className={cn(
                "w-full pl-10 pr-4 py-2 rounded-lg text-sm",
                "transition-colors",
                isDarkMode 
                  ? "bg-gray-800 text-white placeholder-gray-400 border-gray-600 focus:border-blue-500"
                  : "bg-gray-100 text-gray-900 placeholder-gray-500 border-gray-300 focus:border-blue-500",
                "border focus:outline-none focus:ring-1 focus:ring-blue-500"
              )}
            />
          </div>
        </div>

        {/* Selected count */}
        {selectedDocIds.size > 0 && (
          <div className={cn(
            "px-4 py-2 text-sm",
            isDarkMode ? "bg-blue-900/20 text-blue-300" : "bg-blue-50 text-blue-700"
          )}>
            {selectedDocIds.size} document{selectedDocIds.size !== 1 ? 's' : ''} selected
          </div>
        )}

        {/* Document Categories - Vertical Dropdowns */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {/* Opinions Section */}
          <div className={cn(
            "rounded-lg border",
            isDarkMode ? "border-gray-700" : "border-gray-200"
          )}>
            <button
              onClick={() => {
                const newExpanded = new Set(expandedSections);
                if (newExpanded.has('opinions')) {
                  newExpanded.delete('opinions');
                } else {
                  newExpanded.add('opinions');
                }
                setExpandedSections(newExpanded);
              }}
              className={cn(
                "w-full px-4 py-3 flex items-center justify-between",
                "transition-colors",
                isDarkMode 
                  ? "bg-gray-800 hover:bg-gray-700" 
                  : "bg-gray-50 hover:bg-gray-100"
              )}
            >
              <div className="flex items-center gap-2">
                <Gavel className="w-4 h-4" />
                <span className="font-medium">Opinions</span>
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 transition-transform",
                  expandedSections.has('opinions') ? "rotate-180" : ""
                )}
              />
            </button>
            
            {expandedSections.has('opinions') && (
              <div className={cn(
                "border-t",
                isDarkMode ? "border-gray-700" : "border-gray-200"
              )}>
                {judges.map((judge) => (
            <div key={judge.name} className="border rounded-lg overflow-hidden">
              {/* Judge header */}
              <button
                onClick={() => toggleJudge(judge.name)}
                className={cn(
                  "w-full px-4 py-3 flex items-center justify-between",
                  "hover:bg-gray-100 dark:hover:bg-gray-800",
                  "transition-colors",
                  isDarkMode ? "bg-gray-900/50" : "bg-gray-50"
                )}
              >
                <span className="font-medium">Judge {judge.name}</span>
                <div className="flex items-center gap-2">
                  {judge.isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
                  <ChevronDown
                    className={cn(
                      "w-4 h-4 transition-transform",
                      judge.isExpanded ? "rotate-180" : ""
                    )}
                  />
                </div>
              </button>

              {/* Documents list */}
              {judge.isExpanded && (
                <div className={cn(
                  "border-t",
                  isDarkMode ? "border-gray-700" : "border-gray-200"
                )}>
                  {judge.isLoading ? (
                    <div className="p-4 text-center">
                      <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                      <p className="text-sm mt-2 opacity-60">Loading opinions...</p>
                    </div>
                  ) : judge.error ? (
                    <div className="p-4 text-center">
                      <div className="text-red-500 mb-2">
                        <AlertCircle className="w-5 h-5 mx-auto" />
                      </div>
                      <p className="text-sm text-red-500">{judge.error}</p>
                    </div>
                  ) : judge.documents.length === 0 ? (
                    <div className="p-4 text-center text-sm opacity-60">
                      No opinions available
                    </div>
                  ) : (
                    <div className="max-h-96 overflow-y-auto">
                      {judge.documents.map((doc) => (
                        <div
                          key={doc.id}
                          onClick={() => !loadingDocuments.has(doc.id) && toggleDocument(doc)}
                          onMouseEnter={() => setHoveredDocId(doc.id)}
                          onMouseLeave={() => setHoveredDocId(null)}
                          className={cn(
                            "px-4 py-3 cursor-pointer transition-all",
                            "border-b last:border-b-0",
                            isDarkMode ? "border-gray-700" : "border-gray-100",
                            // Selected state
                            selectedDocIds.has(doc.id) && (
                              isDarkMode ? "bg-blue-900/30" : "bg-blue-100"
                            ),
                            // Hover state
                            hoveredDocId === doc.id && !selectedDocIds.has(doc.id) && (
                              isDarkMode ? "bg-gray-800/50" : "bg-gray-50"
                            ),
                            // Loading state
                            loadingDocuments.has(doc.id) && "opacity-50 cursor-wait"
                          )}
                        >
                          <div className="flex items-start gap-2">
                            <FileText className={cn(
                              "w-4 h-4 mt-0.5 flex-shrink-0",
                              selectedDocIds.has(doc.id) 
                                ? "text-blue-500" 
                                : "opacity-40"
                            )} />
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-sm">
                                {formatCaseName(doc)}
                              </div>
                              {/* Show document type if extracted */}
                              {(doc as any).document_type_extracted && (
                                <div className="text-xs text-blue-500 mt-0.5">
                                  {(doc as any).document_type_extracted}
                                </div>
                              )}
                              {doc.preview && (
                                <div className="text-xs opacity-60 mt-1 line-clamp-2">
                                  {doc.preview}
                                </div>
                              )}
                              <div className="text-xs opacity-40 mt-1">
                                {(doc.text_length / 1024).toFixed(1)} KB • ID: {doc.id}
                              </div>
                            </div>
                            {loadingDocuments.has(doc.id) && (
                              <Loader2 className="w-4 h-4 animate-spin flex-shrink-0" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
              </div>
            )}
          </div>
          
          {/* Transcripts Section */}
          <div className={cn(
            "rounded-lg border",
            isDarkMode ? "border-gray-700" : "border-gray-200"
          )}>
            <button
              onClick={() => {
                const newExpanded = new Set(expandedSections);
                if (newExpanded.has('transcripts')) {
                  newExpanded.delete('transcripts');
                } else {
                  newExpanded.add('transcripts');
                }
                setExpandedSections(newExpanded);
              }}
              className={cn(
                "w-full px-4 py-3 flex items-center justify-between",
                "transition-colors",
                isDarkMode 
                  ? "bg-gray-800 hover:bg-gray-700" 
                  : "bg-gray-50 hover:bg-gray-100"
              )}
            >
              <div className="flex items-center gap-2">
                <FileAudio className="w-4 h-4" />
                <span className="font-medium">Transcripts</span>
              </div>
              <ChevronDown
                className={cn(
                  "w-4 h-4 transition-transform",
                  expandedSections.has('transcripts') ? "rotate-180" : ""
                )}
              />
            </button>
            
            {expandedSections.has('transcripts') && (
              <div className={cn(
                "p-4 text-center opacity-60",
                "border-t",
                isDarkMode ? "border-gray-700" : "border-gray-200"
              )}>
                <FileAudio className="w-8 h-8 mx-auto mb-2" />
                <p className="text-sm">No transcripts available</p>
                <p className="text-xs mt-1">Coming soon</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}

