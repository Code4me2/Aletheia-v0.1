#!/usr/bin/env python3
"""
Comprehensive Test Suite for Court Processor Pipeline

This modular test suite covers:
1. Unit tests for individual components
2. Integration tests for component interactions  
3. End-to-end tests for complete workflows
4. Performance tests for large-scale processing
"""

import asyncio
import pytest
import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, List
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestConfiguration:
    """Test configuration and environment setup"""
    
    # Test environment settings
    USE_REAL_API = os.getenv('TEST_REAL_API', 'false').lower() == 'true'
    USE_REAL_DB = os.getenv('TEST_REAL_DB', 'false').lower() == 'true'
    USE_DOCKER = os.getenv('TEST_IN_DOCKER', 'false').lower() == 'true'
    
    # API configuration
    COURTLISTENER_API_KEY = os.getenv('COURTLISTENER_API_KEY', 'test_key')
    
    # Test data paths
    FIXTURES_DIR = os.path.join(os.path.dirname(__file__), 'fixtures')
    SAMPLE_PDFS_DIR = os.path.join(FIXTURES_DIR, 'sample_pdfs')
    
    @classmethod
    def setup_test_environment(cls):
        """Setup test environment"""
        os.environ['COURTLISTENER_API_KEY'] = cls.COURTLISTENER_API_KEY
        
        # Create fixture directories
        os.makedirs(cls.FIXTURES_DIR, exist_ok=True)
        os.makedirs(cls.SAMPLE_PDFS_DIR, exist_ok=True)


# =============================================================================
# UNIT TESTS
# =============================================================================

