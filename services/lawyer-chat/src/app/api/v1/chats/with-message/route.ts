import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/prisma';
import { retryWithBackoff } from '@/lib/retryUtils';
import type { Prisma } from '@prisma/client';

// POST /api/chats/with-message - Create chat with first message atomically
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    const body = await request.json();
    
    if (!session?.user?.email) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate input
    if (!body.message || typeof body.message !== 'string' || body.message.trim().length === 0) {
      return new Response(JSON.stringify({ error: 'Message content is required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get user from database
    const user = await prisma.user.findUnique({
      where: { email: session.user.email }
    });

    if (!user) {
      return new Response(JSON.stringify({ error: 'User not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create chat and first message in a transaction with retry
    const result = await retryWithBackoff(
      async () => {
        return await prisma.$transaction(async (tx: Prisma.TransactionClient) => {
          // Create the chat
          const chat = await tx.chat.create({
            data: {
              userId: user.id,
              title: body.title || 'New Chat',
              preview: body.message.substring(0, 100)
            }
          });

          // Create the first message
          const message = await tx.message.create({
            data: {
              chatId: chat.id,
              role: 'user',
              content: body.message,
              references: body.references || []
            }
          });

          return { chat, message };
        });
      },
      {
        maxAttempts: 3,
        initialDelay: 1000,
        onRetry: (attempt, error) => {
          console.log(`Retrying chat creation with message (attempt ${attempt}/3)`, error.message);
        }
      }
    );

    return new Response(JSON.stringify(result), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error creating chat with message:', error);
    
    // Check for specific database errors
    if (error instanceof Error && error.message.includes('P2002')) {
      return new Response(JSON.stringify({ error: 'Duplicate entry detected' }), {
        status: 409,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}