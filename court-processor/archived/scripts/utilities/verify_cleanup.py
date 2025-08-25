#!/usr/bin/env python3
"""Verify that the cleanup didn't break anything"""

import subprocess
import sys
import json

def run_test(command, description):
    """Run a test command and report results"""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ PASSED")
            if "healthy" in result.stdout or "processed" in result.stdout:
                print(f"Output preview: {result.stdout[:200]}...")
            return True
        else:
            print("❌ FAILED")
            print(f"Error: {result.stderr[:500]}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ TIMEOUT")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

def main():
    """Run all verification tests"""
    print("Court Processor Cleanup Verification")
    print("=" * 60)
    
    tests = [
        # API health check
        ("docker exec aletheia-court-processor-1 curl -s http://localhost:8090/", 
         "API Health Check"),
        
        # Pipeline execution
        ("docker exec aletheia-court-processor-1 python3 scripts/run_pipeline.py 1",
         "Pipeline Execution (1 document)"),
        
        # Database connectivity
        ("docker exec aletheia-court-processor-1 python3 -c \"from services.database import get_db_connection; conn = get_db_connection(); print('DB connected'); conn.close()\"",
         "Database Connectivity"),
        
        # Import verification
        ("docker exec aletheia-court-processor-1 python3 -c \"import eleven_stage_pipeline_robust_complete; print('Pipeline imports OK')\"",
         "Core Pipeline Imports"),
    ]
    
    results = []
    for command, description in tests:
        results.append(run_test(command, description))
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    passed = sum(results)
    total = len(results)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! Cleanup was successful.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())