# n8n-nodes-deepseek

Custom n8n node for DeepSeek R1 AI model integration via Ollama.

## Description
Provides access to DeepSeek R1 language model for text generation in n8n workflows.

## Configuration
Requires Ollama running with DeepSeek model installed.

## Usage
Connect to any n8n node that provides text input. The node will send the text to DeepSeek and return the AI-generated response.

## Testing
```bash
npm test
```

## Development
```bash
npm install
npm run build
```