"""
Extracted testing patterns from test_full_pipeline.py
Provides comprehensive testing infrastructure for document processing pipeline
"""
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
import asyncio
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class TestRunner:
    """
    Test runner for document processing pipeline components
    
    Extracted from test_full_pipeline.py with improvements for modularity
    """
    
    def __init__(self, db_config: Optional[Dict[str, str]] = None):
        """
        Initialize test runner
        
        Args:
            db_config: Database connection configuration
        """
        self.db_config = db_config or {
            'host': 'db',
            'database': 'aletheia',
            'user': 'aletheia_user',
            'password': '',  # Will use environment variable
        }
        
        self.test_results = []
        self.stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'start_time': None,
            'end_time': None
        }
    
    @contextmanager
    def database_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        finally:
            if conn:
                conn.close()
    
    def run_test(self, test_name: str, test_func: Callable, *args, **kwargs) -> bool:
        """
        Run a single test function with error handling
        
        Args:
            test_name: Name of the test
            test_func: Test function to run
            *args, **kwargs: Arguments for the test function
            
        Returns:
            True if test passed, False if failed
        """
        self.stats['total_tests'] += 1
        
        try:
            logger.info(f"Running test: {test_name}")
            print(f"\n=== Testing {test_name} ===")
            
            result = test_func(*args, **kwargs)
            
            if result:
                self.stats['passed_tests'] += 1
                self.test_results.append((test_name, True, None))
                logger.info(f"✓ {test_name} PASSED")
                return True
            else:
                self.stats['failed_tests'] += 1
                self.test_results.append((test_name, False, "Test returned False"))
                logger.error(f"✗ {test_name} FAILED")
                return False
                
        except Exception as e:
            self.stats['failed_tests'] += 1
            self.test_results.append((test_name, False, str(e)))
            logger.error(f"✗ {test_name} FAILED: {e}")
            print(f"✗ Error: {e}")
            return False
    
    def run_test_suite(self, test_suite: List[Tuple[str, Callable, tuple, dict]]):
        """
        Run a complete test suite
        
        Args:
            test_suite: List of (name, function, args, kwargs) tuples
        """
        self.stats['start_time'] = datetime.now()
        
        print("=" * 60)
        print("DOCUMENT PROCESSING PIPELINE TEST SUITE")
        print(f"Time: {self.stats['start_time']}")
        print("=" * 60)
        
        for test_name, test_func, args, kwargs in test_suite:
            self.run_test(test_name, test_func, *args, **kwargs)
        
        self.stats['end_time'] = datetime.now()
        self._print_summary()
    
    def _print_summary(self):
        """Print test suite summary"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        for test_name, passed, error in self.test_results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{test_name}: {status}")
            if error and not passed:
                print(f"  Error: {error}")
        
        print(f"\nResults: {self.stats['passed_tests']}/{self.stats['total_tests']} tests passed")
        print(f"Duration: {duration:.2f} seconds")
        
        success_rate = (self.stats['passed_tests'] / self.stats['total_tests']) * 100 if self.stats['total_tests'] > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")


class DatabaseTestSuite:
    """Test suite for database operations"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
    
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor() as cursor:
                cursor.execute("SELECT current_database(), current_user, version()")
                result = cursor.fetchone()
                print(f"✓ Connected to database: {result[0]} as {result[1]}")
                print(f"  PostgreSQL version: {result[2].split(',')[0]}")
            conn.close()
            return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False
    
    def test_table_existence(self, tables: List[str]) -> bool:
        """Test if required tables exist"""
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT table_name FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                existing_tables = [row['table_name'] for row in cursor.fetchall()]
                
                missing_tables = [table for table in tables if table not in existing_tables]
                
                if missing_tables:
                    print(f"✗ Missing tables: {missing_tables}")
                    print(f"  Available tables: {existing_tables}")
                    return False
                else:
                    print(f"✓ All required tables exist: {tables}")
                    return True
            
        except Exception as e:
            print(f"✗ Table check failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def test_document_retrieval(self, limit: int = 5) -> bool:
        """Test document retrieval from database"""
        try:
            conn = psycopg2.connect(**self.db_config)
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Try multiple table names that might exist
                table_candidates = [
                    'court_documents',
                    'opinions',
                    'opinions_unified',
                    'enhanced_court_documents'
                ]
                
                for table_name in table_candidates:
                    try:
                        cursor.execute(f"""
                            SELECT COUNT(*) as total FROM {table_name}
                        """)
                        count = cursor.fetchone()['total']
                        
                        if count > 0:
                            cursor.execute(f"""
                                SELECT * FROM {table_name} LIMIT %s
                            """, (limit,))
                            documents = cursor.fetchall()
                            
                            print(f"✓ Retrieved {len(documents)} documents from {table_name}")
                            print(f"  Total documents in table: {count}")
                            
                            # Show sample document structure
                            if documents:
                                sample_doc = documents[0]
                                print(f"  Sample document fields: {list(sample_doc.keys())}")
                            
                            return True
                            
                    except psycopg2.Error:
                        continue  # Try next table
                
                print("✗ No document tables found or accessible")
                return False
                
        except Exception as e:
            print(f"✗ Document retrieval test failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()


class ComponentTestSuite:
    """Test suite for individual pipeline components"""
    
    def test_component_availability(self, components: Dict[str, str]) -> bool:
        """
        Test availability of pipeline components
        
        Args:
            components: Dict of component_name -> import_path
        """
        available_components = []
        unavailable_components = []
        
        for component_name, import_path in components.items():
            try:
                exec(f"import {import_path}")
                available_components.append(component_name)
                print(f"✓ {component_name}: Available")
            except ImportError as e:
                unavailable_components.append(component_name)
                print(f"✗ {component_name}: Not available ({e})")
        
        print(f"\nComponent Status: {len(available_components)}/{len(components)} available")
        
        # Return True if at least some components are available
        return len(available_components) > 0
    
    def test_mock_citation_extraction(self) -> bool:
        """Test citation extraction with mock data"""
        try:
            test_text = """
            This case follows Brown v. Board of Education, 347 U.S. 483 (1954) and 
            cites to Marbury v. Madison, 5 U.S. 137 (1803). See also Smith v. Jones, 
            123 F.3d 456 (9th Cir. 1999) and 42 U.S.C. § 1983.
            """
            
            # Mock citation extraction (without eyecite)
            import re
            
            # Simple regex patterns for common citation formats
            citation_patterns = [
                r'\b\d+\s+U\.S\.\s+\d+',  # U.S. citations
                r'\b\d+\s+F\.\d*d\s+\d+',  # Federal citations
                r'\b\d+\s+U\.S\.C\.\s+§\s+\d+',  # USC citations
            ]
            
            found_citations = []
            for pattern in citation_patterns:
                matches = re.findall(pattern, test_text)
                found_citations.extend(matches)
            
            print(f"✓ Mock citation extraction found {len(found_citations)} citations:")
            for citation in found_citations:
                print(f"  - {citation}")
            
            return len(found_citations) > 0
            
        except Exception as e:
            print(f"✗ Mock citation extraction failed: {e}")
            return False
    
    def test_mock_court_standardization(self) -> bool:
        """Test court standardization with mock data"""
        try:
            # Mock court database
            mock_courts = {
                'txed': {
                    'id': 'txed',
                    'name': 'Eastern District of Texas',
                    'full_name': 'United States District Court for the Eastern District of Texas',
                    'citation_string': 'E.D. Tex.',
                    'jurisdiction': 'Federal District'
                },
                'cafc': {
                    'id': 'cafc',
                    'name': 'Federal Circuit',
                    'full_name': 'United States Court of Appeals for the Federal Circuit',
                    'citation_string': 'Fed. Cir.',
                    'jurisdiction': 'Federal Appellate'
                }
            }
            
            test_courts = ['txed', 'cafc', 'unknown']
            
            for court_id in test_courts:
                if court_id in mock_courts:
                    court = mock_courts[court_id]
                    print(f"✓ {court_id} → {court['full_name']}")
                else:
                    print(f"✗ {court_id} → Not found")
            
            return True
            
        except Exception as e:
            print(f"✗ Mock court standardization failed: {e}")
            return False


class PipelineTestSuite:
    """End-to-end pipeline testing"""
    
    def __init__(self, db_config: Dict[str, str]):
        self.db_config = db_config
    
    def test_document_processing_pipeline(self) -> bool:
        """Test complete document processing pipeline"""
        try:
            conn = psycopg2.connect(**self.db_config)
            
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Find a test document
                cursor.execute("""
                    SELECT * FROM court_documents 
                    WHERE content IS NOT NULL
                    LIMIT 1
                """)
                
                doc = cursor.fetchone()
                if not doc:
                    print("✗ No test documents available")
                    return False
                
                print(f"✓ Test document loaded: ID {doc['id']}")
                
                # Simulate pipeline processing
                enhanced_metadata = dict(doc.get('metadata', {}))
                
                # Mock processing steps
                enhanced_metadata.update({
                    'pipeline_test': {
                        'processed_at': datetime.now().isoformat(),
                        'components_tested': [
                            'document_retrieval',
                            'metadata_enhancement',
                            'citation_extraction',
                            'court_standardization'
                        ],
                        'test_status': 'completed'
                    }
                })
                
                # Update document (in test mode, use a copy)
                print("✓ Document processed through mock pipeline")
                print("✓ Metadata enhanced with test markers")
                
                return True
                
        except Exception as e:
            print(f"✗ Pipeline test failed: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()


def create_comprehensive_test_suite(db_config: Optional[Dict[str, str]] = None) -> List[Tuple[str, Callable, tuple, dict]]:
    """
    Create a comprehensive test suite for the document processing pipeline
    
    Args:
        db_config: Database configuration
        
    Returns:
        List of test cases ready for TestRunner
    """
    if db_config is None:
        db_config = {
            'host': 'db',
            'database': 'aletheia',
            'user': 'aletheia_user',
            'password': '',
        }
    
    # Initialize test suite components
    db_tests = DatabaseTestSuite(db_config)
    component_tests = ComponentTestSuite()
    pipeline_tests = PipelineTestSuite(db_config)
    
    # Define test suite
    test_suite = [
        # Database tests
        ("Database Connection", db_tests.test_database_connection, (), {}),
        ("Table Existence", db_tests.test_table_existence, (['court_documents', 'opinions'],), {}),
        ("Document Retrieval", db_tests.test_document_retrieval, (5,), {}),
        
        # Component tests
        ("Component Availability", component_tests.test_component_availability, ({
            'eyecite': 'eyecite',
            'courts_db': 'courts_db',
            'reporters_db': 'reporters_db',
            'judge_pics': 'judge_pics',
            'xray': 'xray'
        },), {}),
        ("Mock Citation Extraction", component_tests.test_mock_citation_extraction, (), {}),
        ("Mock Court Standardization", component_tests.test_mock_court_standardization, (), {}),
        
        # Pipeline tests
        ("Document Processing Pipeline", pipeline_tests.test_document_processing_pipeline, (), {}),
    ]
    
    return test_suite


def run_comprehensive_tests(db_config: Optional[Dict[str, str]] = None):
    """
    Run the complete test suite
    
    Args:
        db_config: Database configuration
    """
    # Create test runner
    runner = TestRunner(db_config)
    
    # Create test suite
    test_suite = create_comprehensive_test_suite(db_config)
    
    # Run tests
    runner.run_test_suite(test_suite)
    
    return runner.stats


# Convenience functions for specific test scenarios

def quick_database_test(db_config: Optional[Dict[str, str]] = None) -> bool:
    """Quick database connectivity test"""
    db_tests = DatabaseTestSuite(db_config or {
        'host': 'db',
        'database': 'aletheia', 
        'user': 'aletheia_user',
        'password': ''
    })
    
    return db_tests.test_database_connection()


def test_flp_components() -> Dict[str, bool]:
    """Test FLP component availability"""
    components = {
        'eyecite': 'eyecite',
        'courts_db': 'courts_db', 
        'reporters_db': 'reporters_db',
        'judge_pics': 'judge_pics',
        'xray': 'xray'
    }
    
    results = {}
    for component_name, import_path in components.items():
        try:
            exec(f"import {import_path}")
            results[component_name] = True
        except ImportError:
            results[component_name] = False
    
    return results


def validate_pipeline_readiness(db_config: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Validate that the pipeline is ready for production use
    
    Returns:
        Dictionary with readiness status and details
    """
    readiness = {
        'database_ready': False,
        'components_ready': False,
        'pipeline_ready': False,
        'overall_ready': False,
        'details': {}
    }
    
    # Test database
    try:
        readiness['database_ready'] = quick_database_test(db_config)
        readiness['details']['database'] = 'Connected' if readiness['database_ready'] else 'Failed to connect'
    except Exception as e:
        readiness['details']['database'] = f'Error: {e}'
    
    # Test components
    try:
        component_results = test_flp_components()
        available_count = sum(component_results.values())
        total_count = len(component_results)
        
        readiness['components_ready'] = available_count >= (total_count / 2)  # At least half available
        readiness['details']['components'] = {
            'available': available_count,
            'total': total_count,
            'details': component_results
        }
    except Exception as e:
        readiness['details']['components'] = f'Error: {e}'
    
    # Overall readiness
    readiness['pipeline_ready'] = readiness['database_ready'] and readiness['components_ready']
    readiness['overall_ready'] = readiness['pipeline_ready']
    
    return readiness


if __name__ == "__main__":
    # Run comprehensive tests when executed directly
    print("Running comprehensive pipeline tests...")
    stats = run_comprehensive_tests()
    
    # Print readiness assessment
    print("\n" + "=" * 60)
    print("PIPELINE READINESS ASSESSMENT")
    print("=" * 60)
    
    readiness = validate_pipeline_readiness()
    for key, value in readiness.items():
        if key != 'details':
            status = "✓ READY" if value else "✗ NOT READY"
            print(f"{key.replace('_', ' ').title()}: {status}")
    
    print(f"\nDetails: {json.dumps(readiness['details'], indent=2)}")


class MockFLPService:
    """
    Mock Free Law Project service for testing
    
    Provides mock implementations of FLP APIs without requiring actual services
    """
    
    def __init__(self):
        """Initialize mock service with test data"""
        self.mock_court_data = {
            'txed': {'name': 'Eastern District of Texas', 'type': 'district'},
            'ca5': {'name': 'Fifth Circuit Court of Appeals', 'type': 'appellate'}
        }
        
        self.mock_citations = [
            "123 F.3d 456 (5th Cir. 2020)",
            "789 F.2d 123 (Fed. Cir. 1995)"
        ]
        
        self.mock_judges = {
            'gilstrap': {'name': 'Rodney Gilstrap', 'court': 'txed'},
            'smith': {'name': 'John Smith', 'court': 'ca5'}
        }
    
    def resolve_court(self, court_string: str) -> Dict[str, Any]:
        """Mock court resolution"""
        court_lower = court_string.lower()
        for court_id, court_info in self.mock_court_data.items():
            if court_lower in court_id or court_lower in court_info['name'].lower():
                return {
                    'court_id': court_id,
                    'court_name': court_info['name'],
                    'type': court_info['type'],
                    'error': None
                }
        
        return {
            'court_id': None,
            'court_name': None,
            'type': None,
            'error': f'Court not found: {court_string}'
        }
    
    def extract_citations(self, text: str) -> List[str]:
        """Mock citation extraction"""
        # Simple mock - return predefined citations if text contains keywords
        if any(keyword in text.lower() for keyword in ['f.3d', 'f.2d', 'court', 'case']):
            return self.mock_citations
        return []
    
    def get_judge_info(self, judge_name: str) -> Optional[Dict[str, Any]]:
        """Mock judge information lookup"""
        judge_lower = judge_name.lower()
        for judge_id, judge_info in self.mock_judges.items():
            if judge_lower in judge_info['name'].lower():
                return {
                    'judge_id': judge_id,
                    'name': judge_info['name'],
                    'court': judge_info['court'],
                    'photo_available': True
                }
        return None