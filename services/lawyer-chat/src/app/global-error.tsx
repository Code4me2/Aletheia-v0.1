'use client';

import { useEffect } from 'react';
import { createLogger } from '@/utils/logger';

const logger = createLogger('global-error-root');

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    logger.error('Root global error boundary caught error', error, {
      digest: error.digest,
      critical: true
    });
  }, [error]);

  // Global error boundary requires html and body tags
  return (
    <html>
      <body>
        <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      backgroundColor: '#f3f4f6'
    }}>
      <div style={{
        maxWidth: '500px',
        width: '100%',
        backgroundColor: 'white',
        borderRadius: '8px',
        padding: '40px',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        textAlign: 'center'
      }}>
        <h1 style={{
          fontSize: '24px',
          fontWeight: 'bold',
          color: '#111827',
          marginBottom: '16px'
        }}>
          Critical Application Error
        </h1>
        
        <p style={{
          fontSize: '16px',
          color: '#6b7280',
          marginBottom: '32px'
        }}>
          The application encountered a critical error and cannot continue. 
          Please refresh the page or contact support if the problem persists.
        </p>

        <div style={{ display: 'flex', gap: '16px', justifyContent: 'center' }}>
          <button
            onClick={reset}
            style={{
              padding: '12px 24px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Try Again
          </button>
          
          <button
            onClick={() => window.location.href = '/'}
            style={{
              padding: '12px 24px',
              backgroundColor: '#e5e7eb',
              color: '#374151',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: '500',
              cursor: 'pointer'
            }}
          >
            Go Home
          </button>
        </div>

        {error.digest && (
          <p style={{
            marginTop: '24px',
            fontSize: '12px',
            color: '#9ca3af',
            fontFamily: 'monospace'
          }}>
            Error ID: {error.digest}
          </p>
        )}
      </div>
    </div>
      </body>
    </html>
  );
}