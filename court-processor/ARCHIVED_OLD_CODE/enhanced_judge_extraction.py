#!/usr/bin/env python3
"""
Enhanced Judge Extraction with OCR Tolerance
Implements recommendations for better judge name extraction from court documents
"""

import re
from typing import Optional, List, Tuple, Dict
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class EnhancedJudgeExtractor:
    """Enhanced judge extraction with OCR tolerance and fuzzy matching"""
    
    # Known Delaware federal judges for fuzzy matching
    KNOWN_JUDGES = [
        "Gregory B. Williams",
        "Jennifer Choe-Groves",
        "Richard G. Andrews",
        "Colm F. Connolly",
        "Maryellen Noreika",
        "Sherry R. Fallon",
        "Christopher J. Burke",
        "Leonard P. Stark",
        "Sue L. Robinson",
        "Kent A. Jordan",
        "Joseph J. Farnan",
        "Mary Pat Thynge"
    ]
    
    @staticmethod
    def preprocess_ocr_text(text: str) -> str:
        """Fix common OCR issues before extraction"""
        if not text:
            return text
            
        # Fix common OCR issues
        replacements = {
            # Broken words
            r'\bGISTRATE\b': 'MAGISTRATE',
            r'\bMAGI STRATE\b': 'MAGISTRATE',
            r'\bDERAL\b': 'FEDERAL',
            r'\bFED ERAL\b': 'FEDERAL',
            r'\bTRICT\b': 'DISTRICT',
            r'\bDIS TRICT\b': 'DISTRICT',
            r'\bIRCUIT\b': 'CIRCUIT',
            r'\bCIR CUIT\b': 'CIRCUIT',
            r'\bUNITEDSTATES\b': 'UNITED STATES',
            r'\bDISTRICTJUDGE\b': 'DISTRICT JUDGE',
            
            # Fix ligatures
            'ﬀ': 'ff',
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
            
            # Remove special characters that interfere
            r'[□■▪▫◦•†‡§¶]': '',
            
            # Fix spacing issues around periods
            r'([A-Z])\.([A-Z])': r'\1. \2',  # Add space after middle initial
            
            # Fix double spaces
            r'\s+': ' ',
            
            # Fix newlines that break names
            r'\n+': '\n'
        }
        
        processed_text = text
        for pattern, replacement in replacements.items():
            processed_text = re.sub(pattern, replacement, processed_text, flags=re.IGNORECASE)
        
        return processed_text
    
    @staticmethod
    def extract_judge_patterns(text: str) -> List[Tuple[str, str, int]]:
        """Extract potential judge names with OCR-tolerant patterns
        Returns: List of (name, pattern_used, confidence_score)
        """
        matches = []
        
        # Preprocess text
        text = EnhancedJudgeExtractor.preprocess_ocr_text(text)
        
        # Enhanced patterns with OCR tolerance
        patterns = [
            # High confidence patterns (score: 90-100)
            (r'/s/\s*([A-Z][A-Za-z\-\.]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)', 'electronic_signature', 95),
            (r'BY THE COURT:\s*\n*\s*(?:[^\n]*\n+)?\s*([A-Z][A-Za-z\-\.]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)', 'by_the_court', 90),
            
            # Standard patterns with OCR tolerance (score: 80-90)
            (r'([A-Z][A-Za-z\-\.]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)[\s,]*(?:Chief\s+)?(?:U\.?S\.?\s+)?(?:District|Circuit|Magistrate)\s+Judge', 'name_before_title', 85),
            (r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][A-Za-z\-\.]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)', 'honorable_judge', 85),
            
            # All caps patterns with better handling (score: 70-80)
            (r'([A-Z]+(?:\s+[A-Z]\.)?(?:\s+[A-Z]+)+)\s*\n*\s*UNITED\s+STATES\s+(?:DISTRICT|CIRCUIT|MAGISTRATE)\s+JUDGE', 'all_caps_signature', 75),
            (r'([A-Z][A-Z\s\.]+?)\s*\n*\s*(?:Chief\s+)?(?:U\.?S\.?\s+)?(?:DISTRICT|CIRCUIT|MAGISTRATE)\s+JUDGE', 'all_caps_relaxed', 70),
            
            # Handle concatenated names (score: 60-70)
            (r'([A-Z][a-z]+[A-Z]\.?[A-Z][a-z]+)\s*(?:UNITED\s+STATES\s+)?(?:DISTRICT|CIRCUIT|MAGISTRATE)?\s*JUDGE', 'concatenated_name', 65),
            (r'signed\s+by\s+([A-Z][a-z]+[A-Z]\.?[A-Z][a-z]+)', 'signed_by_concat', 68),
            
            # Fuzzy patterns for damaged text (score: 60-70) - More restrictive
            (r'([A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)\s*\n*\s*(?:Judge|JUDGE)', 'fuzzy_judge', 65),
            (r'(?:Before|BEFORE):?\s*(?:the\s+)?(?:Honorable\s+)?([A-Z][A-Za-z\-]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][A-Za-z\-]+)+)(?:,|\s+Judge)', 'before_judge', 70),
            
            # Last resort patterns (score: 50-60)
            (r'([A-Z][A-Za-z\-]+\s+[A-Z]\.?\s*[A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+)?)\s*$', 'end_signature', 50),
        ]
        
        # Search in both start and end of document
        search_areas = [
            (text[:2000], 'start'),
            (text[-2000:] if len(text) > 2000 else text, 'end')
        ]
        
        for search_text, location in search_areas:
            for pattern, pattern_name, base_score in patterns:
                for match in re.finditer(pattern, search_text, re.MULTILINE | re.IGNORECASE):
                    name = match.group(1).strip().strip(',')
                    
                    # Clean up the name
                    name = re.sub(r'\s+', ' ', name)  # Normalize spaces
                    
                    # Handle concatenated names
                    concat_match = re.match(r'^([A-Z][a-z]+)([A-Z]\.?)([A-Z][a-z]+)(.*)$', name)
                    if concat_match:
                        name = f"{concat_match.group(1)} {concat_match.group(2)} {concat_match.group(3)}{concat_match.group(4)}"
                    
                    name = name.title() if name.isupper() else name  # Fix all caps
                    
                    # Validate extracted name
                    if EnhancedJudgeExtractor._validate_judge_name(name):
                        # Adjust score based on location
                        score = base_score + (5 if location == 'end' else 0)
                        matches.append((name, f"{pattern_name}_{location}", score))
        
        return matches
    
    @staticmethod
    def _validate_judge_name(name: str) -> bool:
        """Validate that extracted text is likely a judge name"""
        if not name or len(name) < 5:
            return False
            
        # Check for concatenated names (e.g., WilliamC.Bryson)
        if re.match(r'^[A-Z][a-z]+[A-Z]\.?[A-Z][a-z]+', name):
            # This is likely a concatenated name, which is valid
            return True
            
        # Must have at least two parts (first and last name) for normal names
        parts = name.split()
        if len(parts) < 2 and not re.search(r'[A-Z][a-z]+[A-Z]', name):
            return False
            
        # Avoid common false positives
        exclude_terms = [
            'UNITED STATES', 'DISTRICT', 'MAGISTRATE', 'COURT', 'JUDGE',
            'MEMORANDUM', 'OPINION', 'ORDER', 'PURSUANT', 'FEDERAL',
            'CIVIL', 'CRIMINAL', 'ACTION', 'BEFORE', 'SIGNED BY',
            'WITH THE', 'FROM', 'TO', 'IN THE', 'OF THE', 'BY THE',
            'IS', 'ARE', 'WAS', 'WERE', 'BE', 'BEEN', 'BEING',
            'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL',
            'WOULD', 'COULD', 'SHOULD', 'MAY', 'MIGHT', 'MUST',
            'SHALL', 'CAN', 'FAVORABLE', 'DEFENDANT', 'PLAINTIFF',
            'FILED', 'SUIT', 'CLAIM', 'AROSE', 'CONTEXT'
        ]
        
        name_upper = name.upper()
        if any(term in name_upper for term in exclude_terms):
            return False
            
        # Check for reasonable name structure
        # At least one part should be 2+ characters (not just initials)
        if parts and not any(len(part) >= 2 for part in parts):
            return False
            
        return True
    
    @staticmethod
    def fuzzy_match_known_judges(extracted_name: str, threshold: float = 0.8) -> Optional[Tuple[str, float]]:
        """Match extracted name against known judges using fuzzy matching"""
        if not extracted_name:
            return None
            
        extracted_clean = extracted_name.upper().strip()
        best_match = None
        best_score = 0
        
        for known_judge in EnhancedJudgeExtractor.KNOWN_JUDGES:
            known_clean = known_judge.upper()
            
            # Calculate similarity
            score = SequenceMatcher(None, extracted_clean, known_clean).ratio()
            
            # Also try last name matching for higher confidence
            extracted_last = extracted_clean.split()[-1] if ' ' in extracted_clean else extracted_clean
            known_last = known_clean.split()[-1]
            last_name_score = SequenceMatcher(None, extracted_last, known_last).ratio()
            
            # Weight the scores
            combined_score = (score * 0.7) + (last_name_score * 0.3)
            
            if combined_score > best_score and combined_score >= threshold:
                best_score = combined_score
                best_match = known_judge
        
        return (best_match, best_score) if best_match else None
    
    @staticmethod
    def extract_judge_from_content(content: str, document_type: str = 'unknown') -> Dict[str, any]:
        """Main extraction method with all enhancements"""
        
        # Skip extraction for document types that don't contain judges
        if document_type in ['docket', 'recap_docket', 'civil_case']:
            return {
                'found': False,
                'reason': f'Document type {document_type} typically lacks judge signatures',
                'attempted': False
            }
        
        # Extract potential matches
        matches = EnhancedJudgeExtractor.extract_judge_patterns(content)
        
        if not matches:
            return {
                'found': False,
                'reason': 'No judge patterns matched',
                'attempted': True
            }
        
        # Sort by confidence score
        matches.sort(key=lambda x: x[2], reverse=True)
        
        # Try fuzzy matching on top candidates
        best_result = None
        for extracted_name, pattern, confidence in matches[:3]:  # Check top 3
            fuzzy_result = EnhancedJudgeExtractor.fuzzy_match_known_judges(extracted_name)
            
            if fuzzy_result:
                known_name, fuzzy_score = fuzzy_result
                combined_confidence = (confidence + (fuzzy_score * 100)) / 2
                
                if not best_result or combined_confidence > best_result['confidence']:
                    best_result = {
                        'found': True,
                        'judge_name': known_name,
                        'extracted_text': extracted_name,
                        'pattern': pattern,
                        'confidence': combined_confidence,
                        'fuzzy_matched': True,
                        'fuzzy_score': fuzzy_score
                    }
            elif not best_result or confidence > best_result.get('confidence', 0):
                # Use direct extraction if no fuzzy match
                best_result = {
                    'found': True,
                    'judge_name': extracted_name,
                    'extracted_text': extracted_name,
                    'pattern': pattern,
                    'confidence': confidence,
                    'fuzzy_matched': False
                }
        
        return best_result or {
            'found': False,
            'reason': 'Extracted names failed validation',
            'attempted': True,
            'candidates': [(n, p, c) for n, p, c in matches[:3]]
        }


# Test function
if __name__ == "__main__":
    # Test cases with OCR issues
    test_cases = [
        # Concatenated text
        "...signed by WILLIAMC.BRYSON UNITED STATES CIRCUIT JUDGE",
        # Broken words
        "...Mary Smith UNITED STATES GISTRATE JUDGE",
        # Missing spaces
        "/s/JenniferChoe-Groves U.S.DistrictJudge",
        # Garbled text
        "BY THE COURT:\n\nNothin  □□ Treo\nWILLIAMC.BRYSON\nUNITED STATES CIRCUIT JUDGE",
        # Good text
        "BY THE COURT:\n\nGregory B. Williams\nUNITED STATES DISTRICT JUDGE"
    ]
    
    for i, test_text in enumerate(test_cases):
        print(f"\nTest {i+1}:")
        result = EnhancedJudgeExtractor.extract_judge_from_content(test_text, 'opinion')
        if result['found']:
            print(f"  Found: {result['judge_name']} (confidence: {result['confidence']:.1f}%)")
            if result.get('fuzzy_matched'):
                print(f"  Fuzzy matched from: {result['extracted_text']}")
        else:
            print(f"  Not found: {result['reason']}")