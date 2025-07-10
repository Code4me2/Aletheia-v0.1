/**
 * Redis-based rate limiter for server-side use only.
 * This module uses Node.js APIs and cannot be used in Edge Runtime (middleware).
 * For middleware rate limiting, use the in-memory implementation.
 */
import Redis from 'ioredis';
import { config } from './config';

// Create Redis client with error handling
let redis: Redis | null = null;

try {
  redis = new Redis(config.redis.url, {
    retryStrategy: (times) => {
      // Reconnect after 2 seconds, max 10 attempts
      if (times > 10) return null;
      return Math.min(times * 200, 2000);
    },
    maxRetriesPerRequest: 3,
    enableOfflineQueue: false
  });

  redis.on('error', (err) => {
    console.error('Redis connection error:', err);
  });

  redis.on('connect', () => {
    console.log('Redis connected successfully');
  });
} catch (error) {
  console.error('Failed to initialize Redis:', error);
}

export class RateLimiter {
  private keyPrefix: string;
  private maxAttempts: number;
  private windowMs: number;
  // Fallback in-memory storage
  private memoryStore = new Map<string, { count: number; resetTime: number }>();

  constructor(keyPrefix: string, maxAttempts: number, windowMs: number) {
    this.keyPrefix = keyPrefix;
    this.maxAttempts = maxAttempts;
    this.windowMs = windowMs;
  }

  async checkLimit(identifier: string): Promise<{ allowed: boolean; remainingAttempts: number; resetAt: Date }> {
    // Check if Redis is available
    if (redis && redis.status === 'ready') {
      return this.checkLimitRedis(identifier);
    } else {
      // Fallback to in-memory
      return this.checkLimitMemory(identifier);
    }
  }

  private async checkLimitRedis(identifier: string): Promise<{ allowed: boolean; remainingAttempts: number; resetAt: Date }> {
    const key = `${this.keyPrefix}:${identifier}`;
    const now = Date.now();
    
    try {
      // Remove old entries
      await redis!.zremrangebyscore(key, '-inf', now - this.windowMs);
      
      // Count current attempts
      const attempts = await redis!.zcard(key);
      
      if (attempts >= this.maxAttempts) {
        const oldestAttempt = await redis!.zrange(key, 0, 0, 'WITHSCORES');
        const resetAt = oldestAttempt.length > 1 ? 
          new Date(parseInt(oldestAttempt[1]) + this.windowMs) : 
          new Date(now + this.windowMs);
        
        return {
          allowed: false,
          remainingAttempts: 0,
          resetAt
        };
      }
      
      // Add new attempt
      await redis!.zadd(key, now, `${now}-${Math.random()}`);
      await redis!.expire(key, Math.ceil(this.windowMs / 1000));
      
      return {
        allowed: true,
        remainingAttempts: this.maxAttempts - attempts - 1,
        resetAt: new Date(now + this.windowMs)
      };
    } catch (error) {
      console.error('Redis rate limit error:', error);
      // Fallback to memory
      return this.checkLimitMemory(identifier);
    }
  }

  private checkLimitMemory(identifier: string): { allowed: boolean; remainingAttempts: number; resetAt: Date } {
    const key = `${this.keyPrefix}:${identifier}`;
    const now = Date.now();
    const entry = this.memoryStore.get(key);

    if (!entry || now > entry.resetTime) {
      // New window
      this.memoryStore.set(key, { count: 1, resetTime: now + this.windowMs });
      return {
        allowed: true,
        remainingAttempts: this.maxAttempts - 1,
        resetAt: new Date(now + this.windowMs)
      };
    } else if (entry.count >= this.maxAttempts) {
      // Rate limit exceeded
      return {
        allowed: false,
        remainingAttempts: 0,
        resetAt: new Date(entry.resetTime)
      };
    } else {
      // Increment counter
      entry.count++;
      return {
        allowed: true,
        remainingAttempts: this.maxAttempts - entry.count,
        resetAt: new Date(entry.resetTime)
      };
    }
  }

  async reset(identifier: string): Promise<void> {
    const key = `${this.keyPrefix}:${identifier}`;
    
    if (redis && redis.status === 'ready') {
      try {
        await redis.del(key);
      } catch (error) {
        console.error('Redis reset error:', error);
      }
    }
    
    // Also clear from memory store
    this.memoryStore.delete(key);
  }

  // Clean up old entries from memory store
  cleanupMemory(): void {
    const now = Date.now();
    for (const [key, entry] of this.memoryStore.entries()) {
      if (now > entry.resetTime + this.windowMs) {
        this.memoryStore.delete(key);
      }
    }
  }
}

// Export pre-configured rate limiters
export const loginRateLimiter = new RateLimiter('login', 5, 15 * 60 * 1000); // 5 attempts per 15 minutes
export const apiRateLimiter = new RateLimiter('api', 100, 60 * 1000); // 100 requests per minute
export const emailRateLimiter = new RateLimiter('email', 3, 60 * 60 * 1000); // 3 emails per hour

// Cleanup interval for memory store
if (typeof window === 'undefined') {
  setInterval(() => {
    loginRateLimiter.cleanupMemory();
    apiRateLimiter.cleanupMemory();
    emailRateLimiter.cleanupMemory();
  }, 5 * 60 * 1000); // Every 5 minutes
}

// Export Redis client for health checks
export { redis };