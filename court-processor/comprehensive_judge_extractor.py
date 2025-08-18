#!/usr/bin/env python3
"""
Comprehensive judge extraction using all available sources from the 3-step traversal
"""

import re
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class JudgeInfo:
    """Complete judge information with source tracking"""
    name: str
    source: str
    confidence: float
    all_sources: Dict[str, str]  # All places we found judge info
    

class ComprehensiveJudgeExtractor:
    """Extract judge information from all available sources in priority order"""
    
    # Priority order for judge sources (highest to lowest confidence)
    JUDGE_SOURCE_PRIORITY = [
        ('docket', 'assigned_to_str', 1.0),      # Most authoritative
        ('docket', 'assigned_to', 0.95),         # Alternative docket field
        ('cluster', 'judges', 0.9),              # Good source, may have multiple
        ('search', 'judge', 0.85),               # Search result judge
        ('opinion', 'author_str', 0.7),          # Usually just last name
        ('cluster', 'panel_names', 0.6),         # Panel cases
        ('docket_pattern', None, 0.5),           # Extracted from docket number
    ]
    
    # E.D. Texas judge initials mapping (from docket patterns like 2:21-cv-00316-JRG)
    TXED_JUDGE_INITIALS = {
        'JRG': 'Rodney Gilstrap',
        'RSP': 'Roy S. Payne',
        'RWS': 'Robert W. Schroeder III',
        'JDC': 'J. Campbell Barker',
        'MAC': 'Marcia A. Crone',
        'RC': 'Ron Clark',
        'TJW': 'T. John Ward',
        'DF': 'David Folsom',
        'CD': 'Charles Everingham',
        'MHS': 'Michael H. Schneider',
        'NM': 'Neal Manne',
        'AML': 'Amos L. Mazzant III',
    }
    
    @classmethod
    def extract_comprehensive_judge_info(
        cls,
        search_result: Optional[Dict] = None,
        opinion_data: Optional[Dict] = None,
        cluster_data: Optional[Dict] = None,
        docket_data: Optional[Dict] = None,
        docket_number: Optional[str] = None
    ) -> Optional[JudgeInfo]:
        """
        Extract judge information from all available sources
        
        Returns JudgeInfo with the best available judge name and tracking of all sources
        """
        all_sources = {}
        
        # Collect from all sources
        if docket_data:
            if docket_data.get('assigned_to_str'):
                all_sources['docket_assigned_to_str'] = docket_data['assigned_to_str']
            if docket_data.get('assigned_to'):
                all_sources['docket_assigned_to'] = str(docket_data['assigned_to'])
                
        if cluster_data:
            if cluster_data.get('judges'):
                all_sources['cluster_judges'] = cluster_data['judges']
            if cluster_data.get('panel_names'):
                # Handle list of panel judges
                panel = cluster_data['panel_names']
                if isinstance(panel, list) and panel:
                    all_sources['cluster_panel'] = ', '.join(panel)
                elif isinstance(panel, str) and panel:
                    all_sources['cluster_panel'] = panel
                    
        if search_result and search_result.get('judge'):
            all_sources['search_judge'] = search_result['judge']
            
        if opinion_data and opinion_data.get('author_str'):
            all_sources['opinion_author'] = opinion_data['author_str']
        
        # Try docket number pattern extraction
        if docket_number:
            judge_from_pattern = cls.extract_from_docket_number(docket_number)
            if judge_from_pattern:
                all_sources['docket_pattern'] = judge_from_pattern
        
        # Find best source based on priority
        for source_type, field_name, confidence in cls.JUDGE_SOURCE_PRIORITY:
            if source_type == 'docket_pattern':
                if 'docket_pattern' in all_sources:
                    return JudgeInfo(
                        name=all_sources['docket_pattern'],
                        source='docket_pattern',
                        confidence=confidence,
                        all_sources=all_sources
                    )
            else:
                source_key = f"{source_type}_{field_name}"
                if source_key in all_sources and all_sources[source_key]:
                    judge_name = all_sources[source_key]
                    
                    # Clean up judge name
                    judge_name = cls.clean_judge_name(judge_name)
                    
                    if judge_name:
                        return JudgeInfo(
                            name=judge_name,
                            source=source_key,
                            confidence=confidence,
                            all_sources=all_sources
                        )
        
        # Log if we found any sources but couldn't extract
        if all_sources:
            logger.warning(f"Found judge sources but couldn't extract: {all_sources}")
            
        return None
    
    @classmethod
    def extract_from_docket_number(cls, docket_number: str) -> Optional[str]:
        """Extract judge from docket number pattern (e.g., 2:21-cv-00316-JRG)"""
        if not docket_number:
            return None
            
        # Pattern for judge initials at end of docket number
        match = re.search(r'-([A-Z]{2,3})(?:-\d+)?$', docket_number)
        if match:
            initials = match.group(1)
            # Check if we have a mapping for these initials
            if initials in cls.TXED_JUDGE_INITIALS:
                return cls.TXED_JUDGE_INITIALS[initials]
            # Return initials if no mapping
            return initials
            
        return None
    
    @classmethod
    def clean_judge_name(cls, judge_name: str) -> str:
        """Clean and standardize judge name"""
        if not judge_name:
            return ""
            
        # Remove common prefixes
        judge_name = re.sub(r'^(Judge|Hon\.|Honorable|The Honorable)\s+', '', judge_name, flags=re.IGNORECASE)
        
        # Remove trailing punctuation
        judge_name = judge_name.strip().rstrip('.,;')
        
        # Normalize whitespace
        judge_name = ' '.join(judge_name.split())
        
        return judge_name
    
    @classmethod
    def expand_author_name(cls, author_str: str) -> Optional[str]:
        """
        Try to expand author string (usually just last name) to full name
        This would need a database of judges or additional API calls
        """
        # For now, just return as-is
        # In production, this could query a judge database
        return author_str if author_str else None
    
    @classmethod
    def get_judge_summary(cls, judge_info: Optional[JudgeInfo]) -> Dict:
        """Get a summary of judge extraction for logging/debugging"""
        if not judge_info:
            return {"found": False}
            
        return {
            "found": True,
            "name": judge_info.name,
            "source": judge_info.source,
            "confidence": judge_info.confidence,
            "sources_checked": len(judge_info.all_sources),
            "all_values": judge_info.all_sources
        }


