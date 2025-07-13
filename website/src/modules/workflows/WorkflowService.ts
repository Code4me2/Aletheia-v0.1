/**
 * Service for interacting with n8n workflows API
 */

import type { Workflow, WorkflowsResponse } from '@/types/api.types';

export class WorkflowService {
  private baseUrl = '/n8n/rest';

  /**
   * Get all workflows
   */
  public async getWorkflows(): Promise<Workflow[]> {
    try {
      const response = await fetch(`${this.baseUrl}/workflows`, {
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Authentication required. Please log in to n8n first.');
        }
        throw new Error(`Failed to fetch workflows: ${response.statusText}`);
      }

      const data: WorkflowsResponse = await response.json();
      return data.data || [];
    } catch (error) {
      console.error('WorkflowService error:', error);
      throw error;
    }
  }

  /**
   * Get a specific workflow by ID
   */
  public async getWorkflow(id: string): Promise<Workflow> {
    try {
      const response = await fetch(`${this.baseUrl}/workflows/${id}`, {
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch workflow: ${response.statusText}`);
      }

      const workflow: Workflow = await response.json();
      return workflow;
    } catch (error) {
      console.error('WorkflowService error:', error);
      throw error;
    }
  }

  /**
   * Activate a workflow
   */
  public async activateWorkflow(id: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/workflows/${id}/activate`, {
        method: 'PATCH',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to activate workflow: ${response.statusText}`);
      }
    } catch (error) {
      console.error('WorkflowService error:', error);
      throw error;
    }
  }

  /**
   * Deactivate a workflow
   */
  public async deactivateWorkflow(id: string): Promise<void> {
    try {
      const response = await fetch(`${this.baseUrl}/workflows/${id}/deactivate`, {
        method: 'PATCH',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to deactivate workflow: ${response.statusText}`);
      }
    } catch (error) {
      console.error('WorkflowService error:', error);
      throw error;
    }
  }
}