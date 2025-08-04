/**
 * Type-safe error handling utilities
 */

export interface ApiError {
  code: string;
  message: string;
  details?: unknown;
}

export interface PrismaError {
  code: string;
  clientVersion: string;
  meta?: {
    target?: string[];
    cause?: string;
  };
}

/**
 * Type guard for API errors
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'code' in error &&
    'message' in error &&
    typeof (error as any).code === 'string' &&
    typeof (error as any).message === 'string'
  );
}

/**
 * Type guard for Prisma errors
 */
export function isPrismaError(error: unknown): error is PrismaError {
  return (
    error !== null &&
    typeof error === 'object' &&
    'code' in error &&
    'clientVersion' in error &&
    typeof (error as any).code === 'string' &&
    typeof (error as any).clientVersion === 'string'
  );
}

/**
 * Type guard for standard Error objects
 */
export function isError(error: unknown): error is Error {
  return error instanceof Error;
}

/**
 * Safely extract error message from unknown error type
 */
export function getErrorMessage(error: unknown): string {
  if (isApiError(error)) {
    return error.message;
  }
  
  if (isPrismaError(error)) {
    return `Database error: ${error.code}`;
  }
  
  if (isError(error)) {
    return error.message;
  }
  
  if (typeof error === 'string') {
    return error;
  }
  
  return 'An unknown error occurred';
}

/**
 * Create a standardized API error response
 */
export function createApiError(message: string, code: string = 'UNKNOWN_ERROR', details?: unknown): ApiError {
  return {
    code,
    message,
    details
  };
}