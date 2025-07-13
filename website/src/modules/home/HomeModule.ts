/**
 * Home module - Landing page for Data Compose
 */

import type { AppModule, RouteParams } from '@/types/module.types';
import { getApp } from '@core/App';

export class HomeModule implements AppModule {
  public readonly id = 'home';
  public readonly name = 'Home';
  public readonly icon = 'fas fa-home';
  public readonly version = '1.0.0';

  private container: HTMLElement | null = null;

  public async init(): Promise<void> {
    // Module initialization
    console.log('Home module initialized');
  }

  public mount(container: HTMLElement): void {
    this.container = container;
    
    // Find existing home section or create it
    let section = container.querySelector('#home');
    if (!section) {
      section = this.createHomeSection();
      container.appendChild(section);
    }
    
    section.classList.add('active');
    
    // Set up event handlers
    this.setupEventHandlers();
  }

  public unmount(): void {
    if (this.container) {
      const section = this.container.querySelector('#home');
      if (section) {
        section.classList.remove('active');
      }
    }
  }

  public onNavigate(params: RouteParams): void {
    // Handle navigation parameters if needed
    console.log('Home module navigated with params:', params);
  }

  private createHomeSection(): HTMLElement {
    const section = document.createElement('section');
    section.id = 'home';
    section.className = 'content-section';
    
    section.innerHTML = `
      <h2 class="section-title">Welcome to Data Compose</h2>
      <p class="section-subtitle">Your integrated platform for AI-powered workflow automation</p>
      
      <div class="feature-grid">
        <div class="feature-card">
          <h3>🤖 AI Chat</h3>
          <p>Interactive conversations with DeepSeek R1 AI model through n8n workflows</p>
        </div>
        <div class="feature-card">
          <h3>⚡ Workflows</h3>
          <p>Powerful n8n automation workflows with custom nodes and integrations</p>
        </div>
        <div class="feature-card">
          <h3>🔗 Webhooks</h3>
          <p>Real-time webhook communication between frontend and workflow engine</p>
        </div>
      </div>

      <div class="text-center mt-20">
        <h3>System Status</h3>
        <button id="test-connection-btn" class="btn btn-success">Test n8n Connection</button>
        <div id="connection-result" class="info-box hidden"></div>
      </div>

      <div class="text-center mt-20">
        <h3>Quick Start</h3>
        <p>Ready to begin? Start chatting with the AI or explore your workflows.</p>
        <button id="start-chat-btn" class="btn btn-primary btn-large">
          Start AI Chat →
        </button>
      </div>
    `;
    
    return section;
  }

  private setupEventHandlers(): void {
    // Test connection button
    const testBtn = document.getElementById('test-connection-btn');
    if (testBtn) {
      testBtn.addEventListener('click', () => this.testConnection());
    }
    
    // Start chat button
    const startChatBtn = document.getElementById('start-chat-btn');
    if (startChatBtn) {
      startChatBtn.addEventListener('click', () => {
        const app = getApp();
        app.navigateTo('chat');
      });
    }
  }

  private async testConnection(): Promise<void> {
    const resultBox = document.getElementById('connection-result');
    if (!resultBox) return;
    
    resultBox.innerHTML = '<p class="loading">Testing connection...</p>';
    resultBox.className = 'info-box';
    
    try {
      const response = await fetch('/n8n/healthz');
      const data = await response.json();
      
      resultBox.innerHTML = 
        '<p><strong>✅ Connection Successful!</strong></p>' +
        '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
      resultBox.className = 'info-box success';
      
    } catch (error) {
      resultBox.innerHTML = 
        '<p><strong>❌ Connection Failed:</strong> ' + 
        (error instanceof Error ? error.message : String(error)) + '</p>';
      resultBox.className = 'info-box error';
    }
  }
}