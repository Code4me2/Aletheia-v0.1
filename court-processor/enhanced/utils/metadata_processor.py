"""
Advanced Metadata Processing Module

Handles extensive metadata tagging and processing for court documents.
Designed to work with inflated metadata from pipeline tag population systems.
"""

import re
import json
import hashlib
from typing import Dict, List, Any, Optional, Set, Tuple, Union
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
import logging

from ..utils.logging import get_logger


class TagConfidenceLevel(Enum):
    """Confidence levels for metadata tags"""
    HIGH = 1.0
    MEDIUM_HIGH = 0.8
    MEDIUM = 0.6
    MEDIUM_LOW = 0.4
    LOW = 0.2


class TagSource(Enum):
    """Sources of metadata tags"""
    COURTLISTENER = "courtlistener"
    FLP_INTEGRATION = "flp_integration"
    NLP_EXTRACTION = "nlp_extraction"
    MANUAL_ANNOTATION = "manual_annotation"
    PIPELINE_POPULATION = "pipeline_population"
    STRUCTURED_DATA = "structured_data"
    CITATION_PARSER = "citation_parser"
    LEGAL_ENTITY_EXTRACTION = "legal_entity_extraction"


@dataclass
class MetadataTag:
    """Represents a single metadata tag"""
    category: str
    value: str
    confidence: float
    source: TagSource
    context: Optional[str] = None
    start_position: Optional[int] = None
    end_position: Optional[int] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "category": self.category,
            "value": self.value,
            "confidence": self.confidence,
            "source": self.source.value,
            "context": self.context,
            "start_position": self.start_position,
            "end_position": self.end_position,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetadataTag':
        """Create from dictionary"""
        return cls(
            category=data["category"],
            value=data["value"],
            confidence=data["confidence"],
            source=TagSource(data["source"]),
            context=data.get("context"),
            start_position=data.get("start_position"),
            end_position=data.get("end_position"),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat()))
        )


@dataclass
class ProcessedMetadata:
    """Container for processed metadata"""
    tags: List[MetadataTag] = field(default_factory=list)
    legal_concepts: List[str] = field(default_factory=list)
    entities: Dict[str, List[str]] = field(default_factory=dict)
    citations: List[Dict[str, Any]] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    jurisdiction_info: Dict[str, Any] = field(default_factory=dict)
    case_metadata: Dict[str, Any] = field(default_factory=dict)
    processing_stats: Dict[str, Any] = field(default_factory=dict)
    
    def get_tags_by_category(self, category: str) -> List[MetadataTag]:
        """Get all tags for a specific category"""
        return [tag for tag in self.tags if tag.category == category]
    
    def get_tags_by_source(self, source: TagSource) -> List[MetadataTag]:
        """Get all tags from a specific source"""
        return [tag for tag in self.tags if tag.source == source]
    
    def get_high_confidence_tags(self, min_confidence: float = 0.8) -> List[MetadataTag]:
        """Get tags with confidence above threshold"""
        return [tag for tag in self.tags if tag.confidence >= min_confidence]
    
    def to_elasticsearch_format(self) -> Dict[str, Any]:
        """Convert to Elasticsearch-compatible format"""
        return {
            "tags": [tag.to_dict() for tag in self.tags],
            "legal_concepts": self.legal_concepts,
            "entities": self.entities,
            "citations": self.citations,
            "topics": self.topics,
            "jurisdiction": self.jurisdiction_info,
            "case_info": self.case_metadata,
            "processing": self.processing_stats
        }


