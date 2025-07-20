#!/usr/bin/env python3
"""
Verify what Judge Gilstrap information is actually in Haystack
"""

import requests
import json
import logging
import os
import psycopg2
from psycopg2.extras import RealDictCursor

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_haystack")

HAYSTACK_URL = os.getenv('HAYSTACK_URL', 'http://haystack-service:8000')

# Database configuration
DB_CONFIG = {
    'host': 'db',
    'database': 'aletheia',
    'user': 'aletheia',
    'password': 'aletheia123'
}

def test_haystack_gilstrap_search():
    """Test Haystack search for Judge Gilstrap information"""
    
    logger.info("Testing Haystack search for Judge Gilstrap information...")
    
    # Comprehensive search queries
    search_queries = [
        "Judge Gilstrap",
        "Rodney Gilstrap",
        "Judge Rodney Gilstrap",
        "Gilstrap patent",
        "Eastern District of Texas Gilstrap",
        "SurvMatic LLC",  # Recent docket case
        "Televo LLC",     # Recent docket case
        "Casmir v. Allstate",  # Recent docket case
        "Polaris Powerled",  # Opinion case
        "Core Wireless",     # Opinion case
        "Intellectual Ventures"  # Opinion case
    ]
    
    results = {}
    total_documents_found = 0
    
    for query in search_queries:
        logger.info(f"\nSearching for: '{query}'")
        
        try:
            response = requests.post(
                f"{HAYSTACK_URL}/search",
                json={"query": query, "top_k": 20},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('results', [])
                
                logger.info(f"  ✅ Found {len(documents)} results")
                
                # Analyze results
                gilstrap_docs = 0
                opinion_docs = 0
                docket_docs = 0
                
                for doc in documents:
                    content = doc.get('content', '').lower()
                    meta = doc.get('meta', {})
                    
                    if 'gilstrap' in content:
                        gilstrap_docs += 1
                    
                    # Check if it's an opinion
                    if 'opinion' in content or 'united states district judge' in content:
                        opinion_docs += 1
                    
                    # Check if it's docket-related
                    if 'docket' in content or 'case number' in content:
                        docket_docs += 1
                
                results[query] = {
                    'total_results': len(documents),
                    'gilstrap_matches': gilstrap_docs,
                    'opinion_docs': opinion_docs,
                    'docket_docs': docket_docs,
                    'top_scores': [doc.get('score', 0) for doc in documents[:5]]
                }
                
                total_documents_found += len(documents)
                
                # Show sample results
                if documents:
                    logger.info(f"  Top result score: {documents[0].get('score', 0):.3f}")
                    sample_content = documents[0].get('content', '')[:200]
                    logger.info(f"  Sample content: {sample_content}...")
                
            else:
                logger.error(f"  ❌ Search failed: {response.status_code}")
                results[query] = {'error': f"HTTP {response.status_code}"}
                
        except Exception as e:
            logger.error(f"  ❌ Search error: {e}")
            results[query] = {'error': str(e)}
    
    return results, total_documents_found

def check_database_vs_haystack():
    """Compare what's in the database vs what's searchable in Haystack"""
    
    logger.info("\nComparing database vs Haystack content...")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get all Gilstrap documents from database
            cursor.execute("""
                SELECT 
                    id,
                    case_number,
                    document_type,
                    metadata->>'case_name' as case_name,
                    metadata->>'date_filed' as date_filed,
                    metadata->>'source' as source,
                    LENGTH(content) as content_length
                FROM court_documents
                WHERE metadata->>'judge_name' ILIKE '%gilstrap%'
                OR case_number ILIKE '%gilstrap%'
                ORDER BY (metadata->>'date_filed')::date DESC NULLS LAST
            """)
            
            db_documents = cursor.fetchall()
            
            logger.info(f"📊 DATABASE SUMMARY:")
            logger.info(f"   Total Gilstrap documents: {len(db_documents)}")
            
            if db_documents:
                # Year breakdown
                years = {}
                for doc in db_documents:
                    date_filed = doc.get('date_filed', '')
                    if date_filed:
                        year = date_filed[:4]
                        years[year] = years.get(year, 0) + 1
                
                logger.info(f"   Year breakdown: {dict(sorted(years.items()))}")
                
                # Content analysis
                total_chars = sum(doc.get('content_length', 0) for doc in db_documents)
                logger.info(f"   Total content: {total_chars:,} characters")
                
                # Document types
                doc_types = {}
                for doc in db_documents:
                    doc_type = doc.get('document_type', 'unknown')
                    doc_types[doc_type] = doc_types.get(doc_type, 0) + 1
                
                logger.info(f"   Document types: {doc_types}")
                
                # Sample documents
                logger.info(f"\n📄 SAMPLE DOCUMENTS IN DATABASE:")
                for i, doc in enumerate(db_documents[:5], 1):
                    case_name = doc.get('case_name') or doc.get('case_number')
                    date_filed = doc.get('date_filed', 'No date')
                    content_length = doc.get('content_length', 0)
                    source = doc.get('source', 'unknown')
                    
                    logger.info(f"   {i}. {case_name}")
                    logger.info(f"      Date: {date_filed}, Content: {content_length:,} chars, Source: {source}")
        
        conn.close()
        
        return db_documents
        
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return []

def verify_haystack_ingestion():
    """Verify specific documents are in Haystack"""
    
    logger.info("\nVerifying specific document ingestion in Haystack...")
    
    # Test specific case names that should be in Haystack
    specific_cases = [
        "Polaris Powerled Techs., LLC v. Samsung Elecs. Am., Inc.",
        "Core Wireless Licensing S.A.R.L. v. LG Elecs., Inc.",
        "Intellectual Ventures II LLC v. Bitco Gen. Ins. Corp.",
        "Seven Networks, LLC v. Google LLC",
        "SurvMatic LLC",
        "Televo LLC"
    ]
    
    found_cases = 0
    
    for case in specific_cases:
        logger.info(f"\nSearching for specific case: '{case}'")
        
        try:
            response = requests.post(
                f"{HAYSTACK_URL}/search",
                json={"query": case, "top_k": 5},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                documents = data.get('results', [])
                
                # Check if we found the specific case
                case_found = False
                for doc in documents:
                    content = doc.get('content', '').lower()
                    meta = doc.get('meta', {})
                    
                    if case.lower() in content:
                        case_found = True
                        found_cases += 1
                        logger.info(f"  ✅ Found! Score: {doc.get('score', 0):.3f}")
                        
                        # Show metadata
                        db_id = meta.get('database_id')
                        source = meta.get('source', 'unknown')
                        logger.info(f"  📋 Database ID: {db_id}, Source: {source}")
                        break
                
                if not case_found:
                    logger.info(f"  ❌ Not found in Haystack")
            else:
                logger.error(f"  ❌ Search failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"  ❌ Search error: {e}")
    
    logger.info(f"\n📈 VERIFICATION SUMMARY:")
    logger.info(f"   Specific cases tested: {len(specific_cases)}")
    logger.info(f"   Cases found in Haystack: {found_cases}")
    logger.info(f"   Success rate: {found_cases/len(specific_cases)*100:.1f}%")
    
    return found_cases, len(specific_cases)

def main():
    """Main verification function"""
    
    logger.info("="*80)
    logger.info("HAYSTACK GILSTRAP VERIFICATION")
    logger.info("="*80)
    logger.info("Checking if all Judge Gilstrap information is in Haystack")
    logger.info("")
    
    # Step 1: Check database content
    db_documents = check_database_vs_haystack()
    
    # Step 2: Test Haystack search
    search_results, total_found = test_haystack_gilstrap_search()
    
    # Step 3: Verify specific documents
    found_cases, total_cases = verify_haystack_ingestion()
    
    # Step 4: Summary
    logger.info("\n" + "="*80)
    logger.info("FINAL VERIFICATION SUMMARY")
    logger.info("="*80)
    
    logger.info(f"📊 DATABASE STATUS:")
    logger.info(f"   Judge Gilstrap documents in database: {len(db_documents)}")
    
    logger.info(f"\n🔍 HAYSTACK SEARCH STATUS:")
    logger.info(f"   Search queries tested: {len(search_results)}")
    logger.info(f"   Total search results found: {total_found}")
    
    successful_searches = len([r for r in search_results.values() if 'error' not in r])
    logger.info(f"   Successful searches: {successful_searches}/{len(search_results)}")
    
    logger.info(f"\n✅ DOCUMENT VERIFICATION:")
    logger.info(f"   Specific cases verified: {found_cases}/{total_cases}")
    
    # Overall assessment
    pipeline_success = (
        len(db_documents) > 0 and
        successful_searches > 0 and
        found_cases > 0
    )
    
    logger.info(f"\n🎯 PIPELINE STATUS: {'✅ SUCCESS' if pipeline_success else '❌ INCOMPLETE'}")
    
    if pipeline_success:
        logger.info("   ✅ Documents in PostgreSQL database")
        logger.info("   ✅ Documents searchable in Haystack")
        logger.info("   ✅ Full pipeline operational")
    else:
        logger.info("   ❌ Pipeline may have gaps")
    
    logger.info("="*80)
    
    return {
        'db_documents': len(db_documents),
        'search_results': search_results,
        'verified_cases': found_cases,
        'total_cases': total_cases,
        'pipeline_success': pipeline_success
    }

if __name__ == "__main__":
    results = main()
    
    # Save results
    with open('haystack_verification.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info("Verification complete. Results saved to haystack_verification.json")