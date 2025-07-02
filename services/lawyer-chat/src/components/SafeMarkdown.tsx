'use client';

import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
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

type CodeProps = React.HTMLAttributes<HTMLElement> & {
  inline?: boolean;
  className?: string;
  children?: React.ReactNode;
};

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  type?: string;
  checked?: boolean;
  disabled?: boolean;
};


export default function SafeMarkdown({ content, className }: SafeMarkdownProps) {
  const { isDarkMode } = useSidebarStore();
  
  const components: Partial<Components> = {
    // ========== HEADERS - Enhanced hierarchy with clear visual distinction ==========
    h1: ({ children, ...props }: HeadingProps) => (
      <h1 {...props} className={`text-2xl font-semibold mb-4 mt-6 leading-tight ${
        isDarkMode 
          ? 'text-gray-200' 
          : 'text-gray-700'
      }`}>{children}</h1>
    ),
    h2: ({ children, ...props }: HeadingProps) => (
      <h2 {...props} className={`text-xl font-semibold mb-3 mt-5 leading-snug ${
        isDarkMode ? 'text-gray-200' : 'text-gray-700'
      }`}>{children}</h2>
    ),
    h3: ({ children, ...props }: HeadingProps) => (
      <h3 {...props} className={`text-lg font-medium mb-3 mt-4 leading-normal ${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      }`}>{children}</h3>
    ),
    h4: ({ children, ...props }: HeadingProps) => (
      <h4 {...props} className={`text-base font-medium mb-2 mt-3 ${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      }`}>{children}</h4>
    ),
    h5: ({ children, ...props }: HeadingProps) => (
      <h5 {...props} className={`text-base font-medium mb-2 mt-3 ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</h5>
    ),
    h6: ({ children, ...props }: HeadingProps) => (
      <h6 {...props} className={`text-sm font-medium mb-2 mt-2 ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</h6>
    ),
    // ========== TEXT CONTENT - Optimized for readability ==========
    p: ({ children, ...props }: ComponentProps) => (
      <p {...props} className={`mb-4 leading-relaxed text-base ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</p>
    ),
    
    // ========== LISTS - Enhanced with better visual hierarchy ==========
    ul: ({ children, ...props }: ComponentProps) => (
      <ul {...props} className={`list-disc pl-6 mb-4 space-y-1 marker:text-opacity-60 ${
        isDarkMode 
          ? 'text-gray-300 marker:text-gray-500' 
          : 'text-gray-700 marker:text-gray-400'
      }`}>{children}</ul>
    ),
    ol: ({ children, ...props }: ComponentProps) => (
      <ol {...props} className={`list-decimal pl-6 mb-4 space-y-1 marker:font-medium ${
        isDarkMode 
          ? 'text-gray-300 marker:text-gray-400' 
          : 'text-gray-700 marker:text-gray-500'
      }`}>{children}</ol>
    ),
    li: ({ children, ...props }: ComponentProps) => (
      <li {...props} className="leading-relaxed">{children}</li>
    ),
    // ========== TEXT EMPHASIS - Clear visual indicators ==========
    strong: ({ children, ...props }: ComponentProps) => (
      <strong {...props} className={`font-semibold ${
        isDarkMode ? 'text-gray-200' : 'text-gray-800'
      }`}>{children}</strong>
    ),
    em: ({ children, ...props }: ComponentProps) => (
      <em {...props} className="italic">{children}</em>
    ),
    // ========== BLOCKQUOTES - Enhanced visual design for citations ==========
    blockquote: ({ children, ...props }: ComponentProps) => (
      <blockquote {...props} className={`border-l-4 pl-4 pr-2 py-2 my-4 ${
        isDarkMode 
          ? 'border-gray-600 bg-gray-800/30 text-gray-300' 
          : 'border-gray-300 bg-gray-50 text-gray-700'
      }`}>
        <div className="italic">{children}</div>
      </blockquote>
    ),
    
    // ========== SEPARATORS - Visual content division ==========
    hr: ({ ...props }: ComponentProps) => (
      <hr {...props} className={`my-6 border-0 h-px ${
        isDarkMode 
          ? 'bg-gray-700' 
          : 'bg-gray-300'
      }`} />
    ),
    // Enhanced code blocks with syntax highlighting support
    code: (props: CodeProps) => {
      const { inline, className: codeClassName, children } = props;
      const match = /language-(\w+)/.exec(codeClassName || '');
      
      if (!inline && match) {
        return (
          <div className="relative my-6 group">
            <div className={`absolute top-0 right-0 text-xs px-3 py-1.5 rounded-tl rounded-br font-medium ${
              isDarkMode ? 'bg-gray-800 text-gray-400' : 'bg-gray-200 text-gray-600'
            }`}>
              {match[1].toUpperCase()}
            </div>
            <pre className={`${codeClassName} overflow-x-auto p-6 rounded-lg leading-relaxed ${
              isDarkMode 
                ? 'bg-gray-900 text-gray-300 border border-gray-800' 
                : 'bg-gray-50 text-gray-800 border border-gray-200'
            }`}>
              <code className={`${codeClassName} text-sm`}>
                {children}
              </code>
            </pre>
          </div>
        );
      }
      
      return (
        <code className={`${codeClassName || ''} ${
          isDarkMode 
            ? 'bg-gray-800 text-emerald-400 border border-gray-700' 
            : 'bg-gray-100 text-emerald-700 border border-gray-200'
        } px-1.5 py-0.5 rounded text-sm font-mono`}>
          {children}
        </code>
      );
    },
    // ========== PREFORMATTED TEXT - For structured data display ==========
    pre: ({ children, ...props }: ComponentProps) => {
      if ((children as any)?.props?.className?.includes('language-')) {
        return <pre {...props}>{children}</pre>;
      }
      return (
        <pre {...props} className={`overflow-x-auto p-4 rounded-lg my-4 font-mono text-sm leading-relaxed whitespace-pre-wrap ${
          isDarkMode 
            ? 'bg-gray-900 text-gray-300 border border-gray-800' 
            : 'bg-gray-50 text-gray-800 border border-gray-200'
        }`}>{children}</pre>
      );
    },
    // ========== LINKS - Enhanced with visual feedback ==========
    a: ({ children, href, ...props }: LinkProps) => (
      <a 
        {...props}
        href={href}
        className={`inline-flex items-center gap-1 font-medium underline decoration-1 underline-offset-2 transition-all hover:decoration-2 ${
          isDarkMode 
            ? 'text-blue-400 hover:text-blue-300 decoration-blue-400/50 hover:decoration-blue-300' 
            : 'text-blue-600 hover:text-blue-700 decoration-blue-600/50 hover:decoration-blue-700'
        }`}
        target="_blank"
        rel="noopener noreferrer"
      >
        {children}
        <svg className="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
      </a>
    ),
    // ========== TABLES - Responsive with enhanced styling ==========
    table: ({ children, ...props }: ComponentProps) => (
      <div className="my-4 w-full overflow-hidden rounded-lg shadow-sm">
        <div className="overflow-x-auto">
          <table {...props} className={`min-w-full divide-y ${
            isDarkMode ? 'divide-gray-700' : 'divide-gray-200'
          }`}>{children}</table>
        </div>
      </div>
    ),
    thead: ({ children, ...props }: ComponentProps) => (
      <thead {...props} className={`text-xs uppercase tracking-wider font-semibold ${
        isDarkMode ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'
      }`}>{children}</thead>
    ),
    tbody: ({ children, ...props }: ComponentProps) => (
      <tbody {...props} className={`divide-y ${
        isDarkMode ? 'divide-gray-800 bg-gray-900/50' : 'divide-gray-100 bg-white'
      }`}>{children}</tbody>
    ),
    th: ({ children, ...props }: ComponentProps) => (
      <th {...props} className={`px-6 py-4 text-left text-xs font-bold ${
        isDarkMode ? 'text-gray-200' : 'text-gray-900'
      }`}>{children}</th>
    ),
    td: ({ children, ...props }: ComponentProps) => (
      <td {...props} className={`px-6 py-4 text-sm leading-relaxed ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</td>
    ),
    // ========== TASK LISTS - Interactive checkboxes ==========
    input: (props: InputProps) => {
      if (props.type === 'checkbox') {
        return (
          <input
            {...props}
            disabled
            className={`mr-3 rounded cursor-not-allowed ${
              isDarkMode 
                ? 'text-blue-500 bg-gray-800 border-gray-600' 
                : 'text-blue-600 bg-white border-gray-300'
            }`}
          />
        );
      }
      return <input {...props} />;
    },
    // ========== DEFINITION LISTS - Structured term-definition pairs ==========
    dl: ({ children, ...props }: ComponentProps) => (
      <dl {...props} className="my-6 space-y-6">{children}</dl>
    ),
    dt: ({ children, ...props }: ComponentProps) => (
      <dt {...props} className={`font-bold text-lg ${
        isDarkMode ? 'text-gray-200' : 'text-gray-900'
      }`}>{children}</dt>
    ),
    dd: ({ children, ...props }: ComponentProps) => (
      <dd {...props} className={`ml-8 mt-2 leading-relaxed ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</dd>
    ),
    // ========== ADDITIONAL FORMATTING ELEMENTS ==========
    // Keyboard input
    kbd: ({ children, ...props }: ComponentProps) => (
      <kbd {...props} className={`inline-block px-2 py-1 text-sm font-mono rounded shadow-sm ${
        isDarkMode 
          ? 'bg-gray-800 text-gray-300 border border-gray-700 shadow-gray-900/50' 
          : 'bg-gray-100 text-gray-800 border border-gray-300 shadow-gray-200/50'
      }`}>{children}</kbd>
    ),
    // Highlighted/marked text
    mark: ({ children, ...props }: ComponentProps) => (
      <mark {...props} className={`px-1 rounded ${
        isDarkMode 
          ? 'bg-yellow-800/50 text-yellow-200' 
          : 'bg-yellow-200 text-gray-900'
      }`}>{children}</mark>
    ),
    // Subscript
    sub: ({ children, ...props }: ComponentProps) => (
      <sub {...props} className="text-xs">{children}</sub>
    ),
    // Superscript
    sup: ({ children, ...props }: ComponentProps) => (
      <sup {...props} className="text-xs">{children}</sup>
    ),
    // Abbreviations
    abbr: ({ children, title, ...props }: ComponentProps & { title?: string }) => (
      <abbr {...props} title={title} className={`underline decoration-dotted cursor-help ${
        isDarkMode ? 'decoration-gray-500' : 'decoration-gray-400'
      }`}>{children}</abbr>
    ),
    // Details/Summary for collapsible content
    details: ({ children, ...props }: ComponentProps) => (
      <details {...props} className={`my-6 p-4 rounded-lg ${
        isDarkMode 
          ? 'bg-gray-800/50 border border-gray-700' 
          : 'bg-gray-50 border border-gray-200'
      }`}>{children}</details>
    ),
    summary: ({ children, ...props }: ComponentProps) => (
      <summary {...props} className={`cursor-pointer font-medium mb-2 ${
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
      <div className={className}>
        <ReactMarkdown 
          remarkPlugins={[remarkGfm]} 
          components={components}
        >
          {content}
        </ReactMarkdown>
      </div>
    </ErrorBoundary>
  );
}