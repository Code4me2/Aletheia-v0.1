import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { checkCsrf } from '@/utils/csrf';

// Simple in-memory rate limiter (use Redis in production)
const rateLimitMap = new Map<string, { count: number; resetTime: number }>();

// Rate limit configuration
const RATE_LIMIT_WINDOW = 60 * 1000; // 1 minute
const MAX_REQUESTS = {
  '/api/chat': 20, // 20 messages per minute
  '/api/chats/[id]/messages': 30, // 30 message saves per minute (for streaming)
  '/api/chats': 10, // 10 new chats per minute
  '/api/auth': 5,  // 5 login attempts per minute
  default: 100     // 100 requests per minute for other endpoints
};

export async function middleware(request: NextRequest) {
  // Only apply to API routes
  if (!request.nextUrl.pathname.startsWith('/api')) {
    return NextResponse.next();
  }

  // Skip CSRF for specific endpoints
  const csrfExemptPaths = [
    '/api/csrf', // CSRF token generation endpoint
    '/api/auth/', // All NextAuth endpoints handle their own CSRF
    '/api/health' // Health check endpoint
  ];

  const path = request.nextUrl.pathname;

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
  const limit = Object.entries(MAX_REQUESTS).find(([route]) => 
    path.startsWith(route)
  )?.[1] || MAX_REQUESTS.default;

  // Check rate limit
  const now = Date.now();
  const rateLimitInfo = rateLimitMap.get(key);

  if (!rateLimitInfo || now > rateLimitInfo.resetTime) {
    // New window
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

// Clean up old entries periodically (every 5 minutes)
if (typeof window === 'undefined') {
  setInterval(() => {
    const now = Date.now();
    for (const [key, info] of rateLimitMap.entries()) {
      if (now > info.resetTime + RATE_LIMIT_WINDOW) {
        rateLimitMap.delete(key);
      }
    }
  }, 5 * 60 * 1000);
}

export const config = {
  matcher: '/api/:path*'
};