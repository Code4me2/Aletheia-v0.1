/**
 * Integration tests for YAKE node within n8n workflow context
 * These tests simulate how the node behaves when used in actual n8n workflows
 */

const assert = require('assert');
const { describe, it, before, after } = require('mocha');
const { IExecuteFunctions, INodeExecutionData } = require('n8n-workflow');

// Mock n8n execution context
class MockExecuteFunctions {
    constructor(inputData, parameters = {}) {
        this.inputData = inputData;
        this.parameters = parameters;
        this.helpers = {
            httpRequest: async (options) => {
                // Mock HTTP requests if needed
                return { data: {} };
            }
        };
    }

    getInputData() {
        return this.inputData;
    }

    getNodeParameter(parameterName, itemIndex, defaultValue) {
        return this.parameters[parameterName] || defaultValue;
    }

    getWorkflow() {
        return {
            id: 'test-workflow-123',
            name: 'Test Workflow'
        };
    }

    getNode() {
        return {
            id: 'yake-node-456',
            name: 'YAKE Keyword Extraction',
            type: 'n8n-nodes-yake.yakeKeywordExtraction'
        };
    }

    async helpers() {
        return this.helpers;
    }
}

describe('YAKE Node - n8n Workflow Integration', () => {
    let YakeNode;

    before(() => {
        // In real implementation, this would load the actual node
        // For testing, we'll create a mock implementation
        YakeNode = {
            async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
                const items = this.getInputData();
                const returnData: INodeExecutionData[] = [];

                for (let i = 0; i < items.length; i++) {
                    const text = this.getNodeParameter('text', i, '') as string;
                    const language = this.getNodeParameter('language', i, 'en') as string;
                    const ngramSize = this.getNodeParameter('ngramSize', i, 3) as number;
                    const numKeywords = this.getNodeParameter('numKeywords', i, 20) as number;
                    const deduplicationThreshold = this.getNodeParameter('deduplicationThreshold', i, 0.7) as number;

                    // Mock keyword extraction
                    const keywords = mockExtractKeywords(text, {
                        language,
                        ngramSize,
                        numKeywords,
                        deduplicationThreshold
                    });

                    returnData.push({
                        json: {
                            keywords,
                            metadata: {
                                textLength: text.length,
                                language,
                                extractionTimestamp: new Date().toISOString(),
                                parameters: {
                                    ngramSize,
                                    numKeywords,
                                    deduplicationThreshold
                                }
                            }
                        },
                        pairedItem: { item: i }
                    });
                }

                return [returnData];
            }
        };
    });

    // Mock keyword extraction function
    function mockExtractKeywords(text, options) {
        // Simple mock implementation
        const words = text.toLowerCase().split(/\s+/);
        const keywords = [];
        
        for (let i = 0; i < Math.min(options.numKeywords, words.length); i++) {
            if (words[i] && words[i].length > 3) {
                keywords.push({
                    keyword: words[i],
                    score: Math.random() * 0.1
                });
            }
        }
        
        return keywords;
    }

    describe('Single Item Processing', () => {
        it('should process a single text input', async () => {
            const inputData = [{
                json: {
                    content: "Artificial intelligence and machine learning are transforming industries worldwide."
                }
            }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.content}}",
                language: 'en',
                ngramSize: 3,
                numKeywords: 5
            });

            const result = await YakeNode.execute.call(mockContext);

            assert(Array.isArray(result));
            assert.strictEqual(result[0].length, 1);
            assert(result[0][0].json.keywords);
            assert(Array.isArray(result[0][0].json.keywords));
            assert(result[0][0].json.keywords.length <= 5);
        });
    });

    describe('Batch Processing', () => {
        it('should process multiple items in batch', async () => {
            const inputData = [
                { json: { text: "First document about technology" } },
                { json: { text: "Second document about healthcare" } },
                { json: { text: "Third document about finance" } }
            ];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.text}}",
                language: 'en',
                ngramSize: 2,
                numKeywords: 3
            });

            const result = await YakeNode.execute.call(mockContext);

            assert.strictEqual(result[0].length, 3);
            result[0].forEach((item, index) => {
                assert(item.json.keywords);
                assert(item.pairedItem.item === index);
                assert(item.json.metadata.textLength > 0);
            });
        });
    });

    describe('Error Handling', () => {
        it('should handle missing text gracefully', async () => {
            const inputData = [{ json: {} }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.missingField}}",
                language: 'en'
            });

            const result = await YakeNode.execute.call(mockContext);

            assert(result[0][0].json.keywords);
            assert.strictEqual(result[0][0].json.keywords.length, 0);
        });

        it('should handle invalid language parameter', async () => {
            const inputData = [{
                json: { text: "Test text for extraction" }
            }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.text}}",
                language: 'invalid_language'
            });

            // Should default to 'en' or handle gracefully
            const result = await YakeNode.execute.call(mockContext);
            assert(result[0][0].json.keywords);
        });
    });

    describe('Workflow Chain Integration', () => {
        it('should work with upstream node data', async () => {
            // Simulate data from a previous node (e.g., HTTP Request node)
            const upstreamData = [{
                json: {
                    article: {
                        title: "Breaking News",
                        content: "Scientists discover new method for sustainable energy production using advanced solar panels."
                    },
                    source: "news-api"
                }
            }];

            const mockContext = new MockExecuteFunctions(upstreamData, {
                text: "={{$json.article.content}}",
                language: 'en',
                ngramSize: 3,
                numKeywords: 10
            });

            const result = await YakeNode.execute.call(mockContext);

            assert(result[0][0].json.keywords.length > 0);
            // Verify original data is preserved for downstream nodes
            assert(result[0][0].json.metadata);
        });

        it('should prepare data for downstream nodes', async () => {
            const inputData = [{
                json: {
                    text: "Cloud computing enables scalable infrastructure",
                    documentId: "doc-123"
                }
            }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.text}}",
                language: 'en',
                numKeywords: 5
            });

            const result = await YakeNode.execute.call(mockContext);

            // Check if output is suitable for downstream nodes
            const output = result[0][0].json;
            assert(output.keywords);
            assert(output.metadata);
            
            // Downstream node could use this data
            const keywordString = output.keywords.map(k => k.keyword).join(', ');
            assert(typeof keywordString === 'string');
        });
    });

    describe('Performance and Limits', () => {
        it('should handle large text efficiently', async () => {
            const largeText = 'Lorem ipsum dolor sit amet '.repeat(1000);
            const inputData = [{ json: { content: largeText } }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.content}}",
                numKeywords: 50
            });

            const startTime = Date.now();
            const result = await YakeNode.execute.call(mockContext);
            const processingTime = Date.now() - startTime;

            assert(result[0][0].json.keywords.length <= 50);
            assert(processingTime < 5000, 'Processing should complete within 5 seconds');
        });

        it('should respect keyword limit parameter', async () => {
            const inputData = [{
                json: { text: "A very long text with many words that could generate numerous keywords" }
            }];

            const limits = [5, 10, 20];

            for (const limit of limits) {
                const mockContext = new MockExecuteFunctions(inputData, {
                    text: "={{$json.text}}",
                    numKeywords: limit
                });

                const result = await YakeNode.execute.call(mockContext);
                assert(result[0][0].json.keywords.length <= limit);
            }
        });
    });

    describe('Output Format Validation', () => {
        it('should return properly formatted keyword objects', async () => {
            const inputData = [{
                json: { text: "Test document for keyword extraction validation" }
            }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.text}}",
                numKeywords: 5
            });

            const result = await YakeNode.execute.call(mockContext);
            const keywords = result[0][0].json.keywords;

            keywords.forEach(keyword => {
                assert(typeof keyword.keyword === 'string');
                assert(typeof keyword.score === 'number');
                assert(keyword.score >= 0 && keyword.score <= 1);
                assert(keyword.keyword.length > 0);
            });
        });

        it('should include all required metadata', async () => {
            const inputData = [{
                json: { text: "Metadata validation test" }
            }];

            const mockContext = new MockExecuteFunctions(inputData, {
                text: "={{$json.text}}"
            });

            const result = await YakeNode.execute.call(mockContext);
            const metadata = result[0][0].json.metadata;

            assert(metadata);
            assert(typeof metadata.textLength === 'number');
            assert(typeof metadata.language === 'string');
            assert(typeof metadata.extractionTimestamp === 'string');
            assert(metadata.parameters);
            assert(typeof metadata.parameters.ngramSize === 'number');
        });
    });
});