#!/usr/bin/env python3
"""
Simple test of RECAP integration components
"""
import re
from datetime import datetime, date

print("=== Testing RECAP Integration Components ===\n")

# Test 1: IP Case Detection Logic
print("1. Testing IP Case Detection:")
def is_ip_case(docket_data):
    nature_of_suit = docket_data.get('nature_of_suit')
    ip_codes = ['820', '830', '835', '840']
    if nature_of_suit in ip_codes:
        return True
    
    case_name = docket_data.get('case_name', '').lower()
    ip_keywords = ['patent', 'trademark', 'copyright', 'infringement', 
                  'intellectual property', '(ptab)', 'inter partes']
    return any(keyword in case_name for keyword in ip_keywords)

test_cases = [
    {'nature_of_suit': '830', 'case_name': 'Apple v. Samsung', 'expected': True},
    {'nature_of_suit': '840', 'case_name': 'Nike v. Adidas', 'expected': True},
    {'nature_of_suit': '440', 'case_name': 'Contract Dispute', 'expected': False},
    {'nature_of_suit': '190', 'case_name': 'Patent Holder v. Tech', 'expected': True}
]

for case in test_cases:
    result = is_ip_case(case)
    status = "✓" if result == case['expected'] else "✗"
    print(f"  {status} {case['case_name']}: {result}")

# Test 2: Transcript Detection
print("\n2. Testing Transcript Detection:")
def is_transcript(document):
    description = document.get('description', '').lower()
    transcript_keywords = ['transcript', 'hearing', 'trial', 'deposition',
                         'oral argument', 'proceedings']
    
    if any(keyword in description for keyword in transcript_keywords):
        return True
    
    if document.get('document_type') == 'transcript':
        return True
    
    page_count = document.get('page_count', 0)
    if page_count > 50 and 'minute' not in description:
        return 'hearing' in description or 'trial' in description
    
    return False

test_docs = [
    {'description': 'Transcript of Jury Trial', 'expected': True},
    {'description': 'Motion Hearing Transcript', 'expected': True},
    {'description': 'Motion to Dismiss', 'expected': False},
    {'description': 'Order Granting Summary Judgment', 'expected': False}
]

for doc in test_docs:
    result = is_transcript(doc)
    status = "✓" if result == doc['expected'] else "✗"
    print(f"  {status} {doc['description']}: {result}")

# Test 3: Legal Pattern Matching
print("\n3. Testing Legal Pattern Matching:")

speaker_patterns = [
    r'^(THE COURT|JUDGE [A-Z]+):',
    r'^(MR\.|MS\.) [A-Z]+:',
]

objection_patterns = [
    r'\b(Objection|I object)\b',
    r'\b(Hearsay|Relevance|Foundation)\b'
]

ruling_patterns = [
    r'\b(Sustained|Overruled)\b',
]

test_text = """
THE COURT: Good morning, counsel.
MR. SMITH: Good morning, Your Honor.
MS. JONES: Objection, Your Honor. Hearsay.
THE COURT: Overruled.
"""

lines = test_text.strip().split('\n')
speakers_found = set()
objections = 0
rulings = 0

for line in lines:
    # Check speakers
    for pattern in speaker_patterns:
        if match := re.match(pattern, line):
            speakers_found.add(match.group(1))
    
    # Check objections
    if any(re.search(pattern, line, re.I) for pattern in objection_patterns):
        objections += 1
        print(f"  Found objection: {line.strip()}")
    
    # Check rulings
    if any(re.search(pattern, line, re.I) for pattern in ruling_patterns):
        rulings += 1
        print(f"  Found ruling: {line.strip()}")

print(f"\n  Summary: {len(speakers_found)} speakers, {objections} objections, {rulings} rulings")

# Test 4: Document Hash Generation
print("\n4. Testing Document Deduplication:")
import hashlib
import json

def generate_hash(document):
    hash_fields = {
        'court_id': document.get('court_id', ''),
        'docket_number': document.get('docket_number', ''),
        'case_name': document.get('case_name', ''),
        'date_filed': str(document.get('date_filed', '')),
        'text_preview': document.get('plain_text', '')[:1000]
    }
    hash_string = json.dumps(hash_fields, sort_keys=True)
    return hashlib.sha256(hash_string.encode()).hexdigest()

doc1 = {'court_id': 'txed', 'docket_number': '2:24-cv-123', 'case_name': 'Test v. Case'}
doc2 = doc1.copy()
doc3 = {'court_id': 'txed', 'docket_number': '2:24-cv-124', 'case_name': 'Test v. Case'}

hash1 = generate_hash(doc1)
hash2 = generate_hash(doc2)
hash3 = generate_hash(doc3)

print(f"  Doc1 hash: {hash1[:16]}...")
print(f"  Doc2 hash: {hash2[:16]}... (same as doc1: {hash1 == hash2})")
print(f"  Doc3 hash: {hash3[:16]}... (different: {hash1 != hash3})")

# Test 5: CourtListener URL Construction
print("\n5. Testing API URL Construction:")

base_url = "https://www.courtlistener.com"
endpoints = {
    'opinions': '/api/rest/v4/opinions/',
    'dockets': '/api/rest/v4/dockets/',
    'documents': '/api/rest/v4/recap-documents/',
    'search': '/api/rest/v4/search/'
}

params = {
    'court__in': 'txed,deld',
    'nature_of_suit__in': '830,840',
    'date_filed__gte': '2024-01-01',
    'page_size': 100
}

from urllib.parse import urlencode
query_string = urlencode(params)
full_url = f"{base_url}{endpoints['dockets']}?{query_string}"

print(f"  Dockets URL: {full_url[:80]}...")
print(f"  Search URL: {base_url}{endpoints['search']}?type=r&q=patent")

# Test 6: RECAP Document Structure
print("\n6. Testing Unified Document Creation:")

def create_unified_document(docket_data, doc_data):
    return {
        'id': f"recap_{doc_data.get('id')}",
        'source': 'recap',
        'court_id': docket_data.get('court'),
        'docket_number': docket_data.get('docket_number'),
        'case_name': docket_data.get('case_name'),
        'document_number': doc_data.get('document_number'),
        'description': doc_data.get('description'),
        'date_filed': doc_data.get('date_filed'),
        'is_ip_case': is_ip_case(docket_data),
        'document_type': 'transcript' if is_transcript(doc_data) else 'document'
    }

sample_docket = {
    'id': 12345,
    'court': 'txed',
    'case_name': 'Apple v. Samsung',
    'nature_of_suit': '830',
    'docket_number': '2:24-cv-00123'
}

sample_doc = {
    'id': 67890,
    'document_number': '42',
    'description': 'Transcript of Claim Construction Hearing',
    'date_filed': '2024-03-01'
}

unified = create_unified_document(sample_docket, sample_doc)
print(f"  Created document:")
for key, value in unified.items():
    print(f"    {key}: {value}")

print("\n=== All component tests completed ===")
print(f"Note: These are unit tests. Full integration requires API key and services running.")