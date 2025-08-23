# n8n-nodes-citation-gen

Custom n8n node for hierarchical document processing with citation generation.

## Description
Performs 3-level hierarchical document processing (source → first summary → final summary) to generate citations and summaries. Uses PostgreSQL to store document hierarchies and integrates with AI language models for summarization.

## Usage
Processes documents through multiple summarization levels to extract key citations and create structured summaries. Requires database connection and AI model integration.

## Development
```bash
npm install
npm run build
```