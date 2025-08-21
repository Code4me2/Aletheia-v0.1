import { NextRequest } from 'next/server';

// Test endpoint to demonstrate SSE progress streaming
export async function GET(request: NextRequest) {
  const encoder = new TextEncoder();
  
  const stream = new ReadableStream({
    async start(controller) {
      const sendEvent = (data: any) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(data)}\n\n`));
      };

      // Simulate realistic workflow stages
      const stages = [
        { 
          type: 'status',
          stage: 'initializing',
          message: 'Starting workflow execution...',
          delay: 500
        },
        {
          type: 'progress',
          stage: 'initializing',
          message: 'Loading configuration...',
          percent: 10,
          delay: 800
        },
        {
          type: 'status',
          stage: 'analyzing_context',
          message: 'Analyzing document context...',
          delay: 1000
        },
        {
          type: 'progress',
          stage: 'analyzing_context',
          message: 'Processing 3 selected documents...',
          percent: 25,
          delay: 1500
        },
        {
          type: 'status',
          stage: 'retrieving_documents',
          message: 'Searching knowledge base...',
          delay: 1000
        },
        {
          type: 'progress',
          stage: 'retrieving_documents',
          message: 'Found 15 relevant documents...',
          percent: 40,
          delay: 1200
        },
        {
          type: 'status',
          stage: 'processing_query',
          message: 'Processing with AI model...',
          delay: 1500
        },
        {
          type: 'progress',
          stage: 'processing_query',
          message: 'Analyzing legal precedents...',
          percent: 60,
          delay: 2000
        },
        {
          type: 'status',
          stage: 'generating_response',
          message: 'Generating response...',
          delay: 1000
        },
        {
          type: 'progress',
          stage: 'generating_response',
          message: 'Formatting citations...',
          percent: 75,
          delay: 800
        }
      ];

      // Send stages with delays
      for (const stage of stages) {
        await new Promise(resolve => setTimeout(resolve, stage.delay));
        const { delay, ...eventData } = stage;
        sendEvent(eventData);
      }

      // Stream text response
      const response = "Based on the selected court documents and relevant legal precedents, here's my analysis of the case. The court's ruling in Gilstrap's opinion establishes clear guidelines for patent eligibility under 35 U.S.C. § 101.";
      const words = response.split(' ');
      
      for (let i = 0; i < words.length; i++) {
        sendEvent({
          type: 'text',
          text: words[i] + ' '
        });
        await new Promise(resolve => setTimeout(resolve, 50 + Math.random() * 50));
        
        // Update progress during text generation
        if (i % 10 === 0) {
          const percent = 75 + Math.floor((i / words.length) * 20);
          sendEvent({
            type: 'progress',
            stage: 'generating_response',
            message: 'Writing response...',
            percent: Math.min(percent, 95)
          });
        }
      }

      // Finalizing
      await new Promise(resolve => setTimeout(resolve, 500));
      sendEvent({
        type: 'status',
        stage: 'finalizing',
        message: 'Complete!',
      });
      
      sendEvent({
        type: 'progress',
        stage: 'finalizing',
        message: 'Response delivered successfully',
        percent: 100
      });

      // Add mock sources
      sendEvent({
        type: 'sources',
        sources: [
          'Gilstrap Opinion - Case 2:17-CV-00141',
          'Federal Circuit Precedent Database',
          'USPTO Patent Guidelines 2024'
        ]
      });

      // Done
      sendEvent({
        type: 'done',
        totalTime: 12500
      });

      controller.close();
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
}