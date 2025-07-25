/**
 * API versioning configuration
 */

export const API_VERSION = 'v1';
export const API_BASE_PATH = `/api/${API_VERSION}`;

/**
 * Get versioned API endpoint
 */
export function getApiEndpoint(path: string): string {
  // Auth endpoints remain unversioned for compatibility
  if (path.startsWith('/auth')) {
    return `/api${path}`;
  }
  return `${API_BASE_PATH}${path}`;
}

/**
 * Get absolute API endpoint with base URL
 */
export function getAbsoluteApiEndpoint(path: string, baseUrl?: string): string {
  const endpoint = getApiEndpoint(path);
  if (baseUrl) {
    return `${baseUrl}${endpoint}`;
  }
  return endpoint;
}

/**
 * Check if a path is an API endpoint
 */
export function isApiEndpoint(path: string): boolean {
  return path.startsWith('/api/');
}

/**
 * Extract API version from path
 */
export function extractApiVersion(path: string): string | null {
  const match = path.match(/^\/api\/(v\d+)\//);
  return match ? match[1] : null;
}