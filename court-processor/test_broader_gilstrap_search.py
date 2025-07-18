#!/usr/bin/env python3
"""
Test Broader Judge Gilstrap Search

Searches for older Gilstrap cases that might have opinions and text content.
"""
import asyncio
import sys
import os
import aiohttp
from datetime import datetime, timedelta

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

async def test_broader_gilstrap_search():
    """Test broader search for Gilstrap cases with opinions"""
    
    print("=== BROADER JUDGE GILSTRAP SEARCH ===\n")
    print("🎯 Searching for older cases with opinion content")
    
    cl_service = CourtListenerService()
    
    if not await cl_service.test_connection():
        print("❌ API connection failed")
        return False
    
    print("✅ API connected\n")
    
    # Strategy 1: Use search API to find Gilstrap opinions directly
    print("🔍 Strategy 1: Search API for Gilstrap opinions...")
    
    try:
        async with aiohttp.ClientSession() as session:
            # Search for opinions mentioning Gilstrap in Eastern District
            async with session.get(
                f"{cl_service.base_url}/search/",
                headers=cl_service._get_headers(),
                params={
                    "q": "Gilstrap",
                    "type": "o",  # Opinions
                    "court": "txed",
                    "page_size": 10
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    opinions = data.get('results', [])
                    
                    print(f"   ✅ Found {len(opinions)} opinion search results")
                    
                    for i, opinion in enumerate(opinions[:3]):
                        print(f"\n   📄 Opinion {i+1}:")
                        print(f"      Case: {opinion.get('caseName', 'Unknown')}")
                        print(f"      Court: {opinion.get('court', 'Unknown')}")
                        print(f"      Date: {opinion.get('dateFiled', 'Unknown')}")
                        print(f"      URL: {opinion.get('absolute_url', 'None')}")
                        
                        # Try to get full opinion text
                        if 'id' in opinion:
                            opinion_id = opinion['id']
                            print(f"      🔍 Fetching full text for opinion {opinion_id}...")
                            
                            async with session.get(
                                f"{cl_service.base_url}/opinions/{opinion_id}/",
                                headers=cl_service._get_headers(),
                                timeout=aiohttp.ClientTimeout(total=30)
                            ) as opinion_response:
                                
                                if opinion_response.status == 200:
                                    opinion_data = await opinion_response.json()
                                    plain_text = opinion_data.get('plain_text', '')
                                    
                                    if plain_text and plain_text.strip():
                                        print(f"         ✅ Found text: {len(plain_text):,} characters")
                                        print(f"         📝 Preview: {plain_text[:200]}...")
                                    else:
                                        print(f"         ❌ No text content")
                                else:
                                    print(f"         ❌ Failed to fetch: HTTP {opinion_response.status}")
                else:
                    print(f"   ❌ Search failed: HTTP {response.status}")
                    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Strategy 2: Look for broader date range in dockets
    print(f"\n🔍 Strategy 2: Broader date range for dockets...")
    
    try:
        # Search for last 5 years to find older cases
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1825)  # 5 years
        
        print(f"   📅 Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        broader_dockets = await cl_service.fetch_dockets_by_judge(
            judge_name="Gilstrap",
            court_id="txed",
            max_documents=50,  # More dockets
            date_filed_after=start_date.strftime('%Y-%m-%d'),
            date_filed_before=end_date.strftime('%Y-%m-%d')
        )
        
        print(f"   ✅ Found {len(broader_dockets)} dockets in 5-year range")
        
        if broader_dockets:
            # Analyze date distribution
            date_dist = {}
            for docket in broader_dockets:
                date_filed = docket.get('date_filed', '')
                if date_filed:
                    year = date_filed[:4]
                    date_dist[year] = date_dist.get(year, 0) + 1
            
            print(f"   📊 Year distribution:")
            for year, count in sorted(date_dist.items()):
                print(f"      {year}: {count} cases")
            
            # Test a few older dockets for clusters/opinions
            print(f"\n   🔍 Testing older dockets for clusters...")
            
            for i, docket in enumerate(broader_dockets[:5]):
                docket_id = docket.get('docket_id')
                case_name = docket.get('case_name', 'Unknown')[:50]
                date_filed = docket.get('date_filed', 'Unknown')
                
                print(f"      Docket {i+1}: {case_name} ({date_filed})")
                
                # Check for clusters
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{cl_service.base_url}/clusters/",
                        headers=cl_service._get_headers(),
                        params={"docket": docket_id, "page_size": 5},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        
                        if response.status == 200:
                            data = await response.json()
                            clusters = data.get('results', [])
                            
                            if clusters:
                                print(f"         ✅ Found {len(clusters)} clusters")
                                
                                # Check first cluster for opinions
                                cluster_id = clusters[0].get('id')
                                async with session.get(
                                    f"{cl_service.base_url}/opinions/",
                                    headers=cl_service._get_headers(),
                                    params={"cluster": cluster_id, "page_size": 3},
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as opinion_response:
                                    
                                    if opinion_response.status == 200:
                                        opinion_data = await opinion_response.json()
                                        opinions = opinion_data.get('results', [])
                                        
                                        print(f"         📄 Found {len(opinions)} opinions")
                                        
                                        for opinion in opinions:
                                            text = opinion.get('plain_text', '')
                                            if text and text.strip():
                                                print(f"            ✅ Opinion {opinion.get('id')}: {len(text):,} chars")
                                                return True  # Found text content!
                                            else:
                                                print(f"            ❌ Opinion {opinion.get('id')}: No text")
                            else:
                                print(f"         ❌ No clusters found")
                        else:
                            print(f"         ❌ Cluster search failed: HTTP {response.status}")
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    # Strategy 3: Direct opinion search by court
    print(f"\n🔍 Strategy 3: Direct opinion search in Eastern District...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{cl_service.base_url}/opinions/",
                headers=cl_service._get_headers(),
                params={
                    "cluster__docket__court": "txed",
                    "page_size": 10,
                    "ordering": "-date_created"
                },
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    opinions = data.get('results', [])
                    
                    print(f"   ✅ Found {len(opinions)} recent opinions in txed")
                    
                    # Check which have text content
                    text_count = 0
                    for opinion in opinions:
                        text = opinion.get('plain_text', '')
                        if text and text.strip():
                            text_count += 1
                    
                    print(f"   📄 {text_count}/{len(opinions)} opinions have text content")
                    
                    if text_count > 0:
                        print(f"   ✅ Text content is available in Eastern District opinions")
                        return True
                else:
                    print(f"   ❌ Failed: HTTP {response.status}")
                    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
    
    print(f"\n=== SUMMARY ===")
    print(f"🔍 Searched multiple strategies for Gilstrap opinion text")
    print(f"📊 Results suggest recent cases may not have opinions filed yet")
    print(f"💡 Recommendation: Focus on docket metadata or wait for opinions to be filed")
    
    return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_broader_gilstrap_search())
        
        if success:
            print(f"\n🎉 Found Gilstrap opinion text content!")
        else:
            print(f"\n🔧 No opinion text found - cases may be too recent")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)