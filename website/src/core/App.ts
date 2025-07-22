/**
 * Core application class for Data Compose
 * Manages module lifecycle, navigation, and global state
 */

import type { AppModule, ModuleManifest, Route } from '@/types/module.types';
import { Router } from './Router';
import { EventBus } from './EventBus';
import { ServiceRegistry } from './ServiceRegistry';
import { configService } from '@services/config.service';

export class DataComposeApp {
  private modules: Map<string, AppModule> = new Map();
  private currentModule: AppModule | null = null;
  private router: Router;
  private eventBus: EventBus;
  private serviceRegistry: ServiceRegistry;
  private container: HTMLElement | null = null;
  private initialized = false;

  constructor() {
    this.router = new Router();
    this.eventBus = new EventBus();
    this.serviceRegistry = new ServiceRegistry();
    
    // Register core services
    this.serviceRegistry.register('config', configService);
    this.serviceRegistry.register('eventBus', this.eventBus);
    this.serviceRegistry.register('router', this.router);
  }

  /**
   * Initialize the application
   */
  public async init(): Promise<void> {
    if (this.initialized) {
      console.warn('Application already initialized');
      return;
    }

    try {
      // Find main content container
      this.container = document.querySelector('.app-main');
      if (!this.container) {
        throw new Error('Main container not found');
      }

      // Set up navigation
      this.setupNavigation();
      
      // Initialize all registered modules
      await this.initializeModules();
      
      // Handle initial route
      this.router.handleCurrentRoute();
      
      this.initialized = true;
      
      // Emit app ready event
      this.eventBus.emit('app:ready', { timestamp: Date.now() });
      
      console.log('Data Compose Application initialized');
    } catch (error) {
      console.error('Failed to initialize application:', error);
      throw error;
    }
  }

  /**
   * Register a module with the application
   */
  public async registerModule(manifest: ModuleManifest): Promise<void> {
    const { module: ModuleClass, config } = manifest;
    
    try {
      const moduleInstance = new ModuleClass(config);
      
      // Check for duplicate module ID
      if (this.modules.has(moduleInstance.id)) {
        throw new Error(`Module with ID "${moduleInstance.id}" already registered`);
      }
      
      // Register module
      this.modules.set(moduleInstance.id, moduleInstance);
      
      // Register route
      this.router.addRoute({
        path: `/${moduleInstance.id}`,
        moduleId: moduleInstance.id,
      });
      
      // Initialize if app is already initialized
      if (this.initialized) {
        await moduleInstance.init();
      }
      
      console.log(`Module "${moduleInstance.name}" registered`);
    } catch (error) {
      console.error('Failed to register module:', error);
      throw error;
    }
  }

  /**
   * Get a registered service
   */
  public getService<T>(name: string): T {
    return this.serviceRegistry.get<T>(name);
  }

  /**
   * Get the event bus instance
   */
  public getEventBus(): EventBus {
    return this.eventBus;
  }

  /**
   * Navigate to a specific module/section
   */
  public async navigateTo(moduleId: string, params?: Record<string, string>): Promise<void> {
    const route: Route = {
      path: `/${moduleId}`,
      moduleId,
      params,
    };
    
    await this.router.navigate(route);
  }

  /**
   * Get current active module
   */
  public getCurrentModule(): AppModule | null {
    return this.currentModule;
  }

  /**
   * Get all registered modules
   */
  public getModules(): Map<string, AppModule> {
    return new Map(this.modules);
  }

