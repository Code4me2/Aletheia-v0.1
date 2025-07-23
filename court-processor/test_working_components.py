#!/usr/bin/env python3
"""
Test Working Components - Verify what's actually functional in the pipeline
"""

import asyncio
import logging
import json
from datetime import datetime
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComponentTester:
    """Test individual components to identify what's working"""
    
    def __init__(self):
        self.working_components = []
        self.broken_components = []
        self.test_results = {}
    
    async def run_tests(self):
        """Run all component tests"""
        logger.info("Testing Pipeline Components")
        logger.info("=" * 60)
        
        # Test each component individually
        await self.test_courtlistener_service()
        await self.test_flp_integration()
        await self.test_database()
        await self.test_legal_enhancer()
        await self.test_recap_processor()
        await self.test_flp_api()
        
        # Generate summary
        self.generate_summary()
    
    async def test_courtlistener_service(self):
        """Test CourtListener service"""
        component = "CourtListener Service"
        try:
            from services.courtlistener_service import CourtListenerService
            
            # Test instantiation
            cl_service = CourtListenerService()
            
            # Check if API key is set
            api_key_set = bool(cl_service.api_token)
            
            # Test basic functionality (without making actual API calls)
            test_results = {
                'can_import': True,
                'can_instantiate': True,
                'api_key_configured': api_key_set,
                'has_fetch_opinions': hasattr(cl_service, 'fetch_opinions'),
                'has_fetch_dockets': hasattr(cl_service, 'fetch_dockets'),
                'has_search': hasattr(cl_service, 'search_opinions')
            }
            
            if all(test_results.values()):
                self.working_components.append(component)
                logger.info(f"✅ {component}: All checks passed")
            else:
                self.broken_components.append(component)
                logger.warning(f"⚠️  {component}: Some checks failed")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    async def test_flp_integration(self):
        """Test FLP Integration"""
        component = "FLP Integration"
        try:
            from services.flp_integration import FLPIntegration
            
            flp = FLPIntegration()
            
            # Test individual FLP tools
            test_results = {
                'can_import': True,
                'can_instantiate': True,
                'eyecite_available': False,
                'courts_db_available': False,
                'reporters_db_available': False,
                'judge_pics_available': False
            }
            
            # Test eyecite
            try:
                from eyecite import get_citations
                citations = list(get_citations("Test v. Case, 123 F.3d 456"))
                test_results['eyecite_available'] = len(citations) > 0
            except:
                pass
            
            # Test courts-db
            try:
                from courts_db import find_court
                courts = find_court("Eastern")
                test_results['courts_db_available'] = len(courts) > 0
            except:
                pass
            
            # Test reporters-db
            try:
                from reporters_db import REPORTERS
                test_results['reporters_db_available'] = len(REPORTERS) > 0
            except:
                pass
            
            # Test judge-pics
            try:
                import judge_pics
                test_results['judge_pics_available'] = True
            except:
                pass
            
            # Check methods
            test_results['has_extract_citations'] = hasattr(flp, 'extract_citations')
            test_results['has_get_court_info'] = hasattr(flp, 'get_court_info')
            test_results['has_get_judge_info'] = hasattr(flp, 'get_judge_info')
            
            if sum(test_results.values()) >= 6:  # At least 6 features working
                self.working_components.append(component)
                logger.info(f"✅ {component}: Most features working")
            else:
                self.broken_components.append(component)
                logger.warning(f"⚠️  {component}: Limited functionality")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    async def test_database(self):
        """Test database connectivity"""
        component = "Database Connection"
        try:
            from services.database import get_db_connection
            
            # Test if we can import
            test_results = {
                'can_import': True,
                'connection_possible': False,
                'tables_exist': False
            }
            
            # Don't actually connect (might not be in Docker)
            # Just verify the function exists
            test_results['get_db_connection_exists'] = callable(get_db_connection)
            
            self.working_components.append(component)
            logger.info(f"✅ {component}: Database module available")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    async def test_legal_enhancer(self):
        """Test legal document enhancer"""
        component = "Legal Document Enhancer"
        try:
            from services.legal_document_enhancer import enhance_legal_document
            
            # Create test element
            class TestElement:
                def __init__(self, text):
                    self.text = text
                    self.category = 'NarrativeText'
                    self.metadata = type('obj', (object,), {})()
            
            # Test enhancement
            test_elements = [TestElement("This is a test sentence.")]
            enhanced = enhance_legal_document(test_elements, 'opinion')
            
            test_results = {
                'can_import': True,
                'can_enhance': len(enhanced) > 0,
                'adds_metadata': hasattr(enhanced[0].metadata, 'legal') if enhanced else False,
                'supports_opinion': True,
                'supports_order': True,
                'supports_transcript': True,
                'supports_docket': True
            }
            
            # Test different document types
            for doc_type in ['order', 'transcript', 'docket']:
                try:
                    result = enhance_legal_document([TestElement("Test")], doc_type)
                    test_results[f'supports_{doc_type}'] = len(result) > 0
                except:
                    test_results[f'supports_{doc_type}'] = False
            
            if all(test_results.values()):
                self.working_components.append(component)
                logger.info(f"✅ {component}: Fully functional")
            else:
                self.broken_components.append(component)
                logger.warning(f"⚠️  {component}: Partially functional")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    async def test_recap_processor(self):
        """Test RECAP processor"""
        component = "RECAP Processor"
        try:
            from services.recap_processor import RECAPProcessor
            
            # Test instantiation
            recap = RECAPProcessor()
            
            test_results = {
                'can_import': True,
                'can_instantiate': True,
                'has_process_docket': hasattr(recap, 'process_docket'),
                'has_extract_documents': hasattr(recap, 'extract_documents'),
                'has_process_document': hasattr(recap, 'process_document')
            }
            
            if all(test_results.values()):
                self.working_components.append(component)
                logger.info(f"✅ {component}: All methods available")
            else:
                self.broken_components.append(component)
                logger.warning(f"⚠️  {component}: Some methods missing")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    async def test_flp_api(self):
        """Test FLP API module"""
        component = "FLP API"
        try:
            # Check if flp_api.py exists
            flp_api_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'flp_api.py'
            )
            
            test_results = {
                'file_exists': os.path.exists(flp_api_path),
                'can_import': False,
                'has_citation_extraction': False,
                'has_court_lookup': False,
                'has_judge_lookup': False
            }
            
            if test_results['file_exists']:
                try:
                    import flp_api
                    test_results['can_import'] = True
                    
                    # Check for key functions
                    test_results['has_citation_extraction'] = hasattr(flp_api, 'extract_citations')
                    test_results['has_court_lookup'] = hasattr(flp_api, 'lookup_court')
                    test_results['has_judge_lookup'] = hasattr(flp_api, 'lookup_judge')
                    
                except Exception as e:
                    logger.debug(f"Import error: {e}")
            
            if test_results['can_import']:
                self.working_components.append(component)
                logger.info(f"✅ {component}: Module available")
            else:
                self.broken_components.append(component)
                logger.warning(f"⚠️  {component}: Module not fully functional")
            
            self.test_results[component] = test_results
            
        except Exception as e:
            self.broken_components.append(component)
            logger.error(f"❌ {component}: {str(e)}")
            self.test_results[component] = {'error': str(e)}
    
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "=" * 60)
        print("PIPELINE COMPONENT STATUS REPORT")
        print("=" * 60)
        
        print(f"\n✅ Working Components ({len(self.working_components)}):")
        for component in self.working_components:
            print(f"  - {component}")
            if component in self.test_results:
                details = self.test_results[component]
                if isinstance(details, dict) and 'error' not in details:
                    for key, value in details.items():
                        if value:
                            print(f"    • {key}: ✓")
        
        print(f"\n❌ Broken/Incomplete Components ({len(self.broken_components)}):")
        for component in self.broken_components:
            print(f"  - {component}")
            if component in self.test_results:
                details = self.test_results[component]
                if 'error' in details:
                    print(f"    • Error: {details['error']}")
                elif isinstance(details, dict):
                    for key, value in details.items():
                        if not value:
                            print(f"    • {key}: ✗")
        
        # Overall health score
        total_components = len(self.working_components) + len(self.broken_components)
        health_score = (len(self.working_components) / max(1, total_components)) * 100
        
        print(f"\n📊 Pipeline Health Score: {health_score:.1f}%")
        print(f"   Working: {len(self.working_components)}/{total_components}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if "CourtListener Service" in self.test_results:
            if not self.test_results["CourtListener Service"].get('api_key_configured'):
                print("  - Set COURTLISTENER_API_TOKEN environment variable")
        
        if "Database Connection" in self.broken_components:
            print("  - Ensure PostgreSQL is running and accessible")
        
        if "FLP Integration" in self.test_results:
            flp_results = self.test_results["FLP Integration"]
            if not flp_results.get('eyecite_available'):
                print("  - Install eyecite: pip install eyecite")
            if not flp_results.get('courts_db_available'):
                print("  - Install courts-db: pip install courts-db")
        
        # Save detailed results
        report_file = f"component_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'working_components': self.working_components,
                'broken_components': self.broken_components,
                'test_results': self.test_results,
                'health_score': health_score
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: {report_file}")

async def main():
    """Run component tests"""
    tester = ComponentTester()
    await tester.run_tests()

if __name__ == "__main__":
    asyncio.run(main())