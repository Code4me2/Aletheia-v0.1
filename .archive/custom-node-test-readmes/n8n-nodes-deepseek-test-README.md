# DeepSeek Node Tests

This directory contains the test suite for the DeepSeek n8n custom node, using the shared test utilities.

## Test Structure

```
test/
├── run-tests.js          # Main test runner
├── unit/                 # Unit tests
│   ├── test-node-structure.js  # Node compilation and structure
│   └── test-config.js    # DeepSeek configuration validation
└── integration/          # Integration tests
    └── test-ollama-api.js # Ollama API connectivity
```

## Running Tests

### Run All Tests
```bash
npm test
# or
node test/run-tests.js
```

### Run Specific Test
```bash
# Unit tests
node test/unit/test-node-structure.js
node test/unit/test-config.js

# Integration test (requires Ollama)
node test/integration/test-ollama-api.js
```

## Test Descriptions

### Unit Tests

1. **Node Structure** (`test-node-structure.js`)
   - Validates `package.json` configuration
   - Checks required files exist
   - Loads and validates compiled node
   - Verifies n8n interface implementation
   - Checks DeepSeek-specific properties

2. **Configuration** (`test-config.js`)
   - Validates Ollama API configuration
   - Checks default endpoint (localhost:11434)
   - Verifies model selection options
   - Tests for DeepSeek-specific features
   - Checks environment variables

### Integration Tests

1. **Ollama API** (`test-ollama-api.js`)
   - Tests connection to Ollama server
   - Checks Ollama version
   - Lists available models
   - Verifies DeepSeek model availability
   - Tests text generation
   - Tests chat format (if supported)

## Prerequisites

### For Unit Tests
- Node must be built (`npm run build`)
- No external dependencies required

### For Integration Tests
- Ollama must be installed and running
- DeepSeek model must be pulled:
  ```bash
  ollama pull deepseek-r1:1.5b
  ```

## Setup Instructions

1. **Install Ollama**
   - Download from: https://ollama.ai
   - Follow installation instructions for your OS

2. **Start Ollama Server**
   ```bash
   ollama serve
   ```

3. **Pull DeepSeek Model**
   ```bash
   ollama pull deepseek-r1:1.5b
   ```

4. **Build the Node**
   ```bash
   npm run build
   ```

5. **Run Tests**
   ```bash
   npm test
   ```

## Environment Variables (Optional)

DeepSeek uses Ollama's default configuration, but you can override:

```bash
# Custom Ollama host
export OLLAMA_HOST=192.168.1.100

# Custom Ollama port
export OLLAMA_PORT=11435

# Custom API base URL
export OLLAMA_API_BASE=http://custom-ollama:11434
```

## Test Results

Test results are exported to `test-results.json` containing:
- Timestamp
- Summary (passed/failed counts)
- Individual test results
- Test descriptions

## Troubleshooting

### Node Won't Load
- Run `npm run build` to compile TypeScript
- Check for TypeScript errors
- Verify `dist/` directory exists

### Ollama Connection Fails
- Ensure Ollama is running: `ollama serve`
- Check firewall settings
- Verify port 11434 is not in use
- Try: `curl http://localhost:11434/api/version`

### DeepSeek Model Not Found
- Pull the model: `ollama pull deepseek-r1:1.5b`
- List models: `ollama list`
- Try alternative versions: `deepseek-r1`, `deepseek`

### Generation Fails
- Check model is loaded: `ollama run deepseek-r1:1.5b "test"`
- Verify sufficient memory available
- Check Ollama logs for errors

## DeepSeek Features

The node supports:
- Text generation via `/api/generate`
- Optional chat format via `/api/chat`
- Thinking mode (shows reasoning process)
- Temperature and max tokens control
- Streaming responses (if implemented)

## Notes

- DeepSeek runs through Ollama, not a direct API
- No API keys or authentication required
- Model runs locally, requiring sufficient RAM
- First generation may be slow (model loading)
- Supports both completion and chat formats