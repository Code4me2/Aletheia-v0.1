#!/usr/bin/env python3
"""
Validation script for Enhanced Unified Document Processor

This script validates that the enhanced processor works end-to-end
with basic functionality testing.
"""
import asyncio
import sys
import os
import json
import time
from pathlib import Path

# Add enhanced module to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'enhanced'))

try:
    from enhanced.enhanced_unified_processor import EnhancedUnifiedDocumentProcessor
    from enhanced.utils.validation import DocumentValidator
    from enhanced.config import get_settings
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print("Make sure all dependencies are installed and the enhanced module is properly structured.")
    sys.exit(1)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def print_status(test_name: str, success: bool, details: str = ""):
    """Print test status"""
    status = "✅" if success else "❌"
    print(f"{status} {test_name}")
    if details:
        print(f"   {details}")


async def test_processor_initialization():
    """Test that the processor can be initialized"""
    print_header("PROCESSOR INITIALIZATION TEST")
    
    try:
        processor = EnhancedUnifiedDocumentProcessor()
        print_status("Processor initialization", True, "Enhanced processor created successfully")
        
        # Test configuration
        settings = processor.settings
        print_status("Configuration loading", True, f"Environment: {settings.environment}")
        
        # Test health status
        health = processor.get_health_status()
        print_status("Health status", True, f"Status: {health.get('status', 'unknown')}")
        
        return processor
        
    except Exception as e:
        print_status("Processor initialization", False, f"Error: {str(e)}")
        return None


async def test_single_document_processing(processor):
    """Test single document processing"""
    print_header("SINGLE DOCUMENT PROCESSING TEST")
    
    # Create test document
    test_document = {
        'id': 12345,
        'court_id': 'cafc',
        'case_name': 'Enhanced Processor Test v. Validation Suite',
        'docket_number': '24-1000',
        'date_filed': '2024-01-15',
        'author_str': 'Test Judge',
        'plain_text': 'This is a test document for validating the enhanced processor. It cites Smith v. Jones, 123 F.3d 456 (Fed. Cir. 2020).',
        'type': 'opinion'
    }
    
    try:
        start_time = time.time()
        result = await processor.process_single_document(test_document)
        processing_time = time.time() - start_time
        
        if 'saved_id' in result:
            print_status("Document processing", True, f"Processed in {processing_time:.2f}s, saved with ID: {result['saved_id']}")
            return True
        elif 'error' in result:
            print_status("Document processing", False, f"Error: {result['error']}")
            return False
        else:
            print_status("Document processing", False, "Unexpected result format")
            return False
            
    except Exception as e:
        print_status("Document processing", False, f"Exception: {str(e)}")
        return False


async def test_batch_processing(processor):
    """Test batch processing"""
    print_header("BATCH PROCESSING TEST")
    
    try:
        start_time = time.time()
        result = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=5
        )
        processing_time = time.time() - start_time
        
        # Validate result structure
        required_fields = ['total_fetched', 'new_documents', 'duplicates', 'errors']
        missing_fields = [field for field in required_fields if field not in result]
        
        if missing_fields:
            print_status("Batch processing", False, f"Missing fields: {missing_fields}")
            return False
        
        print_status("Batch processing", True, f"Processed {result['total_fetched']} documents in {processing_time:.2f}s")
        print(f"   New: {result['new_documents']}, Duplicates: {result['duplicates']}, Errors: {result['errors']}")
        
        return True
        
    except Exception as e:
        print_status("Batch processing", False, f"Exception: {str(e)}")
        return False


def test_validation_system():
    """Test validation system"""
    print_header("VALIDATION SYSTEM TEST")
    
    try:
        validator = DocumentValidator()
        
        # Test valid document
        valid_doc = {
            'id': 123,
            'court_id': 'cafc',
            'case_name': 'Valid Test Case'
        }
        
        result = validator.validate_courtlistener_document(valid_doc)
        print_status("Valid document validation", result.is_valid, 
                    f"Errors: {len(result.errors)}, Warnings: {len(result.warnings)}")
        
        # Test invalid document
        invalid_doc = {
            'case_name': 'Invalid Test Case'  # Missing required fields
        }
        
        result = validator.validate_courtlistener_document(invalid_doc)
        print_status("Invalid document detection", not result.is_valid, 
                    f"Errors detected: {len(result.errors)}")
        
        return True
        
    except Exception as e:
        print_status("Validation system", False, f"Exception: {str(e)}")
        return False


