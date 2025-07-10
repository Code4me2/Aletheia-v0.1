# Hierarchical Summarization Logging Improvements

## Current Issues from Logs

1. **AI Connection Failures**: The AI model is returning "Bad request" errors
   - The node correctly tries both custom format and default n8n format
   - All retry attempts are failing
   - System falls back to extractive summaries

2. **Missing Hierarchy Details**: Need more detailed logging about document relationships

## Recommended Logging Enhancements

### 1. Enhanced Hierarchy Tracking
Add detailed parent-child relationship logging:

```typescript
// When creating new documents at next level
console.log(`[HS Hierarchy] Level ${nextLevel} Doc ${newDoc.id}: parent=${parentId}, children=[${childIds.join(',')}], type=${documentType}`);

// When updating relationships
console.log(`[HS Relationship] Doc ${parentId} → Children: [${childIds.join(',')}]`);
```

### 2. Document Flow Visualization
Add ASCII visualization of document flow:

```typescript
console.log(`[HS Flow] Level 0: [${level0Docs.map(d => d.id).join(', ')}]`);
console.log(`[HS Flow]     ↓ (chunking/batching)`);
console.log(`[HS Flow] Level 1: [${level1Docs.map(d => d.id).join(', ')}]`);
console.log(`[HS Flow]     ↓ (summarization)`);
console.log(`[HS Flow] Level 2: [${level2Docs.map(d => d.id).join(', ')}]`);
```

### 3. Batch Processing Details
Log batch composition:

```typescript
console.log(`[HS Batch] Batch ${batchId}: ${documents.length} docs, ${totalTokens} tokens`);
documents.forEach(doc => {
  console.log(`[HS Batch]   - Doc ${doc.id}: ${doc.metadata?.filename || 'unnamed'} (${doc.token_count} tokens)`);
});
```

### 4. Summary Quality Metrics
Add quality metrics logging:

```typescript
console.log(`[HS Quality] Summary reduction: ${originalTokens} → ${summaryTokens} tokens (${reductionPercent}%)`);
console.log(`[HS Quality] Compression ratio: ${compressionRatio}:1`);
```

### 5. Database State Logging
Log database operations for debugging:

```typescript
console.log(`[HS DB] Inserted ${documents.length} documents at level ${level}`);
console.log(`[HS DB] Batch ${batchId} status: ${status}, current_level: ${currentLevel}`);
```

### 6. Structured JSON Logging Option
Add option for structured JSON logs:

```typescript
if (config.jsonLogging) {
  console.log(JSON.stringify({
    timestamp: new Date().toISOString(),
    type: 'HS_PROGRESS',
    batchId: config.batchId,
    level: currentLevel,
    documentCount: documents.length,
    totalTokens: totalTokens,
    status: 'processing'
  }));
}
```

## Implementation Steps

1. Add a `verboseLogging` option to node configuration
2. Add structured logging helpers
3. Include document ID tracking throughout the hierarchy
4. Add summary of final hierarchy structure at completion
5. Log all database operations with affected document IDs

## Example Enhanced Log Output

```
[HS Start] Batch abc-123: Processing 3 source documents
[HS Flow] Level 0: [1, 2, 3] (source documents)
[HS Batch] Creating Level 1 batches...
[HS Batch]   Batch 1: Docs [1, 2] (800 tokens)
[HS Batch]   Chunk 1: Doc [3] split into 2 chunks (1200 tokens)
[HS Flow] Level 1: [4, 5, 6] (1 batch + 2 chunks)
[HS Hierarchy] Level 1 Doc 4: parent=null, children=[1,2], type=batch
[HS Hierarchy] Level 1 Doc 5: parent=null, children=[3], type=chunk
[HS Hierarchy] Level 1 Doc 6: parent=null, children=[3], type=chunk
[HS Summary] Processing Level 1 → Level 2...
[HS Quality] Doc 4: 800 → 150 tokens (81% reduction)
[HS Flow] Level 2: [7, 8] (summaries)
[HS Complete] Final hierarchy: 3 source → 3 batches/chunks → 2 summaries → 1 final
```

This enhanced logging will help debug visualization issues by providing clear document flow and relationships.