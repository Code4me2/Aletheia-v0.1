/**
 * Hierarchical Visualization module - Document summarization visualization
 * This is a simplified stub implementation to be expanded with full D3.js functionality
 */

import type { AppModule, RouteParams } from '@/types/module.types';
import type { HierarchyData, SummarizationHistory } from '@/types/api.types';
import Alpine from 'alpinejs';

interface VisualizationState {
  mode: 'form' | 'visualization';
  directoryName: string;
  isProcessing: boolean;
  statusMessage: string;
  history: SummarizationHistory[];
  currentHierarchy: HierarchyData | null;
  
  startSummarization(): Promise<void>;
  loadHistory(): void;
  selectHistoryItem(batchId: string): void;
  createMockHierarchy(): HierarchyData;
}

export class VisualizationModule implements AppModule {
  public readonly id = 'hierarchical-summarization';
  public readonly name = 'Hierarchical Summarization';
  public readonly icon = 'fas fa-layer-group';
  public readonly version = '1.0.0';

  private container: HTMLElement | null = null;

  public async init(): Promise<void> {
    // Register Alpine component
    Alpine.data('visualizationState', (): VisualizationState => ({
      mode: 'form',
      directoryName: '',
      isProcessing: false,
      statusMessage: '',
      history: [],
      currentHierarchy: null,

      async startSummarization() {
        if (!this.directoryName.trim()) {
          this.statusMessage = 'Please enter a directory name';
          return;
        }

        this.isProcessing = true;
        this.statusMessage = 'Processing documents...';

        try {
          // TODO: Implement actual API call
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Mock success
          this.statusMessage = 'Summarization complete!';
          this.mode = 'visualization';
          
          // TODO: Load actual hierarchy data
          this.currentHierarchy = this.createMockHierarchy();
        } catch (error) {
          this.statusMessage = `Error: ${error instanceof Error ? error.message : 'Unknown error'}`;
        } finally {
          this.isProcessing = false;
        }
      },

      loadHistory() {
        // Load from localStorage
        const stored = localStorage.getItem('dataCompose_summarizationHistory_v1');
        if (stored) {
          try {
            this.history = JSON.parse(stored);
          } catch (error) {
            console.error('Failed to parse history:', error);
            this.history = [];
          }
        }
      },

      selectHistoryItem(batchId: string) {
        // TODO: Load hierarchy data for selected batch
        console.log('Selected batch:', batchId);
        this.mode = 'visualization';
      },

      // Helper to create mock data
      createMockHierarchy(): HierarchyData {
        return {
          batchId: 'mock-' + Date.now(),
          directoryName: this.directoryName,
          timestamp: new Date().toISOString(),
          totalDocuments: 4,
          hierarchyDepth: 3,
          levels: [
            { level: 0, count: 4, label: 'Source Documents' },
            { level: 1, count: 2, label: 'Initial Summaries' },
            { level: 2, count: 1, label: 'Final Summary' },
          ],
          documents: {
            '0': [
              { id: 1, content: 'Document 1 content...', child_ids: [5] },
              { id: 2, content: 'Document 2 content...', child_ids: [5] },
              { id: 3, content: 'Document 3 content...', child_ids: [6] },
              { id: 4, content: 'Document 4 content...', child_ids: [6] },
            ],
            '1': [
              { id: 5, summary: 'Summary of docs 1-2...', parent_id: 1, child_ids: [7] },
              { id: 6, summary: 'Summary of docs 3-4...', parent_id: 3, child_ids: [7] },
            ],
            '2': [
              { id: 7, summary: 'Final summary of all documents...', parent_id: 5 },
            ],
          },
        };
      },
    }));

    console.log('Visualization module initialized');
  }

  public mount(container: HTMLElement): void {
    this.container = container;
    
    // Find existing section or create it
    let section = container.querySelector('#hierarchical-summarization');
    if (!section) {
      section = this.createVisualizationSection();
      container.appendChild(section);
    }
    
    section.classList.add('active');
    
    // Initialize Alpine for this section
    Alpine.initTree(section as HTMLElement);
    
    // Load history
    const component = (section as any)._x_dataStack?.[0];
    if (component?.loadHistory) {
      component.loadHistory();
    }
  }

