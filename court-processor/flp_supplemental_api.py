"""
FLP Supplemental API
Works with existing court data without conflicts
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
import logging
import os
from datetime import datetime

from services.flp_supplemental import FLPSupplementalService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="FLP Supplemental Enhancement API",
    description="Enhances existing court data with FLP tools without duplication",
    version="2.0.0"
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),
    'port': os.getenv('DB_PORT', 5432),
    'database': os.getenv('DB_NAME', 'datacompose'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', '')
}

# Global service instance
flp_service = None

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)

@app.on_event("startup")
async def startup_event():
    """Initialize FLP service on startup"""
    global flp_service
    db_conn = get_db_connection()
    flp_service = FLPSupplementalService(db_conn)
    logger.info("FLP Supplemental Service initialized")

# Request/Response models
class EnhanceOpinionRequest(BaseModel):
    opinion_id: int = Field(..., description="Opinion ID to enhance")
    source: Literal["opinions", "cl_opinions"] = Field(
        "opinions", 
        description="Source table: 'opinions' (juriscraper) or 'cl_opinions' (courtlistener)"
    )

class BatchEnhanceRequest(BaseModel):
    limit: int = Field(100, description="Maximum opinions to enhance", le=1000)
    source: Literal["opinions", "cl_opinions", "both"] = Field(
        "both",
        description="Which source to enhance"
    )

class TextExtractionRequest(BaseModel):
    pdf_path: str = Field(..., description="Path to PDF file")
    force: bool = Field(False, description="Force re-extraction even if text exists")

# Endpoints

@app.get("/")
async def root():
    """API information"""
    return {
        "service": "FLP Supplemental Enhancement",
        "version": "2.0.0",
        "description": "Enhances existing court data without conflicts",
        "endpoints": {
            "enhance_single": "/enhance/opinion",
            "enhance_batch": "/enhance/batch",
            "stats": "/stats",
            "pending": "/pending"
        }
    }

@app.get("/health")
async def health_check():
    """Health check with database connectivity test"""
    try:
        db_conn = get_db_connection()
        with db_conn.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")

@app.post("/enhance/opinion")
async def enhance_single_opinion(request: EnhanceOpinionRequest):
    """
    Enhance a single opinion with FLP tools
    - Extracts text if missing
    - Standardizes court names
    - Extracts and normalizes citations
    - Checks for bad redactions
    - Adds judge photos
    """
    try:
        result = await flp_service.enhance_opinion(
            request.opinion_id,
            request.source
        )
        
        if not result['success'] and 'error' in result:
            raise HTTPException(status_code=400, detail=result['error'])
        
        return result
    except Exception as e:
        logger.error(f"Enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/enhance/batch")
async def enhance_batch(
    request: BatchEnhanceRequest,
    background_tasks: BackgroundTasks
):
    """
    Enhance multiple opinions in the background
    """
    background_tasks.add_task(
        flp_service.batch_enhance,
        request.limit,
        request.source
    )
    
    return {
        "status": "started",
        "message": f"Batch enhancement started for up to {request.limit} opinions",
        "source": request.source
    }

@app.get("/pending")
async def get_pending_enhancements(
    source: Literal["opinions", "cl_opinions", "both"] = Query("both"),
    limit: int = Query(100, le=1000)
):
    """
    Get opinions that haven't been enhanced yet
    """
    db_conn = get_db_connection()
    try:
        pending = []
        
        if source in ["opinions", "both"]:
            with db_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, case_name, court_code, case_date,
                           CASE WHEN text_content IS NULL THEN true ELSE false END as needs_text
                    FROM court_data.opinions
                    WHERE metadata->>'flp_supplemental' IS NULL
                    ORDER BY case_date DESC
                    LIMIT %s
                """, (limit,))
                
                for row in cursor.fetchall():
                    pending.append({
                        **dict(row),
                        'source': 'opinions'
                    })
        
        if source in ["cl_opinions", "both"]:
            remaining = limit - len(pending)
            if remaining > 0:
                with db_conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id, case_name, court_id, date_filed as case_date,
                               CASE WHEN plain_text IS NULL THEN true ELSE false END as needs_text
                        FROM court_data.cl_opinions
                        WHERE metadata->>'flp_supplemental' IS NULL
                        ORDER BY date_filed DESC
                        LIMIT %s
                    """, (remaining,))
                    
                    for row in cursor.fetchall():
                        pending.append({
                            **dict(row),
                            'source': 'cl_opinions'
                        })
        
        return {
            "count": len(pending),
            "opinions": pending
        }
    finally:
        db_conn.close()

@app.get("/stats")
async def get_enhancement_stats():
    """
    Get statistics about FLP enhancements
    """
    db_conn = get_db_connection()
    try:
        stats = {}
        
        # Juriscraper opinions stats
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE metadata->>'flp_supplemental' IS NOT NULL) as enhanced,
                    COUNT(*) FILTER (WHERE text_content IS NULL) as missing_text,
                    COUNT(*) FILTER (WHERE text_content IS NOT NULL AND metadata->>'flp_supplemental' IS NULL) as ready_to_enhance
                FROM court_data.opinions
            """)
            stats['juriscraper'] = dict(cursor.fetchone())
        
        # CourtListener opinions stats  
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE metadata->>'flp_supplemental' IS NOT NULL) as enhanced,
                    COUNT(*) FILTER (WHERE plain_text IS NULL) as missing_text,
                    COUNT(*) FILTER (WHERE plain_text IS NOT NULL AND metadata->>'flp_supplemental' IS NULL) as ready_to_enhance
                FROM court_data.cl_opinions
            """)
            stats['courtlistener'] = dict(cursor.fetchone())
        
        # Enhancement details
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT original_code) as courts_standardized,
                    COUNT(DISTINCT original) as reporters_normalized
                FROM court_data.court_standardization
                CROSS JOIN court_data.citation_normalization
            """)
            stats['enhancements'] = dict(cursor.fetchone())
        
        # Redaction checks
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as documents_checked,
                    COUNT(*) FILTER (WHERE has_bad_redactions) as bad_redactions_found
                FROM court_data.redaction_issues
            """)
            stats['redactions'] = dict(cursor.fetchone())
        
        # Judge photos
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_judges,
                    COUNT(*) FILTER (WHERE photo_url IS NOT NULL) as with_photos
                FROM court_data.judges
            """)
            stats['judges'] = dict(cursor.fetchone())
        
        # Calculate totals
        total_opinions = stats['juriscraper']['total'] + stats['courtlistener']['total']
        total_enhanced = stats['juriscraper']['enhanced'] + stats['courtlistener']['enhanced']
        
        stats['summary'] = {
            'total_opinions': total_opinions,
            'total_enhanced': total_enhanced,
            'enhancement_percentage': round((total_enhanced / total_opinions * 100) if total_opinions > 0 else 0, 2),
            'ready_to_enhance': stats['juriscraper']['ready_to_enhance'] + stats['courtlistener']['ready_to_enhance']
        }
        
        return stats
    finally:
        db_conn.close()

