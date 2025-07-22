/**
 * Chat service for handling webhook communication
 */

import type { ChatRequest, ChatResponse } from '@/types/api.types';

export class ChatService {
  constructor(private webhookUrl: string) {}

  /**
   * Send a chat message to the webhook
   */
  public async sendMessage(message: string): Promise<string> {
    const request: ChatRequest = {
      action: 'chat',
      message: message,
      timestamp: new Date().toISOString(),
    };

    try {
      const response = await fetch(this.webhookUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      // Check if response is JSON or plain text
      const contentType = response.headers.get('content-type');
      let responseText: string;

      if (contentType && contentType.includes('application/json')) {
        // Handle JSON response
        const jsonData: ChatResponse = await response.json();
        
        // Extract text from JSON - adjust based on your n8n output structure
        responseText = 
          jsonData.response || 
          jsonData.output || 
          jsonData.message || 
          JSON.stringify(jsonData);
      } else {
        // Handle plain text response
        responseText = await response.text();
      }

      return responseText;
    } catch (error) {
      console.error('Chat service error:', error);
      
      if (error instanceof Error) {
        throw error;
      } else {
        throw new Error('Failed to send message');
      }
    }
  }

  /**
   * Update the webhook URL
   */
  public setWebhookUrl(url: string): void {
    this.webhookUrl = url;
  }

  /**
   * Get the current webhook URL
   */
  public getWebhookUrl(): string {
    return this.webhookUrl;
  }
}