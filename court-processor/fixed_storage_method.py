"""
Fixed storage method with proper conflict handling
"""

def _store_to_postgres_fixed(self, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Stage 9: Enhanced storage with proper conflict handling"""
    stored_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    
    try:
        with self.db_conn.cursor() as cursor:
            for doc in documents:
                try:
                    # Generate hash for deduplication
                    doc_hash = hashlib.sha256(
                        f"{doc.get('id')}_{doc.get('case_number', '')}_{doc.get('content', '')[:100]}".encode()
                    ).hexdigest()
                    
                    # Ensure all data is JSON serializable
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
                    
                    # Extract metadata safely
                    metadata = doc.get('metadata', {})
                    if not isinstance(metadata, dict):
                        metadata = {}
                    
                    # Prepare values
                    cl_id = doc.get('id')
                    court_id = doc.get('court_enhancement', {}).get('court_id')
                    case_name = metadata.get('case_name', doc.get('case_number'))
                    
                    # First check if this cl_id already exists
                    cursor.execute("""
                        SELECT id, document_hash FROM court_data.opinions_unified 
                        WHERE cl_id = %s
                    """, (cl_id,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Document exists - check if we should update
                        existing_id, existing_hash = existing
                        
                        if existing_hash != doc_hash:
                            # Content has changed, update the record
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
                                cl_id
                            ))
                            updated_count += 1
                            logger.info(f"Updated existing record for cl_id: {cl_id}")
                        else:
                            # Same content, skip
                            skipped_count += 1
                            logger.debug(f"Skipped unchanged document cl_id: {cl_id}")
                    else:
                        # New document, insert
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
                            cl_id,
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
                        logger.info(f"Stored new document cl_id: {cl_id}")
                        
                except Exception as e:
                    error_msg = f"Error storing document {doc.get('id')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    # Continue with other documents
                    continue
            
            self.db_conn.commit()
            
            total_processed = stored_count + updated_count + skipped_count
            logger.info(f"✅ Storage complete: {stored_count} new, {updated_count} updated, {skipped_count} unchanged")
            
            if errors:
                logger.warning(f"⚠️  {len(errors)} documents failed to store")
                
    except Exception as e:
        self.db_conn.rollback()
        logger.error(f"Storage transaction failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'stored_count': 0,
            'updated_count': 0,
            'skipped_count': 0,
            'errors': errors
        }
    
    return {
        'success': True,
        'stored_count': stored_count,
        'updated_count': updated_count,
        'skipped_count': skipped_count,
        'total_processed': stored_count + updated_count + skipped_count,
        'errors': errors
    }