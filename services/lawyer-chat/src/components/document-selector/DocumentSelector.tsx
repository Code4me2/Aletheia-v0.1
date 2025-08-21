'use client';

import { useState, useEffect } from 'react';
import { Search, FileText, X, Check, ChevronDown, Loader2 } from 'lucide-react';
import { useDocumentSelection } from '@/hooks/useDocumentSelection';
import { CourtDocument } from '@/types/court-documents';
import { cn } from '@/lib/utils';

interface DocumentSelectorProps {
  onSelectionComplete: (documentIds: number[]) => void;
  className?: string;
}

export function DocumentSelector({ 
  onSelectionComplete, 
  className 
}: DocumentSelectorProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedJudge, setSelectedJudge] = useState('Gilstrap');
  const [isExpanded, setIsExpanded] = useState(true);
  
  const {
    documents,
    selectedDocs,
    loading,
    error,
    searchDocuments,
    toggleDocument,
    clearSelections,
    getSelectedIds,
    totalTextLength
  } = useDocumentSelection();

  // Initial load - get Gilstrap documents (we know these exist)
  useEffect(() => {
    searchDocuments({ 
      judge: 'Gilstrap', 
      type: '020lead',
      limit: 50,
      min_length: 5000 
    });
  }, [searchDocuments]);

  // Search on query/judge change
  useEffect(() => {
    const params: any = { 
      limit: 50, 
      min_length: 5000,
      type: '020lead'  // Focus on lead opinions
    };
    
    if (selectedJudge) params.judge = selectedJudge;
    
    const timer = setTimeout(() => {
      searchDocuments(params);
    }, 300);

    return () => clearTimeout(timer);
  }, [selectedJudge, searchDocuments]);

  const handleComplete = () => {
    const ids = getSelectedIds();
    if (ids.length > 0) {
      onSelectionComplete(ids);
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    return `${(kb / 1024).toFixed(1)} MB`;
  };

  return (
    <div className={cn("bg-white border rounded-lg shadow-sm", className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-semibold">Select Court Documents</h3>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <ChevronDown className={cn(
              "w-5 h-5 transition-transform",
              !isExpanded && "-rotate-90"
            )} />
          </button>
        </div>

        {/* Judge Selector */}
        <div className="flex gap-2">
          <select
            value={selectedJudge}
            onChange={(e) => setSelectedJudge(e.target.value)}
            className="px-3 py-1 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="Gilstrap">Judge Gilstrap (37 docs)</option>
            <option value="Albright">Judge Albright</option>
            <option value="">All Judges</option>
          </select>
          
          {selectedDocs.size > 0 && (
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-sm text-gray-600">
                {selectedDocs.size} selected ({formatSize(totalTextLength)})
              </span>
              <button
                onClick={clearSelections}
                className="text-sm text-red-600 hover:text-red-700 flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                Clear
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Document List */}
      {isExpanded && (
        <div className="max-h-96 overflow-y-auto">
          {loading && (
            <div className="p-8 text-center">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-gray-500" />
              <p className="text-sm text-gray-500 mt-2">Loading documents...</p>
            </div>
          )}

          {error && (
            <div className="p-4 m-4 bg-red-50 text-red-700 rounded">
              {error}
            </div>
          )}

          {!loading && documents.length === 0 && (
            <div className="p-8 text-center text-gray-500">
              No documents found
            </div>
          )}

          {documents.map((doc) => (
            <div
              key={doc.id}
              onClick={() => toggleDocument(doc)}
              className={cn(
                "p-4 border-b cursor-pointer transition-colors hover:bg-gray-50",
                selectedDocs.has(doc.id) && "bg-blue-50 hover:bg-blue-100"
              )}
            >
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-gray-400 mt-1 flex-shrink-0" />
                
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-gray-900 truncate">
                    {doc.case || `Document ${doc.id}`}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    Judge {doc.judge} • {doc.court || 'Federal Court'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatSize(doc.text_length)} • Type: {doc.type}
                  </div>
                  {doc.preview && (
                    <div className="text-xs text-gray-500 mt-2 line-clamp-2">
                      {doc.preview}
                    </div>
                  )}
                </div>

                {selectedDocs.has(doc.id) && (
                  <div className="w-5 h-5 bg-blue-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <Check className="w-3 h-3 text-white" />
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      {selectedDocs.size > 0 && (
        <div className="p-4 border-t bg-gray-50">
          <button
            onClick={handleComplete}
            className="w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors font-medium"
          >
            Use {selectedDocs.size} Document{selectedDocs.size !== 1 ? 's' : ''} for Context
          </button>
        </div>
      )}
    </div>
  );
}