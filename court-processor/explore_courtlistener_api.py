#!/usr/bin/env python3
"""
CourtListener v4 API Exploration Tool

Comprehensive exploration of CourtListener v4 API capabilities to understand:
- All available fields and their meanings
- Search options and filtering capabilities  
- Judge identification methodologies
- Document coverage and metadata structure
"""
import asyncio
import sys
import os
import json
import aiohttp
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.config import get_settings

class CourtListenerAPIExplorer:
    """Comprehensive CourtListener API explorer"""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.services.courtlistener_api_key
        self.base_url = "https://www.courtlistener.com/api/rest/v4"
        self.timeout = 30
        
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        headers = {
            "User-Agent": "CourtListener API Explorer v1.0",
            "Accept": "application/json"
        }
        
        if self.api_key:
            headers["Authorization"] = f"Token {self.api_key}"
        
        return headers
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    def print_json(self, data: Any, max_depth: int = 3, current_depth: int = 0):
        """Pretty print JSON with depth limiting"""
        if current_depth >= max_depth and isinstance(data, (dict, list)):
            if isinstance(data, dict):
                print(f"{{...{len(data)} fields...}}")
            else:
                print(f"[...{len(data)} items...]")
            return
            
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)) and current_depth < max_depth - 1:
                    print(f"{'  ' * current_depth}{key}:")
                    self.print_json(value, max_depth, current_depth + 1)
                else:
                    if isinstance(value, str) and len(value) > 100:
                        print(f"{'  ' * current_depth}{key}: '{value[:100]}...'")
                    else:
                        print(f"{'  ' * current_depth}{key}: {repr(value)}")
        elif isinstance(data, list) and data:
            print(f"{'  ' * current_depth}[{len(data)} items]")
            if current_depth < max_depth - 1:
                self.print_json(data[0], max_depth, current_depth + 1)
    
    async def explore_api_endpoints(self) -> Dict[str, Any]:
        """Explore available API endpoints"""
        self.print_header("API ENDPOINTS EXPLORATION")
        
        endpoints = {
            "opinions": "/opinions/",
            "clusters": "/clusters/", 
            "dockets": "/dockets/",
            "courts": "/courts/",
            "people": "/people/",
            "positions": "/positions/",
            "opinions-cited": "/opinions-cited/",
            "search": "/search/"
        }
        
        endpoint_info = {}
        
        for name, endpoint in endpoints.items():
            print(f"\n🔍 Exploring {name} endpoint...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}{endpoint}",
                        headers=self._get_headers(),
                        params={"page_size": 1},
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            print(f"   ✅ Available - {data.get('count', 'unknown')} total items")
                            
                            # Show structure
                            if 'results' in data and data['results']:
                                sample = data['results'][0]
                                print(f"   📊 Sample structure:")
                                self.print_json(sample, max_depth=2)
                                
                                endpoint_info[name] = {
                                    'url': endpoint,
                                    'total_count': data.get('count'),
                                    'sample_fields': list(sample.keys()) if isinstance(sample, dict) else None,
                                    'status': 'available'
                                }
                            else:
                                endpoint_info[name] = {
                                    'url': endpoint,
                                    'total_count': data.get('count'),
                                    'status': 'available_no_sample'
                                }
                        else:
                            print(f"   ❌ HTTP {response.status}")
                            endpoint_info[name] = {'status': f'error_{response.status}'}
                            
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                endpoint_info[name] = {'status': f'error_{str(e)}'}
        
        return endpoint_info
    
    async def analyze_opinion_fields(self) -> Dict[str, Any]:
        """Deep analysis of opinion document fields"""
        self.print_header("OPINION FIELDS DEEP ANALYSIS")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get multiple samples for field analysis
                async with session.get(
                    f"{self.base_url}/opinions/",
                    headers=self._get_headers(),
                    params={"page_size": 10, "ordering": "-date_created"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ Failed to fetch opinions: HTTP {response.status}")
                        return {}
                    
                    data = await response.json()
                    opinions = data.get('results', [])
                    
                    if not opinions:
                        print("❌ No opinions returned")
                        return {}
                    
                    print(f"📊 Analyzing {len(opinions)} opinion samples...")
                    
                    # Analyze field presence and types
                    field_analysis = {}
                    
                    for opinion in opinions:
                        for field, value in opinion.items():
                            if field not in field_analysis:
                                field_analysis[field] = {
                                    'type': type(value).__name__,
                                    'present_count': 0,
                                    'null_count': 0,
                                    'empty_count': 0,
                                    'sample_values': set(),
                                    'max_length': 0
                                }
                            
                            analysis = field_analysis[field]
                            
                            if value is None:
                                analysis['null_count'] += 1
                            elif value == '':
                                analysis['empty_count'] += 1
                            else:
                                analysis['present_count'] += 1
                                
                                if isinstance(value, str):
                                    analysis['max_length'] = max(analysis['max_length'], len(value))
                                    if len(analysis['sample_values']) < 3:
                                        analysis['sample_values'].add(value[:50] if len(value) > 50 else value)
                                elif not isinstance(value, (dict, list)):
                                    if len(analysis['sample_values']) < 3:
                                        analysis['sample_values'].add(str(value))
                    
                    # Print field analysis
                    print(f"\n📋 Field Analysis (from {len(opinions)} samples):")
                    for field, analysis in sorted(field_analysis.items()):
                        presence_rate = (analysis['present_count'] / len(opinions)) * 100
                        print(f"\n   🔹 {field}:")
                        print(f"      Type: {analysis['type']}")
                        print(f"      Present: {analysis['present_count']}/{len(opinions)} ({presence_rate:.1f}%)")
                        print(f"      Null: {analysis['null_count']}, Empty: {analysis['empty_count']}")
                        
                        if analysis['max_length'] > 0:
                            print(f"      Max length: {analysis['max_length']}")
                        
                        if analysis['sample_values']:
                            samples = list(analysis['sample_values'])[:3]
                            print(f"      Samples: {samples}")
                    
                    return field_analysis
                    
        except Exception as e:
            print(f"❌ Error analyzing opinion fields: {str(e)}")
            return {}
    
    async def explore_cluster_data(self) -> Dict[str, Any]:
        """Explore cluster data structure for judge information"""
        self.print_header("CLUSTER DATA EXPLORATION")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get cluster samples
                async with session.get(
                    f"{self.base_url}/clusters/",
                    headers=self._get_headers(),
                    params={"page_size": 5, "ordering": "-date_filed"},
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ Failed to fetch clusters: HTTP {response.status}")
                        return {}
                    
                    data = await response.json()
                    clusters = data.get('results', [])
                    
                    print(f"📊 Analyzing {len(clusters)} cluster samples...")
                    
                    for i, cluster in enumerate(clusters):
                        print(f"\n📄 Cluster {i+1}:")
                        self.print_json(cluster, max_depth=2)
                        
                        # Check for judge-related fields
                        judge_fields = ['judges', 'panel', 'author', 'judge']
                        found_judge_fields = {}
                        for field in judge_fields:
                            if field in cluster:
                                found_judge_fields[field] = cluster[field]
                        
                        if found_judge_fields:
                            print(f"   🏛️ Judge-related fields found:")
                            for field, value in found_judge_fields.items():
                                print(f"      {field}: {value}")
                    
                    return {"clusters_analyzed": len(clusters), "sample_data": clusters}
                    
        except Exception as e:
            print(f"❌ Error exploring clusters: {str(e)}")
            return {}
    
    async def explore_people_endpoint(self) -> Dict[str, Any]:
        """Explore people endpoint for judge information"""
        self.print_header("PEOPLE ENDPOINT EXPLORATION")
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search for Gilstrap specifically
                search_params = [
                    {"q": "Gilstrap"},
                    {"name": "Gilstrap"},
                    {"name_last": "Gilstrap"}
                ]
                
                results = {}
                
                for params in search_params:
                    param_str = "&".join([f"{k}={v}" for k, v in params.items()])
                    print(f"\n🔍 Searching people with: {param_str}")
                    
                    async with session.get(
                        f"{self.base_url}/people/",
                        headers=self._get_headers(),
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            people = data.get('results', [])
                            print(f"   ✅ Found {len(people)} people")
                            
                            for person in people:
                                print(f"   👤 {person.get('name_full', 'Unknown')}")
                                print(f"      ID: {person.get('id')}")
                                print(f"      Name last: {person.get('name_last')}")
                                print(f"      Positions: {len(person.get('positions', []))}")
                                
                                # Show positions if available
                                if person.get('positions'):
                                    for pos in person.get('positions', [])[:2]:
                                        print(f"         Position: {pos}")
                            
                            results[param_str] = people
                        else:
                            print(f"   ❌ HTTP {response.status}")
                
                return results
                
        except Exception as e:
            print(f"❌ Error exploring people: {str(e)}")
            return {}
    
    async def test_advanced_search_options(self) -> Dict[str, Any]:
        """Test advanced search options and filters"""
        self.print_header("ADVANCED SEARCH OPTIONS TESTING")
        
        search_strategies = [
            # Opinion-level searches
            {
                "endpoint": "/opinions/",
                "name": "Eastern District of Texas Recent",
                "params": {"court": "txed", "ordering": "-date_filed", "page_size": 5}
            },
            {
                "endpoint": "/opinions/",
                "name": "Text search for Gilstrap",
                "params": {"q": "Gilstrap", "court": "txed", "page_size": 5}
            },
            {
                "endpoint": "/opinions/",
                "name": "Author search",
                "params": {"author": "Gilstrap", "page_size": 5}
            },
            
            # Cluster-level searches
            {
                "endpoint": "/clusters/",
                "name": "Cluster text search",
                "params": {"q": "Gilstrap", "court": "txed", "page_size": 5}
            },
            {
                "endpoint": "/clusters/",
                "name": "Cluster by judge",
                "params": {"judge": "Gilstrap", "page_size": 5}
            },
            
            # Docket-level searches
            {
                "endpoint": "/dockets/",
                "name": "Docket search",
                "params": {"q": "Gilstrap", "court": "txed", "page_size": 5}
            },
            {
                "endpoint": "/dockets/",
                "name": "Docket by judge",
                "params": {"assigned_to": "Gilstrap", "page_size": 5}
            }
        ]
        
        results = {}
        
        for strategy in search_strategies:
            print(f"\n🧪 Testing: {strategy['name']}")
            print(f"   Endpoint: {strategy['endpoint']}")
            print(f"   Params: {strategy['params']}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}{strategy['endpoint']}",
                        headers=self._get_headers(),
                        params=strategy['params'],
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            count = data.get('count', 0)
                            items = data.get('results', [])
                            
                            print(f"   ✅ Success: {count} total items, {len(items)} returned")
                            
                            # Show relevant fields from first result
                            if items:
                                item = items[0]
                                relevant_fields = ['id', 'case_name', 'court_id', 'date_filed', 
                                                 'author_str', 'assigned_to', 'judge', 'judges']
                                
                                found_fields = {}
                                for field in relevant_fields:
                                    if field in item:
                                        found_fields[field] = item[field]
                                
                                if found_fields:
                                    print(f"   📊 Sample relevant fields:")
                                    for field, value in found_fields.items():
                                        if isinstance(value, str) and len(value) > 50:
                                            print(f"      {field}: {value[:50]}...")
                                        else:
                                            print(f"      {field}: {value}")
                            
                            results[strategy['name']] = {
                                'status': 'success',
                                'count': count,
                                'sample_data': items[0] if items else None
                            }
                        else:
                            error_text = await response.text()
                            print(f"   ❌ HTTP {response.status}: {error_text[:100]}")
                            results[strategy['name']] = {
                                'status': f'error_{response.status}',
                                'error': error_text[:100]
                            }
                            
            except Exception as e:
                print(f"   ❌ Exception: {str(e)}")
                results[strategy['name']] = {
                    'status': 'exception',
                    'error': str(e)
                }
        
        return results
    
    async def analyze_judge_identification_methods(self) -> Dict[str, Any]:
        """Analyze different methods for identifying judges in documents"""
        self.print_header("JUDGE IDENTIFICATION METHODS ANALYSIS")
        
        print("🎯 Testing different approaches to identify Judge Gilstrap...")
        
        methods = []
        
        # Method 1: Search people endpoint first
        print("\n📋 Method 1: People Endpoint Lookup")
        people_results = await self.explore_people_endpoint()
        
        gilstrap_person_ids = []
        for search_key, people in people_results.items():
            for person in people:
                if 'gilstrap' in person.get('name_full', '').lower():
                    gilstrap_person_ids.append(person.get('id'))
                    print(f"   Found Judge Gilstrap ID: {person.get('id')} - {person.get('name_full')}")
        
        methods.append({
            'name': 'People Endpoint Lookup',
            'judge_ids_found': gilstrap_person_ids,
            'success': len(gilstrap_person_ids) > 0
        })
        
        # Method 2: Use judge IDs to find documents
        if gilstrap_person_ids:
            print(f"\n📋 Method 2: Documents by Judge ID")
            for judge_id in gilstrap_person_ids[:1]:  # Test first ID
                try:
                    async with aiohttp.ClientSession() as session:
                        # Try different endpoints with judge ID
                        endpoints_to_test = [
                            ("/opinions/", {"author": judge_id}),
                            ("/clusters/", {"judges": judge_id}),
                            ("/dockets/", {"assigned_to": judge_id})
                        ]
                        
                        for endpoint, params in endpoints_to_test:
                            print(f"   🔍 Testing {endpoint} with judge ID {judge_id}")
                            
                            async with session.get(
                                f"{self.base_url}{endpoint}",
                                headers=self._get_headers(),
                                params=params,
                                timeout=aiohttp.ClientTimeout(total=self.timeout)
                            ) as response:
                                
                                if response.status == 200:
                                    data = await response.json()
                                    count = data.get('count', 0)
                                    print(f"      ✅ Found {count} documents")
                                    
                                    if count > 0:
                                        methods.append({
                                            'name': f'Judge ID Search - {endpoint}',
                                            'judge_id': judge_id,
                                            'document_count': count,
                                            'success': True
                                        })
                                else:
                                    print(f"      ❌ HTTP {response.status}")
                                    
                except Exception as e:
                    print(f"   ❌ Error: {str(e)}")
        
        # Method 3: Text-based search in different fields
        print(f"\n📋 Method 3: Advanced Text Search")
        text_searches = [
            ("Full text search", {"q": '"Judge Gilstrap" OR "Rodney Gilstrap"'}),
            ("Case name search", {"case_name": "Gilstrap"}),
            ("Court + text", {"court": "txed", "q": "Gilstrap"})
        ]
        
        for search_name, params in text_searches:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.base_url}/opinions/",
                        headers=self._get_headers(),
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            count = data.get('count', 0)
                            print(f"   {search_name}: {count} documents")
                            
                            methods.append({
                                'name': search_name,
                                'params': params,
                                'document_count': count,
                                'success': count > 0
                            })
                        else:
                            print(f"   {search_name}: HTTP {response.status}")
                            
            except Exception as e:
                print(f"   {search_name}: Error - {str(e)}")
        
        return methods

async def run_comprehensive_exploration():
    """Run comprehensive CourtListener API exploration"""
    
    explorer = CourtListenerAPIExplorer()
    
    if not explorer.api_key:
        print("❌ No API key configured. Set COURTLISTENER_API_TOKEN environment variable.")
        return False
    
    explorer.print_header("COURTLISTENER v4 API COMPREHENSIVE EXPLORATION")
    print("🎯 Objective: Understand full API capabilities for judge-specific document retrieval")
    
    # Step 1: Explore available endpoints
    endpoint_info = await explorer.explore_api_endpoints()
    
    # Step 2: Deep dive into opinion fields
    opinion_fields = await explorer.analyze_opinion_fields()
    
    # Step 3: Explore cluster data
    cluster_info = await explorer.explore_cluster_data()
    
    # Step 4: Test advanced search options
    search_results = await explorer.test_advanced_search_options()
    
    # Step 5: Analyze judge identification methods
    judge_methods = await explorer.analyze_judge_identification_methods()
    
    # Step 6: Compile recommendations
    explorer.print_header("RECOMMENDATIONS FOR JUDGE GILSTRAP RETRIEVAL")
    
    successful_methods = [m for m in judge_methods if m.get('success')]
    
    if successful_methods:
        print("✅ Successful identification methods found:")
        for method in successful_methods:
            print(f"   🔹 {method['name']}: {method.get('document_count', 'N/A')} documents")
            if 'params' in method:
                print(f"      Parameters: {method['params']}")
    else:
        print("❌ No successful judge identification methods found")
        print("🔧 Recommendations:")
        print("   1. Verify Judge Gilstrap is in the CourtListener database")
        print("   2. Try alternative name variations")
        print("   3. Search by specific court and date ranges")
        print("   4. Use docket-level searches instead of opinion-level")
    
    # Field analysis summary
    if opinion_fields:
        print(f"\n📊 Key fields for judge identification:")
        judge_related_fields = ['author', 'author_str', 'judges', 'panel', 'assigned_to']
        for field in judge_related_fields:
            if field in opinion_fields:
                analysis = opinion_fields[field]
                presence_rate = (analysis['present_count'] / 10) * 100  # Based on 10 samples
                print(f"   🔹 {field}: {presence_rate:.0f}% populated")
    
    return True

if __name__ == "__main__":
    try:
        print("🚀 Starting comprehensive CourtListener API exploration...")
        success = asyncio.run(run_comprehensive_exploration())
        
        if success:
            print("\n✅ API exploration completed successfully!")
        else:
            print("\n❌ API exploration failed")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Exploration interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)