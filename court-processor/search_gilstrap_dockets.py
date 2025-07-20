#!/usr/bin/env python3
"""
Search for Judge Gilstrap dockets in CourtListener
Dockets contain case procedural information, different from opinions
"""

import requests
import json
import os
from datetime import datetime, timedelta
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gilstrap_dockets")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def search_gilstrap_dockets():
    """Search for Judge Gilstrap dockets in CourtListener"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Gilstrap Docket Search'
    }
    
    logger.info("Searching for Judge Gilstrap dockets in CourtListener")
    
    # Different search approaches for dockets
    search_methods = [
        {
            'name': 'Docket Search by Judge Name',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to__name_last__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Docket Search by Judge First+Last',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to__name_first__icontains': 'rodney',
                'assigned_to__name_last__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Docket Search by Assigned To String',
            'url': f'{BASE_URL}/dockets/',
            'params': {
                'assigned_to_str__icontains': 'gilstrap',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Docket Search Text Query',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'judge:gilstrap',
                'type': 'r',  # RECAP (docket entries)
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Docket Search All Types',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'gilstrap',
                'type': 'r',  # RECAP (docket entries)
                'court': 'txed',
                'page_size': 100
            }
        }
    ]
    
    results = {}
    total_unique_dockets = set()
    
    for method in search_methods:
        logger.info(f"\n=== {method['name']} ===")
        
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
                results_list = data.get('results', [])
                
                logger.info(f"✅ Found {count} total results")
                logger.info(f"✅ Returned {len(results_list)} results in this page")
                
                # Extract unique docket IDs
                docket_ids = set()
                dates = []
                case_names = []
                
                for result in results_list:
                    # Handle different response formats
                    if 'docket_id' in result:
                        docket_ids.add(result['docket_id'])
                    elif 'id' in result:
                        docket_ids.add(result['id'])
                    
                    # Extract case info
                    case_name = result.get('case_name', result.get('caseName', 'Unknown'))
                    date_filed = result.get('date_filed', result.get('dateFiled', ''))
                    
                    if case_name != 'Unknown':
                        case_names.append(case_name)
                    if date_filed:
                        dates.append(date_filed)
                
                total_unique_dockets.update(docket_ids)
                
                # Date analysis
                if dates:
                    dates.sort()
                    logger.info(f"📅 Date range: {dates[0]} to {dates[-1]}")
                    
                    # Year breakdown
                    years = {}
                    for date in dates:
                        year = date[:4]
                        years[year] = years.get(year, 0) + 1
                    
                    logger.info("📊 Year breakdown:")
                    for year, count in sorted(years.items()):
                        logger.info(f"   {year}: {count} dockets")
                
                # Sample cases
                if case_names:
                    logger.info("📄 Sample cases:")
                    for i, case in enumerate(case_names[:5]):
                        logger.info(f"   {i+1}. {case}")
                
                results[method['name']] = {
                    'total_count': count,
                    'results_returned': len(results_list),
                    'unique_dockets': len(docket_ids),
                    'dates': dates,
                    'case_names': case_names[:10],  # Store first 10
                    'success': True
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
    logger.info("JUDGE GILSTRAP DOCKETS SEARCH SUMMARY")
    logger.info("="*60)
    
    logger.info(f"🎯 TOTAL UNIQUE DOCKETS FOUND: {len(total_unique_dockets)}")
    logger.info("")
    
    for method_name, result in results.items():
        if result.get('success'):
            logger.info(f"{method_name}:")
            logger.info(f"  Total count: {result['total_count']}")
            logger.info(f"  Results returned: {result['results_returned']}")
            logger.info(f"  Unique dockets: {result['unique_dockets']}")
        else:
            logger.info(f"{method_name}: FAILED - {result.get('error', 'Unknown')}")
    
    logger.info("="*60)
    
    # Additional targeted searches for more comprehensive results
    logger.info("\n=== ADDITIONAL COMPREHENSIVE SEARCHES ===")
    
    # Search with pagination to get more results
    comprehensive_search_params = {
        'assigned_to_str__icontains': 'gilstrap',
        'court': 'txed',
        'page_size': 100
    }
    
    all_dockets = set()
    page = 1
    
    while page <= 10:  # Limit to 10 pages to avoid infinite loops
        logger.info(f"Searching page {page} of comprehensive docket search...")
        
        params = comprehensive_search_params.copy()
        params['page'] = page
        
        try:
            response = requests.get(
                f'{BASE_URL}/dockets/',
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results_list = data.get('results', [])
                
                if not results_list:
                    logger.info(f"No more results on page {page}")
                    break
                
                page_dockets = set()
                for result in results_list:
                    if 'id' in result:
                        page_dockets.add(result['id'])
                        all_dockets.add(result['id'])
                
                logger.info(f"Page {page}: {len(page_dockets)} dockets")
                
                # Check if there are more pages
                if not data.get('next'):
                    logger.info("Reached last page")
                    break
                
                page += 1
            else:
                logger.error(f"Page {page} failed: {response.status_code}")
                break
                
        except Exception as e:
            logger.error(f"Page {page} error: {e}")
            break
    
    logger.info(f"\n🎯 COMPREHENSIVE SEARCH TOTAL: {len(all_dockets)} unique dockets")
    logger.info("="*60)
    
    return {
        'search_results': results,
        'total_unique_dockets': len(total_unique_dockets),
        'comprehensive_dockets': len(all_dockets),
        'unique_docket_ids': list(all_dockets)
    }

if __name__ == "__main__":
    results = search_gilstrap_dockets()
    
    # Save results to file
    with open('gilstrap_dockets_search.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Search complete. Results saved to gilstrap_dockets_search.json")
    logger.info(f"\nFINAL ANSWER: {results['comprehensive_dockets']} Judge Gilstrap dockets found")