import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/prisma';
import { retryWithBackoff } from '@/lib/retryUtils';

// POST /api/chats/[id]/messages - Add message to chat
export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const session = await getServerSession(authOptions);
    const { id: chatId } = await params;
    const body = await request.json();
    
    if (!session?.user?.email) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
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

    // Verify chat belongs to user
    const chat = await prisma.chat.findFirst({
      where: {
        id: chatId,
        userId: user.id
      }
    });

    if (!chat) {
      return new Response(JSON.stringify({ error: 'Chat not found' }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Validate message content length
    if (!body.content || body.content.length > 10000) {
      return new Response(JSON.stringify({ 
        error: 'Message content must be between 1 and 10,000 characters' 
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create message with retry logic
    const message = await retryWithBackoff(
      async () => {
        return await prisma.message.create({
          data: {
            chatId,
            role: body.role,
            content: body.content,
            references: body.references || []
          }
        });
      },
      {
        maxAttempts: 3,
        initialDelay: 1000,
        onRetry: (attempt, error) => {
          console.log(`Retrying message save (attempt ${attempt}/3)`, error.message);
        }
      }
    );

    // Update chat preview and timestamp with retry
    if (body.role === 'user' && !chat.preview) {
      await retryWithBackoff(
        async () => {
          return await prisma.chat.update({
            where: { id: chatId },
            data: {
              preview: body.content.substring(0, 100),
              title: chat.title || body.content.substring(0, 50) + '...'
            }
          });
        },
        { maxAttempts: 3, initialDelay: 500 }
      );
    } else if (body.role === 'assistant' && (!chat.title || chat.title === 'New Chat')) {
      // Generate smart title from assistant's first response
      // Extract a meaningful title from the content
      const content = body.content;
      let smartTitle = '';
      
      // Try to extract first sentence or meaningful phrase
      const firstSentence = content.match(/^[^.!?]+[.!?]/);
      if (firstSentence) {
        smartTitle = firstSentence[0].trim();
      } else {
        // If no sentence found, take first few words
        const words = content.split(' ').slice(0, 8);
        smartTitle = words.join(' ');
      }
      
      // Remove markdown formatting
      smartTitle = smartTitle.replace(/[*_#`\[\]()]/g, '');
      
      // Limit length and add ellipsis if needed
      if (smartTitle.length > 60) {
        smartTitle = smartTitle.substring(0, 57) + '...';
      }
      
      await prisma.chat.update({
        where: { id: chatId },
        data: {
          title: smartTitle,
          updatedAt: new Date()
        }
      });
    } else {
      // Just update the timestamp
      await prisma.chat.update({
        where: { id: chatId },
        data: { updatedAt: new Date() }
      });
    }

    return new Response(JSON.stringify(message), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    console.error('Error creating message:', error);
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}