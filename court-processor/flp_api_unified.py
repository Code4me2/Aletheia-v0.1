"""
Unified FLP API that integrates with existing court-processor workflow
Works with the existing opinions table and processing pipeline
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
import logging
import os
from datetime import datetime

from services.flp_integration_unified import UnifiedFLPIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="Free Law Project Enhanced Processing API",
    description="FLP tools integration for existing court-processor pipeline",
    version="1.0.0"
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'datacompose'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Global FLP integration instance
flp_integration = None

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@app.on_event("startup")
async def startup_event():
    """Initialize FLP integration on startup"""
    global flp_integration
    db_conn = get_db_connection()
    flp_integration = UnifiedFLPIntegration(db_conn)
    logger.info("FLP integration initialized")

# Request/Response models
class OpinionEnhanceRequest(BaseModel):
    opinion_id: int = Field(..., description="ID of existing opinion to enhance")
    
class BatchEnhanceRequest(BaseModel):
    opinion_ids: List[int] = Field(..., description="List of opinion IDs to enhance")
    max_concurrent: int = Field(5, description="Maximum concurrent processing")

class CourtResolveRequest(BaseModel):
    court_string: str = Field(..., description="Court name to resolve")
    date_found: Optional[str] = Field(None, description="Date for historical court lookup")

class CitationExtractionRequest(BaseModel):
    text: str = Field(..., description="Text to extract citations from")
    
class ReporterNormalizeRequest(BaseModel):
    reporter: str = Field(..., description="Reporter abbreviation to normalize")

# Endpoints

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "flp-integration"}

@app.post("/enhance/opinion")
async def enhance_existing_opinion(request: OpinionEnhanceRequest):
    """
    Enhance an existing opinion with FLP tools
    Adds citations, court standardization, judge photos, etc.
    """
    try:
        result = await flp_integration.process_opinion_for_flp(request.opinion_id)
        return result
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enhance/batch")
async def enhance_opinions_batch(
    request: BatchEnhanceRequest,
    background_tasks: BackgroundTasks
):
    """
    Enhance multiple opinions in background
    """
    background_tasks.add_task(
        process_batch_enhancement,
        request.opinion_ids,
        request.max_concurrent
    )
    
    return {
        "message": f"Enhancement started for {len(request.opinion_ids)} opinions",
        "opinion_ids": request.opinion_ids
    }

async def process_batch_enhancement(opinion_ids: List[int], max_concurrent: int):
    """Process batch enhancement in background"""
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_with_semaphore(opinion_id):
        async with semaphore:
            return await flp_integration.process_opinion_for_flp(opinion_id)
    
    tasks = [process_with_semaphore(oid) for oid in opinion_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Log results
    successful = sum(1 for r in results if isinstance(r, dict) and r.get('success'))
    logger.info(f"Batch enhancement completed: {successful}/{len(opinion_ids)} successful")

@app.get("/enhance/pending")
async def get_pending_opinions(limit: int = Query(100, description="Maximum results")):
    """
    Get opinions that haven't been enhanced with FLP tools yet
    """
    db_conn = get_db_connection()
    try:
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, case_name, court_code, case_date
                FROM court_data.opinions
                WHERE metadata->>'flp_processed' IS NULL
                AND text_content IS NOT NULL
                ORDER BY case_date DESC
                LIMIT %s
            """, (limit,))
            
            opinions = cursor.fetchall()
            
            return {
                "count": len(opinions),
                "opinions": opinions
            }
    finally:
        db_conn.close()

@app.post("/tools/court/resolve")
async def resolve_court(request: CourtResolveRequest):
    """
    Resolve court string to standardized court ID
    """
    result = flp_integration.resolve_court(
        request.court_string,
        request.date_found
    )
    return result

@app.get("/tools/court/list")
async def list_standardized_courts():
    """
    Get all standardized courts from Courts-DB
    """
    from courts_db import courts
    
    court_list = []
    for court_id, court_data in courts.items():
        court_list.append({
            'court_id': court_id,
            'name': court_data.get('name', ''),
            'citation_string': court_data.get('citation_string', ''),
            'level': court_data.get('level', ''),
            'type': court_data.get('type', '')
        })
    
    return {
        "count": len(court_list),
        "courts": sorted(court_list, key=lambda x: x['name'])
    }

