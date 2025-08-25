import { DocumentSource } from './types';
import { courtDocumentSource } from './court-source';

/**
 * Document Source Registry
 * 
 * Central registry for all document sources.
 * New sources can be registered here without modifying existing code.
 */
class DocumentSourceRegistry {
  private sources: Map<string, DocumentSource> = new Map();
  private defaultSourceId: string = 'court';

  constructor() {
    // Register default court document source
    this.register(courtDocumentSource);
  }

  /**
   * Register a new document source
   */
  register(source: DocumentSource): void {
    if (this.sources.has(source.sourceId)) {
      console.warn(`Document source '${source.sourceId}' is already registered. Overwriting.`);
    }
    this.sources.set(source.sourceId, source);
  }

  /**
   * Get a document source by ID
   */
  getSource(sourceId: string): DocumentSource | undefined {
    return this.sources.get(sourceId);
  }

  /**
   * Get the default document source
   */
  getDefaultSource(): DocumentSource {
    const source = this.sources.get(this.defaultSourceId);
    if (!source) {
      throw new Error(`Default document source '${this.defaultSourceId}' not found`);
    }
    return source;
  }

  /**
   * Set the default document source
   */
  setDefaultSource(sourceId: string): void {
    if (!this.sources.has(sourceId)) {
      throw new Error(`Document source '${sourceId}' not registered`);
    }
    this.defaultSourceId = sourceId;
  }

  /**
   * Get all registered sources
   */
  getAllSources(): DocumentSource[] {
    return Array.from(this.sources.values());
  }

  /**
   * Get available sources (that are currently accessible)
   */
  async getAvailableSources(): Promise<DocumentSource[]> {
    const sources = this.getAllSources();
    const availabilityChecks = await Promise.all(
      sources.map(async (source) => ({
        source,
        available: await source.isAvailable().catch(() => false)
      }))
    );
    
    return availabilityChecks
      .filter(({ available }) => available)
      .map(({ source }) => source);
  }

  /**
   * Check if a source is registered
   */
  hasSource(sourceId: string): boolean {
    return this.sources.has(sourceId);
  }

  /**
   * Remove a source from the registry
   */
  unregister(sourceId: string): boolean {
    if (sourceId === this.defaultSourceId) {
      throw new Error('Cannot unregister the default document source');
    }
    return this.sources.delete(sourceId);
  }
}

// Export singleton instance
export const documentSourceRegistry = new DocumentSourceRegistry();

// Export convenience function for getting sources
export function getDocumentSource(sourceId?: string): DocumentSource {
  if (sourceId) {
    const source = documentSourceRegistry.getSource(sourceId);
    if (!source) {
      throw new Error(`Document source '${sourceId}' not found`);
    }
    return source;
  }
  return documentSourceRegistry.getDefaultSource();
}