#!/usr/bin/env python3
"""
Load CourtListener JSON data into PostgreSQL
Processes downloaded JSON files and inserts into court_data schema
"""

import os
import json
import glob
import logging
from datetime import datetime
from typing import Dict, List, Optional
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

class CourtListenerLoader:
    """Load CourtListener JSON data into PostgreSQL"""
    
    def __init__(self, database_url: str):
        self.db_url = database_url
        self.conn = None
        self.cursor = None
        self.stats = {
            'dockets_inserted': 0,
            'dockets_updated': 0,
            'opinions_inserted': 0,
            'opinions_updated': 0,
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
    
    def load_dockets(self, court_id: str, data_dir: str):
        """Load docket JSON files into cl_dockets table"""
        docket_files = sorted(glob.glob(f"{data_dir}/dockets_page_*.json"))
        logger.info(f"Found {len(docket_files)} docket files to process")
        
        for file_path in docket_files:
            try:
                with open(file_path, 'r') as f:
                    dockets = json.load(f)
                
                logger.info(f"Processing {len(dockets)} dockets from {os.path.basename(file_path)}")
                
                for docket in dockets:
                    self._insert_docket(docket, court_id)
                
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.conn.rollback()
                self.stats['errors'] += 1
    
    def _insert_docket(self, docket: Dict, court_id: str):
        """Insert or update a single docket"""
        try:
            # Detect if it's a patent case
            is_patent = self._is_patent_case(docket)
            
            # Prepare data
            docket_data = {
                'id': docket['id'],
                'court_id': court_id,
                'case_name': docket.get('case_name'),
                'case_name_short': docket.get('case_name_short'),
                'case_name_full': docket.get('case_name_full'),
                'docket_number': docket.get('docket_number'),
                'docket_number_core': docket.get('docket_number_core'),
                'date_filed': docket.get('date_filed'),
                'date_terminated': docket.get('date_terminated'),
                'date_last_filing': docket.get('date_last_filing'),
                'date_created': docket.get('date_created'),
                'date_modified': docket.get('date_modified'),
                'nature_of_suit': docket.get('nature_of_suit'),
                'cause': docket.get('cause'),
                'jury_demand': docket.get('jury_demand'),
                'jurisdiction_type': docket.get('jurisdiction_type'),
                'assigned_to_str': docket.get('assigned_to_str'),
                'referred_to_str': docket.get('referred_to_str'),
                'source': docket.get('source'),
                'pacer_case_id': docket.get('pacer_case_id'),
                'filepath_ia': docket.get('filepath_ia'),
                'filepath_local': docket.get('filepath_local'),
                'absolute_url': docket.get('absolute_url'),
                'docket_entries_url': docket.get('docket_entries'),
                'is_patent_case': is_patent,
                'raw_data': Json(docket)
            }
            
            # Insert or update
            self.cursor.execute("""
                INSERT INTO court_data.cl_dockets (
                    id, court_id, case_name, case_name_short, case_name_full,
                    docket_number, docket_number_core, date_filed, date_terminated,
                    date_last_filing, date_created, date_modified, nature_of_suit,
                    cause, jury_demand, jurisdiction_type, assigned_to_str,
                    referred_to_str, source, pacer_case_id, filepath_ia,
                    filepath_local, absolute_url, docket_entries_url,
                    is_patent_case, raw_data
                ) VALUES (
                    %(id)s, %(court_id)s, %(case_name)s, %(case_name_short)s, %(case_name_full)s,
                    %(docket_number)s, %(docket_number_core)s, %(date_filed)s, %(date_terminated)s,
                    %(date_last_filing)s, %(date_created)s, %(date_modified)s, %(nature_of_suit)s,
                    %(cause)s, %(jury_demand)s, %(jurisdiction_type)s, %(assigned_to_str)s,
                    %(referred_to_str)s, %(source)s, %(pacer_case_id)s, %(filepath_ia)s,
                    %(filepath_local)s, %(absolute_url)s, %(docket_entries_url)s,
                    %(is_patent_case)s, %(raw_data)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    date_modified = EXCLUDED.date_modified,
                    date_last_filing = EXCLUDED.date_last_filing,
                    date_terminated = EXCLUDED.date_terminated,
                    is_patent_case = EXCLUDED.is_patent_case,
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, docket_data)
            
            result = self.cursor.fetchone()
            if result[0]:
                self.stats['dockets_inserted'] += 1
            else:
                self.stats['dockets_updated'] += 1
            
        except Exception as e:
            logger.error(f"Error inserting docket {docket.get('id')}: {e}")
            raise
    
    def load_opinions(self, court_id: str, data_dir: str):
        """Load opinion JSON files into cl_opinions table"""
        opinion_files = sorted(glob.glob(f"{data_dir}/opinions_page_*.json"))
        logger.info(f"Found {len(opinion_files)} opinion files to process")
        
        for file_path in opinion_files:
            try:
                with open(file_path, 'r') as f:
                    opinions = json.load(f)
                
                logger.info(f"Processing {len(opinions)} opinions from {os.path.basename(file_path)}")
                
                for opinion in opinions:
                    self._insert_opinion(opinion)
                
                self.conn.commit()
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                self.conn.rollback()
                self.stats['errors'] += 1
    
    def _insert_opinion(self, opinion: Dict):
        """Insert or update a single opinion"""
        try:
            # Extract cluster ID from URL if present
            cluster_url = opinion.get('cluster')
            cluster_id = None
            if cluster_url and isinstance(cluster_url, str):
                parts = cluster_url.rstrip('/').split('/')
                if parts:
                    try:
                        cluster_id = int(parts[-1])
                    except ValueError:
                        pass
            
            # Prepare data
            opinion_data = {
                'id': opinion['id'],
                'cluster_id': cluster_id,
                'author_str': opinion.get('author_str'),
                'author_id': opinion.get('author_id'),
                'per_curiam': opinion.get('per_curiam', False),
                'joined_by_str': opinion.get('joined_by_str'),
                'type': opinion.get('type'),
                'sha1': opinion.get('sha1'),
                'page_count': opinion.get('page_count'),
                'plain_text': opinion.get('plain_text'),
                'html': opinion.get('html'),
                'html_lawbox': opinion.get('html_lawbox'),
                'html_columbia': opinion.get('html_columbia'),
                'html_anon_2020': opinion.get('html_anon_2020'),
                'html_with_citations': opinion.get('html_with_citations'),
                'xml_harvard': opinion.get('xml_harvard'),
                'download_url': opinion.get('download_url'),
                'local_path': opinion.get('local_path'),
                'absolute_url': opinion.get('absolute_url'),
                'opinions_cited': Json(opinion.get('opinions_cited', [])),
                'extracted_by_ocr': opinion.get('extracted_by_ocr', False),
                'date_created': opinion.get('date_created'),
                'date_modified': opinion.get('date_modified'),
                'raw_data': Json(opinion)
            }
            
            # Insert or update
            self.cursor.execute("""
                INSERT INTO court_data.cl_opinions (
                    id, cluster_id, author_str, author_id, per_curiam,
                    joined_by_str, type, sha1, page_count, plain_text,
                    html, html_lawbox, html_columbia, html_anon_2020,
                    html_with_citations, xml_harvard, download_url,
                    local_path, absolute_url, opinions_cited,
                    extracted_by_ocr, date_created, date_modified, raw_data
                ) VALUES (
                    %(id)s, %(cluster_id)s, %(author_str)s, %(author_id)s, %(per_curiam)s,
                    %(joined_by_str)s, %(type)s, %(sha1)s, %(page_count)s, %(plain_text)s,
                    %(html)s, %(html_lawbox)s, %(html_columbia)s, %(html_anon_2020)s,
                    %(html_with_citations)s, %(xml_harvard)s, %(download_url)s,
                    %(local_path)s, %(absolute_url)s, %(opinions_cited)s,
                    %(extracted_by_ocr)s, %(date_created)s, %(date_modified)s, %(raw_data)s
                )
                ON CONFLICT (id) DO UPDATE SET
                    date_modified = EXCLUDED.date_modified,
                    plain_text = COALESCE(EXCLUDED.plain_text, cl_opinions.plain_text),
                    html = COALESCE(EXCLUDED.html, cl_opinions.html),
                    raw_data = EXCLUDED.raw_data,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING (xmax = 0) AS inserted
            """, opinion_data)
            
            result = self.cursor.fetchone()
            if result[0]:
                self.stats['opinions_inserted'] += 1
            else:
                self.stats['opinions_updated'] += 1
            
        except Exception as e:
            logger.error(f"Error inserting opinion {opinion.get('id')}: {e}")
            raise
    
    def link_opinions_to_dockets(self):
        """Link opinions to dockets using cluster information"""
        logger.info("Linking opinions to dockets...")
        
        try:
            # This would require additional API calls or cluster data
            # For now, we'll skip this step
            # In a full implementation, you'd:
            # 1. Get cluster data that links opinions to dockets
            # 2. Update cl_opinions.docket_id based on cluster relationships
            pass
            
        except Exception as e:
            logger.error(f"Error linking opinions to dockets: {e}")
    
    def _is_patent_case(self, docket: Dict) -> bool:
        """Check if a docket is a patent case"""
        # Use the PostgreSQL function we created
        self.cursor.execute(
            "SELECT court_data.is_patent_case(%s, %s)",
            (docket.get('nature_of_suit'), docket.get('case_name'))
        )
        return self.cursor.fetchone()[0]
    
    def update_statistics(self):
        """Update and display import statistics"""
        logger.info("Updating statistics...")
        
        # Get counts from database
        self.cursor.execute("""
            SELECT 
                COUNT(DISTINCT d.id) as docket_count,
                COUNT(DISTINCT o.id) as opinion_count,
                COUNT(DISTINCT d.id) FILTER (WHERE d.is_patent_case) as patent_count,
                COUNT(DISTINCT o.id) FILTER (WHERE o.plain_text IS NOT NULL) as opinions_with_text
            FROM court_data.cl_dockets d
            LEFT JOIN court_data.cl_opinions o ON d.id = o.docket_id
        """)
        
        counts = self.cursor.fetchone()
        
        logger.info("=" * 70)
        logger.info("IMPORT COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Dockets inserted: {self.stats['dockets_inserted']}")
        logger.info(f"Dockets updated: {self.stats['dockets_updated']}")
        logger.info(f"Opinions inserted: {self.stats['opinions_inserted']}")
        logger.info(f"Opinions updated: {self.stats['opinions_updated']}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("-" * 70)
        logger.info(f"Total dockets in database: {counts[0]}")
        logger.info(f"Total opinions in database: {counts[1]}")
        logger.info(f"Patent cases: {counts[2]}")
        logger.info(f"Opinions with text: {counts[3]}")
    
    def load_court_data(self, court_id: str, data_dir: str = None):
        """Load all data for a specific court"""
        if data_dir is None:
            data_dir = f"/data/courtlistener/{court_id}"
        
        logger.info(f"Loading data for {court_id} from {data_dir}")
        
        try:
            self.connect()
            
            # Load dockets first
            self.load_dockets(court_id, data_dir)
            
            # Then load opinions
            self.load_opinions(court_id, data_dir)
            
            # Link opinions to dockets if possible
            self.link_opinions_to_dockets()
            
            # Update statistics
            self.update_statistics()
            
        finally:
            self.disconnect()

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Load CourtListener data into PostgreSQL')
    parser.add_argument('--court', default='txed', help='Court ID to load (default: txed)')
    parser.add_argument('--data-dir', help='Data directory (default: /data/courtlistener/[court])')
    parser.add_argument('--create-schema', action='store_true', help='Create database schema first')
    
    args = parser.parse_args()
    
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable not set")
        return
    
    # Create schema if requested
    if args.create_schema:
        logger.info("Creating database schema...")
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        with open('/app/scripts/init_courtlistener_schema.sql', 'r') as f:
            cursor.execute(f.read())
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Schema created successfully")
    
    # Load data
    loader = CourtListenerLoader(DATABASE_URL)
    loader.load_court_data(args.court, args.data_dir)

if __name__ == "__main__":
    main()