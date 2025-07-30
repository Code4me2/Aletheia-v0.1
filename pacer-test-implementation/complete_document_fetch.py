#!/usr/bin/env python3
"""
Complete example of fetching and downloading documents from PACER/RECAP
"""

import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

class DocumentFetcher:
    def __init__(self):
        self.cl_token = os.environ.get('COURTLISTENER_TOKEN')
        self.headers = {'Authorization': f'Token {self.cl_token}'}
        self.base_url = 'https://www.courtlistener.com'
    
    def search_case(self, docket_number, court):
        """Search for a case in CourtListener"""
        print(f"\n🔍 Searching for {docket_number} in {court.upper()}")
        
        # First try exact search
        search_url = f"{self.base_url}/api/rest/v4/search/"
        params = {
            'type': 'r',  # RECAP search
            'docket_number': docket_number,
            'court': court,
        }
        
        try:
            response = requests.get(search_url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if results:
                    for result in results[:3]:  # Show first 3 results
                        print(f"\n📋 Found: {result.get('caseName', 'Unknown')}")
                        print(f"   Docket: {result.get('docketNumber', 'N/A')}")
                        print(f"   Court: {result.get('court', 'N/A')}")
                        print(f"   Filed: {result.get('dateFiled', 'N/A')}")
                        
                        # Get the docket ID from the URL
                        docket_url = result.get('docket_absolute_url', '')
                        if docket_url:
                            docket_id = docket_url.split('/')[-2] if docket_url.endswith('/') else docket_url.split('/')[-1]
                            print(f"   Docket ID: {docket_id}")
                            print(f"   URL: {self.base_url}{docket_url}")
                            
                            return {
                                'found': True,
                                'docket_id': docket_id,
                                'case_name': result.get('caseName'),
                                'url': f"{self.base_url}{docket_url}"
                            }
                else:
                    print("   ❌ No results found")
            else:
                print(f"   ❌ Search failed: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error: {e}")
        
        return {'found': False}
    
    def get_docket_entries(self, docket_id):
        """Get all entries for a docket"""
        print(f"\n📚 Getting entries for docket {docket_id}")
        
        entries_url = f"{self.base_url}/api/rest/v4/docket-entries/"
        params = {'docket': docket_id}
        
        try:
            response = requests.get(entries_url, params=params, headers=self.headers)
            if response.status_code == 200:
                data = response.json()
                entries = data.get('results', [])
                
                print(f"   Found {len(entries)} entries")
                
                documents = []
                for entry in entries[:5]:  # First 5 entries
                    entry_num = entry.get('entry_number', '?')
                    desc = entry.get('description', 'No description')
                    
                    print(f"\n   Entry #{entry_num}: {desc[:60]}...")
                    
                    # Check for documents
                    for doc in entry.get('recap_documents', []):
                        doc_desc = doc.get('description', 'Document')
                        filepath = doc.get('filepath_local')
                        
                        if filepath:
                            print(f"      📄 {doc_desc}")
                            print(f"         URL: {self.base_url}{filepath}")
                            
                            documents.append({
                                'entry_number': entry_num,
                                'description': doc_desc,
                                'url': f"{self.base_url}{filepath}",
                                'document_number': doc.get('document_number', ''),
                                'page_count': doc.get('page_count', 0)
                            })
                
                return documents
            else:
                print(f"   ❌ Failed to get entries: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error: {e}")
        
        return []
    
    def download_document(self, doc_url, filename):
        """Download a document"""
        print(f"\n📥 Downloading: {filename}")
        
        try:
            response = requests.get(doc_url, headers=self.headers)
            if response.status_code == 200:
                with open(filename, 'wb') as f:
                    f.write(response.content)
                print(f"   ✅ Saved to: {filename}")
                return True
            else:
                print(f"   ❌ Download failed: {response.status_code}")
                
        except Exception as e:
            print(f"   💥 Error: {e}")
        
        return False


def main():
    """Main function to demonstrate document fetching"""
    print("📋 Complete Document Fetch Example")
    print("=" * 60)
    
    fetcher = DocumentFetcher()
    
    # Test cases
    cases = [
        {'docket': '2:2024cv00162', 'court': 'txed', 'name': 'Byteweavr v. Databricks'},
        {'docket': '3:2024cv00217', 'court': 'cand', 'name': 'DoDots v. Apple'},
    ]
    
    for case in cases[:1]:  # Just test first case
        print(f"\n{'='*60}")
        print(f"Processing: {case['name']}")
        
        # Search for the case
        result = fetcher.search_case(case['docket'], case['court'])
        
        if result['found']:
            # Get docket entries
            documents = fetcher.get_docket_entries(result['docket_id'])
            
            if documents:
                print(f"\n📄 Available Documents:")
                for i, doc in enumerate(documents[:3]):
                    print(f"{i+1}. Entry #{doc['entry_number']}: {doc['description']}")
                    print(f"   Pages: {doc['page_count']}")
                    
                # Example: Download first document
                if documents:
                    first_doc = documents[0]
                    filename = f"{case['docket'].replace(':', '-')}_doc{first_doc['document_number']}.pdf"
                    
                    # Uncomment to actually download:
                    # fetcher.download_document(first_doc['url'], filename)
            else:
                print("   ❌ No documents found")
        else:
            print(f"\n❌ Case not found in RECAP")
            print("   This case may need to be fetched from PACER first")
    
    print("\n" + "="*60)
    print("\n💡 Summary:")
    print("1. Search RECAP first (free)")
    print("2. If not found, use PACER fetch")
    print("3. Documents appear in RECAP after fetch completes")
    print("4. Download PDFs using the filepath URLs")


if __name__ == "__main__":
    main()