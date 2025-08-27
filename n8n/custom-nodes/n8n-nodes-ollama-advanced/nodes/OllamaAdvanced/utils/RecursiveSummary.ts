import { IDataObject } from 'n8n-workflow';

export interface SummaryLevel {
  level: number;
  chunks: string[];
  summaries: string[];
  metadata: {
    chunkCount: number;
    totalLength: number;
    summaryLength: number;
  };
}

export interface RecursiveSummaryConfig {
  maxChunkSize?: number;
  overlapSize?: number;
  summaryRatio?: number;
  maxLevels?: number;
}

export class RecursiveSummaryManager {
  private config: Required<RecursiveSummaryConfig>;

  constructor(config: RecursiveSummaryConfig = {}) {
    this.config = {
      maxChunkSize: config.maxChunkSize || 2048,
      overlapSize: config.overlapSize || 200,
      summaryRatio: config.summaryRatio || 0.3,
      maxLevels: config.maxLevels || 3,
    };
  }

  /**
   * Check if text needs chunking based on size threshold
   */
  needsChunking(text: string, threshold?: number): boolean {
    const actualThreshold = threshold || this.config.maxChunkSize;
    return text.length > actualThreshold;
  }

  /**
   * Split text into overlapping chunks
   */
  splitIntoChunks(text: string): string[] {
    const chunks: string[] = [];
    const chunkSize = this.config.maxChunkSize;
    const overlap = this.config.overlapSize;
    
    // If text is smaller than chunk size, return as single chunk
    if (text.length <= chunkSize) {
      return [text];
    }
    
    let position = 0;
    while (position < text.length) {
      // Calculate end position for this chunk
      let endPos = Math.min(position + chunkSize, text.length);
      
      // Try to find a good break point (sentence end, paragraph, etc.)
      if (endPos < text.length) {
        const searchText = text.substring(position, endPos);
        const breakPoints = [
          searchText.lastIndexOf('\n\n'),
          searchText.lastIndexOf('.\n'),
          searchText.lastIndexOf('. '),
          searchText.lastIndexOf('! '),
          searchText.lastIndexOf('? '),
        ];
        
        // Find the best break point (closest to end)
        let bestBreak = -1;
        for (const breakPoint of breakPoints) {
          if (breakPoint > chunkSize * 0.5) { // At least 50% of chunk size
            bestBreak = breakPoint;
            break;
          }
        }
        
        if (bestBreak > 0) {
          endPos = position + bestBreak + 1;
        }
      }
      
      // Extract chunk
      const chunk = text.substring(position, endPos).trim();
      if (chunk) {
        chunks.push(chunk);
      }
      
      // Move position forward (with overlap if not last chunk)
      if (endPos < text.length) {
        position = endPos - overlap;
      } else {
        break;
      }
    }
    
    return chunks;
  }

  /**
   * Generate a context-aware summary prompt
   */
  generateSummaryPrompt(
    text: string,
    level: number,
    options: { topic?: any; style?: any } = {}
  ): string {
    const { topic, style = 'concise' } = options;
    
    let styleInstruction = '';
    switch (style) {
      case 'detailed':
        styleInstruction = 'Provide a comprehensive summary that preserves important details.';
        break;
      case 'technical':
        styleInstruction = 'Focus on technical details, specifications, and precise terminology.';
        break;
      case 'executive':
        styleInstruction = 'Provide a high-level executive summary focusing on key decisions and outcomes.';
        break;
      case 'concise':
      default:
        styleInstruction = 'Provide a clear and concise summary.';
        break;
    }
    
    let prompt = '';
    
    if (level === 0) {
      // First level - initial summarization
      prompt = `${styleInstruction}\n\n`;
      
      if (topic) {
        prompt += `Focus particularly on aspects related to: ${topic}\n\n`;
      }
      
      prompt += `Summarize the following text, capturing the main points and key information:\n\n${text}`;
    } else {
      // Higher levels - summarizing summaries
      prompt = `You are summarizing a collection of summaries from a larger document.\n\n`;
      prompt += `${styleInstruction}\n\n`;
      
      if (topic) {
        prompt += `Maintain focus on: ${topic}\n\n`;
      }
      
      prompt += `Synthesize these summaries into a coherent overview:\n\n${text}`;
    }
    
    return prompt;
  }

  /**
   * Merge multiple summaries into a single text
   */
  mergeSummaries(summaries: string[]): string {
    // Simple concatenation with paragraph breaks
    // Could be enhanced with more sophisticated merging logic
    return summaries
      .filter(s => s && s.trim())
      .join('\n\n')
      .trim();
  }

  /**
   * Format the hierarchical summary output
   */
  formatHierarchicalSummary(levels: SummaryLevel[]): IDataObject {
    if (levels.length === 0) {
      return {
        error: 'No summary levels generated',
      };
    }
    
    const finalLevel = levels[levels.length - 1];
    const finalSummary = this.mergeSummaries(finalLevel.summaries);
    
    // Calculate compression statistics
    const originalLength = levels[0].chunks.reduce((sum, chunk) => sum + chunk.length, 0);
    const compressionRatio = (finalSummary.length / originalLength).toFixed(3);
    
    // Build hierarchical structure
    const hierarchy = levels.map((level, index) => ({
      level: index,
      chunkCount: level.metadata.chunkCount,
      summaryCount: level.summaries.length,
      totalLength: level.metadata.totalLength,
      summaryLength: level.metadata.summaryLength,
      compressionRatio: (level.metadata.summaryLength / level.metadata.totalLength).toFixed(3),
    }));
    
    return {
      finalSummary,
      metadata: {
        originalLength,
        finalLength: finalSummary.length,
        compressionRatio,
        levelsProcessed: levels.length,
        totalChunks: levels.reduce((sum, level) => sum + level.chunks.length, 0),
      },
      hierarchy,
      // Include intermediate summaries for transparency
      intermediateSummaries: levels.map((level, index) => ({
        level: index,
        summary: this.mergeSummaries(level.summaries),
      })),
    };
  }

  /**
   * Estimate token count (rough approximation)
   */
  estimateTokens(text: string): number {
    // Rough estimate: 1 token ≈ 4 characters
    return Math.ceil(text.length / 4);
  }

  /**
   * Calculate optimal chunk size based on model constraints
   */
  calculateOptimalChunkSize(
    modelContextWindow: number,
    summaryRatio: number = this.config.summaryRatio
  ): number {
    // Reserve space for prompt and response
    const usableContext = modelContextWindow * 0.8;
    
    // Account for summary generation needs
    const optimalChunkTokens = usableContext / (1 + summaryRatio);
    
    // Convert to characters (rough estimate)
    return Math.floor(optimalChunkTokens * 4);
  }

  /**
   * Create a summary chain for very long documents
   */
  async createSummaryChain(
    text: string,
    summarizeFunction: (text: string) => Promise<string>
  ): Promise<string> {
    let currentText = text;
    let level = 0;
    
    while (this.needsChunking(currentText) && level < this.config.maxLevels) {
      const chunks = this.splitIntoChunks(currentText);
      const summaries: string[] = [];
      
      // Process chunks in parallel if possible
      for (const chunk of chunks) {
        const summary = await summarizeFunction(chunk);
        summaries.push(summary);
      }
      
      currentText = this.mergeSummaries(summaries);
      level++;
    }
    
    // Final summary pass
    if (currentText.length > 500) { // Only if still substantial
      currentText = await summarizeFunction(currentText);
    }
    
    return currentText;
  }
}