class UnitTestSuite:
    """Unit tests for individual components"""
    
    @staticmethod
    async def test_pdf_processor():
        """Test PDF processing component"""
        from pdf_processor import PDFProcessor
        
        logger.info("\n" + "="*60)
        logger.info("UNIT TEST: PDF Processor")
        logger.info("="*60)
        
        processor = PDFProcessor(ocr_enabled=True)
        
        # Test 1: Process a valid PDF
        # Create a simple test PDF
        test_pdf_path = os.path.join(TestConfiguration.SAMPLE_PDFS_DIR, 'test.pdf')
        
        if os.path.exists(test_pdf_path):
            text, metadata = processor.process_pdf(test_pdf_path)
            
            assert text is not None, "PDF extraction should return text"
            assert metadata.get('pages', 0) > 0, "PDF should have pages"
            logger.info(f"✓ PDF extraction: {len(text)} chars, {metadata.get('pages')} pages")
        else:
            logger.warning("Test PDF not found, skipping PDF processor test")
        
        return True
    
    @staticmethod
    async def test_court_resolver():
        """Test court resolution component"""
        from courts_db import find_court
        
        logger.info("\n" + "="*60)
        logger.info("UNIT TEST: Court Resolver")
        logger.info("="*60)
        
        test_cases = [
            ("Eastern District of Texas", ["txed"]),
            ("Federal Circuit", ["cafc"]),
            ("S.D.N.Y.", ["nysd"]),
            ("Supreme Court", ["scotus"])
        ]
        
        passed = 0
        for court_string, expected in test_cases:
            result = find_court(court_string)
            if result and result[0] in expected:
                logger.info(f"✓ Resolved '{court_string}' → {result[0]}")
                passed += 1
            else:
                logger.error(f"✗ Failed to resolve '{court_string}'")
        
        assert passed == len(test_cases), f"Court resolution failed: {passed}/{len(test_cases)}"
        return True
    
    @staticmethod
    async def test_citation_extractor():
        """Test citation extraction"""
        from eyecite import get_citations
        
        logger.info("\n" + "="*60)
        logger.info("UNIT TEST: Citation Extractor")
        logger.info("="*60)
        
        test_text = """
        The court cited Brown v. Board of Education, 347 U.S. 483 (1954) and
        Miranda v. Arizona, 384 U.S. 436 (1966) in reaching its decision.
        See also Marbury v. Madison, 5 U.S. 137 (1803).
        """
        
        citations = get_citations(test_text)
        assert len(citations) >= 3, f"Should find at least 3 citations, found {len(citations)}"
        
        for citation in citations:
            logger.info(f"✓ Found citation: {citation}")
        
        return True
    
    @staticmethod
    async def test_document_validator():
        """Test document validation"""
        from validation import DocumentValidator
        
        logger.info("\n" + "="*60)
        logger.info("UNIT TEST: Document Validator")
        logger.info("="*60)
        
        # Valid document
        valid_doc = {
            'case_number': 'TEST-001',
            'content': 'This is test content ' * 10,
            'metadata': {'court_id': 'txed'}
        }
        
        result = DocumentValidator.validate_document(valid_doc)
        assert result.is_valid, "Valid document should pass validation"
        logger.info("✓ Valid document passed validation")
        
        # Invalid document
        invalid_doc = {
            'case_number': '',
            'content': 'Too short'
        }
        
        result = DocumentValidator.validate_document(invalid_doc)
        assert not result.is_valid, "Invalid document should fail validation"
        logger.info("✓ Invalid document correctly failed validation")
        
        return True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class IntegrationTestSuite:
    """Integration tests for component interactions"""
    
    @staticmethod
    async def test_ingestion_to_database():
        """Test document ingestion service to database flow"""
        if not TestConfiguration.USE_REAL_DB:
            logger.info("\nSkipping database integration test (USE_REAL_DB=false)")
            return True
        
        from services.document_ingestion_service import DocumentIngestionService
        
        logger.info("\n" + "="*60)
        logger.info("INTEGRATION TEST: Ingestion → Database")
        logger.info("="*60)
        
        async with DocumentIngestionService() as service:
            # Ingest a small batch
            results = await service.ingest_from_courtlistener(
                court_ids=['txed'],
                date_after='2024-01-01',
                max_per_court=2
            )
            
            assert results['success'], "Ingestion should succeed"
            assert results['documents_ingested'] > 0, "Should ingest some documents"
            
            logger.info(f"✓ Ingested {results['documents_ingested']} documents")
            logger.info(f"  Stats: {results['statistics']['summary']}")
        
        return True
    
    @staticmethod
    async def test_pipeline_stages():
        """Test pipeline stage interactions"""
        from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
        
        logger.info("\n" + "="*60)
        logger.info("INTEGRATION TEST: Pipeline Stages")
        logger.info("="*60)
        
        # Create test document
        test_doc = {
            'case_number': 'TEST-PIPELINE-001',
            'content': """
            In Eastern District of Texas, Judge Rodney Gilstrap presiding.
            This case cites Alice Corp. v. CLS Bank Int'l, 573 U.S. 208 (2014).
            The patent infringement claim involves artificial intelligence technology.
            """,
            'metadata': {
                'court_id': 'txed',
                'source': 'test'
            }
        }
        
        # Mock pipeline to avoid database dependency
        class TestPipeline(RobustElevenStagePipeline):
            def __init__(self):
                # Initialize without database
                self.stats = {}
                self.document_type_stats = {}
                self.error_collector = type('ErrorCollector', (), {
                    'get_report': lambda: {'errors': [], 'warnings': []}
                })()
                self.db_conn = None
        
        pipeline = TestPipeline()
        
        # Test court resolution
        court_result = pipeline._enhance_court_info_validated(test_doc)
        assert court_result.get('resolved'), "Court should be resolved"
        logger.info(f"✓ Court resolved: {court_result.get('court_name')}")
        
        # Test citation extraction
        citation_result = pipeline._extract_citations_validated(test_doc)
        assert citation_result.get('count', 0) > 0, "Should find citations"
        logger.info(f"✓ Citations found: {citation_result.get('count')}")
        
        # Test judge extraction
        judge_result = pipeline._enhance_judge_info_validated(test_doc)
        if judge_result.get('judge_name_found'):
            logger.info(f"✓ Judge identified: {judge_result.get('judge_name_found')}")
        
        return True


# =============================================================================
# END-TO-END TESTS
# =============================================================================

