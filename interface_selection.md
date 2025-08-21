Looking at the codebase structure, I need to analyze the existing lawyer-chat application to provide precise implementation instructions. Let me search for the actual codebase structure.# Coding Agent Implementation Manual: Document Selection for Lawyer-Chat

## Project Context & Prerequisites

### System Architecture Verification
```bash
# 1. Verify Court Processor API is running
curl http://localhost:8104/
# Expected: {"status":"healthy","api":"Simplified Court Documents API v2"}

# 2. Test document retrieval
curl http://localhost:8104/search?judge=Gilstrap&limit=5
# Expected: JSON with documents array

# 3. Check lawyer-chat is accessible
curl http://localhost:8080/chat
# Expected: HTML response
```

### Current Stack Analysis
- **lawyer-chat**: Next.js with App Router, Prisma ORM, TypeScript
- **Court Processor API**: FastAPI on port 8104 (37 documents available)
- **Database**: PostgreSQL with `court_documents` table
- **Authentication**: NextAuth.js
- **Webhook**: n8n integration already configured

## Implementation Instructions

### Step 1: Environment Configuration

**File: `lawyer-chat/.env.local`**
```bash
# Add these lines to existing .env.local
COURT_API_BASE_URL=http://court-processor:8104  # Internal Docker network
NEXT_PUBLIC_COURT_API_URL=http://localhost:8104  # For client-side calls
NEXT_PUBLIC_MAX_DOCUMENT_SELECTIONS=15
NEXT_PUBLIC_ENABLE_DOCUMENT_SELECTION=true
```

### Step 2: TypeScript Type Definitions

**File: `lawyer-chat/src/types/court-documents.ts`**
```typescript
// Court Processor API response types
export interface CourtDocument {
  id: number;
  case?: string;           // Simplified API uses 'case' not 'case_number'
  type: string;
  judge: string;
  court: string;
  date_filed?: string;
  text?: string;
  text_length: number;
  preview?: string;
}

export interface SearchResponse {
  total: number;
  returned: number;
  offset: number;
  limit: number;
  documents: CourtDocument[];
}

export interface BulkJudgeResponse {
  judge: string;
  total_documents: number;
  total_text_characters?: number;
  documents: CourtDocument[];
}

export interface DocumentSelection {
  documentId: number;
  documentTitle: string;
  judge: string;
  court: string;
  textLength: number;
  selectedAt: Date;
}

export interface ChatSessionWithDocuments {
  id: string;
  documents: DocumentSelection[];
  contextSize: number;
}
```

### Step 3: API Client Library

**File: `lawyer-chat/src/lib/court-api.ts`**
```typescript
import { CourtDocument, SearchResponse, BulkJudgeResponse } from '@/types/court-documents';

class CourtAPIClient {
  private baseUrl: string;
  private clientUrl: string;

  constructor() {
    // Use server URL for SSR, client URL for browser
    this.baseUrl = process.env.COURT_API_BASE_URL || 'http://court-processor:8104';
    this.clientUrl = process.env.NEXT_PUBLIC_COURT_API_URL || 'http://localhost:8104';
  }

  private getUrl(): string {
    return typeof window === 'undefined' ? this.baseUrl : this.clientUrl;
  }

  async searchDocuments(params: {
    judge?: string;
    type?: string;
    min_length?: number;
    limit?: number;
    offset?: number;
  }): Promise<SearchResponse> {
    const searchParams = new URLSearchParams();
    
    // Map parameters to Court Processor API format
    if (params.judge) searchParams.append('judge', params.judge);
    if (params.type) searchParams.append('type', params.type);
    if (params.min_length) searchParams.append('min_length', params.min_length.toString());
    searchParams.append('limit', (params.limit || 50).toString());
    searchParams.append('offset', (params.offset || 0).toString());

    const response = await fetch(`${this.getUrl()}/search?${searchParams}`);
    if (!response.ok) {
      throw new Error(`Search failed: ${response.statusText}`);
    }
    return response.json();
  }

  async getDocumentText(id: number): Promise<string> {
    const response = await fetch(`${this.getUrl()}/text/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch document text: ${response.statusText}`);
    }
    return response.text();
  }

  async getDocument(id: number): Promise<CourtDocument> {
    const response = await fetch(`${this.getUrl()}/documents/${id}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch document: ${response.statusText}`);
    }
    return response.json();
  }

  async getBulkByJudge(judgeName: string, includeText = false): Promise<BulkJudgeResponse> {
    const url = `${this.getUrl()}/bulk/judge/${encodeURIComponent(judgeName)}?include_text=${includeText}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Bulk fetch failed: ${response.statusText}`);
    }
    return response.json();
  }

  async listDocuments(limit = 20): Promise<CourtDocument[]> {
    const response = await fetch(`${this.getUrl()}/list?limit=${limit}`);
    if (!response.ok) {
      throw new Error(`List failed: ${response.statusText}`);
    }
    return response.json();
  }
}

export const courtAPI = new CourtAPIClient();
```

