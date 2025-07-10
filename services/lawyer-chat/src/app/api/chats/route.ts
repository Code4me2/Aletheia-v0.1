import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/prisma';
import type { Prisma } from '@/generated/prisma';

// Type helper for the chat query result
type ChatWithMessages = Prisma.ChatGetPayload<{
  include: {
    messages: {
      select: {
        id: true;
        role: true;
        content: true;
        createdAt: true;
      }
    };
    _count: {
      select: { messages: true }
    }
  }
}>;

// GET /api/chats - Fetch user's chat history with pagination
export async function GET(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    
    if (!session?.user?.email) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get pagination parameters from query string
    const { searchParams } = new URL(request.url);
    const limit = Math.min(Math.max(1, parseInt(searchParams.get('limit') || '50')), 100); // Limit between 1-100
    const offset = Math.max(0, parseInt(searchParams.get('offset') || '0'));
    const search = searchParams.get('search') || '';

    // Build where clause with optional search using email directly
    const whereClause: any = { 
      user: { email: session.user.email } 
    };
    if (search) {
      whereClause.OR = [
        { title: { contains: search, mode: 'insensitive' } },
        { preview: { contains: search, mode: 'insensitive' } }
      ];
    }

    // Get total count for pagination
    const totalCount = await prisma.chat.count({ where: whereClause });

    // Fetch user's chats with messages for title generation
    const chats = await prisma.chat.findMany({
      where: whereClause,
      orderBy: { updatedAt: 'desc' },
      include: {
        messages: {
          orderBy: { createdAt: 'asc' },
          take: 10, // Include first 10 messages for title generation
          select: {
            id: true,
            role: true,
            content: true,
            createdAt: true
            // Exclude references to reduce payload size
          }
        },
        _count: {
          select: { messages: true }
        }
      },
      take: limit,
      skip: offset
    });

    // Filter out invalid chats (no user message or no assistant response)
    const validChats = chats.filter((chat: ChatWithMessages) => {
      const hasUserMessage = chat.messages.some((m) => m.role === 'user');
      const hasAssistantMessage = chat.messages.some((m) => m.role === 'assistant');
      return hasUserMessage && hasAssistantMessage;
    });

    // For accurate pagination, we should ideally count valid chats in DB
    // For now, we'll use the total count as an approximation
    return new Response(JSON.stringify({
      chats: validChats,
      pagination: {
        total: totalCount, // Use original total count
        limit,
        offset,
        hasMore: offset + limit < totalCount
      }
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    // Use proper error logging in production
    if (process.env.NODE_ENV === 'development') {
      console.error('Error fetching chats:', error);
    }
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// POST /api/chats - Create new chat session
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

    // Create new chat using email directly
    const chat = await prisma.chat.create({
      data: {
        user: {
          connect: { email: session.user.email }
        },
        title: body.title || 'New Chat',
        preview: body.preview || ''
      }
    });

    return new Response(JSON.stringify(chat), {
      status: 201,
      headers: { 'Content-Type': 'application/json' }
    });
  } catch (error) {
    // Use proper error logging in production
    if (process.env.NODE_ENV === 'development') {
      console.error('Error creating chat:', error);
    }
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}