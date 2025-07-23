# Part 3 of eleven_stage_pipeline_robust.py
# Continue adding to the RobustElevenStagePipeline class

    def _enhance_judge_info_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 5: Judge enhancement with validation"""
        metadata = document.get('metadata', {})
        
        # Handle metadata safely
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        elif not isinstance(metadata, dict):
            metadata = {}
        
        # Try metadata first
        judge_name = metadata.get('judge_name', '') or metadata.get('judge', '') or metadata.get('assigned_to', '')
        judge_initials = metadata.get('federal_dn_judge_initials_assigned', '')
        extracted_from_content = False
        
        # If no judge name but we have initials
        if not judge_name and judge_initials:
            return {
                'enhanced': False,
                'reason': 'Only initials available',
                'judge_initials': judge_initials,
                'judge_name_found': f"Judge {judge_initials}",
                'extracted_from_content': False
            }
        
        # If no judge in metadata, try to extract from content
        if not judge_name:
            judge_name = self._extract_judge_from_content_optimized(document.get('content', ''))
            if judge_name:
                extracted_from_content = True
        
        if not judge_name:
            return {'enhanced': False, 'reason': 'No judge name found'}
        
        # Validate judge name
        name_validation = JudgeValidator.validate_judge_name(judge_name)
        
        if not name_validation.is_valid:
            for error in name_validation.errors:
                self.error_collector.add_error(
                    ValidationError(error),
                    stage="Judge Enhancement",
                    document_id=document.get('id')
                )
            return {
                'enhanced': False,
                'reason': 'Judge name validation failed',
                'attempted_name': judge_name,
                'validation_errors': name_validation.errors
            }
        
        # Use validated/cleaned name
        judge_name = name_validation.cleaned_data
        
        try:
            # Load judge data
            judge_data_path = os.path.join(judge_pics.judge_root, 'people.json')
            
            if os.path.exists(judge_data_path):
                with open(judge_data_path, 'r') as f:
                    judges_data = json.load(f)
                
                # Search for judge
                judge_lower = judge_name.lower()
                for judge_data_item in judges_data:
                    if not isinstance(judge_data_item, dict):
                        continue
                    
                    # Handle person field which might be an ID (int) or dict
                    person_field = judge_data_item.get('person')
                    if isinstance(person_field, dict):
                        person_info = person_field
                        person_name = person_info.get('name_full', '')
                    else:
                        # Person is likely an ID, skip
                        continue
                    
                    if judge_lower in person_name.lower() or person_name.lower() in judge_lower:
                        return {
                            'enhanced': True,
                            'judge_id': person_info.get('id'),
                            'full_name': person_name,
                            'slug': person_info.get('slug'),
                            'photo_path': judge_data_item.get('path'),
                            'photo_available': True,
                            'source': 'judge-pics',
                            'extracted_from_content': extracted_from_content,
                            'validation': name_validation.to_dict()
                        }
                
                # Not found in database but name is valid
                return {
                    'enhanced': False,
                    'reason': 'Judge not found in database',
                    'attempted_name': judge_name,
                    'extracted_from_content': extracted_from_content,
                    'judge_name_found': judge_name,
                    'validation': name_validation.to_dict()
                }
            else:
                return {'enhanced': False, 'reason': 'Judge database not available'}
                
        except Exception as e:
            self.error_collector.add_error(
                e,
                stage="Judge Enhancement",
                document_id=document.get('id')
            )
            return {'enhanced': False, 'error': str(e)}
    
    def _extract_judge_from_content_optimized(self, content: str) -> Optional[str]:
        """Extract judge name from document content"""
        if not content:
            return None
        
        # Extended judge patterns
        patterns = [
            r'(?:Honorable\s+)?(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'Before:?\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)(?:,?\s+(?:Chief\s+)?(?:District\s+)?Judge)',
            r'JUDGE:\s+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'Signed\s+by\s+(?:Judge\s+)?([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+)+)',
            r'([A-Z][A-Z\s]+),?\s+UNITED STATES DISTRICT JUDGE'
        ]
        
        # Search in first 2000 characters and last 1000
        content_start = content[:2000]
        content_end = content[-1000:] if len(content) > 1000 else ""
        
        for pattern in patterns:
            # Check start
            match = re.search(pattern, content_start)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                logger.info(f"  Extracted judge from content start: {judge_name}")
                return judge_name
            
            # Check end
            match = re.search(pattern, content_end)
            if match:
                judge_name = match.group(1) if len(match.groups()) > 0 else match.group(0)
                judge_name = judge_name.strip().strip(',')
                logger.info(f"  Extracted judge from content end: {judge_name}")
                return judge_name
        
        return None
    
    def _analyze_structure(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 6: Document structure analysis"""
        content = document.get('content', '')
        
        structure = {
            'elements': [],
            'sections': 0,
            'paragraphs': 0,
            'has_footnotes': False,
            'has_citations': False
        }
        
        if not content:
            return structure
        
        # Count paragraphs (double newline separated)
        paragraphs = re.split(r'\n\s*\n', content)
        structure['paragraphs'] = len([p for p in paragraphs if p.strip()])
        
        # Look for section markers
        section_patterns = [
            r'^[IVX]+\.\s+[A-Z]',  # Roman numerals
            r'^\d+\.\s+[A-Z]',      # Numbered sections
            r'^[A-Z]\.\s+[A-Z]',    # Letter sections
        ]
        
        for para in paragraphs:
            for pattern in section_patterns:
                if re.match(pattern, para.strip()):
                    structure['sections'] += 1
                    structure['elements'].append('section')
                    break
        
        # Check for footnotes
        if re.search(r'\[\d+\]|\(\d+\)|\*\d+', content):
            structure['has_footnotes'] = True
            structure['elements'].append('footnotes')
        
        # Check for citations
        if re.search(r'\d+\s+[A-Z]\.\s*\d+[a-z]?\s+\d+', content):
            structure['has_citations'] = True
            structure['elements'].append('citations')
        
        return structure
    
    def _extract_legal_keywords(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 7: Extract legal keywords (honest about limitations)"""
        content = document.get('content', '')
        doc_type = document.get('document_type', 'unknown')
        
        extraction_result = {
            'method': 'simple_keyword_matching',
            'document_type': doc_type,
            'keywords': [],
            'legal_terms': [],
            'procedural_terms': [],
            'disclaimer': 'This is basic keyword extraction, not legal analysis'
        }
        
        if not content:
            logger.debug("No content for keyword extraction")
            return extraction_result
        
        content_lower = content.lower()
        
        # Legal keywords
        legal_keywords = [
            'summary judgment', 'motion to dismiss', 'claim construction',
            'patent infringement', 'preliminary injunction', 'class action',
            'jurisdiction', 'standing', 'damages', 'liability', 'negligence',
            'breach of contract', 'due process', 'equal protection'
        ]
        
        for keyword in legal_keywords:
            if keyword in content_lower:
                extraction_result['keywords'].append(keyword)
        
        # Legal standards
        legal_standards = {
            'de novo': 'de novo review',
            'abuse of discretion': 'abuse of discretion',
            'clear error': 'clear error',
            'arbitrary and capricious': 'arbitrary and capricious',
            'rational basis': 'rational basis review',
            'strict scrutiny': 'strict scrutiny'
        }
        
        for search_term, standard_name in legal_standards.items():
            if search_term in content_lower:
                extraction_result['legal_terms'].append(standard_name)
        
        # Procedural terms
        procedural_patterns = {
            'granted': 'motion granted',
            'denied': 'motion denied',
            'reversed': 'reversed',
            'affirmed': 'affirmed',
            'remanded': 'remanded',
            'dismissed': 'dismissed',
            'sustained': 'objection sustained',
            'overruled': 'objection overruled'
        }
        
        for term, description in procedural_patterns.items():
            if term in content_lower:
                extraction_result['procedural_terms'].append(description)
        
        # Remove duplicates
        extraction_result['keywords'] = list(set(extraction_result['keywords']))
        extraction_result['legal_terms'] = list(set(extraction_result['legal_terms']))
        extraction_result['procedural_terms'] = list(set(extraction_result['procedural_terms']))
        
        total_keywords = (
            len(extraction_result['keywords']) + 
            len(extraction_result['legal_terms']) + 
            len(extraction_result['procedural_terms'])
        )
        
        logger.info(f"Extracted {total_keywords} keywords from document")
        
        return extraction_result
    
    def _assemble_metadata_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 8: Assemble comprehensive metadata with validation"""
        
        def clean_for_json(obj):
            """Remove non-serializable objects"""
            if isinstance(obj, dict):
                return {k: clean_for_json(v) for k, v in obj.items() if not callable(v)}
            elif isinstance(obj, list):
                return [clean_for_json(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return str(obj)
            else:
                return obj
        
        # Start with original metadata
        original_metadata = document.get('metadata', {})
        if isinstance(original_metadata, str):
            try:
                original_metadata = json.loads(original_metadata)
            except:
                original_metadata = {}
        
        # Assemble all enhancements
        comprehensive = {
            'original_metadata': clean_for_json(original_metadata),
            'document_id': document.get('id'),
            'case_number': document.get('case_number'),
            'document_type': document.get('document_type'),
            'processing_timestamp': datetime.now().isoformat(),
            'enhancements': {
                'court': clean_for_json(document.get('court_enhancement', {})),
                'citations': clean_for_json(document.get('citations_extracted', {})),
                'reporters': clean_for_json(document.get('reporters_normalized', {})),
                'judge': clean_for_json(document.get('judge_enhancement', {})),
                'structure': clean_for_json(document.get('structure_analysis', {})),
                'keywords': clean_for_json(document.get('keyword_extraction', {}))
            },
            'quality_indicators': {
                'court_resolved': document.get('court_enhancement', {}).get('resolved', False),
                'citations_found': document.get('citations_extracted', {}).get('count', 0) > 0,
                'judge_identified': bool(
                    document.get('judge_enhancement', {}).get('enhanced') or
                    document.get('judge_enhancement', {}).get('judge_name_found')
                ),
                'keywords_extracted': len(document.get('keyword_extraction', {}).get('keywords', [])) > 0
            }
        }
        
        # Run final validation
        validation_result = PipelineValidator.validate_processing_result(document)
        comprehensive['validation_summary'] = validation_result.to_dict()
        
        return comprehensive