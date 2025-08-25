# Document Sources Adapter Pattern

This module provides a flexible adapter pattern for integrating different document sources into the lawyer-chat interface without disrupting existing functionality.

## Overview

The adapter pattern allows lawyer-chat to work with various document types (court opinions, contracts, policies, etc.) through a common interface. The existing court document functionality remains unchanged and serves as the default source.

## Architecture

```
DocumentSource (interface)
    ├── CourtDocumentSource (existing court-processor API)
    ├── MockContractSource (example implementation)
    └── [Your Custom Source] (future additions)
```

## Quick Start

### Using the Default (Court) Source

No changes needed! The system works exactly as before:

```typescript
// Existing code continues to work
import { useDocumentSelection } from '@/hooks/useDocumentSelection';

const { searchDocuments, documents } = useDocumentSelection();
searchDocuments({ judge: 'Gilstrap', type: '020lead' });
```

### Adding a New Document Source

1. **Create your source adapter:**

```typescript
// src/lib/document-sources/my-source.ts
import { DocumentSource } from './types';

export class MyDocumentSource implements DocumentSource {
  readonly sourceId = 'my-source';
  readonly sourceName = 'My Documents';
  
  async searchDocuments(params) {
    // Your API call here
    // Map results to CourtDocument format
  }
  
  async getDocumentText(id) {
    // Fetch document text
  }
  
  // ... other required methods
}
```

2. **Register your source:**

```typescript
// In your app initialization
import { documentSourceRegistry } from '@/lib/document-sources';
import { MyDocumentSource } from './my-source';

documentSourceRegistry.register(new MyDocumentSource());
```

3. **Use it in components:**

```typescript
const { searchDocuments, switchSource } = useDocumentSelection();

// Switch to your source
switchSource('my-source');

// Now searches use your source
searchDocuments({ category: 'important' });
```

## API Reference

### DocumentSource Interface

All document sources must implement:

- `searchDocuments(params)` - Search with filters
- `getDocumentText(id)` - Get plain text content
- `getDocument(id)` - Get full document with metadata
- `listDocuments(limit)` - List available documents
- `isAvailable()` - Check if source is accessible

### Document Format

All sources must adapt their data to the `CourtDocument` type for consistency:

```typescript
interface CourtDocument {
  id: number;
  case?: string;        // Document title/name
  type: string;         // Document type
  judge: string;        // Author/department
  court?: string;       // Category/classification
  date_filed?: string;  // Date (YYYY-MM-DD)
  text_length: number;  // Character count
  preview?: string;     // Short preview text
  text?: string;        // Full text (when loaded)
}
```

## Examples

### Enable Mock Sources for Testing

```bash
# In .env.local
NEXT_PUBLIC_ENABLE_MOCK_SOURCES=true
```

```typescript
// In your app
import { initializeDemoSources } from '@/lib/document-sources/initialize';
initializeDemoSources();
```

### Add Source Selector to UI

```tsx
import { DocumentSourceSelector } from '@/components/document-selector/DocumentSourceSelector';

<DocumentSourceSelector
  currentSourceId={currentSourceId}
  onSourceChange={switchSource}
/>
```

## Design Principles

1. **No Breaking Changes**: Existing court document functionality unchanged
2. **Simple Integration**: New sources just implement the interface
3. **Consistent Format**: All sources map to CourtDocument type
4. **Optional Features**: Source switching UI only appears when multiple sources registered
5. **Clear Abstractions**: Each source handles its own API/data mapping

## Production Considerations

- Store API credentials securely (environment variables)
- Implement proper error handling in source adapters
- Consider caching strategies for frequently accessed documents
- Add monitoring/logging for source availability
- Test source switching thoroughly with your specific documents

## Troubleshooting

**Q: My new source isn't appearing**
- Ensure it's registered: `documentSourceRegistry.register(mySource)`
- Check `isAvailable()` returns true
- Verify source ID is unique

**Q: Documents aren't loading**
- Check browser console for errors
- Verify API endpoints are accessible
- Ensure data is mapped to CourtDocument format correctly

**Q: How do I remove a source?**
- Use `documentSourceRegistry.unregister('source-id')`
- Cannot remove the default (court) source