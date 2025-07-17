# Legal Document Enhancer Guide

## Overview

The Legal Document Enhancer adds semantic understanding to documents parsed by Unstructured.io. It identifies legal-specific structures, extracts metadata, and provides a framework for custom enhancements.

## Quick Start

```python
from services.legal_document_enhancer import enhance_legal_document

# Basic usage
enhanced_elements = enhance_legal_document(elements, doc_type="transcript")

# Access enhanced metadata
for elem in enhanced_elements:
    if elem.metadata.legal.get('event') == 'objection':
        print(f"Objection: {elem.text}")
        print(f"Type: {elem.metadata.legal.get('event_type')}")
        print(f"Speaker: {elem.metadata.legal.get('speaker')}")
```

## Document Types

### 1. Transcripts
**Enhancements:**
- Speaker identification
- Objection detection and classification
- Ruling extraction
- Examination phase tracking
- Event sequencing

**Metadata Added:**
```python
elem.metadata.legal = {
    'speaker': 'THE COURT',
    'event': 'ruling',
    'ruling': 'sustained',
    'ruling_on_objection': True,
    'event_type': 'hearsay'
}
```

### 2. Opinions
**Enhancements:**
- Section identification (procedural history, facts, analysis, etc.)
- Legal standard extraction
- Disposition detection
- Citation tracking

**Metadata Added:**
```python
elem.metadata.legal = {
    'section': 'procedural_history',
    'standard_type': 'de_novo',
    'citations': ['123 F.3d 456', '789 U.S. 012'],
    'disposition': 'affirmed'
}
```

### 3. Orders
**Enhancements:**
- Findings of fact numbering
- Conclusions of law tracking
- Order directive extraction

**Metadata Added:**
```python
elem.metadata.legal = {
    'order_section': 'findings',
    'findings_number': 12,
    'section': 'findings_header'
}
```

### 4. Dockets
**Enhancements:**
- Entry parsing (number, date, description)
- Document filing detection
- Entry type classification

**Metadata Added:**
```python
elem.metadata.legal = {
    'docket_number': 45,
    'entry_date': '01/15/2024',
    'entry_type': 'motion',
    'filed_documents': ['motion', 'brief']
}
```

## Adding Custom Enhancements

### Method 1: Extend Existing Document Type

```python
from services.legal_document_enhancer import LegalDocumentEnhancer

def enhance_bankruptcy_opinions(elements):
    """Add bankruptcy-specific enhancements"""
    for elem in elements:
        # Detect chapter references
        if match := re.search(r'Chapter (\d+)', elem.text):
            elem.metadata.legal['bankruptcy_chapter'] = int(match.group(1))
        
        # Detect creditor types
        if 'secured creditor' in elem.text.lower():
            elem.metadata.legal['creditor_type'] = 'secured'
        elif 'unsecured creditor' in elem.text.lower():
            elem.metadata.legal['creditor_type'] = 'unsecured'
            
        # Track discharge mentions
        if 'discharge' in elem.text.lower():
            elem.metadata.legal['discusses_discharge'] = True
    
    return elements

# Register the enhancer
enhancer = LegalDocumentEnhancer()
enhancer.register_custom_enhancer('bankruptcy_opinion', enhance_bankruptcy_opinions)

# Use it
enhanced = enhancer.enhance(elements, doc_type='bankruptcy_opinion')
```

### Method 2: Create New Document Type

```python
def enhance_settlement_agreement(elements):
    """Enhancement for settlement agreements"""
    current_section = None
    
    for elem in elements:
        # Detect recitals
        if 'WHEREAS' in elem.text:
            elem.metadata.legal['is_recital'] = True
            current_section = 'recitals'
        
        # Detect definitions
        elif '"' in elem.text and 'means' in elem.text:
            elem.metadata.legal['contains_definition'] = True
            # Extract defined terms
            defined_terms = re.findall(r'"([^"]+)"', elem.text)
            if defined_terms:
                elem.metadata.legal['defined_terms'] = defined_terms
        
        # Detect payment terms
        elif '$' in elem.text or 'payment' in elem.text.lower():
            elem.metadata.legal['contains_payment_terms'] = True
            amounts = re.findall(r'\$[\d,]+(?:\.\d{2})?', elem.text)
            if amounts:
                elem.metadata.legal['payment_amounts'] = amounts
        
        # Track current section
        if current_section:
            elem.metadata.legal['agreement_section'] = current_section
    
    return elements

# Register as new type
enhancer.register_custom_enhancer('settlement', enhance_settlement_agreement)
```

