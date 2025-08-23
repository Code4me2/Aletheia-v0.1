/**
 * N8N Execution Tracker
 * Polls n8n's REST API to get execution progress
 */

import { createLogger } from '@/utils/logger';

const logger = createLogger('n8n-execution-tracker');

export interface ExecutionStatus {
  id: string;
  status: 'running' | 'success' | 'error' | 'waiting' | 'canceled';
  startedAt: string;
  stoppedAt?: string;
  workflowId: string;
  workflowName?: string;
  data?: {
    resultData?: {
      runData?: Record<string, any[]>;
      lastNodeExecuted?: string;
    };
  };
  progress?: number;
}

export class N8nExecutionTracker {
  private apiUrl: string;
  private apiKey?: string;
  private pollingInterval = 500; // Poll every 500ms
  private maxPollingDuration = 300000; // Max 5 minutes
  
  constructor() {
    const n8nHost = process.env.N8N_HOST || 'n8n';
    const n8nPort = process.env.N8N_PORT || '5678';
    this.apiUrl = `http://${n8nHost}:${n8nPort}/api/v1`;
    this.apiKey = process.env.N8N_API_KEY;
  }
  
  /**
   * Track execution progress by polling the API
   */
  async trackExecution(
    executionId: string,
    onProgress: (status: ExecutionStatus) => void
  ): Promise<ExecutionStatus> {
    const startTime = Date.now();
    
    return new Promise((resolve, reject) => {
      const pollInterval = setInterval(async () => {
        try {
          // Check timeout
          if (Date.now() - startTime > this.maxPollingDuration) {
            clearInterval(pollInterval);
            reject(new Error('Execution tracking timeout'));
            return;
          }
          
          // Get execution status
          const status = await this.getExecutionStatus(executionId);
          
          // Calculate progress based on nodes executed
          if (status.data?.resultData?.runData) {
            const nodes = Object.keys(status.data.resultData.runData);
            // Rough progress estimate based on executed nodes
            status.progress = Math.min(95, nodes.length * 20);
          }
          
          // Notify progress
          onProgress(status);
          
          // Check if execution is complete
          if (status.status !== 'running' && status.status !== 'waiting') {
            clearInterval(pollInterval);
            status.progress = 100;
            resolve(status);
          }
          
        } catch (error) {
          logger.error('Failed to poll execution status', { executionId, error });
          clearInterval(pollInterval);
          reject(error);
        }
      }, this.pollingInterval);
    });
  }
  
  /**
   * Get execution status from n8n API
   */
  async getExecutionStatus(executionId: string): Promise<ExecutionStatus> {
    const headers: HeadersInit = {
      'Accept': 'application/json'
    };
    
    if (this.apiKey) {
      headers['X-N8N-API-KEY'] = this.apiKey;
    }
    
    const response = await fetch(`${this.apiUrl}/executions/${executionId}`, {
      headers
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get execution status: ${response.status}`);
    }
    
    return response.json();
  }
  
  /**
   * Get active executions
   */
  async getActiveExecutions(): Promise<ExecutionStatus[]> {
    const headers: HeadersInit = {
      'Accept': 'application/json'
    };
    
    if (this.apiKey) {
      headers['X-N8N-API-KEY'] = this.apiKey;
    }
    
    const response = await fetch(`${this.apiUrl}/executions?status=running`, {
      headers
    });
    
    if (!response.ok) {
      throw new Error(`Failed to get active executions: ${response.status}`);
    }
    
    const data = await response.json();
    return data.data || [];
  }
  
  /**
   * Try to find execution by workflow ID and approximate time
   * This is a fallback when we don't have the execution ID
   */
  async findRecentExecution(
    workflowId: string,
    since: Date = new Date(Date.now() - 5000)
  ): Promise<string | null> {
    try {
      const executions = await this.getActiveExecutions();
      
      // Find executions for this workflow started after 'since'
      const matching = executions.filter(e => 
        e.workflowId === workflowId && 
        new Date(e.startedAt) >= since
      );
      
      if (matching.length > 0) {
        // Return the most recent one
        return matching.sort((a, b) => 
          new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime()
        )[0].id;
      }
      
      return null;
    } catch (error) {
      logger.error('Failed to find recent execution', { workflowId, error });
      return null;
    }
  }
}