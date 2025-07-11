/**
 * Retry utility with exponential backoff
 */

interface RetryOptions {
  maxAttempts?: number;
  initialDelay?: number;
  maxDelay?: number;
  backoffFactor?: number;
  onRetry?: (attempt: number, error: Error) => void;
}

/**
 * Retry a function with exponential backoff
 * @param fn The async function to retry
 * @param options Retry configuration options
 * @returns The result of the function if successful
 * @throws The last error if all retries fail
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<T> {
  const {
    maxAttempts = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    backoffFactor = 2,
    onRetry
  } = options;

  let lastError: Error;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));
      
      // Don't retry on certain errors
      if (isNonRetryableError(lastError)) {
        throw lastError;
      }
      
      if (attempt === maxAttempts) {
        throw lastError;
      }
      
      // Calculate delay with exponential backoff
      const delay = Math.min(
        initialDelay * Math.pow(backoffFactor, attempt - 1),
        maxDelay
      );
      
      // Call onRetry callback if provided
      if (onRetry) {
        onRetry(attempt, lastError);
      }
      
      // Wait before retrying
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
  
  throw lastError!;
}

/**
 * Determine if an error should not be retried
 */
function isNonRetryableError(error: Error): boolean {
  // Don't retry on validation errors (4xx status codes)
  if ('status' in error && typeof error.status === 'number') {
    return error.status >= 400 && error.status < 500;
  }
  
  // Don't retry on certain error messages
  const message = error.message.toLowerCase();
  if (
    message.includes('unauthorized') ||
    message.includes('forbidden') ||
    message.includes('not found') ||
    message.includes('bad request') ||
    message.includes('validation')
  ) {
    return true;
  }
  
  return false;
}

/**
 * Create a retryable version of a function
 */
export function makeRetryable<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options: RetryOptions = {}
): T {
  return (async (...args: Parameters<T>) => {
    return retryWithBackoff(() => fn(...args), options);
  }) as T;
}