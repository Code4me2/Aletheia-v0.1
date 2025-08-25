'use client';

import { useEffect } from 'react';
import { SessionProvider } from 'next-auth/react';
import { initializeDocumentSources } from '@/lib/document-sources/init-client';

export function Providers({ children }: { children: React.ReactNode }) {
  useEffect(() => {
    // Initialize document sources on client side
    initializeDocumentSources();
  }, []);

  return (
    <SessionProvider 
      basePath="/chat/api/auth"
      refetchInterval={0}
      refetchOnWindowFocus={false}
    >
      {children}
    </SessionProvider>
  );
}