  /**
   * Add a new section dynamically (for backward compatibility)
   */
  public addSection(
    id: string,
    title: string,
    icon: string,
    contentHtml: string,
    handlers: Partial<AppModule> = {}
  ): void {
    // Create a simple module wrapper
    const DynamicModule = class implements AppModule {
      id = id;
      name = title;
      icon = icon;
      version = '1.0.0';

      async init(): Promise<void> {
        if (handlers.init) {
          await handlers.init.call(this);
        }
      }

      mount(container: HTMLElement): void {
        // Create section element
        const section = document.createElement('section');
        section.id = id;
        section.className = 'content-section';
        section.innerHTML = contentHtml;
        container.appendChild(section);
        
        // Call mount handler if provided
        if (handlers.mount) {
          handlers.mount.call(this, container);
        }
      }

      unmount(): void {
        const section = document.getElementById(id);
        if (section) {
          section.remove();
        }
        
        if (handlers.unmount) {
          handlers.unmount.call(this);
        }
      }

      onNavigate(params: Record<string, string>): void {
        if (handlers.onNavigate) {
          handlers.onNavigate.call(this, params);
        }
      }
    };

    // Register the dynamic module
    this.registerModule({
      module: DynamicModule,
    });

    // Add navigation tab
    this.addNavigationTab(id, title, icon);
  }

  /**
   * Private methods
   */

  private async initializeModules(): Promise<void> {
    const initPromises = Array.from(this.modules.values()).map((module) =>
      module.init().catch((error) => {
        console.error(`Failed to initialize module "${module.name}":`, error);
      })
    );
    
    await Promise.all(initPromises);
  }

  private setupNavigation(): void {
    // Set up router navigation handler
    this.router.onNavigate(async (route: Route) => {
      await this.handleNavigation(route);
    });

    // Set up nav tab click handlers
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach((tab) => {
      tab.addEventListener('click', async (e) => {
        e.preventDefault();
        const sectionId = tab.getAttribute('data-section');
        if (sectionId) {
          await this.navigateTo(sectionId);
        }
      });
    });

    // Handle browser back/forward
    window.addEventListener('popstate', () => {
      this.router.handleCurrentRoute();
    });
  }

  private async handleNavigation(route: Route): Promise<void> {
    const module = this.modules.get(route.moduleId);
    if (!module || !this.container) {
      console.error(`Module "${route.moduleId}" not found`);
      return;
    }

    // Check if current module can be deactivated
    if (this.currentModule && this.currentModule.canNavigateAway) {
      const canLeave = await this.currentModule.canNavigateAway();
      if (!canLeave) {
        return;
      }
    }

    // Emit navigation event
    this.eventBus.emit('navigation:before', { from: this.currentModule?.id, to: route.moduleId });

    // Unmount current module
    if (this.currentModule) {
      this.currentModule.unmount();
    }

    // Update UI state
    this.updateNavigationUI(route.moduleId);

    // Mount new module
    module.mount(this.container);
    
    // Call navigation handler
    if (module.onNavigate && route.params) {
      module.onNavigate(route.params);
    }

    this.currentModule = module;

    // Emit navigation complete event
    this.eventBus.emit('navigation:after', { moduleId: route.moduleId });
  }

  private updateNavigationUI(activeModuleId: string): void {
    // Update nav tabs
    document.querySelectorAll('.nav-tab').forEach((tab) => {
      const sectionId = tab.getAttribute('data-section');
      if (sectionId === activeModuleId) {
        tab.classList.add('active');
      } else {
        tab.classList.remove('active');
      }
    });

    // Hide all content sections
    document.querySelectorAll('.content-section').forEach((section) => {
      section.classList.remove('active');
    });
  }

  private addNavigationTab(id: string, title: string, icon: string): void {
    const navTabs = document.querySelector('.nav-tabs');
    if (!navTabs) return;

    const newTab = document.createElement('button');
    newTab.className = 'nav-tab';
    newTab.setAttribute('data-section', id);
    newTab.innerHTML = `<i class="${icon}"></i> ${title}`;
    
    newTab.addEventListener('click', async (e) => {
      e.preventDefault();
      await this.navigateTo(id);
    });
    
    navTabs.appendChild(newTab);
  }
}

// Export singleton instance
let appInstance: DataComposeApp | null = null;

export function createApp(): DataComposeApp {
  if (!appInstance) {
    appInstance = new DataComposeApp();
  }
  return appInstance;
}

export function getApp(): DataComposeApp {
  if (!appInstance) {
    throw new Error('App not initialized. Call createApp() first.');
  }
  return appInstance;
}