"""
Database connection module for court processor
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

def get_db_connection(cursor_factory=None):
    """
    Get database connection using environment variable or defaults
    """
    # Get DATABASE_URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'postgresql://aletheia:aletheia123@db:5432/aletheia')
    
    try:
        if cursor_factory:
            conn = psycopg2.connect(database_url, cursor_factory=cursor_factory)
        else:
            conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

def get_db_config():
    """
    Parse database configuration from DATABASE_URL
    """
    database_url = os.getenv('DATABASE_URL', 'postgresql://aletheia:aletheia123@db:5432/aletheia')
    
    # Parse the URL
    import re
    match = re.match(r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', database_url)
    
    if match:
        return {
            'user': match.group(1),
            'password': match.group(2),
            'host': match.group(3),
            'port': match.group(4),
            'database': match.group(5)
        }
    else:
        # Fallback defaults
        return {
            'user': 'aletheia',
            'password': 'aletheia123',
            'host': 'db',
            'port': '5432',
            'database': 'aletheia'
        }