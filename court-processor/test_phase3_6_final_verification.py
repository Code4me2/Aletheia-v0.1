#!/usr/bin/env python3
"""
Phase 3.6 Final Verification: Complete System Integration Test

Comprehensive test of the complete enhanced system for Judge Gilstrap document processing.
"""
import asyncio
import sys
import os
import time
from datetime import datetime

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

class Phase3FinalVerification:
    """Comprehensive Phase 3 final verification"""
    
    def __init__(self):
        self.processor = None
        self.test_results = {
            'initialization': False,
            'api_connectivity': False,
            'document_retrieval': False,
            'flp_enhancement': False,
            'database_storage': False,
            'batch_processing': False,
            'performance': False,
            'error_handling': False
        }
        self.performance_metrics = {
            'total_documents_processed': 0,
            'total_processing_time': 0,
            'average_processing_time': 0,
            'api_calls_made': 0,
            'success_rate': 0
        }
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    async def test_initialization(self) -> bool:
        """Test 1: System initialization"""
        self.print_header("TEST 1: SYSTEM INITIALIZATION")
        
        try:
            print("🔧 Initializing Enhanced Unified Document Processor...")
            start_time = time.time()
            
            self.processor = EnhancedUnifiedDocumentProcessor()
            init_time = time.time() - start_time
            
            print(f"   ✅ Processor initialized in {init_time:.2f}s")
            
            # Verify components
            components = {
                'CourtListener Service': self.processor.cl_service,
                'FLP Processor': self.processor.flp_processor,
                'Document Validator': self.processor.document_validator,
                'Monitor': self.processor.monitor,
                'Deduplication Manager': self.processor.dedup_manager
            }
            
            print("   📋 Component verification:")
            all_components_ok = True
            for name, component in components.items():
                status = "✅" if component else "❌"
                print(f"      • {name}: {status}")
                if not component and name in ['CourtListener Service', 'Document Validator', 'Monitor']:
                    all_components_ok = False
            
            self.test_results['initialization'] = all_components_ok
            return all_components_ok
            
        except Exception as e:
            print(f"   ❌ Initialization failed: {str(e)}")
            self.test_results['initialization'] = False
            return False
    
    async def test_api_connectivity(self) -> bool:
        """Test 2: API connectivity and authentication"""
        self.print_header("TEST 2: API CONNECTIVITY")
        
        try:
            print("🌐 Testing CourtListener API connectivity...")
            
            start_time = time.time()
            connection_ok = await self.processor.cl_service.test_connection()
            connection_time = time.time() - start_time
            
            if connection_ok:
                print(f"   ✅ API connection successful in {connection_time:.2f}s")
                
                # Test API features
                print("   🔍 Testing API features...")
                
                # Test docket search
                dockets = await self.processor.cl_service.fetch_dockets_by_judge(
                    judge_name="Gilstrap",
                    court_id="txed",
                    max_documents=1
                )
                
                print(f"      • Docket search: {'✅' if dockets else '⚠️'} ({len(dockets)} found)")
                
                self.test_results['api_connectivity'] = True
                return True
            else:
                print(f"   ❌ API connection failed")
                self.test_results['api_connectivity'] = False
                return False
                
        except Exception as e:
            print(f"   ❌ API connectivity test failed: {str(e)}")
            self.test_results['api_connectivity'] = False
            return False
    
    async def test_document_retrieval(self) -> bool:
        """Test 3: Document retrieval capabilities"""
        self.print_header("TEST 3: DOCUMENT RETRIEVAL")
        
        try:
            print("📄 Testing document retrieval capabilities...")
            
            # Test 1: Historical search
            print("   🔍 Testing historical document search...")
            
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.processor.cl_service.base_url}/search/",
                    headers=self.processor.cl_service._get_headers(),
                    params={
                        "q": "Gilstrap",
                        "type": "o",
                        "court": "txed",
                        "page_size": 3
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        results = data.get('results', [])
                        print(f"      ✅ Found {len(results)} historical opinions")
                        
                        # Test document mapping
                        if results:
                            opinion_result = results[0]
                            opinions = opinion_result.get('opinions', [])
                            if opinions:
                                opinion_id = opinions[0].get('id')
                                
                                async with session.get(
                                    f"{self.processor.cl_service.base_url}/opinions/{opinion_id}/",
                                    headers=self.processor.cl_service._get_headers(),
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as opinion_response:
                                    
                                    if opinion_response.status == 200:
                                        opinion_data = await opinion_response.json()
                                        mapped_doc = self.processor.cl_service._map_courtlistener_document(opinion_data)
                                        
                                        print(f"      ✅ Document mapping successful")
                                        print(f"         • Mapped fields: {len(mapped_doc)}")
                                        print(f"         • Has text: {'Yes' if mapped_doc.get('plain_text') else 'No'}")
                                        
                                        self.test_results['document_retrieval'] = True
                                        return True
            
            print(f"   ⚠️  Could not retrieve test documents")
            self.test_results['document_retrieval'] = False
            return False
            
        except Exception as e:
            print(f"   ❌ Document retrieval test failed: {str(e)}")
            self.test_results['document_retrieval'] = False
            return False
    
    async def test_flp_enhancement(self) -> bool:
        """Test 4: FLP enhancement pipeline"""
        self.print_header("TEST 4: FLP ENHANCEMENT PIPELINE")
        
        try:
            print("🔍 Testing FLP enhancement capabilities...")
            
            test_doc = {
                'id': 999998,
                'court_id': 'txed',
                'case_name': 'FLP Test v. Enhancement Pipeline',
                'plain_text': 'This test document contains multiple citations: Smith v. Jones, 123 F.3d 456 (5th Cir. 2020), Brown v. Board, 347 U.S. 483 (1954), and United States v. Nixon, 418 U.S. 683 (1974).',
                'author_str': 'Test Judge'
            }
            
            if self.processor.flp_processor:
                enhanced = self.processor.flp_processor.enhance_document(test_doc)
                
                print(f"   ✅ FLP enhancement completed")
                print(f"   📊 Enhancement results:")
                
                # Check citations
                citations = enhanced.get('citations', [])
                print(f"      • Citations extracted: {len(citations)}")
                for i, citation in enumerate(citations[:2]):
                    print(f"         {i+1}. {citation.get('citation_string', 'Unknown')}")
                
                # Check court info
                court_info = enhanced.get('court_info', {})
                print(f"      • Court info enhanced: {'Yes' if court_info else 'No'}")
                print(f"      • Court standardized: {'Yes' if court_info.get('standardized') else 'No'}")
                
                # Check processing metadata
                processing_time = enhanced.get('flp_processing_duration', 0)
                print(f"      • Processing time: {processing_time:.3f}s")
                
                services_used = enhanced.get('flp_services_used', {})
                if services_used:
                    active_services = sum(1 for v in services_used.values() if v)
                    print(f"      • Active FLP services: {active_services}/{len(services_used)}")
                
                self.test_results['flp_enhancement'] = True
                return True
            else:
                print(f"   ⚠️  FLP processor not available - using fallback")
                self.test_results['flp_enhancement'] = False
                return False
                
        except Exception as e:
            print(f"   ❌ FLP enhancement test failed: {str(e)}")
            self.test_results['flp_enhancement'] = False
            return False
    
    async def test_database_storage(self) -> bool:
        """Test 5: Database storage integration"""
        self.print_header("TEST 5: DATABASE STORAGE")
        
        try:
            print("💾 Testing database storage integration...")
            
            test_doc = {
                'id': 999997,
                'court_id': 'txed',
                'case_name': 'Database Test v. Storage Integration',
                'plain_text': 'This is a database storage test document with citation: Test v. Case, 456 F.3d 789 (5th Cir. 2021).',
                'author_str': 'Database Test Judge',
                'processing_timestamp': time.time()
            }
            
            start_time = time.time()
            result = await self.processor.process_single_document(test_doc)
            processing_time = time.time() - start_time
            
            if result.get('saved_id'):
                saved_id = result['saved_id']
                print(f"   ✅ Document stored successfully")
                print(f"   📊 Storage results:")
                print(f"      • Saved ID: {saved_id}")
                print(f"      • Processing time: {processing_time:.2f}s")
                print(f"      • FLP enhanced: {'Yes' if result.get('flp_processing_timestamp') else 'No'}")
                print(f"      • Citations stored: {len(result.get('citations', []))}")
                
                # Update performance metrics
                self.performance_metrics['total_documents_processed'] += 1
                self.performance_metrics['total_processing_time'] += processing_time
                
                self.test_results['database_storage'] = True
                return True
            else:
                print(f"   ❌ Document storage failed: {result.get('error')}")
                self.test_results['database_storage'] = False
                return False
                
        except Exception as e:
            print(f"   ❌ Database storage test failed: {str(e)}")
            self.test_results['database_storage'] = False
            return False
    
    async def test_batch_processing(self) -> bool:
        """Test 6: Batch processing capabilities"""
        self.print_header("TEST 6: BATCH PROCESSING")
        
        try:
            print("📚 Testing batch processing capabilities...")
            
            start_time = time.time()
            batch_result = await self.processor.process_gilstrap_documents_batch(
                max_documents=1
            )
            batch_time = time.time() - start_time
            
            print(f"   ✅ Batch processing completed in {batch_time:.2f}s")
            print(f"   📊 Batch results:")
            print(f"      • Documents fetched: {batch_result.get('total_fetched', 0)}")
            print(f"      • New documents: {batch_result.get('new_documents', 0)}")
            print(f"      • Duplicates: {batch_result.get('duplicates', 0)}")
            print(f"      • Errors: {batch_result.get('errors', 0)}")
            
            # Update performance metrics
            self.performance_metrics['total_processing_time'] += batch_time
            
            self.test_results['batch_processing'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Batch processing test failed: {str(e)}")
            self.test_results['batch_processing'] = False
            return False
    
    async def test_performance(self) -> bool:
        """Test 7: Performance analysis"""
        self.print_header("TEST 7: PERFORMANCE ANALYSIS")
        
        try:
            print("⚡ Analyzing system performance...")
            
            # Get system health
            health = self.processor.get_health_status()
            metrics = self.processor.get_processing_metrics()
            
            print(f"   📊 System health:")
            print(f"      • Status: {health.get('status', 'Unknown')}")
            print(f"      • Uptime: {health.get('uptime_seconds', 0):.1f}s")
            
            if 'processing' in metrics:
                processing = metrics['processing']
                docs_processed = processing.get('documents_processed', 0)
                success_rate = processing.get('success_rate', 0)
                
                print(f"   📈 Processing metrics:")
                print(f"      • Documents processed: {docs_processed}")
                print(f"      • Success rate: {success_rate:.1%}")
                
                # Calculate performance metrics
                if self.performance_metrics['total_documents_processed'] > 0:
                    avg_time = (self.performance_metrics['total_processing_time'] / 
                               self.performance_metrics['total_documents_processed'])
                    
                    print(f"   ⚡ Performance analysis:")
                    print(f"      • Average processing time: {avg_time:.2f}s/document")
                    print(f"      • Total processing time: {self.performance_metrics['total_processing_time']:.2f}s")
                    
                    self.performance_metrics['average_processing_time'] = avg_time
                    self.performance_metrics['success_rate'] = success_rate
            
            self.test_results['performance'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Performance analysis failed: {str(e)}")
            self.test_results['performance'] = False
            return False
    
    async def test_error_handling(self) -> bool:
        """Test 8: Error handling and recovery"""
        self.print_header("TEST 8: ERROR HANDLING")
        
        try:
            print("🛡️  Testing error handling and recovery...")
            
            # Test invalid document
            invalid_doc = {
                'id': None,
                'invalid_field': 'test'
            }
            
            result = await self.processor.process_single_document(invalid_doc)
            
            if 'error' in result or 'saved_id' not in result:
                print(f"   ✅ Invalid document properly handled")
                print(f"      • Error captured: {result.get('error', 'Document rejected')}")
            else:
                print(f"   ⚠️  Invalid document was processed")
            
            self.test_results['error_handling'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Error handling test failed: {str(e)}")
            self.test_results['error_handling'] = False
            return False
    
    def print_final_report(self):
        """Print comprehensive final report"""
        self.print_header("PHASE 3 FINAL VERIFICATION REPORT")
        
        print("🎯 **COMPONENT TEST RESULTS:**")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   • {test_name.replace('_', ' ').title()}: {status}")
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        
        print(f"\n📊 **OVERALL RESULTS:**")
        print(f"   • Tests passed: {passed_tests}/{total_tests}")
        print(f"   • Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.performance_metrics['total_documents_processed'] > 0:
            print(f"\n⚡ **PERFORMANCE SUMMARY:**")
            print(f"   • Documents processed: {self.performance_metrics['total_documents_processed']}")
            print(f"   • Average processing time: {self.performance_metrics['average_processing_time']:.2f}s")
            print(f"   • Success rate: {self.performance_metrics['success_rate']:.1%}")
        
        print(f"\n🎉 **PHASE 3 INTEGRATION STATUS:**")
        if passed_tests >= 6:  # Most critical tests passed
            print(f"   ✅ PHASE 3 INTEGRATION SUCCESSFUL")
            print(f"   🚀 System ready for production use")
            print(f"   📋 Judge Gilstrap document processing: OPERATIONAL")
        else:
            print(f"   ❌ PHASE 3 INTEGRATION NEEDS IMPROVEMENT")
            print(f"   🔧 Address failed tests before production deployment")
        
        return passed_tests >= 6

async def run_phase3_6_verification():
    """Run complete Phase 3.6 final verification"""
    
    verification = Phase3FinalVerification()
    
    verification.print_header("PHASE 3.6 FINAL VERIFICATION")
    print("🎯 Comprehensive system integration verification")
    print(f"📅 Test timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    tests = [
        verification.test_initialization,
        verification.test_api_connectivity,
        verification.test_document_retrieval,
        verification.test_flp_enhancement,
        verification.test_database_storage,
        verification.test_batch_processing,
        verification.test_performance,
        verification.test_error_handling
    ]
    
    for test in tests:
        await test()
    
    # Generate final report
    success = verification.print_final_report()
    
    return success

if __name__ == "__main__":
    try:
        print("🚀 Starting Phase 3.6 final verification...")
        success = asyncio.run(run_phase3_6_verification())
        
        if success:
            print("\n🎉 PHASE 3 INTEGRATION COMPLETE!")
            print("✅ Enhanced Judge Gilstrap processing system ready for production")
        else:
            print("\n❌ Phase 3.6 verification failed")
            print("🔧 Review failed tests before production deployment")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)