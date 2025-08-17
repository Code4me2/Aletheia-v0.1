'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

interface AuthGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export default function AuthGuard({ children, fallback }: AuthGuardProps) {
  const { data: session, status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === 'loading') return; // Still loading
    
    if (!session) {
      // Redirect to sign-in page with callback URL
      // Note: basePath is /chat, so the route is relative to that
      // Use /chat instead of / to stay within the lawyer-chat app
      router.push('/auth/signin?callbackUrl=/chat');
    }
  }, [session, status, router]);

  // Show loading state
  if (status === 'loading') {
    return fallback || (
      <div className="flex h-screen items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600 dark:text-gray-400">Loading...</p>
        </div>
      </div>
    );
  }

  // Not authenticated, show nothing (redirect will happen)
  if (!session) {
    return null;
  }

  // Authenticated, show content
  return <>{children}</>;
}