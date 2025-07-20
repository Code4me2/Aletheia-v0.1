#!/usr/bin/env python3
"""
Analyze Judge Gilstrap docket content to determine character count
"""

import requests
import json
import os
import logging
from datetime import datetime
import asyncio
import aiohttp

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("docket_content")

API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', 'f751990518aacab953214f2e56ac6ccbff9e2c14')
BASE_URL = 'https://www.courtlistener.com/api/rest/v4'

def analyze_docket_content_size():
    """Analyze the content size of Judge Gilstrap dockets"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Docket Content Analyzer'
    }
    
    logger.info("Analyzing Judge Gilstrap docket content size...")
    
    # Get sample dockets to analyze
    params = {
        'assigned_to_str__icontains': 'gilstrap',
        'court': 'txed',
        'page_size': 20  # Get first 20 for analysis
    }
    
    try:
        response = requests.get(
            f'{BASE_URL}/dockets/',
            params=params,
            headers=headers,
            timeout=30
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch dockets: {response.status_code}")
            return None
        
        data = response.json()
        dockets = data.get('results', [])
        
        if not dockets:
            logger.error("No dockets found")
            return None
        
        logger.info(f"Analyzing {len(dockets)} dockets...")
        
        total_content_chars = 0
        docket_analyses = []
        
        for i, docket in enumerate(dockets, 1):
            logger.info(f"\nAnalyzing docket {i}/{len(dockets)}: {docket.get('case_name', 'Unknown')}")
            
            # Get basic docket info
            docket_id = docket.get('id')
            case_name = docket.get('case_name', 'Unknown')
            docket_number = docket.get('docket_number', 'Unknown')
            date_filed = docket.get('date_filed', 'Unknown')
            assigned_to = docket.get('assigned_to_str', 'Unknown')
            
            # Calculate content from basic fields
            basic_content = f"""
Case: {case_name}
Docket Number: {docket_number}
Date Filed: {date_filed}
Assigned To: {assigned_to}
Court: Eastern District of Texas
"""
            
            basic_chars = len(basic_content)
            
            # Get docket entries (these contain the procedural information)
            docket_entries_chars = 0
            try:
                entries_response = requests.get(
                    f'{BASE_URL}/docket-entries/?docket={docket_id}',
                    headers=headers,
                    timeout=30
                )
                
                if entries_response.status_code == 200:
                    entries_data = entries_response.json()
                    entries = entries_data.get('results', [])
                    
                    for entry in entries:
                        # Each entry has description, date, and potentially documents
                        entry_text = f"""
Date: {entry.get('date_created', 'Unknown')}
Entry: {entry.get('description', 'No description')}
"""
                        docket_entries_chars += len(entry_text)
                    
                    logger.info(f"  Found {len(entries)} docket entries")
                else:
                    logger.warning(f"  Could not fetch docket entries: {entries_response.status_code}")
                    
            except Exception as e:
                logger.error(f"  Error fetching docket entries: {e}")
            
            # Get recap documents (PDFs and filings)
            recap_docs_chars = 0
            try:
                recap_response = requests.get(
                    f'{BASE_URL}/recap-documents/?docket_entry__docket={docket_id}',
                    headers=headers,
                    timeout=30
                )
                
                if recap_response.status_code == 200:
                    recap_data = recap_response.json()
                    recap_docs = recap_data.get('results', [])
                    
                    for doc in recap_docs:
                        # Each RECAP document has description and metadata
                        doc_text = f"""
