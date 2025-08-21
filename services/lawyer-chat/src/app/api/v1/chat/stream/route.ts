import { NextRequest } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { createLogger } from '@/utils/logger';

const logger = createLogger('chat-stream-api');

// SSE endpoint for streaming chat responses with progress
export async function GET(request: NextRequest) {
  try {
    // Check authentication
    const session = await getServerSession(authOptions);
    if (!session) {
      return new Response(JSON.stringify({ error: 'Authentication required' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Get execution ID from query params
    const searchParams = request.nextUrl.searchParams;
    const executionId = searchParams.get('executionId');
    const message = searchParams.get('message');
    
    if (!executionId && !message) {
      return new Response(JSON.stringify({ error: 'executionId or message required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    // Create SSE stream
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        // Helper to send SSE events
        const sendEvent = (data: any) => {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
        };

        try {
          // Send initial status
          sendEvent({
            type: 'status',
            stage: 'initializing',
            message: 'Preparing to process your request...'
          });

          // If we have a message, trigger n8n workflow first
          if (message) {
            sendEvent({
              type: 'status',
              stage: 'analyzing_context',
              message: 'Analyzing your query...'
            });

            // TODO: Call n8n webhook and get execution ID
            const webhookUrl = process.env.N8N_WEBHOOK_URL;
            if (!webhookUrl) {
              throw new Error('Webhook URL not configured');
            }

            // Simulate processing stages with realistic timing
            const stages = [
              { stage: 'analyzing_context', message: 'Understanding your request...', delay: 1000 },
              { stage: 'retrieving_documents', message: 'Searching relevant information...', delay: 2000 },
              { stage: 'processing_query', message: 'Processing with AI model...', delay: 3000 },
              { stage: 'generating_response', message: 'Generating response...', delay: 2000 }
            ];

            let totalProgress = 0;
            for (const stageInfo of stages) {
              await new Promise(resolve => setTimeout(resolve, stageInfo.delay));
              totalProgress += 25;
              
              sendEvent({
                type: 'progress',
                stage: stageInfo.stage,
                message: stageInfo.message,
                percent: totalProgress
              });
            }

            // Send mock response text in chunks
            const mockResponse = "Based on the analysis, I can help you with that request. Here's what I found...";
            const words = mockResponse.split(' ');
            
            for (let i = 0; i < words.length; i++) {
              sendEvent({
                type: 'text',
                text: words[i] + ' '
              });
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          }

          // If monitoring existing execution
          if (executionId && !message) {
            // TODO: Poll n8n execution status
            sendEvent({
              type: 'status',
              stage: 'processing_query',
              message: `Monitoring execution ${executionId}...`
            });
          }

          // Send completion
          sendEvent({
            type: 'done',
            totalTime: 8000
          });

        } catch (error: any) {
          logger.error('Stream error', error);
          sendEvent({
            type: 'error',
            message: error.message || 'An error occurred'
          });
        } finally {
          controller.close();
        }
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Content-Type-Options': 'nosniff'
      }
    });

  } catch (error: any) {
    logger.error('SSE endpoint error', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// POST endpoint to trigger workflow and return execution ID
export async function POST(request: NextRequest) {
  try {
    const session = await getServerSession(authOptions);
    if (!session) {
      return new Response(JSON.stringify({ error: 'Authentication required' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' }
      });
    }

    const body = await request.json();
    
    // Trigger n8n workflow
    const webhookUrl = process.env.N8N_WEBHOOK_URL;
    if (!webhookUrl) {
      throw new Error('Webhook URL not configured');
    }

    // For now, return a mock execution ID
    // TODO: Actually trigger n8n and get real execution ID
    const executionId = `exec_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

    return new Response(JSON.stringify({ 
      executionId,
      streamUrl: `/api/v1/chat/stream?executionId=${executionId}`
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });

  } catch (error: any) {
    logger.error('POST endpoint error', error);
    return new Response(JSON.stringify({ 
      error: 'Internal server error',
      message: error.message
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}