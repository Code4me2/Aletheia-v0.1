/**
 * Markdown formatting utilities for improving AI response formatting
 * Ensures consistent, well-structured markdown output
 */

/**
 * Formats raw AI response text into well-structured markdown
 * @param text - Raw text from AI response
 * @returns Properly formatted markdown
 */
export function formatMarkdown(text: string): string {
  if (!text) return '';
  
  let formatted = text;
  
  // Step 1: Normalize line endings and clean up extra whitespace
  formatted = formatted.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  
  // Step 2: Detect and format section headers
  formatted = detectAndFormatHeaders(formatted);
  
  // Step 3: Format mathematical expressions
  formatted = formatMathExpressions(formatted);
  
  // Step 4: Format bullet lists properly
  formatted = formatBulletLists(formatted);
  
  // Step 5: Ensure proper spacing between sections
  formatted = ensureSectionSpacing(formatted);
  
  // Step 6: Format emphasis (bold/italic) for key terms
  formatted = formatEmphasis(formatted);
  
  // Step 7: Clean up final formatting
  formatted = cleanupFormatting(formatted);
  
  return formatted;
}

/**
 * Detects potential headers and formats them with proper markdown syntax
 */
function detectAndFormatHeaders(text: string): string {
  const lines = text.split('\n');
  const formatted: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
    const prevLine = i > 0 ? lines[i - 1].trim() : '';
    
    // Skip if already a markdown header
    if (line.match(/^#{1,6}\s+/)) {
      formatted.push(lines[i]);
      continue;
    }
    
    // Detect main sections (e.g., "Basic Definition", "Applications")
    if (isLikelyMainHeader(line, prevLine, nextLine)) {
      formatted.push(`## ${line}`);
    }
    // Detect subsections (e.g., "Integral Form", "Differential Form")
    else if (isLikelySubHeader(line, prevLine, nextLine)) {
      formatted.push(`### ${line}`);
    }
    // Detect sub-subsections
    else if (isLikelySubSubHeader(line, prevLine, nextLine)) {
      formatted.push(`#### ${line}`);
    }
    else {
      formatted.push(lines[i]);
    }
  }
  
  return formatted.join('\n');
}

/**
 * Determines if a line is likely a main header
 */
function isLikelyMainHeader(line: string, prevLine: string, nextLine: string): boolean {
  // Check various conditions that suggest a header
  if (line.length < 60 && line.length > 2) {
    // Common header patterns
    const headerPatterns = [
      /^(Basic |General |Main |Primary |Key )?Definition\s*$/i,
      /^(Forms|Types|Categories|Versions) of .+$/i,
      /^Applications?( and Use Cases)?$/i,
      /^(Key |Main |Important )?Features?$/i,
      /^(Technical |Implementation )?Details?$/i,
      /^(Conceptual |Theoretical )?Importance$/i,
      /^(Historical |Modern )?Context$/i,
      /^(Related|Associated) (Laws?|Concepts?|Topics?)$/i,
      /^Extensions?( and Variations)?$/i,
      /^Examples?( and Cases)?$/i,
      /^Summary( and Conclusions?)?$/i,
      /^Introduction$/i,
      /^Overview$/i,
      /^Background$/i,
      /^Methodology$/i,
      /^Results?$/i,
      /^Discussions?$/i,
      /^Conclusions?$/i,
      /^References?$/i
    ];
    
    const matchesPattern = headerPatterns.some(pattern => pattern.test(line));
    
    // Additional heuristics
    const hasEmptyLineBefore = prevLine === '';
    const hasContentAfter = nextLine !== '';
    const endsWithColon = line.endsWith(':');
    const isShortPhrase = line.split(' ').length <= 6;
    const startsWithCapital = /^[A-Z]/.test(line);
    
    // A line is likely a header if:
    // 1. It matches a known pattern, OR
    // 2. It has empty line before AND content after AND is short, OR
    // 3. It ends with colon AND is short AND starts with capital
    return matchesPattern || 
           (hasEmptyLineBefore && hasContentAfter && isShortPhrase && startsWithCapital) ||
           (endsWithColon && isShortPhrase && startsWithCapital);
  }
  return false;
}

