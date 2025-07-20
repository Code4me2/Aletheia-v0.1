#!/usr/bin/env python3
"""
Precise count of dockets actually assigned to Judge Rodney Gilstrap
"""

import requests
import json
import os
import logging
from collections import defaultdict

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("precise_gilstrap_count")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def count_actual_gilstrap_dockets():
    """Count dockets actually assigned to Judge Rodney Gilstrap"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Precise Gilstrap Counter'
    }
    
    logger.info("Counting dockets actually assigned to Judge Rodney Gilstrap...")
    
    # Use a more specific search
    params = {
        'assigned_to_str__icontains': 'rodney gilstrap',
        'court': 'txed',
        'page_size': 100
    }
    
    actual_gilstrap_dockets = []
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
                    assigned_to = result.get('assigned_to_str', '').lower()
                    
                    # Check if actually assigned to Rodney Gilstrap
                    if 'rodney gilstrap' in assigned_to or 'gilstrap' in assigned_to:
                        docket_id = result.get('id')
                        if docket_id and docket_id not in unique_dockets:
                            unique_dockets.add(docket_id)
                            actual_gilstrap_dockets.append(result)
                            page_count += 1
                
                logger.info(f"Page {page}: {page_count} actual Gilstrap dockets")
                
                # Check if there are more pages
                if not data.get('next'):
                    logger.info("Reached last page")
                    break
                
                page += 1
                
                # Safety limit
                if page > 100:
                    logger.info("Reached safety limit of 100 pages")
                    break
                
            else:
                logger.error(f"Error on page {page}: {response.status_code}")
                break
                
        except Exception as e:
            logger.error(f"Exception on page {page}: {e}")
            break
    
    logger.info(f"\n🎯 ACTUAL GILSTRAP DOCKETS: {len(actual_gilstrap_dockets)}")
    
    # Now try alternative search method
    logger.info("\nTrying alternative search method...")
    
    # Alternative search by assigned_to field
    alt_params = {
        'assigned_to_str': 'Rodney Gilstrap',
        'court': 'txed',
        'page_size': 100
    }
    
    alt_dockets = []
    alt_unique = set()
    page = 1
    
    while page <= 20:  # Limit to 20 pages
        logger.info(f"Alternative search page {page}...")
        
        current_params = alt_params.copy()
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
                    break
                
                for result in results:
                    docket_id = result.get('id')
                    if docket_id and docket_id not in alt_unique:
                        alt_unique.add(docket_id)
                        alt_dockets.append(result)
                
                logger.info(f"Alt page {page}: {len(results)} dockets")
                
                if not data.get('next'):
                    break
                
                page += 1
                
            else:
                break
                
        except Exception as e:
            logger.error(f"Alternative search page {page} error: {e}")
            break
    
    logger.info(f"Alternative search found: {len(alt_dockets)} dockets")
    
    # Combine results
    combined_unique = unique_dockets.union(alt_unique)
    
    logger.info(f"\n🎯 COMBINED TOTAL: {len(combined_unique)} unique Gilstrap dockets")
    
    # Show detailed analysis
    if actual_gilstrap_dockets:
        logger.info("\nDetailed analysis of actual Gilstrap dockets:")
        
        # Date analysis
        dates = [d.get('date_filed') for d in actual_gilstrap_dockets if d.get('date_filed')]
        if dates:
            dates.sort()
            logger.info(f"Date range: {dates[0]} to {dates[-1]}")
            
            # Year breakdown
            years = defaultdict(int)
            for date in dates:
                year = date[:4]
                years[year] += 1
            
            logger.info("Year breakdown:")
            for year, count in sorted(years.items()):
                logger.info(f"  {year}: {count} dockets")
        
        # Sample recent cases
        recent_cases = sorted(actual_gilstrap_dockets, 
                            key=lambda x: x.get('date_filed', ''), 
                            reverse=True)[:10]
        
        logger.info("\nRecent Judge Gilstrap cases:")
        for i, case in enumerate(recent_cases, 1):
            case_name = case.get('case_name', 'Unknown')
            date_filed = case.get('date_filed', 'Unknown')
            docket_number = case.get('docket_number', 'Unknown')
            
            logger.info(f"{i:2d}. {case_name}")
            logger.info(f"     Docket: {docket_number}, Filed: {date_filed}")
    
    return {
        'actual_gilstrap_dockets': len(actual_gilstrap_dockets),
        'alternative_search_dockets': len(alt_dockets),
        'combined_unique_dockets': len(combined_unique),
        'docket_details': actual_gilstrap_dockets[:50]  # First 50 for analysis
    }

if __name__ == "__main__":
    results = count_actual_gilstrap_dockets()
    
    # Save results
    with open('precise_gilstrap_count.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Precise count complete. Results saved to precise_gilstrap_count.json")
    print(f"\n🎯 FINAL ANSWER: {results['combined_unique_dockets']} dockets actually assigned to Judge Rodney Gilstrap")