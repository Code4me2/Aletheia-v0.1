# Part 2 of eleven_stage_pipeline_robust.py
# Add this to the end of the RobustElevenStagePipeline class

    def _fetch_documents(self, limit: int, source_table: str) -> List[Dict[str, Any]]:
        """Stage 1: Fetch documents from database with validation"""
        try:
            with self.db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
                # Validate table name to prevent SQL injection
                if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*$', source_table):
                    raise ValidationError(f"Invalid table name: {source_table}")
                
                if source_table == 'public.court_documents':
                    cursor.execute("""
                        SELECT id, case_number, document_type, content, metadata, created_at
                        FROM public.court_documents
                        WHERE content IS NOT NULL AND LENGTH(content) > 100
                        ORDER BY created_at DESC
                        LIMIT %s
                    """, (limit,))
                else:
                    # For other tables, use parameterized query
                    schema, table = source_table.split('.')
                    cursor.execute("""
                        SELECT * FROM %s.%s
                        WHERE content IS NOT NULL
                        LIMIT %s
                    """, (AsIs(schema), AsIs(table), limit))
                
                return [dict(row) for row in cursor.fetchall()]
        except psycopg2.Error as e:
            raise DatabaseConnectionError(
                f"Database query failed: {str(e)}",
                stage="Document Retrieval"
            )
    
    def _enhance_court_info_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 2: Court resolution with validation"""
        metadata = document.get('metadata', {})
        
        # Handle metadata that might be a string (JSON) or other type
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                self.error_collector.add_warning(
                    "Failed to parse metadata JSON",
                    stage="Court Resolution",
                    document_id=document.get('id')
                )
                metadata = {}
        elif not isinstance(metadata, dict):
            self.error_collector.add_warning(
                f"Unexpected metadata type: {type(metadata).__name__}",
                stage="Court Resolution",
                document_id=document.get('id')
            )
            metadata = {}
        
        # Try to find court information
        court_hint = None
        extracted_from_content = False
        
        # Check metadata fields
        court_hint = metadata.get('court') or metadata.get('court_id')
        
        # Try to extract from case number
        if not court_hint:
            case_number = document.get('case_number', '')
            if case_number:
                # Extract court from case number patterns
                if ':' in case_number:
                    parts = case_number.split(':')
                    if len(parts[0]) <= 10:  # Reasonable court ID length
                        potential_court = parts[0].split('-')[0].lower()
                        if len(potential_court) >= 2:
                            court_hint = potential_court
                            extracted_from_content = True
        
        if not court_hint:
            # No court found - return unresolved status
            logger.warning(f"Could not determine court for document {document.get('id')}")
            return {
                'resolved': False,
                'reason': 'No court information found in metadata or content',
                'attempted_extraction': True,
                'search_locations': ['metadata.court', 'metadata.court_id', 'case_number pattern']
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
                'extracted_from_content': extracted_from_content,
                'validation': court_validation.to_dict()
            }
        else:
            # Invalid court ID
            for error in court_validation.errors:
                self.error_collector.add_error(
                    ValidationError(error),
                    stage="Court Resolution",
                    document_id=document.get('id')
                )
            
            return {
                'resolved': False,
                'attempted_court_id': court_hint,
                'reason': 'Court ID validation failed',
                'validation_errors': court_validation.errors,
                'validation_warnings': court_validation.warnings
            }
    
    def _extract_citations_validated(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Stage 3: Citation extraction with validation"""
        content = document.get('content', '')
        
        if not content:
            return {
                'count': 0,
                'valid_count': 0,
                'citations': [],
                'validation_summary': {'errors': 0, 'warnings': 0}
            }
        
        # Extract citations using eyecite
        citations = get_citations(content)
        
        citation_data = []
        valid_count = 0
        total_errors = 0
        total_warnings = 0
        
        for cite in citations:
            citation_dict = {
                'text': str(cite),
                'type': type(cite).__name__,
                'groups': cite.groups if hasattr(cite, 'groups') else {}
            }
            
            # Add metadata if available
            if hasattr(cite, 'metadata'):
                citation_dict['metadata'] = {
                    'plaintiff': getattr(cite.metadata, 'plaintiff', None),
                    'defendant': getattr(cite.metadata, 'defendant', None),
                    'year': getattr(cite.metadata, 'year', None),
                    'court': getattr(cite.metadata, 'court', None),
                }
            
            # Extract key citation parts
            if hasattr(cite, 'groups'):
                citation_dict.update({
                    'volume': cite.groups.get('volume'),
                    'reporter': cite.groups.get('reporter'),
                    'page': cite.groups.get('page')
                })
            
            # Validate citation
            validation_result = CitationValidator.validate_citation(citation_dict)
            citation_dict['validation'] = validation_result.to_dict()
            
            if validation_result.is_valid:
                valid_count += 1
            
            total_errors += len(validation_result.errors)
            total_warnings += len(validation_result.warnings)
            
            citation_data.append(citation_dict)
        
        logger.info(f"Extracted {len(citations)} citations, {valid_count} valid")
        
        return {
            'count': len(citations),
            'valid_count': valid_count,
            'citations': citation_data,
            'validation_summary': {
                'errors': total_errors,
                'warnings': total_warnings
            }
        }
    
    def _normalize_reporters_validated(self, citations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 4: Reporter normalization with validation"""
        normalized_reporters = []
        unique_reporters = set()
        normalized_count = 0
        
        for citation in citations:
            reporter = citation.get('reporter')
            if not reporter:
                continue
            
            # Get reporter info
            reporter_info = self._get_reporter_info(reporter)
            
            normalization = {
                'original': reporter,
                'edition': reporter_info.get('edition', reporter),
                'found': reporter_info.get('found', False),
                'name': reporter_info.get('name', ''),
                'cite_type': reporter_info.get('cite_type', '')
            }
            
            # Track if this was actually normalized (changed)
            if normalization['edition'] != normalization['original']:
                normalized_count += 1
            
            normalized_reporters.append(normalization)
            unique_reporters.add(normalization['edition'])
        
        # Validate normalization results
        validation_result = ReporterValidator.validate_reporter_normalization({
            'normalized_reporters': normalized_reporters
        })
        
        return {
            'count': len(unique_reporters),
            'normalized_count': normalized_count,
            'unique_reporters': list(unique_reporters),
            'normalized_reporters': normalized_reporters,
            'validation': validation_result.to_dict()
        }
    
    def _get_reporter_info(self, reporter: str) -> Dict[str, Any]:
        """Get reporter information with proper handling of editions"""
        # This is the fixed version from our earlier work
        reporter_clean = reporter.strip()
        
        # Handle Federal Reporter series (F., F.2d, F.3d, etc.)
        if reporter_clean.lower().startswith('f.'):
            base_key = 'F.'
            if base_key in REPORTERS:
                reporter_data = REPORTERS[base_key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    
                    # Determine edition
                    if '3d' in reporter_clean:
                        edition = 'F.3d'
                    elif '2d' in reporter_clean:
                        edition = 'F.2d'
                    elif '4th' in reporter_clean:
                        edition = 'F.4th'
                    else:
                        edition = 'F.'
                    
                    return {
                        'found': True,
                        'base_reporter': base_key,
                        'edition': edition,
                        'name': base_info.get('name', 'Federal Reporter'),
                        'cite_type': base_info.get('cite_type', 'federal')
                    }
        
        # Handle Federal Supplement
        if 'supp' in reporter_clean.lower():
            base_key = 'F. Supp.'
            if '3d' in reporter_clean.lower():
                edition = 'F. Supp. 3d'
            elif '2d' in reporter_clean.lower():
                edition = 'F. Supp. 2d'
            else:
                edition = 'F. Supp.'
            
            if base_key in REPORTERS:
                reporter_data = REPORTERS[base_key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    return {
                        'found': True,
                        'base_reporter': base_key,
                        'edition': edition,
                        'name': base_info.get('name', 'Federal Supplement'),
                        'cite_type': base_info.get('cite_type', 'federal')
                    }
        
        # Direct lookup for other reporters
        if reporter_clean in REPORTERS:
            reporter_data = REPORTERS[reporter_clean]
            if isinstance(reporter_data, list) and reporter_data:
                base_info = reporter_data[0]
                return {
                    'found': True,
                    'base_reporter': reporter_clean,
                    'edition': reporter_clean,
                    'name': base_info.get('name', ''),
                    'cite_type': base_info.get('cite_type', '')
                }
        
        # Case-insensitive lookup
        for key in REPORTERS.keys():
            if reporter_clean.lower() == key.lower():
                reporter_data = REPORTERS[key]
                if isinstance(reporter_data, list) and reporter_data:
                    base_info = reporter_data[0]
                    return {
                        'found': True,
                        'base_reporter': key,
                        'edition': key,
                        'name': base_info.get('name', ''),
                        'cite_type': base_info.get('cite_type', '')
                    }
        
        return {
            'found': False,
            'base_reporter': reporter_clean,
            'edition': reporter_clean,
            'name': '',
            'cite_type': ''
        }

# Continue with remaining methods...