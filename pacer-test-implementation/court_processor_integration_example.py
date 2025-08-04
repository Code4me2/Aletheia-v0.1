#!/usr/bin/env python3
"""
Example: Integrating PACER authentication into court processor pipeline

This shows how to use the ProductionPACERRECAPClient in a real workflow
"""

import os
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from pacer_integration import ProductionPACERRECAPClient, validate_environment


class PACERDocumentFetcher:
    """
    Example class showing how to integrate PACER fetching into court processor
    """
    
    def __init__(self, environment='PRODUCTION'):
        self.client = ProductionPACERRECAPClient(environment)
        self.working_method_discovered = False
        
    async def fetch_documents_for_cases(self, cases: List[Dict]) -> List[Dict]:
        """
        Fetch documents for a list of cases
        
        Args:
            cases: List of dicts with 'docket_number' and 'court' keys
            
        Returns:
            List of results with document data or errors
        """
        results = []
        
        # Discover working method with first case if not done
        if not self.working_method_discovered and cases:
            first_case = cases[0]
            try:
                print(f"🔍 Discovering PACER integration method with {first_case['docket_number']}...")
                self.client.discover_working_method(
                    first_case['docket_number'],
                    first_case['court']
                )
                self.working_method_discovered = True
            except Exception as e:
                print(f"❌ Failed to discover working method: {e}")
                return []
        
        # Process each case
        for case in cases:
            result = await self._fetch_single_case(case)
            results.append(result)
            
            # Small delay to be respectful of API
            await asyncio.sleep(1)
        
        return results
    
    async def _fetch_single_case(self, case: Dict) -> Dict:
        """Fetch documents for a single case"""
        docket_number = case.get('docket_number')
        court = case.get('court')
        
        if not docket_number or not court:
            return {
                'success': False,
                'case': case,
                'error': 'Missing docket_number or court'
            }
        
        try:
            # Request the docket
            print(f"📄 Fetching {docket_number} from {court}...")
            
            fetch_result = self.client.fetch_docket(
                docket_number=docket_number,
                court=court,
                show_parties_and_counsel=True,
                show_terminated_parties=False,
                show_list_of_member_cases=False
            )
            
            request_id = fetch_result.get('id')
            if not request_id:
                return {
                    'success': False,
                    'case': case,
                    'error': 'No request ID returned'
                }
            
            # Monitor completion
            print(f"⏳ Monitoring request {request_id}...")
            final_status = self.client.recap_tester.monitor_request(request_id, timeout=300)
            
            # Check status
            status = final_status.get('status')
            if status in [2, 5]:  # Success statuses
                return {
                    'success': True,
                    'case': case,
                    'request_id': request_id,
                    'status': final_status,
                    'cost': final_status.get('cost', 0),
                    'completed_at': datetime.now().isoformat()
                }
            else:
                return {
                    'success': False,
                    'case': case,
                    'request_id': request_id,
                    'error': final_status.get('error_message', 'Unknown error'),
                    'status_code': status
                }
                
        except Exception as e:
            return {
                'success': False,
                'case': case,
                'error': str(e),
                'error_type': type(e).__name__
            }
    
    def get_completed_documents(self, request_ids: List[str]) -> List[Dict]:
        """
        Retrieve completed documents by request ID
        
        This would integrate with court processor's storage
        """
        documents = []
        
        for request_id in request_ids:
            try:
                # In production, this would fetch from CourtListener's API
                # or from your local database where results are stored
                print(f"📥 Retrieving completed document for request {request_id}")
                
                # Example: fetch from RECAP API
                # doc = fetch_completed_document(request_id)
                # documents.append(doc)
                
            except Exception as e:
                print(f"❌ Error retrieving {request_id}: {e}")
        
        return documents


async def example_integration():
    """
    Example showing how to integrate PACER fetching into court processor pipeline
    """
    print("🚀 Court Processor PACER Integration Example")
    print("=" * 50)
    
    # Validate environment
    try:
        validate_environment()
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
        return
    
    # Example cases to fetch (replace with real data)
    test_cases = [
        {
            'docket_number': '1:20-cv-12345',
            'court': 'txed',
            'case_name': 'Example Patent Case'
        },
        {
            'docket_number': '2:21-cv-67890',
            'court': 'cand',
            'case_name': 'Example Tech Case'
        }
    ]
    
    # Initialize fetcher
    fetcher = PACERDocumentFetcher(environment='QA')  # Use PRODUCTION in real usage
    
    # Fetch documents
    print(f"\n📋 Processing {len(test_cases)} cases...")
    results = await fetcher.fetch_documents_for_cases(test_cases)
    
    # Process results
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"\n📊 Results Summary:")
    print(f"   ✅ Successful: {len(successful)}")
    print(f"   ❌ Failed: {len(failed)}")
    
    # Show successful fetches
    if successful:
        print("\n✅ Successful Fetches:")
        for result in successful:
            case = result['case']
            print(f"   - {case['docket_number']} ({case['court']})")
            print(f"     Request ID: {result['request_id']}")
            print(f"     Cost: ${result.get('cost', 0):.2f}")
    
    # Show failures
    if failed:
        print("\n❌ Failed Fetches:")
        for result in failed:
            case = result['case']
            print(f"   - {case['docket_number']} ({case['court']})")
            print(f"     Error: {result['error']}")
    
    # In production, you would now:
    # 1. Retrieve the completed documents
    # 2. Process them through the 11-stage pipeline
    # 3. Store in opinions_unified table
    
    print("\n🏁 Integration example completed!")


def integrate_with_court_processor():
    """
    Example of how to modify court_processor_orchestrator.py to use PACER
    """
    code_example = '''
# In court_processor_orchestrator.py, add:

from pacer_integration import ProductionPACERRECAPClient

class CourtProcessorOrchestrator:
    def __init__(self):
        # ... existing init code ...
        self.pacer_client = None
        if os.environ.get('ENABLE_PACER_FETCH', 'false').lower() == 'true':
            self.pacer_client = ProductionPACERRECAPClient('PRODUCTION')
    
    async def fetch_pacer_documents(self, missing_cases):
        """Fetch documents from PACER for cases not in RECAP"""
        if not self.pacer_client:
            logger.info("PACER fetching disabled")
            return []
        
        logger.info(f"Fetching {len(missing_cases)} documents from PACER...")
        
        # Discover working method if needed
        if not self.pacer_client.preferred_method:
            test_case = missing_cases[0]
            self.pacer_client.discover_working_method(
                test_case['docket_number'],
                test_case['court']
            )
        
        # Fetch each case
        results = []
        for case in missing_cases:
            try:
                result = self.pacer_client.fetch_docket(
                    docket_number=case['docket_number'],
                    court=case['court']
                )
                results.append(result)
            except Exception as e:
                logger.error(f"PACER fetch failed for {case}: {e}")
        
        return results
'''
    
    print("\n📝 Integration Code Example:")
    print("-" * 50)
    print(code_example)


if __name__ == "__main__":
    # Run the async example
    asyncio.run(example_integration())
    
    # Show integration code
    integrate_with_court_processor()