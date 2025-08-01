# Migration Guide: Updating Outdated Tests

## Overview

This guide helps you update outdated test files to work with the enhanced pipeline that includes:
- Courts database as a list (not dict)
- Judge initials mapping
- Document type awareness
- Enhanced court/judge extraction

## Key Changes Required

### 1. Courts Database Handling

**OLD (Incorrect):**
```python
from courts_db import courts
# Treating courts as a dict
court_data = courts.get('txed')  # ❌ WRONG
```

**NEW (Correct):**
```python
from courts_db import courts

# Create dictionary for lookups
COURTS_DICT = {court['id']: court for court in courts if isinstance(court, dict)}

# Now use the dictionary
court_data = COURTS_DICT.get('txed')  # ✅ CORRECT
```

### 2. Judge Initials Mapping

**OLD (Missing feature):**
```python
# Only checks for full judge name
judge_name = metadata.get('judge_name')
```

**NEW (With initials support):**
```python
from judge_initials_mapping import get_judge_from_initials

# Check for initials first
judge_initials = metadata.get('federal_dn_judge_initials_assigned')
if judge_initials:
    judge_info = get_judge_from_initials(judge_initials, court_id)
    if judge_info:
        judge_name = judge_info['name']
```

### 3. Document Type Awareness

**OLD (No type differentiation):**
```python
# Same expectations for all documents
expected_enhancements = 6
```

**NEW (Type-specific expectations):**
```python
def get_expected_enhancements(doc_type):
    if doc_type == 'docket':
        return 5  # No reporter normalization expected
    elif doc_type == 'opinion':
        return 6  # All enhancements expected
    else:
        return 6  # Default
```

### 4. URL Handling

**OLD (No URL support):**
```python
court = metadata.get('court')  # Might be a URL
```

**NEW (Handles URLs):**
```python
court_hint = metadata.get('court')
if court_hint and 'courtlistener.com' in court_hint:
    # Extract court_id from URL
    match = re.search(r'/courts/([^/]+)/?', court_hint)
    if match:
        court_id = match.group(1)
```

### 5. Case Number Court Extraction

**NEW (Extract court from case number):**
```python
def extract_court_from_case_number(case_number):
    """Extract court from patterns like '2:24-cv-00123-RG'"""
    case_lower = case_number.lower()
    
    patterns = {
        'txed': ['txed', 'e.d. tex', 'edtx'],
        'txnd': ['txnd', 'n.d. tex', 'ndtx'],
        # ... more patterns
    }
    
    for court_id, patterns_list in patterns.items():
        for pattern in patterns_list:
            if pattern in case_lower:
                return court_id
    return None
```

## Files to Update

### High Priority (Core functionality):
1. `test_working_pipeline.py` → Use `eleven_stage_pipeline_enhanced.py`
2. `test_complete_pipeline_20_docs.py` → Add judge initials support
3. `test_maximum_pipeline.py` → Fix courts list handling

### Medium Priority (Specific features):
1. `test_court_extraction_v4.py` → Use enhanced court extraction
2. `test_pipeline_v4_api.py` → Migrate to enhanced pipeline
3. `test_court_resolution_standalone.py` → Update courts dict creation

### Low Priority (May be deprecated):
1. `test_improved_court_extraction.py` → Superseded by enhanced version
2. Older test files without document type support

## Example: Updating a Test File

### Before:
```python
from eleven_stage_pipeline import ElevenStagePipeline
from courts_db import courts

def test_pipeline():
    pipeline = ElevenStagePipeline()
    
    # Process documents
    results = pipeline.process_batch(limit=10)
    
    # Check results
    assert results['completeness_score'] > 50
```

### After:
```python
from eleven_stage_pipeline_enhanced import EnhancedElevenStagePipeline
from courts_db import courts
from judge_initials_mapping import JUDGE_INITIALS_MAP

# Create courts dictionary
COURTS_DICT = {court['id']: court for court in courts if isinstance(court, dict)}

def test_enhanced_pipeline():
    pipeline = EnhancedElevenStagePipeline()
    
    # Process documents
    results = await pipeline.process_batch(limit=10)
    
    # Check type-specific completeness
    for doc_type, stats in results['verification']['completeness_by_type'].items():
        if doc_type == 'docket':
            assert stats['completeness'] >= 80  # 5/6 enhancements
        elif doc_type == 'opinion':
            assert stats['completeness'] >= 95  # 6/6 enhancements
    
    # Verify improvements
    improvements = results['verification']['extraction_improvements']
    assert improvements['judges_from_initials'] > 0  # Should map some initials
```

## Testing Checklist

When updating a test file, ensure it:

- [ ] Imports `EnhancedElevenStagePipeline` (not old versions)
- [ ] Creates `COURTS_DICT` from courts list
- [ ] Imports and uses `judge_initials_mapping`
- [ ] Handles different document types appropriately
- [ ] Extracts courts from URLs and case numbers
- [ ] Expects correct completeness scores by document type
- [ ] Uses async/await for pipeline processing
- [ ] Handles metadata as dict, string, or integer

## Deprecation Notice

The following patterns are deprecated:
- Direct indexing into `courts` object
- Ignoring `federal_dn_judge_initials_assigned` field
- Same completeness expectations for all document types
- Not handling CourtListener URLs

## Reference Implementation

See `test_pipeline_updated.py` for a complete example of a properly updated test file that demonstrates all the new features and correct usage patterns.