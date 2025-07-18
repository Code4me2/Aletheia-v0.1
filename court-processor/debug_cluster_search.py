#!/usr/bin/env python3
"""
Debug script to investigate cluster search results

Analyzes why we're getting 20 clusters but no verified Gilstrap judges.
"""
import asyncio
import sys
import os
import json

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.services.courtlistener_service import CourtListenerService

async def debug_cluster_search():
    """Debug the cluster search to understand the results"""
    
    print("=== DEBUG: Cluster Search Analysis ===\n")
    
    cl_service = CourtListenerService()
    
    # Test connection
    if not await cl_service.test_connection():
        print("❌ API connection failed")
        return
    
    print("✅ API connected\n")
    
    # Fetch a sample cluster to understand structure
    print("🔍 Fetching sample clusters to analyze structure...")
    
    clusters = await cl_service.fetch_clusters_by_judge(
        judge_name="Gilstrap",
        court_id="txed",
        max_documents=3  # Just a few for analysis
    )
    
    print(f"📊 Found {len(clusters)} clusters\n")
    
    for i, cluster in enumerate(clusters):
        print(f"--- Cluster {i+1} ---")
        print(f"ID: {cluster.get('cluster_id')}")
        print(f"Case name: {cluster.get('case_name', 'None')}")
        print(f"Date filed: {cluster.get('date_filed', 'None')}")
        print(f"Court ID: {cluster.get('court_id', 'None')}")
        print(f"Judges field: '{cluster.get('judges', 'None')}'")
        print(f"Panel field: {cluster.get('panel', 'None')}")
        print(f"Non-participating judges: {cluster.get('non_participating_judges', 'None')}")
        
        # Check all fields that might contain judge info
        judge_related_fields = ['judges', 'panel', 'non_participating_judges', 'author_str']
        print("Judge-related fields:")
        for field in judge_related_fields:
            value = cluster.get(field)
            if value:
                print(f"  {field}: {value}")
        
        # Check if Gilstrap appears anywhere in the cluster data
        cluster_str = json.dumps(cluster, default=str).lower()
        if 'gilstrap' in cluster_str:
            print("🎯 'Gilstrap' found somewhere in cluster data!")
            # Find where
            for key, value in cluster.items():
                if isinstance(value, str) and 'gilstrap' in value.lower():
                    print(f"  Found in {key}: {value}")
        else:
            print("❌ 'Gilstrap' not found in cluster data")
        
        print()
    
    # Try a different search approach - without specific judge name
    print("🔍 Testing broad search in Eastern District of Texas...")
    
    broad_clusters = await cl_service.fetch_clusters_by_judge(
        judge_name="",  # Empty judge name
        court_id="txed",
        max_documents=5
    )
    
    print(f"📊 Broad search found {len(broad_clusters)} clusters")
    
    if broad_clusters:
        sample = broad_clusters[0]
        print(f"Sample case: {sample.get('case_name')}")
        print(f"Sample judges: '{sample.get('judges', 'None')}'")

if __name__ == "__main__":
    asyncio.run(debug_cluster_search())