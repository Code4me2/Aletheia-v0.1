#!/usr/bin/env python3
"""
Test Agent Retrieval of Judge Gilstrap Information

This script tests whether an agent can now successfully retrieve Gilstrap information
from the improved Haystack index.
"""

import requests
import json
import sys
from datetime import datetime

class AgentRetrievalTester:
    """Test agent retrieval functionality with enhanced Haystack data"""
    
    def __init__(self, haystack_url: str = "http://localhost:8000"):
        self.haystack_url = haystack_url
        self.test_queries = [
            "Judge Rodney Gilstrap patent cases",
            "Eastern District of Texas patent infringement",
            "Gilstrap preliminary injunction",
            "claim construction Markman hearing",
            "summary judgment patent case",
            "Enhanced Pipeline Technologies patent"
        ]
    
    def test_search_retrieval(self, query: str, top_k: int = 3) -> dict:
        """Test search retrieval for a specific query"""
        try:
            response = requests.post(
                f"{self.haystack_url}/search",
                json={"query": query, "top_k": top_k},
                timeout=10
            )
            
            if response.status_code == 200:
                results = response.json()
                return {
                    "success": True,
                    "query": query,
                    "total_results": results.get("total_results", 0),
                    "documents": results.get("results", []),
                    "search_type": results.get("search_type", "unknown")
                }
            else:
                return {
                    "success": False,
                    "query": query,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "query": query,
                "error": str(e)
            }
    
    def extract_gilstrap_info(self, content: str) -> dict:
        """Extract Judge Gilstrap information from document content"""
        gilstrap_info = {
            "judge_found": False,
            "judge_name": None,
            "court": None,
            "case_name": None,
            "patent_case": False,
            "legal_topics": [],
            "case_number": None
        }
        
        content_lower = content.lower()
        
        # Check for Judge Gilstrap
        if "gilstrap" in content_lower:
            gilstrap_info["judge_found"] = True
            if "rodney gilstrap" in content_lower:
                gilstrap_info["judge_name"] = "Rodney Gilstrap"
        
        # Extract court information
        if "eastern district of texas" in content_lower:
            gilstrap_info["court"] = "Eastern District of Texas"
        
        # Check if patent case
        if any(term in content_lower for term in ["patent", "infringement", "claim construction"]):
            gilstrap_info["patent_case"] = True
        
        # Extract legal topics
        legal_terms = ["preliminary injunction", "summary judgment", "claim construction", 
                      "patent infringement", "markman", "obviousness", "validity"]
        for term in legal_terms:
            if term in content_lower:
                gilstrap_info["legal_topics"].append(term)
        
        # Try to extract case name (basic pattern)
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if 'v.' in line and len(line) < 200:  # Likely case title
                gilstrap_info["case_name"] = line.strip()
                break
        
        # Try to extract case number
        import re
        case_num_pattern = r'Civil Action No\.?\s+([0-9:-]+)'
        match = re.search(case_num_pattern, content, re.IGNORECASE)
        if match:
            gilstrap_info["case_number"] = match.group(1)
        
        return gilstrap_info
    
    def run_comprehensive_test(self) -> dict:
        """Run comprehensive retrieval test"""
        print("=" * 80)
        print("AGENT RETRIEVAL TEST FOR JUDGE GILSTRAP INFORMATION")
        print("=" * 80)
        print(f"Testing at: {datetime.now().isoformat()}")
        print(f"Haystack URL: {self.haystack_url}")
        print()
        
        test_results = {
            "overall_success": True,
            "queries_tested": len(self.test_queries),
            "successful_queries": 0,
            "failed_queries": 0,
            "gilstrap_documents_found": 0,
            "patent_cases_found": 0,
            "query_results": []
        }
        
        for i, query in enumerate(self.test_queries, 1):
            print(f"[{i}/{len(self.test_queries)}] Testing query: '{query}'")
            
            # Test search
            search_result = self.test_search_retrieval(query)
            
            if search_result["success"]:
                test_results["successful_queries"] += 1
                print(f"  ✅ Search successful: {search_result['total_results']} results")
                
                # Analyze each document
                for j, doc in enumerate(search_result["documents"]):
                    content = doc.get("content", "")
                    score = doc.get("score", 0)
                    
                    print(f"     Document {j+1}: Score {score:.3f}")
                    
                    # Extract Gilstrap information
                    gilstrap_info = self.extract_gilstrap_info(content)
                    
                    if gilstrap_info["judge_found"]:
                        test_results["gilstrap_documents_found"] += 1
                        print(f"       🎯 Judge Gilstrap found!")
                        
                        if gilstrap_info["judge_name"]:
                            print(f"       👨‍⚖️ Judge: {gilstrap_info['judge_name']}")
                        
                        if gilstrap_info["court"]:
                            print(f"       🏛️ Court: {gilstrap_info['court']}")
                        
                        if gilstrap_info["case_name"]:
                            print(f"       📁 Case: {gilstrap_info['case_name']}")
                        
                        if gilstrap_info["case_number"]:
                            print(f"       🔢 Number: {gilstrap_info['case_number']}")
                        
                        if gilstrap_info["patent_case"]:
                            test_results["patent_cases_found"] += 1
                            print(f"       ⚖️ Patent case confirmed")
                        
                        if gilstrap_info["legal_topics"]:
                            print(f"       📚 Topics: {', '.join(gilstrap_info['legal_topics'])}")
                    
                    else:
                        print(f"       ❌ No Gilstrap information found")
                
                search_result["gilstrap_analysis"] = [
                    self.extract_gilstrap_info(doc.get("content", "")) 
                    for doc in search_result["documents"]
                ]
                
            else:
                test_results["failed_queries"] += 1
                test_results["overall_success"] = False
                print(f"  ❌ Search failed: {search_result['error']}")
            
            test_results["query_results"].append(search_result)
            print()
        
        return test_results
    
    def print_summary(self, results: dict):
        """Print test summary"""
        print("=" * 80)
        print("AGENT RETRIEVAL TEST SUMMARY")
        print("=" * 80)
        
        success_rate = (results["successful_queries"] / results["queries_tested"]) * 100
        print(f"Overall Success: {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
        print(f"Query Success Rate: {success_rate:.1f}% ({results['successful_queries']}/{results['queries_tested']})")
        print(f"Gilstrap Documents Found: {results['gilstrap_documents_found']}")
        print(f"Patent Cases Found: {results['patent_cases_found']}")
        
        if results["gilstrap_documents_found"] > 0:
            print("\n🎉 SUCCESS: Agent can now retrieve Judge Gilstrap information!")
            print("   The enhanced Haystack ingestion has resolved the retrieval issues.")
        else:
            print("\n⚠️ ISSUE: No Gilstrap information found in search results.")
            print("   Further investigation may be needed.")
        
        print("=" * 80)

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test agent retrieval of Judge Gilstrap information')
    parser.add_argument('--haystack-url', default='http://localhost:8000', help='Haystack service URL')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    # Create tester
    tester = AgentRetrievalTester(args.haystack_url)
    
    # Run comprehensive test
    results = tester.run_comprehensive_test()
    
    # Print summary
    tester.print_summary(results)
    
    # Return appropriate exit code
    sys.exit(0 if results["overall_success"] and results["gilstrap_documents_found"] > 0 else 1)

if __name__ == "__main__":
    main()