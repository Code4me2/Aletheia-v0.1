/**
 * Router class for managing application navigation
 */

import type { Route, NavigationGuard } from '@/types/module.types';

type NavigationHandler = (route: Route) => Promise<void> | void;

export class Router {
  private routes: Map<string, Route> = new Map();
  private currentRoute: Route | null = null;
  private navigationHandler: NavigationHandler | null = null;
  private guards: NavigationGuard[] = [];

  constructor() {
    // Initialize with default home route
    this.addRoute({
      path: '/',
      moduleId: 'home',
    });
  }

  /**
   * Add a route to the router
   */
  public addRoute(route: Route): void {
    this.routes.set(route.path, route);
  }

  /**
   * Get all registered routes
   */
  public getRoutes(): Route[] {
    return Array.from(this.routes.values());
  }

  /**
   * Set the navigation handler
   */
  public onNavigate(handler: NavigationHandler): void {
    this.navigationHandler = handler;
  }

  /**
   * Add a navigation guard
   */
  public addGuard(guard: NavigationGuard): void {
    this.guards.push(guard);
  }

  /**
   * Navigate to a route
   */
  public async navigate(route: Route): Promise<boolean> {
    // Run navigation guards
    for (const guard of this.guards) {
      const canNavigate = await guard(route, this.currentRoute);
      if (!canNavigate) {
        return false;
      }
    }

    // Update browser URL without page reload
    const url = this.buildUrl(route);
    window.history.pushState({ route }, '', url);

    // Handle navigation
    if (this.navigationHandler) {
      await this.navigationHandler(route);
    }

    this.currentRoute = route;
    return true;
  }

  /**
   * Navigate back in history
   */
  public back(): void {
    window.history.back();
  }

  /**
   * Navigate forward in history
   */
  public forward(): void {
    window.history.forward();
  }

  /**
   * Get current route
   */
  public getCurrentRoute(): Route | null {
    return this.currentRoute;
  }

  /**
   * Handle current browser URL
   */
  public handleCurrentRoute(): void {
    const path = window.location.pathname;
    const route = this.matchRoute(path);
    
    if (route && this.navigationHandler) {
      this.navigationHandler(route);
      this.currentRoute = route;
    }
  }

  /**
   * Parse route from URL
   */
  public parseUrl(url: string): Route | null {
    const urlObj = new URL(url, window.location.origin);
    return this.matchRoute(urlObj.pathname);
  }

  /**
   * Build URL from route
   */
  private buildUrl(route: Route): string {
    let url = route.path;
    
    if (route.params) {
      const queryParams = new URLSearchParams(route.params as Record<string, string>).toString();
      if (queryParams) {
        url += `?${queryParams}`;
      }
    }
    
    return url;
  }

  /**
   * Match a path to a route
   */
  private matchRoute(path: string): Route | null {
    // Direct match
    if (this.routes.has(path)) {
      return this.routes.get(path)!;
    }

    // Try to match module ID from path
    const moduleId = path.replace(/^\//, '').split('/')[0];
    
    // If path is just the module ID, match it
    const modulePath = `/${moduleId}`;
    if (this.routes.has(modulePath)) {
      const route = this.routes.get(modulePath)!;
      
      // Extract any additional path segments as params
      const pathSegments = path.split('/').slice(2);
      if (pathSegments.length > 0) {
        return {
          ...route,
          params: {
            ...route.params,
            subpath: pathSegments.join('/'),
          },
        };
      }
      
      return route;
    }

    // Default to home if no match
    return this.routes.get('/') || null;
  }
}