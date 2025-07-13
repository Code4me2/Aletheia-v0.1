/**
 * Workflows module - n8n workflow management
 */

import type { AppModule, RouteParams } from '@/types/module.types';
import type { Workflow } from '@/types/api.types';
import { WorkflowService } from './WorkflowService';
import Alpine from 'alpinejs';

interface WorkflowsState {
  workflows: Workflow[];
  isLoading: boolean;
  error: string | null;
  selectedWorkflow: Workflow | null;
  
  loadWorkflows(): Promise<void>;
  selectWorkflow(workflow: Workflow): void;
  openN8nInterface(): void;
}

export class WorkflowsModule implements AppModule {
  public readonly id = 'workflows';
  public readonly name = 'Workflows';
  public readonly icon = 'fas fa-project-diagram';
  public readonly version = '1.0.0';

  private container: HTMLElement | null = null;
  private workflowService: WorkflowService;

  constructor() {
    this.workflowService = new WorkflowService();
  }

  public async init(): Promise<void> {
    // Register Alpine component
    Alpine.data('workflowsState', (): WorkflowsState => ({
      workflows: [],
      isLoading: false,
      error: null,
      selectedWorkflow: null,

      async loadWorkflows() {
        this.isLoading = true;
        this.error = null;

        try {
          this.workflows = await workflowService.getWorkflows();
        } catch (error) {
          this.error = error instanceof Error ? error.message : 'Failed to load workflows';
          console.error('Failed to load workflows:', error);
        } finally {
          this.isLoading = false;
        }
      },

      selectWorkflow(workflow: Workflow) {
        this.selectedWorkflow = workflow;
      },

      openN8nInterface() {
        window.open('/n8n/home/workflows', '_blank');
      },
    }));

    const workflowService = this.workflowService;
    console.log('Workflows module initialized');
  }

  public mount(container: HTMLElement): void {
    this.container = container;
    
    // Find existing workflows section or create it
    let section = container.querySelector('#workflows');
    if (!section) {
      section = this.createWorkflowsSection();
      container.appendChild(section);
    }
    
    section.classList.add('active');
    
    // Initialize Alpine for this section
    Alpine.initTree(section as HTMLElement);
    
    // Trigger initial load
    const component = (section as any)._x_dataStack?.[0];
    if (component?.loadWorkflows) {
      component.loadWorkflows();
    }
  }

  public unmount(): void {
    if (this.container) {
      const section = this.container.querySelector('#workflows');
      if (section) {
        section.classList.remove('active');
      }
    }
  }

  public onNavigate(params: RouteParams): void {
    console.log('Workflows module navigated with params:', params);
  }

  private createWorkflowsSection(): HTMLElement {
    const section = document.createElement('section');
    section.id = 'workflows';
    section.className = 'content-section';
    section.setAttribute('x-data', 'workflowsState()');
    
    section.innerHTML = `
      <h2 class="section-title">Workflow Management</h2>
      <p class="section-subtitle">Create and manage your n8n automation workflows</p>
      
      <div class="text-center mb-20">
        <button @click="openN8nInterface" class="btn btn-primary btn-large">
          <i class="fas fa-external-link-alt"></i> Open n8n Interface
        </button>
      </div>
      
      <div id="workflows-list" class="workflow-list">
        <!-- Loading state -->
        <p x-show="isLoading" class="loading">Loading workflows...</p>
        
        <!-- Error state -->
        <div x-show="error && !isLoading" class="error-message">
          <p><strong>Error:</strong> <span x-text="error"></span></p>
          <button @click="loadWorkflows" class="btn btn-secondary mt-10">
            <i class="fas fa-redo"></i> Retry
          </button>
        </div>
        
        <!-- Empty state -->
        <div x-show="!isLoading && !error && workflows.length === 0" class="empty-state">
          <p>No workflows found.</p>
          <button @click="openN8nInterface" class="btn btn-primary">
            Create your first workflow
          </button>
        </div>
        
        <!-- Workflows list -->
        <div x-show="!isLoading && !error && workflows.length > 0">
          <h3>Current Workflows:</h3>
          <template x-for="workflow in workflows" :key="workflow.id">
            <div class="workflow-item" @click="selectWorkflow(workflow)">
              <span class="workflow-name" x-text="workflow.name"></span>
              <span 
                class="workflow-status" 
                :class="workflow.active ? 'active' : 'inactive'"
              >
                <span x-text="workflow.active ? '✅ Active' : '⏸️ Inactive'"></span>
              </span>
            </div>
          </template>
        </div>
        
        <!-- Selected workflow details -->
        <div x-show="selectedWorkflow" class="workflow-details mt-20">
          <h4>Workflow Details</h4>
          <div class="details-content">
            <p><strong>Name:</strong> <span x-text="selectedWorkflow?.name"></span></p>
            <p><strong>ID:</strong> <code x-text="selectedWorkflow?.id"></code></p>
            <p><strong>Status:</strong> 
              <span 
                :class="selectedWorkflow?.active ? 'text-success' : 'text-warning'"
                x-text="selectedWorkflow?.active ? 'Active' : 'Inactive'"
              ></span>
            </p>
            <p><strong>Created:</strong> 
              <span x-text="selectedWorkflow ? new Date(selectedWorkflow.createdAt).toLocaleString() : ''"></span>
            </p>
            <p><strong>Updated:</strong> 
              <span x-text="selectedWorkflow ? new Date(selectedWorkflow.updatedAt).toLocaleString() : ''"></span>
            </p>
          </div>
        </div>
      </div>
    `;
    
    return section;
  }
}