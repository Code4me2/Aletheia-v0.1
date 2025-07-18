#!/usr/bin/env python3
"""
Test script with corrected CourtListener API syntax

Based on official API documentation, tests the correct way to find Judge Gilstrap's documents.
"""
import asyncio
import sys
import os
import json
import aiohttp
from typing import Dict, List, Any

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.config import get_settings

class CorrectedAPITester:
    """Test corrected API syntax for Judge Gilstrap search"""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.services.courtlistener_api_key
        self.base_url = "https://www.courtlistener.com/api/rest/v4"
        self.timeout = 30
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "User-Agent": "CourtListener API Corrected Test v1.0",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        
        return headers
    
    async def find_judge_gilstrap_in_people(self) -> List[Dict[str, Any]]:
        """Step 1: Find Judge Gilstrap using the /people/ endpoint"""
        print("🔍 Step 1: Finding Judge Gilstrap in /people/ endpoint...")
        
        search_terms = [
            {"name_last": "Gilstrap"},
            {"name_last": "Gilstrap", "name_first": "Rodney"}
        ]
        
        found_judges = []
        
        for params in search_terms:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/people/",
                        headers=self._get_headers(),
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            people = data.get('results', [])
                            
                            print(f"   Found {len(people)} people with params {params}")
                            
                            for person in people:
                                name_full = person.get('name_full', '')
                                if 'gilstrap' in name_full.lower():
                                    print(f"   ✅ Found: {name_full} (ID: {person.get('id')})")
                                    found_judges.append(person)
                                    
                                    # Show positions
                                    positions = person.get('positions', [])
                                    for pos in positions:
                                        if isinstance(pos, str):
                                            print(f"      Position URL: {pos}")
                                        else:
                                            print(f"      Position: {pos}")
                        else:
                            print(f"   ❌ HTTP {response.status}")
                            
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        return found_judges
    
    async def search_using_correct_search_api(self) -> List[Dict[str, Any]]:
        """Step 2: Use the /search/ endpoint with correct parameters"""
        print("\n🔍 Step 2: Using /search/ endpoint for Judge Gilstrap...")
        
        search_strategies = [
            {
                "name": "Opinion search for Gilstrap in Eastern District",
                "params": {
                    "q": "Gilstrap",
                    "type": "o",  # Case law opinions
                    "court": "txed"
                }
            },
            {
                "name": "RECAP docket search for Gilstrap",
                "params": {
                    "q": "Judge Gilstrap",
                    "type": "r",  # RECAP dockets
                    "court": "txed"
                }
            },
            {
                "name": "People search for Gilstrap",
                "params": {
                    "q": "Rodney Gilstrap",
                    "type": "p"  # People/Judges
                }
            }
        ]
        
        results = []
        
        for strategy in search_strategies:
            print(f"\n   Testing: {strategy['name']}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/search/",
                        headers=self._get_headers(),
                        params=strategy['params'],
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            count = data.get('count', 0)
                            items = data.get('results', [])
                            
                            print(f"      ✅ Found {count} total results, {len(items)} returned")
                            
                            if items:
                                sample = items[0]
                                print(f"      Sample result type: {type(sample)}")
                                if isinstance(sample, dict):
                                    print(f"      Sample fields: {list(sample.keys())[:5]}")
                                
                                results.extend(items)
                        else:
                            print(f"      ❌ HTTP {response.status}")
                            
            except Exception as e:
                print(f"      ❌ Error: {str(e)}")
        
        return results
    
    async def test_direct_docket_search(self) -> List[Dict[str, Any]]:
        """Step 3: Direct docket search in Eastern District of Texas"""
        print("\n🔍 Step 3: Direct docket search in Eastern District...")
        
        try:
            params = {
                "court": "txed",
                "page_size": 10,
                "ordering": "-date_filed"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/dockets/",
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        dockets = data.get('results', [])
                        
                        print(f"   Found {len(dockets)} recent dockets in Eastern District")
                        
                        # Check each docket for Gilstrap
                        gilstrap_dockets = []
                        for docket in dockets:
                            # Check assigned judge
                            assigned_to = docket.get('assigned_to_str', '')
                            if 'gilstrap' in assigned_to.lower():
                                print(f"   ✅ Found Gilstrap case: {docket.get('case_name')}")
                                print(f"      Assigned to: {assigned_to}")
                                print(f"      Date filed: {docket.get('date_filed')}")
                                gilstrap_dockets.append(docket)
                        
                        if not gilstrap_dockets:
                            print("   No Gilstrap cases found in recent dockets")
                        
                        return gilstrap_dockets
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        return []
                        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return []
    
    async def test_cluster_search_corrected(self) -> List[Dict[str, Any]]:
        """Step 4: Test cluster search with corrected syntax"""
        print("\n🔍 Step 4: Testing cluster search with corrected parameters...")
        
        # According to the API docs, clusters can be filtered by:
        # docket__court, date_filed__range
        
        try:
            params = {
                "docket__court": "txed",  # Correct nested parameter syntax
                "page_size": 20,
                "ordering": "-date_filed"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/clusters/",
                    headers=self._get_headers(),
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        clusters = data.get('results', [])
                        
                        print(f"   Found {len(clusters)} clusters in Eastern District")
                        
                        # Check for Gilstrap in judges field
                        gilstrap_clusters = []
                        for cluster in clusters:
                            judges = cluster.get('judges', '')
                            if 'gilstrap' in judges.lower():
                                print(f"   ✅ Found Gilstrap cluster: {cluster.get('case_name')}")
                                print(f"      Judges: {judges}")
                                gilstrap_clusters.append(cluster)
                        
                        if not gilstrap_clusters:
                            print("   No Gilstrap clusters found")
                            # Show sample of what we did find
                            if clusters:
                                sample = clusters[0]
                                print(f"   Sample cluster judges: '{sample.get('judges', 'None')}'")
                        
                        return gilstrap_clusters
                    else:
                        print(f"   ❌ HTTP {response.status}")
                        return []
                        
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            return []

async def test_corrected_api_syntax():
    """Run comprehensive test with corrected API syntax"""
    
    print("=== CORRECTED COURTLISTENER API SYNTAX TEST ===\n")
    print("🎯 Using official API documentation parameter syntax")
    
    tester = CorrectedAPITester()
    
    if not tester.api_key:
        print("❌ No API key configured")
        return False
    
    # Step 1: Find judge in people endpoint
    judges = await tester.find_judge_gilstrap_in_people()
    
    # Step 2: Use search endpoint
    search_results = await tester.search_using_correct_search_api()
    
    # Step 3: Direct docket search
    dockets = await tester.test_direct_docket_search()
    
    # Step 4: Corrected cluster search
    clusters = await tester.test_cluster_search_corrected()
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"✅ Found {len(judges)} judges in /people/ endpoint")
    print(f"✅ Found {len(search_results)} results in /search/ endpoint")
    print(f"✅ Found {len(dockets)} Gilstrap dockets")
    print(f"✅ Found {len(clusters)} Gilstrap clusters")
    
    success = len(judges) > 0 or len(dockets) > 0 or len(clusters) > 0
    
    if success:
        print("\n🎉 Successfully found Judge Gilstrap using corrected API syntax!")
    else:
        print("\n🔧 Still need to investigate alternative approaches")
    
    return success

if __name__ == "__main__":
    try:
        success = asyncio.run(test_corrected_api_syntax())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)