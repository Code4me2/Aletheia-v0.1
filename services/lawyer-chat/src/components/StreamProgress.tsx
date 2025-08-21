'use client';

import React, { useState, useEffect } from 'react';
import { 
  Loader2, 
  FileSearch, 
  Database, 
  Brain, 
  PenTool, 
  CheckCircle,
  Clock,
  Activity
} from 'lucide-react';
import { cn } from '@/lib/utils';

export type ProcessingStage = 
  | 'initializing'
  | 'analyzing_context'
  | 'retrieving_documents'
  | 'processing_query'
  | 'generating_response'
  | 'finalizing';

interface StreamProgressProps {
  stage: ProcessingStage;
  message: string;
  percent?: number;
  elapsedTime?: number;
  detail?: string;
  isDarkMode?: boolean;
  className?: string;
}

const STAGE_CONFIG: Record<ProcessingStage, {
  icon: React.ElementType;
  color: string;
  bgColor: string;
  verb: string;
}> = {
  initializing: { 
    icon: Loader2, 
    color: 'text-blue-500',
    bgColor: 'bg-blue-100',
    verb: 'Initializing'
  },
  analyzing_context: { 
    icon: FileSearch, 
    color: 'text-purple-500',
    bgColor: 'bg-purple-100',
    verb: 'Analyzing'
  },
  retrieving_documents: { 
    icon: Database, 
    color: 'text-indigo-500',
    bgColor: 'bg-indigo-100',
    verb: 'Retrieving'
  },
  processing_query: { 
    icon: Brain, 
    color: 'text-cyan-500',
    bgColor: 'bg-cyan-100',
    verb: 'Processing'
  },
  generating_response: { 
    icon: PenTool, 
    color: 'text-green-500',
    bgColor: 'bg-green-100',
    verb: 'Writing'
  },
  finalizing: { 
    icon: CheckCircle, 
    color: 'text-emerald-500',
    bgColor: 'bg-emerald-100',
    verb: 'Finalizing'
  }
};

export function StreamProgress({
  stage,
  message,
  percent,
  elapsedTime = 0,
  detail,
  isDarkMode = false,
  className
}: StreamProgressProps) {
  const [dots, setDots] = useState('');
  const config = STAGE_CONFIG[stage];
  const Icon = config.icon;

  // Animate dots
  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);

  // Format elapsed time
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const isAnimating = stage !== 'finalizing';

  return (
    <div className={cn(
      "flex flex-col gap-3 p-4 rounded-lg border transition-all",
      isDarkMode ? "bg-gray-800 border-gray-700" : "bg-white border-gray-200",
      className
    )}>
      {/* Main status row */}
      <div className="flex items-center gap-3">
        {/* Icon with animation */}
        <div className={cn(
          "p-2 rounded-lg",
          isDarkMode ? "bg-gray-700" : config.bgColor
        )}>
          <Icon className={cn(
            "w-5 h-5",
            config.color,
            isAnimating && "animate-pulse"
          )} />
        </div>

        {/* Status text */}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className={cn(
              "font-medium",
              isDarkMode ? "text-gray-200" : "text-gray-800"
            )}>
              {config.verb}
            </span>
            {isAnimating && (
              <span className={cn(
                "text-sm",
                isDarkMode ? "text-gray-400" : "text-gray-500"
              )}>
                {dots}
              </span>
            )}
          </div>
          <div className={cn(
            "text-sm",
            isDarkMode ? "text-gray-400" : "text-gray-600"
          )}>
            {message}
          </div>
          {detail && (
            <div className={cn(
              "text-xs mt-1",
              isDarkMode ? "text-gray-500" : "text-gray-500"
            )}>
              {detail}
            </div>
          )}
        </div>

        {/* Elapsed time */}
        {elapsedTime > 0 && (
          <div className="flex items-center gap-1.5">
            <Clock className={cn(
              "w-4 h-4",
              isDarkMode ? "text-gray-500" : "text-gray-400"
            )} />
            <span className={cn(
              "text-sm",
              isDarkMode ? "text-gray-400" : "text-gray-500"
            )}>
              {formatTime(elapsedTime)}
            </span>
          </div>
        )}
      </div>

      {/* Progress bar */}
      {percent !== undefined && (
        <div className="relative">
          <div className={cn(
            "h-2 rounded-full overflow-hidden",
            isDarkMode ? "bg-gray-700" : "bg-gray-200"
          )}>
            <div 
              className={cn(
                "h-full transition-all duration-500 ease-out",
                stage === 'initializing' && "bg-blue-500",
                stage === 'analyzing_context' && "bg-purple-500",
                stage === 'retrieving_documents' && "bg-indigo-500",
                stage === 'processing_query' && "bg-cyan-500",
                stage === 'generating_response' && "bg-green-500",
                stage === 'finalizing' && "bg-emerald-500"
              )}
              style={{ width: `${percent}%` }}
            />
          </div>
          {/* Percentage text */}
          <div className={cn(
            "absolute -top-5 text-xs font-medium",
            isDarkMode ? "text-gray-400" : "text-gray-600"
          )}
          style={{ left: `${Math.min(percent, 90)}%` }}>
            {percent}%
          </div>
        </div>
      )}

      {/* Activity indicator for streaming */}
      {stage === 'generating_response' && (
        <div className="flex items-center gap-2">
          <Activity className={cn(
            "w-4 h-4 animate-pulse",
            config.color
          )} />
          <div className="flex gap-1">
            {[...Array(5)].map((_, i) => (
              <div
                key={i}
                className={cn(
                  "w-1 h-3 rounded-full",
                  isDarkMode ? "bg-gray-600" : "bg-gray-300",
                  "animate-pulse"
                )}
                style={{
                  animationDelay: `${i * 100}ms`,
                  opacity: 0.3 + (i * 0.15)
                }}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// Compact version for inline use
export function StreamProgressCompact({
  stage,
  message,
  isDarkMode = false
}: Pick<StreamProgressProps, 'stage' | 'message' | 'isDarkMode'>) {
  const config = STAGE_CONFIG[stage];
  const Icon = config.icon;
  const [dots, setDots] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex items-center gap-2">
      <Icon className={cn(
        "w-4 h-4 animate-spin",
        config.color
      )} />
      <span className={cn(
        "text-sm",
        isDarkMode ? "text-gray-300" : "text-gray-600"
      )}>
        {message}{dots}
      </span>
    </div>
  );
}