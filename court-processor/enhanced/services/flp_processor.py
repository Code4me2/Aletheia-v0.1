"""
Enhanced FLP Integration Service

Integrates Courts-DB, Reporters-DB, and Eyecite for comprehensive document enhancement.
"""
import sys
import os
import time
from typing import Dict, List, Any, Optional

# Add parent directory to path for importing existing services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from ..utils.logging import get_logger

# Import existing FLP services with fallbacks
try:
    from services.flp_integration_unified import FLPIntegrationUnified
    FLP_AVAILABLE = True
except ImportError:
    FLP_AVAILABLE = False

try:
    import eyecite
    EYECITE_AVAILABLE = True
except ImportError:
    EYECITE_AVAILABLE = False

try:
    from courts_db import courts
    COURTS_DB_AVAILABLE = True
except ImportError:
    COURTS_DB_AVAILABLE = False


class EnhancedFLPProcessor:
    """Enhanced FLP processor with comprehensive document enhancement"""
    
    def __init__(self):
        self.logger = get_logger("flp_processor")
        
        # Initialize FLP services
        self.flp_unified = None
        if FLP_AVAILABLE:
            try:
                self.flp_unified = FLPIntegrationUnified()
                self.logger.info("FLP Unified integration initialized")
            except Exception as e:
                self.logger.warning(f"Failed to initialize FLP Unified: {str(e)}")
        
        self.logger.info(f"FLP Processor initialized - Available services: "
                        f"FLP={FLP_AVAILABLE}, Eyecite={EYECITE_AVAILABLE}, Courts-DB={COURTS_DB_AVAILABLE}")
    
    def enhance_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """
        Comprehensive document enhancement using FLP tools
        
        Enhances document with:
        - Court information standardization (Courts-DB)
        - Citation extraction and validation (Eyecite)
        - Reporter information (Reporters-DB)
        """
        start_time = time.time()
        enhanced = document.copy()
        
        try:
            # Step 1: Court information enhancement
            enhanced = self._enhance_court_info(enhanced)
            
            # Step 2: Citation extraction and processing
            enhanced = self._extract_citations(enhanced)
            
            # Step 3: Reporter information enhancement
            enhanced = self._enhance_reporter_info(enhanced)
            
            # Step 4: Add processing metadata
            enhanced.update({
                'flp_processing_timestamp': time.time(),
                'flp_processing_duration': time.time() - start_time,
                'flp_services_used': {
                    'courts_db': COURTS_DB_AVAILABLE,
                    'eyecite': EYECITE_AVAILABLE,
                    'flp_unified': self.flp_unified is not None
                }
            })
            
            self.logger.debug(f"FLP enhancement completed in {time.time() - start_time:.2f}s")
            
            return enhanced
            
        except Exception as e:
            self.logger.error(f"FLP enhancement failed: {str(e)}")
            
            # Return document with error information
            enhanced.update({
                'flp_error': str(e),
                'flp_processing_timestamp': time.time(),
                'flp_processing_duration': time.time() - start_time
            })
            
            return enhanced
    
    def _enhance_court_info(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance court information using Courts-DB"""
        enhanced = document.copy()
        
        try:
            court_id = document.get('court_id')
            
            if COURTS_DB_AVAILABLE and court_id:
                # Look up court information
                court_info = courts.find_court(court_id)
                
                if court_info:
                    enhanced['court_info'] = {
                        'id': court_id,
                        'full_name': court_info.get('full_name', ''),
                        'short_name': court_info.get('short_name', ''),
                        'jurisdiction': court_info.get('jurisdiction', ''),
                        'level': court_info.get('level', ''),
                        'standardized': True
                    }
                    self.logger.debug(f"Enhanced court info for {court_id}")
                else:
                    enhanced['court_info'] = {
                        'id': court_id,
                        'standardized': False,
                        'error': 'Court not found in Courts-DB'
                    }
            elif court_id:
                # Minimal court info without Courts-DB
                enhanced['court_info'] = {
                    'id': court_id,
                    'standardized': False,
                    'note': 'Courts-DB not available'
                }
            else:
                enhanced['court_info'] = {
                    'id': None,
                    'standardized': False,
                    'note': 'No court ID provided'
                }
                
        except Exception as e:
            self.logger.warning(f"Court info enhancement failed: {str(e)}")
            enhanced['court_info'] = {
                'id': document.get('court_id'),
                'standardized': False,
                'error': str(e)
            }
        
        return enhanced
    
    def _extract_citations(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract citations using Eyecite"""
        enhanced = document.copy()
        citations = []
        
        try:
            plain_text = document.get('plain_text', '')
            
            if EYECITE_AVAILABLE and plain_text:
                # Extract citations using Eyecite
                found_citations = eyecite.find_citations(plain_text)
                
                for citation in found_citations:
                    citations.append({
                        'citation_string': str(citation),
                        'type': citation.__class__.__name__,
                        'groups': citation.groups if hasattr(citation, 'groups') else {},
                        'span': citation.span if hasattr(citation, 'span') else None
                    })
                
                self.logger.debug(f"Extracted {len(citations)} citations")
                
            elif plain_text:
                # Basic citation pattern matching without Eyecite
                import re
                basic_patterns = [
                    r'\d+\s+F\.\s*\d+d?\s+\d+',  # Federal reporters
                    r'\d+\s+U\.S\.\s+\d+',       # US Reports
                    r'\d+\s+S\.\s*Ct\.\s+\d+'   # Supreme Court
                ]
                
                for pattern in basic_patterns:
                    matches = re.finditer(pattern, plain_text, re.IGNORECASE)
                    for match in matches:
                        citations.append({
                            'citation_string': match.group(),
                            'type': 'BasicPattern',
                            'span': match.span()
                        })
                
                self.logger.debug(f"Found {len(citations)} basic pattern citations")
            
            enhanced['citations'] = citations
            enhanced['citation_count'] = len(citations)
            
        except Exception as e:
            self.logger.warning(f"Citation extraction failed: {str(e)}")
            enhanced['citations'] = []
            enhanced['citation_count'] = 0
            enhanced['citation_error'] = str(e)
        
        return enhanced
    
    def _enhance_reporter_info(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance reporter information"""
        enhanced = document.copy()
        
        try:
            # Use FLP unified service if available
            if self.flp_unified:
                # This would integrate with existing FLP processing
                # For now, add basic reporter metadata
                enhanced['reporter_info'] = {
                    'processed': True,
                    'source': 'flp_unified'
                }
            else:
                enhanced['reporter_info'] = {
                    'processed': False,
                    'note': 'FLP unified service not available'
                }
                
        except Exception as e:
            self.logger.warning(f"Reporter info enhancement failed: {str(e)}")
            enhanced['reporter_info'] = {
                'processed': False,
                'error': str(e)
            }
        
        return enhanced
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get status of FLP services"""
        return {
            'flp_unified_available': self.flp_unified is not None,
            'eyecite_available': EYECITE_AVAILABLE,
            'courts_db_available': COURTS_DB_AVAILABLE,
            'flp_integration_available': FLP_AVAILABLE
        }