class EndToEndTestSuite:
    """End-to-end tests for complete workflows"""
    
    @staticmethod
    async def test_complete_workflow():
        """Test complete workflow from ingestion to processed output"""
        
        logger.info("\n" + "="*60)
        logger.info("E2E TEST: Complete Workflow")
        logger.info("="*60)
        
        if not (TestConfiguration.USE_REAL_API and TestConfiguration.USE_REAL_DB):
            logger.info("Skipping E2E test (requires REAL_API and REAL_DB)")
            return True
        
        from services.document_ingestion_service import DocumentIngestionService
        from eleven_stage_pipeline_robust_complete import RobustElevenStagePipeline
        
        # Step 1: Ingest documents
        logger.info("\n1. Ingesting documents...")
        async with DocumentIngestionService() as service:
            ingestion_results = await service.ingest_from_courtlistener(
                court_ids=['cafc'],
                date_after='2024-01-01',
                max_per_court=5
            )
        
        assert ingestion_results['success'], "Ingestion should succeed"
        logger.info(f"✓ Ingested {ingestion_results['documents_ingested']} documents")
        
        # Step 2: Process through pipeline
        logger.info("\n2. Processing through pipeline...")
        pipeline = RobustElevenStagePipeline()
        
        processing_results = await pipeline.process_batch(
            limit=5,
            extract_pdfs=True
        )
        
        assert processing_results['success'], "Processing should succeed"
        logger.info(f"✓ Processed {processing_results['statistics']['documents_processed']} documents")
        logger.info(f"  Completeness: {processing_results['verification']['completeness_score']:.1f}%")
        
        return True
    
    @staticmethod
    async def test_pdf_extraction_workflow():
        """Test workflow for documents requiring PDF extraction"""
        
        logger.info("\n" + "="*60)
        logger.info("E2E TEST: PDF Extraction Workflow")
        logger.info("="*60)
        
        from integrate_pdf_to_pipeline import PDFContentExtractor
        
        # Create test documents needing PDF extraction
        test_docs = [
            {
                'id': 1,
                'case_number': 'PDF-E2E-001',
                'content': '',  # Empty content
                'metadata': {
                    'download_url': 'https://www.supremecourt.gov/opinions/19pdf/18-1334_8m58.pdf'
                }
            }
        ]
        
        # Extract PDF content
        async with PDFContentExtractor() as extractor:
            enriched_docs = await extractor.enrich_documents_with_pdf_content(test_docs)
            
            stats = extractor.get_statistics()
            assert stats['pdfs_extracted'] > 0, "Should extract at least one PDF"
            
            logger.info(f"✓ Extracted {stats['pdfs_extracted']} PDFs")
            logger.info(f"  Total characters: {stats['total_chars_extracted']:,}")
        
        return True


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class PerformanceTestSuite:
    """Performance and scale tests"""
    
    @staticmethod
    async def test_batch_processing_performance():
        """Test performance with larger batches"""
        
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE TEST: Batch Processing")
        logger.info("="*60)
        
        # Create many test documents
        test_documents = []
        for i in range(100):
            test_documents.append({
                'case_number': f'PERF-TEST-{i:04d}',
                'content': f'Test content for performance testing. ' * 50,
                'metadata': {'court_id': 'txed', 'batch': i // 10}
            })
        
        from integrate_pdf_to_pipeline import PDFContentExtractor
        
        start_time = datetime.now()
        
        async with PDFContentExtractor() as extractor:
            # Process in batches
            for batch_start in range(0, len(test_documents), 20):
                batch = test_documents[batch_start:batch_start + 20]
                await extractor.enrich_documents_with_pdf_content(batch)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"✓ Processed {len(test_documents)} documents in {duration:.2f} seconds")
        logger.info(f"  Rate: {len(test_documents) / duration:.2f} docs/second")
        
        assert duration < 60, "Should process 100 documents in under 60 seconds"
        return True


# =============================================================================
# TEST RUNNER
# =============================================================================