def test_comprehensive_extraction():
    """Test the comprehensive judge extraction"""
    
    # Test data mimicking real API responses
    search_result = {
        'judge': 'Ron Clark',
        'docketNumber': '2:21-cv-00316-JRG'
    }
    
    cluster_data = {
        'judges': 'Rodney Gilstrap',  # This is often populated!
        'panel_names': []
    }
    
    docket_data = {
        'assigned_to_str': '',  # Often empty
        'assigned_to': None
    }
    
    opinion_data = {
        'author_str': 'Gilstrap'  # Just last name
    }
    
    # Test extraction
    judge_info = ComprehensiveJudgeExtractor.extract_comprehensive_judge_info(
        search_result=search_result,
        opinion_data=opinion_data,
        cluster_data=cluster_data,
        docket_data=docket_data,
        docket_number=search_result['docketNumber']
    )
    
    print("Test Results:")
    print(ComprehensiveJudgeExtractor.get_judge_summary(judge_info))
    
    # Test with empty docket
    print("\nTest with empty docket but good cluster:")
    judge_info2 = ComprehensiveJudgeExtractor.extract_comprehensive_judge_info(
        cluster_data={'judges': 'Roy S. Payne'},
        docket_data={'assigned_to_str': ''}
    )
    print(ComprehensiveJudgeExtractor.get_judge_summary(judge_info2))


if __name__ == "__main__":
    test_comprehensive_extraction()