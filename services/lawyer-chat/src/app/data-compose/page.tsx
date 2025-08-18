'use client';

import React from 'react';
import { useSession } from 'next-auth/react';
import { redirect } from 'next/navigation';
import TaskBar from '@/components/TaskBar';
import { useSidebarStore } from '@/store/sidebar';

export default function DataComposePage() {
  const { data: session, status } = useSession();
  const isTaskBarExpanded = useSidebarStore((state) => state.isTaskBarExpanded);
  const isDarkMode = useSidebarStore((state) => state.isDarkMode);

  // Redirect if not authenticated
  if (status === 'loading') {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!session) {
    redirect('/auth/signin?callbackUrl=/data-compose');
  }

  return (
    <div className={`flex h-screen ${isDarkMode ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <TaskBar />
      
      <main className={`flex-1 transition-all duration-300 ${isTaskBarExpanded ? 'ml-[280px]' : 'ml-[56px]'}`}>
        <div className={`h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
          {/* Header */}
          <div className={`border-b ${isDarkMode ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'} px-6 py-4`}>
            <h1 className={`text-2xl font-semibold ${isDarkMode ? 'text-white' : 'text-gray-900'}`}>
              Data Compose Dashboard
            </h1>
            <p className={`mt-1 text-sm ${isDarkMode ? 'text-gray-400' : 'text-gray-600'}`}>
              AI-powered workflow automation and document processing
            </p>
          </div>

          {/* Iframe Container */}
          <div className="h-[calc(100vh-5rem)] p-6">
            <div className={`h-full rounded-lg border ${isDarkMode ? 'border-gray-700' : 'border-gray-200'} overflow-hidden shadow-sm`}>
              <iframe
                src="/chat/data-compose-app/tailwind-wrapper.html"
                className="w-full h-full border-0"
                title="Data Compose Application"
              />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}