import { NextRequest, NextResponse } from 'next/server';
import { generateCsrfToken } from '@/utils/csrf';
import { createLogger } from '@/utils/logger';

const logger = createLogger('csrf-api');

// GET endpoint to generate CSRF token for frontend
export async function GET(request: NextRequest) {
  try {
    const token = await generateCsrfToken();
    
    return NextResponse.json({
      csrfToken: token
    });
  } catch (error) {
    logger.error('CSRF token generation error', error);
    return NextResponse.json(
      { error: 'Failed to generate CSRF token' },
      { status: 500 }
    );
  }
}