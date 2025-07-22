/**
 * Event bus for application-wide event handling
 */

import type { AppEvent, EventHandler, EventSubscription } from '@/types/module.types';

interface EventHandlerEntry {
  handler: EventHandler;
  once: boolean;
}

export class EventBus {
  private events: Map<string, EventHandlerEntry[]> = new Map();
  private eventHistory: AppEvent[] = [];
  private maxHistorySize = 100;

  /**
   * Subscribe to an event
   */
  public on<T = unknown>(eventType: string, handler: EventHandler<T>): EventSubscription {
    return this.addHandler(eventType, handler as EventHandler, false);
  }

  /**
   * Subscribe to an event once
   */
  public once<T = unknown>(eventType: string, handler: EventHandler<T>): EventSubscription {
    return this.addHandler(eventType, handler as EventHandler, true);
  }

  /**
   * Emit an event
   */
  public async emit<T = unknown>(eventType: string, payload?: T, source?: string): Promise<void> {
    const event: AppEvent<T> = {
      type: eventType,
      payload,
      timestamp: Date.now(),
      source,
    };

    // Add to history
    this.addToHistory(event);

    // Get handlers for this event type
    const handlers = this.events.get(eventType);
    if (!handlers || handlers.length === 0) {
      return;
    }

    // Execute handlers
    const handlersToRemove: number[] = [];
    
    await Promise.all(
      handlers.map(async (entry, index) => {
        try {
          await entry.handler(event);
          
          // Mark once handlers for removal
          if (entry.once) {
            handlersToRemove.push(index);
          }
        } catch (error) {
          console.error(`Error in event handler for "${eventType}":`, error);
        }
      })
    );

    // Remove once handlers
    if (handlersToRemove.length > 0) {
      const remainingHandlers = handlers.filter((_, index) => !handlersToRemove.includes(index));
      
      if (remainingHandlers.length > 0) {
        this.events.set(eventType, remainingHandlers);
      } else {
        this.events.delete(eventType);
      }
    }
  }

  /**
   * Remove all handlers for an event type
   */
  public off(eventType: string): void {
    this.events.delete(eventType);
  }

  /**
   * Remove all event handlers
   */
  public clear(): void {
    this.events.clear();
  }

  /**
   * Get event history
   */
  public getHistory(eventType?: string): AppEvent[] {
    if (eventType) {
      return this.eventHistory.filter(event => event.type === eventType);
    }
    return [...this.eventHistory];
  }

  /**
   * Clear event history
   */
  public clearHistory(): void {
    this.eventHistory = [];
  }

  /**
   * Get registered event types
   */
  public getEventTypes(): string[] {
    return Array.from(this.events.keys());
  }

  /**
   * Check if event type has handlers
   */
  public hasHandlers(eventType: string): boolean {
    const handlers = this.events.get(eventType);
    return !!handlers && handlers.length > 0;
  }

  /**
   * Create a scoped event emitter
   */
  public createScoped(scope: string): ScopedEventBus {
    return new ScopedEventBus(this, scope);
  }

  /**
   * Private methods
   */

  private addHandler(eventType: string, handler: EventHandler, once: boolean): EventSubscription {
    const handlers = this.events.get(eventType) || [];
    const entry: EventHandlerEntry = { handler, once };
    
    handlers.push(entry);
    this.events.set(eventType, handlers);

    // Return subscription object
    return {
      unsubscribe: () => {
        const currentHandlers = this.events.get(eventType);
        if (currentHandlers) {
          const index = currentHandlers.indexOf(entry);
          if (index > -1) {
            currentHandlers.splice(index, 1);
            
            if (currentHandlers.length === 0) {
              this.events.delete(eventType);
            }
          }
        }
      },
    };
  }

  private addToHistory(event: AppEvent): void {
    this.eventHistory.push(event);
    
    // Trim history if needed
    if (this.eventHistory.length > this.maxHistorySize) {
      this.eventHistory = this.eventHistory.slice(-this.maxHistorySize);
    }
  }
}

/**
 * Scoped event bus for module-specific events
 */
export class ScopedEventBus {
  constructor(
    private parent: EventBus,
    private scope: string
  ) {}

  public on<T = unknown>(eventType: string, handler: EventHandler<T>): EventSubscription {
    return this.parent.on(this.scopedType(eventType), handler);
  }

  public once<T = unknown>(eventType: string, handler: EventHandler<T>): EventSubscription {
    return this.parent.once(this.scopedType(eventType), handler);
  }

  public async emit<T = unknown>(eventType: string, payload?: T): Promise<void> {
    await this.parent.emit(this.scopedType(eventType), payload, this.scope);
  }

  public off(eventType: string): void {
    this.parent.off(this.scopedType(eventType));
  }

  private scopedType(eventType: string): string {
    return `${this.scope}:${eventType}`;
  }
}