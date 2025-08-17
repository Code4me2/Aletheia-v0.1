"""
Database Search Endpoint for Full-Text Court Opinions
Returns complete, untruncated opinion text with metadata from existing database
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import re

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/database", tags=["database"])

class DatabaseSearchRequest(BaseModel):
    """Request model for database search"""
    document_type: Optional[str] = Field(default="020lead", description="Document type: 020lead, opinion, opinion_doctor, or all")
    judge_name: Optional[str] = Field(None, description="Filter by judge name (partial match)")
    court_id: Optional[str] = Field(None, description="Filter by court ID")
    date_after: Optional[str] = Field(None, description="Documents filed after this date (YYYY-MM-DD)")
    date_before: Optional[str] = Field(None, description="Documents filed before this date (YYYY-MM-DD)")
    min_content_length: int = Field(default=5000, description="Minimum content length (filters out empty docs)")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum documents to return")
    include_plain_text: bool = Field(default=True, description="Extract plain text from HTML/XML")

class DatabaseDocument(BaseModel):
    """Complete document with full content and metadata"""
    id: int
    case_number: str
    document_type: str
    content: Dict[str, Any]  # Contains 'raw' (original HTML/XML) and optionally 'plain_text'
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str
    statistics: Dict[str, int]  # Content length, citation count, etc.

class DatabaseSearchResponse(BaseModel):
    """Response model for database search"""
    success: bool
    total_results: int
    documents: List[DatabaseDocument]
    query_info: Dict[str, Any]
    processing_time: str

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host='db',
        database='aletheia',
        user='aletheia',
        password='aletheia123'
    )

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

@router.post("/search", response_model=DatabaseSearchResponse)
async def search_database(request: DatabaseSearchRequest):
    """
    Search existing database for full-text court opinions
    
    This endpoint returns COMPLETE, UNTRUNCATED opinion text from the database.
    It does NOT make external API calls - it only queries existing stored documents.
    
    The 020lead documents contain the richest content (typically 10-40KB of legal text).
    """
    start_time = datetime.now()
    
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query with filters
        conditions = ["1=1"]
        params = []
        
        # Document type filter
        if request.document_type and request.document_type != 'all':
            conditions.append("document_type = %s")
            params.append(request.document_type)
        else:
            # Focus on opinion types by default
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
        
        # Content length filter (exclude empty documents)
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
                content,  -- This is the FULL, UNTRUNCATED content
                metadata,
                created_at,
                updated_at
            FROM public.court_documents
            WHERE {where_clause}
            ORDER BY 
                CASE 
                    WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                    THEN (metadata->>'date_filed')::date 
                    ELSE created_at::date 
                END DESC
            LIMIT %s
        """
        params.append(request.limit)
        
        cur.execute(query, params)
        documents = cur.fetchall()
        
        # Process documents
        processed_docs = []
        for doc in documents:
            # Extract metadata
            metadata = doc['metadata'] if isinstance(doc['metadata'], dict) else json.loads(doc['metadata'] or '{}')
            
            # Prepare content object
            content_obj = {
                'raw': doc['content'],  # FULL, UNTRUNCATED HTML/XML content
                'length': len(doc['content']) if doc['content'] else 0
            }
            
            # Extract plain text if requested
            if request.include_plain_text and doc['content']:
                plain_text = extract_plain_text(doc['content'])
                content_obj['plain_text'] = plain_text  # FULL, UNTRUNCATED plain text
                content_obj['plain_text_length'] = len(plain_text)
            
            # Count citations if present
            citation_count = 0
            if doc['content']:
                # Count legal citations (e.g., "123 F.3d 456")
                citation_pattern = r'\d+\s+[A-Z]\.\d?[a-z]{0,2}\s+\d+'
                citations = re.findall(citation_pattern, doc['content'])
                citation_count = len(citations)
            
            # Build complete document object
            processed_doc = DatabaseDocument(
                id=doc['id'],
                case_number=doc['case_number'] or f"DOC-{doc['id']}",
                document_type=doc['document_type'],
                content=content_obj,
                metadata=metadata,
                created_at=str(doc['created_at']),
                updated_at=str(doc['updated_at']),
                statistics={
                    'content_length': len(doc['content']) if doc['content'] else 0,
                    'citation_count': citation_count,
                    'has_judge': bool(metadata.get('judge_name')),
                    'has_court': bool(metadata.get('court_id'))
                }
            )
            
            processed_docs.append(processed_doc)
        
        cur.close()
        conn.close()
        
        processing_time = str(datetime.now() - start_time)
        
        return DatabaseSearchResponse(
            success=True,
            total_results=total_count,
            documents=processed_docs,
            query_info={
                'document_type': request.document_type,
                'judge_name': request.judge_name,
                'court_id': request.court_id,
                'date_range': {
                    'after': request.date_after,
                    'before': request.date_before
                },
                'min_content_length': request.min_content_length,
                'limit': request.limit
            },
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"Database search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/document/{document_id}")
async def get_document_by_id(document_id: int, include_plain_text: bool = True):
    """
    Get a single document by ID with FULL content
    
    Returns the complete, untruncated document text and all metadata.
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
        
        # Prepare content object with FULL content
        content_obj = {
            'raw': doc['content'],  # FULL, UNTRUNCATED content
            'length': len(doc['content']) if doc['content'] else 0
        }
        
        # Extract plain text if requested
        if include_plain_text and doc['content']:
            plain_text = extract_plain_text(doc['content'])
            content_obj['plain_text'] = plain_text  # FULL, UNTRUNCATED plain text
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
                'updated_at': str(doc['updated_at'])
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_database_statistics():
    """
    Get statistics about documents in the database
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Get document counts by type
        cur.execute("""
            SELECT 
                document_type,
                COUNT(*) as count,
                AVG(LENGTH(content)) as avg_content_length,
                MAX(LENGTH(content)) as max_content_length,
                MIN(LENGTH(content)) as min_content_length
            FROM public.court_documents
            GROUP BY document_type
            ORDER BY count DESC
        """)
        
        type_stats = cur.fetchall()
        
        # Get judge coverage
        cur.execute("""
            SELECT 
                COUNT(DISTINCT metadata->>'judge_name') as unique_judges,
                COUNT(*) FILTER (WHERE metadata->>'judge_name' IS NOT NULL) as docs_with_judges
            FROM public.court_documents
            WHERE document_type IN ('020lead', 'opinion', 'opinion_doctor')
        """)
        
        judge_stats = cur.fetchone()
        
        # Get content statistics for 020lead documents
        cur.execute("""
            SELECT 
                COUNT(*) as total_020lead,
                COUNT(*) FILTER (WHERE LENGTH(content) > 5000) as with_substantial_content,
                COUNT(*) FILTER (WHERE LENGTH(content) > 10000) as with_full_opinions,
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
                'judge_coverage': judge_stats,
                '020lead_documents': lead_stats
            }
        }
        
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))