Document: {doc.get('description', 'No description')}
Document Type: {doc.get('document_type', 'Unknown')}
Page Count: {doc.get('page_count', 'Unknown')}
"""
                        recap_docs_chars += len(doc_text)
                    
                    logger.info(f"  Found {len(recap_docs)} RECAP documents")
                else:
                    logger.warning(f"  Could not fetch RECAP documents: {recap_response.status_code}")
                    
            except Exception as e:
                logger.error(f"  Error fetching RECAP documents: {e}")
            
            # Calculate total for this docket
            docket_total_chars = basic_chars + docket_entries_chars + recap_docs_chars
            total_content_chars += docket_total_chars
            
            docket_analysis = {
                'docket_id': docket_id,
                'case_name': case_name,
                'docket_number': docket_number,
                'date_filed': date_filed,
                'assigned_to': assigned_to,
                'basic_content_chars': basic_chars,
                'docket_entries_chars': docket_entries_chars,
                'recap_docs_chars': recap_docs_chars,
                'total_chars': docket_total_chars
            }
            
            docket_analyses.append(docket_analysis)
            
            logger.info(f"  Content breakdown:")
            logger.info(f"    Basic info: {basic_chars:,} chars")
            logger.info(f"    Docket entries: {docket_entries_chars:,} chars")
            logger.info(f"    RECAP docs: {recap_docs_chars:,} chars")
            logger.info(f"    Total: {docket_total_chars:,} chars")
        
        # Calculate statistics
        avg_chars_per_docket = total_content_chars / len(dockets) if dockets else 0
        
        # Extrapolate to all 20 dockets
        estimated_total_chars = avg_chars_per_docket * 20
        
        logger.info(f"\n📊 DOCKET CONTENT ANALYSIS SUMMARY:")
        logger.info(f"   Dockets analyzed: {len(dockets)}")
        logger.info(f"   Total content: {total_content_chars:,} characters")
        logger.info(f"   Average per docket: {avg_chars_per_docket:,.0f} characters")
        logger.info(f"   Estimated total for all 20 dockets: {estimated_total_chars:,.0f} characters")
        
        # Compare with opinions
        opinion_chars = 1134576  # From previous analysis
        docket_percentage = (estimated_total_chars / opinion_chars) * 100 if opinion_chars > 0 else 0
        
        logger.info(f"\n📈 COMPARISON WITH OPINIONS:")
        logger.info(f"   Opinion content: {opinion_chars:,} characters")
        logger.info(f"   Estimated docket content: {estimated_total_chars:,.0f} characters")
        logger.info(f"   Dockets are {docket_percentage:.1f}% of opinion content")
        
        # Content breakdown analysis
        total_basic = sum(d['basic_content_chars'] for d in docket_analyses)
        total_entries = sum(d['docket_entries_chars'] for d in docket_analyses)
        total_recap = sum(d['recap_docs_chars'] for d in docket_analyses)
        
        logger.info(f"\n📋 CONTENT TYPE BREAKDOWN:")
        logger.info(f"   Basic docket info: {total_basic:,} chars ({total_basic/total_content_chars*100:.1f}%)")
        logger.info(f"   Docket entries: {total_entries:,} chars ({total_entries/total_content_chars*100:.1f}%)")
        logger.info(f"   RECAP documents: {total_recap:,} chars ({total_recap/total_content_chars*100:.1f}%)")
        
        return {
            'dockets_analyzed': len(dockets),
            'total_content_chars': total_content_chars,
            'avg_chars_per_docket': avg_chars_per_docket,
            'estimated_total_chars': estimated_total_chars,
            'docket_analyses': docket_analyses,
            'comparison_with_opinions': {
                'opinion_chars': opinion_chars,
                'docket_percentage': docket_percentage
            },
            'content_breakdown': {
                'basic_info': total_basic,
                'docket_entries': total_entries,
                'recap_documents': total_recap
            }
        }
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return None

def analyze_specific_recent_dockets():
    """Analyze the specific recent Judge Gilstrap dockets we identified"""
    
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'User-Agent': 'Recent Docket Analyzer'
    }
    
    logger.info("\nAnalyzing specific recent Judge Gilstrap dockets...")
    
    # Get exact matches for Rodney Gilstrap
    params = {
        'assigned_to_str': 'Rodney Gilstrap',
        'court': 'txed',
        'page_size': 10
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
            recent_dockets = data.get('results', [])
            
            logger.info(f"Found {len(recent_dockets)} recent Gilstrap dockets")
            
            total_recent_chars = 0
            
            for docket in recent_dockets:
                case_name = docket.get('case_name', 'Unknown')
                docket_number = docket.get('docket_number', 'Unknown')
                date_filed = docket.get('date_filed', 'Unknown')
                
                # Estimate content based on case complexity
                # Patent cases typically have more content
                if any(term in case_name.lower() for term in ['llc', 'patent', 'technology', 'wireless']):
                    estimated_chars = 8000  # Patent cases tend to be more complex
                else:
                    estimated_chars = 5000  # General cases
                
                total_recent_chars += estimated_chars
                
                logger.info(f"  {case_name} ({docket_number}): ~{estimated_chars:,} chars")
            
            logger.info(f"\n📊 RECENT DOCKETS ESTIMATE:")
            logger.info(f"   Recent dockets: {len(recent_dockets)}")
            logger.info(f"   Estimated total content: {total_recent_chars:,} characters")
            
            return total_recent_chars
        
    except Exception as e:
        logger.error(f"Recent docket analysis failed: {e}")
        return 0

def main():
    """Main analysis function"""
    
    logger.info("="*80)
    logger.info("JUDGE GILSTRAP DOCKET CONTENT ANALYSIS")
    logger.info("="*80)
    
    # Analyze sample dockets
    analysis_result = analyze_docket_content_size()
    
    # Analyze recent specific dockets
    recent_chars = analyze_specific_recent_dockets()
    
    if analysis_result:
        logger.info("\n" + "="*80)
        logger.info("FINAL DOCKET CONTENT SUMMARY")
        logger.info("="*80)
        
        estimated_total = analysis_result['estimated_total_chars']
        opinion_chars = analysis_result['comparison_with_opinions']['opinion_chars']
        
        logger.info(f"🎯 ESTIMATED DOCKET CONTENT: {estimated_total:,.0f} characters")
        logger.info(f"📊 COMPARISON:")
        logger.info(f"   Judge Gilstrap opinions: {opinion_chars:,} characters")
        logger.info(f"   Judge Gilstrap dockets: {estimated_total:,.0f} characters")
        logger.info(f"   Dockets are {estimated_total/opinion_chars*100:.1f}% of opinion content")
        
        combined_total = opinion_chars + estimated_total
        logger.info(f"   Combined total: {combined_total:,.0f} characters")
        
        logger.info("="*80)
        
        return estimated_total
    
    return 0

if __name__ == "__main__":
    result = main()
    print(f"\n🎯 ANSWER: Judge Gilstrap dockets contain approximately {result:,.0f} characters")