"""
Enhanced Judge Extraction Patterns for E.D. Texas and other courts

This module provides comprehensive judge extraction patterns and mappings.
"""

import re
from typing import Optional, Dict, List

class EnhancedJudgePatterns:
    """Enhanced patterns for judge extraction"""
    
    # Comprehensive judge initials mapping for major districts
    JUDGE_INITIALS_MAP = {
        # Eastern District of Texas
        'JRG': 'Rodney Gilstrap',
        'RWS': 'Robert W. Schroeder III', 
        'RSP': 'Roy S. Payne',
        'MSS': 'Mitchell S. Sandlin',
        'JDC': 'J. Campbell Barker',
        'RAS': 'Richard A. Schell',
        'MAM': 'Marcia A. Mitchell',
        
        # Southern District of Texas
        'LHR': 'Lee H. Rosenthal',
        'KBE': 'Keith B. Ellison',
        'AML': 'Alfred M. Bennett',
        
        # Northern District of Texas
        'BSO': 'Barbara M.G. Lynn',
        'SGF': 'Sidney A. Fitzwater',
        
        # Add more as discovered
    }
    
    # Enhanced extraction patterns
    JUDGE_PATTERNS = [
        # Standard patterns
        (r"Before[:\s]+(?:Chief\s+)?(?:Circuit\s+)?Judge[s]?\s+([A-Z][A-Za-z\s,.'-]+?)(?:\.|,|
|$)", 0.9),
        (r"(?:Honorable\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+),?\s+(?:Chief\s+)?(?:District|Circuit)\s+Judge", 0.95),
        
        # Signature patterns
        (r"^\s*/s/\s+([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+)\s*$", 0.85),
        (r"_+\s*
\s*([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+)\s*
\s*(?:Chief\s+)?(?:United States\s+)?(?:District|Circuit)", 0.9),
        
        # Opinion author patterns
        (r"([A-Z]+),\s+(?:Chief\s+)?(?:District|Circuit)\s+Judge[,.]?\s+(?:delivered|announced)", 0.95),
        (r"Opinion\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+)", 0.9),
        
        # Concurrence/Dissent patterns
        (r"([A-Z][a-z]+(?:\s+[A-Z]\.)?\s+[A-Z][a-z]+),\s+J\.,\s+(?:concurring|dissenting)", 0.85),
        
        # Panel patterns
        (r"Before\s+([A-Z][A-Z']+(?:,\s+[A-Z][A-Z']+)*(?:\s+and\s+[A-Z][A-Z']+)?),?\s+Circuit\s+Judges", 0.8),
    ]
    
    @classmethod
    def extract_judge_from_docket_number(cls, docket_number: str) -> Optional[str]:
        """
        Extract judge from docket number pattern
        Examples: 
        - 2:16-CV-682-JRG → Rodney Gilstrap
        - 4:20-cv-123-RWS → Robert W. Schroeder III
        """
        if not docket_number:
            return None
            
        # Pattern: ends with dash followed by 2-3 uppercase letters
        match = re.search(r'-([A-Z]{2,4})(?:-\d+)?$', docket_number)
        if match:
            initials = match.group(1)
            
            # First check our mapping
            if initials in cls.JUDGE_INITIALS_MAP:
                return cls.JUDGE_INITIALS_MAP[initials]
            
            # Return initials if not mapped (still useful)
            return f"Judge {initials}"
            
        return None
    
    @classmethod
    def extract_from_content(cls, content: str, doc_type: str = 'opinion') -> Dict:
        """Enhanced content extraction with multiple patterns"""
        
        if not content:
            return {'found': False, 'reason': 'No content provided'}
        
        # Try each pattern with confidence scoring
        best_match = None
        best_confidence = 0
        
        for pattern, base_confidence in cls.JUDGE_PATTERNS:
            matches = re.finditer(pattern, content, re.MULTILINE | re.IGNORECASE)
            
            for match in matches:
                judge_text = match.group(1).strip()
                
                # Clean up the match
                judge_text = re.sub(r'\s+', ' ', judge_text)
                judge_text = re.sub(r'[,.]$', '', judge_text)
                
                # Skip if too short or too long
                if len(judge_text) < 5 or len(judge_text) > 50:
                    continue
                
                # Calculate confidence based on position in document
                position_ratio = match.start() / len(content)
                position_boost = 0.1 if position_ratio < 0.2 or position_ratio > 0.8 else 0
                
                confidence = base_confidence + position_boost
                
                if confidence > best_confidence:
                    best_match = judge_text
                    best_confidence = confidence
        
        if best_match:
            return {
                'found': True,
                'judge_name': best_match,
                'confidence': best_confidence * 100,
                'source': 'pattern_matching'
            }
        
        # Try docket number extraction as fallback
        docket_match = re.search(r'(?:Case\s+)?(?:No\.?\s+)?(\d+:\d+-[A-Z]{2}-\d+-[A-Z]{2,4})', content)
        if docket_match:
            judge_from_docket = cls.extract_judge_from_docket_number(docket_match.group(1))
            if judge_from_docket:
                return {
                    'found': True,
                    'judge_name': judge_from_docket,
                    'confidence': 75,
                    'source': 'docket_number'
                }
        
        return {'found': False, 'reason': 'No judge patterns matched'}
    
    @classmethod
    def normalize_judge_name(cls, name: str) -> str:
        """Normalize judge name for consistency"""
        
        # Remove titles
        name = re.sub(r'(?:Hon\.|Honorable|Judge|Justice|Chief|Senior)', '', name, flags=re.IGNORECASE)
        
        # Clean up spacing and punctuation
        name = re.sub(r'\s+', ' ', name)
        name = re.sub(r'[,.]$', '', name)
        name = name.strip()
        
        # Standardize initials
        name = re.sub(r'([A-Z])', r'.', name)
        
        return name
