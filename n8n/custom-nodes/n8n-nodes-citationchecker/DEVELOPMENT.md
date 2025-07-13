# Citation Checker Node - Development Documentation

## Architecture Overview

The Citation Checker node provides comprehensive citation validation for legal documents through three layers:
1. **Parsing**: Extract citations from various formats
2. **Verification**: Check existence in database
3. **Validation**: AI-powered appropriateness checking with scripted fallback

## Key Design Decisions

### Dual Validation Approach
The node implements both scripted and AI validation to ensure reliability:
- **Scripted**: Fast, deterministic format checking
- **AI**: Semantic appropriateness validation with resilience features

### AI Connection Strategy
Following the Hierarchical Summarization pattern, the node:
1. Attempts custom node format (messages array)
2. Falls back to n8n default format (string prompt)
3. Uses scripted validation if AI fails

## Core Components

### 1. Citation Parser (`parseCitations`)
Extracts three citation types:
- **Inline**: `<cite id="case-name">quoted text</cite>`
- **References**: `[1]`, `[2a]`, `[2b]`
- **Full Citations**: From markdown `## Citations` section

**Regex Patterns**:
```typescript
const CITE_TAG_PATTERN = /<cite\s+id="([^"]+)">([^<]+)<\/cite>/g;
const REF_PATTERN = /\[(\d+[a-z]?(?:,\s*\d+[a-z]?)*)\]/g;
```

### 2. Database Verifier (`verifyCitations`)
Supports two modes:
- **Mock**: For testing (70% success rate with random data)
- **PostgreSQL**: Fuzzy matching on case names and citations

**Connection Pattern**:
```typescript
const client = new Client(dbConfig.connectionString);
await client.connect();
// ... queries ...
await client.end();
```

### 3. Format Validator (`validateCitationFormat`)
Scripted checks for:
- Citation ID format (alphanumeric + hyphens/underscores)
- Quoted text presence
- Reference number format
- Metadata completeness
- Valid connection types

### 4. AI Validator (`validateCitations`)
Enhanced with resilience features:
- **Retry Logic**: Exponential backoff with jitter
- **Timeout Protection**: 30-second default per request
- **Format Fallback**: Tries multiple AI invocation formats
- **Response Parser**: Handles 16+ AI provider formats

## Configuration Options

### Operation Modes
```typescript
'parse'              // Extract citations only
'verify'             // Database check only
'scriptedValidation' // Format validation only
'fullValidation'     // All validations combined
```

### Resilience Configuration
```typescript
{
  retryEnabled: true,      // Enable retry logic
  maxRetries: 3,          // Number of retries
  requestTimeout: 30000,   // Timeout in ms
  fallbackEnabled: true    // Use scripted validation on AI failure
}
```

## Error Handling Strategy

1. **Graceful Degradation**: Operations continue even if some fail
2. **Detailed Error Messages**: Each failure includes context
3. **Fallback Mechanisms**: AI failures trigger scripted validation
4. **Batch Processing**: Individual citation failures don't stop processing

## Testing Guidelines

### Unit Tests
Run existing tests:
```bash
npm test
```

Test coverage includes:
- Citation parsing for all formats
- Metadata extraction
- Multiple citation types in single text

### Integration Testing
1. **Mock Database**: Use `dbType: 'mock'` for quick testing
2. **AI Connection**: Test with various n8n AI nodes
3. **Error Scenarios**: Disconnect AI, use invalid database

### Test Data Examples
```javascript
// Inline citation
'<cite id="smith-2020">procedural requirements must be strictly followed</cite>'

// Reference with metadata
`[1] **Smith v. Jones, 123 F.3d 456 (2d Cir. 2020)**
- **Holding**: The court ruled on procedural requirements
- **Relevance**: Directly applicable
- **Connection**: Primary`
```

## Performance Considerations

1. **Batch Processing**: All citations processed in single pass
2. **Database Connections**: One connection per execution
3. **AI Rate Limiting**: Built-in retry delays prevent overload
4. **Memory Usage**: Minimal - processes one document at a time

## Future Enhancement Ideas

1. **Caching Layer**: Cache database verification results
2. **Parallel Processing**: Process multiple citations simultaneously
3. **Custom Validation Rules**: User-defined format requirements
4. **Webhook Integration**: Real-time citation checking service
5. **Citation Correction**: Suggest fixes for invalid citations

## Common Issues and Solutions

### Issue: AI Connection Fails
**Solution**: Check AI node connection, enable fallback validation

### Issue: Database Timeout
**Solution**: Increase connection timeout, check database accessibility

### Issue: Citation Not Found
**Solution**: Check citation format, verify database content

### Issue: JSON Parse Error
**Solution**: AI response not in expected format, check AI model configuration

## Code Style Guidelines

1. **TypeScript**: Strict mode enabled
2. **Error Handling**: Always use try-catch with specific error types
3. **Comments**: Document complex regex patterns and business logic
4. **Interfaces**: Define all data structures explicitly
5. **Methods**: Keep under 50 lines, extract helper functions

## Debugging Tips

1. **Enable Logging**: Add console.log statements in development
2. **Check Regex**: Use regex101.com to test citation patterns
3. **Inspect AI Response**: Log full response to understand format
4. **Database Queries**: Test SQL directly in PostgreSQL client
5. **Use Mock Mode**: Faster iteration during development