@app.get("/stats/enhancements")
async def get_enhancement_breakdown():
    """
    Get detailed breakdown of what enhancements have been applied
    """
    db_conn = get_db_connection()
    try:
        breakdown = {
            'text_extractions': 0,
            'court_standardizations': 0,
            'citation_extractions': 0,
            'redaction_checks': 0,
            'judge_photos': 0
        }
        
        # Count opinions by enhancement type
        for table in ['court_data.opinions', 'court_data.cl_opinions']:
            with db_conn.cursor() as cursor:
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) FILTER (WHERE metadata->'flp_supplemental'->'enhancements'->>'text_extracted' = 'true') as text_extracted,
                        COUNT(*) FILTER (WHERE metadata->'flp_supplemental'->'enhancements'->>'court_standardization' IS NOT NULL) as court_std,
                        COUNT(*) FILTER (WHERE metadata->'flp_supplemental'->'enhancements'->>'citations' IS NOT NULL) as citations,
                        COUNT(*) FILTER (WHERE metadata->'flp_supplemental'->'enhancements'->>'redaction_check' IS NOT NULL) as redactions,
                        COUNT(*) FILTER (WHERE metadata->'flp_supplemental'->'enhancements'->>'judge' IS NOT NULL) as judges
                    FROM {table}
                    WHERE metadata->>'flp_supplemental' IS NOT NULL
                """)
                
                result = cursor.fetchone()
                if result:
                    breakdown['text_extractions'] += result['text_extracted'] or 0
                    breakdown['court_standardizations'] += result['court_std'] or 0
                    breakdown['citation_extractions'] += result['citations'] or 0
                    breakdown['redaction_checks'] += result['redactions'] or 0
                    breakdown['judge_photos'] += result['judges'] or 0
        
        return breakdown
    finally:
        db_conn.close()

@app.post("/tools/extract-text")
async def extract_text_only(request: TextExtractionRequest):
    """
    Extract text from a PDF using Doctor service
    """
    pdf_path = Path(request.pdf_path)
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail=f"PDF not found: {request.pdf_path}")
    
    try:
        result = await flp_service._extract_with_doctor(pdf_path)
        if result['success']:
            return {
                'success': True,
                'text': result['text'],
                'page_count': result.get('page_count', 0),
                'method': result.get('method', 'doctor')
            }
        else:
            raise HTTPException(status_code=500, detail=result.get('error', 'Extraction failed'))
    except Exception as e:
        logger.error(f"Text extraction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tools/court/{court_code}")
async def get_court_standardization(court_code: str):
    """
    Get standardized court information
    """
    try:
        result = await flp_service._standardize_court(court_code)
        return result
    except Exception as e:
        logger.error(f"Court standardization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/monitor/progress")
async def monitor_enhancement_progress():
    """
    Monitor real-time enhancement progress
    """
    db_conn = get_db_connection()
    try:
        progress = {}
        
        # Get recent enhancements
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    DATE(metadata->'flp_supplemental'->>'enhanced_at') as enhancement_date,
                    COUNT(*) as opinions_enhanced
                FROM (
                    SELECT metadata FROM court_data.opinions 
                    WHERE metadata->>'flp_supplemental' IS NOT NULL
                    UNION ALL
                    SELECT metadata FROM court_data.cl_opinions 
                    WHERE metadata->>'flp_supplemental' IS NOT NULL
                ) combined
                GROUP BY enhancement_date
                ORDER BY enhancement_date DESC
                LIMIT 7
            """)
            
            progress['daily_enhancements'] = [
                dict(row) for row in cursor.fetchall()
            ]
        
        # Get enhancement rate
        with db_conn.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) as last_hour
                FROM (
                    SELECT metadata FROM court_data.opinions 
                    WHERE metadata->'flp_supplemental'->>'enhanced_at' > NOW() - INTERVAL '1 hour'
                    UNION ALL
                    SELECT metadata FROM court_data.cl_opinions 
                    WHERE metadata->'flp_supplemental'->>'enhanced_at' > NOW() - INTERVAL '1 hour'
                ) combined
            """)
            
            progress['enhancements_last_hour'] = cursor.fetchone()['last_hour']
        
        return progress
    finally:
        db_conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)