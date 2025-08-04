import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import prisma from '@/lib/prisma';
import type { Prisma } from '@prisma/client';
import { z } from 'zod';
import { getErrorMessage, isPrismaError } from '@/utils/errors';

// Query parameter validation schema
const QuerySchema = z.object({
  limit: z.coerce.number().min(1).max(100).default(50),
  offset: z.coerce.number().min(0).default(0),
  search: z.string().optional()
});

// POST body validation schema
const CreateChatSchema = z.object({
  title: z.string().min(1).max(200).default('New Chat')
});

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

    // Get pagination parameters from query string with validation
    const { searchParams } = new URL(request.url);
    
    // Validate and parse query parameters
    const queryResult = QuerySchema.safeParse({
      limit: searchParams.get('limit'),
      offset: searchParams.get('offset'),
      search: searchParams.get('search')
    });
    
    if (!queryResult.success) {
      return new Response(JSON.stringify({ 
        error: 'Invalid query parameters', 
        details: queryResult.error.flatten() 
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const { limit, offset, search } = queryResult.data;

    // Build where clause with optional search using email directly
    const whereClause: Prisma.ChatWhereInput = { 
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
      console.error('Error fetching chats:', getErrorMessage(error));
    }
    
    // Provide more specific error messages for known error types
    if (isPrismaError(error)) {
      return new Response(JSON.stringify({ 
        error: 'Database error occurred',
        code: error.code 
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
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
    
    if (!session?.user?.email) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = await request.json();
    
    // Validate request body
    const bodyResult = CreateChatSchema.safeParse(body);
    
    if (!bodyResult.success) {
      return new Response(JSON.stringify({ 
        error: 'Invalid request body', 
        details: bodyResult.error.flatten() 
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create new chat using email directly
    const chat = await prisma.chat.create({
      data: {
        user: {
          connect: { email: session.user.email }
        },
        title: bodyResult.data.title,
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
      console.error('Error creating chat:', getErrorMessage(error));
    }
    
    // Provide more specific error messages for known error types
    if (isPrismaError(error)) {
      return new Response(JSON.stringify({ 
        error: 'Database error occurred',
        code: error.code 
      }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    return new Response(JSON.stringify({ error: 'Internal server error' }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}