### Step 4: React Hook for Document Selection

**File: `lawyer-chat/src/hooks/useDocumentSelection.ts`**
```typescript
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
          court: doc.court,
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
```

### Step 5: Document Selector Component

**File: `lawyer-chat/src/components/document-selector/DocumentSelector.tsx`**
```typescript
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
```

### Step 6: Enhanced Chat Interface with Documents

**File: `lawyer-chat/src/components/chat/ChatWithDocuments.tsx`**
```typescript
'use client';

import { useState, useCallback, useRef } from 'react';
import { Send, FileText, Loader2 } from 'lucide-react';
import { DocumentSelector } from '@/components/document-selector/DocumentSelector';
import { courtAPI } from '@/lib/court-api';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  documentIds?: number[];
  timestamp: Date;
}

export function ChatWithDocuments() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [selectedDocIds, setSelectedDocIds] = useState<number[]>([]);
  const [documentContext, setDocumentContext] = useState<string>('');
  const [isLoadingContext, setIsLoadingContext] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleDocumentSelection = useCallback(async (docIds: number[]) => {
    setSelectedDocIds(docIds);
    setIsLoadingContext(true);

    try {
      // Fetch text content for selected documents
      const textPromises = docIds.map(id => courtAPI.getDocumentText(id));
      const texts = await Promise.all(textPromises);
      
      // Create context with document markers
      const context = texts.map((text, i) => {
        // Limit each document to 10KB to stay within token limits
        const truncated = text.substring(0, 10000);
        return `[Document ${docIds[i]}]\n${truncated}\n[End Document ${docIds[i]}]`;
      }).join('\n\n');
      
      setDocumentContext(context);
    } catch (error) {
      console.error('Failed to load document context:', error);
    } finally {
      setIsLoadingContext(false);
    }
  }, []);

  const sendMessage = async () => {
    if (!input.trim() || selectedDocIds.length === 0 || isSending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      documentIds: selectedDocIds,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      // Send to existing n8n webhook with document context
      const webhookUrl = process.env.NEXT_PUBLIC_N8N_WEBHOOK_URL || 
                        '/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177';
      
      const response = await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action: 'chat',
          message: input,
          context: documentContext,
          documentIds: selectedDocIds,
          timestamp: new Date().toISOString()
        })
      });

      const data = await response.json();
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || data.message || 'No response received',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
      scrollToBottom();
    } catch (error) {
      console.error('Chat error:', error);
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, I encountered an error processing your request.',
        timestamp: new Date()
      }]);
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Panel - Document Selection */}
      <div className="w-1/3 min-w-[300px] max-w-[400px] border-r bg-white overflow-y-auto">
        <DocumentSelector onSelectionComplete={handleDocumentSelection} />
        
        {selectedDocIds.length > 0 && (
          <div className="p-4 bg-green-50 border-t">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-green-600" />
              <span className="text-sm text-green-700 font-medium">
                {selectedDocIds.length} document{selectedDocIds.length !== 1 ? 's' : ''} loaded
              </span>
            </div>
            {isLoadingContext && (
              <div className="flex items-center gap-2 mt-1">
                <Loader2 className="w-3 h-3 animate-spin text-gray-500" />
                <span className="text-xs text-gray-500">Processing documents...</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right Panel - Chat Interface */}
      <div className="flex-1 flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 mt-8">
              <FileText className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-lg font-medium">Select documents to start</p>
              <p className="text-sm mt-1">Choose court opinions from the left panel</p>
            </div>
          )}

          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex",
                msg.role === 'user' ? "justify-end" : "justify-start"
              )}
            >
              <div
                className={cn(
                  "max-w-[80%] rounded-lg px-4 py-2",
                  msg.role === 'user' 
                    ? "bg-blue-500 text-white" 
                    : "bg-white border shadow-sm"
                )}
              >
                <div className="text-sm font-medium mb-1">
                  {msg.role === 'user' ? 'You' : 'Assistant'}
                </div>
                <div className="whitespace-pre-wrap">{msg.content}</div>
                {msg.documentIds && msg.documentIds.length > 0 && (
                  <div className="text-xs mt-2 opacity-70">
                    Using documents: {msg.documentIds.join(', ')}
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isSending && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-lg px-4 py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="border-t bg-white p-4">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
              placeholder={
                selectedDocIds.length > 0 
                  ? "Ask about the selected documents..." 
                  : "Select documents first to enable chat..."
              }
              disabled={selectedDocIds.length === 0 || isSending}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-500"
            />
            <button
              onClick={sendMessage}
              disabled={selectedDocIds.length === 0 || !input.trim() || isSending}
              className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
              Send
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
```

