#!/usr/bin/env python3
"""
Analyze Judge Gilstrap document availability in CourtListener
Check what date ranges are actually available
"""

import asyncio
import logging
import requests
import json
from datetime import datetime, timedelta
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gilstrap_analysis")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def analyze_judge_gilstrap_availability():
    """Analyze what Judge Gilstrap documents are available in CourtListener"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Gilstrap Analysis Tool'
    }
    
    logger.info("Analyzing Judge Gilstrap document availability in CourtListener")
    
    # Different search approaches
    search_methods = [
        {
            'name': 'Judge Name Search',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'judge:gilstrap',
                'type': 'o',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Broader Judge Search',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'judge:"Rodney Gilstrap"',
                'type': 'o',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Text Search',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'gilstrap',
                'type': 'o',
                'court': 'txed',
                'page_size': 100
            }
        },
        {
            'name': 'Date Range 2020-2025',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'judge:gilstrap',
                'type': 'o',
                'court': 'txed',
                'filed_after': '2020-01-01',
                'filed_before': '2025-12-31',
                'page_size': 100
            }
        },
        {
            'name': 'Date Range 2015-2019',
            'url': f'{BASE_URL}/search/',
            'params': {
                'q': 'judge:gilstrap',
                'type': 'o',
                'court': 'txed',
                'filed_after': '2015-01-01',
                'filed_before': '2019-12-31',
                'page_size': 100
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
                results_list = data.get('results', [])
                
                logger.info(f"  ✅ Found {count} documents")
                
                # Analyze dates
                dates = []
                for result in results_list:
                    date_filed = result.get('date_filed')
                    if date_filed:
                        dates.append(date_filed)
                
                if dates:
                    dates.sort()
                    logger.info(f"  📅 Date range: {dates[0]} to {dates[-1]}")
                    
                    # Year breakdown
                    years = {}
                    for date in dates:
                        year = date[:4]
                        years[year] = years.get(year, 0) + 1
                    
                    for year, count in sorted(years.items()):
                        logger.info(f"    {year}: {count} documents")
                
                results[method['name']] = {
                    'total_count': count,
                    'results_returned': len(results_list),
                    'dates': dates,
                    'year_breakdown': years if dates else {},
                    'success': True
                }
                
                # Show some sample document info
                if results_list:
                    logger.info("  📄 Sample documents:")
                    for i, doc in enumerate(results_list[:3]):
                        logger.info(f"    {i+1}. {doc.get('case_name', 'Unknown')} ({doc.get('date_filed', 'No date')})")
                
            else:
                logger.error(f"  ❌ Error {response.status_code}: {response.text}")
                results[method['name']] = {
                    'error': f"HTTP {response.status_code}",
                    'success': False
                }
        
        except Exception as e:
            logger.error(f"  ❌ Exception: {e}")
            results[method['name']] = {
                'error': str(e),
                'success': False
            }
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("JUDGE GILSTRAP AVAILABILITY ANALYSIS SUMMARY")
    logger.info("="*60)
    
    for method_name, result in results.items():
        if result.get('success'):
            logger.info(f"{method_name}: {result['total_count']} documents")
            if result.get('year_breakdown'):
                years = ", ".join([f"{year}({count})" for year, count in result['year_breakdown'].items()])
                logger.info(f"  Years: {years}")
        else:
            logger.info(f"{method_name}: FAILED - {result.get('error', 'Unknown')}")
    
    logger.info("="*60)
    
    return results

if __name__ == "__main__":
    results = analyze_judge_gilstrap_availability()
    
    # Save results to file
    with open('gilstrap_availability_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Analysis complete. Results saved to gilstrap_availability_analysis.json")