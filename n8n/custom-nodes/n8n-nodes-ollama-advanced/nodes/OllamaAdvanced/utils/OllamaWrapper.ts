import { NodeOperationError } from 'n8n-workflow';

export interface OllamaModel {
  name: string;
  modified_at: string;
  size: number;
  digest: string;
  details?: {
    format?: string;
    family?: string;
    parameter_size?: string;
    quantization_level?: string;
  };
}

export interface OllamaGenerateRequest {
  model: string;
  prompt: string;
  options?: any;
  stream?: boolean;
  format?: string;
  context?: number[];
  system?: string;
  template?: string;
  raw?: boolean;
  keep_alive?: string | number;
}

export interface OllamaChatRequest {
  model: string;
  messages: Array<{
    role: string;
    content: string;
    images?: string[];
  }>;
  options?: any;
  stream?: boolean;
  format?: string;
  keep_alive?: string | number;
}

export interface OllamaEmbeddingRequest {
  model: string;
  prompt: string;
  options?: any;
  keep_alive?: string | number;
}

export class OllamaConnectionManager {
  private baseUrl: string;
  private headers: HeadersInit;

  constructor(baseUrl: string = 'http://localhost:11434') {
    this.baseUrl = baseUrl.replace(/\/$/, ''); // Remove trailing slash
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  /**
   * Check if Ollama service is healthy
   */
  async checkHealth(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`, {
        method: 'GET',
        headers: this.headers,
      });
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  /**
   * List all available models
   */
  async listModels(): Promise<OllamaModel[]> {
    try {
      const response = await fetch(`${this.baseUrl}/api/tags`, {
        method: 'GET',
        headers: this.headers,
      });
      
      if (!response.ok) {
        throw new Error(`Failed to list models: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data.models || [];
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to connect to Ollama: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Pull a model from Ollama library
   */
  async pullModel(modelName: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/pull`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          name: modelName,
          stream: false,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to pull model ${modelName}: ${error}`);
      }
      
      // Wait for pull to complete
      const result = await response.json();
      if (result.error) {
        throw new Error(`Failed to pull model: ${result.error}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to pull model: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Delete a model
   */
  async deleteModel(modelName: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/delete`, {
        method: 'DELETE',
        headers: this.headers,
        body: JSON.stringify({
          name: modelName,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to delete model ${modelName}: ${error}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to delete model: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Get model information
   */
  async getModelInfo(modelName: string): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/show`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          name: modelName,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to get model info for ${modelName}: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to get model info: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Ensure a model exists (pull if necessary)
   */
  async ensureModel(modelName: string): Promise<void> {
    const models = await this.listModels();
    const modelExists = models.some(m => m.name === modelName);
    
    if (!modelExists) {
      console.log(`Model ${modelName} not found, pulling...`);
      await this.pullModel(modelName);
    }
  }

  /**
   * Generate text completion
   */
  async generate(request: OllamaGenerateRequest): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          ...request,
          stream: false, // Always disable streaming for n8n
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Generation failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to generate: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Chat with model
   */
  async chat(request: OllamaChatRequest): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/chat`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          ...request,
          stream: false, // Always disable streaming for n8n
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Chat failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to chat: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Generate embeddings
   */
  async embeddings(request: OllamaEmbeddingRequest): Promise<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/embeddings`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify(request),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Embedding generation failed: ${error}`);
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to generate embeddings: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Stream generate text (returns async generator)
   */
  async *streamGenerate(request: OllamaGenerateRequest): AsyncGenerator<any> {
    try {
      const response = await fetch(`${this.baseUrl}/api/generate`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          ...request,
          stream: true,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Stream generation failed: ${error}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Response body is not readable');
      }
      
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (const line of lines) {
          if (line.trim()) {
            try {
              const data = JSON.parse(line);
              yield data;
            } catch (e) {
              console.error('Failed to parse streaming response:', line);
            }
          }
        }
      }
      
      // Process any remaining buffer
      if (buffer.trim()) {
        try {
          const data = JSON.parse(buffer);
          yield data;
        } catch (e) {
          console.error('Failed to parse final streaming response:', buffer);
        }
      }
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to stream generate: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Copy a model
   */
  async copyModel(source: string, destination: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/copy`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          source,
          destination,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to copy model from ${source} to ${destination}: ${error}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to copy model: ${error.message}`);
      }
      throw error;
    }
  }

  /**
   * Create a model from a Modelfile
   */
  async createModel(name: string, modelfile: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/api/create`, {
        method: 'POST',
        headers: this.headers,
        body: JSON.stringify({
          name,
          modelfile,
          stream: false,
        }),
      });
      
      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Failed to create model ${name}: ${error}`);
      }
      
      const result = await response.json();
      if (result.error) {
        throw new Error(`Failed to create model: ${result.error}`);
      }
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`Failed to create model: ${error.message}`);
      }
      throw error;
    }
  }
}