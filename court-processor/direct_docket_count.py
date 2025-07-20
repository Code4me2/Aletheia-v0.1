#!/usr/bin/env python3
"""
Direct approach to count Judge Gilstrap dockets
"""

import requests
import json
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("direct_docket_count")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def count_dockets_direct():
    """Direct count of dockets by paginating through all results"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Direct Docket Counter'
    }
    
    logger.info("Counting Judge Gilstrap dockets by direct pagination...")
    
    # Search parameters
    params = {
        'assigned_to_str__icontains': 'gilstrap',
        'court': 'txed',
        'page_size': 100
    }
    
    total_dockets = 0
    unique_dockets = set()
    page = 1
    
    while True:
        logger.info(f"Fetching page {page}...")
        
        current_params = params.copy()
        current_params['page'] = page
        
        try:
            response = requests.get(
                f'{BASE_URL}/dockets/',
                params=current_params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                if not results:
                    logger.info(f"No results on page {page}. Stopping.")
                    break
                
                page_count = 0
                for result in results:
                    docket_id = result.get('id')
                    if docket_id:
                        unique_dockets.add(docket_id)
                        page_count += 1
                
                total_dockets += page_count
                logger.info(f"Page {page}: {page_count} dockets (Total: {total_dockets})")
                
                # Sample case info from first page
                if page == 1 and results:
                    sample = results[0]
                    logger.info(f"Sample case: {sample.get('case_name', 'Unknown')}")
                    logger.info(f"Date filed: {sample.get('date_filed', 'Unknown')}")
                    logger.info(f"Assigned to: {sample.get('assigned_to_str', 'Unknown')}")
                    
                    # Check if this is actually a Gilstrap case
                    assigned_to = sample.get('assigned_to_str', '').lower()
                    if 'gilstrap' in assigned_to:
                        logger.info("✅ Confirmed: This is a Gilstrap case")
                    else:
                        logger.info("⚠️  Warning: This may not be a Gilstrap case")
                
                # Check if there are more pages
                if not data.get('next'):
                    logger.info("Reached last page")
                    break
                
                page += 1
                
                # Safety limit to prevent infinite loops
                if page > 50:
                    logger.info("Reached safety limit of 50 pages")
                    break
                
            else:
                logger.error(f"Error on page {page}: {response.status_code}")
                break
                
        except Exception as e:
            logger.error(f"Exception on page {page}: {e}")
            break
    
    logger.info(f"\n🎯 FINAL COUNT: {len(unique_dockets)} unique Judge Gilstrap dockets")
    logger.info(f"📊 Total entries processed: {total_dockets}")
    logger.info(f"🔍 Pages searched: {page - 1}")
    
    return {
        'unique_dockets': len(unique_dockets),
        'total_entries': total_dockets,
        'pages_searched': page - 1,
        'docket_ids': list(unique_dockets)
    }

def get_sample_docket_details():
    """Get details of a few sample dockets for verification"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Sample Docket Details'
    }
    
    logger.info("\nGetting sample docket details for verification...")
    
    params = {
        'assigned_to_str__icontains': 'gilstrap',
        'court': 'txed',
        'page_size': 5
    }
    
    try:
        response = requests.get(
            f'{BASE_URL}/dockets/',
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            
            logger.info(f"Sample dockets (first 5):")
            for i, result in enumerate(results, 1):
                case_name = result.get('case_name', 'Unknown')
                date_filed = result.get('date_filed', 'Unknown')
                assigned_to = result.get('assigned_to_str', 'Unknown')
                docket_number = result.get('docket_number', 'Unknown')
                
                logger.info(f"{i}. {case_name}")
                logger.info(f"   Docket: {docket_number}")
                logger.info(f"   Filed: {date_filed}")
                logger.info(f"   Assigned to: {assigned_to}")
                logger.info("")
    
    except Exception as e:
        logger.error(f"Error getting sample details: {e}")

if __name__ == "__main__":
    # Count dockets
    count_result = count_dockets_direct()
    
    # Get sample details
    get_sample_docket_details()
    
    # Save results
    with open('direct_docket_count.json', 'w') as f:
        json.dump(count_result, f, indent=2)
    
    logger.info("Analysis complete. Results saved to direct_docket_count.json")
    print(f"\n🎯 ANSWER: {count_result['unique_dockets']} Judge Gilstrap dockets")