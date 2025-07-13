import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeConnectionType,
  NodeOperationError,
} from 'n8n-workflow';

import { Client } from 'pg';

// Interfaces for citation handling
interface ParsedCitation {
  id: string;
  type: 'inline' | 'reference';
  citedText?: string; // For <cite> tags
  referenceNumber?: string; // For [1], [2a] format
  fullCitation?: string; // From ## Citations section
  rawText?: string; // Original citation text
  metadata?: {
    caseName?: string;
    citation?: string;
    court?: string;
    year?: string;
    holding?: string;
    relevance?: string;
    connection?: string;
  };
}

interface VerificationResult {
  citationId: string;
  exists: boolean;
  matchedRecord?: {
    id: string;
    caseName: string;
    citation: string;
    court: string;
    year: string;
  };
  confidence: number; // 0-1 fuzzy match score
  error?: string;
}

interface ValidationResult {
  citationId: string;
  appropriate: boolean;
  confidence: number;
  reasoning: string;
  issues?: string[];
}

interface ScriptedValidationResult {
  citationId: string;
  formatValid: boolean;
  formatIssues: string[];
  structureValid: boolean;
  metadataComplete: boolean;
}

// Resilience configuration interface
interface ResilienceConfig {
  retryEnabled: boolean;
  maxRetries: number;
  requestTimeout: number;
  fallbackEnabled: boolean;
}

