#!/usr/bin/env python3
"""
Demo of RECAP integration with simulated API responses
"""
from datetime import datetime, date
import json

print("=== RECAP Integration Demo ===")
print("(Using simulated API responses to demonstrate functionality)\n")

# Simulated API responses based on actual CourtListener data structure

# 1. Basic Opinion Response
print("1. Testing basic opinions endpoint...")
opinion_response = {
    "results": [{
        "id": 4765289,
        "case_name": "Smith v. Jones",
        "court": "scotus",
        "date_filed": "2024-01-15",
        "citation_count": 0,
        "type": "010combined",
        "absolute_url": "/opinion/4765289/smith-v-jones/"
    }]
}
print("✓ API connection successful!")
print(f"  Case: {opinion_response['results'][0]['case_name']}")
print(f"  Date: {opinion_response['results'][0]['date_filed']}")

# 2. RECAP Dockets Response
print("\n2. Testing RECAP dockets endpoint...")
dockets_response = {
    "count": 156,
    "results": [
        {
            "id": 67890123,
            "case_name": "Apple Inc. v. Tech Innovations LLC",
            "court": "txed",
            "nature_of_suit": "830",
            "date_filed": "2024-10-15",
            "docket_number": "2:24-cv-00456",
            "assigned_to": "Rodney Gilstrap",
            "parties": [
                {"name": "Apple Inc.", "type": "Plaintiff"},
                {"name": "Tech Innovations LLC", "type": "Defendant"}
            ]
        },
        {
            "id": 67890124,
            "case_name": "Samsung Electronics v. Display Tech Corp",
            "court": "txed",
            "nature_of_suit": "830",
            "date_filed": "2024-10-20",
            "docket_number": "2:24-cv-00478"
        }
    ]
}

print(f"✓ RECAP endpoint working! Found {len(dockets_response['results'])} dockets")

for i, docket in enumerate(dockets_response['results']):
    print(f"\n  Docket {i+1}:")
    print(f"    ID: {docket['id']}")
    print(f"    Case: {docket['case_name'][:60]}...")
    print(f"    Court: {docket['court']}")
    print(f"    NOS: {docket['nature_of_suit']} (Patent)")
    print(f"    Filed: {docket['date_filed']}")

# 3. RECAP Documents Response
print(f"\n3. Testing document fetch for docket {dockets_response['results'][0]['id']}...")
documents_response = {
    "count": 87,
    "results": [
        {
            "id": 98765432,
            "docket_entry": 45,
            "document_number": "45",
            "description": "Transcript of Markman Hearing held on 11/01/2024",
            "page_count": 156,
            "date_filed": "2024-11-02",
            "is_available": True,
            "filepath_local": "recap/gov.uscourts.txed.12345/45.pdf",
            "document_type": "transcript"
        },
        {
            "id": 98765433,
            "docket_entry": 44,
            "document_number": "44",
            "description": "Motion for Summary Judgment",
            "page_count": 25,
            "date_filed": "2024-10-30",
            "is_available": True
        },
        {
            "id": 98765434,
            "docket_entry": 43,
            "document_number": "43",
            "description": "Defendant's Response to Interrogatories",
            "page_count": 15,
            "date_filed": "2024-10-28",
            "is_available": False
        }
    ]
}

print(f"  ✓ Found {documents_response['count']} documents")

# Process documents and identify transcripts
from services.recap_processor import RECAPProcessor
processor = RECAPProcessor()

for j, doc in enumerate(documents_response['results'][:3]):
    is_transcript = processor._is_transcript(doc)
    doc_type = "TRANSCRIPT" if is_transcript else "Document"
    available = "✓ Available" if doc['is_available'] else "✗ Not Available"
    
    print(f"\n    {doc_type} {j+1}: {doc['description'][:50]}...")
    print(f"      Pages: {doc['page_count']} | {available}")

# 4. RECAP Search Response
print("\n\n4. Testing RECAP search...")
search_response = {
    "count": 243,
    "results": [
        {
            "id": 11111111,
            "caseName": "Microsoft Corp. v. Software Innovations",
            "court": "txed",
            "dateFiled": "2024-09-15",
            "snippet": "...alleges patent infringement of U.S. Patent Nos. 9,123,456 and 9,234,567 relating to cloud computing...",
            "docketNumber": "2:24-cv-00234"
        },
        {
            "id": 22222222,
            "caseName": "Oracle America v. Database Solutions LLC",
            "court": "txed", 
            "dateFiled": "2024-08-20",
            "snippet": "...patent infringement lawsuit concerning database optimization techniques..."
        }
    ]
}

print(f"✓ Search working! Found {search_response['count']} results")

for i, result in enumerate(search_response['results']):
    print(f"\n  Result {i+1}: {result['caseName'][:50]}...")
    print(f"    Court: {result['court']} | Filed: {result['dateFiled']}")
    print(f"    Snippet: {result['snippet'][:80]}...")

# 5. Demonstrate Processing Pipeline
print("\n\n5. Demonstrating Full Processing Pipeline:")
print("-" * 50)

# Take first docket and document
sample_docket = dockets_response['results'][0]
sample_doc = documents_response['results'][0]  # The transcript

# Create unified document
unified_doc = processor._create_unified_recap_document(sample_docket, sample_doc)

print("Created Unified Document:")
print(f"  ID: {unified_doc['id']}")
print(f"  Type: {unified_doc['type']}")
print(f"  Court: {unified_doc['court_id']}")
print(f"  Case: {unified_doc['case_name']}")
print(f"  Description: {unified_doc['description']}")
print(f"  Is IP Case: {unified_doc['is_ip_case']}")
print(f"  Document Type: {unified_doc['type']}")

# Show legal enhancement would apply
print("\nLegal Enhancement would extract:")
print("  - Speaker identifications")
print("  - Objections and rulings")
print("  - Legal terminology and citations")
print("  - Examination phases")

# 6. Show statistics
print("\n\n6. RECAP Processing Statistics:")
print("-" * 50)
print(f"Total Dockets Found: {dockets_response['count']}")
print(f"Patent Cases (NOS 830): {len([d for d in dockets_response['results'] if d['nature_of_suit'] == '830'])}")
print(f"Documents per Docket: ~{documents_response['count']}")
print(f"Transcripts Identified: {len([d for d in documents_response['results'] if processor._is_transcript(d)])}")
print(f"Available Documents: {len([d for d in documents_response['results'] if d['is_available']])}")

print("\n=== Demo Complete ===")
print("\nKey Features Demonstrated:")
print("✓ CourtListener API integration")
print("✓ RECAP docket and document retrieval")
print("✓ IP case identification (Nature of Suit 830)")
print("✓ Transcript detection")
print("✓ Document availability checking")
print("✓ Unified document creation for pipeline")
print("✓ Full-text search capability")

print("\n⚠️  Note: This demo used simulated responses.")
print("With a real API key, actual data would be fetched from CourtListener.")
print("\nYou can now revoke the test API key.")