@app.post("/tools/citations/extract")
async def extract_citations(request: CitationExtractionRequest):
    """
    Extract legal citations from text
    """
    from eyecite import get_citations, clean_text
    
    citations = get_citations(clean_text(request.text))
    
    citation_list = []
    for citation in citations:
        citation_data = {
            'text': str(citation),
            'type': citation.__class__.__name__
        }
        
        # Add specific fields based on citation type
        if hasattr(citation, 'reporter'):
            citation_data['reporter'] = citation.reporter
            # Normalize reporter
            reporter_info = flp_integration.normalize_reporter(citation.reporter)
            citation_data['normalized_reporter'] = reporter_info['normalized']
            citation_data['reporter_full_name'] = reporter_info['full_name']
        
        if hasattr(citation, 'volume'):
            citation_data['volume'] = citation.volume
        if hasattr(citation, 'page'):
            citation_data['page'] = citation.page
            
        citation_list.append(citation_data)
    
    return {
        "count": len(citation_list),
        "citations": citation_list
    }

@app.post("/tools/reporter/normalize")
async def normalize_reporter(request: ReporterNormalizeRequest):
    """
    Normalize reporter abbreviation
    """
    result = flp_integration.normalize_reporter(request.reporter)
    return result

@app.get("/stats/enhancement")
async def get_enhancement_stats():
    """
    Get statistics about FLP enhancement coverage
    """
    db_conn = get_db_connection()
    try:
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_opinions,
                    COUNT(*) FILTER (WHERE metadata->>'flp_processed' = 'true') as enhanced_opinions,
                    COUNT(*) FILTER (WHERE metadata->'flp_enhancements'->>'has_bad_redactions' = 'true') as bad_redactions_found,
                    COUNT(*) FILTER (WHERE metadata->'flp_enhancements'->>'court_standardized' IS NOT NULL) as courts_standardized,
                    COUNT(*) FILTER (WHERE jsonb_array_length(COALESCE(metadata->'flp_enhancements'->'citations', '[]'::jsonb)) > 0) as opinions_with_citations
                FROM court_data.opinions
            """)
            
            stats = cursor.fetchone()
            
            # Get judge photo stats
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT id) as total_judges,
                    COUNT(DISTINCT id) FILTER (WHERE photo_url IS NOT NULL) as judges_with_photos
                FROM court_data.judges
            """)
            
            judge_stats = cursor.fetchone()
            
            return {
                "opinions": stats,
                "judges": judge_stats,
                "enhancement_percentage": round(
                    (stats['enhanced_opinions'] / stats['total_opinions'] * 100) 
                    if stats['total_opinions'] > 0 else 0, 
                    2
                )
            }
    finally:
        db_conn.close()

@app.post("/integrate/new-document")
async def process_new_document_with_flp(
    pdf_path: str = Query(..., description="Path to PDF file"),
    case_name: str = Query(..., description="Case name"),
    court_string: str = Query(..., description="Court name"),
    judge_name: Optional[str] = Query(None, description="Judge name"),
    docket_number: Optional[str] = Query(None, description="Docket number"),
    date_filed: Optional[str] = Query(None, description="Filing date (YYYY-MM-DD)")
):
    """
    Process a new document with FLP tools before inserting into database
    This endpoint is designed to be called by the existing court-processor
    """
    pdf_file_path = Path(pdf_path)
    if not pdf_file_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF file not found: {pdf_path}")
    
    metadata = {
        'case_name': case_name,
        'court_string': court_string,
        'judge_name': judge_name,
        'docket_number': docket_number,
        'date_filed': date_filed
    }
    
    try:
        # Process with FLP tools
        result = await flp_integration.enhance_new_document(pdf_file_path, metadata)
        
        if result['success']:
            # Return data in format expected by court-processor
            return {
                'success': True,
                'text_content': result['text_content'],
                'court_code': result['metadata'].get('court_code'),
                'metadata': result['enhancements'],
                'judge_name': judge_name,
                'processing_notes': 'Enhanced with FLP tools'
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Processing failed'))
            
    except Exception as e:
        logger.error(f"Document processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)