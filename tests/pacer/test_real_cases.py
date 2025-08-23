#!/usr/bin/env python3
"""
Test PACER integration with real IP law case docket numbers
"""

import os
import sys
from pacer_integration import ProductionPACERRECAPClient, validate_environment

# Real patent case docket numbers from 2024
REAL_PATENT_CASES = [
    {
        'docket_number': '2:2024cv00162',
        'court': 'txed',
        'case_name': 'Byteweavr, LLC v. Databricks, Inc.',
        'filed_date': 'March 8, 2024'
    },
    {
        'docket_number': '2:2024cv00181',
        'court': 'txed',
        'case_name': 'Cerence Operating Company v. Samsung Electronics',
        'filed_date': 'March 15, 2024'
    },
    {
        'docket_number': '3:2024cv00217',
        'court': 'cand',
        'case_name': 'DoDots Licensing Solutions LLC v. Apple Inc.',
        'filed_date': 'January 12, 2024'
    }
]

def test_real_patent_cases():
    """Test PACER with real patent case docket numbers"""
    print("🚀 Testing PACER with Real Patent Cases")
    print("=" * 60)
    
    # Validate environment
    try:
        validate_environment()
    except EnvironmentError as e:
        print(f"❌ Environment validation failed: {e}")
        return False
    
    successful_cases = []
    failed_cases = []
    
    with ProductionPACERRECAPClient('PRODUCTION') as client:
        # Test first case to discover working method
        if REAL_PATENT_CASES:
            first_case = REAL_PATENT_CASES[0]
            print(f"\n🔍 Discovering method with: {first_case['case_name']}")
            
            try:
                method = client.discover_working_method(
                    first_case['docket_number'], 
                    first_case['court']
                )
                print(f"✅ Using method: {method}")
            except Exception as e:
                print(f"❌ Method discovery failed: {e}")
                return False
        
        # Test all cases
        for i, case in enumerate(REAL_PATENT_CASES):
            print(f"\n📋 Case {i+1}/{len(REAL_PATENT_CASES)}: {case['case_name']}")
            print(f"   Docket: {case['docket_number']} in {case['court'].upper()}")
            print(f"   Filed: {case['filed_date']}")
            
            try:
                # Fetch docket
                result = client.fetch_docket(
                    docket_number=case['docket_number'],
                    court=case['court'],
                    show_parties_and_counsel=True,
                    show_terminated_parties=False,
                    show_list_of_member_cases=False
                )
                
                request_id = result.get('id')
                print(f"   Request ID: {request_id}")
                
                # Monitor completion
                if request_id:
                    print("   ⏳ Monitoring request...")
                    final_status = client.recap_tester.monitor_request(request_id, timeout=60)
                    
                    status_code = final_status.get('status')
                    
                    # Interpret status
                    if status_code == 2:  # SUCCESSFUL
                        print(f"   ✅ SUCCESS! Document retrieved")
                        successful_cases.append(case)
                    elif status_code == 5:  # SUCCESSFUL_DUPLICATE
                        print(f"   ✅ Already in RECAP (free access!)")
                        successful_cases.append(case)
                    elif status_code == 3:  # FAILED
                        error_msg = final_status.get('message', 'Unknown error')
                        print(f"   ❌ Failed: {error_msg}")
                        failed_cases.append((case, error_msg))
                    elif status_code == 4:  # UNABLE TO FIND
                        print(f"   ⚠️  Not found in PACER")
                        failed_cases.append((case, "Not found"))
                    else:
                        print(f"   ❓ Status: {status_code}")
                        failed_cases.append((case, f"Status {status_code}"))
                
            except Exception as e:
                print(f"   💥 Error: {e}")
                failed_cases.append((case, str(e)))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print(f"   Total cases tested: {len(REAL_PATENT_CASES)}")
    print(f"   ✅ Successful: {len(successful_cases)}")
    print(f"   ❌ Failed: {len(failed_cases)}")
    
    if successful_cases:
        print("\n✅ Successfully Retrieved:")
        for case in successful_cases:
            print(f"   - {case['case_name']}")
    
    if failed_cases:
        print("\n❌ Failed Cases:")
        for case, error in failed_cases:
            print(f"   - {case['case_name']}: {error}")
    
    return len(successful_cases) > 0


if __name__ == "__main__":
    success = test_real_patent_cases()
    
    if success:
        print("\n🎉 PACER integration working with real cases!")
        print("✅ You can now fetch patent litigation documents")
    else:
        print("\n⚠️  Some issues with real case testing")
        print("Check the errors above for details")