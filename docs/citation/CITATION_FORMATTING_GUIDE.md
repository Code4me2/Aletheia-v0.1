# Citation Formatting Guide for AI System Prompting

## Overview

This guide defines the citation formatting system for AI responses that require academic, legal, or research citations with interactive hover effects and cross-references.

## Core Formatting Syntax

### 1. In-Text Citations

#### Primary Format
```
<cite id="unique-id">quoted or referenced text</cite>
```

#### Superscript References
```
The court held that this principle applies broadly[1].
Multiple sources support this view[2,3,4].
Sub-citations use letters[2a].
```

### 2. Citation Panel Format

Each citation must include a corresponding entry in the Citations section:

```markdown
## Citations

[1] **Smith v. Jones**, 123 F.3d 456 (2d Cir. 2023)
- **Holding**: Tax penalties must be proportional to violation severity
- **Relevance**: Direct precedent for proportionality principle
- **Connection**: Primary authority
- **Pages**: pp. 461-462

[2] **Brown v. IRS**, 456 F.Supp.3d 789 (S.D.N.Y. 2024)
- **Holding**: Corporate tax evasion penalties follow proportionality rule
- **Relevance**: Extends Smith holding to corporate context
- **Connection**: Supporting authority

[2a] **Brown v. IRS** (corporate intent analysis)
- **Specific Point**: Court emphasized deliberate intent as aggravating factor
- **Pages**: pp. 794-796
- **Connection**: Specific factual parallel
```

## Citation Connection Levels

### Primary Authority
- Direct precedent or controlling authority
- Statute or regulation directly on point
- Use when: The source directly answers the legal question

### Supporting Authority
- Cases that reinforce or extend the principle
- Secondary sources that explain the rule
- Use when: The source strengthens the argument

### Distinguishing Authority
- Cases with different outcomes but relevant reasoning
- Sources that show limits or exceptions
- Use when: Showing boundaries of a principle

### Background Authority
- Historical context or foundational principles
- General explanations of legal concepts
- Use when: Providing context or education

## Formatting Examples

### Legal Research Example

```markdown
The doctrine of qualified immunity protects government officials <cite id="harlow-v-fitzgerald">performing discretionary functions from liability for civil damages</cite>[1]. This protection applies unless the official violated <cite id="pearson-v-callahan">"clearly established statutory or constitutional rights of which a reasonable person would have known"</cite>[2].

However, the Supreme Court recently emphasized that <cite id="taylor-v-riojas">some violations are so obvious that prior case law is not needed</cite>[3]. This represents a potential shift in how courts analyze qualified immunity claims[4,5].

## Citations

[1] **Harlow v. Fitzgerald**, 457 U.S. 800 (1982)
- **Holding**: Established modern qualified immunity standard
- **Relevance**: Foundational case defining the doctrine
- **Connection**: Primary authority
- **Key Quote**: "bare allegations of malice should not suffice" (p. 817)

[2] **Pearson v. Callahan**, 555 U.S. 223 (2009)
- **Holding**: Courts may grant immunity without deciding constitutional violation
- **Relevance**: Modified analytical framework
- **Connection**: Primary authority

[3] **Taylor v. Riojas**, 141 S. Ct. 52 (2020)
- **Holding**: Obvious violations don't require prior precedent
- **Relevance**: Limits qualified immunity in extreme cases
- **Connection**: Distinguishing authority
```

### Academic Research Example

```markdown
Recent studies demonstrate that <cite id="johnson-2024">climate change impacts vary significantly by geographic region</cite>[1]. The data shows particularly severe effects in <cite id="smith-meta-2023">coastal areas and small island nations</cite>[2], with sea level rise projections exceeding earlier estimates[2a].

## Citations

[1] **Johnson, M. et al.** (2024). "Regional Climate Variability and Impact Assessment." *Nature Climate Change*, 14(3), 234-251.
- **Finding**: 40% greater impact variation than previous models
- **Method**: Meta-analysis of 127 regional studies
- **Connection**: Primary source

[2] **Smith, K. & Lee, J.** (2023). "Coastal Vulnerability Index: A Global Assessment." *Environmental Research Letters*, 18(9).
- **Finding**: 2.3x higher risk for populations under 10m elevation
- **Data**: Analysis of 15,000 coastal settlements
- **Connection**: Supporting source

[2a] **Smith & Lee** (sea level projections)
- **Specific Point**: RCP8.5 scenario shows 1.2m rise by 2100
- **Table**: Table 3, p. 7
- **Connection**: Specific data point
```

## System Prompt Template

```
When providing responses that require citations, use the following formatting:

1. For in-text citations, use: <cite id="unique-identifier">relevant text</cite>
2. For reference markers, use: [1], [2], [2a] format
3. Always include a "Citations" section with:
   - Full citation in bold
   - Holding/Finding
   - Relevance to the query
   - Connection level (Primary/Supporting/Distinguishing/Background)
   - Page numbers or specific sections when relevant

4. Connection levels:
   - Primary: Direct authority on the issue
   - Supporting: Reinforces the principle
   - Distinguishing: Shows exceptions or limits
   - Background: Provides context

5. For legal citations, include:
   - Case name, reporter citation, court, year
   - Key holdings and relevant quotes
   
6. For academic citations, include:
   - Author(s), year, title, journal/source
   - Key findings and methodology when relevant

Ensure all citations are properly linked to their references using consistent ID formatting.
```

## Implementation Notes

### ID Naming Conventions
- Legal cases: Use shortened case names (e.g., "smith-v-jones")
- Academic: Use first author and year (e.g., "johnson-2024")
- Statutes: Use abbreviated title and section (e.g., "26-usc-501")
- Multiple references to same source: Add descriptors (e.g., "smith-v-jones-standing")

### Hover Effect Behavior
- Hovering over `<cite>` text highlights the corresponding citation
- Hovering over [1] superscript highlights the full citation
- Citation panel shows visual indicator (border, background) when referenced
- Multiple citations can be highlighted simultaneously

### Best Practices
1. Keep citation IDs short but descriptive
2. Use consistent formatting throughout response
3. Group related citations (e.g., [2,3,4] not [2][3][4])
4. Include page numbers for specific quotes or data
5. Clearly indicate connection level for each source

## Example System Prompt for Legal Research

```
You are a legal research assistant. When answering queries:

1. Use <cite id="case-name">quoted holdings</cite> for direct quotes
2. Use [1], [2] etc. for general references
3. Provide full citations in a "Citations" section
4. Label each citation's connection level
5. Include page numbers for specific references
6. Format case names in bold
7. Structure citations with bullet points for clarity

Focus on accuracy and proper attribution of all legal principles.
```

## Example System Prompt for Academic Research

```
You are an academic research assistant. When answering queries:

1. Use <cite id="author-year">key findings</cite> for specific claims
2. Use [1], [2] for supporting references
3. Include methodology notes where relevant
4. Distinguish between primary research and reviews
5. Note sample sizes and statistical significance
6. Format author names and journals consistently

Prioritize peer-reviewed sources and recent publications.
```