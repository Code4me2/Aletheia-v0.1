"""
Enhanced Storage Module with Docket Fetching

This module replaces the storage functionality in Stage 9 of the pipeline
to implement the 3-step traversal and save docket information.
"""

import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib

from services.courtlistener_service import CourtListenerService
from services.enhanced_ingestion_service import FieldMapper, JudgeExtractor

logger = logging.getLogger(__name__)


class EnhancedStorageProcessor:
    """Enhanced storage that fetches and saves docket information"""
    
    def __init__(self, db_conn):
        self.db_conn = db_conn
        self.cl_service = CourtListenerService()
        self.stats = {
            'dockets_fetched': 0,
            'judges_from_dockets': 0,
            'judges_updated': 0
        }
    
    async def store_with_docket_enhancement(self, documents: List[Dict[str, Any]], 
                                          force_reprocess: bool = False) -> Dict[str, Any]:
        """
        Enhanced storage that fetches docket information for better judge attribution
        
        This implements the 3-step traversal:
        1. Opinion (already have from document)
        2. Cluster (fetch if we have cluster URL)
        3. Docket (fetch if we have docket URL from cluster)
        """
        stored_count = 0
        updated_count = 0
        skipped_count = 0
        errors = []
        
        # Process documents with docket enhancement
        for doc in documents:
            try:
                # First, try to enhance with docket data
                enhanced_doc = await self._enhance_with_docket_data(doc)
                
                # Then store as before but with enhanced data
                result = await self._store_document(enhanced_doc, force_reprocess)
                
                if result == 'stored':
                    stored_count += 1
                elif result == 'updated':
                    updated_count += 1
                elif result == 'skipped':
                    skipped_count += 1
                    
            except Exception as e:
                import traceback
                logger.error(f"Error processing document {doc.get('id')}: {e}")
                logger.error(f"Traceback: {traceback.format_exc()}")
                errors.append(str(e))
        
        await self.cl_service.close()
        
        return {
            'total_processed': len(documents),
            'stored': stored_count,
            'updated': updated_count,
            'skipped': skipped_count,
            'errors': errors,
            'docket_stats': self.stats
        }
    
    async def _enhance_with_docket_data(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance document with docket data using 3-step traversal"""
        metadata = doc.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        # Check if we already have good judge info
        current_judge = doc.get('judge_enhancement', {})
        has_judge = current_judge.get('enhanced', False) and current_judge.get('full_name')
        
        # Also check metadata for judge info (from ingestion)
        if not has_judge and metadata.get('judge_name'):
            doc['judge_enhancement'] = {
                'enhanced': True,
                'full_name': metadata.get('judge_name'),
                'source': f"metadata_{metadata.get('judge_source', 'unknown')}",
                'extracted_from_content': False
            }
            has_judge = True
        
        # If we already have a judge from content extraction, we might not need docket
        # But we should still fetch docket for completeness
        
        # Check for cluster URL in metadata
        cluster_url = metadata.get('cluster')
        if not cluster_url:
            # Try to construct from cluster_id if available
            cluster_id = metadata.get('cluster_id')
            if cluster_id:
                cluster_url = f"{self.cl_service.BASE_URL}/clusters/{cluster_id}/"
        
        if cluster_url:
            try:
                session = await self.cl_service._get_session()
                
                # Step 2: Fetch cluster
                async with session.get(cluster_url, headers=self.cl_service.headers) as response:
                    if response.status == 200:
                        cluster_data = await response.json()
                        
                        # Get docket URL from cluster
                        docket_url = cluster_data.get('docket')
                        if docket_url:
                            # Step 3: Fetch docket
                            async with session.get(docket_url, headers=self.cl_service.headers) as docket_response:
                                if docket_response.status == 200:
                                    docket_data = await docket_response.json()
                                    self.stats['dockets_fetched'] += 1
                                    
                                    # Extract judge from docket
                                    judge_name, judge_source = FieldMapper.extract_judge(docket_data)
                                    
                                    if judge_name and (not has_judge or judge_source == 'assigned_to_str'):
                                        # Update judge enhancement with docket data
                                        doc['judge_enhancement'] = {
                                            'enhanced': True,
                                            'full_name': judge_name,
                                            'source': f'docket_{judge_source}',
                                            'extracted_from_content': False,
                                            'docket_fetched': True
                                        }
                                        self.stats['judges_from_dockets'] += 1
                                    
                                    # Save docket to cl_dockets table
                                    await self._save_docket(docket_data, doc)
                                    
                                    # Add docket metadata to document
                                    doc['docket_data'] = {
                                        'cl_docket_id': docket_data.get('id'),
                                        'docket_number': docket_data.get('docket_number'),
                                        'parties': self._extract_parties(docket_data),
                                        'date_terminated': docket_data.get('date_terminated')
                                    }
                                    
                                    # Also update metadata for storage
                                    metadata['cl_docket_id'] = docket_data.get('id')
                                    metadata['docket_number'] = docket_data.get('docket_number', metadata.get('docket_number'))
                                    doc['metadata'] = metadata
                                    
            except Exception as e:
                logger.warning(f"Failed to fetch docket data: {e}")
        
        # Try to extract judge from docket number if still no judge
        if not doc.get('judge_enhancement', {}).get('enhanced'):
            docket_number = metadata.get('docket_number', '')
            if docket_number:
                judge_from_pattern = JudgeExtractor.extract_from_docket_number(docket_number)
                if judge_from_pattern:
                    doc['judge_enhancement'] = {
                        'enhanced': True,
                        'full_name': judge_from_pattern,
                        'source': 'docket_number_pattern',
                        'extracted_from_content': False
                    }
        
        return doc
    
    async def _save_docket(self, docket_data: Dict, opinion_doc: Dict):
        """Save docket information to cl_dockets table"""
        try:
            with self.db_conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO court_data.cl_dockets (
                        id, court_id, case_name, case_name_short,
                        docket_number, date_filed, date_terminated,
                        assigned_to_str, cause, nature_of_suit,
                        jurisdiction_type, jury_demand, imported_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        assigned_to_str = COALESCE(EXCLUDED.assigned_to_str, cl_dockets.assigned_to_str),
                        date_terminated = COALESCE(EXCLUDED.date_terminated, cl_dockets.date_terminated),
                        updated_at = NOW()
                """, (
                    docket_data.get('id'),
                    docket_data.get('court_id', docket_data.get('court')),
                    docket_data.get('case_name'),
                    docket_data.get('case_name_short'),
                    docket_data.get('docket_number'),
                    docket_data.get('date_filed'),
                    docket_data.get('date_terminated'),
                    docket_data.get('assigned_to_str', docket_data.get('assigned_to')),
                    docket_data.get('cause'),
                    docket_data.get('nature_of_suit'),
                    docket_data.get('jurisdiction_type'),
                    docket_data.get('jury_demand')
                ))
                self.db_conn.commit()
                logger.info(f"Saved docket {docket_data.get('id')} to cl_dockets")
        except Exception as e:
            logger.error(f"Failed to save docket: {e}")
            self.db_conn.rollback()
    
    def _extract_parties(self, docket_data: Dict) -> List[str]:
        """Extract party names from docket data"""
        parties = []
        if 'parties' in docket_data:
            for party in docket_data.get('parties', []):
                if isinstance(party, dict):
                    name = party.get('name')
                    if name:
                        parties.append(name)
                elif isinstance(party, str):
                    parties.append(party)
        return parties
    
    async def _store_document(self, doc: Dict[str, Any], force_reprocess: bool) -> str:
        """Store document with enhanced judge information"""
        # Get the CourtListener opinion ID from metadata
        metadata = doc.get('metadata', {})
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except:
                metadata = {}
        
        cl_opinion_id = metadata.get('cl_opinion_id')
        if not cl_opinion_id:
            logger.warning(f"No cl_opinion_id found for document {doc.get('id')}")
            return 'skipped'
        
        # Generate hash
        content_sample = str(doc.get('content', ''))[:1000]
        doc_hash = hashlib.sha256(
            f"{cl_opinion_id}_{doc.get('case_number', '')}_{content_sample}".encode()
        ).hexdigest()
        
        # Get enhanced judge info
        judge_info = doc.get('judge_enhancement', {})
        judge_name = judge_info.get('full_name', '')
        judge_source = judge_info.get('source', '')
        
        # If no judge from enhancement, check metadata directly
        if not judge_name and metadata.get('judge_name'):
            judge_name = metadata.get('judge_name')
            judge_source = f"metadata_{metadata.get('judge_source', 'ingestion')}"
        
        # Get court info
        court_enhancement = doc.get('court_enhancement', {})
        court_id = court_enhancement.get('court_id') if court_enhancement.get('resolved') else None
        
        # Case name
        case_name = metadata.get('case_name', doc.get('case_number', f'Document-{cl_opinion_id}'))
        
        # Docket linking
        cl_docket_id = doc.get('docket_data', {}).get('cl_docket_id')
        docket_number = metadata.get('docket_number', doc.get('docket_data', {}).get('docket_number'))
        
        try:
            with self.db_conn.cursor() as cursor:
                # Check if exists
                cursor.execute("""
                    SELECT id, document_hash, assigned_judge_name 
                    FROM court_data.opinions_unified 
                    WHERE cl_id = %s
                """, (cl_opinion_id,))
                existing = cursor.fetchone()
                
                if existing:
                    existing_id, existing_hash, existing_judge = existing
                    
                    # Update if forced or changed or we have better judge info
                    if force_reprocess or existing_hash != doc_hash or (judge_name and not existing_judge):
                        cursor.execute("""
                            UPDATE court_data.opinions_unified SET
                                court_id = %s,
                                case_name = %s,
                                docket_number = %s,
                                cl_docket_id = %s,
                                assigned_judge_name = %s,
                                judge_extraction_source = %s,
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
                            docket_number,
                            cl_docket_id,
                            judge_name,
                            judge_source,
                            doc.get('content'),
                            json.dumps(doc.get('citations_extracted', {})),
                            json.dumps(judge_info),
                            json.dumps(court_enhancement),
                            json.dumps(doc.get('comprehensive_metadata', {})),
                            doc_hash,
                            datetime.now(),
                            datetime.now(),
                            cl_opinion_id
                        ))
                        
                        if judge_name and not existing_judge:
                            self.stats['judges_updated'] += 1
                            
                        self.db_conn.commit()
                        return 'updated'
                    else:
                        return 'skipped'
                else:
                    # Insert new
                    cursor.execute("""
                        INSERT INTO court_data.opinions_unified (
                            cl_id, court_id, case_name, docket_number,
                            cl_docket_id, assigned_judge_name, judge_extraction_source,
                            plain_text, citations, judge_info, court_info,
                            structured_elements, document_hash,
                            flp_processing_timestamp, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        )
                    """, (
                        cl_opinion_id,
                        court_id,
                        case_name,
                        docket_number,
                        cl_docket_id,
                        judge_name,
                        judge_source,
                        doc.get('content'),
                        json.dumps(doc.get('citations_extracted', {})),
                        json.dumps(judge_info),
                        json.dumps(court_enhancement),
                        json.dumps(doc.get('comprehensive_metadata', {})),
                        doc_hash,
                        datetime.now(),
                        datetime.now()
                    ))
                    self.db_conn.commit()
                    return 'stored'
                    
        except Exception as e:
            logger.error(f"Storage error: {e}")
            self.db_conn.rollback()
            raise