# CourtListener API Quick Reference

## Essential Information

**Base URL**: `https://www.courtlistener.com/api/rest/v4`  
**Authentication**: `Authorization: Token YOUR_TOKEN`  
**Rate Limit**: 5,000 requests/hour (authenticated)

## Free Endpoints Summary

| Endpoint | Purpose | Key Parameters |
|----------|---------|----------------|
| `/courts/` | Court information | `id`, `jurisdiction` |
| `/dockets/` | Case dockets | `court`, `date_filed__gte`, `nature_of_suit` |
| `/clusters/` | Opinion groups | `docket__court`, `date_filed__range` |
| `/opinions/` | Opinion text | `cluster__docket__court`, `type` |
| `/search/` | Full-text search | `q`, `type`, `court` |
| `/recap-query/` | Check RECAP availability | `pacer_doc_id__in`, `court` |
| `/people/` | Judge data | `name_last`, `court` |
| `/audio/` | Oral arguments | `docket__court`, `date_argued` |
| `/citation-lookup/` | Citation validation | POST with `text` |

## Restricted Endpoints (Need Permission)

- `/recap-documents/` - Full text from PACER docs
- `/docket-entries/` - Individual filings with text
- `/parties/` - Case parties
- `/attorneys/` - Attorney information

## Search Types

```python
search_types = {
    'o': 'Case law opinions',
    'r': 'RECAP dockets with documents',
    'rd': 'RECAP documents (flat)',
    'd': 'Dockets only',
    'p': 'People/Judges',
    'oa': 'Oral arguments'
}
```

## Common Filters

```python
# Date filtering
params = {
    'date_filed__gte': '2024-01-01',
    'date_filed__lte': '2024-12-31',
    'date_filed__range': '2024-01-01,2024-12-31'
}

# Court filtering
params = {
    'court': 'scotus',  # Direct court
    'cluster__docket__court': 'scotus',  # Nested court
    'court__in': 'cafc,txed,deld'  # Multiple courts
}

# IP-specific
params = {
    'nature_of_suit__in': '820,830,840',  # Copyright, Patent, Trademark
    'court__in': 'cafc,txed,deld'  # Common IP courts
}
```

## Pagination Examples

```python
# Initial request
response = requests.get(
    f"{base_url}/dockets/",
    headers=headers,
    params={'page_size': 100}
)

# Follow cursor
while response.json().get('next'):
    next_url = response.json()['next']
    response = requests.get(next_url, headers=headers)
    # Process results
```

## Quick Code Examples

### Check if Document Exists in RECAP
```python
def check_recap_availability(court, pacer_doc_ids):
    response = requests.get(
        f"{base_url}/recap-query/",
        headers=headers,
        params={
            'docket_entry__docket__court': court,
            'pacer_doc_id__in': ','.join(pacer_doc_ids)
        }
    )
    return response.json()['results']
```

### Search for Patent Cases
```python
def search_patent_cases(query, court=None):
    params = {
        'q': query,
        'type': 'r',
        'nature_of_suit': '830'
    }
    if court:
        params['court'] = court
    
    response = requests.get(
        f"{base_url}/search/",
        headers=headers,
        params=params
    )
    return response.json()
```

### Get Opinion Text
```python
def get_opinion_text(opinion_id):
    response = requests.get(
        f"{base_url}/opinions/{opinion_id}/",
        headers=headers
    )
    data = response.json()
    
    # Try different text fields in order of preference
    text = (data.get('plain_text') or 
            data.get('html') or 
            data.get('xml_harvard') or 
            'No text available')
    
    return text
```

## Important Notes

1. **RECAP Coverage**: Not all documents are available - only those previously purchased
2. **Text Access**: Full OCR text requires permission for `/recap-documents/`
3. **Court IDs**: Match PACER subdomains (e.g., `txed` = Eastern District of Texas)
4. **Error 403**: Usually authentication issue - check "Token " prefix
5. **Deep Pagination**: Use cursor for results beyond page 100

## IP Court Reference

| Court ID | Name | Type |
|----------|------|------|
| `cafc` | Court of Appeals for the Federal Circuit | Appellate |
| `txed` | Eastern District of Texas | District |
| `deld` | District of Delaware | District |
| `cand` | Northern District of California | District |
| `uscfc` | US Court of Federal Claims | Special |

## Nature of Suit Codes

| Code | Description |
|------|-------------|
| 820 | Copyright |
| 830 | Patent |
| 835 | Patent - ANDA |
| 840 | Trademark |
