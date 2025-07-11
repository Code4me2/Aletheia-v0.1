#!/usr/bin/env python3
"""
Prepare CourtListener data for RAG (Retrieval-Augmented Generation)
Converts downloaded JSON data into structured documents for vector indexing
"""

import os
import json
import glob
from datetime import datetime
from typing import Dict, List

def load_courtlistener_data(court_id: str = 'txed') -> List[Dict]:
    """Load all downloaded JSON files for a court"""
    data_dir = f"/data/courtlistener/{court_id}"
    all_documents = []
    
    # Load dockets
    docket_files = glob.glob(f"{data_dir}/dockets_page_*.json")
    print(f"Found {len(docket_files)} docket files")
    
    for file_path in sorted(docket_files):
        with open(file_path, 'r') as f:
            dockets = json.load(f)
            all_documents.extend([{'type': 'docket', 'data': d} for d in dockets])
    
    # Load opinions
    opinion_files = glob.glob(f"{data_dir}/opinions_page_*.json")
    print(f"Found {len(opinion_files)} opinion files")
    
    for file_path in sorted(opinion_files):
        with open(file_path, 'r') as f:
            opinions = json.load(f)
            all_documents.extend([{'type': 'opinion', 'data': d} for d in opinions])
    
    return all_documents

def prepare_docket_for_rag(docket: Dict) -> Dict:
    """Convert a docket into a document suitable for RAG"""
    # Extract key information
    doc = {
        'id': f"docket_{docket['id']}",
        'type': 'court_docket',
        'court': 'txed',
        'title': docket.get('case_name', 'Unknown Case'),
        'case_number': docket.get('docket_number', ''),
        'date_filed': docket.get('date_filed', ''),
        'nature_of_suit': docket.get('nature_of_suit', ''),
        'assigned_to': docket.get('assigned_to_str', ''),
        'parties': [],
        'metadata': {
            'source': 'courtlistener',
            'court_full': 'Eastern District of Texas',
            'url': docket.get('absolute_url', ''),
            'date_terminated': docket.get('date_terminated'),
            'cause': docket.get('cause', ''),
            'jury_demand': docket.get('jury_demand', '')
        }
    }
    
    # Create searchable text
    text_parts = [
        f"Case: {doc['title']}",
        f"Case Number: {doc['case_number']}",
        f"Court: Eastern District of Texas",
        f"Filed: {doc['date_filed']}",
    ]
    
    if doc['assigned_to']:
        text_parts.append(f"Judge: {doc['assigned_to']}")
    
    if doc['nature_of_suit']:
        text_parts.append(f"Nature of Suit: {doc['nature_of_suit']}")
        
        # Check if it's a patent case
        if doc['nature_of_suit'] in ['830', '835', '840']:
            doc['metadata']['is_patent'] = True
            text_parts.append("Type: Patent Case")
    
    # Check case name for patent indicators
    case_lower = doc['title'].lower()
    if any(term in case_lower for term in ['patent', 'infringement', '35 u.s.c.']):
        doc['metadata']['is_patent'] = True
        text_parts.append("Type: Patent Case")
    
    doc['content'] = '\n'.join(text_parts)
    
    return doc

def prepare_opinion_for_rag(opinion: Dict) -> Dict:
    """Convert an opinion into a document suitable for RAG"""
    doc = {
        'id': f"opinion_{opinion['id']}",
        'type': 'court_opinion',
        'court': 'txed',
        'title': f"Opinion in Case {opinion.get('cluster_id', 'Unknown')}",
        'author': opinion.get('author_str', ''),
        'date_created': opinion.get('date_created', ''),
        'opinion_type': opinion.get('type', ''),
        'metadata': {
            'source': 'courtlistener',
            'court_full': 'Eastern District of Texas',
            'url': opinion.get('absolute_url', ''),
            'download_url': opinion.get('download_url', ''),
            'has_text': bool(opinion.get('plain_text') or opinion.get('html'))
        }
    }
    
    # Extract text content
    text_parts = [
        f"Court Opinion - Eastern District of Texas",
        f"Date: {doc['date_created']}",
    ]
    
    if doc['author']:
        text_parts.append(f"Author: {doc['author']}")
    
    # Add the actual opinion text if available
    if opinion.get('plain_text'):
        text_parts.append("\n--- Opinion Text ---")
        text_parts.append(opinion['plain_text'][:5000])  # First 5000 chars
        doc['full_text'] = opinion['plain_text']
    elif opinion.get('html'):
        # Strip HTML tags for searchable text
        import re
        clean_text = re.sub('<.*?>', '', opinion['html'])
        text_parts.append("\n--- Opinion Text ---")
        text_parts.append(clean_text[:5000])
        doc['full_text'] = clean_text
    
    doc['content'] = '\n'.join(text_parts)
    
    return doc

