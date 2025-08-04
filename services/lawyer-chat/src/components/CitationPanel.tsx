'use client';

import { X, ArrowLeftRight } from 'lucide-react';
import { useSidebarStore } from '@/store/sidebar';
import DownloadButton from '@/components/DownloadButton';
import { PDFGenerator, generateCitationsText, downloadBlob, downloadText } from '@/utils/pdfGenerator';
import type { Citation } from '@/types';

interface CitationPanelProps {
  citation: Citation;
  onClose: () => void;
  onSwap?: () => void;
  isCitationOnRight?: boolean;
}

export default function CitationPanel({ citation, onClose, onSwap, isCitationOnRight = true }: CitationPanelProps) {
  const { isDarkMode } = useSidebarStore();

  const handleDownloadPDF = async () => {
    const pdfGenerator = new PDFGenerator();
    const blob = pdfGenerator.generateCitationsPDF([citation], {
      title: 'Legal Citation',
      includeTimestamp: true
    });
    
    const filename = `citation-${citation.title.replace(/\s+/g, '_').substring(0, 30)}.pdf`;
    downloadBlob(blob, filename);
  };

  const handleDownloadText = () => {
    const text = generateCitationsText([citation]);
    const filename = `citation-${citation.title.replace(/\s+/g, '_').substring(0, 30)}.txt`;
    downloadText(text, filename);
  };

  return (
    <div className={`h-full flex flex-col ${
      isDarkMode ? 'bg-[#25262b] border-l border-gray-700' : 'bg-white border-l border-gray-200'
    }`}>
      {/* Header */}
      <div className={`flex items-center justify-between p-4 border-b ${
        isDarkMode ? 'border-gray-700' : 'border-gray-200'
      }`}>
        <h3 className={`text-lg font-semibold ${
          isDarkMode ? 'text-white' : 'text-gray-900'
        }`}>
          Citation Document
        </h3>
        <div className="flex items-center space-x-2">
          {onSwap && (
            <button
              onClick={onSwap}
              className={`p-2 rounded-lg transition-colors ${
                isDarkMode 
                  ? 'hover:bg-gray-700 text-gray-400 hover:text-white' 
                  : 'hover:bg-gray-100 text-gray-600 hover:text-gray-900'
              }`}
              title={isCitationOnRight ? 'Move citation to left' : 'Move citation to right'}
            >
              <ArrowLeftRight className="w-5 h-5" />
            </button>
          )}
          <DownloadButton 
            onDownloadPDF={handleDownloadPDF}
            onDownloadText={handleDownloadText}
            compact
          />
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
      </div>

      {/* Citation Content */}
      <div className="flex-1 overflow-y-auto hide-scrollbar p-6">
        <div className="space-y-4">
          {/* Citation Title */}
          <h2 className={`text-xl font-bold ${
            isDarkMode ? 'text-gray-100' : 'text-gray-900'
          }`}>
            {citation.title}
          </h2>

          {/* Citation Metadata */}
          <div className={`space-y-2 text-sm ${
            isDarkMode ? 'text-gray-400' : 'text-gray-600'
          }`}>
            {citation.court && (
              <div>
                <span className="font-medium">Court:</span> {citation.court}
              </div>
            )}
            {citation.date && (
              <div>
                <span className="font-medium">Date:</span> {citation.date}
              </div>
            )}
            {citation.caseNumber && (
              <div>
                <span className="font-medium">Case Number:</span> {citation.caseNumber}
              </div>
            )}
          </div>

          {/* Divider */}
          <div className={`border-t ${
            isDarkMode ? 'border-gray-700' : 'border-gray-300'
          }`} />

          {/* Citation Text */}
          <div className={`whitespace-pre-wrap leading-relaxed ${
            isDarkMode ? 'text-gray-300' : 'text-gray-700'
          }`}>
            {citation.content || ''}
          </div>
        </div>
      </div>
    </div>
  );
}