import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { checkCsrf } from '@/utils/csrf';
import { API_VERSION } from '@/lib/api-config';
import { SECURITY } from '@/config/constants';

// Simple in-memory rate limiter for Edge Runtime with size limit
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();
const MAX_RATE_LIMIT_ENTRIES = 10000; // Prevent unbounded growth

// Rate limit configuration
const RATE_LIMIT_WINDOW = SECURITY.RATE_LIMIT.EDGE_WINDOW_MS;
const RATE_LIMITS: Record<string, number> = {
  '/api/auth': 5,
  '/api/chat': 20,
  '/api/chats': 10,
  [`/api/${API_VERSION}/chat`]: 20,
  [`/api/${API_VERSION}/chats`]: 10,
  '/messages': 30,
  default: SECURITY.RATE_LIMIT.MAX_REQUESTS
};

export async function middleware(request: NextRequest) {
  const url = request.nextUrl;
  const pathname = url.pathname;

  // Handle legacy API redirects (non-auth endpoints)
  if (pathname.startsWith('/api/') && !pathname.startsWith('/api/auth/') && !pathname.startsWith(`/api/${API_VERSION}/`)) {
    // Check if this is a non-auth endpoint that should be redirected
    const legacyEndpoints = ['/api/chats', '/api/chat', '/api/admin', '/api/csrf'];
    const shouldRedirect = legacyEndpoints.some(endpoint => pathname.startsWith(endpoint));
    
    if (shouldRedirect) {
      // Redirect to versioned endpoint
      const versionedPath = pathname.replace('/api/', `/api/${API_VERSION}/`);
      url.pathname = versionedPath;
      return NextResponse.redirect(url);
    }
  }

  // Only apply to API routes
  if (!pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  // Skip CSRF for specific endpoints
  const csrfExemptPaths = [
    '/api/csrf', // CSRF token generation endpoint
    `/api/${API_VERSION}/csrf`, // Versioned CSRF endpoint
    '/api/auth/', // All NextAuth endpoints handle their own CSRF
    '/api/health' // Health check endpoint
  ];

  const path = pathname;

  // Check CSRF for state-changing requests (unless exempt)
  if (!csrfExemptPaths.some(exemptPath => path.startsWith(exemptPath))) {
    if (['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method)) {
      const csrfValid = await checkCsrf(request);
      
      if (!csrfValid) {
        return new NextResponse(
          JSON.stringify({ 
            error: 'Invalid or missing CSRF token',
            code: 'CSRF_TOKEN_INVALID'
          }),
          { 
            status: 403, 
            headers: { 'Content-Type': 'application/json' } 
          }
        );
      }
    }
  }

  // Get client identifier (IP or user ID)
  const ip = request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
  const key = `${ip}:${path}`;
  
  // Get rate limit for this endpoint
  let limit = RATE_LIMITS.default;
  for (const [route, routeLimit] of Object.entries(RATE_LIMITS)) {
    if (path.startsWith(route)) {
      limit = routeLimit;
      break;
    }
  }

  // Check rate limit
  const now = Date.now();
  const rateLimitInfo = rateLimitMap.get(key);

  if (!rateLimitInfo || now > rateLimitInfo.resetTime) {
    // New window
    // Check size limit before adding new entry
    if (rateLimitMap.size >= MAX_RATE_LIMIT_ENTRIES) {
      // Simple LRU: remove the oldest entry (first in map)
      const firstKey = rateLimitMap.keys().next().value;
      if (firstKey) {
        rateLimitMap.delete(firstKey);
      }
    }
    rateLimitMap.set(key, { count: 1, resetTime: now + RATE_LIMIT_WINDOW });
  } else if (rateLimitInfo.count >= limit) {
    // Rate limit exceeded
    return new NextResponse(
      JSON.stringify({ 
        error: 'Too many requests. Please try again later.',
        retryAfter: Math.ceil((rateLimitInfo.resetTime - now) / 1000)
      }),
      { 
        status: 429, 
        headers: { 
          'Content-Type': 'application/json',
          'X-RateLimit-Limit': limit.toString(),
          'X-RateLimit-Remaining': '0',
          'X-RateLimit-Reset': rateLimitInfo.resetTime.toString()
        } 
      }
    );
  } else {
    // Increment counter
    rateLimitInfo.count++;
  }

  // Add rate limit headers to response
  const response = NextResponse.next();
  const info = rateLimitMap.get(key)!;
  response.headers.set('X-RateLimit-Limit', limit.toString());
  response.headers.set('X-RateLimit-Remaining', (limit - info.count).toString());
  response.headers.set('X-RateLimit-Reset', info.resetTime.toString());

  return response;
}


// Clean up old entries periodically
declare global {
  var rateLimitCleanupInterval: NodeJS.Timeout | undefined;
}

if (typeof globalThis !== 'undefined' && !globalThis.rateLimitCleanupInterval) {
  globalThis.rateLimitCleanupInterval = setInterval(() => {
    const now = Date.now();
    for (const [key, info] of rateLimitMap.entries()) {
      if (now > info.resetTime + RATE_LIMIT_WINDOW) {
        rateLimitMap.delete(key);
      }
    }
  }, 5 * 60 * 1000); // Every 5 minutes
}

export const config = {
  matcher: '/api/:path*'
};