def generate_rag_documents(court_id: str = 'txed', output_file: str = None):
    """Generate RAG-ready documents from CourtListener data"""
    print(f"Loading data for {court_id}...")
    documents = load_courtlistener_data(court_id)
    print(f"Total documents loaded: {len(documents)}")
    
    rag_documents = []
    stats = {
        'dockets': 0,
        'opinions': 0,
        'patent_cases': 0,
        'opinions_with_text': 0
    }
    
    for doc in documents:
        if doc['type'] == 'docket':
            rag_doc = prepare_docket_for_rag(doc['data'])
            rag_documents.append(rag_doc)
            stats['dockets'] += 1
            if rag_doc['metadata'].get('is_patent'):
                stats['patent_cases'] += 1
                
        elif doc['type'] == 'opinion':
            rag_doc = prepare_opinion_for_rag(doc['data'])
            rag_documents.append(rag_doc)
            stats['opinions'] += 1
            if rag_doc['metadata'].get('has_text'):
                stats['opinions_with_text'] += 1
    
    # Save to file if specified
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(rag_documents, f, indent=2)
        print(f"Saved {len(rag_documents)} documents to {output_file}")
    
    # Print statistics
    print("\n=== Statistics ===")
    print(f"Total RAG documents: {len(rag_documents)}")
    print(f"Dockets: {stats['dockets']}")
    print(f"Patent cases: {stats['patent_cases']}")
    print(f"Opinions: {stats['opinions']}")
    print(f"Opinions with text: {stats['opinions_with_text']}")
    
    # Show sample documents
    print("\n=== Sample Documents ===")
    
    # Show a patent case if found
    patent_docs = [d for d in rag_documents if d.get('metadata', {}).get('is_patent')]
    if patent_docs:
        print("\nSample Patent Case:")
        print("-" * 50)
        print(patent_docs[0]['content'])
    
    # Show an opinion with text
    opinion_docs = [d for d in rag_documents if d['type'] == 'court_opinion' and d['metadata'].get('has_text')]
    if opinion_docs:
        print("\nSample Opinion:")
        print("-" * 50)
        print(opinion_docs[0]['content'][:500] + "...")
    
    return rag_documents

def main():
    """Main entry point"""
    output_file = "/data/courtlistener/txed/rag_documents.json"
    documents = generate_rag_documents('txed', output_file)
    
    print(f"\n✓ RAG preparation complete!")
    print(f"  Documents are ready for vector indexing")
    print(f"  Output saved to: {output_file}")
    
    # Show how to integrate with existing Haystack
    print("\n=== Next Steps for RAG Integration ===")
    print("1. Load these documents into your vector database (Elasticsearch/Haystack)")
    print("2. Generate embeddings using your embedding model")
    print("3. Index documents for semantic search")
    print("4. Query using natural language for legal research")
    
    print("\nExample integration code:")
    print("```python")
    print("# Load prepared documents")
    print("with open('/data/courtlistener/txed/rag_documents.json') as f:")
    print("    documents = json.load(f)")
    print("")
    print("# Send to Haystack for indexing")
    print("for doc in documents:")
    print("    haystack_api.index_document(doc)")
    print("```")

if __name__ == "__main__":
    main()