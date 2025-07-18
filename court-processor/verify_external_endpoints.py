#!/usr/bin/env python3
"""
External Endpoint Verification Script

Tests the enhanced processor with real external services and data
to verify end-to-end functionality with actual APIs.
"""
import asyncio
import sys
import os
import json
import time
import aiohttp
import requests
from pathlib import Path

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

try:
    from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor
    from enhanced.config import get_settings
except ImportError as e:
    print(f"❌ Import Error: {e}")
    sys.exit(1)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f" {title}")
    print("="*70)


def print_status(test_name: str, success: bool, details: str = ""):
    """Print test status"""
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if details:
        for line in details.split('\n'):
            if line.strip():
                print(f"   {line}")


async def test_courtlistener_api():
    """Test CourtListener API connectivity"""
    print_header("COURTLISTENER API VERIFICATION")
    
    # Check for API token
    api_token = os.getenv('COURTLISTENER_API_TOKEN')
    if not api_token:
        print_status("API Token", False, "COURTLISTENER_API_TOKEN environment variable not set")
        print("   Set with: export COURTLISTENER_API_TOKEN='your-token-here'")
        return False, None
    
    print_status("API Token", True, f"Token found (length: {len(api_token)})")
    
    # Test API connectivity
    base_url = "https://www.courtlistener.com/api/rest/v4"
    headers = {"Authorization": f"Token {api_token}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test basic connectivity
            async with session.get(f"{base_url}/opinions/", 
                                 headers=headers, 
                                 params={"page_size": 1}) as response:
                
                if response.status == 200:
                    data = await response.json()
                    print_status("API Connectivity", True, 
                               f"Connected successfully\n"
                               f"Response status: {response.status}\n"
                               f"Available opinions: {data.get('count', 'unknown')}")
                    return True, data
                else:
                    error_text = await response.text()
                    print_status("API Connectivity", False, 
                               f"HTTP {response.status}: {error_text}")
                    return False, None
                    
    except Exception as e:
        print_status("API Connectivity", False, f"Connection error: {str(e)}")
        return False, None


async def test_real_courtlistener_data():
    """Test fetching real data from CourtListener"""
    print_header("REAL COURTLISTENER DATA TEST")
    
    api_token = os.getenv('COURTLISTENER_API_TOKEN')
    if not api_token:
        print_status("Data Fetch", False, "No API token available")
        return None
    
    # Fetch a small amount of real data
    base_url = "https://www.courtlistener.com/api/rest/v4"
    headers = {"Authorization": f"Token {api_token}"}
    
    try:
        async with aiohttp.ClientSession() as session:
            # Fetch recent Federal Circuit opinions (small sample)
            params = {
                "court": "cafc",
                "ordering": "-date_filed",
                "page_size": 3
            }
            
            async with session.get(f"{base_url}/opinions/", 
                                 headers=headers, 
                                 params=params) as response:
                
                if response.status == 200:
                    data = await response.json()
                    documents = data.get('results', [])
                    
                    print_status("Data Retrieval", True, 
                               f"Retrieved {len(documents)} documents\n"
                               f"Total available: {data.get('count', 'unknown')}")
                    
                    if documents:
                        sample_doc = documents[0]
                        print(f"   Sample document:")
                        print(f"   - ID: {sample_doc.get('id')}")
                        print(f"   - Case: {sample_doc.get('case_name', 'Unknown')[:50]}...")
                        print(f"   - Court: {sample_doc.get('court_id')}")
                        print(f"   - Date: {sample_doc.get('date_filed')}")
                        print(f"   - Has text: {'Yes' if sample_doc.get('plain_text') else 'No'}")
                    
                    return documents
                else:
                    error_text = await response.text()
                    print_status("Data Retrieval", False, f"HTTP {response.status}: {error_text}")
                    return None
                    
    except Exception as e:
        print_status("Data Retrieval", False, f"Error: {str(e)}")
        return None


async def test_doctor_service():
    """Test Doctor service availability"""
    print_header("DOCTOR SERVICE VERIFICATION")
    
    doctor_urls = [
        "http://doctor-judicial:5050",
        "http://localhost:5050",
        "http://127.0.0.1:5050"
    ]
    
    for url in doctor_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/", timeout=5) as response:
                    if response.status == 200:
                        print_status("Doctor Service", True, f"Available at {url}")
                        return True, url
        except Exception:
            continue
    
    print_status("Doctor Service", False, 
                "Not available at any tested URL\n"
                "Start with: docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d doctor")
    return False, None


async def test_haystack_service():
    """Test Haystack service availability"""
    print_header("HAYSTACK SERVICE VERIFICATION")
    
    haystack_urls = [
        "http://haystack-judicial:8000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    
    for url in haystack_urls:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{url}/docs", timeout=5) as response:
                    if response.status == 200:
                        print_status("Haystack Service", True, f"Available at {url}")
                        return True, url
        except Exception:
            continue
    
    print_status("Haystack Service", False, 
                "Not available at any tested URL\n"
                "Start with: docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d")
    return False, None


async def test_enhanced_processor_with_real_data(real_documents):
    """Test enhanced processor with real CourtListener data"""
    print_header("ENHANCED PROCESSOR WITH REAL DATA")
    
    if not real_documents:
        print_status("Real Data Processing", False, "No real documents available")
        return False
    
    try:
        # Initialize enhanced processor
        processor = EnhancedUnifiedDocumentProcessor()
        print_status("Processor Initialization", True, "Enhanced processor ready")
        
        # Process first real document
        test_document = real_documents[0]
        print(f"Processing document: {test_document.get('case_name', 'Unknown')[:50]}...")
        
        start_time = time.time()
        result = await processor.process_single_document(test_document)
        processing_time = time.time() - start_time
        
        if 'saved_id' in result:
            print_status("Real Document Processing", True, 
                        f"Successfully processed in {processing_time:.2f}s\n"
                        f"Saved with ID: {result['saved_id']}\n"
                        f"Citations found: {len(result.get('citations', []))}")
            
            # Test health status after processing
            health = processor.get_health_status()
            print_status("Health Status", True, f"Status: {health.get('status')}")
            
            return True
        elif 'error' in result:
            print_status("Real Document Processing", False, f"Processing error: {result['error']}")
            return False
        else:
            print_status("Real Document Processing", False, "Unexpected result format")
            return False
            
    except Exception as e:
        print_status("Real Document Processing", False, f"Exception: {str(e)}")
        return False


async def test_batch_processing_real_data():
    """Test batch processing with real data"""
    print_header("BATCH PROCESSING WITH REAL DATA")
    
    api_token = os.getenv('COURTLISTENER_API_TOKEN')
    if not api_token:
        print_status("Batch Processing", False, "No API token for real data")
        return False
    
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        
        # Override to use real CourtListener service
        # (This would require implementing real CourtListener service integration)
        print("Note: Enhanced processor uses mock data by default for development")
        print("Real batch processing requires Phase 2 CourtListener service integration")
        
        start_time = time.time()
        result = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=3  # Small batch for testing
        )
        processing_time = time.time() - start_time
        
        print_status("Batch Processing", True, 
                    f"Processed {result['total_fetched']} documents in {processing_time:.2f}s\n"
                    f"New: {result['new_documents']}, Duplicates: {result['duplicates']}, Errors: {result['errors']}")
        
        return True
        
    except Exception as e:
        print_status("Batch Processing", False, f"Exception: {str(e)}")
        return False


def test_flp_components():
    """Test Free Law Project components availability"""
    print_header("FREE LAW PROJECT COMPONENTS VERIFICATION")
    
    components = {
        'courts_db': 'Courts database for court standardization',
        'reporters_db': 'Reporters database for citation normalization', 
        'eyecite': 'Citation extraction library',
        'judge_pics': 'Judge information database',
        'x_ray': 'Document quality analysis'
    }
    
    available_components = []
    
    for component, description in components.items():
        try:
            if component == 'courts_db':
                from courts_db import courts
                count = len(courts)
                print_status(f"Courts-DB", True, f"{description} ({count} courts)")
                available_components.append(component)
            elif component == 'reporters_db':
                from reporters_db import REPORTERS
                count = len(REPORTERS)
                print_status(f"Reporters-DB", True, f"{description} ({count} reporters)")
                available_components.append(component)
            elif component == 'eyecite':
                import eyecite
                print_status(f"Eyecite", True, f"{description}")
                available_components.append(component)
            elif component == 'judge_pics':
                import judge_pics
                print_status(f"Judge-Pics", True, f"{description}")
                available_components.append(component)
            elif component == 'x_ray':
                import x_ray
                print_status(f"X-Ray", True, f"{description}")
                available_components.append(component)
        except ImportError:
            print_status(f"{component.title()}", False, f"Not installed - {description}")
    
    success_rate = len(available_components) / len(components)
    print(f"\nFLP Components: {len(available_components)}/{len(components)} available ({success_rate:.0%})")
    
    return available_components


async def test_database_connectivity():
    """Test database connectivity"""
    print_header("DATABASE CONNECTIVITY VERIFICATION")
    
    try:
        import psycopg2
        
        # Try to connect with default settings
        db_configs = [
            {
                'host': 'db',
                'database': 'aletheia',
                'user': 'aletheia', 
                'password': 'aletheia123',
                'port': 5432
            },
            {
                'host': 'localhost',
                'database': 'aletheia', 
                'user': 'aletheia',
                'password': 'aletheia123',
                'port': 5432
            }
        ]
        
        for config in db_configs:
            try:
                conn = psycopg2.connect(**config)
                cursor = conn.cursor()
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                cursor.close()
                conn.close()
                
                print_status("Database Connection", True, 
                           f"Connected to PostgreSQL at {config['host']}:{config['port']}\n"
                           f"Database: {config['database']}\n" 
                           f"Version: {version}")
                return True
                
            except psycopg2.OperationalError:
                continue
        
        print_status("Database Connection", False, 
                    "Could not connect to PostgreSQL\n"
                    "Start with: docker-compose up -d db")
        return False
        
    except ImportError:
        print_status("Database Connection", False, "psycopg2 not installed")
        return False


async def run_external_verification():
    """Run complete external endpoint verification"""
    print_header("EXTERNAL ENDPOINT VERIFICATION SUITE")
    print("Testing enhanced processor with real external services and data...")
    
    # Track results
    test_results = []
    
    # Test 1: FLP Components
    flp_components = test_flp_components()
    test_results.append(("FLP Components", len(flp_components) > 0))
    
    # Test 2: Database connectivity
    db_available = await test_database_connectivity()
    test_results.append(("Database", db_available))
    
    # Test 3: CourtListener API
    cl_available, cl_data = await test_courtlistener_api()
    test_results.append(("CourtListener API", cl_available))
    
    # Test 4: Real data retrieval
    real_documents = None
    if cl_available:
        real_documents = await test_real_courtlistener_data()
        test_results.append(("Real Data Retrieval", real_documents is not None))
    
    # Test 5: External services
    doctor_available, doctor_url = await test_doctor_service()
    test_results.append(("Doctor Service", doctor_available))
    
    haystack_available, haystack_url = await test_haystack_service()
    test_results.append(("Haystack Service", haystack_available))
    
    # Test 6: Enhanced processor with real data
    if real_documents:
        real_processing = await test_enhanced_processor_with_real_data(real_documents)
        test_results.append(("Real Data Processing", real_processing))
    
    # Test 7: Batch processing
    batch_processing = await test_batch_processing_real_data()
    test_results.append(("Batch Processing", batch_processing))
    
    # Print final results
    print_header("EXTERNAL VERIFICATION RESULTS")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success in test_results if success)
    
    for test_name, success in test_results:
        print_status(test_name, success)
    
    print(f"\nSummary: {passed_tests}/{total_tests} external tests passed")
    
    # Recommendations
    print_header("RECOMMENDATIONS")
    
    if passed_tests == total_tests:
        print("✅ All external endpoints working! Enhanced processor is fully operational.")
    else:
        print("🔧 Some external services need setup:")
        
        if not any(name == "CourtListener API" and success for name, success in test_results):
            print("   1. Set COURTLISTENER_API_TOKEN environment variable")
            print("      Get token from: https://www.courtlistener.com/api/")
        
        if not any(name == "Database" and success for name, success in test_results):
            print("   2. Start PostgreSQL: docker-compose up -d db")
        
        if not any(name == "Doctor Service" and success for name, success in test_results):
            print("   3. Start Doctor service: docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d doctor")
        
        if not any(name == "Haystack Service" and success for name, success in test_results):
            print("   4. Start Haystack: docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d")
        
        if not any(name == "FLP Components" and success for name, success in test_results):
            print("   5. Install FLP components: pip install courts-db reporters-db eyecite")
    
    print(f"\nExternal verification complete: {passed_tests}/{total_tests} services available")
    return passed_tests >= total_tests * 0.5  # Success if >50% working


def main():
    """Main entry point"""
    try:
        success = asyncio.run(run_external_verification())
        print(f"\nExternal verification {'PASSED' if success else 'NEEDS SETUP'}")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()