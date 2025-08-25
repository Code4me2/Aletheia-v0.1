'use client';

import { useEffect, useState } from 'react';
import { FileText, Database, FileSpreadsheet, ChevronDown } from 'lucide-react';
import { documentSourceRegistry } from '@/lib/document-sources/registry';
import { DocumentSource } from '@/lib/document-sources/types';
import { cn } from '@/lib/utils';

interface DocumentSourceSelectorProps {
  currentSourceId: string;
  onSourceChange: (sourceId: string) => void;
  className?: string;
}

/**
 * Optional component for switching between document sources.
 * 
 * This component is not required - the system will work with just 
 * the court document source by default. Add this to your UI only if
 * you have multiple document sources registered.
 */
export function DocumentSourceSelector({
  currentSourceId,
  onSourceChange,
  className
}: DocumentSourceSelectorProps) {
  const [sources, setSources] = useState<DocumentSource[]>([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Get available sources on mount
    documentSourceRegistry.getAvailableSources().then(setSources);
  }, []);

  // Don't render if only one source is available
  if (sources.length <= 1) {
    return null;
  }

  const currentSource = sources.find(s => s.sourceId === currentSourceId);
  
  const getSourceIcon = (sourceId: string) => {
    switch (sourceId) {
      case 'court':
        return <FileText className="w-4 h-4" />;
      case 'contracts':
        return <FileSpreadsheet className="w-4 h-4" />;
      default:
        return <Database className="w-4 h-4" />;
    }
  };

  return (
    <div className={cn("relative", className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 border rounded-md bg-white hover:bg-gray-50 transition-colors"
      >
        {getSourceIcon(currentSourceId)}
        <span className="text-sm font-medium">
          {currentSource?.sourceName || 'Select Source'}
        </span>
        <ChevronDown className={cn(
          "w-4 h-4 transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-64 bg-white border rounded-md shadow-lg z-20">
            {sources.map(source => (
              <button
                key={source.sourceId}
                onClick={() => {
                  onSourceChange(source.sourceId);
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full flex items-start gap-3 px-3 py-2 hover:bg-gray-50 transition-colors",
                  source.sourceId === currentSourceId && "bg-blue-50"
                )}
              >
                <div className="mt-0.5">
                  {getSourceIcon(source.sourceId)}
                </div>
                <div className="flex-1 text-left">
                  <div className="text-sm font-medium">
                    {source.sourceName}
                  </div>
                  {source.description && (
                    <div className="text-xs text-gray-500">
                      {source.description}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}