### Method 3: Add Pattern-Based Rules

```python
def add_patent_patterns(enhancer):
    """Add patent-specific patterns to base enhancer"""
    
    # Add to initialization
    enhancer.patent_patterns = [
        r'U\.S\. Patent No\. [\d,]+',
        r'claim\s+\d+',
        r'prior art',
        r'obvious(ness)?',
        r'non-obvious(ness)?'
    ]
    
    # Modify base enhancement to use these patterns
    original_base = enhancer._apply_base_enhancements
    
    def enhanced_base(elements):
        elements = original_base(elements)
        
        for elem in elements:
            # Find patent numbers
            patents = re.findall(enhancer.patent_patterns[0], elem.text)
            if patents:
                elem.metadata.legal['patent_numbers'] = patents
            
            # Track claim references
            claims = re.findall(r'claim\s+(\d+)', elem.text, re.I)
            if claims:
                elem.metadata.legal['claim_refs'] = [int(c) for c in claims]
            
            # Detect obviousness discussion
            if any(re.search(pattern, elem.text, re.I) 
                   for pattern in enhancer.patent_patterns[2:]):
                elem.metadata.legal['discusses_patentability'] = True
        
        return elements
    
    enhancer._apply_base_enhancements = enhanced_base
```

## Advanced Usage

### 1. Chaining Enhancements

```python
def enhance_complex_document(elements):
    """Apply multiple enhancement passes"""
    enhancer = LegalDocumentEnhancer()
    
    # First pass: basic legal enhancements
    elements = enhancer.enhance(elements, doc_type='opinion')
    
    # Second pass: jurisdiction-specific
    elements = add_federal_circuit_enhancements(elements)
    
    # Third pass: subject-matter specific
    elements = add_patent_enhancements(elements)
    
    return elements
```

### 2. Context-Aware Enhancement

```python
def enhance_with_context(elements):
    """Use surrounding elements for better classification"""
    
    for i, elem in enumerate(elements):
        # Look at previous element for context
        if i > 0:
            prev_elem = elements[i-1]
            
            # If previous was a question, this might be an answer
            if prev_elem.text.strip().endswith('?'):
                elem.metadata.legal['is_answer'] = True
                elem.metadata.legal['question_index'] = i-1
        
        # Look ahead for rulings on objections
        if elem.metadata.legal.get('event') == 'objection':
            # Check next 3 elements for ruling
            for j in range(1, min(4, len(elements) - i)):
                if elements[i+j].metadata.legal.get('event') == 'ruling':
                    elem.metadata.legal['has_ruling'] = True
                    elem.metadata.legal['ruling_distance'] = j
                    break
    
    return elements
```

### 3. Statistical Enhancement

```python
def add_document_statistics(elements):
    """Add document-wide statistics"""
    
    # Count various elements
    stats = {
        'total_citations': 0,
        'total_objections': 0,
        'total_rulings': 0,
        'speakers': set(),
        'sections': set()
    }
    
    for elem in elements:
        legal = elem.metadata.legal
        
        if legal.get('citations'):
            stats['total_citations'] += len(legal['citations'])
        
        if legal.get('event') == 'objection':
            stats['total_objections'] += 1
        
        if legal.get('event') == 'ruling':
            stats['total_rulings'] += 1
        
        if legal.get('speaker'):
            stats['speakers'].add(legal['speaker'])
        
        if legal.get('section'):
            stats['sections'].add(legal['section'])
    
    # Add stats to first element
    elements[0].metadata.legal['document_stats'] = {
        'citation_count': stats['total_citations'],
        'objection_count': stats['total_objections'],
        'ruling_count': stats['total_rulings'],
        'speaker_count': len(stats['speakers']),
        'section_count': len(stats['sections'])
    }
    
    return elements
```

