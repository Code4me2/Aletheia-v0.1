import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  IDataObject,
  NodeOperationError,
  NodeConnectionType,
} from 'n8n-workflow';

export class HaystackSearch implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Haystack Search',
    name: 'haystackSearch',
    icon: 'file:haystack.svg',
    group: ['transform'],
    version: 1,
    subtitle: '={{$parameter.operation}}',
    description: 'RAG (Retrieval-Augmented Generation) with Elasticsearch for document search',
    defaults: {
      name: 'Haystack Search',
    },
    inputs: [{ type: NodeConnectionType.Main }],
    outputs: [{ type: NodeConnectionType.Main }],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        noDataExpression: true,
        options: [
          {
            name: 'Search',
            value: 'search',
            description: 'Search documents using keyword, semantic, or hybrid methods',
            action: 'Search indexed documents',
          },
          {
            name: 'Ingest Documents',
            value: 'ingest',
            description: 'Ingest documents into Elasticsearch for RAG',
            action: 'Ingest documents',
          },
          {
            name: 'Health Check',
            value: 'health',
            description: 'Verify Elasticsearch and API service connectivity',
            action: 'Check system status',
          },
        ],
        default: 'search',
      },
      // Ingest operation parameters
      {
        displayName: 'Content Field',
        name: 'contentField',
        type: 'string',
        default: 'content',
        displayOptions: {
          show: {
            operation: ['ingest'],
          },
        },
        description: 'Field name containing the document content',
      },
      {
        displayName: 'Metadata Fields',
        name: 'metadataFields',
        type: 'string',
        default: 'title,source,author',
        displayOptions: {
          show: {
            operation: ['ingest'],
          },
        },
        description: 'Comma-separated list of metadata field names to include',
      },
      // Search operation parameters
      {
        displayName: 'Query',
        name: 'query',
        type: 'string',
        default: '',
        required: true,
        displayOptions: {
          show: {
            operation: ['search'],
          },
        },
        description: 'Search query text',
        placeholder: 'constitutional rights due process',
      },
      {
        displayName: 'Search Type',
        name: 'searchType',
        type: 'options',
        options: [
          {
            name: 'Hybrid',
            value: 'hybrid',
            description: 'Combine keyword and semantic search',
          },
          {
            name: 'Vector',
            value: 'vector',
            description: 'Semantic search using embeddings',
          },
          {
            name: 'BM25',
            value: 'bm25',
            description: 'Keyword-based search',
          },
        ],
        default: 'hybrid',
        displayOptions: {
          show: {
            operation: ['search'],
          },
        },
        description: 'Type of search to perform',
      },
      {
        displayName: 'Top K Results',
        name: 'topK',
        type: 'number',
        default: 10,
        displayOptions: {
          show: {
            operation: ['search'],
          },
        },
        description: 'Number of top results to return',
      },
      {
        displayName: 'Filters',
        name: 'filters',
        type: 'json',
        default: '{}',
        displayOptions: {
          show: {
            operation: ['search'],
          },
        },
        description: 'Additional filters to apply to search',
        placeholder: '{"document_type": "summary", "hierarchy_level": 2}',
      },
      // Common parameters
      {
        displayName: 'Haystack Service URL',
        name: 'haystackUrl',
        type: 'string',
        default: 'http://haystack-service:8000',
        description: 'URL of the Haystack service',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;
    const haystackUrl = this.getNodeParameter('haystackUrl', 0) as string;

    for (let i = 0; i < items.length; i++) {
      try {
        let response: any;
        let endpoint: string;
        let method: string = 'POST';
        let body: any = {};

        switch (operation) {
          case 'ingest':
            endpoint = '/ingest';
            const contentField = this.getNodeParameter('contentField', i) as string;
            const metadataFields = this.getNodeParameter('metadataFields', i) as string;
            
            const inputData = items[i].json;
            const document: any = {
              content: inputData[contentField] || '',
              metadata: {},
            };
            
            // Add metadata fields
            if (metadataFields) {
              const fields = metadataFields.split(',').map(f => f.trim());
              fields.forEach(field => {
                if (inputData[field] !== undefined) {
                  document.metadata[field] = inputData[field];
                }
              });
            }
            
            // Add timestamp
            document.metadata.ingested_at = new Date().toISOString();
            
            body = [document]; // The ingest endpoint expects an array
            break;

          case 'search':
            endpoint = '/search';
            body = {
              query: this.getNodeParameter('query', i) as string,
              top_k: this.getNodeParameter('topK', i) as number,
            };
            
            const searchType = this.getNodeParameter('searchType', i) as string;
            if (searchType === 'hybrid') {
              body.use_hybrid = true;
            } else if (searchType === 'vector') {
              body.use_vector = true;
            } else if (searchType === 'bm25') {
              body.use_bm25 = true;
            }

            const filtersParam = this.getNodeParameter('filters', i);
            if (filtersParam) {
              try {
                if (typeof filtersParam === 'string' && filtersParam !== '{}') {
                  body.filters = JSON.parse(filtersParam);
                } else if (typeof filtersParam === 'object') {
                  body.filters = filtersParam;
                }
              } catch (error) {
                throw new NodeOperationError(this.getNode(), 'Invalid JSON in filters parameter');
              }
            }
            break;

          case 'health':
            endpoint = '/health';
            method = 'GET';
            body = null;
            break;

          default:
            throw new NodeOperationError(this.getNode(), `Unknown operation: ${operation}`);
        }

        const url = `${haystackUrl}${endpoint}`;
        
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
              `Failed to connect to Haystack service at ${url}: ${error.message}`,
            );
          }
          throw error;
        }

        if (operation === 'search' && response.results) {
          for (const result of response.results) {
            returnData.push({
              json: {
                ...result,
                _search_metadata: {
                  total_results: response.total_results,
                  search_type: response.search_type,
                  query: body.query,
                },
              },
            });
          }
        } else {
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
}