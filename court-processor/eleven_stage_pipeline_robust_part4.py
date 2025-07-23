# Part 4 of eleven_stage_pipeline_robust.py
# Final methods for the RobustElevenStagePipeline class

    async def _store_enhanced_documents_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 9: Enhanced storage with validation and comprehensive error handling"""
        stored_count = 0
        updated_count = 0
        skipped_count = 0
        validation_failures = 0
        errors = []
        
        try:
            with self.db_conn.cursor() as cursor:
                for doc in documents:
                    doc_id = doc.get('id')
                    
                    try:
                        # Validate document before storage
                        validation_result = PipelineValidator.validate_processing_result(doc)
                        
                        if not validation_result.is_valid and len(validation_result.errors) > 0:
                            validation_failures += 1
                            self.error_collector.add_validation_failure(
                                validation_result.to_dict(),
                                stage="Storage Validation",
                                document_id=doc_id
                            )
                            logger.warning(f"Document {doc_id} has validation errors, storing anyway")
                        
                        # Generate hash based on content
                        content_sample = str(doc.get('content', ''))[:1000]
                        doc_hash = hashlib.sha256(
                            f"{doc_id}_{doc.get('case_number', '')}_{content_sample}".encode()
                        ).hexdigest()
                        
                        # Make data JSON serializable
                        def make_serializable(obj):
                            if isinstance(obj, dict):
                                return {k: make_serializable(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [make_serializable(item) for item in obj]
                            elif hasattr(obj, '__dict__'):
                                return str(obj)
                            elif callable(obj):
                                return None
                            else:
                                return obj
                        
                        # Extract values with validation
                        metadata = doc.get('metadata', {})
                        if not isinstance(metadata, dict):
                            metadata = {}
                        
                        court_enhancement = doc.get('court_enhancement', {})
                        court_id = court_enhancement.get('court_id') if court_enhancement.get('resolved') else None
                        case_name = metadata.get('case_name', doc.get('case_number', f'Document-{doc_id}'))
                        
                        # Check if document exists
                        cursor.execute("""
                            SELECT id, document_hash FROM court_data.opinions_unified 
                            WHERE cl_id = %s
                        """, (doc_id,))
                        existing = cursor.fetchone()
                        
                        if existing:
                            existing_id, existing_hash = existing
                            
                            if existing_hash != doc_hash:
                                # Update existing record
                                cursor.execute("""
                                    UPDATE court_data.opinions_unified SET
                                        court_id = %s,
                                        case_name = %s,
                                        plain_text = %s,
                                        citations = %s,
                                        judge_info = %s,
                                        court_info = %s,
                                        structured_elements = %s,
                                        document_hash = %s,
                                        flp_processing_timestamp = %s,
                                        updated_at = %s
                                    WHERE cl_id = %s
                                """, (
                                    court_id,
                                    case_name,
                                    doc.get('content'),
                                    json.dumps(make_serializable(doc.get('citations_extracted', {}))),
                                    json.dumps(make_serializable(doc.get('judge_enhancement', {}))),
                                    json.dumps(make_serializable(doc.get('court_enhancement', {}))),
                                    json.dumps(make_serializable(doc.get('comprehensive_metadata', {}))),
                                    doc_hash,
                                    datetime.now(),
                                    datetime.now(),
                                    doc_id
                                ))
                                updated_count += 1
                                logger.info(f"Updated existing record for cl_id: {doc_id}")
                            else:
                                skipped_count += 1
                                logger.debug(f"Skipped unchanged document cl_id: {doc_id}")
                        else:
                            # Insert new record
                            cursor.execute("""
                                INSERT INTO court_data.opinions_unified (
                                    cl_id, court_id, case_name, plain_text,
                                    citations, judge_info, court_info,
                                    structured_elements, document_hash,
                                    flp_processing_timestamp, created_at
                                ) VALUES (
                                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                                )
                            """, (
                                doc_id,
                                court_id,
                                case_name,
                                doc.get('content'),
                                json.dumps(make_serializable(doc.get('citations_extracted', {}))),
                                json.dumps(make_serializable(doc.get('judge_enhancement', {}))),
                                json.dumps(make_serializable(doc.get('court_enhancement', {}))),
                                json.dumps(make_serializable(doc.get('comprehensive_metadata', {}))),
                                doc_hash,
                                datetime.now(),
                                datetime.now()
                            ))
                            stored_count += 1
                            logger.info(f"Stored new document cl_id: {doc_id}")
                            
                    except psycopg2.IntegrityError as e:
                        if 'duplicate key value violates unique constraint' in str(e):
                            self.error_collector.add_error(
                                DuplicateDocumentError(
                                    f"Document {doc_id} already exists",
                                    document_id=doc_id
                                ),
                                stage="Storage",
                                document_id=doc_id
                            )
                            skipped_count += 1
                        else:
                            raise
                    except ValidationError as e:
                        self.error_collector.add_error(e, "Storage", doc_id)
                        errors.append(f"Validation error for {doc_id}: {str(e)}")
                    except Exception as e:
                        error_msg = f"Error storing document {doc_id}: {str(e)}"
                        logger.error(error_msg)
                        self.error_collector.add_error(
                            StorageError(error_msg, document_id=doc_id),
                            stage="Storage",
                            document_id=doc_id
                        )
                        errors.append(error_msg)
                        continue
                
                self.db_conn.commit()
                
                total_processed = stored_count + updated_count + skipped_count
                logger.info(f"✅ Storage complete: {stored_count} new, {updated_count} updated, {skipped_count} unchanged")
                
                if validation_failures > 0:
                    logger.warning(f"⚠️  {validation_failures} documents had validation issues")
                
                if errors:
                    logger.warning(f"⚠️  {len(errors)} documents failed to store")
                    
        except Exception as e:
            self.db_conn.rollback()
            logger.error(f"Storage transaction failed: {e}")
            raise StorageError(
                f"Storage transaction failed: {str(e)}",
                stage="Storage"
            )
        
        return {
            'success': True,
            'stored_count': stored_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'validation_failures': validation_failures,
            'total_processed': stored_count + updated_count + skipped_count,
            'errors': errors
        }
    
    async def _index_to_haystack_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 10: Index to Haystack with validation"""
        try:
            haystack_docs = []
            
            for doc in documents:
                # Validate document has minimum required fields
                if not doc.get('content'):
                    self.error_collector.add_warning(
                        f"Document {doc.get('id')} has no content, skipping Haystack indexing",
                        stage="Haystack Integration",
                        document_id=doc.get('id')
                    )
                    continue
                
                # Create clean metadata
                clean_metadata = {
                    'id': str(doc.get('id')),
                    'case_number': doc.get('case_number'),
                    'document_type': doc.get('document_type'),
                    'court_id': doc.get('court_enhancement', {}).get('court_id'),
                    'court_name': doc.get('court_enhancement', {}).get('court_name'),
                    'court_resolved': doc.get('court_enhancement', {}).get('resolved', False),
                    'judge_name': doc.get('judge_enhancement', {}).get('full_name', 
                                        doc.get('judge_enhancement', {}).get('judge_name_found', '')),
                    'citation_count': doc.get('citations_extracted', {}).get('count', 0),
                    'keywords': doc.get('keyword_extraction', {}).get('keywords', []),
                    'processing_timestamp': datetime.now().isoformat(),
                    'validation_passed': doc.get('comprehensive_metadata', {}).get(
                        'validation_summary', {}
                    ).get('is_valid', False)
                }
                
                haystack_doc = {
                    'content': doc.get('content', ''),
                    'meta': clean_metadata
                }
                haystack_docs.append(haystack_doc)
            
            if not haystack_docs:
                return {
                    'success': True,
                    'indexed_count': 0,
                    'message': 'No documents to index'
                }
            
            # Send to Haystack
            async with aiohttp.ClientSession() as session:
                url = f"{SERVICES['haystack']['url']}/ingest"
                
                try:
                    async with session.post(
                        url,
                        json=haystack_docs,
                        timeout=30
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"✅ Indexed {len(haystack_docs)} documents to Haystack")
                            return {
                                'success': True,
                                'indexed_count': len(haystack_docs),
                                'response': result
                            }
                        else:
                            error_text = await response.text()
                            raise HaystackError(
                                f"Haystack returned {response.status}: {error_text}",
                                stage="Haystack Integration"
                            )
                except asyncio.TimeoutError:
                    raise HaystackError(
                        "Haystack request timed out after 30 seconds",
                        stage="Haystack Integration"
                    )
                except Exception as e:
                    raise HaystackError(
                        f"Haystack integration failed: {str(e)}",
                        stage="Haystack Integration"
                    )
                    
        except HaystackError:
            raise
        except Exception as e:
            raise ExternalServiceError(
                f"Unexpected error in Haystack integration: {str(e)}",
                stage="Haystack Integration"
            )
    
    def _verify_pipeline_results_validated(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Stage 11: Comprehensive pipeline verification"""
        verification = {
            'documents_with_court_resolution': 0,
            'documents_with_valid_court': 0,
            'documents_with_citations': 0,
            'documents_with_valid_citations': 0,
            'documents_with_normalized_reporters': 0,
            'documents_with_judge_info': 0,
            'documents_with_valid_judge': 0,
            'documents_with_structure': 0,
            'documents_with_keywords': 0,
            'documents_fully_valid': 0,
            'average_enhancements_per_doc': 0,
            'completeness_score': 0,
            'quality_score': 0,
            'extraction_improvements': {
                'courts_from_content': 0,
                'judges_from_content': 0
            }
        }
        
        total_enhancements = 0
        total_quality_points = 0
        
        for doc in documents:
            doc_enhancements = 0
            doc_quality_points = 0
            
            # Court resolution
            court_data = doc.get('court_enhancement', {})
            if court_data.get('resolved'):
                verification['documents_with_court_resolution'] += 1
                doc_enhancements += 1
                
                # Check if court is valid
                if not court_data.get('validation', {}).get('errors'):
                    verification['documents_with_valid_court'] += 1
                    doc_quality_points += 2  # Higher points for valid data
                else:
                    doc_quality_points += 1
                
                if court_data.get('extracted_from_content'):
                    verification['extraction_improvements']['courts_from_content'] += 1
            
            # Citations
            citations_data = doc.get('citations_extracted', {})
            if citations_data.get('count', 0) > 0:
                verification['documents_with_citations'] += 1
                doc_enhancements += 1
                
                # Check citation validity
                if citations_data.get('valid_count', 0) > 0:
                    verification['documents_with_valid_citations'] += 1
                    valid_ratio = citations_data['valid_count'] / citations_data['count']
                    doc_quality_points += 2 * valid_ratio
                else:
                    doc_quality_points += 0.5
            
            # Normalized reporters
            if doc.get('reporters_normalized', {}).get('normalized_count', 0) > 0:
                verification['documents_with_normalized_reporters'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Judge info
            judge_data = doc.get('judge_enhancement', {})
            if judge_data.get('enhanced') or judge_data.get('judge_name_found'):
                verification['documents_with_judge_info'] += 1
                doc_enhancements += 1
                
                # Check if judge name is valid
                if not judge_data.get('validation', {}).get('errors'):
                    verification['documents_with_valid_judge'] += 1
                    doc_quality_points += 2
                else:
                    doc_quality_points += 1
                
                if judge_data.get('extracted_from_content'):
                    verification['extraction_improvements']['judges_from_content'] += 1
            
            # Structure
            if len(doc.get('structure_analysis', {}).get('elements', [])) > 0:
                verification['documents_with_structure'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Keywords
            if len(doc.get('keyword_extraction', {}).get('keywords', [])) > 0:
                verification['documents_with_keywords'] += 1
                doc_enhancements += 1
                doc_quality_points += 1
            
            # Check if document is fully valid
            validation_summary = doc.get('comprehensive_metadata', {}).get('validation_summary', {})
            if validation_summary.get('is_valid', False):
                verification['documents_fully_valid'] += 1
            
            total_enhancements += doc_enhancements
            total_quality_points += doc_quality_points
        
        # Calculate metrics
        num_docs = len(documents)
        if num_docs > 0:
            verification['average_enhancements_per_doc'] = total_enhancements / num_docs
            
            # Completeness: how many enhancements were applied
            max_enhancements = 6  # court, citations, reporters, judge, structure, keywords
            verification['completeness_score'] = (
                (verification['documents_with_court_resolution'] +
                 verification['documents_with_citations'] +
                 verification['documents_with_normalized_reporters'] +
                 verification['documents_with_judge_info'] +
                 verification['documents_with_structure'] +
                 verification['documents_with_keywords']) / 
                (num_docs * max_enhancements) * 100
            )
            
            # Quality: how good are the enhancements
            max_quality_points = 10  # Maximum quality points per document
            verification['quality_score'] = (total_quality_points / (num_docs * max_quality_points)) * 100
        
        logger.info(f"✅ Pipeline verification complete:")
        logger.info(f"   Completeness: {verification['completeness_score']:.1f}%")
        logger.info(f"   Quality: {verification['quality_score']:.1f}%")
        logger.info(f"   Valid documents: {verification['documents_fully_valid']}/{num_docs}")
        
        return verification
    
    def _calculate_quality_metrics(self) -> Dict[str, Any]:
        """Calculate overall quality metrics for the pipeline run"""
        total_docs = self.stats['documents_processed']
        
        if total_docs == 0:
            return {}
        
        return {
            'validation_rate': (self.stats['documents_validated'] / total_docs) * 100,
            'court_resolution_rate': (self.stats['courts_resolved'] / total_docs) * 100,
            'citation_extraction_rate': (self.stats['citations_extracted'] / total_docs) * 100,
            'judge_identification_rate': (
                (self.stats['judges_enhanced'] + self.stats['judges_extracted_from_content']) / 
                total_docs
            ) * 100,
            'error_rate': (self.stats['total_errors'] / total_docs) * 100,
            'data_quality_indicators': {
                'has_validation_failures': self.stats['validation_failures'] > 0,
                'has_unresolved_courts': self.stats['courts_unresolved'] > 0,
                'has_errors': self.stats['total_errors'] > 0,
                'has_warnings': self.stats['total_warnings'] > 0
            }
        }
    
    def _calculate_complexity_score(self) -> float:
        """Calculate pipeline complexity score"""
        # This is a simple metric - could be enhanced
        return 11.0  # 11 stages