import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IDataObject,
  NodeOperationError,
  NodeConnectionType,
  ISupplyDataFunctions,
  ILoadOptionsFunctions,
  INodePropertyOptions,
} from 'n8n-workflow';

import { OllamaConnectionManager } from './utils/OllamaWrapper';
import { RecursiveSummaryManager, SummaryLevel } from './utils/RecursiveSummary';

// Helper functions that accept execution context
function getConnectionUrl(context: IExecuteFunctions | ILoadOptionsFunctions | ISupplyDataFunctions, connectionMode: string, index: number = 0): string {
  switch (connectionMode) {
    case 'docker':
      return context.getNodeParameter('dockerHost', index) as string;
    case 'remote':
      return context.getNodeParameter('ollamaUrl', index) as string;
    case 'local':
    default:
      return 'http://localhost:11434';
  }
}

function getModelName(context: IExecuteFunctions | ISupplyDataFunctions, itemIndex: number): string {
  const model = context.getNodeParameter('model', itemIndex) as string;
  return model === 'custom'
    ? context.getNodeParameter('customModel', itemIndex) as string
    : model;
}

function buildOllamaOptions(context: IExecuteFunctions, genOptions: IDataObject, itemIndex: number): any {
  const perfOptions = context.getNodeParameter('performanceOptions', itemIndex) as IDataObject;
  
  const options: any = {};
  
  // Generation options
  if (genOptions.temperature !== undefined) options.temperature = genOptions.temperature;
  if (genOptions.maxTokens !== undefined) options.num_predict = genOptions.maxTokens;
  if (genOptions.topP !== undefined) options.top_p = genOptions.topP;
  if (genOptions.topK !== undefined) options.top_k = genOptions.topK;
  if (genOptions.repeatPenalty !== undefined) options.repeat_penalty = genOptions.repeatPenalty;
  if (genOptions.seed !== undefined && genOptions.seed !== 0) options.seed = genOptions.seed;
  
  // Performance options
  if (perfOptions.numCtx !== undefined) options.num_ctx = perfOptions.numCtx;
  if (perfOptions.numBatch !== undefined) options.num_batch = perfOptions.numBatch;
  if (perfOptions.numGpu !== undefined) options.num_gpu = perfOptions.numGpu;
  if (perfOptions.numThread !== undefined && perfOptions.numThread !== 0) {
    options.num_thread = perfOptions.numThread;
  }
  if (perfOptions.lowVram) options.low_vram = true;
  
  // Stop sequences
  if (genOptions.stop) {
    options.stop = (genOptions.stop as string).split(',').map(s => s.trim());
  }
  
  // Stream
  options.stream = genOptions.stream || false;
  
  return options;
}

function processResponse(response: any, includeReasoning: boolean): IDataObject {
  let content = response.response || response.message?.content || '';
  let reasoning = '';
  
  // Extract thinking/reasoning if present
  const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
  if (thinkMatch) {
    reasoning = thinkMatch[1].trim();
    if (!includeReasoning) {
      content = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
    }
  }
  
  const result: IDataObject = {
    content,
    model: response.model,
  };
  
  if (reasoning) {
    result.reasoning = reasoning;
  }
  
  if (response.total_duration) {
    result.duration_ms = Math.round(response.total_duration / 1000000);
  }
  
  if (response.eval_count && response.eval_duration) {
    result.tokens_per_second = Math.round(
      response.eval_count / (response.eval_duration / 1000000000)
    );
  }
  
  return result;
}

