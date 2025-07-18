#!/usr/bin/env python3
"""
Improved Haystack Ingestion for Judge Gilstrap Documents

Fixes metadata extraction and enhances document indexing to improve agent retrieval.
"""

import asyncio
import json
import re
import time
import requests
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.utils.logging import get_logger

class ImprovedHaystackIngester:
    """Improved Haystack ingestion with proper metadata extraction"""
    
    def __init__(self, haystack_url: str = "http://localhost:8000"):
        self.haystack_url = haystack_url
        self.logger = get_logger("improved_haystack")
        self.stats = {
            'processed': 0,
            'improved': 0,
            'failed': 0,
            'gilstrap_docs': 0
        }
    
    def check_haystack_health(self) -> bool:
        """Check if Haystack service is available"""
        try:
            response = requests.get(f"{self.haystack_url}/health", timeout=5)
            if response.status_code == 200:
                health_data = response.json()
                self.logger.info(f"Haystack service healthy: {health_data.get('status')}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Haystack health check failed: {e}")
            return False
    
    def get_current_documents(self, query: str = "Gilstrap", limit: int = 50) -> List[Dict[str, Any]]:
        """Get current documents from Haystack"""
        try:
            response = requests.post(
                f"{self.haystack_url}/search",
                json={"query": query, "top_k": limit},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('results', [])
                self.logger.info(f"Retrieved {len(documents)} documents for processing")
                return documents
            else:
                self.logger.error(f"Search failed: {response.status_code}")
                return []
                
        except Exception as e:
            self.logger.error(f"Failed to retrieve documents: {str(e)}")
            return []
    
    def extract_enhanced_metadata(self, content: str) -> Dict[str, Any]:
        """Extract enhanced metadata from document content"""
        metadata = {
            'case_name': 'Unknown Case',
            'judge_name': '',
            'court_name': '',
            'docket_number': '',
            'date_filed': '',
            'case_type': '',
            'citations': [],
            'legal_issues': [],
            'parties': {},
            'nature_of_suit': ''
        }
        
        try:
            # Extract case name from header
            case_match = re.search(r'([A-Z][A-Z\s,\.]+)\s+v\.\s+([A-Z][A-Z\s,\.]+)', content, re.MULTILINE)
            if case_match:
                plaintiff = case_match.group(1).strip()
                defendant = case_match.group(2).strip()
                metadata['case_name'] = f"{plaintiff} v. {defendant}"
                metadata['parties'] = {
                    'plaintiff': plaintiff,
                    'defendant': defendant
                }
            
            # Extract civil action number
            civil_action_match = re.search(r'Civil Action No\.?\s+(\S+)', content, re.IGNORECASE)
            if civil_action_match:
                metadata['docket_number'] = civil_action_match.group(1).strip()
            
            # Extract judge information
            judge_patterns = [
                r'Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'United States District Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'District Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
                r'Chief Judge\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
            ]
            
            for pattern in judge_patterns:
                judge_match = re.search(pattern, content, re.IGNORECASE)
                if judge_match:
                    judge_name = judge_match.group(1).strip()
                    if 'gilstrap' in judge_name.lower():
                        metadata['judge_name'] = judge_name
                        break
            
            # Extract court information
            court_patterns = [
                r'IN THE UNITED STATES DISTRICT COURT\s+FOR THE ([A-Z\s]+DISTRICT OF [A-Z]+)',
                r'UNITED STATES DISTRICT COURT\s+FOR THE ([A-Z\s]+DISTRICT OF [A-Z]+)',
                r'DISTRICT COURT\s+FOR THE ([A-Z\s]+DISTRICT OF [A-Z]+)'
            ]
            
            for pattern in court_patterns:
                court_match = re.search(pattern, content, re.IGNORECASE)
                if court_match:
                    metadata['court_name'] = court_match.group(1).strip()
                    break
            
            # Extract citations
            citation_patterns = [
                r'\d+\s+U\.S\.?\s+\d+',  # US Reports
                r'\d+\s+S\.?\s*Ct\.?\s+\d+',  # Supreme Court Reporter
                r'\d+\s+F\.?\s*\d*d?\s+\d+',  # Federal Reporter
                r'\d+\s+F\.?\s*Supp\.?\s*\d*d?\s+\d+',  # Federal Supplement
                r'Fed\.?\s*R\.?\s*Civ\.?\s*P\.?\s*\d+',  # Federal Rules
                r'\d+\s+U\.S\.C\.?\s*§?\s*\d+'  # US Code
            ]
            
            citations = set()
            for pattern in citation_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    citation = match.group().strip()
                    citations.add(citation)
            
            metadata['citations'] = list(citations)[:20]  # Limit to first 20
            
            # Extract legal issues/topics
            legal_issue_keywords = [
                'patent', 'copyright', 'trademark', 'infringement',
                'summary judgment', 'motion to dismiss', 'preliminary injunction',
                'damages', 'licensing', 'validity', 'claim construction',
                'obviousness', 'anticipation', 'enablement', 'written description'
            ]
            
            legal_issues = []
            content_lower = content.lower()
            for keyword in legal_issue_keywords:
                if keyword in content_lower:
                    legal_issues.append(keyword)
            
            metadata['legal_issues'] = legal_issues[:10]  # Limit to first 10
            
            # Determine case type
            if any(word in content_lower for word in ['patent', 'patent infringement']):
                metadata['case_type'] = 'Patent'
            elif any(word in content_lower for word in ['copyright', 'dmca']):
                metadata['case_type'] = 'Copyright'
            elif any(word in content_lower for word in ['trademark', 'service mark']):
                metadata['case_type'] = 'Trademark'
            elif 'civil' in content_lower:
                metadata['case_type'] = 'Civil'
            else:
                metadata['case_type'] = 'General'
            
            # Extract date filed from content
            date_patterns = [
                r'filed?\s+(?:on\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
                r'(\d{1,2}/\d{1,2}/\d{4})',
                r'(\d{4}-\d{2}-\d{2})'
            ]
            
            for pattern in date_patterns:
                date_match = re.search(pattern, content, re.IGNORECASE)
                if date_match:
                    metadata['date_filed'] = date_match.group(1).strip()
                    break
            
            self.logger.debug(f"Extracted metadata: {metadata}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed: {str(e)}")
            return metadata
    
    def create_enhanced_document(self, original_doc: Dict[str, Any]) -> Dict[str, Any]:
        """Create enhanced document with improved metadata"""
        
        content = original_doc.get('content', '')
        original_metadata = original_doc.get('metadata', {})
        
        # Extract enhanced metadata from content
        enhanced_metadata = self.extract_enhanced_metadata(content)
        
        # Check if this is a Gilstrap document
        is_gilstrap = (
            'gilstrap' in content.lower() or
            'rodney gilstrap' in content.lower() or
            enhanced_metadata['judge_name'].lower().find('gilstrap') != -1
        )
        
        if is_gilstrap:
            self.stats['gilstrap_docs'] += 1
        
        # Create enhanced metadata
        final_metadata = {
            # Core identification
            'source': 'courtlistener',
            'document_type': 'court_opinion',
            'document_id': original_doc.get('document_id'),
            
            # Case information
            'case_name': enhanced_metadata['case_name'],
            'docket_number': enhanced_metadata['docket_number'],
            'date_filed': enhanced_metadata['date_filed'],
            'case_type': enhanced_metadata['case_type'],
            'nature_of_suit': enhanced_metadata['nature_of_suit'],
            
            # Court and judge information
            'court': enhanced_metadata['court_name'] or 'Eastern District of Texas',
            'judge_name': enhanced_metadata['judge_name'],
            'assigned_to': enhanced_metadata['judge_name'],
            
            # Legal content
            'citations': enhanced_metadata['citations'],
            'citation_count': len(enhanced_metadata['citations']),
            'legal_issues': enhanced_metadata['legal_issues'],
            'parties': enhanced_metadata['parties'],
            
            # Processing metadata
            'is_gilstrap_case': is_gilstrap,
            'enhanced_timestamp': datetime.now().isoformat(),
            'content_length': len(content),
            'enhancement_version': '2.0',
            
            # Search optimization
            'searchable_text': self.create_searchable_text(enhanced_metadata, content),
            'keywords': self.extract_keywords(content),
            
            # Original metadata preservation
            'original_metadata': original_metadata
        }
        
        # Merge with any existing good metadata
        for key, value in original_metadata.items():
            if value and value != 'Unknown Case' and key not in final_metadata:
                final_metadata[key] = value
        
        # Create enhanced document
        enhanced_doc = {
            'content': content,
            'meta': final_metadata
        }
        
        return enhanced_doc
    
    def create_searchable_text(self, metadata: Dict[str, Any], content: str) -> str:
        """Create optimized searchable text"""
        searchable_parts = []
        
        # Add case information
        if metadata['case_name'] != 'Unknown Case':
            searchable_parts.append(f"Case: {metadata['case_name']}")
        
        if metadata['judge_name']:
            searchable_parts.append(f"Judge: {metadata['judge_name']}")
        
        if metadata['court_name']:
            searchable_parts.append(f"Court: {metadata['court_name']}")
        
        if metadata['docket_number']:
            searchable_parts.append(f"Docket: {metadata['docket_number']}")
        
        if metadata['case_type']:
            searchable_parts.append(f"Type: {metadata['case_type']}")
        
        # Add legal issues
        if metadata['legal_issues']:
            searchable_parts.append(f"Issues: {', '.join(metadata['legal_issues'])}")
        
        # Add citations
        if metadata['citations']:
            searchable_parts.append(f"Citations: {', '.join(metadata['citations'][:5])}")
        
        # Add parties
        if metadata['parties']:
            parties = metadata['parties']
            if parties.get('plaintiff'):
                searchable_parts.append(f"Plaintiff: {parties['plaintiff']}")
            if parties.get('defendant'):
                searchable_parts.append(f"Defendant: {parties['defendant']}")
        
        # Add original content
        searchable_parts.append(content)
        
        return '\n'.join(searchable_parts)
    
    def extract_keywords(self, content: str) -> List[str]:
        """Extract key terms for search optimization"""
        keywords = set()
        
        # Legal terms
        legal_terms = [
            'patent', 'copyright', 'trademark', 'infringement', 'damages',
            'injunction', 'summary judgment', 'motion', 'claim construction',
            'validity', 'obviousness', 'anticipation', 'licensing'
        ]
        
        content_lower = content.lower()
        for term in legal_terms:
            if term in content_lower:
                keywords.add(term)
        
        # Extract capitalized terms (likely proper nouns)
        capitalized_terms = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', content)
        for term in capitalized_terms[:20]:  # Limit to first 20
            if len(term) > 3 and not term.lower() in ['the', 'and', 'for', 'with']:
                keywords.add(term.lower())
        
        return list(keywords)[:30]  # Limit to 30 keywords
    
    def update_document_in_haystack(self, enhanced_doc: Dict[str, Any]) -> bool:
        """Update document in Haystack with enhanced metadata"""
        try:
            # Use the ingest endpoint to update the document
            payload = {
                "documents": [enhanced_doc]
            }
            
            response = requests.post(
                f"{self.haystack_url}/ingest",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                self.logger.info(f"Successfully updated document: {enhanced_doc['meta'].get('case_name')}")
                return True
            else:
                self.logger.error(f"Update failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to update document: {str(e)}")
            return False
    
    async def improve_all_documents(self, query: str = "Gilstrap") -> Dict[str, Any]:
        """Improve all documents matching the query"""
        self.logger.info(f"Starting document improvement for query: '{query}'")
        
        # Check service health
        if not self.check_haystack_health():
            self.logger.error("Haystack service is not available")
            return self.stats
        
        # Get current documents
        documents = self.get_current_documents(query, limit=100)
        self.logger.info(f"Found {len(documents)} documents to improve")
        
        for i, doc in enumerate(documents):
            try:
                self.logger.info(f"Processing document {i+1}/{len(documents)}")
                
                # Create enhanced document
                enhanced_doc = self.create_enhanced_document(doc)
                
                # Update in Haystack
                if self.update_document_in_haystack(enhanced_doc):
                    self.stats['improved'] += 1
                else:
                    self.stats['failed'] += 1
                
                self.stats['processed'] += 1
                
                # Rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Failed to process document {i}: {str(e)}")
                self.stats['failed'] += 1
        
        return self.stats
    
    def test_improved_search(self, query: str = "Judge Gilstrap patent") -> bool:
        """Test search functionality with improved documents"""
        try:
            self.logger.info(f"Testing search with query: '{query}'")
            
            response = requests.post(
                f"{self.haystack_url}/search",
                json={"query": query, "top_k": 5},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                documents = results.get('results', [])
                
                self.logger.info(f"Search test returned {len(documents)} results:")
                for i, doc in enumerate(documents):
                    meta = doc.get('metadata', {})
                    case_name = meta.get('case_name', 'Unknown')
                    judge = meta.get('judge_name', 'Unknown')
                    score = doc.get('score', 0)
                    
                    self.logger.info(f"  {i+1}. {case_name} (Judge: {judge}) - Score: {score:.3f}")
                
                return len(documents) > 0
            else:
                self.logger.error(f"Search test failed: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Search test error: {str(e)}")
            return False
    
    def print_statistics(self):
        """Print improvement statistics"""
        self.logger.info("\n" + "="*60)
        self.logger.info("HAYSTACK IMPROVEMENT COMPLETE")
        self.logger.info("="*60)
        self.logger.info(f"Total documents processed: {self.stats['processed']}")
        self.logger.info(f"Successfully improved: {self.stats['improved']}")
        self.logger.info(f"Failed improvements: {self.stats['failed']}")
        self.logger.info(f"Gilstrap documents found: {self.stats['gilstrap_docs']}")
        
        if self.stats['processed'] > 0:
            success_rate = (self.stats['improved'] / self.stats['processed']) * 100
            self.logger.info(f"Success rate: {success_rate:.1f}%")
        
        self.logger.info("="*60)


async def main():
    """Main function to run the improvement process"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Improve Haystack document metadata for better agent retrieval')
    parser.add_argument('--query', default='Gilstrap', help='Query to find documents to improve')
    parser.add_argument('--haystack-url', default='http://localhost:8000', help='Haystack service URL')
    parser.add_argument('--test-search', action='store_true', help='Test search after improvement')
    
    args = parser.parse_args()
    
    # Create improver
    improver = ImprovedHaystackIngester(args.haystack_url)
    
    # Run improvement process
    stats = await improver.improve_all_documents(args.query)
    
    # Print statistics
    improver.print_statistics()
    
    # Test search if requested
    if args.test_search:
        print("\n" + "="*60)
        print("TESTING IMPROVED SEARCH")
        print("="*60)
        
        test_queries = [
            "Judge Gilstrap patent",
            "Rodney Gilstrap",
            "Eastern District Texas",
            "patent infringement Gilstrap",
            "CLO Virtual Fashion"
        ]
        
        for query in test_queries:
            print(f"\nTesting query: '{query}'")
            improver.test_improved_search(query)
    
    return stats['improved'] > 0


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        print(f"\n{'✅ Improvement successful!' if success else '❌ Improvement failed'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)