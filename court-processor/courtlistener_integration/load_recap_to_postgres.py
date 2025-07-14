#!/usr/bin/env python3
"""
Load RECAP documents and transcripts into PostgreSQL
Processes downloaded JSON files with transcript detection
"""

import os
import json
import glob
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import Json, execute_batch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RECAPLoader:
    """Load RECAP documents and transcripts into PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.db_url = database_url
        self.conn = None
        self.cursor = None
        self.stats = {
            'entries_processed': 0,
            'recap_docs_inserted': 0,
            'recap_docs_updated': 0,
            'transcripts_found': 0,
            'audio_inserted': 0,
            'errors': 0
        }
    
    def connect(self):
        """Connect to PostgreSQL"""
        try:
            self.conn = psycopg2.connect(self.db_url)
            self.cursor = self.conn.cursor()
            logger.info("Connected to PostgreSQL")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from PostgreSQL"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from PostgreSQL")
    
    def ensure_schema_exists(self):
        """Ensure RECAP schema is created"""
        schema_file = '/app/scripts/add_recap_schema.sql'
        if os.path.exists(schema_file):
            logger.info("Creating/updating RECAP schema...")
            with open(schema_file, 'r') as f:
                self.cursor.execute(f.read())
            self.conn.commit()
            logger.info("RECAP schema ready")
    
    def load_docket_entries(self, court_id: str, data_dir: str):
        """Load docket entries with RECAP documents"""
        # Find all entry files
        entry_files = glob.glob(f"{data_dir}/recap_documents/docket_*_entries.json")
        logger.info(f"Found {len(entry_files)} docket entry files to process")
        
        for file_path in entry_files:
            try:
                with open(file_path, 'r') as f:
                    entries = json.load(f)
                
                # Extract docket_id from filename
                filename = os.path.basename(file_path)
                docket_id = int(filename.split('_')[1])
                
                logger.info(f"Processing {len(entries)} entries for docket {docket_id}")
                
                for entry in entries:
                    self._insert_docket_entry(entry, docket_id)
                
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.conn.rollback()
                self.stats['errors'] += 1
    
    def _insert_docket_entry(self, entry: Dict, docket_id: int):
        """Insert or update a docket entry"""
        try:
            # Check if this might contain transcripts
            has_transcripts = entry.get('potential_transcript', False)
            
            entry_data = {
                'id': entry['id'],
                'docket_id': docket_id,
                'date_filed': entry.get('date_filed'),
                'entry_number': entry.get('entry_number'),
                'recap_sequence_number': entry.get('recap_sequence_number'),
                'pacer_sequence_number': entry.get('pacer_sequence_number'),
                'description': entry.get('description'),
                'short_description': entry.get('short_description'),
                'document_count': len(entry.get('recap_documents', [])),
                'has_recap_documents': bool(entry.get('recap_documents')),
                'recap_document_count': len(entry.get('recap_documents', [])),
                'raw_data': Json(entry)
            }
            
            # Insert or update
            self.cursor.execute("""
                INSERT INTO court_data.cl_docket_entries (
                    id, docket_id, date_filed, entry_number,
                    recap_sequence_number, pacer_sequence_number,
                    description, short_description, document_count,
                    has_recap_documents, recap_document_count, raw_data
                ) VALUES (
                    %(id)s, %(docket_id)s, %(date_filed)s, %(entry_number)s,
                    %(recap_sequence_number)s, %(pacer_sequence_number)s,
                    %(description)s, %(short_description)s, %(document_count)s,
                    %(has_recap_documents)s, %(recap_document_count)s, %(raw_data)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    document_count = EXCLUDED.document_count,
                    has_recap_documents = EXCLUDED.has_recap_documents,
                    recap_document_count = EXCLUDED.recap_document_count,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
            """, entry_data)
            
            self.stats['entries_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error inserting entry {entry.get('id')}: {e}")
            raise
    
    def load_recap_documents(self, court_id: str, data_dir: str):
        """Load RECAP documents including transcripts"""
        recap_files = glob.glob(f"{data_dir}/recap_documents/entry_*_recap_docs.json")
        logger.info(f"Found {len(recap_files)} RECAP document files to process")
        
        for file_path in recap_files:
            try:
                with open(file_path, 'r') as f:
                    documents = json.load(f)
                
                # Extract entry_id from filename
                filename = os.path.basename(file_path)
                entry_id = int(filename.split('_')[1])
                
                logger.info(f"Processing {len(documents)} RECAP documents for entry {entry_id}")
                
                for doc in documents:
                    self._insert_recap_document(doc, entry_id)
                
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.conn.rollback()
                self.stats['errors'] += 1
    
    def _insert_recap_document(self, doc: Dict, entry_id: int):
        """Insert or update a RECAP document"""
        try:
            # Detect if this is a transcript
            is_transcript = doc.get('is_transcript', False)
            transcript_type = doc.get('transcript_type') if is_transcript else None
            
            # Get docket_id from entry
            self.cursor.execute(
                "SELECT docket_id FROM court_data.cl_docket_entries WHERE id = %s",
                (entry_id,)
            )
            result = self.cursor.fetchone()
            docket_id = result[0] if result else None
            
            doc_data = {
                'id': doc['id'],
                'docket_entry_id': entry_id,
                'docket_id': docket_id,
                'document_number': doc.get('document_number'),
                'attachment_number': doc.get('attachment_number'),
                'pacer_doc_id': doc.get('pacer_doc_id'),
                'description': doc.get('description'),
                'short_description': doc.get('short_description'),
                'document_type': doc.get('document_type'),
                'page_count': doc.get('page_count'),
                'file_size': doc.get('file_size'),
                'filepath_local': doc.get('filepath_local'),
                'filepath_ia': doc.get('filepath_ia'),
                'sha1': doc.get('sha1'),
                'plain_text': doc.get('plain_text'),
                'ocr_status': doc.get('ocr_status'),
                'extracted_by_ocr': doc.get('extracted_by_ocr', False),
                'is_transcript': is_transcript,
                'transcript_type': transcript_type,
                'download_url': doc.get('download_url'),
                'absolute_url': doc.get('absolute_url'),
                'thumbnail': doc.get('thumbnail'),
                'date_created': doc.get('date_created'),
                'date_modified': doc.get('date_modified'),
                'date_upload': doc.get('date_upload'),
                'text_extracted': bool(doc.get('plain_text')),
                'raw_data': Json(doc)
            }
            
            # Insert or update
            self.cursor.execute("""
                INSERT INTO court_data.cl_recap_documents (
                    id, docket_entry_id, docket_id, document_number,
                    attachment_number, pacer_doc_id, description,
                    short_description, document_type, page_count,
                    file_size, filepath_local, filepath_ia, sha1,
                    plain_text, ocr_status, extracted_by_ocr,
                    is_transcript, transcript_type, download_url,
                    absolute_url, thumbnail, date_created,
                    date_modified, date_upload, text_extracted, raw_data
                ) VALUES (
                    %(id)s, %(docket_entry_id)s, %(docket_id)s, %(document_number)s,
                    %(attachment_number)s, %(pacer_doc_id)s, %(description)s,
                    %(short_description)s, %(document_type)s, %(page_count)s,
                    %(file_size)s, %(filepath_local)s, %(filepath_ia)s, %(sha1)s,
                    %(plain_text)s, %(ocr_status)s, %(extracted_by_ocr)s,
                    %(is_transcript)s, %(transcript_type)s, %(download_url)s,
                    %(absolute_url)s, %(thumbnail)s, %(date_created)s,
                    %(date_modified)s, %(date_upload)s, %(text_extracted)s, %(raw_data)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    plain_text = COALESCE(EXCLUDED.plain_text, cl_recap_documents.plain_text),
                    ocr_status = EXCLUDED.ocr_status,
                    text_extracted = EXCLUDED.text_extracted,
                    is_transcript = EXCLUDED.is_transcript,
                    transcript_type = EXCLUDED.transcript_type,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, doc_data)
            
            result = self.cursor.fetchone()
            if result[0]:
                self.stats['recap_docs_inserted'] += 1
                if is_transcript:
                    self.stats['transcripts_found'] += 1
            else:
                self.stats['recap_docs_updated'] += 1
            
        except Exception as e:
            logger.error(f"Error inserting RECAP document {doc.get('id')}: {e}")
            raise
    
    def load_audio_recordings(self, court_id: str, data_dir: str):
        """Load audio recording metadata"""
        audio_files = glob.glob(f"{data_dir}/audio/audio_page_*.json")
        logger.info(f"Found {len(audio_files)} audio files to process")
        
        for file_path in audio_files:
            try:
                with open(file_path, 'r') as f:
                    recordings = json.load(f)
                
                logger.info(f"Processing {len(recordings)} audio recordings")
                
                for audio in recordings:
                    self._insert_audio_recording(audio, court_id)
                
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.conn.rollback()
                self.stats['errors'] += 1
    
    def _insert_audio_recording(self, audio: Dict, court_id: str):
        """Insert or update an audio recording"""
        try:
            # Try to link to docket if possible
            docket_id = None
            if audio.get('docket'):
                # Extract docket ID from URL or use direct ID
                docket_ref = audio['docket']
                if isinstance(docket_ref, int):
                    docket_id = docket_ref
                elif isinstance(docket_ref, str) and docket_ref.isdigit():
                    docket_id = int(docket_ref)
            
            audio_data = {
                'id': audio['id'],
                'docket_id': docket_id,
                'case_name': audio.get('case_name'),
                'case_name_short': audio.get('case_name_short'),
                'case_name_full': audio.get('case_name_full'),
                'court_id': court_id,
                'duration': audio.get('duration'),
                'judges': audio.get('judges'),
                'sha1': audio.get('sha1'),
                'download_url': audio.get('download_url'),
                'local_path_mp3': audio.get('local_path_mp3'),
                'local_path_original': audio.get('local_path_original'),
                'filepath_ia': audio.get('filepath_ia'),
                'processing_complete': audio.get('processing_complete', False),
                'date_blocked': audio.get('date_blocked'),
                'blocked': audio.get('blocked', False),
                'date_created': audio.get('date_created'),
                'date_modified': audio.get('date_modified'),
                'raw_data': Json(audio)
            }
            
            # Insert or update
            self.cursor.execute("""
                INSERT INTO court_data.cl_audio (
                    id, docket_id, case_name, case_name_short,
                    case_name_full, court_id, duration, judges,
                    sha1, download_url, local_path_mp3,
                    local_path_original, filepath_ia,
                    processing_complete, date_blocked, blocked,
                    date_created, date_modified, raw_data
                ) VALUES (
                    %(id)s, %(docket_id)s, %(case_name)s, %(case_name_short)s,
                    %(case_name_full)s, %(court_id)s, %(duration)s, %(judges)s,
                    %(sha1)s, %(download_url)s, %(local_path_mp3)s,
                    %(local_path_original)s, %(filepath_ia)s,
                    %(processing_complete)s, %(date_blocked)s, %(blocked)s,
                    %(date_created)s, %(date_modified)s, %(raw_data)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    date_modified = EXCLUDED.date_modified,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, audio_data)
            
            result = self.cursor.fetchone()
            if result[0]:
                self.stats['audio_inserted'] += 1
                
        except Exception as e:
            logger.error(f"Error inserting audio {audio.get('id')}: {e}")
            raise
    
    def update_transcript_statistics(self):
        """Update and display transcript statistics"""
        logger.info("Updating transcript statistics...")
        
        # Get transcript counts by type
        self.cursor.execute("""
            SELECT 
                transcript_type,
                COUNT(*) as count,
                SUM(page_count) as total_pages,
                COUNT(*) FILTER (WHERE plain_text IS NOT NULL) as with_text
            FROM court_data.cl_recap_documents
            WHERE is_transcript = true
            GROUP BY transcript_type
            ORDER BY count DESC
        """)
        
        transcript_stats = self.cursor.fetchall()
        
        # Get overall statistics
        self.cursor.execute("""
            SELECT * FROM court_data.recap_stats
        """)
        
        overall_stats = self.cursor.fetchone()
        
        logger.info("=" * 70)
        logger.info("RECAP IMPORT COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Entries processed: {self.stats['entries_processed']}")
        logger.info(f"RECAP documents inserted: {self.stats['recap_docs_inserted']}")
        logger.info(f"RECAP documents updated: {self.stats['recap_docs_updated']}")
        logger.info(f"Transcripts found: {self.stats['transcripts_found']}")
        logger.info(f"Audio recordings: {self.stats['audio_inserted']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        if transcript_stats:
            logger.info("\nTranscript Breakdown:")
            for transcript_type, count, pages, with_text in transcript_stats:
                logger.info(f"  {transcript_type or 'other'}: {count} documents, "
                          f"{pages or 0} pages, {with_text} with text")
        
        if overall_stats:
            logger.info("\nOverall Database Statistics:")
            logger.info(f"  Total RECAP documents: {overall_stats[0]:,}")
            logger.info(f"  Total transcripts: {overall_stats[1]:,}")
            logger.info(f"  Documents with text: {overall_stats[2]:,}")
            logger.info(f"  Pending indexing: {overall_stats[3]:,}")
            logger.info(f"  Audio recordings: {overall_stats[4]:,}")
            logger.info(f"  Audio with transcripts: {overall_stats[5]:,}")
            logger.info(f"  Total pages: {overall_stats[6]:,}")
            logger.info(f"  Total file size: {overall_stats[7]}")
    
    def load_court_recap_data(self, court_id: str, data_dir: str = None):
        """Load all RECAP data for a specific court"""
        if data_dir is None:
            data_dir = f"/data/courtlistener/{court_id}"
        
        logger.info(f"Loading RECAP data for {court_id} from {data_dir}")
        
        try:
            self.connect()
            
            # Ensure schema exists
            self.ensure_schema_exists()
            
            # Load docket entries
            self.load_docket_entries(court_id, data_dir)
            
            # Load RECAP documents
            self.load_recap_documents(court_id, data_dir)
            
            # Load audio recordings
            self.load_audio_recordings(court_id, data_dir)
            
            # Update statistics
            self.update_transcript_statistics()
            
        finally:
            self.disconnect()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load RECAP data into PostgreSQL')
    parser.add_argument('--court', default='txed', help='Court ID to load (default: txed)')
    parser.add_argument('--data-dir', help='Data directory (default: /data/courtlistener/[court])')
    
    args = parser.parse_args()
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    # Load data
    loader = RECAPLoader(DATABASE_URL)
    loader.load_court_recap_data(args.court, args.data_dir)

if __name__ == "__main__":
    main()