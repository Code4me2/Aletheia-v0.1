/**
 * Service registry for dependency injection
 */

import type { ServiceConstructor, ServiceDefinition } from '@/types/module.types';

interface ServiceEntry {
  definition: ServiceDefinition;
  instance?: unknown;
}

export class ServiceRegistry {
  private services: Map<string, ServiceEntry> = new Map();
  private resolving: Set<string> = new Set();

  /**
   * Register a service instance
   */
  public register<T>(name: string, instance: T): void {
    this.services.set(name, {
      definition: {
        name,
        service: (instance as any).constructor as ServiceConstructor<T>,
        singleton: true,
      },
      instance,
    });
  }

  /**
   * Register a service definition
   */
  public registerDefinition(definition: ServiceDefinition): void {
    if (this.services.has(definition.name)) {
      throw new Error(`Service "${definition.name}" is already registered`);
    }

    this.services.set(definition.name, { definition });
  }

  /**
   * Get a service instance
   */
  public get<T>(name: string): T {
    const entry = this.services.get(name);
    if (!entry) {
      throw new Error(`Service "${name}" not found`);
    }

    // Return existing instance if available
    if (entry.instance) {
      return entry.instance as T;
    }

    // Create new instance
    const instance = this.createInstance<T>(entry.definition);

    // Store instance if singleton
    if (entry.definition.singleton !== false) {
      entry.instance = instance;
    }

    return instance;
  }

  /**
   * Check if a service is registered
   */
  public has(name: string): boolean {
    return this.services.has(name);
  }

  /**
   * Get all registered service names
   */
  public getServiceNames(): string[] {
    return Array.from(this.services.keys());
  }

  /**
   * Clear all services
   */
  public clear(): void {
    this.services.clear();
    this.resolving.clear();
  }

  /**
   * Create an instance with dependency injection
   */
  private createInstance<T>(definition: ServiceDefinition): T {
    // Check for circular dependencies
    if (this.resolving.has(definition.name)) {
      throw new Error(`Circular dependency detected for service "${definition.name}"`);
    }

    this.resolving.add(definition.name);

    try {
      // Resolve dependencies
      const dependencies: unknown[] = [];
      
      if (definition.dependencies) {
        for (const depName of definition.dependencies) {
          dependencies.push(this.get(depName));
        }
      }

      // Create instance
      const ServiceClass = definition.service as ServiceConstructor<T>;
      const instance = new ServiceClass(...dependencies);

      return instance;
    } finally {
      this.resolving.delete(definition.name);
    }
  }

  /**
   * Create a scoped registry
   */
  public createScoped(): ServiceRegistry {
    const scoped = new ServiceRegistry();
    
    // Copy service definitions (not instances)
    for (const [name, entry] of this.services) {
      scoped.services.set(name, {
        definition: entry.definition,
        // Only copy singleton instances
        instance: entry.definition.singleton !== false ? entry.instance : undefined,
      });
    }
    
    return scoped;
  }
}