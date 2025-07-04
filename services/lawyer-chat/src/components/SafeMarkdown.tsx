'use client';

import React from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import rehypeRaw from 'rehype-raw';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ErrorBoundary } from './ErrorBoundary';
import { AlertCircle, Copy, Check } from 'lucide-react';
import { useSidebarStore } from '@/store/sidebar';
import 'katex/dist/katex.min.css';

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
  const [copiedCode, setCopiedCode] = React.useState<string | null>(null);
  
  const copyToClipboard = React.useCallback(async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedCode(id);
      setTimeout(() => setCopiedCode(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, []);
  
  const components: Partial<Components> = {
    // ========== HEADERS - AI-standard typography with enhanced hierarchy ==========
    h1: ({ children, ...props }: HeadingProps) => (
      <h1 {...props} className={`text-4xl font-extrabold mb-6 mt-8 leading-tight tracking-tight ${
        isDarkMode 
          ? 'text-white' 
          : 'text-gray-900'
      }`}>{children}</h1>
    ),
    h2: ({ children, ...props }: HeadingProps) => (
      <h2 {...props} className={`text-2xl font-bold mb-5 mt-8 leading-tight tracking-tight ${
        isDarkMode ? 'text-gray-100' : 'text-gray-800'
      }`}>{children}</h2>
    ),
    h3: ({ children, ...props }: HeadingProps) => (
      <h3 {...props} className={`text-xl font-bold mb-4 mt-6 leading-snug ${
        isDarkMode ? 'text-gray-100' : 'text-gray-800'
      }`}>{children}</h3>
    ),
    h4: ({ children, ...props }: HeadingProps) => (
      <h4 {...props} className={`text-lg font-semibold mb-3 mt-5 ${
        isDarkMode ? 'text-gray-200' : 'text-gray-700'
      }`}>{children}</h4>
    ),
    h5: ({ children, ...props }: HeadingProps) => (
      <h5 {...props} className={`text-base font-semibold mb-3 mt-4 ${
        isDarkMode ? 'text-gray-300' : 'text-gray-600'
      }`}>{children}</h5>
    ),
    h6: ({ children, ...props }: HeadingProps) => (
      <h6 {...props} className={`text-sm font-semibold mb-2 mt-3 uppercase tracking-wide ${
        isDarkMode ? 'text-gray-400' : 'text-gray-600'
      }`}>{children}</h6>
    ),
    // ========== TEXT CONTENT - AI-standard paragraph formatting ==========
    p: ({ children, ...props }: ComponentProps) => (
      <p {...props} className={`mb-5 leading-[1.8] text-base ${
        isDarkMode ? 'text-gray-300' : 'text-gray-700'
      }`}>{children}</p>
    ),
    
    // ========== LISTS - AI-standard spacing and hierarchy ==========
    ul: ({ children, ...props }: ComponentProps) => (
      <ul {...props} className={`list-disc pl-8 mb-4 space-y-1.5 marker:text-opacity-80 ${
        isDarkMode 
          ? 'text-gray-300 marker:text-gray-400' 
          : 'text-gray-700 marker:text-gray-500'
      }`}>{children}</ul>
    ),
    ol: ({ children, ...props }: ComponentProps) => (
      <ol {...props} className={`list-decimal pl-8 mb-5 space-y-3 marker:font-semibold ${
        isDarkMode 
          ? 'text-gray-300 marker:text-gray-400' 
          : 'text-gray-700 marker:text-gray-600'
      }`}>{children}</ol>
    ),
    li: ({ children, ...props }: ComponentProps) => (
      <li {...props} className="leading-[1.8] pl-1">{children}</li>
    ),
    // ========== TEXT EMPHASIS - Clear visual indicators ==========
    strong: ({ children, ...props }: ComponentProps) => (
      <strong {...props} className={`font-bold ${
        isDarkMode ? 'text-gray-100' : 'text-gray-900'
      }`}>{children}</strong>
    ),
    em: ({ children, ...props }: ComponentProps) => (
      <em {...props} className="italic">{children}</em>
    ),
    // ========== BLOCKQUOTES - AI-standard citation formatting ==========
    blockquote: ({ children, ...props }: ComponentProps) => (
      <blockquote {...props} className={`border-l-4 pl-6 pr-4 py-5 my-6 rounded-r-md ${
        isDarkMode 
          ? 'border-gray-600 bg-gray-800/50 text-gray-300' 
          : 'border-gray-300 bg-gray-50 text-gray-700'
      }`}>
        <div className="leading-[1.7]">{children}</div>
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
      const codeString = String(children).replace(/\n$/, '');
      const codeId = React.useId();
      
      if (!inline && match) {
        const language = match[1];
        return (
          <div className="relative my-6 group">
            <div className="absolute top-2 right-2 flex items-center gap-2 z-10">
              <span className={`text-xs px-2.5 py-1 font-medium rounded ${
                isDarkMode ? 'bg-gray-700/80 text-gray-300' : 'bg-gray-100/80 text-gray-700'
              }`}>
                {language}
              </span>
              <button
                onClick={() => copyToClipboard(codeString, codeId)}
                className={`p-1.5 rounded transition-all opacity-0 group-hover:opacity-100 ${
                  isDarkMode 
                    ? 'bg-gray-700/80 text-gray-300 hover:bg-gray-600 hover:text-gray-200' 
                    : 'bg-gray-100/80 text-gray-700 hover:bg-gray-200 hover:text-gray-800'
                }`}
                title="Copy code"
              >
                {copiedCode === codeId ? (
                  <Check className="w-4 h-4" />
                ) : (
                  <Copy className="w-4 h-4" />
                )}
              </button>
            </div>
            <SyntaxHighlighter
              style={isDarkMode ? oneDark : oneLight}
              language={language}
              PreTag="div"
              className="!mt-0 !mb-0 rounded-md overflow-hidden"
              customStyle={{
                margin: 0,
                padding: '1.25rem 1.5rem',
                fontSize: '0.875rem',
                lineHeight: '1.6',
                backgroundColor: isDarkMode ? '#1a1a1a' : '#f8f9fa',
                border: 'none',
              }}
              showLineNumbers={codeString.split('\n').length > 10}
              lineNumberStyle={{
                minWidth: '2.5em',
                paddingRight: '1em',
                color: isDarkMode ? '#666' : '#999',
                userSelect: 'none',
              }}
            >
              {codeString}
            </SyntaxHighlighter>
          </div>
        );
      }
      
      return (
        <code className={`${codeClassName || ''} ${
          isDarkMode 
            ? 'bg-gray-800 text-gray-200' 
            : 'bg-gray-100 text-gray-800'
        } px-1.5 py-0.5 rounded font-mono text-[0.85em]`}>
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
      <div className={`my-6 w-full overflow-hidden rounded-lg shadow-md border ${
        isDarkMode ? 'border-gray-700' : 'border-gray-200'
      }`}>
        <div className="overflow-x-auto">
          <table {...props} className={`min-w-full divide-y ${
            isDarkMode ? 'divide-gray-700' : 'divide-gray-200'
          }`}>{children}</table>
        </div>
      </div>
    ),
    thead: ({ children, ...props }: ComponentProps) => (
      <thead {...props} className={`text-xs uppercase tracking-wider font-bold ${
        isDarkMode ? 'bg-gray-800 text-gray-200' : 'bg-gray-50 text-gray-700'
      }`}>{children}</thead>
    ),
    tbody: ({ children, ...props }: ComponentProps) => (
      <tbody {...props} className={`divide-y ${
        isDarkMode ? 'divide-gray-800 bg-gray-900/30' : 'divide-gray-100 bg-white'
      }`}>{children}</tbody>
    ),
    th: ({ children, ...props }: ComponentProps) => (
      <th {...props} className={`px-6 py-4 text-left text-xs font-bold uppercase tracking-wider ${
        isDarkMode ? 'text-gray-100' : 'text-gray-900'
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
          remarkPlugins={[remarkGfm, remarkMath]} 
          rehypePlugins={[rehypeKatex, rehypeRaw]}
          components={components}
        >
          {content || ''}
        </ReactMarkdown>
      </div>
    </ErrorBoundary>
  );
}