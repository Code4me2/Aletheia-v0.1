const http = require('http');

// Proxy server that translates Ollama API calls to llama.cpp format
const LLAMA_SERVER = process.env.LLAMA_SERVER || 'http://localhost:11434';
const PROXY_PORT = parseInt(process.env.OLLAMA_PROXY_PORT || '11435');

console.log(`Starting Ollama proxy: ${PROXY_PORT} -> ${LLAMA_SERVER}`);

const proxy = http.createServer(async (req, res) => {
  let body = '';
  
  req.on('data', chunk => body += chunk);
  req.on('end', async () => {
    try {
      // Handle Ollama /api/generate endpoint
      if (req.method === 'POST' && req.url === '/api/generate') {
        const ollamaRequest = JSON.parse(body);
        
        // Translate to llama.cpp format
        const llamaRequest = {
          prompt: ollamaRequest.prompt,
          n_predict: ollamaRequest.options?.num_predict || 512,
          temperature: ollamaRequest.options?.temperature || 0.8,
          top_k: ollamaRequest.options?.top_k || 40,
          top_p: ollamaRequest.options?.top_p || 0.95,
          stream: false
        };

        // Make request to llama.cpp server
        const response = await fetch(`${LLAMA_SERVER}/completion`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(llamaRequest)
        });

        const llamaResponse = await response.json();

        // Translate response back to Ollama format
        const ollamaResponse = {
          model: ollamaRequest.model || 'bitnet',
          created_at: new Date().toISOString(),
          response: llamaResponse.content,
          done: true,
          context: [],
          total_duration: (llamaResponse.timings?.total_time || 0) * 1000000, // convert to nanoseconds
          load_duration: 0,
          prompt_eval_duration: (llamaResponse.timings?.prompt_ms || 0) * 1000000,
          eval_count: llamaResponse.tokens_predicted,
          eval_duration: (llamaResponse.timings?.predicted_ms || 0) * 1000000
        };

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(ollamaResponse));
        
      } else {
        // Forward all other requests as-is
        const proxyReq = http.request(
          `${LLAMA_SERVER}${req.url}`,
          {
            method: req.method,
            headers: req.headers
          },
          (proxyRes) => {
            res.writeHead(proxyRes.statusCode, proxyRes.headers);
            proxyRes.pipe(res);
          }
        );
        
        proxyReq.on('error', (e) => {
          res.writeHead(500);
          res.end(JSON.stringify({ error: e.message }));
        });
        
        if (body) proxyReq.write(body);
        proxyReq.end();
      }
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: error.message }));
    }
  });
});

proxy.listen(PROXY_PORT, () => {
  console.log(`Ollama-to-llama proxy running on port ${PROXY_PORT}`);
  console.log(`Forwarding Ollama API calls to llama.cpp server at ${LLAMA_SERVER}`);
});

// For ES modules compatibility
if (!global.fetch) {
  const { default: fetch } = require('node-fetch');
  global.fetch = fetch;
}