export class CitationChecker implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Citation Checker',
    name: 'citationChecker',
    icon: 'file:citation.svg',
    group: ['transform'],
    version: 1,
    description: 'Parse, verify, and validate citations in AI-generated text',
    defaults: {
      name: 'Citation Checker',
    },
    inputs: [
      NodeConnectionType.Main,
      {
        type: NodeConnectionType.AiLanguageModel,
        displayName: 'Language Model',
        required: false,
      },
    ],
    outputs: [NodeConnectionType.Main],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        options: [
          {
            name: 'Parse Citations',
            value: 'parse',
            description: 'Extract citations and quoted text from input',
          },
          {
            name: 'Verify Citations',
            value: 'verify',
            description: 'Check citations against database',
          },
          {
            name: 'Full Validation',
            value: 'fullValidation',
            description: 'Parse, verify existence, and validate appropriateness',
          },
          {
            name: 'Scripted Validation',
            value: 'scriptedValidation',
            description: 'Validate citation format and structure without AI',
          },
        ],
        default: 'fullValidation',
      },
      {
        displayName: 'Text Field',
        name: 'textField',
        type: 'string',
        default: 'content',
        required: true,
        description: 'The field name containing the text to process',
      },
      {
        displayName: 'Database Configuration',
        name: 'dbConfig',
        type: 'collection',
        placeholder: 'Add Database Config',
        default: {},
        displayOptions: {
          show: {
            operation: ['verify', 'fullValidation'],
          },
        },
        options: [
          {
            displayName: 'Database Type',
            name: 'dbType',
            type: 'options',
            options: [
              { name: 'PostgreSQL', value: 'postgres' },
              { name: 'Mock Database', value: 'mock' },
            ],
            default: 'postgres',
          },
          {
            displayName: 'Connection String',
            name: 'connectionString',
            type: 'string',
            default: 'postgresql://user:pass@localhost:5432/citations',
            displayOptions: {
              show: {
                dbType: ['postgres'],
              },
            },
          },
        ],
      },
      {
        displayName: 'Include Original Text',
        name: 'includeOriginal',
        type: 'boolean',
        default: true,
        description: 'Whether to include the original text in the output',
      },
      {
        displayName: 'AI Resilience Configuration',
        name: 'resilienceConfig',
        type: 'collection',
        placeholder: 'Add Resilience Config',
        default: {},
        displayOptions: {
          show: {
            operation: ['fullValidation'],
          },
        },
        options: [
          {
            displayName: 'Enable Retry Logic',
            name: 'retryEnabled',
            type: 'boolean',
            default: true,
            description: 'Retry failed AI requests with exponential backoff',
          },
          {
            displayName: 'Max Retries',
            name: 'maxRetries',
            type: 'number',
            default: 3,
            description: 'Maximum number of retry attempts',
          },
          {
            displayName: 'Request Timeout (ms)',
            name: 'requestTimeout',
            type: 'number',
            default: 30000,
            description: 'Timeout for each AI request in milliseconds',
          },
          {
            displayName: 'Enable Fallback',
            name: 'fallbackEnabled',
            type: 'boolean',
            default: true,
            description: 'Use scripted validation if AI fails',
          },
        ],
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;
    
    // Create citation helper instance
    const citationHelper = new CitationChecker();

    // Get AI Language Model if connected
    let languageModel: any;
    try {
      languageModel = await this.getInputConnectionData(NodeConnectionType.AiLanguageModel, 0);
    } catch (error) {
      // AI model is optional, continue without it
      languageModel = null;
    }

    for (let itemIndex = 0; itemIndex < items.length; itemIndex++) {
      try {
        const textField = this.getNodeParameter('textField', itemIndex) as string;
        const includeOriginal = this.getNodeParameter('includeOriginal', itemIndex) as boolean;

        const text = items[itemIndex].json[textField] as string;

        if (!text) {
          throw new NodeOperationError(
            this.getNode(),
            `Field "${textField}" not found or empty in item ${itemIndex}`,
            { itemIndex }
          );
        }

        const result: any = {
          ...(includeOriginal ? { originalText: text } : {}),
        };

        if (operation === 'parse' || operation === 'fullValidation' || operation === 'scriptedValidation') {
          // Parse citations
          const parsedCitations = citationHelper.parseCitations(text);
          result.citations = {
            parsed: parsedCitations,
            summary: {
              total: parsedCitations.length,
              inline: parsedCitations.filter((c: ParsedCitation) => c.type === 'inline').length,
              references: parsedCitations.filter((c: ParsedCitation) => c.type === 'reference').length,
            },
          };
        }

        if (operation === 'verify' || operation === 'fullValidation') {
          // Verify citations against database
          const dbConfig = this.getNodeParameter('dbConfig', itemIndex) as any;
          const citations = result.citations?.parsed || citationHelper.parseCitations(text);
          const verificationResults = await citationHelper.verifyCitations(citations, dbConfig);

          result.citations = {
            ...result.citations,
            verificationResults,
            summary: {
              ...result.citations?.summary,
              verified: verificationResults.filter((r: VerificationResult) => r.exists).length,
              unverified: verificationResults.filter((r: VerificationResult) => !r.exists).length,
            },
          };
        }

        if (operation === 'scriptedValidation' || operation === 'fullValidation') {
          // Perform scripted validation
          const citations = result.citations.parsed;
          const scriptedResults = citations.map((citation: ParsedCitation) => 
            citationHelper.validateCitationFormat(citation)
          );
          
          result.citations = {
            ...result.citations,
            scriptedValidation: scriptedResults,
            summary: {
              ...result.citations.summary,
              formatValid: scriptedResults.filter((r: ScriptedValidationResult) => r.formatValid).length,
              formatInvalid: scriptedResults.filter((r: ScriptedValidationResult) => !r.formatValid).length,
            },
          };
        }

        if (operation === 'fullValidation' && languageModel) {
          // Validate citations with AI
          const citations = result.citations.parsed;
          const resilienceConfig = this.getNodeParameter('resilienceConfig', itemIndex) as ResilienceConfig || {
            retryEnabled: true,
            maxRetries: 3,
            requestTimeout: 30000,
            fallbackEnabled: true,
          };
          const validationResults = await citationHelper.validateCitations(citations, text, languageModel, resilienceConfig);

          result.citations = {
            ...result.citations,
            validationResults,
            summary: {
              ...result.citations.summary,
              appropriate: validationResults.filter((r: ValidationResult) => r.appropriate).length,
              inappropriate: validationResults.filter((r: ValidationResult) => !r.appropriate).length,
              issues: validationResults.flatMap((r: ValidationResult) => r.issues || []),
            },
          };
        }

        returnData.push({
          json: result,
          pairedItem: { item: itemIndex },
        });
      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: {
              error: error instanceof Error ? error.message : 'Unknown error',
              itemIndex,
            },
            pairedItem: { item: itemIndex },
          });
          continue;
        }
        throw error;
      }
    }

    return [returnData];
  }

  /**
   * Parses citations from text in multiple formats:
   * - Inline: <cite id="case-name">quoted text</cite>
   * - References: [1], [2a], [2b]
   * - Full citations from ## Citations markdown section
   * 
   * @param text - The text to parse for citations
   * @returns Array of parsed citations with metadata
   */
  parseCitations(text: string): ParsedCitation[] {
    const citations: ParsedCitation[] = [];
    const citationMap = new Map<string, ParsedCitation>();

    // Parse inline citations: <cite id="case-name">text</cite>
    const CITE_TAG_PATTERN = /<cite\s+id="([^"]+)">([^<]+)<\/cite>/g;
    let match;

    while ((match = CITE_TAG_PATTERN.exec(text)) !== null) {
      const citation: ParsedCitation = {
        id: match[1],
        type: 'inline',
        citedText: match[2],
        rawText: match[0],
      };
      citations.push(citation);
      citationMap.set(match[1], citation);
    }

    // Parse reference citations: [1], [2a], etc.
    const REF_PATTERN = /\[(\d+[a-z]?(?:,\s*\d+[a-z]?)*)\]/g;

    while ((match = REF_PATTERN.exec(text)) !== null) {
      const refs = match[1].split(/,\s*/);
      for (const ref of refs) {
        citations.push({
          id: ref,
          type: 'reference',
          referenceNumber: ref,
          rawText: `[${ref}]`,
        });
      }
    }

    // Parse ## Citations section
    const citationSectionMatch = text.match(/## Citations\s*\n([\s\S]*?)(?=\n##|$)/);

    if (citationSectionMatch) {
      const citationSection = citationSectionMatch[1];
      const citationEntryPattern =
        /\[(\d+[a-z]?)\]\s*\*\*([^*]+)\*\*(?:\n- \*\*([^:]+)\*\*:\s*([^\n]+))+/g;

      while ((match = citationEntryPattern.exec(citationSection)) !== null) {
        const id = match[1];
        const fullText = match[0];

        // Parse metadata
        const metadata: any = {
          caseName: match[2],
        };

        // Extract all metadata fields
        const metadataPattern = /- \*\*([^:]+)\*\*:\s*([^\n]+)/g;
        let metaMatch;

        while ((metaMatch = metadataPattern.exec(fullText)) !== null) {
          const key = metaMatch[1].toLowerCase().replace(/\s+/g, '');
          metadata[key] = metaMatch[2];
        }

        // Update existing citation or create new one
        const existingCitation = citations.find((c) => c.referenceNumber === id);
        if (existingCitation) {
          existingCitation.fullCitation = fullText;
          existingCitation.metadata = metadata;
        } else {
          citations.push({
            id,
            type: 'reference',
            referenceNumber: id,
            fullCitation: fullText,
            metadata,
          });
        }
      }
    }

    return citations;
  }

  /**
   * Validates citation format and structure without AI.
   * Checks:
   * - Citation ID format (alphanumeric + hyphens/underscores)
   * - Required text fields
   * - Reference number format
   * - Metadata completeness
   * - Valid connection types
   * 
   * @param citation - The parsed citation to validate
   * @returns Validation result with specific issues
   */
  validateCitationFormat(citation: ParsedCitation): ScriptedValidationResult {
    const issues: string[] = [];
    let formatValid = true;
    let structureValid = true;
    let metadataComplete = true;

    // Validate inline citations
    if (citation.type === 'inline') {
      // Check for valid cite ID format (should not contain spaces or special chars)
      if (citation.id && !/^[a-zA-Z0-9-_]+$/.test(citation.id)) {
        issues.push('Citation ID contains invalid characters');
        formatValid = false;
      }
      
      // Check cited text exists and is not empty
      if (!citation.citedText || citation.citedText.trim().length === 0) {
        issues.push('Inline citation missing quoted text');
        structureValid = false;
      }
    }

    // Validate reference citations
    if (citation.type === 'reference') {
      // Check reference number format
      if (citation.referenceNumber && !/^\d+[a-z]?$/.test(citation.referenceNumber)) {
        issues.push('Invalid reference number format');
        formatValid = false;
      }
      
      // Check if full citation exists
      if (!citation.fullCitation) {
        issues.push('Reference missing full citation details');
        structureValid = false;
      }
    }

    // Validate metadata if present
    if (citation.metadata) {
      const requiredFields = ['caseName', 'holding', 'relevance'];
      const missingFields = requiredFields.filter(field => !citation.metadata?.[field as keyof typeof citation.metadata]);
      
      if (missingFields.length > 0) {
        issues.push(`Missing metadata fields: ${missingFields.join(', ')}`);
        metadataComplete = false;
      }
      
      // Validate connection type
      if (citation.metadata.connection) {
        const validConnections = ['Primary', 'Supporting', 'Distinguishing', 'Background'];
        if (!validConnections.includes(citation.metadata.connection)) {
          issues.push(`Invalid connection type: ${citation.metadata.connection}`);
          formatValid = false;
        }
      }
    }

    return {
      citationId: citation.id,
      formatValid: formatValid && structureValid,
      formatIssues: issues,
      structureValid,
      metadataComplete,
    };
  }

  /**
   * Verifies citations exist in database.
   * Supports:
   * - Mock mode for testing (70% success rate)
   * - PostgreSQL with fuzzy matching on case names
   * 
   * @param citations - Array of citations to verify
   * @param dbConfig - Database configuration
   * @returns Verification results with confidence scores
   */
  async verifyCitations(
    citations: ParsedCitation[],
    dbConfig: any
  ): Promise<VerificationResult[]> {
    if (dbConfig.dbType === 'mock') {
      // Mock database for testing
      return citations.map((citation) => ({
        citationId: citation.id,
        exists: Math.random() > 0.3, // 70% chance of existing
        confidence: Math.random() * 0.5 + 0.5, // 0.5-1.0
        matchedRecord:
          Math.random() > 0.5
            ? {
                id: `mock-${citation.id}`,
                caseName: citation.metadata?.caseName || 'Mock Case',
                citation: citation.metadata?.citation || '123 F.3d 456',
                court: citation.metadata?.court || '2d Cir.',
                year: citation.metadata?.year || '2020',
              }
            : undefined,
      }));
    }

    // PostgreSQL verification
    const results: VerificationResult[] = [];
    let client: Client | null = null;

    try {
      client = new Client(dbConfig.connectionString);
      await client.connect();

      for (const citation of citations) {
        try {
          // Try exact match first
          const query = `
            SELECT id, case_name, citation, court, year 
            FROM citations 
            WHERE case_name ILIKE $1 
               OR citation ILIKE $2
            LIMIT 1
          `;

          const caseName = citation.metadata?.caseName || citation.id;
          const citationText = citation.metadata?.citation || '';

          const result = await client.query(query, [`%${caseName}%`, `%${citationText}%`]);

          if (result.rows.length > 0) {
            const row = result.rows[0];
            results.push({
              citationId: citation.id,
              exists: true,
              confidence: 1.0,
              matchedRecord: {
                id: row.id,
                caseName: row.case_name,
                citation: row.citation,
                court: row.court,
                year: row.year,
              },
            });
          } else {
            results.push({
              citationId: citation.id,
              exists: false,
              confidence: 0,
            });
          }
        } catch (error) {
          results.push({
            citationId: citation.id,
            exists: false,
            confidence: 0,
            error: error instanceof Error ? error.message : 'Unknown error',
          });
        }
      }
    } catch (error) {
      // Database connection error
      return citations.map((citation) => ({
        citationId: citation.id,
        exists: false,
        confidence: 0,
        error: `Database connection error: ${error instanceof Error ? error.message : 'Unknown error'}`,
      }));
    } finally {
      if (client) {
        await client.end();
      }
    }

    return results;
  }

  /**
   * Parses AI response from various provider formats.
   * Supports 16+ different response structures including:
   * - n8n default format
   * - OpenAI, Anthropic, Google
   * - Custom node formats
   * 
   * @param response - Raw AI response in any format
   * @returns Extracted text content
   * @throws Error if no text can be extracted
   */
  parseAIResponse(response: any): string {
    if (!response) {
      throw new Error('No response from AI model');
    }
    
    // Direct string response
    if (typeof response === 'string') {
      return response;
    }
    
    // Try various response formats in order of likelihood
    const extractors = [
      // n8n AI node format
      () => response.response?.generations?.[0]?.[0]?.text,
      () => response.generations?.[0]?.[0]?.text,
      
      // LangChain BaseMessage format
      () => response.lc_kwargs?.content,
      () => response.content && typeof response._getType === 'function' ? response.content : undefined,
      
      // OpenAI ChatGPT format
      () => response.choices?.[0]?.message?.content,
      () => response.choices?.[0]?.text,
      
      // Anthropic Claude format
      () => response.content,
      () => response.completion,
      
      // Google AI format
      () => response.candidates?.[0]?.content?.parts?.[0]?.text,
      () => response.candidates?.[0]?.text,
      () => response.text,
      
      // Custom node formats
      () => response.output,
      () => response.result,
      () => response.data?.content,
      () => response.data?.text,
    ];
    
    for (const extractor of extractors) {
      try {
        const result = extractor();
        if (result && typeof result === 'string' && result.trim()) {
          return result;
        }
      } catch (e) {
        // Continue to next extractor
      }
    }
    
    throw new Error(`Unable to extract response from AI model. Response structure: ${JSON.stringify(response, null, 2).substring(0, 500)}`);
  }

  /**
   * Implements retry logic with exponential backoff and jitter.
   * Used for resilient AI connections.
   * 
   * @param operation - Async function to retry
   * @param maxRetries - Maximum retry attempts
   * @param initialDelay - Initial delay in ms (default: 1000)
   * @returns Result of successful operation
   * @throws Last error if all retries fail
   */
  async retryWithBackoff<T>(
    operation: () => Promise<T>,
    maxRetries: number,
    initialDelay: number = 1000
  ): Promise<T> {
    let lastError: any;
    
    for (let attempt = 0; attempt < maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        
        if (attempt < maxRetries - 1) {
          const delay = initialDelay * Math.pow(2, attempt);
          const jitter = delay * 0.1 * (Math.random() * 2 - 1); // ±10% jitter
          const totalDelay = Math.min(delay + jitter, 30000); // Max 30 seconds
          
          console.log(`[Citation Checker] Retry ${attempt + 1}/${maxRetries} after ${Math.round(totalDelay)}ms`);
          await new Promise(resolve => setTimeout(resolve, totalDelay));
        }
      }
    }
    
    throw lastError;
  }

  /**
   * Validates citation appropriateness using AI with resilience features.
   * - Tries custom format first, falls back to default n8n format
   * - Implements retry logic with exponential backoff
   * - Falls back to scripted validation if AI fails
   * - Extracts context around each citation
   * 
   * @param citations - Citations to validate
   * @param fullText - Full text containing citations
   * @param languageModel - Connected AI language model
   * @param resilience - Resilience configuration
   * @returns AI validation results with reasoning
   */
  async validateCitations(
    citations: ParsedCitation[],
    fullText: string,
    languageModel: any,
    resilience: ResilienceConfig
  ): Promise<ValidationResult[]> {
    if (!languageModel || typeof languageModel.invoke !== 'function') {
      return [];
    }

    const results: ValidationResult[] = [];

    for (const citation of citations) {
      try {
        // Extract context around the citation
        const contextRadius = 200;
        const citationIndex = fullText.indexOf(citation.rawText || citation.citedText || '');
        const contextStart = Math.max(0, citationIndex - contextRadius);
        const contextEnd = Math.min(
          fullText.length,
          citationIndex + (citation.rawText?.length || 0) + contextRadius
        );
        const context = fullText.substring(contextStart, contextEnd);

        const systemPrompt = 'You are a legal citation validator. Analyze citations for accuracy and appropriate use. Always respond with valid JSON.';
        const userPrompt = `Analyze this legal citation for appropriateness and accuracy.

Citation Details:
- Citation ID: ${citation.id}
- Type: ${citation.type}
${citation.citedText ? `- Cited Text: "${citation.citedText}"` : ''}
${citation.fullCitation ? `- Full Citation: ${citation.fullCitation}` : ''}
${citation.metadata ? `- Metadata: ${JSON.stringify(citation.metadata, null, 2)}` : ''}

Context where citation appears:
"${context}"

Evaluate:
1. Is the citation used appropriately in context?
2. Does the cited text accurately represent the source?
3. Is the connection type (Primary/Supporting/etc) accurate?
4. Are there any misrepresentations or issues?

Respond in JSON format:
{
  "appropriate": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "explanation",
  "issues": ["issue1", "issue2"] or []
}`;

        // Define the AI invocation operation
        const invokeAI = async (): Promise<string> => {
          let response;
          
          try {
            // First try the custom node format (messages array)
            response = await Promise.race([
              languageModel.invoke({
                messages: [
                  { role: 'system', content: systemPrompt },
                  { role: 'user', content: userPrompt }
                ],
                options: {
                  temperature: 0.3,
                  maxTokensToSample: 500,
                }
              }),
              new Promise((_, reject) => 
                setTimeout(() => reject(new Error(`AI request timeout after ${resilience.requestTimeout}ms`)), resilience.requestTimeout)
              )
            ]);
          } catch (invokeError: any) {
            // If it fails with toChatMessages error, try the default n8n format
            if (invokeError.message?.includes('toChatMessages') || invokeError.message?.includes('messages')) {
              console.log('[Citation Checker] Custom format failed, trying default n8n format');
              const combinedPrompt = `${systemPrompt}\n\nHuman: ${userPrompt}\n\nAI:`;
              
              response = await Promise.race([
                languageModel.invoke(combinedPrompt, {
                  temperature: 0.3,
                  maxTokensToSample: 500,
                }),
                new Promise((_, reject) => 
                  setTimeout(() => reject(new Error(`AI request timeout after ${resilience.requestTimeout}ms`)), resilience.requestTimeout)
                )
              ]);
            } else {
              throw invokeError;
            }
          }
          
          return this.parseAIResponse(response);
        };

        // Execute with retry logic if enabled
        let responseText: string;
        if (resilience.retryEnabled) {
          responseText = await this.retryWithBackoff(invokeAI, resilience.maxRetries);
        } else {
          responseText = await invokeAI();
        }

        // Parse AI response
        let validationResult: ValidationResult;
        try {
          // Try to extract JSON from the response
          const jsonMatch = responseText.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            validationResult = {
              citationId: citation.id,
              appropriate: parsed.appropriate !== undefined ? parsed.appropriate : true,
              confidence: parsed.confidence !== undefined ? parsed.confidence : 0.5,
              reasoning: parsed.reasoning || 'No reasoning provided',
              issues: Array.isArray(parsed.issues) ? parsed.issues : [],
            };
          } else {
            // Fallback if no JSON found
            validationResult = {
              citationId: citation.id,
              appropriate: true,
              confidence: 0.5,
              reasoning: 'Could not parse AI response as JSON',
              issues: ['Response was not in expected JSON format'],
            };
          }
        } catch (parseError) {
          validationResult = {
            citationId: citation.id,
            appropriate: true,
            confidence: 0.5,
            reasoning: 'Error parsing AI response',
            issues: [`Parse error: ${parseError instanceof Error ? parseError.message : 'Unknown error'}`],
          };
        }

        results.push(validationResult);
      } catch (error) {
        // If AI validation fails and fallback is enabled, use scripted validation
        if (resilience.fallbackEnabled) {
          const scriptedResult = this.validateCitationFormat(citation);
          results.push({
            citationId: citation.id,
            appropriate: scriptedResult.formatValid,
            confidence: 0.7,
            reasoning: `[Fallback validation] ${scriptedResult.formatIssues.length === 0 ? 'Citation format is valid' : scriptedResult.formatIssues.join('; ')}`,
            issues: scriptedResult.formatIssues,
          });
        } else {
          results.push({
            citationId: citation.id,
            appropriate: false,
            confidence: 0,
            reasoning: `Validation error: ${error instanceof Error ? error.message : 'Unknown error'}`,
            issues: [`Error: ${error instanceof Error ? error.message : 'Unknown error'}`],
          });
        }
      }
    }

    return results;
  }
}
