'use client';

import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { ErrorBoundary } from './ErrorBoundary';
import { AlertCircle } from 'lucide-react';
import { useSidebarStore } from '@/store/sidebar';

interface SafeMarkdownProps {
  content: string;
  className?: string;
}

// Type definitions for component props
type ComponentProps = React.HTMLAttributes<HTMLElement> & {
  children?: React.ReactNode;
};

type HeadingProps = React.HTMLAttributes<HTMLHeadingElement> & {
  children?: React.ReactNode;
};

type LinkProps = React.AnchorHTMLAttributes<HTMLAnchorElement> & {
  children?: React.ReactNode;
  href?: string;
};


type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  type?: string;
  checked?: boolean;
  disabled?: boolean;
};


export default function SafeMarkdown({ content, className }: SafeMarkdownProps) {
  const { isDarkMode } = useSidebarStore();
  
  const components: Partial<Components> = {
    // ========== HEADERS - Consistent hierarchy with unified spacing ==========
    h1: ({ children, ...props }: HeadingProps) => (
      <h1 {...props} className={`text-4xl font-extrabold mb-8 mt-8 leading-tight ${
        isDarkMode ? 'text-white' : 'text-gray-900'
      }`}>{children}</h1>
    ),
    h2: ({ children, ...props }: HeadingProps) => (
      <h2 {...props} className={`text-3xl font-bold mb-6 mt-8 leading-snug ${
        isDarkMode ? 'text-gray-200' : 'text-gray-800'
      }`}>{children}</h2>
    ),
    h3: ({ children, ...props }: HeadingProps) => (
      <h3 {...props} className={`text-2xl font-semibold mb-4 mt-6 leading-snug ${
        isDarkMode ? 'text-gray-100' : 'text-gray-700'
      }`}>{children}</h3>
    ),
    h4: ({ children, ...props }: HeadingProps) => (
      <h4 {...props} className={`text-xl font-semibold mb-4 mt-6 leading-normal ${
        isDarkMode ? 'text-gray-200' : 'text-gray-700'
      }`}>{children}</h4>
    ),
    h5: ({ children, ...props }: HeadingProps) => (
      <h5 {...props} className={`text-lg font-semibold mb-4 mt-4 leading-normal ${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      }`}>{children}</h5>
    ),
    h6: ({ children, ...props }: HeadingProps) => (
      <h6 {...props} className={`text-base font-semibold mb-4 mt-4 leading-normal ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</h6>
    ),
    // ========== TEXT CONTENT - Consistent paragraph formatting ==========
    p: ({ children, ...props }: ComponentProps) => (
      <p {...props} className={`mb-4 leading-relaxed text-base ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</p>
    ),
    
    // ========== LISTS - Unified spacing and clean hierarchy ==========
    ul: ({ children, ...props }: ComponentProps) => (
      <ul {...props} className={`list-disc pl-6 mb-4 space-y-2 ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</ul>
    ),
    ol: ({ children, ...props }: ComponentProps) => (
      <ol {...props} className={`list-decimal pl-6 mb-4 space-y-2 ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</ol>
    ),
    li: ({ children, ...props }: ComponentProps) => (
      <li {...props} className="leading-relaxed">{children}</li>
    ),
    // ========== TEXT EMPHASIS - Clear visual indicators ==========
    strong: ({ children, ...props }: ComponentProps) => (
      <strong {...props} className={`font-semibold ${
        isDarkMode ? 'text-gray-100' : 'text-gray-900'
      }`}>{children}</strong>
    ),
    em: ({ children, ...props }: ComponentProps) => (
      <em {...props} className="italic">{children}</em>
    ),
    // ========== BLOCKQUOTES - Enhanced citation formatting ==========
    blockquote: ({ children, ...props }: ComponentProps) => (
      <blockquote {...props} className={`border-l-4 p-6 my-6 rounded-md ${
        isDarkMode 
          ? 'border-gray-600 bg-gray-800/40 text-gray-300' 
          : 'border-gray-300 bg-gray-100 text-gray-700'
      }`}>
        {children}
      </blockquote>
    ),
    
    // ========== SEPARATORS - Visual content division ==========
    hr: ({ ...props }: ComponentProps) => (
      <hr {...props} className={`my-6 border-t ${
        isDarkMode ? 'border-gray-700' : 'border-gray-300'
      }`} />
    ),
    // ========== CODE - Simple formatting without syntax highlighting ==========
    code: ({ children, ...props }: ComponentProps) => (
      <code {...props} className={`px-2 py-1 rounded font-mono text-sm ${
        isDarkMode 
          ? 'bg-gray-800 text-gray-200' 
          : 'bg-gray-100 text-gray-800'
      }`}>
        {children}
      </code>
    ),
    // ========== PREFORMATTED TEXT - For structured data display ==========
    pre: ({ children, ...props }: ComponentProps) => (
      <pre {...props} className={`overflow-x-auto p-6 rounded-lg my-6 font-mono text-sm leading-relaxed whitespace-pre-wrap ${
        isDarkMode 
          ? 'bg-gray-900 text-gray-300 border border-gray-800' 
          : 'bg-gray-50 text-gray-800 border border-gray-200'
      }`}>{children}</pre>
    ),
    // ========== LINKS - Clean and accessible ==========
    a: ({ children, href, ...props }: LinkProps) => (
      <a 
        {...props}
        href={href}
        className={`underline underline-offset-2 transition-colors ${
          isDarkMode 
            ? 'text-blue-400 hover:text-blue-300' 
            : 'text-blue-600 hover:text-blue-800'
        }`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
      </a>
    ),
    // ========== TABLES - Clean and readable ==========
    table: ({ children, ...props }: ComponentProps) => (
      <div className="my-6 overflow-x-auto">
        <table {...props} className={`min-w-full text-sm border-collapse ${
          isDarkMode ? 'text-gray-300' : 'text-gray-800'
        }`}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children, ...props }: ComponentProps) => (
      <thead {...props} className={isDarkMode ? 'bg-gray-800' : 'bg-gray-100'}>
        {children}
      </thead>
    ),
    tbody: ({ children, ...props }: ComponentProps) => (
      <tbody {...props}>{children}</tbody>
    ),
    th: ({ children, ...props }: ComponentProps) => (
      <th {...props} className={`text-left px-4 py-3 font-semibold ${
        isDarkMode ? 'text-gray-200' : 'text-gray-900'
      }`}>{children}</th>
    ),
    td: ({ children, ...props }: ComponentProps) => (
      <td {...props} className={`px-4 py-3 border-t ${
        isDarkMode ? 'border-gray-700' : 'border-gray-200'
      }`}>{children}</td>
    ),
    // ========== TASK LISTS - Simple checkboxes ==========
    input: (props: InputProps) => {
      if (props.type === 'checkbox') {
        return (
          <input
            {...props}
            disabled
            className="mr-2 rounded cursor-not-allowed"
          />
        );
      }
      return <input {...props} />;
    },
    // ========== DEFINITION LISTS - Clean term-definition pairs ==========
    dl: ({ children, ...props }: ComponentProps) => (
      <dl {...props} className="my-6 space-y-4">{children}</dl>
    ),
    dt: ({ children, ...props }: ComponentProps) => (
      <dt {...props} className={`font-semibold ${
        isDarkMode ? 'text-gray-200' : 'text-gray-900'
      }`}>{children}</dt>
    ),
    dd: ({ children, ...props }: ComponentProps) => (
      <dd {...props} className={`ml-6 mt-1 ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</dd>
    ),
    // ========== ADDITIONAL FORMATTING - Simplified ==========
    kbd: ({ children, ...props }: ComponentProps) => (
      <kbd {...props} className={`inline-block px-2 py-1 text-sm font-mono rounded border ${
        isDarkMode 
          ? 'bg-gray-800 text-gray-300 border-gray-700' 
          : 'bg-gray-100 text-gray-800 border-gray-300'
      }`}>{children}</kbd>
    ),
    mark: ({ children, ...props }: ComponentProps) => (
      <mark {...props} className={`px-1 rounded ${
        isDarkMode 
          ? 'bg-yellow-900/50 text-yellow-200' 
          : 'bg-yellow-200 text-gray-900'
      }`}>{children}</mark>
    ),
    sub: ({ children, ...props }: ComponentProps) => (
      <sub {...props} className="text-xs">{children}</sub>
    ),
    sup: ({ children, ...props }: ComponentProps) => (
      <sup {...props} className="text-xs">{children}</sup>
    ),
    abbr: ({ children, title, ...props }: ComponentProps & { title?: string }) => (
      <abbr {...props} title={title} className="underline decoration-dotted cursor-help">{children}</abbr>
    ),
    details: ({ children, ...props }: ComponentProps) => (
      <details {...props} className={`my-6 p-4 rounded-lg border ${
        isDarkMode 
          ? 'bg-gray-800/50 border-gray-700' 
          : 'bg-gray-50 border-gray-200'
      }`}>{children}</details>
    ),
    summary: ({ children, ...props }: ComponentProps) => (
      <summary {...props} className={`cursor-pointer font-medium ${
        isDarkMode ? 'text-gray-200' : 'text-gray-800'
      }`}>{children}</summary>
    )
  };
  
  const fallback = (
    <div className={`p-4 rounded-md ${
      isDarkMode ? 'bg-red-900/20 border border-red-800' : 'bg-red-50 border border-red-200'
    }`}>
      <div className="flex items-start gap-2">
        <AlertCircle className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
          isDarkMode ? 'text-red-400' : 'text-red-600'
        }`} />
        <div>
          <p className={`font-medium ${
            isDarkMode ? 'text-red-300' : 'text-red-800'
          }`}>
            Unable to render message
          </p>
          <p className={`text-sm mt-1 ${
            isDarkMode ? 'text-red-400/80' : 'text-red-600'
          }`}>
            The message content could not be displayed properly. The raw content has been preserved.
          </p>
          <details className="mt-2">
            <summary className={`cursor-pointer text-sm ${
              isDarkMode ? 'text-red-400' : 'text-red-700'
            }`}>
              Show raw content
            </summary>
            <pre className={`mt-2 p-2 text-xs rounded overflow-x-auto ${
              isDarkMode ? 'bg-gray-900 text-gray-300' : 'bg-white text-gray-700'
            }`}>
              {content}
            </pre>
          </details>
        </div>
      </div>
    </div>
  );

  return (
    <ErrorBoundary 
      fallback={fallback}
      isolate
      level="component"
      resetKeys={[content]}
      resetOnKeysChange
    >
      <div 
        className={`${className} markdown-content`} 
        dir="ltr" 
        style={{ 
          unicodeBidi: 'embed',
          direction: 'ltr',
          textAlign: 'left'
        }}
      >
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]} 
          rehypePlugins={[rehypeRaw]}
          components={components}
        >
          {content || ''}
        </ReactMarkdown>
      </div>
    </ErrorBoundary>
  );
}