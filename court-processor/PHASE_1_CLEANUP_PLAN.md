# Phase 1 Cleanup Plan

## 1. Database Schema Issues

### Current State
- `court_data.opinions_unified` exists with UNIQUE constraint on `cl_id`
- Pipeline uses document ID as `cl_id`, causing duplicates
- No proper conflict handling

### Fix Required
- Implement ON CONFLICT DO UPDATE clause
- Add source tracking (e.g., 'court_documents', 'courtlistener_api')
- Consider composite keys or UUID generation

## 2. Hardcoded Defaults to Remove

### Line 346: Court Resolution
```python
if not court_hint:
    court_hint = 'txed'  # Default fallback to court ID
```
**Issue**: Makes every document appear to have successful court resolution
**Fix**: Return explicit "unresolved" status when court cannot be determined

### Line 842-857: Legal "Enhancement"
```python
legal_concepts = [
    'summary judgment', 'motion to dismiss', 'claim construction',
    'patent infringement', 'preliminary injunction', 'class action',
    'jurisdiction', 'standing', 'damages', 'liability'
]
```
**Issue**: Just keyword matching, not real legal analysis
**Fix**: Rename to "keyword_extraction" and be honest about what it does

## 3. Error Handling Issues

### Silent Failures
- Line 291: `metadata = {}` when JSON parsing fails
- Line 644: `metadata = {}` when metadata is integer
- Citations return empty arrays on any error

**Fix**: Log errors and return explicit failure states

### Overly Broad Exception Handling
- Multiple `except Exception as e:` blocks
- Errors are caught but not properly reported

**Fix**: Catch specific exceptions and propagate meaningful errors

## 4. Data Validation Missing

### No Validation of:
- Court IDs actually exist in courts database
- Judge names are properly formatted
- Citations are valid legal citations
- Reporter normalizations are improvements

**Fix**: Add validation functions for each data type

## Implementation Order

1. **Fix Database Handling** (Immediate)
   - Add ON CONFLICT handling
   - Implement proper duplicate detection
   
2. **Remove Hardcoded Defaults** (Next)
   - Court resolution returns "unresolved" when unknown
   - Rename "legal_enhancement" to "keyword_extraction"
   
3. **Proper Error Handling**
   - Add specific exception types
   - Log all errors with context
   - Return structured error responses
   
4. **Add Validation**
   - Validate court IDs exist
   - Check citation formats
   - Verify enhancement quality