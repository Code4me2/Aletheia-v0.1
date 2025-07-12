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
        description: 'AI model for citation appropriateness verification',
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
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const operation = this.getNodeParameter('operation', 0) as string;

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

        if (operation === 'parse' || operation === 'fullValidation') {
          // Parse citations
          const parsedCitations = this.parseCitations(text);
          result.citations = {
            parsed: parsedCitations,
            summary: {
              total: parsedCitations.length,
              inline: parsedCitations.filter((c) => c.type === 'inline').length,
              references: parsedCitations.filter((c) => c.type === 'reference').length,
            },
          };
        }

        if (operation === 'verify' || operation === 'fullValidation') {
          // Verify citations against database
          const dbConfig = this.getNodeParameter('dbConfig', itemIndex) as any;
          const citations = result.citations?.parsed || this.parseCitations(text);
          const verificationResults = await this.verifyCitations(citations, dbConfig);

          result.citations = {
            ...result.citations,
            verificationResults,
            summary: {
              ...result.citations?.summary,
              verified: verificationResults.filter((r) => r.exists).length,
              unverified: verificationResults.filter((r) => !r.exists).length,
            },
          };
        }

        if (operation === 'fullValidation' && languageModel) {
          // Validate citations with AI
          const citations = result.citations.parsed;
          const validationResults = await this.validateCitations(citations, text, languageModel);

          result.citations = {
            ...result.citations,
            validationResults,
            summary: {
              ...result.citations.summary,
              appropriate: validationResults.filter((r) => r.appropriate).length,
              inappropriate: validationResults.filter((r) => !r.appropriate).length,
              issues: validationResults.flatMap((r) => r.issues || []),
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
              error: error.message,
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

  private parseCitations(text: string): ParsedCitation[] {
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

  private async verifyCitations(
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
            error: error.message,
          });
        }
      }
    } catch (error) {
      // Database connection error
      return citations.map((citation) => ({
        citationId: citation.id,
        exists: false,
        confidence: 0,
        error: `Database connection error: ${error.message}`,
      }));
    } finally {
      if (client) {
        await client.end();
      }
    }

    return results;
  }

  private async validateCitations(
    citations: ParsedCitation[],
    fullText: string,
    languageModel: any
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
          citationIndex + citation.rawText?.length + contextRadius
        );
        const context = fullText.substring(contextStart, contextEnd);

        const prompt = `Analyze this legal citation for appropriateness and accuracy.

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

        const response = await languageModel.invoke({
          messages: [
            {
              role: 'system',
              content:
                'You are a legal citation validator. Analyze citations for accuracy and appropriate use.',
            },
            {
              role: 'user',
              content: prompt,
            },
          ],
        });

        // Parse AI response
        let validationResult: ValidationResult;
        try {
          const responseText =
            typeof response === 'string' ? response : response.text || JSON.stringify(response);

          // Try to extract JSON from the response
          const jsonMatch = responseText.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const parsed = JSON.parse(jsonMatch[0]);
            validationResult = {
              citationId: citation.id,
              appropriate: parsed.appropriate || false,
              confidence: parsed.confidence || 0.5,
              reasoning: parsed.reasoning || 'No reasoning provided',
              issues: parsed.issues || [],
            };
          } else {
            // Fallback if no JSON found
            validationResult = {
              citationId: citation.id,
              appropriate: true,
              confidence: 0.5,
              reasoning: 'Could not parse AI response',
              issues: [],
            };
          }
        } catch (parseError) {
          validationResult = {
            citationId: citation.id,
            appropriate: true,
            confidence: 0.5,
            reasoning: 'Error parsing AI response',
            issues: [`Parse error: ${parseError.message}`],
          };
        }

        results.push(validationResult);
      } catch (error) {
        results.push({
          citationId: citation.id,
          appropriate: false,
          confidence: 0,
          reasoning: `Validation error: ${error.message}`,
          issues: [`Error: ${error.message}`],
        });
      }
    }

    return results;
  }
}
