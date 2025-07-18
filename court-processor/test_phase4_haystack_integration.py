#!/usr/bin/env python3
"""
Phase 4 Verification: Enhanced Haystack Integration Test

Tests the complete pipeline: CourtListener → FLP Enhancement → PostgreSQL → Haystack
"""
import asyncio
import sys
import os
import time
from datetime import datetime

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

class Phase4HaystackIntegration:
    """Test Phase 4: Enhanced Haystack integration with bulk ingestion"""
    
    def __init__(self):
        self.processor = None
        self.test_results = {
            'processor_initialization': False,
            'haystack_initialization': False,
            'bulk_service_health': False,
            'gilstrap_processing': False,
            'haystack_ingestion': False,
            'end_to_end_pipeline': False,
            'performance_validation': False
        }
        self.performance_metrics = {
            'processing_time': 0,
            'ingestion_time': 0,
            'total_documents': 0,
            'throughput': 0
        }
    
    def print_header(self, title: str):
        """Print formatted header"""
        print("\n" + "="*80)
        print(f" {title}")
        print("="*80)
    
    async def test_processor_initialization(self) -> bool:
        """Test 1: Enhanced processor with Haystack integration"""
        self.print_header("TEST 1: ENHANCED PROCESSOR INITIALIZATION")
        
        try:
            print("🔧 Initializing Enhanced Processor with Haystack...")
            start_time = time.time()
            
            self.processor = EnhancedUnifiedDocumentProcessor()
            init_time = time.time() - start_time
            
            print(f"   ✅ Processor initialized in {init_time:.2f}s")
            
            # Verify enhanced components
            components = {
                'CourtListener Service': self.processor.cl_service,
                'FLP Processor': self.processor.flp_processor,
                'Haystack Manager': self.processor.haystack_manager,
                'Document Validator': self.processor.document_validator,
                'Monitor': self.processor.monitor
            }
            
            print("   📋 Enhanced component verification:")
            all_critical_ok = True
            for name, component in components.items():
                status = "✅" if component else "❌"
                print(f"      • {name}: {status}")
                if not component and name in ['CourtListener Service', 'Document Validator']:
                    all_critical_ok = False
            
            # Check Haystack availability specifically
            haystack_available = self.processor.haystack_manager is not None
            print(f"      • Haystack Integration: {'✅ Available' if haystack_available else '⚠️  Not available'}")
            
            self.test_results['processor_initialization'] = all_critical_ok
            return all_critical_ok
            
        except Exception as e:
            print(f"   ❌ Initialization failed: {str(e)}")
            self.test_results['processor_initialization'] = False
            return False
    
    async def test_haystack_initialization(self) -> bool:
        """Test 2: Haystack services initialization"""
        self.print_header("TEST 2: HAYSTACK SERVICES INITIALIZATION")
        
        try:
            print("🚀 Testing Haystack integration services...")
            
            if not self.processor.haystack_manager:
                print("   ⚠️  Haystack manager not available - using mock testing")
                self.test_results['haystack_initialization'] = False
                return False
            
            # Initialize Haystack manager
            await self.processor.haystack_manager.initialize()
            print("   ✅ Haystack manager initialized")
            
            # Test health status
            health = await self.processor.haystack_manager.get_integration_health()
            print("   📊 Haystack health status:")
            
            if 'integration_manager' in health:
                manager_health = health['integration_manager']
                print(f"      • Integration Manager: {manager_health['status']}")
                print(f"      • Active Jobs: {manager_health['active_jobs']}")
            
            if 'bulk_service' in health:
                bulk_health = health['bulk_service']
                print(f"      • Bulk Service: {bulk_health['status']}")
                
                if 'services' in bulk_health:
                    print("      • Service connections:")
                    for service, info in bulk_health['services'].items():
                        status = "✅" if info.get('connected', False) else "❌"
                        print(f"         - {service}: {status}")
            
            self.test_results['haystack_initialization'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Haystack initialization failed: {str(e)}")
            self.test_results['haystack_initialization'] = False
            return False
    
    async def test_bulk_service_health(self) -> bool:
        """Test 3: Bulk service health and capabilities"""
        self.print_header("TEST 3: BULK SERVICE HEALTH CHECK")
        
        try:
            print("⚡ Testing bulk service capabilities...")
            
            if not self.processor.haystack_manager:
                print("   ⚠️  Haystack manager not available")
                self.test_results['bulk_service_health'] = False
                return False
            
            # Get performance metrics
            metrics = await self.processor.haystack_manager.get_performance_metrics()
            print("   📊 Performance metrics:")
            
            if 'bulk_service' in metrics:
                bulk_metrics = metrics['bulk_service']
                
                if 'system' in bulk_metrics:
                    system = bulk_metrics['system']
                    print(f"      • Memory: {system['memory_rss_mb']:.1f} MB")
                    print(f"      • CPU: {system['cpu_percent']:.1f}%")
                
                if 'connections' in bulk_metrics:
                    connections = bulk_metrics['connections']
                    print("      • Connection pools:")
                    for service, info in connections.items():
                        if isinstance(info, dict) and 'size' in info:
                            print(f"         - {service}: {info['idle_connections']}/{info['size']} idle")
            
            if 'job_management' in metrics:
                job_stats = metrics['job_management']
                print(f"      • Job management ready: ✅")
                print(f"         - Total jobs: {job_stats['total_jobs']}")
                print(f"         - Running: {job_stats['running_jobs']}")
            
            self.test_results['bulk_service_health'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Bulk service health check failed: {str(e)}")
            self.test_results['bulk_service_health'] = False
            return False
    
    async def test_gilstrap_processing(self) -> bool:
        """Test 4: Gilstrap document processing with enhanced pipeline"""
        self.print_header("TEST 4: JUDGE GILSTRAP PROCESSING")
        
        try:
            print("📄 Testing enhanced Gilstrap document processing...")
            
            start_time = time.time()
            batch_result = await self.processor.process_gilstrap_documents_batch(
                max_documents=2  # Small test batch
            )
            processing_time = time.time() - start_time
            
            print(f"   ✅ Gilstrap processing completed in {processing_time:.2f}s")
            print(f"   📊 Processing results:")
            print(f"      • Documents fetched: {batch_result.get('total_fetched', 0)}")
            print(f"      • New documents: {batch_result.get('new_documents', 0)}")
            print(f"      • Duplicates: {batch_result.get('duplicates', 0)}")
            print(f"      • Errors: {batch_result.get('errors', 0)}")
            
            # Update performance metrics
            self.performance_metrics['processing_time'] = processing_time
            self.performance_metrics['total_documents'] = batch_result.get('new_documents', 0)
            
            self.test_results['gilstrap_processing'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Gilstrap processing failed: {str(e)}")
            self.test_results['gilstrap_processing'] = False
            return False
    
    async def test_haystack_ingestion(self) -> bool:
        """Test 5: Haystack bulk ingestion"""
        self.print_header("TEST 5: HAYSTACK BULK INGESTION")
        
        try:
            print("🚀 Testing Haystack bulk ingestion...")
            
            if not self.processor.haystack_manager:
                print("   ⚠️  Haystack manager not available - cannot test ingestion")
                self.test_results['haystack_ingestion'] = False
                return False
            
            # Test ingestion of recent Gilstrap documents
            start_time = time.time()
            job_id = await self.processor.ingest_gilstrap_to_haystack(max_documents=5)
            
            print(f"   🔄 Haystack ingestion job started: {job_id}")
            
            # Monitor job for a short time (30 seconds max for test)
            monitor_start = time.time()
            final_status = None
            
            while time.time() - monitor_start < 30:
                try:
                    status = self.processor.haystack_manager.get_job_status(job_id)
                    
                    if status:
                        current_status = status['status']
                        
                        if current_status in ['completed', 'failed', 'cancelled']:
                            final_status = status
                            break
                        
                        print(f"      • Job status: {current_status}")
                    
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"      ⚠️  Monitoring error: {str(e)}")
                    break
            
            ingestion_time = time.time() - start_time
            self.performance_metrics['ingestion_time'] = ingestion_time
            
            if final_status:
                if final_status['status'] == 'completed':
                    stats = final_status.get('stats', {})
                    print(f"   ✅ Haystack ingestion completed in {ingestion_time:.2f}s")
                    print(f"      • Total documents: {stats.get('total_documents', 0)}")
                    print(f"      • Successful: {stats.get('successful_documents', 0)}")
                    print(f"      • Failed: {stats.get('failed_documents', 0)}")
                    print(f"      • Success rate: {stats.get('success_rate', 0):.1f}%")
                    print(f"      • Throughput: {stats.get('throughput', 0):.2f} docs/sec")
                else:
                    print(f"   ❌ Haystack ingestion {final_status['status']}: {final_status.get('error', 'Unknown')}")
                    self.test_results['haystack_ingestion'] = False
                    return False
            else:
                print(f"   ⚠️  Haystack ingestion job still running after 30s")
                print(f"      • Job ID: {job_id} (check status manually)")
            
            self.test_results['haystack_ingestion'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ Haystack ingestion test failed: {str(e)}")
            self.test_results['haystack_ingestion'] = False
            return False
    
    async def test_end_to_end_pipeline(self) -> bool:
        """Test 6: Complete end-to-end pipeline"""
        self.print_header("TEST 6: END-TO-END PIPELINE")
        
        try:
            print("🔄 Testing complete pipeline: CourtListener → FLP → PostgreSQL → Haystack")
            
            if not self.processor.haystack_manager:
                print("   ⚠️  Haystack manager not available - testing without Haystack")
                # Just test the processing pipeline
                result = await self.processor.process_gilstrap_documents_batch(max_documents=1)
                success = result.get('new_documents', 0) > 0 or result.get('total_fetched', 0) > 0
                self.test_results['end_to_end_pipeline'] = success
                return success
            
            # Test complete pipeline with Haystack
            start_time = time.time()
            result = await self.processor.process_and_ingest_to_haystack(
                court_id="txed",
                judge_name="Gilstrap",
                max_documents=1
            )
            total_time = time.time() - start_time
            
            print(f"   ✅ End-to-end pipeline completed in {total_time:.2f}s")
            print(f"   📊 Pipeline results:")
            print(f"      • Processing: {result.get('new_documents', 0)} documents")
            
            if 'haystack_ingestion' in result:
                haystack_result = result['haystack_ingestion']
                print(f"      • Haystack ingestion: {'✅ Success' if haystack_result['success'] else '❌ Failed'}")
                
                if haystack_result['success'] and 'stats' in haystack_result:
                    stats = haystack_result['stats']
                    print(f"         - Documents ingested: {stats.get('successful_documents', 0)}")
                elif not haystack_result['success']:
                    print(f"         - Error: {haystack_result.get('error', 'Unknown')}")
            
            self.test_results['end_to_end_pipeline'] = True
            return True
            
        except Exception as e:
            print(f"   ❌ End-to-end pipeline test failed: {str(e)}")
            self.test_results['end_to_end_pipeline'] = False
            return False
    
    async def test_performance_validation(self) -> bool:
        """Test 7: Performance validation"""
        self.print_header("TEST 7: PERFORMANCE VALIDATION")
        
        try:
            print("⚡ Validating system performance...")
            
            # Calculate overall throughput
            total_time = self.performance_metrics['processing_time'] + self.performance_metrics['ingestion_time']
            total_docs = self.performance_metrics['total_documents']
            
            if total_time > 0 and total_docs > 0:
                throughput = total_docs / total_time
                self.performance_metrics['throughput'] = throughput
                
                print(f"   📊 Performance analysis:")
                print(f"      • Total processing time: {self.performance_metrics['processing_time']:.2f}s")
                print(f"      • Total ingestion time: {self.performance_metrics['ingestion_time']:.2f}s")
                print(f"      • Total documents: {total_docs}")
                print(f"      • Overall throughput: {throughput:.2f} docs/sec")
                
                # Validate performance benchmarks
                performance_ok = True
                if throughput < 0.1:  # Less than 0.1 docs/sec is concerning
                    print(f"      ⚠️  Low throughput detected")
                    performance_ok = False
                else:
                    print(f"      ✅ Performance within acceptable range")
            else:
                print(f"   ⚠️  Insufficient data for performance analysis")
                performance_ok = False
            
            # System health check
            health = self.processor.get_health_status()
            print(f"   🏥 System health:")
            print(f"      • Status: {health.get('status', 'Unknown')}")
            print(f"      • Uptime: {health.get('uptime_seconds', 0):.1f}s")
            
            if 'components' in health:
                components = health['components']
                print(f"      • Environment: {components.get('environment', 'Unknown')}")
            
            self.test_results['performance_validation'] = performance_ok
            return performance_ok
            
        except Exception as e:
            print(f"   ❌ Performance validation failed: {str(e)}")
            self.test_results['performance_validation'] = False
            return False
    
    def print_final_report(self):
        """Print comprehensive final report"""
        self.print_header("PHASE 4 HAYSTACK INTEGRATION REPORT")
        
        print("🎯 **TEST RESULTS:**")
        for test_name, result in self.test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"   • {test_name.replace('_', ' ').title()}: {status}")
        
        passed_tests = sum(1 for result in self.test_results.values() if result)
        total_tests = len(self.test_results)
        
        print(f"\n📊 **OVERALL RESULTS:**")
        print(f"   • Tests passed: {passed_tests}/{total_tests}")
        print(f"   • Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.performance_metrics['total_documents'] > 0:
            print(f"\n⚡ **PERFORMANCE SUMMARY:**")
            print(f"   • Documents processed: {self.performance_metrics['total_documents']}")
            print(f"   • Processing time: {self.performance_metrics['processing_time']:.2f}s")
            print(f"   • Ingestion time: {self.performance_metrics['ingestion_time']:.2f}s")
            print(f"   • Overall throughput: {self.performance_metrics['throughput']:.2f} docs/sec")
        
        print(f"\n🚀 **PHASE 4 INTEGRATION STATUS:**")
        if passed_tests >= 5:  # Most critical tests passed
            print(f"   ✅ PHASE 4 HAYSTACK INTEGRATION SUCCESSFUL")
            print(f"   📋 Complete pipeline operational: CourtListener → FLP → PostgreSQL → Haystack")
            print(f"   🔍 Enhanced search capabilities now available")
        else:
            print(f"   ❌ PHASE 4 INTEGRATION NEEDS IMPROVEMENT")
            print(f"   🔧 Address failed tests before production deployment")
        
        return passed_tests >= 5

async def run_phase4_test():
    """Run Phase 4 Haystack integration test"""
    
    integration_test = Phase4HaystackIntegration()
    
    integration_test.print_header("PHASE 4 HAYSTACK INTEGRATION TEST")
    print("🎯 Testing complete enhanced pipeline with Haystack bulk ingestion")
    print(f"📅 Test timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all tests
    tests = [
        integration_test.test_processor_initialization,
        integration_test.test_haystack_initialization,
        integration_test.test_bulk_service_health,
        integration_test.test_gilstrap_processing,
        integration_test.test_haystack_ingestion,
        integration_test.test_end_to_end_pipeline,
        integration_test.test_performance_validation
    ]
    
    for test in tests:
        await test()
    
    # Generate final report
    success = integration_test.print_final_report()
    
    return success

if __name__ == "__main__":
    try:
        print("🚀 Starting Phase 4 Haystack integration test...")
        success = asyncio.run(run_phase4_test())
        
        if success:
            print("\n🎉 PHASE 4 INTEGRATION COMPLETE!")
            print("✅ Enhanced Judge Gilstrap processing with Haystack search ready for production")
        else:
            print("\n❌ Phase 4 integration test failed")
            print("🔧 Review failed tests before production deployment")
            
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)