class AdvancedMetadataProcessor:
    """
    Advanced metadata processor for court documents
    
    Handles extensive metadata tagging including:
    - Legal entity extraction
    - Citation parsing and validation
    - Topic modeling and classification
    - Jurisdiction analysis
    - Procedural posture detection
    """
    
    def __init__(self):
        self.logger = get_logger("metadata_processor")
        
        # Legal patterns for entity extraction
        self._initialize_legal_patterns()
        
        # Citation patterns
        self._initialize_citation_patterns()
        
        # Legal concept mappings
        self._initialize_legal_concepts()
        
        self.logger.info("Advanced Metadata Processor initialized")
    
    def _initialize_legal_patterns(self):
        """Initialize regex patterns for legal entity extraction"""
        self.legal_patterns = {
            "case_citation": [
                r'\b\d+\s+[A-Z][a-z]*\.?\s*\d*d?\s+\d+',  # Federal citations
                r'\b\d+\s+U\.S\.\s+\d+',  # Supreme Court
                r'\b\d+\s+F\.\s*[23]?d\s+\d+',  # Federal circuits
                r'\b\d+\s+S\.\s*Ct\.\s+\d+',  # Supreme Court Reporter
            ],
            "statute": [
                r'\b\d+\s+U\.S\.C\.?\s*§?\s*\d+',  # U.S. Code
                r'\b\d+\s+C\.F\.R\.?\s*§?\s*\d+',  # Code of Federal Regulations
                r'\bRule\s+\d+\b',  # Federal Rules
            ],
            "court_name": [
                r'United States Court of Appeals',
                r'U\.S\. District Court',
                r'Supreme Court of the United States',
                r'Court of Appeals for the [A-Z][a-z]+ Circuit',
            ],
            "legal_procedure": [
                r'motion\s+(?:for\s+)?(?:summary\s+)?judgment',
                r'preliminary\s+injunction',
                r'temporary\s+restraining\s+order',
                r'cease\s+and\s+desist',
                r'discovery\s+motion',
            ],
            "legal_doctrine": [
                r'res\s+judicata',
                r'collateral\s+estoppel',
                r'burden\s+of\s+proof',
                r'standard\s+of\s+review',
                r'de\s+novo',
                r'clearly\s+erroneous',
            ]
        }
    
    def _initialize_citation_patterns(self):
        """Initialize citation parsing patterns"""
        self.citation_patterns = [
            # Federal case citations
            {
                "pattern": r'(\d+)\s+([A-Z][a-z]*\.?)\s*(\d*d?)\s+(\d+)(?:\s*\(([^)]+)\))?',
                "type": "case_citation",
                "format": "federal"
            },
            # U.S. Code citations
            {
                "pattern": r'(\d+)\s+U\.S\.C\.?\s*§?\s*(\d+(?:\([a-z]\))?)',
                "type": "statute",
                "format": "usc"
            },
            # CFR citations
            {
                "pattern": r'(\d+)\s+C\.F\.R\.?\s*§?\s*(\d+(?:\.\d+)*)',
                "type": "regulation",
                "format": "cfr"
            }
        ]
    
    def _initialize_legal_concepts(self):
        """Initialize legal concept mapping"""
        self.legal_concepts = {
            "intellectual_property": [
                "patent", "trademark", "copyright", "trade secret", "infringement",
                "prior art", "obviousness", "novelty", "claim construction"
            ],
            "contract_law": [
                "breach", "consideration", "offer", "acceptance", "damages",
                "specific performance", "unconscionable", "frustration"
            ],
            "tort_law": [
                "negligence", "liability", "causation", "damages", "duty of care",
                "strict liability", "intentional tort", "defamation"
            ],
            "civil_procedure": [
                "jurisdiction", "venue", "standing", "motion to dismiss",
                "summary judgment", "discovery", "class action"
            ],
            "criminal_law": [
                "mens rea", "actus reus", "intent", "conspiracy", "sentencing",
                "plea bargain", "miranda", "search and seizure"
            ],
            "constitutional_law": [
                "due process", "equal protection", "first amendment", "commerce clause",
                "federalism", "separation of powers", "substantive due process"
            ]
        }
    
    def process_document_metadata(self, 
                                 document: Dict[str, Any],
                                 include_nlp_extraction: bool = True,
                                 include_citation_parsing: bool = True,
                                 include_entity_extraction: bool = True) -> ProcessedMetadata:
        """
        Process comprehensive metadata for a court document
        
        Args:
            document: Court document data
            include_nlp_extraction: Whether to perform NLP-based extraction
            include_citation_parsing: Whether to parse citations
            include_entity_extraction: Whether to extract legal entities
        
        Returns:
            ProcessedMetadata object with extracted information
        """
        start_time = datetime.now()
        
        try:
            metadata = ProcessedMetadata()
            
            # Step 1: Process basic document metadata
            self._process_basic_metadata(document, metadata)
            
            # Step 2: Extract citations if requested
            if include_citation_parsing:
                self._extract_citations(document, metadata)
            
            # Step 3: Extract legal entities if requested
            if include_entity_extraction:
                self._extract_legal_entities(document, metadata)
            
            # Step 4: Perform NLP extraction if requested
            if include_nlp_extraction:
                self._perform_nlp_extraction(document, metadata)
            
            # Step 5: Process inflated metadata from pipeline
            self._process_pipeline_metadata(document, metadata)
            
            # Step 6: Derive higher-level concepts
            self._derive_legal_concepts(metadata)
            
            # Step 7: Calculate processing statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata.processing_stats = {
                "processing_time_seconds": processing_time,
                "total_tags": len(metadata.tags),
                "high_confidence_tags": len(metadata.get_high_confidence_tags()),
                "citations_found": len(metadata.citations),
                "entities_found": sum(len(entities) for entities in metadata.entities.values()),
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            self.logger.info(
                f"Processed metadata: {len(metadata.tags)} tags, "
                f"{len(metadata.citations)} citations, "
                f"{processing_time:.2f}s"
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata processing failed: {e}")
            # Return minimal metadata on error
            error_metadata = ProcessedMetadata()
            error_metadata.processing_stats = {
                "error": str(e),
                "processing_timestamp": datetime.now(timezone.utc).isoformat()
            }
            return error_metadata
    
    def _process_basic_metadata(self, document: Dict[str, Any], metadata: ProcessedMetadata):
        """Process basic document metadata from structured fields"""
        
        # Document identification tags
        if document.get('id'):
            metadata.tags.append(MetadataTag(
                category="document_id",
                value=str(document['id']),
                confidence=TagConfidenceLevel.HIGH.value,
                source=TagSource.STRUCTURED_DATA
            ))
        
        # Case information
        case_name = document.get('case_name')
        if case_name:
            metadata.tags.append(MetadataTag(
                category="case_name",
                value=case_name,
                confidence=TagConfidenceLevel.HIGH.value,
                source=TagSource.COURTLISTENER
            ))
            metadata.case_metadata['case_name'] = case_name
        
        # Court information
        court_id = document.get('court_id')
        if court_id:
            metadata.tags.append(MetadataTag(
                category="court",
                value=court_id,
                confidence=TagConfidenceLevel.HIGH.value,
                source=TagSource.COURTLISTENER
            ))
            metadata.jurisdiction_info['court_id'] = court_id
        
        # Date information
        date_filed = document.get('date_filed')
        if date_filed:
            metadata.tags.append(MetadataTag(
                category="date_filed",
                value=str(date_filed),
                confidence=TagConfidenceLevel.HIGH.value,
                source=TagSource.COURTLISTENER
            ))
            metadata.case_metadata['date_filed'] = date_filed
        
        # Judge information
        judges = document.get('judges') or document.get('assigned_to_str')
        if judges:
            for judge in self._parse_judge_names(judges):
                metadata.tags.append(MetadataTag(
                    category="judge",
                    value=judge,
                    confidence=TagConfidenceLevel.HIGH.value,
                    source=TagSource.COURTLISTENER
                ))
            
            if 'judges' not in metadata.entities:
                metadata.entities['judges'] = []
            metadata.entities['judges'].extend(self._parse_judge_names(judges))
        
        # Nature of suit / case type
        nature_of_suit = document.get('nature_of_suit')
        if nature_of_suit:
            metadata.tags.append(MetadataTag(
                category="nature_of_suit",
                value=nature_of_suit,
                confidence=TagConfidenceLevel.HIGH.value,
                source=TagSource.COURTLISTENER
            ))
            metadata.case_metadata['nature_of_suit'] = nature_of_suit
        
        # Procedural information
        procedural_history = document.get('procedural_history')
        if procedural_history:
            metadata.tags.append(MetadataTag(
                category="procedural_history",
                value=procedural_history,
                confidence=TagConfidenceLevel.MEDIUM_HIGH.value,
                source=TagSource.COURTLISTENER,
                context="full_procedural_history"
            ))
    
    def _extract_citations(self, document: Dict[str, Any], metadata: ProcessedMetadata):
        """Extract and parse legal citations from document text"""
        
        # Get text content
        content = document.get('content') or document.get('plain_text', '')
        if not content:
            return
        
        citations_found = set()  # Avoid duplicates
        
        # Use existing citations from CourtListener if available
        existing_citations = document.get('citations', [])
        for citation in existing_citations:
            if isinstance(citation, dict):
                citation_str = citation.get('citation_string', '')
                citation_type = citation.get('type', 'unknown')
            else:
                citation_str = str(citation)
                citation_type = 'unknown'
            
            if citation_str and citation_str not in citations_found:
                citations_found.add(citation_str)
                metadata.citations.append({
                    "citation": citation_str,
                    "type": citation_type,
                    "source": "courtlistener",
                    "confidence": TagConfidenceLevel.HIGH.value
                })
                
                metadata.tags.append(MetadataTag(
                    category="citation",
                    value=citation_str,
                    confidence=TagConfidenceLevel.HIGH.value,
                    source=TagSource.COURTLISTENER
                ))
        
        # Parse additional citations from text
        for pattern_info in self.citation_patterns:
            pattern = pattern_info["pattern"]
            citation_type = pattern_info["type"]
            
            for match in re.finditer(pattern, content, re.IGNORECASE):
                citation_text = match.group(0)
                
                if citation_text not in citations_found:
                    citations_found.add(citation_text)
                    
                    metadata.citations.append({
                        "citation": citation_text,
                        "type": citation_type,
                        "source": "text_extraction",
                        "confidence": TagConfidenceLevel.MEDIUM_HIGH.value,
                        "start_position": match.start(),
                        "end_position": match.end()
                    })
                    
                    metadata.tags.append(MetadataTag(
                        category="citation",
                        value=citation_text,
                        confidence=TagConfidenceLevel.MEDIUM_HIGH.value,
                        source=TagSource.CITATION_PARSER,
                        context=content[max(0, match.start()-50):match.end()+50],
                        start_position=match.start(),
                        end_position=match.end()
                    ))
    
    def _extract_legal_entities(self, document: Dict[str, Any], metadata: ProcessedMetadata):
        """Extract legal entities using pattern matching"""
        
        content = document.get('content') or document.get('plain_text', '')
        if not content:
            return
        
        for entity_type, patterns in self.legal_patterns.items():
            if entity_type not in metadata.entities:
                metadata.entities[entity_type] = []
            
            entities_found = set()
            
            for pattern in patterns:
                for match in re.finditer(pattern, content, re.IGNORECASE):
                    entity_text = match.group(0).strip()
                    
                    if entity_text and entity_text not in entities_found:
                        entities_found.add(entity_text)
                        metadata.entities[entity_type].append(entity_text)
                        
                        metadata.tags.append(MetadataTag(
                            category=f"legal_entity_{entity_type}",
                            value=entity_text,
                            confidence=TagConfidenceLevel.MEDIUM.value,
                            source=TagSource.LEGAL_ENTITY_EXTRACTION,
                            context=content[max(0, match.start()-30):match.end()+30],
                            start_position=match.start(),
                            end_position=match.end()
                        ))
    
    def _perform_nlp_extraction(self, document: Dict[str, Any], metadata: ProcessedMetadata):
        """Perform NLP-based extraction (simplified version)"""
        
        content = document.get('content') or document.get('plain_text', '')
        if not content:
            return
        
        # Simple keyword-based topic detection
        content_lower = content.lower()
        
        for topic, keywords in self.legal_concepts.items():
            matches = sum(1 for keyword in keywords if keyword.lower() in content_lower)
            
            if matches > 0:
                confidence = min(matches / len(keywords), 1.0)
                
                if confidence >= 0.1:  # Minimum threshold
                    metadata.topics.append(topic)
                    metadata.legal_concepts.extend([kw for kw in keywords if kw.lower() in content_lower])
                    
                    metadata.tags.append(MetadataTag(
                        category="legal_topic",
                        value=topic,
                        confidence=confidence,
                        source=TagSource.NLP_EXTRACTION,
                        context=f"Found {matches}/{len(keywords)} relevant terms"
                    ))
    
    def _process_pipeline_metadata(self, document: Dict[str, Any], metadata: ProcessedMetadata):
        """Process inflated metadata from pipeline tag population"""
        
        # Handle various metadata fields that might contain extensive tagging
        metadata_fields = [
            'metadata_json', 'metadata_tags', 'enhanced_metadata',
            'pipeline_tags', 'extracted_metadata', 'processed_metadata'
        ]
        
        for field in metadata_fields:
            field_data = document.get(field)
            if not field_data:
                continue
            
            try:
                # Try to parse as JSON if it's a string
                if isinstance(field_data, str):
                    try:
                        field_data = json.loads(field_data)
                    except json.JSONDecodeError:
                        # Treat as plain text metadata
                        metadata.tags.append(MetadataTag(
                            category="raw_metadata",
                            value=field_data,
                            confidence=TagConfidenceLevel.LOW.value,
                            source=TagSource.PIPELINE_POPULATION
                        ))
                        continue
                
                # Process structured metadata
                if isinstance(field_data, dict):
                    self._process_structured_metadata(field_data, metadata)
                elif isinstance(field_data, list):
                    for item in field_data:
                        if isinstance(item, dict):
                            self._process_structured_metadata(item, metadata)
                        else:
                            metadata.tags.append(MetadataTag(
                                category="pipeline_tag",
                                value=str(item),
                                confidence=TagConfidenceLevel.MEDIUM_LOW.value,
                                source=TagSource.PIPELINE_POPULATION
                            ))
                
            except Exception as e:
                self.logger.warning(f"Failed to process pipeline metadata field {field}: {e}")
    
    def _process_structured_metadata(self, data: Dict[str, Any], metadata: ProcessedMetadata):
        """Process structured metadata dictionary"""
        
        for key, value in data.items():
            if value is None:
                continue
            
            # Handle nested structures
            if isinstance(value, dict):
                for nested_key, nested_value in value.items():
                    if nested_value is not None:
                        metadata.tags.append(MetadataTag(
                            category=f"{key}_{nested_key}",
                            value=str(nested_value),
                            confidence=TagConfidenceLevel.MEDIUM.value,
                            source=TagSource.PIPELINE_POPULATION
                        ))
            
            elif isinstance(value, list):
                for item in value:
                    if item is not None:
                        metadata.tags.append(MetadataTag(
                            category=key,
                            value=str(item),
                            confidence=TagConfidenceLevel.MEDIUM.value,
                            source=TagSource.PIPELINE_POPULATION
                        ))
            
            else:
                # Simple key-value pair
                metadata.tags.append(MetadataTag(
                    category=key,
                    value=str(value),
                    confidence=TagConfidenceLevel.MEDIUM.value,
                    source=TagSource.PIPELINE_POPULATION
                ))
    
    def _derive_legal_concepts(self, metadata: ProcessedMetadata):
        """Derive higher-level legal concepts from extracted tags"""
        
        # Group related tags
        tag_categories = {}
        for tag in metadata.tags:
            if tag.category not in tag_categories:
                tag_categories[tag.category] = []
            tag_categories[tag.category].append(tag)
        
        # Derive practice areas
        practice_areas = set()
        
        if 'legal_topic' in tag_categories:
            for tag in tag_categories['legal_topic']:
                if tag.confidence >= 0.3:
                    practice_areas.add(tag.value)
        
        if 'nature_of_suit' in tag_categories:
            for tag in tag_categories['nature_of_suit']:
                # Map nature of suit to practice areas
                nos_value = tag.value.lower()
                if any(ip_term in nos_value for ip_term in ['patent', 'trademark', 'copyright']):
                    practice_areas.add('intellectual_property')
                elif any(contract_term in nos_value for contract_term in ['contract', 'breach']):
                    practice_areas.add('contract_law')
                elif any(tort_term in nos_value for tort_term in ['tort', 'negligence', 'liability']):
                    practice_areas.add('tort_law')
        
        # Add derived concepts as tags
        for area in practice_areas:
            metadata.tags.append(MetadataTag(
                category="derived_practice_area",
                value=area,
                confidence=TagConfidenceLevel.MEDIUM.value,
                source=TagSource.NLP_EXTRACTION,
                context="derived_from_multiple_indicators"
            ))
    
    def _parse_judge_names(self, judges_text: str) -> List[str]:
        """Parse judge names from text"""
        if not judges_text:
            return []
        
        # Simple parsing - split by common separators
        separators = [',', ';', ' and ', ' & ']
        judges = [judges_text]
        
        for sep in separators:
            new_judges = []
            for judge in judges:
                new_judges.extend(judge.split(sep))
            judges = new_judges
        
        # Clean up judge names
        cleaned_judges = []
        for judge in judges:
            judge = judge.strip()
            if judge and len(judge) > 2:  # Avoid single letters/initials
                # Remove common titles
                judge = re.sub(r'^(Judge|Justice|Hon\.?|Chief)\s+', '', judge, flags=re.IGNORECASE)
                cleaned_judges.append(judge)
        
        return cleaned_judges
    
    def optimize_metadata_for_search(self, metadata: ProcessedMetadata) -> Dict[str, Any]:
        """
        Optimize metadata structure for Elasticsearch search performance
        
        Creates search-optimized field mappings and reduces redundancy
        """
        
        # Group tags by category for efficient searching
        tags_by_category = {}
        for tag in metadata.tags:
            if tag.category not in tags_by_category:
                tags_by_category[tag.category] = []
            tags_by_category[tag.category].append({
                "value": tag.value,
                "confidence": tag.confidence,
                "source": tag.source.value
            })
        
        # Create searchable field mappings
        search_fields = {
            "all_judges": list(set(metadata.entities.get('judges', []))),
            "all_citations": [c["citation"] for c in metadata.citations],
            "all_topics": list(set(metadata.topics)),
            "all_legal_concepts": list(set(metadata.legal_concepts)),
            "high_confidence_tags": [
                tag.value for tag in metadata.get_high_confidence_tags()
            ],
            "categories": list(tags_by_category.keys())
        }
        
        # Create faceted search structure
        facets = {
            "practice_areas": list(set([
                tag.value for tag in metadata.tags 
                if tag.category in ["legal_topic", "derived_practice_area"]
                and tag.confidence >= 0.4
            ])),
            "courts": list(set([
                tag.value for tag in metadata.tags 
                if tag.category == "court"
            ])),
            "judges": list(set([
                tag.value for tag in metadata.tags 
                if tag.category == "judge"
            ])),
            "time_periods": [
                tag.value for tag in metadata.tags 
                if tag.category == "date_filed"
            ]
        }
        
        return {
            "structured_tags": tags_by_category,
            "search_fields": search_fields,
            "facets": facets,
            "raw_metadata": metadata.to_elasticsearch_format(),
            "optimization_stats": {
                "total_categories": len(tags_by_category),
                "searchable_fields": len(search_fields),
                "facet_categories": len(facets),
                "optimization_timestamp": datetime.now(timezone.utc).isoformat()
            }
        }


# Utility functions for metadata operations

def extract_quick_metadata(document: Dict[str, Any]) -> Dict[str, Any]:
    """Quick metadata extraction for high-volume processing"""
    processor = AdvancedMetadataProcessor()
    
    # Use faster processing options
    metadata = processor.process_document_metadata(
        document,
        include_nlp_extraction=False,
        include_citation_parsing=True,
        include_entity_extraction=False
    )
    
    return metadata.to_elasticsearch_format()


def extract_full_metadata(document: Dict[str, Any]) -> Dict[str, Any]:
    """Full metadata extraction with all features"""
    processor = AdvancedMetadataProcessor()
    
    metadata = processor.process_document_metadata(
        document,
        include_nlp_extraction=True,
        include_citation_parsing=True,
        include_entity_extraction=True
    )
    
    return processor.optimize_metadata_for_search(metadata)


def batch_process_metadata(documents: List[Dict[str, Any]], 
                          quick_mode: bool = False) -> List[Dict[str, Any]]:
    """Process metadata for a batch of documents"""
    processor = AdvancedMetadataProcessor()
    results = []
    
    for document in documents:
        try:
            if quick_mode:
                metadata = processor.process_document_metadata(
                    document,
                    include_nlp_extraction=False,
                    include_citation_parsing=True,
                    include_entity_extraction=False
                )
                result = metadata.to_elasticsearch_format()
            else:
                metadata = processor.process_document_metadata(document)
                result = processor.optimize_metadata_for_search(metadata)
            
            results.append(result)
            
        except Exception as e:
            logging.error(f"Failed to process metadata for document {document.get('id', 'unknown')}: {e}")
            results.append({"error": str(e)})
    
    return results


# Example usage
if __name__ == "__main__":
    # Example document
    sample_document = {
        "id": 12345,
        "case_name": "TechCorp v. Innovation LLC",
        "court_id": "cafc",
        "date_filed": "2024-01-15",
        "judges": "Judge Smith, Judge Johnson",
        "nature_of_suit": "Patent Infringement",
        "content": "This case involves patent infringement claims regarding U.S. Patent No. 7,123,456. The plaintiff alleges willful infringement of claims 1-3. See Smith v. Jones, 123 F.3d 456 (Fed. Cir. 2020).",
        "citations": [{"citation_string": "Smith v. Jones, 123 F.3d 456", "type": "case"}],
        "metadata_json": '{"extracted_concepts": ["patent", "infringement"], "confidence_scores": {"high": 0.9}}'
    }
    
    # Process metadata
    processor = AdvancedMetadataProcessor()
    processed = processor.process_document_metadata(sample_document)
    optimized = processor.optimize_metadata_for_search(processed)
    
    print(f"Processed {len(processed.tags)} metadata tags")
    print(f"Found {len(processed.citations)} citations")
    print(f"Identified {len(processed.topics)} legal topics")
    print(f"Extracted {sum(len(entities) for entities in processed.entities.values())} entities")