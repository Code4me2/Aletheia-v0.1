#!/usr/bin/env python3
"""
Standalone Database API for Full-Text Court Opinion Retrieval

This script provides direct access to the court documents database,
returning COMPLETE, UNTRUNCATED opinion text with all metadata.

Runs independently of the court-processor container on port 8103.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re
import os
import uvicorn
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '8200'),  # Using the exposed port
    'database': os.getenv('DB_NAME', 'aletheia'),
    'user': os.getenv('DB_USER', 'aletheia'),
    'password': os.getenv('DB_PASSWORD', 'aletheia123')
}

API_PORT = int(os.getenv('COURT_DB_API_PORT', '8103'))

# Initialize FastAPI
app = FastAPI(
    title="Court Documents Database API",
    description="Direct database access for full-text court opinions (020lead documents)",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class SearchRequest(BaseModel):
    """Request model for database search"""
    document_type: Optional[str] = Field(default="020lead", description="Document type: 020lead, opinion, opinion_doctor, or all")
    judge_name: Optional[str] = Field(None, description="Filter by judge name (partial match)")
    court_id: Optional[str] = Field(None, description="Filter by court ID")
    date_after: Optional[str] = Field(None, description="Documents filed after (YYYY-MM-DD)")
    date_before: Optional[str] = Field(None, description="Documents filed before (YYYY-MM-DD)")
    min_content_length: int = Field(default=5000, description="Minimum content length")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum documents to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    include_plain_text: bool = Field(default=True, description="Extract plain text from HTML/XML")

class DocumentResponse(BaseModel):
    """Complete document with full content"""
    id: int
    case_number: Optional[str]
    document_type: str
    content: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: str
    updated_at: Optional[str]
    statistics: Dict[str, Any]

# Database connection
def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            database=DB_CONFIG['database'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password']
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

def extract_plain_text(html_content: str) -> str:
    """Extract plain text from HTML/XML content"""
    if not html_content:
        return ""
    
    # Remove XML/HTML tags
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove extra spaces around punctuation
    text = re.sub(r'\s+([.,;!?])', r'\1', text)
    text = re.sub(r'([.,;!?])\s+', r'\1 ', text)
    
    return text.strip()

@app.get("/")
async def root():
    """Health check and API info"""
    return {
        "status": "healthy",
        "service": "Court Documents Database API",
        "version": "1.0.0",
        "database": DB_CONFIG['database'],
        "port": API_PORT,
        "endpoints": [
            "/search - Search for full-text documents",
            "/document/{id} - Get single document by ID",
            "/statistics - Database statistics",
            "/test - Test with sample Gilstrap opinion"
        ]
    }

@app.post("/search")
async def search_documents(request: SearchRequest):
    """
    Search for court documents with FULL, UNTRUNCATED content
    
    Returns complete opinion text (typically 10-40KB for 020lead documents).
    This queries the existing PostgreSQL database directly.
    """
    start_time = datetime.now()
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query conditions
        conditions = ["1=1"]
        params = []
        
        # Document type filter
        if request.document_type and request.document_type != 'all':
            conditions.append("document_type = %s")
            params.append(request.document_type)
        else:
            # Focus on opinion types
            conditions.append("document_type IN ('020lead', 'opinion', 'opinion_doctor')")
        
        # Judge filter (case-insensitive partial match)
        if request.judge_name:
            conditions.append("metadata->>'judge_name' ILIKE %s")
            params.append(f'%{request.judge_name}%')
        
        # Court filter
        if request.court_id:
            conditions.append("metadata->>'court_id' = %s")
            params.append(request.court_id)
        
        # Date filters
        if request.date_after:
            conditions.append("metadata->>'date_filed' >= %s")
            params.append(request.date_after)
        
        if request.date_before:
            conditions.append("metadata->>'date_filed' <= %s")
            params.append(request.date_before)
        
        # Content length filter
        if request.min_content_length > 0:
            conditions.append("LENGTH(content) >= %s")
            params.append(request.min_content_length)
        
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total
            FROM public.court_documents
            WHERE {where_clause}
        """
        cur.execute(count_query, params)
        total_count = cur.fetchone()['total']
        
        # Get documents with FULL CONTENT
        query = f"""
            SELECT 
                id,
                case_number,
                document_type,
                content,  -- FULL, UNTRUNCATED content
                metadata,
                created_at,
                updated_at
            FROM public.court_documents
            WHERE {where_clause}
            ORDER BY 
                CASE 
                    WHEN metadata->>'date_filed' IS NOT NULL 
                    THEN (metadata->>'date_filed')::date 
                    ELSE created_at::date 
                END DESC
            LIMIT %s OFFSET %s
        """
        params.extend([request.limit, request.offset])
        
        cur.execute(query, params)
        documents = cur.fetchall()
        
        # Process documents
        results = []
        for doc in documents:
            # Parse metadata
            metadata = doc['metadata'] if isinstance(doc['metadata'], dict) else json.loads(doc['metadata'] or '{}')
            
            # Prepare content object
            content_obj = {
                'raw': doc['content'],  # FULL HTML/XML
                'length': len(doc['content']) if doc['content'] else 0
            }
            
            # Extract plain text if requested
            if request.include_plain_text and doc['content']:
                plain_text = extract_plain_text(doc['content'])
                content_obj['plain_text'] = plain_text  # FULL plain text
                content_obj['plain_text_length'] = len(plain_text)
            
            # Calculate statistics
            stats = {
                'content_length': len(doc['content']) if doc['content'] else 0,
                'has_judge': bool(metadata.get('judge_name')),
                'has_court': bool(metadata.get('court_id')),
                'source': metadata.get('source', 'unknown')
            }
            
            # Count citations if present
            if doc['content']:
                citation_pattern = r'\d+\s+[A-Z]\.\d?[a-z]{0,2}\s+\d+'
                citations = re.findall(citation_pattern, doc['content'])
                stats['citation_count'] = len(citations)
            
            results.append({
                'id': doc['id'],
                'case_number': doc['case_number'] or f"DOC-{doc['id']}",
                'document_type': doc['document_type'],
                'content': content_obj,
                'metadata': metadata,
                'created_at': str(doc['created_at']),
                'updated_at': str(doc['updated_at']) if doc['updated_at'] else None,
                'statistics': stats
            })
        
        cur.close()
        conn.close()
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return {
            'success': True,
            'total_results': total_count,
            'returned': len(results),
            'documents': results,
            'query': {
                'document_type': request.document_type,
                'judge_name': request.judge_name,
                'court_id': request.court_id,
                'min_content_length': request.min_content_length,
                'offset': request.offset,
                'limit': request.limit
            },
            'processing_time_seconds': processing_time
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/document/{document_id}")
async def get_document(document_id: int, include_plain_text: bool = True):
    """
    Get a single document by ID with FULL content
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        query = """
            SELECT 
                id,
                case_number,
                document_type,
                content,
                metadata,
                created_at,
                updated_at
            FROM public.court_documents
            WHERE id = %s
        """
        
        cur.execute(query, (document_id,))
        doc = cur.fetchone()
        
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Process document
        metadata = doc['metadata'] if isinstance(doc['metadata'], dict) else json.loads(doc['metadata'] or '{}')
        
        content_obj = {
            'raw': doc['content'],
            'length': len(doc['content']) if doc['content'] else 0
        }
        
        if include_plain_text and doc['content']:
            plain_text = extract_plain_text(doc['content'])
            content_obj['plain_text'] = plain_text
            content_obj['plain_text_length'] = len(plain_text)
        
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'document': {
                'id': doc['id'],
                'case_number': doc['case_number'],
                'document_type': doc['document_type'],
                'content': content_obj,
                'metadata': metadata,
                'created_at': str(doc['created_at']),
                'updated_at': str(doc['updated_at']) if doc['updated_at'] else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics")
async def get_statistics():
    """
    Get database statistics
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Document type statistics
        cur.execute("""
            SELECT 
                document_type,
                COUNT(*) as count,
                AVG(LENGTH(content)) as avg_content_length,
                MAX(LENGTH(content)) as max_content_length,
                COUNT(*) FILTER (WHERE LENGTH(content) > 5000) as with_substantial_content
            FROM public.court_documents
            GROUP BY document_type
            ORDER BY count DESC
        """)
        type_stats = cur.fetchall()
        
        # Judge statistics
        cur.execute("""
            SELECT 
                metadata->>'judge_name' as judge,
                COUNT(*) as document_count,
                AVG(LENGTH(content)) as avg_content_length
            FROM public.court_documents
            WHERE document_type = '020lead'
            AND metadata->>'judge_name' IS NOT NULL
            GROUP BY metadata->>'judge_name'
            ORDER BY document_count DESC
            LIMIT 10
        """)
        judge_stats = cur.fetchall()
        
        # 020lead specific stats
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE LENGTH(content) > 10000) as full_opinions,
                MIN(LENGTH(content)) as min_length,
                MAX(LENGTH(content)) as max_length,
                AVG(LENGTH(content)) as avg_length
            FROM public.court_documents
            WHERE document_type = '020lead'
        """)
        lead_stats = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'statistics': {
                'by_document_type': type_stats,
                'top_judges_020lead': judge_stats,
                '020lead_summary': lead_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test")
async def test_gilstrap():
    """
    Test endpoint - retrieves one Gilstrap opinion to verify full content
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get one Gilstrap 020lead document
        cur.execute("""
            SELECT 
                id,
                case_number,
                document_type,
                content,
                metadata,
                LENGTH(content) as content_length
            FROM public.court_documents
            WHERE document_type = '020lead'
            AND metadata->>'judge_name' ILIKE '%Gilstrap%'
            AND LENGTH(content) > 10000
            LIMIT 1
        """)
        
        doc = cur.fetchone()
        
        if not doc:
            return {
                'success': False,
                'message': 'No Gilstrap 020lead documents found'
            }
        
        # Extract plain text
        plain_text = extract_plain_text(doc['content'])
        
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'document_id': doc['id'],
            'case_number': doc['case_number'],
            'document_type': doc['document_type'],
            'content_stats': {
                'raw_html_length': doc['content_length'],
                'plain_text_length': len(plain_text),
                'first_500_chars': plain_text[:500],
                'middle_500_chars': plain_text[10000:10500] if len(plain_text) > 10500 else 'Document shorter than 10500 chars',
                'last_500_chars': plain_text[-500:]
            },
            'metadata': doc['metadata'] if isinstance(doc['metadata'], dict) else json.loads(doc['metadata'] or '{}')
        }
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    logger.info(f"Starting Court Documents Database API on port {API_PORT}")
    logger.info(f"Database: {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")
    
    # Run the API
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=API_PORT,
        log_level="info"
    )