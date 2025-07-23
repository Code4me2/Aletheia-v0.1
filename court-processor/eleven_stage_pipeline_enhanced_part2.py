# Part 2 of eleven_stage_pipeline_enhanced.py
# Type-specific processing methods

    async def _process_opinion_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process opinion document with opinion-specific extraction strategies"""
        doc_id = doc.get('id')
        
        # Stage 2: Opinion-specific court resolution
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 2: Court Resolution Enhancement (Opinion)")
            logger.info("=" * 60)
        
        court_info = self._enhance_court_info_opinion(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        # Continue with standard processing for other stages
        return await self._process_common_stages(doc, idx)
    
    async def _process_docket_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process docket document with docket-specific extraction strategies"""
        doc_id = doc.get('id')
        
        # Stage 2: Docket-specific court resolution
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 2: Court Resolution Enhancement (Docket)")
            logger.info("=" * 60)
        
        court_info = self._enhance_court_info_docket(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        # Continue with standard processing
        return await self._process_common_stages(doc, idx)
    
    async def _process_generic_document(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process generic/unknown document with fallback strategies"""
        # Use the original court resolution method
        court_info = self._enhance_court_info_validated(doc)
        doc['court_enhancement'] = court_info
        
        if court_info.get('resolved'):
            self.stats['courts_resolved'] += 1
        else:
            self.stats['courts_unresolved'] += 1
        
        return await self._process_common_stages(doc, idx)
    
    async def _process_common_stages(self, doc: Dict[str, Any], idx: int) -> Dict[str, Any]:
        """Process common stages for all document types"""
        doc_id = doc.get('id')
        doc_type = doc.get('detected_type', 'unknown')
        
        # Stage 3: Citation Extraction
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 3: Citation Extraction and Analysis")
            logger.info("=" * 60)
        
        citations_data = self._extract_citations_validated(doc)
        doc['citations_extracted'] = citations_data
        self.stats['citations_extracted'] += citations_data.get('count', 0)
        self.stats['citations_validated'] += citations_data.get('valid_count', 0)
        
        # Stage 4: Reporter Normalization
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 4: Reporter Normalization")
            logger.info("=" * 60)
        
        if doc['citations_extracted']['count'] > 0:
            reporters_data = self._normalize_reporters_validated(
                doc['citations_extracted']['citations']
            )
            doc['reporters_normalized'] = reporters_data
            self.stats['reporters_normalized'] += reporters_data.get('normalized_count', 0)
        else:
            doc['reporters_normalized'] = {'count': 0, 'normalized_reporters': []}
        
        # Stage 5: Judge Enhancement (type-aware)
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 5: Judge Information Enhancement")
            logger.info("=" * 60)
        
        if doc_type == 'opinion':
            judge_info = self._enhance_judge_info_opinion(doc)
        else:
            judge_info = self._enhance_judge_info_validated(doc)
        
        doc['judge_enhancement'] = judge_info
        
        if judge_info.get('enhanced'):
            self.stats['judges_enhanced'] += 1
        if judge_info.get('extracted_from_content'):
            self.stats['judges_extracted_from_content'] += 1
        
        # Stages 6-8: Standard processing
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 6: Document Structure Analysis")
            logger.info("=" * 60)
        
        structure = self._analyze_structure(doc)
        doc['structure_analysis'] = structure
        
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 7: Legal Keyword Extraction")
            logger.info("=" * 60)
        
        keyword_extraction = self._extract_legal_keywords(doc)
        doc['keyword_extraction'] = keyword_extraction
        self.stats['keywords_extracted'] += len(keyword_extraction.get('keywords', []))
        
        if idx == 0:
            logger.info("\n" + "=" * 60)
            logger.info("STAGE 8: Comprehensive Metadata Assembly")
            logger.info("=" * 60)
        
        metadata = self._assemble_metadata_validated(doc)
        doc['comprehensive_metadata'] = metadata
        
        return doc
    
    def _enhance_court_info_opinion(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced court resolution for opinion documents"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        court_hint = None
        extraction_method = None
        
        # Method 1: Extract from cluster URL
        cluster_url = metadata.get('cluster', '')
        if cluster_url and not court_hint:
            # CourtListener cluster URLs sometimes contain court info
            # We would need to fetch the cluster data via API for full info
            # For now, try to extract from the URL pattern
            logger.debug(f"Opinion has cluster URL: {cluster_url}")
            extraction_method = 'cluster_url'
        
        # Method 2: Extract from case name patterns
        case_name = metadata.get('case_name', '') or document.get('case_number', '')
        if case_name and not court_hint:
            court_hint = self._extract_court_from_case_name(case_name)
            if court_hint:
                extraction_method = 'case_name_pattern'
        
        # Method 3: Extract from content
        if not court_hint:
            content = document.get('content', '')
            court_hint = self._extract_court_from_opinion_content(content)
            if court_hint:
                extraction_method = 'content_analysis'
        
        # Method 4: Try the download URL
        download_url = metadata.get('download_url', '')
        if download_url and not court_hint:
            # Ohio Supreme Court example: supremecourt.ohio.gov
            if 'supremecourt.ohio.gov' in download_url:
                court_hint = 'ohioctapp'  # Ohio Court of Appeals
                extraction_method = 'download_url'
        
        if not court_hint:
            logger.warning(f"Could not determine court for opinion {document.get('id')}")
            return {
                'resolved': False,
                'reason': 'No court information found in opinion metadata or content',
                'attempted_methods': ['cluster_url', 'case_name_pattern', 'content_analysis', 'download_url'],
                'metadata_keys': list(metadata.keys())
            }
        
        # Validate and resolve court
        court_validation = CourtValidator.validate_court_id(court_hint)
        
        if court_validation.is_valid:
            court_data = COURTS_DICT.get(court_hint, {})
            return {
                'resolved': True,
                'court_id': court_hint,
                'court_name': court_data.get('name', ''),
                'court_citation': court_data.get('citation_string', ''),
                'court_type': court_data.get('type', ''),
                'court_level': court_data.get('level', ''),
                'extraction_method': extraction_method,
                'document_type': 'opinion',
                'validation': court_validation.to_dict()
            }
        else:
            return {
                'resolved': False,
                'attempted_court_id': court_hint,
                'reason': 'Court ID validation failed',
                'extraction_method': extraction_method,
                'validation_errors': court_validation.errors
            }
    
    def _enhance_court_info_docket(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced court resolution for docket documents"""
        # For dockets, use the standard resolution which works well
        return self._enhance_court_info_validated(document)
    
    def _extract_court_from_case_name(self, case_name: str) -> Optional[str]:
        """Extract court hints from case name patterns"""
        # Common patterns in case names
        patterns = {
            r'United States v\.': 'federal',  # Federal cases
            r'State v\.': 'state',  # State cases
            r'Commonwealth v\.': 'state',  # Commonwealth states
            r'People v\.': 'state',  # Some state cases
            r'In re': 'bankruptcy',  # Often bankruptcy or family court
        }
        
        for pattern, court_type in patterns.items():
            if re.search(pattern, case_name, re.IGNORECASE):
                logger.debug(f"Found {court_type} pattern in case name: {case_name}")
                # This gives us a hint but not a specific court ID
                # Would need more context to determine exact court
                return None
        
        return None
    
    def _extract_court_from_opinion_content(self, content: str) -> Optional[str]:
        """Extract court from opinion content patterns"""
        if not content:
            return None
        
        # Look in first 500 chars for court identification
        content_start = content[:500].upper()
        
        # Federal court patterns
        federal_patterns = [
            (r'UNITED STATES DISTRICT COURT.*?(?:FOR THE\s+)?([A-Z]+)\s+DISTRICT OF\s+([A-Z]+)', 'federal_district'),
            (r'UNITED STATES COURT OF APPEALS.*?([A-Z]+)\s+CIRCUIT', 'federal_appeals'),
            (r'SUPREME COURT OF THE UNITED STATES', 'scotus'),
        ]
        
        for pattern, court_type in federal_patterns:
            match = re.search(pattern, content_start)
            if match:
                if court_type == 'federal_district':
                    # Try to construct court ID like 'txed' for Eastern District of Texas
                    # This would need a mapping table
                    logger.debug(f"Found federal district court pattern: {match.group(0)}")
                elif court_type == 'federal_appeals':
                    # Map circuit number to court ID
                    logger.debug(f"Found federal appeals court pattern: {match.group(0)}")
                return None  # Need mapping logic
        
        # State court patterns
        state_patterns = [
            (r'SUPREME COURT OF ([A-Z]+)', 'state_supreme'),
            (r'COURT OF APPEALS OF ([A-Z]+)', 'state_appeals'),
            (r'([A-Z]+) COURT OF APPEALS', 'state_appeals'),
        ]
        
        for pattern, court_type in state_patterns:
            match = re.search(pattern, content_start)
            if match:
                state_name = match.group(1)
                logger.debug(f"Found {court_type} for state: {state_name}")
                # Would need state name to court ID mapping
                return None
        
        return None
    
    def _enhance_judge_info_opinion(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced judge extraction for opinion documents"""
        metadata = document.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # For opinions, check author fields first
        judge_name = metadata.get('author_str', '') or metadata.get('author', '')
        
        if judge_name:
            logger.info(f"Found judge in opinion author field: {judge_name}")
            return {
                'enhanced': False,
                'reason': 'Found in author metadata',
                'judge_name_found': judge_name,
                'extracted_from_author': True,
                'per_curiam': metadata.get('per_curiam', False),
                'joined_by': metadata.get('joined_by', [])
            }
        
        # Fall back to standard extraction
        return self._enhance_judge_info_validated(document)