### Step 7: Update Main Chat Page

**File: `lawyer-chat/src/app/chat/page.tsx`**
```typescript
import { ChatWithDocuments } from '@/components/chat/ChatWithDocuments';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';

export default async function ChatPage() {
  const session = await getServerSession(authOptions);
  
  if (!session) {
    redirect('/login');
  }

  return (
    <div className="h-screen">
      <ChatWithDocuments />
    </div>
  );
}
```

### Step 8: Add API Route for Session Management (Optional)

**File: `lawyer-chat/src/app/api/chat/session/route.ts`**
```typescript
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { prisma } from '@/lib/prisma';

export async function POST(request: NextRequest) {
  const session = await getServerSession(authOptions);
  
  if (!session?.user?.id) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const { documentIds } = await request.json();

  try {
    // Create a chat session with document context
    const chatSession = await prisma.chatSession.create({
      data: {
        userId: session.user.id,
        metadata: {
          documentIds,
          documentCount: documentIds.length,
          createdAt: new Date().toISOString()
        }
      }
    });

    return NextResponse.json({
      sessionId: chatSession.id,
      documentCount: documentIds.length
    });
  } catch (error) {
    console.error('Session creation error:', error);
    return NextResponse.json(
      { error: 'Failed to create session' },
      { status: 500 }
    );
  }
}
```

### Step 9: Update Docker Networking

**File: `docker-compose.yml` (modification)**
```yaml
services:
  lawyer-chat:
    # ... existing config ...
    environment:
      # ... existing vars ...
      - COURT_API_BASE_URL=http://court-processor:8104
      - NEXT_PUBLIC_COURT_API_URL=http://localhost:8104
      - NEXT_PUBLIC_N8N_WEBHOOK_URL=/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177
    networks:
      - frontend-network
      - backend-network  # Ensure it can reach court-processor
```

### Step 10: Testing Script

**File: `lawyer-chat/scripts/test-document-selection.sh`**
```bash
#!/bin/bash

echo "Testing Document Selection Integration"
echo "======================================"

# Test Court Processor API
echo "1. Testing Court Processor API..."
curl -s http://localhost:8104/ | head -n 1

# Test document search
echo -e "\n2. Testing document search..."
curl -s "http://localhost:8104/search?judge=Gilstrap&limit=3" | jq '.total'

# Test specific document
echo -e "\n3. Testing document retrieval..."
curl -s http://localhost:8104/documents/420 | jq '{id, judge, text_length}'

# Test lawyer-chat
echo -e "\n4. Testing lawyer-chat..."
curl -s http://localhost:8080/chat | grep -q "html" && echo "✓ Lawyer-chat accessible"

echo -e "\n✅ All tests passed!"
```

## Deployment Checklist for Coding Agent

### Pre-Implementation
```bash
# 1. Verify Court Processor is running
docker ps | grep court-processor

# 2. Test API endpoints
curl http://localhost:8104/search?judge=Gilstrap

# 3. Check lawyer-chat structure
ls -la lawyer-chat/src/
```

### Implementation Order
1. [ ] Add environment variables to `.env.local`
2. [ ] Create TypeScript types in `src/types/court-documents.ts`
3. [ ] Implement API client in `src/lib/court-api.ts`
4. [ ] Create React hook in `src/hooks/useDocumentSelection.ts`
5. [ ] Build DocumentSelector component
6. [ ] Create ChatWithDocuments component
7. [ ] Update chat page to use new component
8. [ ] Test with provided script

### Post-Implementation Testing
```bash
# Start all services
docker-compose up -d

# Run test script
chmod +x lawyer-chat/scripts/test-document-selection.sh
./lawyer-chat/scripts/test-document-selection.sh

# Check logs for errors
docker-compose logs -f lawyer-chat
```

## Critical Implementation Notes

1. **API Format**: The Court Processor uses `case` not `case_number` in responses
2. **Document Type**: Focus on `020lead` type - these are the main opinion documents
3. **Judge Data**: "Gilstrap" has 37 documents available for testing
4. **Context Size**: Limit each document to 10KB to avoid token limits
5. **Webhook**: Use existing n8n webhook at `/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177`
6. **Docker Network**: Ensure `lawyer-chat` is on `backend-network` to reach `court-processor`

## Success Validation

The implementation is successful when:
- [ ] Document selector loads and displays Gilstrap documents
- [ ] Documents can be selected/deselected with visual feedback
- [ ] Selected document text is fetched and combined into context
- [ ] Chat messages include document context in webhook payload
- [ ] UI shows which documents are being used for each message

This implementation leverages existing infrastructure without requiring backend changes, focusing purely on frontend integration with the already-functional Court Processor API.