export class OllamaAdvanced implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Ollama Advanced',
    name: 'ollamaAdvanced',
    icon: 'file:ollama.svg',
    group: ['ai', 'languageModel'],
    version: 1,
    subtitle: '={{$parameter.operation + ": " + $parameter.model}}',
    description: 'Advanced Ollama integration with AI Agent support and recursive summarization',
    defaults: {
      name: 'Ollama Advanced',
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
            name: 'Chat',
            value: 'chat',
            description: 'Chat with conversation context',
            action: 'Chat with context',
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
            action: 'Generate embeddings',
          },
          {
            name: 'Vision Analysis',
            value: 'vision',
            description: 'Analyze images with multimodal models',
            action: 'Analyze images',
          },
          {
            name: 'Code Generation',
            value: 'code',
            description: 'Generate or analyze code',
            action: 'Generate code',
          },
          {
            name: 'Model Management',
            value: 'model_management',
            description: 'List, pull, or delete models',
            action: 'Manage models',
          },
          {
            name: 'Health Check',
            value: 'health',
            description: 'Check Ollama service health',
            action: 'Check health',
          },
        ],
        default: 'chat',
      },
      // Connection Configuration
      {
        displayName: 'Connection Mode',
        name: 'connectionMode',
        type: 'options',
        options: [
          {
            name: 'Local Ollama',
            value: 'local',
            description: 'Connect to local Ollama service',
          },
          {
            name: 'Remote Ollama',
            value: 'remote',
            description: 'Connect to remote Ollama instance',
          },
          {
            name: 'Docker Ollama',
            value: 'docker',
            description: 'Connect to Ollama in Docker',
          },
        ],
        default: 'local',
        description: 'How to connect to Ollama service',
      },
      {
        displayName: 'Ollama URL',
        name: 'ollamaUrl',
        type: 'string',
        default: 'http://localhost:11434',
        description: 'URL of the Ollama API',
        displayOptions: {
          show: {
            connectionMode: ['remote'],
          },
        },
      },
      {
        displayName: 'Docker Host',
        name: 'dockerHost',
        type: 'string',
        default: 'http://host.docker.internal:11434',
        description: 'URL for Docker-hosted Ollama',
        displayOptions: {
          show: {
            connectionMode: ['docker'],
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
            operation: ['completion', 'chat', 'recursive_summary', 'embeddings', 'vision', 'code'],
          },
        },
        typeOptions: {
          loadOptionsMethod: 'getModels',
        },
        default: '',
        description: 'Select or enter a model name. Popular models will auto-pull if not present.',
        options: [
          {
            name: 'QWQ 32B (Q4_K_M)',
            value: 'qwq:32b-q4_K_M',
            description: 'Qwen-based reasoning model, 32B parameters',
          },
          {
            name: 'Qwen3 Coder 30B (Q8_0)',
            value: 'qwen3-coder:30b-a3b-q8_0',
            description: 'Specialized for code generation, 30B parameters',
          },
          {
            name: 'Llama 3.2',
            value: 'llama3.2',
            description: 'Latest Llama model (will auto-pull)',
          },
          {
            name: 'DeepSeek R1',
            value: 'deepseek-r1:1.5b',
            description: 'DeepSeek reasoning model (will auto-pull)',
          },
          {
            name: 'Mistral',
            value: 'mistral',
            description: 'Mistral 7B model (will auto-pull)',
          },
          {
            name: 'Qwen 2.5',
            value: 'qwen2.5',
            description: 'Qwen 2.5 model (will auto-pull)',
          },
          {
            name: 'Custom Model',
            value: 'custom',
            description: 'Specify a custom model name',
          },
        ],
      },
      {
        displayName: 'Custom Model Name',
        name: 'customModel',
        type: 'string',
        displayOptions: {
          show: {
            model: ['custom'],
          },
        },
        default: '',
        placeholder: 'llama3.2:3b',
        description: 'Custom model name (format: name:tag)',
      },
      // Model Management Operations
      {
        displayName: 'Model Action',
        name: 'modelAction',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['model_management'],
          },
        },
        options: [
          {
            name: 'List Models',
            value: 'list',
            description: 'List all available models',
          },
          {
            name: 'Pull Model',
            value: 'pull',
            description: 'Download a model',
          },
          {
            name: 'Delete Model',
            value: 'delete',
            description: 'Remove a model',
          },
          {
            name: 'Model Info',
            value: 'info',
            description: 'Get model information',
          },
        ],
        default: 'list',
      },
      {
        displayName: 'Model to Manage',
        name: 'modelToManage',
        type: 'string',
        displayOptions: {
          show: {
            operation: ['model_management'],
            modelAction: ['pull', 'delete', 'info'],
          },
        },
        default: '',
        placeholder: 'llama3.2',
        description: 'Model name for management operation',
      },
      // Chat Parameters
      {
        displayName: 'Message',
        name: 'message',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['chat'],
          },
        },
        description: 'Message to send to the model',
        placeholder: 'How can I help you today?',
      },
      {
        displayName: 'System Prompt',
        name: 'systemPrompt',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['chat', 'code'],
          },
        },
        description: 'System message to set context',
        placeholder: 'You are a helpful assistant...',
      },
      {
        displayName: 'Conversation History',
        name: 'conversationHistory',
        type: 'json',
        default: '[]',
        displayOptions: {
          show: {
            operation: ['chat'],
          },
        },
        description: 'Previous messages in the conversation',
      },
      // Completion Parameters
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
      },
      // Code Generation Parameters
      {
        displayName: 'Code Task',
        name: 'codeTask',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['code'],
          },
        },
        options: [
          {
            name: 'Generate Code',
            value: 'generate',
            description: 'Generate new code',
          },
          {
            name: 'Explain Code',
            value: 'explain',
            description: 'Explain existing code',
          },
          {
            name: 'Review Code',
            value: 'review',
            description: 'Review code for improvements',
          },
          {
            name: 'Fix Code',
            value: 'fix',
            description: 'Fix errors in code',
          },
          {
            name: 'Convert Code',
            value: 'convert',
            description: 'Convert between languages',
          },
        ],
        default: 'generate',
      },
      {
        displayName: 'Code Input',
        name: 'codeInput',
        type: 'string',
        typeOptions: {
          rows: 10,
        },
        default: '',
        displayOptions: {
          show: {
            operation: ['code'],
          },
        },
        description: 'Code or requirements',
      },
      {
        displayName: 'Programming Language',
        name: 'programmingLanguage',
        type: 'string',
        default: 'python',
        displayOptions: {
          show: {
            operation: ['code'],
          },
        },
        description: 'Target programming language',
      },
      // Vision Parameters
      {
        displayName: 'Image Source',
        name: 'imageSource',
        type: 'options',
        displayOptions: {
          show: {
            operation: ['vision'],
          },
        },
        options: [
          {
            name: 'URL',
            value: 'url',
            description: 'Image from URL',
          },
          {
            name: 'Base64',
            value: 'base64',
            description: 'Base64 encoded image',
          },
        ],
        default: 'url',
      },
      {
        displayName: 'Image URL',
        name: 'imageUrl',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['vision'],
            imageSource: ['url'],
          },
        },
        description: 'URL of the image to analyze',
      },
      {
        displayName: 'Image Data',
        name: 'imageData',
        type: 'string',
        default: '',
        displayOptions: {
          show: {
            operation: ['vision'],
            imageSource: ['base64'],
          },
        },
        description: 'Base64 encoded image data',
      },
      {
        displayName: 'Vision Prompt',
        name: 'visionPrompt',
        type: 'string',
        default: 'What do you see in this image?',
        displayOptions: {
          show: {
            operation: ['vision'],
          },
        },
        description: 'Question about the image',
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
            displayName: 'Focus Topic',
            name: 'topic',
            type: 'string',
            default: '',
            description: 'Optional topic to focus the summary on',
          },
          {
            displayName: 'Summary Style',
            name: 'style',
            type: 'options',
            options: [
              {
                name: 'Concise',
                value: 'concise',
                description: 'Brief and to the point',
              },
              {
                name: 'Detailed',
                value: 'detailed',
                description: 'More comprehensive',
              },
              {
                name: 'Technical',
                value: 'technical',
                description: 'Preserve technical details',
              },
              {
                name: 'Executive',
                value: 'executive',
                description: 'High-level overview',
              },
            ],
            default: 'concise',
          },
        ],
      },
      // Generation Options
      {
        displayName: 'Generation Options',
        name: 'generationOptions',
        type: 'collection',
        placeholder: 'Add Option',
        default: {},
        displayOptions: {
          show: {
            operation: ['completion', 'chat', 'recursive_summary', 'code', 'vision'],
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
            default: 1024,
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
            displayName: 'Repeat Penalty',
            name: 'repeatPenalty',
            type: 'number',
            typeOptions: {
              minValue: 0,
              maxValue: 2,
              numberPrecision: 2,
            },
            default: 1.1,
            description: 'Penalty for repeating tokens',
          },
          {
            displayName: 'Stop Sequences',
            name: 'stop',
            type: 'string',
            default: '',
            description: 'Comma-separated stop sequences',
            placeholder: '\n\n,END,###',
          },
          {
            displayName: 'Seed',
            name: 'seed',
            type: 'number',
            default: 0,
            description: 'Random seed for reproducibility (0=random)',
          },
          {
            displayName: 'Stream Response',
            name: 'stream',
            type: 'boolean',
            default: false,
            description: 'Stream the response token by token',
          },
          {
            displayName: 'Include Reasoning',
            name: 'includeReasoning',
            type: 'boolean',
            default: false,
            description: 'Include thinking/reasoning process if available',
          },
        ],
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
            displayName: 'Context Window',
            name: 'numCtx',
            type: 'number',
            typeOptions: {
              minValue: 512,
            },
            default: 4096,
            description: 'Maximum context window size',
          },
          {
            displayName: 'Batch Size',
            name: 'numBatch',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: 512,
            description: 'Batch size for processing',
          },
          {
            displayName: 'GPU Layers',
            name: 'numGpu',
            type: 'number',
            typeOptions: {
              minValue: 0,
            },
            default: 999,
            description: 'Number of layers to offload to GPU (0=CPU only)',
          },
          {
            displayName: 'CPU Threads',
            name: 'numThread',
            type: 'number',
            typeOptions: {
              minValue: 1,
            },
            default: 0,
            description: 'Number of CPU threads (0=auto)',
          },
          {
            displayName: 'Keep Alive',
            name: 'keepAlive',
            type: 'string',
            default: '5m',
            description: 'How long to keep model in memory (e.g., 5m, 1h)',
          },
          {
            displayName: 'Low VRAM Mode',
            name: 'lowVram',
            type: 'boolean',
            default: false,
            description: 'Enable low VRAM mode for large models',
          },
        ],
      },
      // AI Model Output (for LangChain integration)
      {
        displayName: 'AI Model Max Tokens',
        name: 'aiModelMaxTokens',
        type: 'number',
        default: 256,
        description: 'Maximum tokens when used as AI Language Model provider',
        hint: 'Overrides connected node requests. Adjust based on use case.',
        typeOptions: {
          minValue: 10,
          maxValue: 8192,
        },
      },
    ],
  };

  methods = {
    loadOptions: {
      async getModels(this: ILoadOptionsFunctions): Promise<INodePropertyOptions[]> {
        try {
          const connectionMode = this.getNodeParameter('connectionMode', 0) as string;
          const url = getConnectionUrl(this, connectionMode);
          const manager = new OllamaConnectionManager(url);
          const models = await manager.listModels();
          
          return models.map(model => ({
            name: `${model.name} (${(model.size / 1024 / 1024 / 1024).toFixed(2)} GB)`,
            value: model.name,
            description: model.details?.parameter_size || 'Local model',
          }));
        } catch (error) {
          return [];
        }
      },
    },
  };


  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;

    for (let i = 0; i < items.length; i++) {
      try {
        const connectionMode = this.getNodeParameter('connectionMode', i) as string;
        const baseUrl = getConnectionUrl(this, connectionMode, i);
        const manager = new OllamaConnectionManager(baseUrl);

        // Check health first
        const isHealthy = await manager.checkHealth();
        if (!isHealthy && operation !== 'health') {
          throw new NodeOperationError(
            this.getNode(),
            `Cannot connect to Ollama service at ${baseUrl}`,
          );
        }

        let result: IDataObject = {};

        switch (operation) {
          case 'health':
            result = {
              healthy: isHealthy,
              url: baseUrl,
              timestamp: new Date().toISOString(),
            };
            
            if (isHealthy) {
              try {
                const models = await manager.listModels();
                result.modelCount = models.length;
                result.models = models.map(m => m.name);
              } catch (error) {
                result.modelsError = error instanceof Error ? error.message : 'Failed to list models';
              }
            }
            break;

          case 'model_management':
            const modelAction = this.getNodeParameter('modelAction', i) as string;
            
            switch (modelAction) {
              case 'list':
                const models = await manager.listModels();
                result = {
                  models: models,
                  count: models.length,
                };
                break;
                
              case 'pull':
                const modelToPull = this.getNodeParameter('modelToManage', i) as string;
                await manager.pullModel(modelToPull);
                result = {
                  action: 'pulled',
                  model: modelToPull,
                  success: true,
                };
                break;
                
              case 'delete':
                const modelToDelete = this.getNodeParameter('modelToManage', i) as string;
                await manager.deleteModel(modelToDelete);
                result = {
                  action: 'deleted',
                  model: modelToDelete,
                  success: true,
                };
                break;
                
              case 'info':
                const modelToInfo = this.getNodeParameter('modelToManage', i) as string;
                const info = await manager.getModelInfo(modelToInfo);
                result = info;
                break;
            }
            break;

          case 'chat':
            const chatModel = getModelName(this, i);
            const message = this.getNodeParameter('message', i) as string;
            const systemPrompt = this.getNodeParameter('systemPrompt', i, '') as string;
            const conversationHistory = this.getNodeParameter('conversationHistory', i, '[]') as string;
            const genOptions = this.getNodeParameter('generationOptions', i) as IDataObject;
            
            // Ensure model exists
            await manager.ensureModel(chatModel);
            
            // Build messages array
            let messages: any[] = [];
            try {
              messages = JSON.parse(conversationHistory);
            } catch {
              messages = [];
            }
            
            if (systemPrompt) {
              messages.unshift({ role: 'system', content: systemPrompt });
            }
            
            messages.push({ role: 'user', content: message });
            
            const chatResponse = await manager.chat({
              model: chatModel,
              messages,
              options: buildOllamaOptions(this, genOptions, i),
            });
            
            result = processResponse(chatResponse, genOptions.includeReasoning as boolean);
            break;

          case 'completion':
            const completionModel = getModelName(this, i);
            const prompt = this.getNodeParameter('prompt', i) as string;
            const completionOptions = this.getNodeParameter('generationOptions', i) as IDataObject;
            
            await manager.ensureModel(completionModel);
            
            const completionResponse = await manager.generate({
              model: completionModel,
              prompt,
              options: buildOllamaOptions(this, completionOptions, i),
            });
            
            result = processResponse(completionResponse, completionOptions.includeReasoning as boolean);
            break;

          case 'code':
            const codeModel = getModelName(this, i);
            const codeTask = this.getNodeParameter('codeTask', i) as string;
            const codeInput = this.getNodeParameter('codeInput', i) as string;
            const language = this.getNodeParameter('programmingLanguage', i) as string;
            const codeSystemPrompt = this.getNodeParameter('systemPrompt', i, '') as string;
            const codeOptions = this.getNodeParameter('generationOptions', i) as IDataObject;
            
            await manager.ensureModel(codeModel);
            
            // Build code-specific prompt
            let codePrompt = '';
            switch (codeTask) {
              case 'generate':
                codePrompt = `Generate ${language} code for the following requirements:\n\n${codeInput}`;
                break;
              case 'explain':
                codePrompt = `Explain the following ${language} code:\n\n${codeInput}`;
                break;
              case 'review':
                codePrompt = `Review the following ${language} code and suggest improvements:\n\n${codeInput}`;
                break;
              case 'fix':
                codePrompt = `Fix any errors in the following ${language} code:\n\n${codeInput}`;
                break;
              case 'convert':
                codePrompt = `Convert the following code to ${language}:\n\n${codeInput}`;
                break;
            }
            
            const codeMessages = [];
            if (codeSystemPrompt) {
              codeMessages.push({ role: 'system', content: codeSystemPrompt });
            } else {
              codeMessages.push({ 
                role: 'system', 
                content: `You are an expert ${language} programmer. Provide clean, well-commented code.` 
              });
            }
            codeMessages.push({ role: 'user', content: codePrompt });
            
            const codeResponse = await manager.chat({
              model: codeModel,
              messages: codeMessages,
              options: buildOllamaOptions(this, codeOptions, i),
            });
            
            result = {
              ...processResponse(codeResponse, codeOptions.includeReasoning as boolean),
              task: codeTask,
              language,
            };
            break;

          case 'embeddings':
            const embeddingModel = getModelName(this, i);
            const embeddingText = this.getNodeParameter('embeddingText', i) as string;
            
            await manager.ensureModel(embeddingModel);
            
            const embeddingResponse = await manager.embeddings({
              model: embeddingModel,
              prompt: embeddingText,
            });
            
            result = {
              embeddings: embeddingResponse.embedding,
              model: embeddingModel,
            };
            break;

          case 'vision':
            const visionModel = getModelName(this, i);
            const imageSource = this.getNodeParameter('imageSource', i) as string;
            const visionPrompt = this.getNodeParameter('visionPrompt', i) as string;
            const visionOptions = this.getNodeParameter('generationOptions', i) as IDataObject;
            
            await manager.ensureModel(visionModel);
            
            let images: string[] = [];
            if (imageSource === 'url') {
              const imageUrl = this.getNodeParameter('imageUrl', i) as string;
              images = [imageUrl];
            } else {
              const imageData = this.getNodeParameter('imageData', i) as string;
              images = [imageData];
            }
            
            const visionMessages = [
              {
                role: 'user',
                content: visionPrompt,
                images,
              },
            ];
            
            const visionResponse = await manager.chat({
              model: visionModel,
              messages: visionMessages,
              options: buildOllamaOptions(this, visionOptions, i),
            });
            
            result = processResponse(visionResponse, visionOptions.includeReasoning as boolean);
            break;

          case 'recursive_summary':
            result = await executeRecursiveSummary(this, i, manager);
            break;

          default:
            throw new NodeOperationError(
              this.getNode(),
              `Unknown operation: ${operation}`,
            );
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

  // AI Agent integration
  async supplyData(this: ISupplyDataFunctions): Promise<any> {
    const connectionMode = this.getNodeParameter('connectionMode', 0) as string;
    const baseUrl = getConnectionUrl(this, connectionMode, 0);
    const manager = new OllamaConnectionManager(baseUrl);
    const model = getModelName(this, 0);
    const aiModelMaxTokens = this.getNodeParameter('aiModelMaxTokens', 0) as number;
    
    // Ensure model exists
    await manager.ensureModel(model);
    
    return {
      response: {
        invoke: async (params: {
          messages: Array<{role: string, content: string}>,
          options?: {
            temperature?: number,
            maxTokensToSample?: number,
            [key: string]: any
          }
        }) => {
          const { messages, options = {} } = params;
          
          const generationOptions = this.getNodeParameter('generationOptions', 0) as IDataObject;
          const performanceOptions = this.getNodeParameter('performanceOptions', 0) as IDataObject;
          
          // Build Ollama options
          const ollamaOptions: any = {
            temperature: options.temperature ?? generationOptions.temperature ?? 0.7,
            num_predict: options.maxTokensToSample ?? aiModelMaxTokens ?? generationOptions.maxTokens ?? 256,
            top_p: options.topP ?? generationOptions.topP ?? 0.9,
            top_k: options.topK ?? generationOptions.topK ?? 40,
            stream: false,
          };
          
          // Add performance options
          if (performanceOptions.numCtx) ollamaOptions.num_ctx = performanceOptions.numCtx;
          if (performanceOptions.numGpu !== undefined) ollamaOptions.num_gpu = performanceOptions.numGpu;
          
          // Make API call
          const response = await manager.chat({
            model,
            messages,
            options: ollamaOptions,
          });
          
          // Process response
          let content = response.message?.content || response.response || '';
          let reasoning = '';
          
          // Extract thinking/reasoning if present
          const thinkMatch = content.match(/<think>([\s\S]*?)<\/think>/);
          if (thinkMatch) {
            reasoning = thinkMatch[1].trim();
            content = content.replace(/<think>[\s\S]*?<\/think>/, '').trim();
          }
          
          // Return in expected format
          return {
            text: content,
            content: content,
            usage: {
              prompt_tokens: response.prompt_eval_count,
              completion_tokens: response.eval_count,
              total_tokens: (response.prompt_eval_count || 0) + (response.eval_count || 0),
            },
            reasoning: reasoning || undefined,
          };
        },
      },
    };
  }
}

async function executeRecursiveSummary(
  context: IExecuteFunctions,
  itemIndex: number,
  manager: OllamaConnectionManager
): Promise<IDataObject> {
  const summaryManager = new RecursiveSummaryManager();
  const items = context.getInputData();
  
  // Get text to summarize
  const textSource = context.getNodeParameter('textSource', itemIndex) as string;
  let text: string;
  
  if (textSource === 'field') {
    const fieldName = context.getNodeParameter('textField', itemIndex) as string;
    text = items[itemIndex].json[fieldName] as string;
    
    if (!text) {
      throw new NodeOperationError(
        context.getNode(),
        `Field "${fieldName}" not found or empty in input data`,
      );
    }
  } else {
    text = context.getNodeParameter('summaryText', itemIndex) as string;
  }

  // Get configuration
  const model = getModelName(context, itemIndex);
  const summaryOptions = context.getNodeParameter('summaryOptions', itemIndex) as IDataObject;
  const generationOptions = context.getNodeParameter('generationOptions', itemIndex) as IDataObject;
  
  await manager.ensureModel(model);

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

    for (const chunk of chunks) {
      const prompt = summaryManagerWithConfig.generateSummaryPrompt(
        chunk, 
        currentLevel,
        { 
          topic: summaryOptions.topic,
          style: summaryOptions.style 
        }
      );

      const response = await manager.generate({
        model,
        prompt,
        options: buildOllamaOptions(context, generationOptions, itemIndex),
      });

      summaries.push(response.response);
    }

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

    currentText = summaryManagerWithConfig.mergeSummaries(summaries);
    currentLevel++;

    // Final summary if text is now small enough
    if (currentText.length < config.maxChunkSize) {
      const finalPrompt = summaryManagerWithConfig.generateSummaryPrompt(
        currentText,
        currentLevel,
        { 
          topic: summaryOptions.topic,
          style: summaryOptions.style 
        }
      );

      const finalResponse = await manager.generate({
        model,
        prompt: finalPrompt,
        options: buildOllamaOptions(context, generationOptions, itemIndex),
      });
      
      levels.push({
        level: currentLevel,
        chunks: [currentText],
        summaries: [finalResponse.response],
        metadata: {
          chunkCount: 1,
          totalLength: currentText.length,
          summaryLength: finalResponse.response.length,
        },
      });
      
      break;
    }
  }

  return summaryManagerWithConfig.formatHierarchicalSummary(levels);
}