  public unmount(): void {
    if (this.container) {
      const section = this.container.querySelector('#hierarchical-summarization');
      if (section) {
        section.classList.remove('active');
      }
    }
  }

  public onNavigate(params: RouteParams): void {
    console.log('Visualization module navigated with params:', params);
  }

  private createVisualizationSection(): HTMLElement {
    const section = document.createElement('section');
    section.id = 'hierarchical-summarization';
    section.className = 'content-section';
    section.setAttribute('x-data', 'visualizationState()');
    
    section.innerHTML = `
      <div class="hierarchical-container">
        <div class="section-header">
          <div>
            <h2 class="section-title">Hierarchical Document Summarization</h2>
            <p class="section-subtitle">Process directories of documents into hierarchical summaries</p>
          </div>
        </div>
        
        <!-- Form View -->
        <div x-show="mode === 'form'" class="form-container">
          <div class="card">
            <h3><i class="fas fa-folder-open"></i> Create New Summarization</h3>
            <p class="info-text">
              Place your document directory in <code>n8n/local-files/uploads/[your-directory-name]/</code><br>
              Then enter the directory name below to start processing.
            </p>
            
            <div class="form-group">
              <label for="directory-name">Directory Name:</label>
              <div class="input-group">
                <span class="input-prefix">/files/uploads/</span>
                <input 
                  type="text" 
                  id="directory-name" 
                  class="form-input" 
                  placeholder="e.g., legal-docs-2024"
                  autocomplete="off"
                  x-model="directoryName"
                  @keydown.enter="startSummarization"
                  :disabled="isProcessing"
                >
              </div>
            </div>
            
            <button 
              class="btn btn-primary btn-large" 
              @click="startSummarization"
              :disabled="isProcessing || !directoryName.trim()"
            >
              <i class="fas" :class="isProcessing ? 'fa-spinner fa-spin' : 'fa-play'"></i> 
              <span x-text="isProcessing ? 'Processing...' : 'Generate Hierarchy'"></span>
            </button>
            
            <div x-show="statusMessage" class="processing-status" :class="statusMessage.includes('Error') ? 'error' : ''">
              <span x-text="statusMessage"></span>
            </div>
          </div>
          
          <!-- History -->
          <div x-show="history.length > 0" class="history-section mt-20">
            <h3>Recent Summarizations</h3>
            <template x-for="item in history" :key="item.batchId">
              <div class="history-item" @click="selectHistoryItem(item.batchId)">
                <div class="history-item-title" x-text="item.directoryName"></div>
                <div class="history-item-meta">
                  <span x-text="new Date(item.timestamp).toLocaleDateString()"></span> • 
                  <span x-text="item.totalDocuments + ' docs'"></span> • 
                  <span x-text="item.hierarchyDepth + ' levels'"></span>
                </div>
              </div>
            </template>
          </div>
        </div>
        
        <!-- Visualization View (Simplified) -->
        <div x-show="mode === 'visualization'" class="visualization-container">
          <div class="visualization-header">
            <button @click="mode = 'form'" class="btn btn-secondary">
              <i class="fas fa-arrow-left"></i> Back
            </button>
            <h3>Hierarchy Visualization</h3>
          </div>
          
          <div class="visualization-placeholder">
            <p>Full D3.js visualization will be implemented here</p>
            <p>Current hierarchy: <span x-text="currentHierarchy?.directoryName"></span></p>
            
            <!-- Simple text representation -->
            <template x-if="currentHierarchy">
              <div class="hierarchy-text">
                <h4>Hierarchy Structure:</h4>
                <template x-for="level in currentHierarchy.levels" :key="level.level">
                  <div class="level-info">
                    Level <span x-text="level.level"></span>: 
                    <span x-text="level.label"></span> 
                    (<span x-text="level.count"></span> items)
                  </div>
                </template>
              </div>
            </template>
          </div>
        </div>
      </div>
    `;
    
    return section;
  }
}