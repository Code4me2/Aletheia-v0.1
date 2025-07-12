# n8n-nodes-citationchecker

This is an n8n community node that provides citation parsing, verification, and validation capabilities for AI-generated legal text.

## Features

- **Parse Citations**: Extract inline citations (`<cite>` tags) and reference citations (`[1]`, `[2a]`)
- **Verify Citations**: Check citations against a database (PostgreSQL or mock)
- **Validate Citations**: Use AI to verify citation appropriateness and accuracy
- **Batch Processing**: Handle multiple documents efficiently
- **Flexible Operations**: Use individual operations or full validation pipeline

## Installation

In your n8n instance:

```bash
cd ~/.n8n/custom
npm install n8n-nodes-citationchecker
```

Or for development:

```bash
cd n8n/custom-nodes/n8n-nodes-citationchecker
npm install
npm run build
```

## Node Operations

### 1. Parse Citations

Extracts all citations from the input text:

- Inline citations: `<cite id="smith-2020">quoted text</cite>`
- Reference citations: `[1]`, `[2a]`, `[2b]`
- Citation metadata from `## Citations` section

### 2. Verify Citations

Checks if citations exist in your database:

- Supports PostgreSQL databases
- Includes fuzzy matching for variations
- Returns confidence scores

### 3. Full Validation

Complete pipeline that:

1. Parses all citations
2. Verifies existence in database
3. Uses AI to validate appropriateness

## Configuration

### Database Configuration

- **Database Type**: PostgreSQL or Mock (for testing)
- **Connection String**: PostgreSQL connection URL

### AI Model Connection

- Connect any n8n AI Language Model node
- Used for citation appropriateness validation
- Optional - node works without AI connection

## Input/Output

### Input

- Text field containing citations
- Optional AI Language Model connection

### Output

```json
{
  "originalText": "...",
  "citations": {
    "parsed": [
      {
        "id": "smith-2020",
        "type": "inline",
        "citedText": "quoted text",
        "metadata": { ... }
      }
    ],
    "verificationResults": [
      {
        "citationId": "smith-2020",
        "exists": true,
        "confidence": 0.95,
        "matchedRecord": { ... }
      }
    ],
    "validationResults": [
      {
        "citationId": "smith-2020",
        "appropriate": true,
        "confidence": 0.9,
        "reasoning": "Citation accurately represents the source",
        "issues": []
      }
    ],
    "summary": {
      "total": 5,
      "inline": 2,
      "references": 3,
      "verified": 4,
      "unverified": 1,
      "appropriate": 4,
      "inappropriate": 0,
      "issues": []
    }
  }
}
```

## Example Workflow

1. **AI Response Node** → generates text with citations
2. **Citation Checker** → validates all citations
3. **IF Node** → routes based on validation results
4. **Set Node** → formats output for display

## Database Schema

For PostgreSQL verification, use a table like:

```sql
CREATE TABLE citations (
  id SERIAL PRIMARY KEY,
  case_name VARCHAR(255),
  citation VARCHAR(255),
  court VARCHAR(100),
  year VARCHAR(4),
  holding TEXT,
  relevance TEXT
);
```

## Development

```bash
# Install dependencies
npm install

# Build for production
npm run build

# Development mode with watch
npm run dev

# Run tests
npm test
```

## License

MIT
