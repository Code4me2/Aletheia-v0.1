'use client';

import { useState, useCallback, useEffect } from 'react';
import { courtAPI } from '@/lib/court-api';
import { CourtDocument, DocumentSelection } from '@/types/court-documents';

interface UseDocumentSelectionReturn {
  documents: CourtDocument[];
  selectedDocs: Map<number, DocumentSelection>;
  loading: boolean;
  error: string | null;
  searchDocuments: (params: any) => Promise<void>;
  toggleDocument: (doc: CourtDocument) => void;
  clearSelections: () => void;
  getSelectedIds: () => number[];
  totalTextLength: number;
}

export function useDocumentSelection(maxSelections = 15): UseDocumentSelectionReturn {
  const [documents, setDocuments] = useState<CourtDocument[]>([]);
  const [selectedDocs, setSelectedDocs] = useState<Map<number, DocumentSelection>>(new Map());
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const searchDocuments = useCallback(async (params: any) => {
    setLoading(true);
    setError(null);
    try {
      const result = await courtAPI.searchDocuments(params);
      setDocuments(result.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const toggleDocument = useCallback((doc: CourtDocument) => {
    setSelectedDocs(prev => {
      const next = new Map(prev);
      
      if (next.has(doc.id)) {
        next.delete(doc.id);
      } else if (next.size < maxSelections) {
        next.set(doc.id, {
          documentId: doc.id,
          documentTitle: doc.case || `Document ${doc.id}`,
          judge: doc.judge,
          court: doc.court || 'Unknown',  // Provide default value since court is optional
          textLength: doc.text_length,
          selectedAt: new Date()
        });
      } else {
        setError(`Maximum ${maxSelections} documents can be selected`);
      }
      
      return next;
    });
  }, [maxSelections]);

  const clearSelections = useCallback(() => {
    setSelectedDocs(new Map());
    setError(null);
  }, []);

  const getSelectedIds = useCallback(() => {
    return Array.from(selectedDocs.keys());
  }, [selectedDocs]);

  const totalTextLength = Array.from(selectedDocs.values())
    .reduce((sum, doc) => sum + doc.textLength, 0);

  return {
    documents,
    selectedDocs,
    loading,
    error,
    searchDocuments,
    toggleDocument,
    clearSelections,
    getSelectedIds,
    totalTextLength
  };
}