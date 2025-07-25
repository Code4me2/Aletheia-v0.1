import { NextRequest } from 'next/server';
import { validateMessage, sanitizeJson } from '@/utils/validation';
import { getAuthHeaders } from '@/utils/apiAuth';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { createLogger } from '@/utils/logger';
import { getErrorMessage } from '@/utils/errors';
import { ChatRequestSchema } from '@/schemas/api';
import { STREAM, API, CHAT, UI } from '@/config/constants';
import type { ChatResponse } from '@/types';

const logger = createLogger('chat-api');

export async function POST(request: NextRequest) {
  try {
    // Check if user is authenticated (required)
    const session = await getServerSession(authOptions);
    
    if (!session) {
      return new Response(JSON.stringify({ error: 'Authentication required' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const rawBody = await request.json();
    
    // Validate and parse request body with schema
    const parseResult = ChatRequestSchema.safeParse(rawBody);
    
    if (!parseResult.success) {
      return new Response(JSON.stringify({ 
        error: 'Invalid request body',
        details: parseResult.error.flatten()
      }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    
    const body = parseResult.data;
    
    // Validate and sanitize message
    const messageValidation = validateMessage(body.message);
    if (!messageValidation.isValid) {
      return new Response(JSON.stringify({ error: messageValidation.error }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const webhookUrl = process.env.N8N_WEBHOOK_URL;
    
    if (!webhookUrl) {
      logger.error('N8N_WEBHOOK_URL is not configured');
      return new Response(JSON.stringify({ error: 'Webhook URL not configured' }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Prepare payload for n8n webhook with sanitized data
    const payload = {
      action: 'public_chat',
      message: messageValidation.sanitized!,
      tools: body.tools.slice(0, 5), // Max 5 tools (already validated by schema)
      tool: 'default', // Keep for backward compatibility
      sessionKey: body.sessionKey || body.sessionId || session.user?.email || 'anonymous',
      sessionId: session.user?.email || body.sessionId,
      userId: session.user?.email || body.userId,
      timestamp: new Date().toISOString(),
      // Removed metadata to prevent information disclosure
    };

    logger.debug('Sending to n8n webhook', { webhookUrl, payload });

    // Get authentication headers
    const authHeaders = getAuthHeaders(payload);
    
    // Forward request to n8n webhook with authentication
    const response = await fetch(webhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        ...authHeaders
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      logger.error('Webhook response error', null, { 
        status: response.status, 
        statusText: response.statusText 
      });
      const errorText = await response.text();
      logger.error('Error details', null, { errorText });
      
      // If n8n webhook is not active, provide a fallback response
      if (response.status === 404 && errorText.includes('workflow must be active')) {
        logger.warn('n8n workflow is not active. Using fallback response');
        
        // Create a fallback streaming response
        const fallbackText = "I'm currently unable to connect to the AI service. Please ensure the n8n workflow is activated. \n\nTo fix this:\n1. Open n8n at http://localhost:5678\n2. Find the workflow with webhook ID: c188c31c-1c45-4118-9ece-5b6057ab5177\n3. Activate it using the toggle in the top-right\n\nFor testing, I can still demonstrate the UI features.";
        
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
          async start(controller) {
            // Stream the fallback message
            const chunkSize = STREAM.CHUNK_SIZE_CHARS;
            for (let i = 0; i < fallbackText.length; i += chunkSize) {
              const chunk = fallbackText.slice(i, Math.min(i + chunkSize, fallbackText.length));
              // Ensure chunk is properly encoded to prevent unicode issues
              const safeChunk = {
                text: chunk,
                type: 'text'
              };
              controller.enqueue(encoder.encode(`data: ${JSON.stringify(safeChunk)}\n\n`));
              await new Promise(resolve => setTimeout(resolve, STREAM.CHUNK_DELAY_MS));
            }
            
            // Add mock analytics if analytics tool was selected
            if (payload.tools?.includes('analytics')) {
              const mockAnalytics = {
                trends: [
                  { period: "Q1 2024", value: 156, category: "Contract Reviews" },
                  { period: "Q2 2024", value: 203, category: "Contract Reviews" }
                ],
                statistics: {
                  totalDocuments: 1247,
                  averageProcessingTime: "2.3 days",
                  successRate: "94.2%"
                },
                summary: "Analytics data (mock) - n8n workflow not active"
              };
              controller.enqueue(encoder.encode(`data: ${JSON.stringify({ analytics: mockAnalytics, type: 'analytics' })}\n\n`));
            }
            
            // Send done signal
            controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`));
            controller.close();
          }
        });
        
        return new Response(stream, {
          headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
          }
        });
      }
      
      return new Response(JSON.stringify({ 
        error: 'Failed to process message',
        details: errorText 
      }), {
        status: response.status,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Handle streaming response if needed
    const contentType = response.headers.get('content-type');
    logger.debug('Response content-type', { contentType });
    
    if (contentType?.includes('text/event-stream')) {
      // For streaming responses, pass through the stream
      return new Response(response.body, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache',
          'Connection': 'keep-alive'
        }
      });
    }
    
    // For non-streaming responses, convert to streaming for smooth display
    const responseText = await response.text();
    let responseData: ChatResponse;
    
    // Parse response based on content type
    if (contentType?.includes('text/html') || contentType?.includes('text/plain')) {
      // For text/html or text/plain responses from n8n
      responseData = { response: responseText.trim(), sources: [] };
    } else {
      try {
        responseData = JSON.parse(responseText);
      } catch {
        // Fallback for any unparseable response
        responseData = { response: responseText.trim(), sources: [] };
      }
    }
    
    // Create a streaming response for smooth character-by-character display
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        const text = responseData.message || responseData.response || 'I received your message. Processing...';
        const sources = responseData.sources || responseData.references || [];
        
        // Send text in chunks for smooth streaming effect
        const chunkSize = STREAM.CHUNK_SIZE_CHARS;
        for (let i = 0; i < text.length; i += chunkSize) {
          const chunk = text.slice(i, Math.min(i + chunkSize, text.length));
          // Ensure chunk is properly encoded to prevent unicode issues
          const safeChunk = {
            text: chunk,
            type: 'text'
          };
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(safeChunk)}\n\n`));
          
          // Small delay for typing effect (adjust as needed)
          await new Promise(resolve => setTimeout(resolve, STREAM.CHUNK_DELAY_MS));
        }
        
        // Send sources at the end
        if (sources.length > 0) {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify({ sources, type: 'sources' })}\n\n`));
        }
        
        // Send done signal
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done' })}\n\n`));
        controller.close();
      }
    });
    
    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive'
      }
    });

  } catch (error) {
    logger.error('API route error', getErrorMessage(error));
    
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      message: getErrorMessage(error)
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Optional: Add GET method for health check
export async function GET() {
  return new Response(JSON.stringify({ 
    status: 'ok',
    webhook: process.env.N8N_WEBHOOK_URL ? 'configured' : 'not configured'
  }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' }
  });
}