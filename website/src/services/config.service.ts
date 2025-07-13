/**
 * Configuration service for Data Compose application
 */

import type { WebhookConfig } from '@/types/api.types';
import type { TreeViewConfig, VisualizationTheme } from '@/types/visualization.types';

export interface AppConfig {
  webhook: WebhookConfig;
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
  };
  visualization: {
    defaultMode: 'panel' | 'tree';
    treeView: TreeViewConfig;
    theme: VisualizationTheme;
  };
  features: {
    enableDebugMode: boolean;
    enableMockData: boolean;
    enableKeyboardShortcuts: boolean;
    enableExport: boolean;
  };
  storage: {
    prefix: string;
    version: number;
  };
}

class ConfigService {
  private static instance: ConfigService;
  private config: AppConfig;

  private constructor() {
    this.config = this.loadConfig();
  }

  public static getInstance(): ConfigService {
    if (!ConfigService.instance) {
      ConfigService.instance = new ConfigService();
    }
    return ConfigService.instance;
  }

  private loadConfig(): AppConfig {
    // Get base URL from current location
    const baseUrl = `${window.location.protocol}//${window.location.host}`;
    
    // Default configuration
    const defaultConfig: AppConfig = {
      webhook: {
        WEBHOOK_ID: 'c188c31c-1c45-4118-9ece-5b6057ab5177',
        WEBHOOK_URL: `${baseUrl}/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177`,
      },
      api: {
        baseUrl: baseUrl,
        timeout: 30000,
        retryAttempts: 3,
      },
      visualization: {
        defaultMode: 'panel',
        treeView: {
          width: 1200,
          height: 800,
          nodeWidth: 300,
          nodeHeight: 200,
          horizontalSpacing: 400,
          verticalSpacing: 100,
          animationDuration: 750,
          maxZoom: 3,
          minZoom: 0.1,
        },
        theme: {
          levelColors: {
            0: { background: '#e3f2fd', border: '#2196f3', text: '#0d47a1' },
            1: { background: '#e8f5e9', border: '#4caf50', text: '#1b5e20' },
            2: { background: '#fff3e0', border: '#ff9800', text: '#e65100' },
            3: { background: '#f3e5f5', border: '#9c27b0', text: '#4a148c' },
          },
          linkColor: '#999',
          highlightColor: '#ff6b6b',
          font: {
            family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
            size: 14,
            weight: 400,
          },
        },
      },
      features: {
        enableDebugMode: import.meta.env.MODE === 'development',
        enableMockData: import.meta.env.MODE === 'development',
        enableKeyboardShortcuts: true,
        enableExport: true,
      },
      storage: {
        prefix: 'dataCompose',
        version: 1,
      },
    };

    // Override with environment variables if available
    if (import.meta.env.VITE_WEBHOOK_ID) {
      defaultConfig.webhook.WEBHOOK_ID = import.meta.env.VITE_WEBHOOK_ID;
      defaultConfig.webhook.WEBHOOK_URL = `${baseUrl}/webhook/${import.meta.env.VITE_WEBHOOK_ID}`;
    }

    if (import.meta.env.VITE_API_BASE_URL) {
      defaultConfig.api.baseUrl = import.meta.env.VITE_API_BASE_URL;
    }

    return defaultConfig;
  }

  public get<K extends keyof AppConfig>(key: K): AppConfig[K] {
    return this.config[key];
  }

  public getWebhookUrl(): string {
    return this.config.webhook.WEBHOOK_URL;
  }

  public getWebhookId(): string {
    return this.config.webhook.WEBHOOK_ID;
  }

  public isDebugMode(): boolean {
    return this.config.features.enableDebugMode || window.DEBUG === true;
  }

  public getStorageKey(key: string): string {
    return `${this.config.storage.prefix}_${key}_v${this.config.storage.version}`;
  }

  public updateConfig(updates: DeepPartial<AppConfig>): void {
    this.config = this.deepMerge(this.config, updates) as AppConfig;
  }

  private deepMerge(target: any, source: any): any {
    const output = { ...target };
    
    if (this.isObject(target) && this.isObject(source)) {
      Object.keys(source).forEach((key) => {
        if (this.isObject(source[key])) {
          if (!(key in target)) {
            Object.assign(output, { [key]: source[key] });
          } else {
            output[key] = this.deepMerge(target[key], source[key]);
          }
        } else {
          Object.assign(output, { [key]: source[key] });
        }
      });
    }
    
    return output;
  }

  private isObject(item: any): boolean {
    return item && typeof item === 'object' && !Array.isArray(item);
  }
}

// Type helper for deep partial
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Export singleton instance
export const configService = ConfigService.getInstance();