async def test_deduplication_system(processor):
    """Test deduplication system"""
    print_header("DEDUPLICATION SYSTEM TEST")
    
    try:
        # Process the same batch twice to test deduplication
        print("Processing first batch...")
        result1 = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=3
        )
        
        print("Processing second batch (same parameters)...")
        result2 = await processor.process_courtlistener_batch(
            court_id="cafc",
            max_documents=3
        )
        
        # Second batch should have duplicates
        has_duplicates = result2['duplicates'] > 0
        print_status("Deduplication detection", has_duplicates, 
                    f"First batch: {result1['new_documents']} new, Second batch: {result2['duplicates']} duplicates")
        
        # Check cache hit rate
        cache_hit_rate = processor.dedup_manager.cache_hit_rate
        print_status("Deduplication cache", True, f"Cache hit rate: {cache_hit_rate:.2%}")
        
        return True
        
    except Exception as e:
        print_status("Deduplication system", False, f"Exception: {str(e)}")
        return False


def test_monitoring_system(processor):
    """Test monitoring and metrics system"""
    print_header("MONITORING SYSTEM TEST")
    
    try:
        # Get metrics
        metrics = processor.get_processing_metrics()
        print_status("Metrics collection", True, f"Collected {len(metrics)} metric categories")
        
        # Get health status
        health = processor.get_health_status()
        print_status("Health monitoring", True, f"Health status: {health.get('status', 'unknown')}")
        
        # Print some key metrics if available
        if 'processing' in metrics:
            processing = metrics['processing']
            print(f"   Documents processed: {processing.get('documents_processed', 0)}")
            print(f"   Success rate: {processing.get('success_rate', 0):.2%}")
        
        return True
        
    except Exception as e:
        print_status("Monitoring system", False, f"Exception: {str(e)}")
        return False


async def run_validation():
    """Run complete validation suite"""
    print_header("ENHANCED UNIFIED DOCUMENT PROCESSOR VALIDATION")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    
    # Track test results
    test_results = []
    
    # Test 1: Processor initialization
    processor = await test_processor_initialization()
    test_results.append(("Initialization", processor is not None))
    
    if processor is None:
        print_header("VALIDATION FAILED")
        print("❌ Cannot proceed without successful processor initialization")
        return False
    
    # Test 2: Validation system
    validation_success = test_validation_system()
    test_results.append(("Validation System", validation_success))
    
    # Test 3: Single document processing
    single_doc_success = await test_single_document_processing(processor)
    test_results.append(("Single Document Processing", single_doc_success))
    
    # Test 4: Batch processing
    batch_success = await test_batch_processing(processor)
    test_results.append(("Batch Processing", batch_success))
    
    # Test 5: Deduplication
    dedup_success = await test_deduplication_system(processor)
    test_results.append(("Deduplication", dedup_success))
    
    # Test 6: Monitoring
    monitoring_success = test_monitoring_system(processor)
    test_results.append(("Monitoring", monitoring_success))
    
    # Print final results
    print_header("VALIDATION RESULTS")
    
    total_tests = len(test_results)
    passed_tests = sum(1 for _, success in test_results if success)
    
    for test_name, success in test_results:
        print_status(test_name, success)
    
    print(f"\nSummary: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print_header("✅ VALIDATION SUCCESSFUL")
        print("The Enhanced Unified Document Processor is working correctly!")
        print("\nNext steps:")
        print("1. Run the full test suite: pytest tests/enhanced/ -v")
        print("2. Begin Phase 2 implementation (Service Integration Enhancement)")
        print("3. Consider deploying to development environment")
        return True
    else:
        print_header("❌ VALIDATION FAILED")
        print(f"Only {passed_tests}/{total_tests} tests passed.")
        print("Please review the errors above and fix issues before proceeding.")
        return False


def main():
    """Main entry point"""
    try:
        success = asyncio.run(run_validation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nValidation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during validation: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()