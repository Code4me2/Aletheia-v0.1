"""
Extracted progressive enhancement patterns from flp_supplemental_api.py
Provides conflict-free document enhancement and resumable processing
"""
import logging
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class ProgressiveEnhancer:
    """
    Progressive document enhancement without conflicts
    
    Extracted from flp_supplemental_api.py for reusable enhancement patterns
    """
    
    def __init__(self, db_connection_config: Optional[Dict[str, str]] = None):
        """
        Initialize progressive enhancer
        
        Args:
            db_connection_config: Database connection parameters
        """
        self.db_config = db_connection_config
        self.enhancement_version = "1.0"
        self.enhancement_key = "flp_supplemental"  # Can be customized for different enhancement types
        
        # Track enhancement statistics
        self.stats = {
            'documents_checked': 0,
            'documents_enhanced': 0,
            'documents_skipped': 0,
            'errors': 0
        }
    
    def get_db_connection(self):
        """Get database connection"""
        if not self.db_config:
            raise ValueError("Database configuration not provided")
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def check_if_already_enhanced(self, document_metadata: Dict[str, Any]) -> bool:
        """
        Check if document has already been enhanced
        
        Args:
            document_metadata: Document metadata dictionary
            
        Returns:
            True if already enhanced, False if needs enhancement
        """
        enhancement_data = document_metadata.get(self.enhancement_key)
        
        if enhancement_data is None:
            return False
        
        # Check for enhancement version compatibility
        current_version = enhancement_data.get('enhancement_version')
        if current_version != self.enhancement_version:
            logger.debug(f"Enhancement version mismatch: {current_version} vs {self.enhancement_version}")
            return False
        
        # Check if enhancement is complete
        return enhancement_data.get('enhancement_complete', False)
    
    def mark_document_enhanced(self, 
                             document_metadata: Dict[str, Any],
                             enhancements_applied: Dict[str, Any],
                             additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Mark document as enhanced with enhancement metadata
        
        Args:
            document_metadata: Current document metadata
            enhancements_applied: Dictionary of enhancements that were applied
            additional_data: Optional additional enhancement data
            
        Returns:
            Updated metadata dictionary
        """
        enhanced_metadata = document_metadata.copy()
        
        enhancement_record = {
            'enhanced_at': datetime.now().isoformat(),
            'enhancement_version': self.enhancement_version,
            'enhancement_complete': True,
            'enhancements': enhancements_applied
        }
        
        if additional_data:
            enhancement_record.update(additional_data)
        
        enhanced_metadata[self.enhancement_key] = enhancement_record
        
        return enhanced_metadata
    
    def get_enhancement_progress(self, document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get enhancement progress for a document
        
        Args:
            document_metadata: Document metadata
            
        Returns:
            Enhancement progress information
        """
        enhancement_data = document_metadata.get(self.enhancement_key, {})
        
        return {
            'is_enhanced': self.check_if_already_enhanced(document_metadata),
            'enhanced_at': enhancement_data.get('enhanced_at'),
            'enhancement_version': enhancement_data.get('enhancement_version'),
            'enhancements_applied': enhancement_data.get('enhancements', {}),
            'enhancement_complete': enhancement_data.get('enhancement_complete', False)
        }
    
    def batch_enhance_documents(self,
                              documents: List[Dict[str, Any]],
                              enhancement_function: Callable,
                              skip_enhanced: bool = True) -> Dict[str, Any]:
        """
        Enhance multiple documents in batch with conflict avoidance
        
        Args:
            documents: List of documents to enhance
            enhancement_function: Function to apply enhancements
            skip_enhanced: Whether to skip already enhanced documents
            
        Returns:
            Enhancement results summary
        """
        results = {
            'total_documents': len(documents),
            'enhanced': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        for doc in documents:
            try:
                self.stats['documents_checked'] += 1
                
                # Check if already enhanced
                if skip_enhanced and self.check_if_already_enhanced(doc.get('metadata', {})):
                    results['skipped'] += 1
                    self.stats['documents_skipped'] += 1
                    logger.debug(f"Skipping already enhanced document: {doc.get('id')}")
                    continue
                
                # Apply enhancements
                enhanced_doc = enhancement_function(doc)
                
                if enhanced_doc:
                    results['enhanced'] += 1
                    self.stats['documents_enhanced'] += 1
                    logger.debug(f"Enhanced document: {doc.get('id')}")
                else:
                    results['errors'] += 1
                    self.stats['errors'] += 1
                    
            except Exception as e:
                results['errors'] += 1
                self.stats['errors'] += 1
                error_msg = f"Error enhancing document {doc.get('id')}: {str(e)}"
                results['error_details'].append(error_msg)
                logger.error(error_msg)
        
        return results
    
    def get_pending_enhancements(self,
                                table_name: str,
                                limit: int = 100,
                                additional_conditions: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get documents that need enhancement from database
        
        Args:
            table_name: Database table to query
            limit: Maximum documents to return
            additional_conditions: Additional WHERE conditions
            
        Returns:
            List of documents needing enhancement
        """
        try:
            conn = self.get_db_connection()
            
            with conn.cursor() as cursor:
                # Build query
                base_query = f"""
                    SELECT id, metadata, case_name, court_code, case_date
                    FROM {table_name}
                    WHERE metadata->>{self.enhancement_key!r} IS NULL
                """
                
                if additional_conditions:
                    base_query += f" AND {additional_conditions}"
                
                base_query += " ORDER BY case_date DESC LIMIT %s"
                
                cursor.execute(base_query, (limit,))
                documents = cursor.fetchall()
                
                return [dict(doc) for doc in documents]
                
        except Exception as e:
            logger.error(f"Failed to get pending enhancements: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()
    
    def update_document_enhancement(self,
                                  table_name: str,
                                  document_id: int,
                                  enhanced_metadata: Dict[str, Any]) -> bool:
        """
        Update document with enhancement metadata in database
        
        Args:
            table_name: Database table name
            document_id: Document ID
            enhanced_metadata: Updated metadata
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self.get_db_connection()
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET metadata = %s,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (json.dumps(enhanced_metadata), document_id))
                
                success = cursor.rowcount > 0
                conn.commit()
                
                if success:
                    logger.debug(f"Updated enhancement for document {document_id}")
                else:
                    logger.warning(f"No document found with ID {document_id}")
                
                return success
                
        except Exception as e:
            logger.error(f"Failed to update document enhancement: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def get_enhancement_statistics(self,
                                 table_names: List[str],
                                 enhancement_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Get enhancement statistics from database
        
        Args:
            table_names: List of table names to check
            enhancement_key: Enhancement key to check (uses instance default if None)
            
        Returns:
            Enhancement statistics
        """
        enhancement_key = enhancement_key or self.enhancement_key
        
        try:
            conn = self.get_db_connection()
            stats = {}
            
            for table_name in table_names:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(*) FILTER (WHERE metadata->>%s IS NOT NULL) as enhanced,
                            COUNT(*) FILTER (WHERE metadata->>%s IS NULL) as pending
                        FROM {table_name}
                    """, (enhancement_key, enhancement_key))
                    
                    result = cursor.fetchone()
                    stats[table_name] = dict(result)
                    
                    # Calculate percentage
                    if result['total'] > 0:
                        stats[table_name]['enhancement_percentage'] = round(
                            (result['enhanced'] / result['total']) * 100, 2
                        )
                    else:
                        stats[table_name]['enhancement_percentage'] = 0.0
            
            # Calculate overall statistics
            total_documents = sum(table_stats['total'] for table_stats in stats.values())
            total_enhanced = sum(table_stats['enhanced'] for table_stats in stats.values())
            
            stats['summary'] = {
                'total_documents': total_documents,
                'total_enhanced': total_enhanced,
                'total_pending': total_documents - total_enhanced,
                'overall_percentage': round((total_enhanced / total_documents * 100) if total_documents > 0 else 0, 2)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get enhancement statistics: {e}")
            return {'error': str(e)}
        finally:
            if 'conn' in locals():
                conn.close()
    
    def resume_from_checkpoint(self, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resume enhancement from checkpoint data
        
        Args:
            checkpoint_data: Checkpoint information
            
        Returns:
            Resume status and parameters
        """
        return {
            'last_processed_id': checkpoint_data.get('last_processed_id'),
            'last_processed_table': checkpoint_data.get('last_processed_table'),
            'enhancement_session': checkpoint_data.get('enhancement_session'),
            'resume_parameters': checkpoint_data.get('resume_parameters', {})
        }
    
    def create_checkpoint(self,
                         last_processed_id: int,
                         table_name: str,
                         session_id: str,
                         additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create checkpoint for resumable enhancement
        
        Args:
            last_processed_id: Last processed document ID
            table_name: Table being processed
            session_id: Enhancement session ID
            additional_data: Additional checkpoint data
            
        Returns:
            Checkpoint data
        """
        checkpoint = {
            'last_processed_id': last_processed_id,
            'last_processed_table': table_name,
            'enhancement_session': session_id,
            'checkpoint_created_at': datetime.now().isoformat(),
            'stats': self.stats.copy()
        }
        
        if additional_data:
            checkpoint['resume_parameters'] = additional_data
        
        return checkpoint
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get current processing statistics"""
        return {
            **self.stats,
            'success_rate': (self.stats['documents_enhanced'] / self.stats['documents_checked'] * 100) 
                           if self.stats['documents_checked'] > 0 else 0.0
        }
    
    def reset_stats(self):
        """Reset processing statistics"""
        self.stats = {
            'documents_checked': 0,
            'documents_enhanced': 0,
            'documents_skipped': 0,
            'errors': 0
        }


class ConflictAvoidanceManager:
    """
    Manages conflict avoidance during document processing
    
    Prevents duplicate processing and handles concurrent access
    """
    
    def __init__(self, db_connection_config: Dict[str, str]):
        self.db_config = db_connection_config
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def acquire_processing_lock(self,
                              document_id: int,
                              table_name: str,
                              processor_id: str,
                              lock_duration_minutes: int = 30) -> bool:
        """
        Acquire processing lock for a document
        
        Args:
            document_id: Document to lock
            table_name: Table containing document
            processor_id: Unique processor identifier
            lock_duration_minutes: Lock duration in minutes
            
        Returns:
            True if lock acquired, False otherwise
        """
        try:
            conn = self.get_db_connection()
            
            with conn.cursor() as cursor:
                # Check if already locked
                cursor.execute(f"""
                    SELECT 
                        metadata->'processing_lock'->>'processor_id' as locked_by,
                        metadata->'processing_lock'->>'locked_at' as locked_at
                    FROM {table_name}
                    WHERE id = %s
                """, (document_id,))
                
                result = cursor.fetchone()
                
                if result and result['locked_by']:
                    # Check if lock is expired
                    locked_at = datetime.fromisoformat(result['locked_at'])
                    if (datetime.now() - locked_at).total_seconds() < (lock_duration_minutes * 60):
                        logger.debug(f"Document {document_id} is locked by {result['locked_by']}")
                        return False
                
                # Acquire lock
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{{}}'),
                        '{{processing_lock}}',
                        %s
                    )
                    WHERE id = %s
                """, (json.dumps({
                    'processor_id': processor_id,
                    'locked_at': datetime.now().isoformat(),
                    'lock_duration_minutes': lock_duration_minutes
                }), document_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to acquire processing lock: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()
    
    def release_processing_lock(self,
                              document_id: int,
                              table_name: str,
                              processor_id: str) -> bool:
        """
        Release processing lock for a document
        
        Args:
            document_id: Document to unlock
            table_name: Table containing document
            processor_id: Processor identifier (must match lock owner)
            
        Returns:
            True if lock released, False otherwise
        """
        try:
            conn = self.get_db_connection()
            
            with conn.cursor() as cursor:
                cursor.execute(f"""
                    UPDATE {table_name}
                    SET metadata = metadata - 'processing_lock'
                    WHERE id = %s
                    AND metadata->'processing_lock'->>'processor_id' = %s
                """, (document_id, processor_id))
                
                conn.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Failed to release processing lock: {e}")
            return False
        finally:
            if 'conn' in locals():
                conn.close()


# Convenience functions for common enhancement patterns

def enhance_existing_documents_safe(documents: List[Dict[str, Any]],
                                  enhancement_function: Callable,
                                  enhancement_key: str = "flp_supplemental") -> Dict[str, Any]:
    """
    Safely enhance documents without conflicts
    
    Args:
        documents: Documents to enhance
        enhancement_function: Enhancement function to apply
        enhancement_key: Metadata key for enhancement tracking
        
    Returns:
        Enhancement results
    """
    enhancer = ProgressiveEnhancer()
    enhancer.enhancement_key = enhancement_key
    
    return enhancer.batch_enhance_documents(documents, enhancement_function)


def check_documents_enhancement_status(documents: List[Dict[str, Any]],
                                     enhancement_key: str = "flp_supplemental") -> Dict[str, Any]:
    """
    Check enhancement status of multiple documents
    
    Args:
        documents: Documents to check
        enhancement_key: Enhancement key to check
        
    Returns:
        Status summary
    """
    enhancer = ProgressiveEnhancer()
    enhancer.enhancement_key = enhancement_key
    
    status = {
        'total_documents': len(documents),
        'enhanced': 0,
        'pending': 0,
        'enhancement_details': []
    }
    
    for doc in documents:
        progress = enhancer.get_enhancement_progress(doc.get('metadata', {}))
        
        if progress['is_enhanced']:
            status['enhanced'] += 1
        else:
            status['pending'] += 1
        
        status['enhancement_details'].append({
            'document_id': doc.get('id'),
            'enhancement_status': progress
        })
    
    return status


def create_enhancement_metadata(enhancements_applied: Dict[str, Any],
                              enhancement_version: str = "1.0",
                              enhancement_key: str = "flp_supplemental") -> Dict[str, Any]:
    """
    Create standardized enhancement metadata
    
    Args:
        enhancements_applied: Dictionary of applied enhancements
        enhancement_version: Version of enhancement process
        enhancement_key: Metadata key for enhancement
        
    Returns:
        Enhancement metadata structure
    """
    return {
        enhancement_key: {
            'enhanced_at': datetime.now().isoformat(),
            'enhancement_version': enhancement_version,
            'enhancement_complete': True,
            'enhancements': enhancements_applied
        }
    }


# Migration helpers for existing data

def migrate_enhancement_format(old_metadata: Dict[str, Any],
                             old_key: str,
                             new_key: str = "flp_supplemental") -> Dict[str, Any]:
    """
    Migrate enhancement metadata from old format to new format
    
    Args:
        old_metadata: Existing metadata with old enhancement format
        old_key: Old enhancement key
        new_key: New enhancement key
        
    Returns:
        Migrated metadata
    """
    migrated_metadata = old_metadata.copy()
    
    if old_key in old_metadata:
        old_enhancement = old_metadata[old_key]
        
        # Convert to new format
        migrated_metadata[new_key] = {
            'enhanced_at': old_enhancement.get('processed_at', datetime.now().isoformat()),
            'enhancement_version': "1.0",
            'enhancement_complete': True,
            'enhancements': old_enhancement.get('enhancements', {}),
            'migrated_from': old_key,
            'migration_date': datetime.now().isoformat()
        }
        
        # Remove old key
        del migrated_metadata[old_key]
    
    return migrated_metadata