## SQL Queries for Enhanced Data

### Find Objections and Their Rulings
```sql
WITH objections AS (
  SELECT 
    id,
    elem->>'text' as objection_text,
    elem->'metadata'->'legal'->>'speaker' as objector,
    elem->'metadata'->'legal'->>'event_type' as objection_type,
    elem_index
  FROM court_data.opinions_unified,
    jsonb_array_elements(structured_elements->'structured_elements') 
    WITH ORDINALITY AS t(elem, elem_index)
  WHERE elem->'metadata'->'legal'->>'event' = 'objection'
),
rulings AS (
  SELECT 
    id,
    elem->>'text' as ruling_text,
    elem->'metadata'->'legal'->>'ruling' as ruling,
    elem_index
  FROM court_data.opinions_unified,
    jsonb_array_elements(structured_elements->'structured_elements') 
    WITH ORDINALITY AS t(elem, elem_index)
  WHERE elem->'metadata'->'legal'->>'event' = 'ruling'
)
SELECT 
  o.objection_text,
  o.objection_type,
  r.ruling,
  r.ruling_text
FROM objections o
JOIN rulings r ON o.id = r.id AND r.elem_index > o.elem_index
WHERE r.elem_index - o.elem_index <= 3;
```

### Extract Document Sections
```sql
SELECT 
  id,
  case_name,
  jsonb_object_agg(
    elem->'metadata'->'legal'->>'section',
    elem->>'text'
  ) as sections
FROM court_data.opinions_unified,
  jsonb_array_elements(structured_elements->'structured_elements') elem
WHERE elem->'metadata'->'legal'->>'section' IS NOT NULL
GROUP BY id, case_name;
```

### Analyze Speaking Time in Transcripts
```sql
SELECT 
  elem->'metadata'->'legal'->>'speaker' as speaker,
  COUNT(*) as speaking_turns,
  SUM(LENGTH(elem->>'text')) as total_characters
FROM court_data.opinions_unified,
  jsonb_array_elements(structured_elements->'structured_elements') elem
WHERE elem->'metadata'->'legal'->>'speaker' IS NOT NULL
  AND document_type = 'transcript'
GROUP BY speaker
ORDER BY total_characters DESC;
```

## Best Practices

1. **Test Patterns Thoroughly**
   ```python
   test_texts = [
       "Objection, Your Honor. Hearsay.",
       "I object on the grounds of relevance.",
       "OBJECTION: Asked and answered."
   ]
   
   for text in test_texts:
       # Verify your patterns match expected text
       assert any(re.search(p, text, re.I) for p in objection_patterns)
   ```

2. **Handle Edge Cases**
   - Multi-line text
   - ALL CAPS vs mixed case
   - Typos and variations
   - Missing punctuation

3. **Performance Considerations**
   - Compile regex patterns once
   - Use early exit conditions
   - Avoid nested loops where possible

4. **Maintain Backwards Compatibility**
   - Always check if metadata exists before accessing
   - Use `.get()` method for optional fields
   - Don't modify original element structure

## Troubleshooting

### Missing Enhancements
```python
# Debug why enhancements aren't applied
for elem in elements:
    print(f"Text: {elem.text[:50]}")
    print(f"Category: {elem.category}")
    print(f"Legal metadata: {elem.metadata.legal}")
    print("---")
```

### Pattern Not Matching
```python
# Test individual patterns
pattern = r'THE COURT:'
test_text = "THE COURT: Sustained."

if re.search(pattern, test_text):
    print("Pattern matches!")
else:
    print("Pattern failed - check case sensitivity and spacing")
```

### Performance Issues
```python
import time

start = time.time()
enhanced = enhance_legal_document(elements)
elapsed = time.time() - start

print(f"Enhanced {len(elements)} elements in {elapsed:.2f} seconds")
print(f"Average: {elapsed/len(elements)*1000:.2f} ms per element")
```