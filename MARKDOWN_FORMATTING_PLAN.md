# Markdown Formatting Plan for AI Chat

## Current State Analysis

### Problem
The AI chat in the Aletheia-v0.1 SPA currently displays AI responses as plain text using `textContent`, which prevents markdown formatting from being rendered properly.

### Current Implementation
- **Location**: `website/js/app.js`, line 185
- **Method**: `addMessage(text, isUser = false)`
- **Issue**: Uses `messageDiv.textContent = text;` which escapes all HTML/markdown

### AI Response Format
Based on testing the webhook endpoint, the AI returns properly formatted markdown including:
- Headers (`#`, `##`, etc.)
- Bold (`**text**`) and italic (`*text*`)
- Code blocks (` ``` `) and inline code (`` ` ``)
- Lists (both ordered and unordered)
- Links (`[text](url)`)
- Tables
- Blockquotes (`>`)

## Requirements

### Must Support
1. **Headers** (h1-h6)
2. **Text formatting** (bold, italic, strikethrough)
3. **Code blocks** with syntax highlighting
4. **Inline code**
5. **Lists** (ordered and unordered, nested)
6. **Links** (with security considerations)
7. **Tables**
8. **Blockquotes**
9. **Line breaks** and paragraphs
10. **Horizontal rules**

### Security Considerations
- Sanitize HTML to prevent XSS attacks
- Only allow safe HTML tags
- Ensure links open in new tabs with `rel="noopener noreferrer"`
- Escape user input while preserving AI markdown

## Implementation Options

### Option 1: Marked.js (Recommended)
- **Pros**: Lightweight, well-maintained, secure by default
- **Size**: ~40KB minified
- **Features**: Full CommonMark support, extensible
- **Security**: Built-in sanitization options

### Option 2: Markdown-it
- **Pros**: Very flexible, plugin system
- **Size**: ~90KB minified
- **Features**: Full featured, excellent spec compliance

### Option 3: Custom Implementation
- **Pros**: Minimal size, exact control
- **Cons**: Security risks, maintenance burden

## Proposed Solution

### 1. Use Marked.js with DOMPurify
```javascript
// Add to HTML
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify/dist/purify.min.js"></script>

// Update addMessage function
addMessage(text, isUser = false) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message');
    messageDiv.classList.add(isUser ? 'user' : 'bot');
    
    if (isUser) {
        // User messages remain plain text for security
        messageDiv.textContent = text;
    } else {
        // AI messages get markdown parsing
        const rawHtml = marked.parse(text);
        const cleanHtml = DOMPurify.sanitize(rawHtml, {
            ADD_ATTR: ['target', 'rel'],
            ALLOWED_TAGS: ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'br', 'hr',
                          'strong', 'em', 'del', 'code', 'pre', 'blockquote',
                          'ul', 'ol', 'li', 'a', 'table', 'thead', 'tbody', 
                          'tr', 'td', 'th']
        });
        messageDiv.innerHTML = cleanHtml;
        
        // Post-process links for security
        messageDiv.querySelectorAll('a').forEach(link => {
            link.setAttribute('target', '_blank');
            link.setAttribute('rel', 'noopener noreferrer');
        });
    }
    
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
```

### 2. Add CSS Styling for Markdown Elements
```css
/* Message markdown styles */
.message h1, .message h2, .message h3, 
.message h4, .message h5, .message h6 {
    margin: 0.5em 0;
    font-weight: 600;
}

.message h1 { font-size: 1.5em; }
.message h2 { font-size: 1.3em; }
.message h3 { font-size: 1.1em; }

.message code {
    background: rgba(0, 0, 0, 0.1);
    padding: 0.2em 0.4em;
    border-radius: 3px;
    font-family: var(--code-font);
    font-size: 0.9em;
}

.message pre {
    background: var(--dark-bg);
    color: var(--light-text);
    padding: 1em;
    border-radius: var(--border-radius-sm);
    overflow-x: auto;
    margin: 0.5em 0;
}

.message pre code {
    background: none;
    padding: 0;
    color: inherit;
}

.message ul, .message ol {
    margin: 0.5em 0;
    padding-left: 1.5em;
}

.message table {
    border-collapse: collapse;
    margin: 0.5em 0;
    width: 100%;
}

.message th, .message td {
    border: 1px solid var(--border-color);
    padding: 0.5em;
    text-align: left;
}

.message th {
    background: var(--light-bg);
    font-weight: 600;
}

.message blockquote {
    border-left: 4px solid var(--secondary-color);
    margin: 0.5em 0;
    padding-left: 1em;
    color: var(--text-secondary);
}

.message a {
    color: var(--secondary-color);
    text-decoration: none;
}

.message a:hover {
    text-decoration: underline;
}
```

## Testing Plan

### Test Cases
1. **Basic formatting**: Bold, italic, strikethrough
2. **Headers**: All levels (h1-h6)
3. **Code**: Inline and blocks (with/without language)
4. **Lists**: Nested, mixed ordered/unordered
5. **Links**: External, with special characters
6. **Tables**: With headers, alignment
7. **Mixed content**: Complex documents with multiple elements
8. **Security**: Attempt XSS injections
9. **Performance**: Large markdown documents

### Test Messages
```javascript
const testMessages = [
    "# Hello World\nThis is a **bold** and *italic* test.",
    "```javascript\nconst x = 42;\nconsole.log(x);\n```",
    "Visit [OpenAI](https://openai.com) for more info.",
    "| Column 1 | Column 2 |\n|----------|----------|\n| Data 1   | Data 2   |",
    "> Important: This is a blockquote\n> with multiple lines",
    "1. First item\n   - Nested bullet\n   - Another bullet\n2. Second item"
];
```

## Rollout Strategy

### Phase 1: Implementation
1. Add marked.js and DOMPurify libraries
2. Update addMessage function
3. Add CSS styles for markdown elements

### Phase 2: Testing
1. Test with various markdown inputs
2. Verify security (XSS prevention)
3. Check performance with large messages

### Phase 3: Enhancement
1. Add syntax highlighting for code blocks (Prism.js)
2. Add copy button for code blocks
3. Add collapsible sections for long responses

## Alternative: Minimal Implementation

If external libraries are not desired, a minimal safe implementation could handle:
- Convert `**text**` to `<strong>text</strong>`
- Convert `*text*` to `<em>text</em>`
- Convert `` `code` `` to `<code>code</code>`
- Convert newlines to `<br>` appropriately
- Auto-link URLs

This would provide basic formatting without full markdown support.