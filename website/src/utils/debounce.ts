/**
 * Debounce and throttle utilities
 */

/**
 * Debounce function execution
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options?: {
    leading?: boolean;
    trailing?: boolean;
    maxWait?: number;
  }
): T & { cancel(): void; flush(): void } {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let previous = 0;
  let result: ReturnType<T>;
  
  const { leading = false, trailing = true, maxWait } = options || {};
  
  function debounced(this: any, ...args: Parameters<T>): ReturnType<T> {
    const now = Date.now();
    
    if (!previous && !leading) {
      previous = now;
    }
    
    const remaining = wait - (now - previous);
    
    const callFunc = () => {
      previous = leading ? Date.now() : 0;
      timeout = null;
      result = func.apply(this, args);
    };
    
    if (timeout) {
      clearTimeout(timeout);
    }
    
    if (maxWait && now - previous >= maxWait) {
      callFunc();
    } else if (remaining <= 0 || remaining > wait) {
      if (timeout) {
        clearTimeout(timeout);
        timeout = null;
      }
      previous = now;
      result = func.apply(this, args);
    } else if (trailing) {
      timeout = setTimeout(callFunc, remaining);
    }
    
    return result;
  }
  
  debounced.cancel = () => {
    if (timeout) {
      clearTimeout(timeout);
      timeout = null;
    }
    previous = 0;
  };
  
  debounced.flush = () => {
    if (timeout) {
      result = func.apply(undefined, [] as any);
      clearTimeout(timeout);
      timeout = null;
    }
    return result;
  };
  
  return debounced as any as T & { cancel(): void; flush(): void };
}

/**
 * Throttle function execution
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  wait: number,
  options?: {
    leading?: boolean;
    trailing?: boolean;
  }
): T & { cancel(): void } {
  const { leading = true, trailing = true } = options || {};
  
  return debounce(func, wait, {
    leading,
    trailing,
    maxWait: wait,
  });
}

/**
 * Request animation frame throttle
 */
export function rafThrottle<T extends (...args: any[]) => any>(
  func: T
): T & { cancel(): void } {
  let rafId: number | null = null;
  let lastArgs: Parameters<T> | null = null;
  
  function throttled(this: any, ...args: Parameters<T>): void {
    lastArgs = args;
    
    if (rafId === null) {
      rafId = requestAnimationFrame(() => {
        func.apply(this, lastArgs!);
        rafId = null;
      });
    }
  }
  
  throttled.cancel = () => {
    if (rafId !== null) {
      cancelAnimationFrame(rafId);
      rafId = null;
    }
  };
  
  return throttled as T & { cancel(): void };
}

/**
 * Create a debounced promise
 */
export function debouncePromise<T extends (...args: any[]) => Promise<any>>(
  func: T,
  wait: number
): T {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  let resolvePromise: ((value: any) => void) | null = null;
  let rejectPromise: ((reason: any) => void) | null = null;
  
  return function debounced(this: any, ...args: Parameters<T>): Promise<ReturnType<T>> {
    return new Promise((resolve, reject) => {
      if (timeout) {
        clearTimeout(timeout);
      }
      
      resolvePromise = resolve;
      rejectPromise = reject;
      
      timeout = setTimeout(async () => {
        try {
          const result = await func.apply(this, args);
          resolvePromise?.(result);
        } catch (error) {
          rejectPromise?.(error);
        }
      }, wait);
    });
  } as T;
}