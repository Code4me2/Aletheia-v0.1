/**
 * LocalStorage service with type safety and versioning
 */

import type { StorageAdapter } from '@/types/module.types';
import { configService } from '@services/config.service';

export class LocalStorageService implements StorageAdapter {
  private prefix: string;
  private version: number;

  constructor() {
    const config = configService.get('storage');
    this.prefix = config.prefix;
    this.version = config.version;
  }

  /**
   * Get item from storage
   */
  public get<T>(key: string): T | null {
    try {
      const fullKey = this.getFullKey(key);
      const item = localStorage.getItem(fullKey);
      
      if (!item) {
        return null;
      }
      
      const parsed = JSON.parse(item);
      
      // Check version
      if (parsed.version !== this.version) {
        // Version mismatch, remove old data
        this.remove(key);
        return null;
      }
      
      // Check expiration
      if (parsed.expires && parsed.expires < Date.now()) {
        this.remove(key);
        return null;
      }
      
      return parsed.data as T;
    } catch (error) {
      console.error(`Failed to get item "${key}" from localStorage:`, error);
      return null;
    }
  }

  /**
   * Set item in storage
   */
  public set<T>(key: string, value: T, ttl?: number): void {
    try {
      const fullKey = this.getFullKey(key);
      const data = {
        version: this.version,
        data: value,
        timestamp: Date.now(),
        expires: ttl ? Date.now() + ttl : null,
      };
      
      localStorage.setItem(fullKey, JSON.stringify(data));
    } catch (error) {
      console.error(`Failed to set item "${key}" in localStorage:`, error);
      
      // Handle quota exceeded error
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        this.clearOldItems();
        
        // Try again
        try {
          const fullKey = this.getFullKey(key);
          localStorage.setItem(fullKey, JSON.stringify({
            version: this.version,
            data: value,
            timestamp: Date.now(),
            expires: ttl ? Date.now() + ttl : null,
          }));
        } catch (retryError) {
          console.error('Failed to set item after clearing old items:', retryError);
        }
      }
    }
  }

  /**
   * Remove item from storage
   */
  public remove(key: string): void {
    try {
      const fullKey = this.getFullKey(key);
      localStorage.removeItem(fullKey);
    } catch (error) {
      console.error(`Failed to remove item "${key}" from localStorage:`, error);
    }
  }

  /**
   * Clear all items with current prefix
   */
  public clear(): void {
    try {
      const keysToRemove: string[] = [];
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.prefix)) {
          keysToRemove.push(key);
        }
      }
      
      keysToRemove.forEach(key => localStorage.removeItem(key));
    } catch (error) {
      console.error('Failed to clear localStorage:', error);
    }
  }

  /**
   * Check if key exists
   */
  public has(key: string): boolean {
    const fullKey = this.getFullKey(key);
    return localStorage.getItem(fullKey) !== null;
  }

  /**
   * Get all keys with current prefix
   */
  public keys(): string[] {
    const keys: string[] = [];
    const prefixLength = this.prefix.length + 1; // +1 for underscore
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.prefix)) {
        // Remove prefix and version suffix
        const cleanKey = key.substring(prefixLength).replace(/_v\d+$/, '');
        keys.push(cleanKey);
      }
    }
    
    return keys;
  }

  /**
   * Get storage size in bytes
   */
  public getSize(): number {
    let size = 0;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.prefix)) {
        const value = localStorage.getItem(key);
        if (value) {
          size += key.length + value.length;
        }
      }
    }
    
    return size;
  }

  /**
   * Private methods
   */

  private getFullKey(key: string): string {
    return `${this.prefix}_${key}_v${this.version}`;
  }

  private clearOldItems(): void {
    const items: Array<{ key: string; timestamp: number }> = [];
    
    // Collect items with timestamps
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key.startsWith(this.prefix)) {
        try {
          const value = localStorage.getItem(key);
          if (value) {
            const parsed = JSON.parse(value);
            if (parsed.timestamp) {
              items.push({ key, timestamp: parsed.timestamp });
            }
          }
        } catch {
          // Ignore parse errors
        }
      }
    }
    
    // Sort by timestamp (oldest first)
    items.sort((a, b) => a.timestamp - b.timestamp);
    
    // Remove oldest 25% of items
    const removeCount = Math.floor(items.length * 0.25);
    for (let i = 0; i < removeCount; i++) {
      localStorage.removeItem(items[i]!.key);
    }
  }
}

// Export singleton instance
export const localStorageService = new LocalStorageService();