/**
 * Determines if a line is likely a subheader
 */
function isLikelySubHeader(line: string, prevLine: string, nextLine: string): boolean {
  if (line.length < 40 && line.length > 3) {
    const subHeaderPatterns = [
      /^\d+\.\s*.+$/,  // Numbered items
      /^(Integral|Differential|Vector|Scalar) Form$/i,
      /^(First|Second|Third|Primary|Secondary) .+$/i,
      /^(Type|Category|Form|Version|Method|Approach) \d+:?\s*.*/i,
      /^(Step|Phase|Stage) \d+:?\s*.*/i,
      /^[A-Z][a-z]+ (Law|Equation|Theorem|Principle)$/,
      /^(Advantages?|Disadvantages?|Benefits?|Limitations?)$/i,
      /^(Properties|Characteristics|Attributes)$/i,
      /^(Requirements?|Prerequisites?|Conditions?)$/i
    ];
    
    return subHeaderPatterns.some(pattern => pattern.test(line));
  }
  return false;
}

/**
 * Determines if a line is likely a sub-subheader
 */
function isLikelySubSubHeader(line: string, prevLine: string, nextLine: string): boolean {
  if (line.length < 30 && line.length > 3) {
    const subSubHeaderPatterns = [
      /^[a-z]\)\s*.+$/,  // a), b), c) style
      /^[ivx]+\.\s*.+$/i,  // Roman numerals
      /^(Example|Case|Scenario|Instance):?\s*.*/i,
      /^(Note|Remark|Important|Tip):?\s*.*/i
    ];
    
    return subSubHeaderPatterns.some(pattern => pattern.test(line));
  }
  return false;
}

/**
 * Formats mathematical expressions with proper code blocks or inline code
 */
function formatMathExpressions(text: string): string {
  const lines = text.split('\n');
  const formatted: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    
    // Skip if already in a code block
    if (line.startsWith('```')) {
      formatted.push(lines[i]);
      // Skip lines until closing ```
      i++;
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        formatted.push(lines[i]);
        i++;
      }
      if (i < lines.length) {
        formatted.push(lines[i]);
      }
      continue;
    }
    
    // Check if entire line looks like an equation
    const equationPattern = /^[∮∫∇⋅×∂∑∏\w\s]+[=≈≠≤≥<>][^.!?]*$/;
    const hasSpecialSymbols = /[∮∫∇⋅×∂∑∏εμσρφψωΩαβγδεζηθικλμνξοπρστυφχψω₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹±∓∞]/.test(line);
    
    if (equationPattern.test(line) && hasSpecialSymbols) {
      // This is a standalone equation
      formatted.push('```');
      formatted.push(line);
      formatted.push('```');
    } else {
      // Process inline math in regular text
      let processedLine = lines[i];
      
      // Only format specific math terms, not every symbol
      const mathTerms = [
        /\bε₀\b/g,
        /\bμ₀\b/g,
        /\bq_[a-z]+\b/g,
        /\b∇²\b/g,
        /\bd[A-Z]\b/g,
        /\b[A-Z]\b(?=\s*(is|are|represents?|denotes?)\s+the)/g // Single letters that are defined
      ];
      
      mathTerms.forEach(pattern => {
        processedLine = processedLine.replace(pattern, match => `\`${match}\``);
      });
      
      formatted.push(processedLine);
    }
  }
  
  return formatted.join('\n');
}

/**
 * Formats bullet lists for better consistency
 */
