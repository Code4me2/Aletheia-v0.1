#!/usr/bin/env python3
"""
Get the exact count of Judge Gilstrap dockets in CourtListener
"""

import requests
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("count_gilstrap_dockets")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def get_exact_docket_count():
    """Get exact count of Judge Gilstrap dockets"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Gilstrap Docket Count'
    }
    
    logger.info("Getting exact count of Judge Gilstrap dockets...")
    
    # Use the count API endpoint
    search_methods = [
        {
            'name': 'Assigned To String (Most Reliable)',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to_str__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 1  # We only want the count
            }
        },
        {
            'name': 'Judge Last Name',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to__name_last__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 1
            }
        },
        {
            'name': 'Judge Full Name',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to__name_first__icontains': 'rodney',
                'assigned_to__name_last__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 1
            }
        }
    ]
    
    results = {}
    
    for method in search_methods:
        logger.info(f"\nTesting: {method['name']}")
        
        try:
            response = requests.get(
                method['url'],
                params=method['params'],
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                count = data.get('count', 0)
                
                logger.info(f"✅ Total dockets: {count}")
                
                # Get sample of results to verify
                sample_results = data.get('results', [])
                if sample_results:
                    sample = sample_results[0]
                    logger.info(f"   Sample case: {sample.get('case_name', 'Unknown')}")
                    logger.info(f"   Date filed: {sample.get('date_filed', 'Unknown')}")
                    logger.info(f"   Assigned to: {sample.get('assigned_to_str', 'Unknown')}")
                
                results[method['name']] = {
                    'count': count,
                    'success': True,
                    'sample': sample_results[0] if sample_results else None
                }
                
            else:
                logger.error(f"❌ Error {response.status_code}: {response.text}")
                results[method['name']] = {
                    'error': f"HTTP {response.status_code}",
                    'success': False
                }
        
        except Exception as e:
            logger.error(f"❌ Exception: {e}")
            results[method['name']] = {
                'error': str(e),
                'success': False
            }
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("JUDGE GILSTRAP DOCKETS COUNT SUMMARY")
    logger.info("="*60)
    
    for method_name, result in results.items():
        if result.get('success'):
            logger.info(f"{method_name}: {result['count']} dockets")
        else:
            logger.info(f"{method_name}: FAILED - {result.get('error', 'Unknown')}")
    
    # Get the most reliable count
    most_reliable = results.get('Assigned To String (Most Reliable)', {})
    if most_reliable.get('success'):
        final_count = most_reliable['count']
        logger.info(f"\n🎯 FINAL ANSWER: {final_count} Judge Gilstrap dockets")
    else:
        # Try other methods
        for method_name, result in results.items():
            if result.get('success'):
                final_count = result['count']
                logger.info(f"\n🎯 FINAL ANSWER: {final_count} Judge Gilstrap dockets (via {method_name})")
                break
        else:
            logger.info("\n❌ Could not determine docket count")
            final_count = 0
    
    logger.info("="*60)
    
    return {
        'final_count': final_count,
        'method_results': results
    }

if __name__ == "__main__":
    results = get_exact_docket_count()
    
    # Save results to file
    with open('gilstrap_docket_count.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Count complete. Results saved to gilstrap_docket_count.json")