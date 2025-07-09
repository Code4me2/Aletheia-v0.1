import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IDataObject,
  NodeOperationError,
  NodeConnectionType,
  ISupplyDataFunctions,
} from 'n8n-workflow';

import { RecursiveSummaryManager, SummaryLevel } from './RecursiveSummary';

import * as dotenv from 'dotenv';
import * as path from 'path';

// Load BitNet-specific environment variables
const envPath = path.resolve(__dirname, '../../.env.bitnet');
dotenv.config({ path: envPath });

// Load the wrapper - when compiled, this will be in dist/
const BitNetServerWrapper = require(path.resolve(__dirname, '../../bitnet-server-wrapper.js'));

// Singleton server instance
let serverInstance: any = null;

export class BitNet implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'BitNet LLM',
    name: 'bitnet',
    icon: 'file:bitnet.svg',
    group: ['ai', 'languageModel'],
    version: 1,
    subtitle: '={{$parameter.operation + ": " + $parameter.model}}',
    description: 'Interact with BitNet 1-bit LLMs for efficient inference',
    defaults: {
      name: 'BitNet',
    },
    inputs: [{ type: NodeConnectionType.Main }],
    outputs: [
      { type: NodeConnectionType.Main },
      { 
        type: NodeConnectionType.AiLanguageModel,
        displayName: 'Model'
      }
    ],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        noDataExpression: true,
        options: [
          {
            name: 'Text Completion',
            value: 'completion',
            description: 'Generate text completion',
            action: 'Generate text completion',
          },
          {
            name: 'Chat Completion',
            value: 'chat',
            description: 'Chat with conversation context',
            action: 'Chat with conversation context',
          },
          {
            name: 'Recursive Summary',
            value: 'recursive_summary',
            description: 'Create hierarchical summaries of large texts',
            action: 'Create recursive summary',
          },
          {
            name: 'Generate Embeddings',
            value: 'embeddings',
            description: 'Create text embeddings',
            action: 'Generate text embeddings',
          },
          {
            name: 'Tokenize',
            value: 'tokenize',
            description: 'Convert text to tokens',
            action: 'Tokenize text',
          },
          {
            name: 'Health Check',
            value: 'health',
            description: 'Check BitNet server health',
            action: 'Check server health',
          },
          {
            name: 'Server Control',
            value: 'server_control',
            description: 'Start/stop BitNet server',
            action: 'Control server',
          },
        ],
        default: 'completion',
      },
      // Server Configuration
      {
        displayName: 'Server Mode',
        name: 'serverMode',
        type: 'options',
        options: [
          {
            name: 'External Server',
            value: 'external',
            description: 'Connect to existing BitNet server',
          },
          {
            name: 'Managed Server',
            value: 'managed',
            description: 'Auto-manage BitNet server lifecycle',
          },
        ],
        default: 'external',
        description: 'How to connect to BitNet server',
      },
      {
        displayName: 'BitNet Server URL',
        name: 'serverUrl',
        type: 'string',
        default: process.env.BITNET_EXTERNAL_SERVER_URL || 'http://localhost:11434',
        description: 'URL of the BitNet inference server',
        displayOptions: {
          show: {
            serverMode: ['external'],
          },
        },
      },
      // Managed Server Configuration
      {
        displayName: 'BitNet Installation Path',
        name: 'bitnetPath',
        type: 'string',
        default: process.env.BITNET_INSTALLATION_PATH || '/opt/bitnet',
        description: 'Path to BitNet installation directory',
        displayOptions: {
          show: {
            serverMode: ['managed'],
          },
        },
      },
      {
        displayName: 'Server Port',
        name: 'serverPort',
        type: 'number',
        default: parseInt(process.env.BITNET_SERVER_PORT || '11434'),
        description: 'Port for managed BitNet server',
        displayOptions: {
          show: {
            serverMode: ['managed'],
          },
        },
      },
      // Model Selection
      {
        displayName: 'Model',
        name: 'model',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['completion', 'chat', 'embeddings', 'recursive_summary'],
          },
        },
        options: [
          {
            name: 'BitNet b1.58 2B',
            value: process.env.BITNET_MODEL_PATH || 'models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf',
            description: 'Official BitNet 2B model',
          },
          {
            name: 'BitNet b1.58 3B',
            value: 'models/bitnet_b1_58-3B/ggml-model.gguf',
            description: 'BitNet 3B model',
          },
          {
            name: 'BitNet b1.58 Large',
            value: 'models/bitnet_b1_58-large/ggml-model.gguf',
            description: 'BitNet Large model',
          },
          {
            name: 'Custom Model',
            value: 'custom',
            description: 'Specify a custom model path',
          },
        ],
        default: 'models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf',
        description: 'Model to use for inference',
      },
      {
        displayName: 'Custom Model Path',
        name: 'customModel',
        type: 'string',
        displayOptions: {
          show: {
            model: ['custom'],
          },
        },
        default: '',
        placeholder: '/path/to/model.gguf',
        description: 'Path to custom BitNet model file',
      },
      // Server Control Operation
      {
        displayName: 'Server Action',
        name: 'serverAction',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['server_control'],
          },
        },
        options: [
          {
            name: 'Start',
            value: 'start',
            description: 'Start the BitNet server',
          },
          {
            name: 'Stop',
            value: 'stop',
            description: 'Stop the BitNet server',
          },
          {
            name: 'Restart',
            value: 'restart',
            description: 'Restart the BitNet server',
          },
          {
            name: 'Status',
            value: 'status',
            description: 'Check server status',
          },
        ],
        default: 'start',
      },
      // Recursive Summary Parameters
      {
        displayName: 'Text Source',
        name: 'textSource',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['recursive_summary'],
          },
        },
        options: [
          {
            name: 'Input Field',
            value: 'field',
            description: 'Use text from input data',
          },
          {
            name: 'Direct Input',
            value: 'direct',
            description: 'Enter text directly',
          },
        ],
        default: 'field',
      },
      {
        displayName: 'Text Field',
        name: 'textField',
        type: 'string',
        default: 'text',
        required: true,
        displayOptions: {
          show: {
            operation: ['recursive_summary'],
            textSource: ['field'],
          },
        },
        description: 'Field containing text to summarize',
      },
      {
        displayName: 'Text',
        name: 'summaryText',
        type: 'string',
        typeOptions: {
          rows: 10,
        },
        default: '',
        required: true,
        displayOptions: {
          show: {
            operation: ['recursive_summary'],
            textSource: ['direct'],
          },
        },
        description: 'Text to summarize',
      },
      {
        displayName: 'Summary Options',
        name: 'summaryOptions',
        type: 'collection',
        placeholder: 'Add Option',
        default: {},
        displayOptions: {
          show: {
            operation: ['recursive_summary'],
          },
        },
        options: [
          {
            displayName: 'Max Chunk Size',
            name: 'maxChunkSize',
            type: 'number',
            default: 2048,
            description: 'Maximum size of text chunks',
          },
          {
            displayName: 'Chunk Overlap',
            name: 'overlapSize',
            type: 'number',
            default: 200,
            description: 'Number of characters to overlap between chunks',
          },
          {
            displayName: 'Summary Ratio',
            name: 'summaryRatio',
            type: 'number',
            typeOptions: {
              minValue: 0.1,
              maxValue: 0.9,
              numberPrecision: 2,
            },
            default: 0.3,
            description: 'Target summary length as ratio of original',
          },
          {
            displayName: 'Max Recursion Levels',
            name: 'maxLevels',
            type: 'number',
            default: 3,
            description: 'Maximum levels of summarization',
          },
          {
            displayName: 'Topic',
            name: 'topic',
            type: 'string',
            default: '',
            description: 'Optional topic to focus the summary on',
          },
          {
            displayName: 'Output Format',
            name: 'outputFormat',
            type: 'options',
            options: [
              {
                name: 'Hierarchical',
                value: 'hierarchical',
                description: 'Full hierarchical structure',
              },
              {
                name: 'Final Summary Only',
                value: 'final',
                description: 'Just the final summary',
              },
              {
                name: 'All Summaries',
                value: 'all',
                description: 'All intermediate summaries',
              },
            ],
            default: 'hierarchical',
          },
        ],
      },
      // Text Completion Parameters
      {
        displayName: 'Prompt',
        name: 'prompt',
        type: 'string',
        default: '',
        required: true,
        displayOptions: {
          show: {
            operation: ['completion'],
          },
        },
        description: 'Text prompt for completion',
        placeholder: 'Once upon a time...',
      },
      // Chat Parameters
      {
        displayName: 'Message Source',
        name: 'messageSource',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['chat'],
          },
        },
        options: [
          {
            name: 'Input Data',
            value: 'inputData',
            description: 'Use messages from incoming data',
          },
          {
            name: 'Parameters',
            value: 'parameters',
            description: 'Use messages defined in parameters',
          },
        ],
        default: 'parameters',
        description: 'Where to get the chat messages from',
      },
      {
        displayName: 'Message Field',
        name: 'messageField',
        type: 'string',
        default: 'message',
        displayOptions: {
          show: {
            operation: ['chat'],
            messageSource: ['inputData'],
          },
        },
        description: 'Name of the field containing the message in the input data',
        placeholder: 'message',
      },
      {
        displayName: 'Messages',
        name: 'messages',
        type: 'json',
        default: '',
        required: false,
        displayOptions: {
          show: {
            operation: ['chat'],
            messageSource: ['parameters'],
          },
        },
        description: 'Chat messages in JSON format, or just type plain text',
        placeholder: 'Hello! or [{"role": "user", "content": "Hello!"}]',
      },
      {
        displayName: 'System Prompt',
        name: 'systemPrompt',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['chat'],
          },
        },
        description: 'System message to set context',
        placeholder: 'You are a helpful assistant...',
      },
      {
        displayName: 'User Message',
        name: 'userMessage',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['chat'],
          },
        },
        description: 'Simple message input (used if messages array is empty)',
        placeholder: 'Hello, how are you?',
      },
      // Embedding Parameters
      {
        displayName: 'Text',
        name: 'embeddingText',
        type: 'string',
        default: '',
        required: true,
        displayOptions: {
          show: {
            operation: ['embeddings'],
          },
        },
        description: 'Text to generate embeddings for',
      },
      // Tokenize Parameters
      {
        displayName: 'Text',
        name: 'tokenizeText',
        type: 'string',
        default: '',
        required: true,
        displayOptions: {
          show: {
            operation: ['tokenize'],
          },
        },
        description: 'Text to tokenize',
      },
      // Generation Parameters
      {
        displayName: 'Additional Options',
        name: 'additionalOptions',
        type: 'collection',
        placeholder: 'Add Option',
        default: {},
        displayOptions: {
          show: {
            operation: ['completion', 'chat', 'recursive_summary'],
          },
        },
        options: [
          {
            displayName: 'Temperature',
            name: 'temperature',
            type: 'number',
            typeOptions: {
              minValue: 0,
              maxValue: 2,
              numberPrecision: 2,
            },
            default: 0.7,
            description: 'Controls randomness (0=deterministic, 2=very random)',
          },
          {
            displayName: 'Max Tokens',
            name: 'maxTokens',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: 512,
            description: 'Maximum tokens to generate',
          },
          {
            displayName: 'Top P',
            name: 'topP',
            type: 'number',
            typeOptions: {
              minValue: 0,
              maxValue: 1,
              numberPrecision: 2,
            },
            default: 0.9,
            description: 'Nucleus sampling threshold',
          },
          {
            displayName: 'Top K',
            name: 'topK',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: 40,
            description: 'Top K sampling parameter',
          },
          {
            displayName: 'Stop Sequences',
            name: 'stopSequences',
            type: 'string',
            default: '',
            description: 'Comma-separated stop sequences',
            placeholder: '\n\n,END,STOP',
          },
          {
            displayName: 'Stream Response',
            name: 'stream',
            type: 'boolean',
            default: false,
            description: 'Whether to stream the response',
          },
          {
            displayName: 'Include Thinking',
            name: 'includeThinking',
            type: 'boolean',
            default: false,
            description: 'Whether to include reasoning process in response',
          },
        ],
      },
      // AI Language Model Options (for when used as AI provider)
      {
        displayName: 'AI Model Output Limit',
        name: 'aiModelMaxTokens',
        type: 'number',
        default: 150,
        description: 'Maximum tokens when used as AI Language Model provider (e.g., with Hierarchical Summarization)',
        hint: 'Overrides requests from connected nodes. Set to 50 for short summaries, 150 for medium, 500 for long.',
        typeOptions: {
          minValue: 10,
          maxValue: 2048,
        },
      },
      // Performance Options
      {
        displayName: 'Performance Options',
        name: 'performanceOptions',
        type: 'collection',
        placeholder: 'Add Option',
        default: {},
        options: [
          {
            displayName: 'CPU Threads',
            name: 'threads',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: parseInt(process.env.BITNET_CPU_THREADS || '4'),
            description: 'Number of CPU threads to use',
          },
          {
            displayName: 'GPU Layers',
            name: 'gpuLayers',
            type: 'number',
            typeOptions: {
              minValue: 0,
            },
            default: parseInt(process.env.BITNET_GPU_LAYERS || '0'),
            description: 'Number of layers to offload to GPU (0=CPU only)',
          },
          {
            displayName: 'Context Size',
            name: 'contextSize',
            type: 'number',
            typeOptions: {
              minValue: 512,
            },
            default: parseInt(process.env.BITNET_CONTEXT_SIZE || '4096'),
            description: 'Maximum context window size',
          },
          {
            displayName: 'Batch Size',
            name: 'batchSize',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: parseInt(process.env.BITNET_BATCH_SIZE || '512'),
            description: 'Batch size for processing',
          },
        ],
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;
    const serverMode = this.getNodeParameter('serverMode', 0) as string;

    // Get server URL based on mode
    let serverUrl: string;
    if (serverMode === 'managed') {
      // Ensure server is running
      if (!serverInstance) {
        const bitnetPath = this.getNodeParameter('bitnetPath', 0) as string;
        const serverPort = this.getNodeParameter('serverPort', 0) as number;
        const perfOptions = this.getNodeParameter('performanceOptions', 0) as IDataObject;
        
        serverInstance = new BitNetServerWrapper({
          bitnetPath,
          port: serverPort,
          contextSize: perfOptions.contextSize || 4096,
          threads: perfOptions.threads || 4,
          gpuLayers: perfOptions.gpuLayers || 0,
        });

        try {
          await serverInstance.start();
        } catch (error) {
          throw new NodeOperationError(
            this.getNode(),
            `Failed to start BitNet server: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      }
      serverUrl = serverInstance.getServerUrl();
    } else {
      serverUrl = this.getNodeParameter('serverUrl', 0) as string;
    }

    // Handle server control operations
    if (operation === 'server_control') {
      const action = this.getNodeParameter('serverAction', 0) as string;
      
      if (serverMode !== 'managed') {
        throw new NodeOperationError(
          this.getNode(),
          'Server control operations require managed server mode',
        );
      }

      let result: IDataObject = {};
      
      switch (action) {
        case 'start':
          if (!serverInstance) {
            const bitnetPath = this.getNodeParameter('bitnetPath', 0) as string;
            const serverPort = this.getNodeParameter('serverPort', 0) as number;
            const perfOptions = this.getNodeParameter('performanceOptions', 0) as IDataObject;
            
            serverInstance = new BitNetServerWrapper({
              bitnetPath,
              port: serverPort,
              contextSize: perfOptions.contextSize || 4096,
              threads: perfOptions.threads || 4,
              gpuLayers: perfOptions.gpuLayers || 0,
            });
          }
          
          await serverInstance.start();
          result = { status: 'started', url: serverInstance.getServerUrl() };
          break;
          
        case 'stop':
          if (serverInstance) {
            serverInstance.stop();
            serverInstance = null;
          }
          result = { status: 'stopped' };
          break;
          
        case 'restart':
          if (serverInstance) {
            serverInstance.stop();
            await new Promise(resolve => setTimeout(resolve, 2000));
            await serverInstance.start();
          }
          result = { status: 'restarted', url: serverInstance.getServerUrl() };
          break;
          
        case 'status':
          result = {
            status: serverInstance && serverInstance.isRunning() ? 'running' : 'stopped',
            url: serverInstance ? serverInstance.getServerUrl() : null,
          };
          break;
      }
      
      returnData.push({ json: result });
      return [returnData];
    }

    // Handle recursive summary operation
    if (operation === 'recursive_summary') {
      const summaryManager = new RecursiveSummaryManager();
      
      for (let i = 0; i < items.length; i++) {
        try {
          // Get text to summarize
          const textSource = this.getNodeParameter('textSource', i) as string;
          let text: string;
          
          if (textSource === 'field') {
            const fieldName = this.getNodeParameter('textField', i) as string;
            text = items[i].json[fieldName] as string;
            
            if (!text) {
              throw new NodeOperationError(
                this.getNode(),
                `Field "${fieldName}" not found or empty in input data`,
              );
            }
          } else {
            text = this.getNodeParameter('summaryText', i) as string;
          }

          // Get summary options
          const summaryOptions = this.getNodeParameter('summaryOptions', i) as IDataObject;
          const additionalOptions = this.getNodeParameter('additionalOptions', i) as IDataObject;

          // Configure summary manager
          const config = {
            maxChunkSize: summaryOptions.maxChunkSize as number || 2048,
            overlapSize: summaryOptions.overlapSize as number || 200,
            summaryRatio: summaryOptions.summaryRatio as number || 0.3,
            maxLevels: summaryOptions.maxLevels as number || 3,
          };

          const summaryManagerWithConfig = new RecursiveSummaryManager(config);
          
          // Perform recursive summarization
          const levels: SummaryLevel[] = [];
          let currentText = text;
          let currentLevel = 0;

          while (currentLevel < config.maxLevels && summaryManagerWithConfig.needsChunking(currentText, 3000)) {
            const chunks = summaryManagerWithConfig.splitIntoChunks(currentText);
            const summaries: string[] = [];

            // Process each chunk
            for (const chunk of chunks) {
              const prompt = summaryManagerWithConfig.generateSummaryPrompt(
                chunk, 
                currentLevel,
                { topic: summaryOptions.topic }
              );

              // Make API call to summarize chunk
              const response = await this.helpers.httpRequest({
                method: 'POST',
                url: `${serverUrl}/completion`,
                headers: {
                  'Content-Type': 'application/json',
                },
                body: {
                  prompt,
                  temperature: additionalOptions.temperature || 0.7,
                  max_tokens: Math.floor(chunk.length * config.summaryRatio / 4), // Estimate tokens
                  top_p: additionalOptions.topP || 0.9,
                  top_k: additionalOptions.topK || 40,
                },
                json: true,
              });

              const summaryText = response.choices?.[0]?.text || response.content || '';
              summaries.push(summaryText);
            }

            // Store level data
            levels.push({
              level: currentLevel,
              chunks,
              summaries,
              metadata: {
                chunkCount: chunks.length,
                totalLength: currentText.length,
                summaryLength: summaries.join(' ').length,
              },
            });

            // Prepare for next level
            currentText = summaryManagerWithConfig.mergeSummaries(summaries);
            currentLevel++;

            // Break if text is now small enough
            if (currentText.length < config.maxChunkSize) {
              // Do one final summary
              const finalPrompt = summaryManagerWithConfig.generateSummaryPrompt(
                currentText,
                currentLevel,
                { topic: summaryOptions.topic }
              );

              const finalResponse = await this.helpers.httpRequest({
                method: 'POST',
                url: `${serverUrl}/completion`,
                headers: {
                  'Content-Type': 'application/json',
                },
                body: {
                  prompt: finalPrompt,
                  temperature: additionalOptions.temperature || 0.7,
                  max_tokens: Math.floor(currentText.length * 0.5 / 4),
                  top_p: additionalOptions.topP || 0.9,
                  top_k: additionalOptions.topK || 40,
                },
                json: true,
              });

              const finalSummary = finalResponse.choices?.[0]?.text || finalResponse.content || '';
              
              levels.push({
                level: currentLevel,
                chunks: [currentText],
                summaries: [finalSummary],
                metadata: {
                  chunkCount: 1,
                  totalLength: currentText.length,
                  summaryLength: finalSummary.length,
                },
              });
              
              break;
            }
          }

          // Format output based on preference
          const outputFormat = summaryOptions.outputFormat as string || 'hierarchical';
          let result: IDataObject;

          switch (outputFormat) {
            case 'final':
              result = {
                summary: levels[levels.length - 1].summaries[0],
                metadata: {
                  originalLength: text.length,
                  summaryLength: levels[levels.length - 1].summaries[0].length,
                  compressionRatio: (levels[levels.length - 1].summaries[0].length / text.length).toFixed(2),
                  levelsProcessed: levels.length,
                },
              };
              break;
              
            case 'all':
              result = {
                summaries: levels.map((level, index) => ({
                  level: index,
                  text: summaryManagerWithConfig.mergeSummaries(level.summaries),
                  metadata: level.metadata,
                })),
              };
              break;
              
            case 'hierarchical':
            default:
              result = summaryManagerWithConfig.formatHierarchicalSummary(levels);
              break;
          }

          returnData.push({ json: result });
        } catch (error) {
          if (this.continueOnFail()) {
            returnData.push({
              json: {
                error: error instanceof Error ? error.message : String(error),
              },
              pairedItem: i,
            });
            continue;
          }
          throw error;
        }
      }
      
      return [returnData];
    }

    // Handle other operations (existing code)
    for (let i = 0; i < items.length; i++) {
      try {
        let response: any;
        let endpoint: string;
        let method: string = 'POST';
        let body: any = {};

        // Get model configuration
        const model = this.getNodeParameter('model', i) as string;
        const modelPath = model === 'custom' 
          ? this.getNodeParameter('customModel', i) as string 
          : model;

        switch (operation) {
          case 'completion':
            endpoint = '/completion';
            const prompt = this.getNodeParameter('prompt', i) as string;
            const additionalOptions = this.getNodeParameter('additionalOptions', i) as IDataObject;
            
            body = {
              model: modelPath,
              prompt: prompt,
              temperature: additionalOptions.temperature || 0.7,
              max_tokens: additionalOptions.maxTokens || 512,
              top_p: additionalOptions.topP || 0.9,
              top_k: additionalOptions.topK || 40,
              stream: additionalOptions.stream || false,
            };

            // Add stop sequences if provided
            if (additionalOptions.stopSequences) {
              body.stop = (additionalOptions.stopSequences as string)
                .split(',')
                .map(s => s.trim())
                .filter(s => s.length > 0);
            }

            // Add performance options
            const perfOptions = this.getNodeParameter('performanceOptions', i) as IDataObject;
            if (perfOptions.threads) body.n_threads = perfOptions.threads;
            if (perfOptions.gpuLayers) body.n_gpu_layers = perfOptions.gpuLayers;
            if (perfOptions.contextSize) body.n_ctx = perfOptions.contextSize;
            if (perfOptions.batchSize) body.n_batch = perfOptions.batchSize;
            break;

          case 'chat':
            endpoint = '/v1/chat/completions';
            const messagesParam = this.getNodeParameter('messages', i);
            const systemPrompt = this.getNodeParameter('systemPrompt', i) as string;
            const chatOptions = this.getNodeParameter('additionalOptions', i) as IDataObject;
            
            // Parse messages
            let messages: any[];
            if (typeof messagesParam === 'string') {
              const trimmed = messagesParam.trim();
              if (!trimmed || trimmed === '[]') {
                messages = [];
              } else {
                // Try to parse as JSON first
                try {
                  messages = JSON.parse(trimmed);
                } catch (error) {
                  // If not valid JSON, treat it as a plain text user message
                  messages = [{ role: 'user', content: trimmed }];
                }
              }
            } else if (Array.isArray(messagesParam)) {
              messages = messagesParam;
            } else {
              messages = [];
            }
            
            // If no messages provided, create a default user message
            if (messages.length === 0) {
              const userMessage = this.getNodeParameter('userMessage', i, '') as string;
              if (userMessage) {
                messages = [{ role: 'user', content: userMessage }];
              } else {
                throw new NodeOperationError(this.getNode(), 'No messages provided. Please add at least one message or use the userMessage field.');
              }
            }

            // Add system prompt if provided
            if (systemPrompt) {
              messages.unshift({
                role: 'system',
                content: systemPrompt,
              });
            }

            body = {
              model: modelPath,
              messages: messages,
              temperature: chatOptions.temperature || 0.7,
              max_tokens: chatOptions.maxTokens || 512,
              top_p: chatOptions.topP || 0.9,
              top_k: chatOptions.topK || 40,
              stream: chatOptions.stream || false,
            };

            // Add stop sequences if provided
            if (chatOptions.stopSequences) {
              body.stop = (chatOptions.stopSequences as string)
                .split(',')
                .map(s => s.trim())
                .filter(s => s.length > 0);
            }

            // Add performance options
            const chatPerfOptions = this.getNodeParameter('performanceOptions', i) as IDataObject;
            if (chatPerfOptions.threads) body.n_threads = chatPerfOptions.threads;
            if (chatPerfOptions.gpuLayers) body.n_gpu_layers = chatPerfOptions.gpuLayers;
            if (chatPerfOptions.contextSize) body.n_ctx = chatPerfOptions.contextSize;
            break;

          case 'embeddings':
            endpoint = '/v1/embeddings';
            const embeddingText = this.getNodeParameter('embeddingText', i) as string;
            
            body = {
              model: modelPath,
              input: embeddingText,
            };
            break;

          case 'tokenize':
            endpoint = '/tokenize';
            const tokenizeText = this.getNodeParameter('tokenizeText', i) as string;
            
            body = {
              content: tokenizeText,
            };
            break;

          case 'health':
            endpoint = '/health';
            method = 'GET';
            body = null;
            break;

          default:
            throw new NodeOperationError(this.getNode(), `Unknown operation: ${operation}`);
        }

        // Make HTTP request
        const url = `${serverUrl}${endpoint}`;
        
        try {
          const requestOptions: any = {
            method,
            headers: {
              'Content-Type': 'application/json',
            },
            json: true,
          };

          if (body && method !== 'GET') {
            requestOptions.body = body;
          }

          response = await this.helpers.httpRequest({
            ...requestOptions,
            url,
          });
        } catch (error) {
          if (error instanceof Error) {
            throw new NodeOperationError(
              this.getNode(),
              `Failed to connect to BitNet server at ${url}: ${error.message}`,
            );
          }
          throw error;
        }

        // Process response based on operation
        if (operation === 'completion') {
          // Extract completion text and metadata
          const result: IDataObject = {
            text: response.choices?.[0]?.text || response.content || '',
            model: response.model || modelPath,
            usage: response.usage || {},
          };

          // Handle thinking/reasoning if present
          if (response.choices?.[0]?.text) {
            const text = response.choices[0].text;
            const thinkingMatch = text.match(/<think>(.*?)<\/think>/s);
            if (thinkingMatch) {
              result.thinking = thinkingMatch[1].trim();
              result.text = text.replace(/<think>.*?<\/think>/s, '').trim();
            }
          }

          returnData.push({ json: result });
        } else if (operation === 'chat') {
          // Extract chat response
          const result: IDataObject = {
            content: response.choices?.[0]?.message?.content || '',
            role: response.choices?.[0]?.message?.role || 'assistant',
            model: response.model || modelPath,
            usage: response.usage || {},
            finish_reason: response.choices?.[0]?.finish_reason || 'stop',
          };

          // Handle thinking/reasoning if present
          const content = result.content as string;
          if (content) {
            const thinkingMatch = content.match(/<think>(.*?)<\/think>/s);
            if (thinkingMatch) {
              result.thinking = thinkingMatch[1].trim();
              result.content = content.replace(/<think>.*?<\/think>/s, '').trim();
            }
          }

          returnData.push({ json: result });
        } else if (operation === 'embeddings') {
          // Return embeddings
          returnData.push({
            json: {
              embeddings: response.data?.[0]?.embedding || response.embedding || [],
              model: response.model || modelPath,
              usage: response.usage || {},
            },
          });
        } else if (operation === 'tokenize') {
          // Return tokens
          returnData.push({
            json: {
              tokens: response.tokens || [],
              count: response.tokens?.length || 0,
            },
          });
        } else if (operation === 'health') {
          // Return health status
          returnData.push({
            json: {
              status: response.status || 'ok',
              model: response.model || 'unknown',
              slots: response.slots || {},
              version: response.version || 'unknown',
            },
          });
        } else {
          // Return raw response
          returnData.push({
            json: response as IDataObject,
          });
        }
      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              error: error instanceof Error ? error.message : String(error),
            },
            pairedItem: i,
          });
          continue;
        }
        throw error;
      }
    }

    return [returnData];
  }

  // AI Agent integration
  async supplyData(this: ISupplyDataFunctions): Promise<any> {
    const serverMode = this.getNodeParameter('serverMode', 0) as string;
    
    // Get server URL based on mode
    let serverUrl: string;
    if (serverMode === 'managed') {
      // Ensure server is running
      if (!serverInstance) {
        const bitnetPath = this.getNodeParameter('bitnetPath', 0) as string;
        const serverPort = this.getNodeParameter('serverPort', 0) as number;
        const perfOptions = this.getNodeParameter('performanceOptions', 0) as IDataObject;
        
        serverInstance = new BitNetServerWrapper({
          bitnetPath,
          port: serverPort,
          contextSize: perfOptions.contextSize || 4096,
          threads: perfOptions.threads || 4,
          gpuLayers: perfOptions.gpuLayers || 0,
        });

        try {
          await serverInstance.start();
        } catch (error) {
          throw new NodeOperationError(
            this.getNode(),
            `Failed to start BitNet server: ${error instanceof Error ? error.message : String(error)}`,
          );
        }
      }
      serverUrl = serverInstance.getServerUrl();
    } else {
      serverUrl = this.getNodeParameter('serverUrl', 0) as string;
    }

    // Get model configuration
    const modelName = this.getNodeParameter('model', 0) as string;
    const modelPath = modelName === 'custom' 
      ? this.getNodeParameter('customModel', 0) as string 
      : modelName;

    // Create a mock LangChain-compatible model object
    const model = {
      invoke: async (params: {
        messages: Array<{role: string, content: string}>,
        options?: {
          temperature?: number,
          maxTokensToSample?: number,
          [key: string]: any
        }
      }) => {
        const { messages, options = {} } = params;
        
        // Get additional options from node parameters
        const additionalOptions = this.getNodeParameter('additionalOptions', 0) as IDataObject;
        const perfOptions = this.getNodeParameter('performanceOptions', 0) as IDataObject;
        const aiModelMaxTokens = this.getNodeParameter('aiModelMaxTokens', 0) as number;
        
        // Prepare request body
        const body: any = {
          model: modelPath,
          messages: messages,
          temperature: options.temperature ?? additionalOptions.temperature ?? 0.7,
          max_tokens: options.maxTokensToSample ?? aiModelMaxTokens ?? additionalOptions.maxTokens ?? 512,
          top_p: options.topP ?? additionalOptions.topP ?? 0.9,
          top_k: options.topK ?? additionalOptions.topK ?? 40,
          stream: false, // AI Agents don't support streaming yet
        };

        // Add stop sequences if provided
        if (additionalOptions.stopSequences) {
          body.stop = (additionalOptions.stopSequences as string)
            .split(',')
            .map(s => s.trim())
            .filter(s => s.length > 0);
        }

        // Add performance options
        if (perfOptions.threads) body.n_threads = perfOptions.threads;
        if (perfOptions.gpuLayers) body.n_gpu_layers = perfOptions.gpuLayers;
        if (perfOptions.contextSize) body.n_ctx = perfOptions.contextSize;

        // Make API call
        const url = `${serverUrl}/v1/chat/completions`;
        
        try {
          const response = await this.helpers.httpRequest({
            method: 'POST',
            url,
            headers: {
              'Content-Type': 'application/json',
            },
            body,
            json: true,
          });

          // Extract response content
          const content = response.choices?.[0]?.message?.content || '';
          
          // Handle thinking/reasoning if present
          let finalContent = content;
          let thinking = '';
          if (content) {
            const thinkingMatch = content.match(/<think>(.*?)<\/think>/s);
            if (thinkingMatch) {
              thinking = thinkingMatch[1].trim();
              finalContent = content.replace(/<think>.*?<\/think>/s, '').trim();
            }
          }

          // Return in the format expected by AI Agents
          return {
            text: finalContent,
            content: finalContent,
            // Optional metadata that might be useful
            usage: response.usage,
            thinking: thinking || undefined,
          };
        } catch (error) {
          if (error instanceof Error) {
            throw new NodeOperationError(
              this.getNode(),
              `Failed to connect to BitNet server at ${url}: ${error.message}`,
            );
          }
          throw error;
        }
      }
    };

    // Return in LangChain-compatible format
    // The 'response' property is what LangChain nodes expect
    return {
      response: model,
      // Also keep the invoke method for backward compatibility
      invoke: model.invoke
    };
  }
}