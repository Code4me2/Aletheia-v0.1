"""
Legal Document Enhancer for Unstructured.io Elements

This module provides legal-specific enhancements to documents parsed by Unstructured.io.
It adds semantic understanding of legal document structures, identifies key sections,
and extracts legal-specific metadata.
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported legal document types"""
    OPINION = "opinion"
    TRANSCRIPT = "transcript"
    ORDER = "order"
    DOCKET = "docket"
    BRIEF = "brief"
    MOTION = "motion"
    UNKNOWN = "unknown"


class LegalSection(Enum):
    """Standard legal document sections"""
    CAPTION = "caption"
    PROCEDURAL_HISTORY = "procedural_history"
    FACTS = "facts"
    LEGAL_STANDARD = "legal_standard"
    ANALYSIS = "analysis"
    CONCLUSION = "conclusion"
    DISPOSITION = "disposition"
    SIGNATURE = "signature"
    FOOTNOTE = "footnote"


class LegalEvent(Enum):
    """Legal events in transcripts"""
    OBJECTION = "objection"
    RULING = "ruling"
    EXAMINATION = "examination"
    ARGUMENT = "argument"
    RECESS = "recess"
    SWEARING_IN = "swearing_in"


class LegalDocumentEnhancer:
    """
    Main class for enhancing Unstructured.io elements with legal intelligence.
    
    Usage:
        enhancer = LegalDocumentEnhancer()
        enhanced_elements = enhancer.enhance(elements, doc_type="opinion")
    """
    
    def __init__(self):
        # Initialize pattern matchers
        self._init_patterns()
        
        # Registry for custom enhancements
        self.custom_enhancers = {}
    
    def _init_patterns(self):
        """Initialize regex patterns for legal text matching"""
        
        # Speaker patterns for transcripts
        self.speaker_patterns = [
            r'^(THE COURT|JUDGE [A-Z]+|MAGISTRATE [A-Z]+):',
            r'^(MR\.|MS\.|MX\.|DR\.) [A-Z]+:',
            r'^(PLAINTIFF|DEFENDANT|COUNSEL|ATTORNEY|WITNESS):',
            r'^([A-Z][A-Z\s]+):(?=\s+[A-Z])'  # Generic all-caps speaker
        ]
        
        # Objection patterns
        self.objection_patterns = [
            r'\b(Objection|I object|We object)\b',
            r'\b(Move to strike|Motion to strike)\b',
            r'\b(Asked and answered|Hearsay|Relevance|Foundation)\b'
        ]
        
        # Ruling patterns
        self.ruling_patterns = [
            r'\b(Sustained|Overruled|Granted|Denied)\b',
            r'\b(I\'ll allow it|I\'ll sustain|I\'ll overrule)\b',
            r'\b(Motion is granted|Motion is denied)\b'
        ]
        
        # Legal standard phrases
        self.standard_phrases = [
            r'standard of review',
            r'we review.*?(de novo|for abuse of discretion|for clear error)',
            r'(plausibility|reasonableness|substantial evidence) standard',
            r'(summary judgment|motion to dismiss) standard'
        ]
        
        # Procedural history indicators
        self.procedural_indicators = [
            r'procedural (history|background|posture)',
            r'(came before|comes before) this court',
            r'on appeal from',
            r'petition for (review|writ)',
            r'(filed|brought) this action',
            r'(complaint|answer|motion) was filed'
        ]
        
        # Disposition indicators
        self.disposition_indicators = [
            r'\b(AFFIRMED|REVERSED|REMANDED|VACATED|DISMISSED)\b',
            r'\b(IT IS SO ORDERED|IT IS HEREBY ORDERED)\b',
            r'\b(judgment|order|decree) is (entered|granted|denied)\b'
        ]
        
        # Citation patterns
        self.citation_patterns = [
            r'\d+\s+F\.\d?d\s+\d+',  # Federal Reporter
            r'\d+\s+U\.S\.\s+\d+',   # US Reports
            r'\d+\s+S\.Ct\.\s+\d+',  # Supreme Court Reporter
            r'\d+\s+[A-Z][a-z]+\.?\d?d\s+\d+'  # State reporters
        ]
    
    def enhance(self, elements: List[Any], doc_type: str = None) -> List[Any]:
        """
        Main enhancement method - applies appropriate enhancements based on document type
        
        Args:
            elements: List of Unstructured.io elements
            doc_type: Type of legal document (opinion, transcript, order, etc.)
            
        Returns:
            Enhanced elements with additional legal metadata
        """
        # Auto-detect document type if not provided
        if not doc_type:
            doc_type = self._detect_document_type(elements)
        
        # Apply base enhancements to all documents
        elements = self._apply_base_enhancements(elements)
        
        # Apply document-specific enhancements
        if doc_type == DocumentType.TRANSCRIPT.value:
            elements = self._enhance_transcript(elements)
        elif doc_type == DocumentType.OPINION.value:
            elements = self._enhance_opinion(elements)
        elif doc_type == DocumentType.ORDER.value:
            elements = self._enhance_order(elements)
        elif doc_type == DocumentType.DOCKET.value:
            elements = self._enhance_docket(elements)
        elif doc_type == DocumentType.BRIEF.value:
            elements = self._enhance_brief(elements)
        elif doc_type == DocumentType.MOTION.value:
            elements = self._enhance_motion(elements)
        
        # Apply custom enhancements if registered
        if doc_type in self.custom_enhancers:
            elements = self.custom_enhancers[doc_type](elements)
        
        return elements
    
    def _detect_document_type(self, elements: List[Any]) -> str:
        """Auto-detect document type from content"""
        text_sample = " ".join([elem.text[:200] for elem in elements[:10]])
        
        # Check for transcript indicators
        if any(re.search(pattern, text_sample, re.I) for pattern in self.speaker_patterns):
            return DocumentType.TRANSCRIPT.value
        
        # Check for docket indicators
        if re.search(r'^\d+\s+\d{2}/\d{2}/\d{4}', text_sample, re.M):
            return DocumentType.DOCKET.value
        
        # Check for order indicators
        if "IT IS HEREBY ORDERED" in text_sample.upper():
            return DocumentType.ORDER.value
        
        # Check for brief indicators
        if any(phrase in text_sample.lower() for phrase in 
               ["appellant's brief", "appellee's brief", "reply brief"]):
            return DocumentType.BRIEF.value
        
        # Check for motion indicators
        if "MOTION " in text_sample.upper() and "COMES NOW" in text_sample.upper():
            return DocumentType.MOTION.value
        
        # Default to opinion
        return DocumentType.OPINION.value
    
    def _apply_base_enhancements(self, elements: List[Any]) -> List[Any]:
        """Apply enhancements common to all document types"""
        for i, elem in enumerate(elements):
            # Initialize legal metadata if not present
            if not hasattr(elem.metadata, 'legal'):
                elem.metadata.legal = {}
            
            # Track citations
            citations = re.findall('|'.join(self.citation_patterns), elem.text)
            if citations:
                elem.metadata.legal['citations'] = citations
            
            # Track exhibit references
            exhibits = re.findall(r'Exhibit\s+([A-Z0-9]+)', elem.text, re.I)
            if exhibits:
                elem.metadata.legal['exhibit_refs'] = exhibits
            
            # Detect footnote references
            footnote_refs = re.findall(r'\[(\d+)\]|\b[¹²³⁴⁵⁶⁷⁸⁹⁰]+', elem.text)
            if footnote_refs:
                elem.metadata.legal['footnote_refs'] = footnote_refs
            
            # Mark signature blocks
            if re.search(r'^/s/|^s/|^Respectfully submitted', elem.text, re.M):
                elem.metadata.legal['section'] = LegalSection.SIGNATURE.value
        
        return elements
    
    def _enhance_transcript(self, elements: List[Any]) -> List[Any]:
        """Enhance transcript-specific elements"""
        current_speaker = None
        
        for i, elem in enumerate(elements):
            # Identify speakers
            for pattern in self.speaker_patterns:
                if match := re.match(pattern, elem.text.strip()):
                    current_speaker = match.group(1)
                    elem.metadata.legal['speaker'] = current_speaker
                    elem.metadata.legal['is_speaker_label'] = True
                    break
            
            # If not a speaker label, assign current speaker
            if not elem.metadata.legal.get('is_speaker_label') and current_speaker:
                elem.metadata.legal['speaker'] = current_speaker
            
            # Detect objections
            if any(re.search(pattern, elem.text, re.I) for pattern in self.objection_patterns):
                elem.metadata.legal['event'] = LegalEvent.OBJECTION.value
                elem.metadata.legal['event_type'] = self._classify_objection(elem.text)
            
            # Detect rulings
            if any(re.search(pattern, elem.text, re.I) for pattern in self.ruling_patterns):
                elem.metadata.legal['event'] = LegalEvent.RULING.value
                elem.metadata.legal['ruling'] = self._extract_ruling(elem.text)
                
                # Link ruling to previous objection if exists
                if i > 0 and elements[i-1].metadata.legal.get('event') == LegalEvent.OBJECTION.value:
                    elem.metadata.legal['ruling_on_objection'] = True
                    elements[i-1].metadata.legal['ruling_index'] = i
            
            # Detect examination types
            if re.search(r'(DIRECT|CROSS|REDIRECT|RECROSS) EXAMINATION', elem.text, re.I):
                elem.metadata.legal['event'] = LegalEvent.EXAMINATION.value
                elem.metadata.legal['examination_type'] = re.search(
                    r'(DIRECT|CROSS|REDIRECT|RECROSS)', elem.text, re.I
                ).group(1).lower()
            
            # Detect witness swearing
            if re.search(r'(sworn|swear|oath|affirm)', elem.text, re.I):
                elem.metadata.legal['event'] = LegalEvent.SWEARING_IN.value
        
        return elements
    
    def _enhance_opinion(self, elements: List[Any]) -> List[Any]:
        """Enhance judicial opinion elements"""
        # Track current section
        current_section = None
        
        for i, elem in enumerate(elements):
            text_lower = elem.text.lower()
            
            # Identify procedural history
            if any(re.search(pattern, text_lower) for pattern in self.procedural_indicators):
                current_section = LegalSection.PROCEDURAL_HISTORY.value
                elem.metadata.legal['section'] = current_section
            
            # Identify facts section
            elif re.search(r'(statement of|background|facts|factual background)', text_lower):
                current_section = LegalSection.FACTS.value
                elem.metadata.legal['section'] = current_section
            
            # Identify legal standard
            elif any(re.search(pattern, text_lower) for pattern in self.standard_phrases):
                elem.metadata.legal['section'] = LegalSection.LEGAL_STANDARD.value
                elem.metadata.legal['standard_type'] = self._extract_standard_type(elem.text)
            
            # Identify analysis/discussion
            elif re.search(r'(discussion|analysis|merits)', text_lower):
                current_section = LegalSection.ANALYSIS.value
                elem.metadata.legal['section'] = current_section
            
            # Identify conclusion/disposition
            elif any(re.search(pattern, elem.text, re.I) for pattern in self.disposition_indicators):
                elem.metadata.legal['section'] = LegalSection.DISPOSITION.value
                elem.metadata.legal['disposition'] = self._extract_disposition(elem.text)
            
            # Assign current section if not specifically identified
            elif current_section and not elem.metadata.legal.get('section'):
                elem.metadata.legal['section'] = current_section
            
            # Track section headings
            if elem.category in ['Title', 'Header'] and len(elem.text) < 100:
                elem.metadata.legal['is_section_heading'] = True
                
                # Roman numeral sections
                if re.match(r'^[IVX]+\.?\s+', elem.text):
                    elem.metadata.legal['section_number'] = re.match(r'^([IVX]+)', elem.text).group(1)
        
        return elements
    
    def _enhance_order(self, elements: List[Any]) -> List[Any]:
        """Enhance court order elements"""
        order_sections = {
            'findings': False,
            'conclusions': False,
            'order': False
        }
        
        current_section = 'introduction'
        
        for elem in elements:
            text_upper = elem.text.upper()
            
            # Detect findings of fact
            if 'FINDINGS OF FACT' in text_upper:
                current_section = 'findings'
                order_sections['findings'] = True
                elem.metadata.legal['section'] = 'findings_header'
            
            # Detect conclusions of law
            elif 'CONCLUSIONS OF LAW' in text_upper:
                current_section = 'conclusions'
                order_sections['conclusions'] = True
                elem.metadata.legal['section'] = 'conclusions_header'
            
            # Detect order section
            elif 'IT IS HEREBY ORDERED' in text_upper or 'IT IS SO ORDERED' in text_upper:
                current_section = 'order'
                order_sections['order'] = True
                elem.metadata.legal['section'] = 'order_start'
            
            # Assign section
            elem.metadata.legal['order_section'] = current_section
            
            # Number findings and conclusions
            if current_section in ['findings', 'conclusions']:
                if match := re.match(r'^(\d+)\.\s+', elem.text):
                    elem.metadata.legal[f'{current_section}_number'] = int(match.group(1))
        
        return elements
    
    def _enhance_docket(self, elements: List[Any]) -> List[Any]:
        """Enhance docket entry elements"""
        for elem in elements:
            # Parse docket entries
            if match := re.match(r'^(\d+)\s+(\d{1,2}/\d{1,2}/\d{2,4})\s+(.*)', elem.text):
                elem.metadata.legal['docket_number'] = int(match.group(1))
                elem.metadata.legal['entry_date'] = match.group(2)
                elem.metadata.legal['entry_text'] = match.group(3)
                elem.metadata.legal['entry_type'] = self._classify_docket_entry(match.group(3))
            
            # Detect filed documents
            if 'filed' in elem.text.lower():
                docs = re.findall(r'(motion|brief|complaint|answer|reply|response)', 
                                elem.text, re.I)
                if docs:
                    elem.metadata.legal['filed_documents'] = docs
            
            # Extract case numbers
            case_patterns = [
                r'\b\d{2}-cv-\d{4,5}\b',
                r'\b\d{2}-cr-\d{4,5}\b',
                r'\b\d{4}WL\d{6,}\b'
            ]
            for pattern in case_patterns:
                if matches := re.findall(pattern, elem.text):
                    elem.metadata.legal['case_numbers'] = matches
        
        return elements
    
    def _enhance_brief(self, elements: List[Any]) -> List[Any]:
        """Enhance legal brief elements"""
        current_section = None
        
        for elem in elements:
            text_lower = elem.text.lower()
            
            # Standard brief sections
            brief_sections = {
                'table of contents': 'toc',
                'table of authorities': 'toa',
                'statement of the case': 'statement',
                'statement of facts': 'facts',
                'summary of argument': 'summary',
                'argument': 'argument',
                'conclusion': 'conclusion'
            }
            
            for section_name, section_code in brief_sections.items():
                if section_name in text_lower:
                    current_section = section_code
                    elem.metadata.legal['section'] = current_section
                    elem.metadata.legal['is_section_header'] = True
                    break
            
            # Assign current section
            if current_section and not elem.metadata.legal.get('section'):
                elem.metadata.legal['section'] = current_section
            
            # Track argument headings
            if current_section == 'argument' and elem.category in ['Title', 'Header']:
                if match := re.match(r'^([IVX]+|\d+)\.\s+(.+)', elem.text):
                    elem.metadata.legal['argument_number'] = match.group(1)
                    elem.metadata.legal['argument_heading'] = match.group(2)
        
        return elements
    
    def _enhance_motion(self, elements: List[Any]) -> List[Any]:
        """Enhance motion elements"""
        motion_type = None
        
        for elem in elements:
            # Detect motion type
            if 'MOTION' in elem.text.upper():
                motion_types = [
                    'dismiss', 'summary judgment', 'limine', 'compel',
                    'protective order', 'sanctions', 'reconsideration'
                ]
                for mtype in motion_types:
                    if mtype in elem.text.lower():
                        motion_type = mtype
                        elem.metadata.legal['motion_type'] = motion_type
                        break
            
            # Track relief requested
            if re.search(r'(request|pray|seek|move)', elem.text, re.I):
                elem.metadata.legal['contains_relief_request'] = True
            
            # Mark memorandum sections
            if 'MEMORANDUM' in elem.text.upper():
                elem.metadata.legal['is_memorandum'] = True
        
        return elements
    
    # Helper methods for extraction
    def _classify_objection(self, text: str) -> str:
        """Classify type of objection"""
        objection_types = {
            'hearsay': r'\bhearsay\b',
            'relevance': r'\brelevan(ce|t)\b',
            'foundation': r'\bfoundation\b',
            'speculation': r'\bspeculat',
            'asked_and_answered': r'asked and answered',
            'argumentative': r'\bargumentative\b',
            'compound': r'\bcompound\b',
            'narrative': r'\bnarrative\b'
        }
        
        for obj_type, pattern in objection_types.items():
            if re.search(pattern, text, re.I):
                return obj_type
        
        return 'general'
    
    def _extract_ruling(self, text: str) -> str:
        """Extract ruling from text"""
        for pattern in self.ruling_patterns:
            if match := re.search(pattern, text, re.I):
                return match.group(0).lower()
        return 'unknown'
    
    def _extract_standard_type(self, text: str) -> str:
        """Extract type of legal standard"""
        standards = {
            'de_novo': r'de novo',
            'abuse_of_discretion': r'abuse of discretion',
            'clear_error': r'clear error',
            'substantial_evidence': r'substantial evidence',
            'plausibility': r'plausibility',
            'summary_judgment': r'summary judgment'
        }
        
        for std_type, pattern in standards.items():
            if re.search(pattern, text, re.I):
                return std_type
        
        return 'other'
    
    def _extract_disposition(self, text: str) -> str:
        """Extract case disposition"""
        dispositions = ['affirmed', 'reversed', 'remanded', 'vacated', 'dismissed']
        
        for disposition in dispositions:
            if disposition in text.lower():
                return disposition
        
        return 'other'
    
    def _classify_docket_entry(self, entry_text: str) -> str:
        """Classify type of docket entry"""
        entry_types = {
            'filing': r'(filed|filing)',
            'order': r'\border\b',
            'motion': r'\bmotion\b',
            'notice': r'\bnotice\b',
            'minute_entry': r'minute entry',
            'judgment': r'\bjudgment\b',
            'stipulation': r'\bstipulat'
        }
        
        for entry_type, pattern in entry_types.items():
            if re.search(pattern, entry_text, re.I):
                return entry_type
        
        return 'other'
    
    def register_custom_enhancer(self, doc_type: str, enhancer_func):
        """
        Register a custom enhancement function for a document type
        
        Args:
            doc_type: Document type to enhance
            enhancer_func: Function that takes elements and returns enhanced elements
        """
        self.custom_enhancers[doc_type] = enhancer_func
        logger.info(f"Registered custom enhancer for {doc_type}")


# Convenience function
def enhance_legal_document(elements: List[Any], doc_type: str = None) -> List[Any]:
    """
    Quick function to enhance legal documents
    
    Args:
        elements: Unstructured.io elements
        doc_type: Type of document (optional, will auto-detect)
    
    Returns:
        Enhanced elements with legal metadata
    """
    enhancer = LegalDocumentEnhancer()
    return enhancer.enhance(elements, doc_type)