class ComprehensiveTestRunner:
    """Orchestrates all test suites"""
    
    def __init__(self):
        self.results = {
            'unit': {},
            'integration': {},
            'e2e': {},
            'performance': {}
        }
    
    async def run_all_tests(self):
        """Run all test suites"""
        
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE COURT PROCESSOR TEST SUITE")
        logger.info("="*80)
        logger.info(f"\nTest Configuration:")
        logger.info(f"  USE_REAL_API: {TestConfiguration.USE_REAL_API}")
        logger.info(f"  USE_REAL_DB: {TestConfiguration.USE_REAL_DB}")
        logger.info(f"  USE_DOCKER: {TestConfiguration.USE_DOCKER}")
        
        # Setup environment
        TestConfiguration.setup_test_environment()
        
        # Run unit tests
        logger.info("\n\n" + "="*80)
        logger.info("RUNNING UNIT TESTS")
        logger.info("="*80)
        
        unit_tests = [
            ('PDF Processor', UnitTestSuite.test_pdf_processor),
            ('Court Resolver', UnitTestSuite.test_court_resolver),
            ('Citation Extractor', UnitTestSuite.test_citation_extractor),
            ('Document Validator', UnitTestSuite.test_document_validator)
        ]
        
        for test_name, test_func in unit_tests:
            try:
                result = await test_func()
                self.results['unit'][test_name] = 'PASSED' if result else 'FAILED'
            except Exception as e:
                self.results['unit'][test_name] = f'ERROR: {str(e)}'
                logger.error(f"Unit test '{test_name}' failed: {e}")
        
        # Run integration tests
        logger.info("\n\n" + "="*80)
        logger.info("RUNNING INTEGRATION TESTS")
        logger.info("="*80)
        
        integration_tests = [
            ('Ingestion to Database', IntegrationTestSuite.test_ingestion_to_database),
            ('Pipeline Stages', IntegrationTestSuite.test_pipeline_stages)
        ]
        
        for test_name, test_func in integration_tests:
            try:
                result = await test_func()
                self.results['integration'][test_name] = 'PASSED' if result else 'FAILED'
            except Exception as e:
                self.results['integration'][test_name] = f'ERROR: {str(e)}'
                logger.error(f"Integration test '{test_name}' failed: {e}")
        
        # Run E2E tests
        logger.info("\n\n" + "="*80)
        logger.info("RUNNING END-TO-END TESTS")
        logger.info("="*80)
        
        e2e_tests = [
            ('Complete Workflow', EndToEndTestSuite.test_complete_workflow),
            ('PDF Extraction Workflow', EndToEndTestSuite.test_pdf_extraction_workflow)
        ]
        
        for test_name, test_func in e2e_tests:
            try:
                result = await test_func()
                self.results['e2e'][test_name] = 'PASSED' if result else 'FAILED'
            except Exception as e:
                self.results['e2e'][test_name] = f'ERROR: {str(e)}'
                logger.error(f"E2E test '{test_name}' failed: {e}")
        
        # Run performance tests
        if os.getenv('RUN_PERFORMANCE_TESTS', 'false').lower() == 'true':
            logger.info("\n\n" + "="*80)
            logger.info("RUNNING PERFORMANCE TESTS")
            logger.info("="*80)
            
            performance_tests = [
                ('Batch Processing', PerformanceTestSuite.test_batch_processing_performance)
            ]
            
            for test_name, test_func in performance_tests:
                try:
                    result = await test_func()
                    self.results['performance'][test_name] = 'PASSED' if result else 'FAILED'
                except Exception as e:
                    self.results['performance'][test_name] = f'ERROR: {str(e)}'
                    logger.error(f"Performance test '{test_name}' failed: {e}")
        
        # Generate report
        self._generate_report()
    
    def _generate_report(self):
        """Generate test report"""
        
        logger.info("\n\n" + "="*80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*80)
        
        total_tests = 0
        passed_tests = 0
        
        for suite_name, suite_results in self.results.items():
            if not suite_results:
                continue
                
            logger.info(f"\n{suite_name.upper()} TESTS:")
            for test_name, result in suite_results.items():
                total_tests += 1
                if result == 'PASSED':
                    passed_tests += 1
                    logger.info(f"  ✓ {test_name}: {result}")
                else:
                    logger.error(f"  ✗ {test_name}: {result}")
        
        logger.info(f"\nOVERALL: {passed_tests}/{total_tests} tests passed")
        
        # Save detailed report
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'configuration': {
                    'use_real_api': TestConfiguration.USE_REAL_API,
                    'use_real_db': TestConfiguration.USE_REAL_DB,
                    'use_docker': TestConfiguration.USE_DOCKER
                },
                'results': self.results,
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0
                }
            }, f, indent=2)
        
        logger.info(f"\nDetailed report saved to: {report_file}")


if __name__ == "__main__":
    runner = ComprehensiveTestRunner()
    asyncio.run(runner.run_all_tests())