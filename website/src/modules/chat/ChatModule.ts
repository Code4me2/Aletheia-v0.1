/**
 * Chat module - AI chat interface
 */

import type { AppModule, RouteParams } from '@/types/module.types';
import type { ChatMessage } from '@/types/api.types';
import { ChatService } from './ChatService';
import { configService } from '@services/config.service';
import Alpine from 'alpinejs';

interface ChatState {
  messages: ChatMessage[];
  input: string;
  status: 'idle' | 'sending' | 'error';
  errorMessage: string;
  
  sendMessage(): Promise<void>;
  clearError(): void;
}

export class ChatModule implements AppModule {
  public readonly id = 'chat';
  public readonly name = 'AI Chat';
  public readonly icon = 'fas fa-comments';
  public readonly version = '1.0.0';

  private container: HTMLElement | null = null;
  private chatService: ChatService;
  private messageInput: HTMLInputElement | null = null;

  constructor() {
    this.chatService = new ChatService(configService.getWebhookUrl());
  }

  public async init(): Promise<void> {
    // Register Alpine component
    Alpine.data('chatState', (): ChatState => ({
      messages: [
        {
          role: 'assistant',
          content: "Welcome! I'm your AI assistant powered by DeepSeek R1. How can I help you today?",
          timestamp: new Date().toISOString(),
        },
      ],
      input: '',
      status: 'idle',
      errorMessage: '',

      async sendMessage() {
        if (!this.input.trim() || this.status === 'sending') return;

        const userMessage: ChatMessage = {
          role: 'user',
          content: this.input.trim(),
          timestamp: new Date().toISOString(),
        };

        this.messages.push(userMessage);
        this.input = '';
        this.status = 'sending';
        this.errorMessage = '';

        try {
          const response = await chatService.sendMessage(userMessage.content);
          
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: response,
            timestamp: new Date().toISOString(),
          };
          
          this.messages.push(assistantMessage);
          this.status = 'idle';
          
          // Scroll to bottom
          setTimeout(() => {
            const chatMessages = document.getElementById('chat-messages');
            if (chatMessages) {
              chatMessages.scrollTop = chatMessages.scrollHeight;
            }
          }, 50);
        } catch (error) {
          this.status = 'error';
          this.errorMessage = error instanceof Error ? error.message : 'Failed to send message';
        }
      },

      clearError() {
        this.errorMessage = '';
        this.status = 'idle';
      },
    }));

    const chatService = this.chatService;
    console.log('Chat module initialized');
  }

  public mount(container: HTMLElement): void {
    this.container = container;
    
    // Find existing chat section or create it
    let section = container.querySelector('#chat');
    if (!section) {
      section = this.createChatSection();
      container.appendChild(section);
    }
    
    section.classList.add('active');
    
    // Initialize Alpine for this section
    Alpine.initTree(section as HTMLElement);
    
    // Set up additional event handlers
    this.setupEventHandlers();
    
    // Focus input
    this.messageInput = section.querySelector('#chat-input');
    if (this.messageInput) {
      this.messageInput.focus();
    }
  }

  public unmount(): void {
    if (this.container) {
      const section = this.container.querySelector('#chat');
      if (section) {
        section.classList.remove('active');
      }
    }
  }

  public onNavigate(params: RouteParams): void {
    // Handle navigation parameters
    console.log('Chat module navigated with params:', params);
  }

  private createChatSection(): HTMLElement {
    const section = document.createElement('section');
    section.id = 'chat';
    section.className = 'content-section';
    section.setAttribute('x-data', 'chatState()');
    
    section.innerHTML = `
      <h2 class="section-title">AI Chat Interface</h2>
      <p class="section-subtitle">Chat with DeepSeek R1 through n8n workflows</p>
      
      <div class="chat-container">
        <div id="chat-messages" class="chat-messages">
          <template x-for="message in messages" :key="message.timestamp">
            <div class="message" :class="message.role === 'user' ? 'user' : 'bot'">
              <span x-text="message.content"></span>
            </div>
          </template>
        </div>
        
        <div class="chat-input-area">
          <input 
            type="text" 
            id="chat-input" 
            class="chat-input" 
            placeholder="Type your message here..."
            autocomplete="off"
            x-model="input"
            @keydown.enter="sendMessage"
            :disabled="status === 'sending'"
          >
          <button 
            @click="sendMessage" 
            class="btn btn-primary"
            :disabled="status === 'sending' || !input.trim()"
          >
            <i class="fas fa-paper-plane" x-show="status !== 'sending'"></i>
            <i class="fas fa-spinner fa-spin" x-show="status === 'sending'"></i>
            <span x-text="status === 'sending' ? 'Sending...' : 'Send'"></span>
          </button>
        </div>
        
        <div id="chat-status" class="chat-status" x-show="status === 'sending' || errorMessage">
          <span x-show="status === 'sending'" class="text-info">
            <i class="fas fa-spinner fa-spin"></i> Processing...
          </span>
          <span x-show="errorMessage" class="text-danger">
            <i class="fas fa-exclamation-circle"></i> 
            <span x-text="errorMessage"></span>
            <button @click="clearError" class="btn-link">Dismiss</button>
          </span>
        </div>
      </div>
    `;
    
    return section;
  }

  private setupEventHandlers(): void {
    // Additional event handlers if needed
  }
}