function formatBulletLists(text: string): string {
  const lines = text.split('\n');
  const formatted: string[] = [];
  let inList = false;
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();
    
    // Detect list items with various markers
    const bulletPatterns = [
      { pattern: /^[•]\s+(.+)$/, marker: '•' },
      { pattern: /^[·]\s+(.+)$/, marker: '·' },
      { pattern: /^[▪▫◦‣⁃∙]\s+(.+)$/, marker: 'other' },
      { pattern: /^[-–—]\s+(.+)$/, marker: '-' }
    ];
    
    const numberedPattern = /^\d+[.)]\s+(.+)$/;
    
    let isBulletItem = false;
    let processedContent = line;
    
    // Check for bullet patterns
    for (const { pattern, marker } of bulletPatterns) {
      const match = trimmed.match(pattern);
      if (match) {
        // Convert all bullet types to standard dash
        processedContent = `- ${match[1]}`;
        isBulletItem = true;
        break;
      }
    }
    
    if (isBulletItem) {
      formatted.push(processedContent);
      inList = true;
    } else if (numberedPattern.test(trimmed)) {
      formatted.push(line);
      inList = true;
    } else {
      // Add spacing after list if needed
      if (inList && trimmed !== '' && !trimmed.startsWith('-') && !numberedPattern.test(trimmed)) {
        if (formatted[formatted.length - 1] !== '') {
          formatted.push('');
        }
        inList = false;
      }
      formatted.push(line);
    }
  }
  
  return formatted.join('\n');
}

/**
 * Ensures proper spacing between sections
 */
function ensureSectionSpacing(text: string): string {
  const lines = text.split('\n');
  const formatted: string[] = [];
  
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const nextLine = i + 1 < lines.length ? lines[i + 1] : '';
    
    formatted.push(line);
    
    // Add spacing after headers
    if (line.match(/^#{1,6}\s+/) && nextLine.trim() !== '') {
      formatted.push('');
    }
    
    // Add spacing before headers (if not already present)
    if (nextLine.match(/^#{1,6}\s+/) && line.trim() !== '' && !line.match(/^#{1,6}\s+/)) {
      formatted.push('');
    }
  }
  
  return formatted.join('\n');
}

/**
 * Formats emphasis for key terms
 */
function formatEmphasis(text: string): string {
  // Key terms that should be bold
  const boldTerms = [
    'electric field',
    'magnetic field',
    'charge density',
    'electric flux',
    'permittivity',
    'permeability',
    'divergence',
    'gradient',
    'curl',
    'laplacian',
    'potential',
    'voltage',
    'current',
    'resistance',
    'capacitance',
    'inductance'
  ];
  
  let formatted = text;
  
  // Make key terms bold (case insensitive)
  boldTerms.forEach(term => {
    const regex = new RegExp(`\\b(${term})\\b`, 'gi');
    formatted = formatted.replace(regex, (match) => {
      // Don't format if already in emphasis or code
      if (formatted.slice(formatted.lastIndexOf(match) - 2, formatted.lastIndexOf(match)).includes('*') ||
          formatted.slice(formatted.lastIndexOf(match) - 1, formatted.lastIndexOf(match)) === '`') {
        return match;
      }
      return `**${match}**`;
    });
  });
  
  return formatted;
}

/**
 * Final cleanup of formatting
 */
function cleanupFormatting(text: string): string {
  let formatted = text;
  
  // Remove excessive blank lines (more than 2)
  formatted = formatted.replace(/\n{3,}/g, '\n\n');
  
  // Ensure document doesn't start or end with blank lines
  formatted = formatted.trim();
  
  // Fix spacing around code blocks
  formatted = formatted.replace(/\n*```\n*/g, '\n\n```\n');
  formatted = formatted.replace(/\n*```\n*/g, '\n```\n\n');
  
  // Ensure consistent list formatting
  formatted = formatted.replace(/\n- /g, '\n- ');
  
  return formatted;
}

/**
 * Preprocesses AI response for optimal SafeMarkdown rendering
 * This is the main function to use in the chat component
 */
export function preprocessAIResponse(text: string): string {
  // First apply existing cleaning
  let processed = text;
  
  // Then apply markdown formatting
  processed = formatMarkdown(processed);
  
  return processed;
}