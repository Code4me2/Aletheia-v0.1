"""
Free Law Project Integration API
Comprehensive endpoints for all FLP tools
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
from dotenv import load_dotenv

from services.flp_integration import FLPIntegration

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Free Law Project Integration API",
    description="Comprehensive API for Courts-DB, Doctor, Juriscraper, Eyecite, X-Ray, Reporters-DB, and Judge-pics",
    version="3.0.0"
)

# Database connection
def get_db_connection():
    """Create a database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'db'),
        port=os.getenv('DB_PORT', '5432'),
        user=os.getenv('DB_USER', 'aletheia_user'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'aletheia')
    )

# Request/Response models
class CourtResolveRequest(BaseModel):
    court_string: str
    date: Optional[str] = None

class ReporterNormalizeRequest(BaseModel):
    reporter: str

class JudgePhotoRequest(BaseModel):
    judge_name: str
    court: Optional[str] = None

class ComprehensiveProcessRequest(BaseModel):
    file_path: str
    case_name: str
    docket_number: Optional[str] = None
    court_string: str
    date_filed: Optional[str] = None
    judges: Optional[List[str]] = None

# Health check
@app.get("/health")
async def health_check():
    """Check API and service health"""
    try:
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "services": {
                "database": "connected",
                "courts_db": "available",
                "reporters_db": "available",
                "eyecite": "available",
                "xray": "available",
                "judge_pics": "available"
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Courts-DB endpoints
@app.post("/courts/resolve")
async def resolve_court(request: CourtResolveRequest):
    """Resolve court name to standardized ID"""
    try:
        conn = get_db_connection()
        flp = FLPIntegration(conn)
        result = flp.resolve_court(request.court_string, request.date)
        conn.close()
        
        if result['court_id']:
            return result
        else:
            raise HTTPException(status_code=404, detail=result['error'])
    
    except Exception as e:
        logger.error(f"Error resolving court: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Reporters-DB endpoints
@app.post("/reporters/normalize")
async def normalize_reporter(request: ReporterNormalizeRequest):
    """Normalize reporter abbreviation"""
    try:
        conn = get_db_connection()
        flp = FLPIntegration(conn)
        result = flp.normalize_reporter(request.reporter)
        conn.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error normalizing reporter: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reporters/list")
async def list_reporters():
    """List all available reporters"""
    try:
        from reporters_db import REPORTERS
        
        reporters_list = []
        for key, data in REPORTERS.items():
            reporters_list.append({
                "abbreviation": key,
                "name": data.get('name', ''),
                "publisher": data.get('publisher', ''),
                "type": data.get('type', '')
            })
        
        return {
            "total": len(reporters_list),
            "reporters": sorted(reporters_list, key=lambda x: x['name'])
        }
    
    except Exception as e:
        logger.error(f"Error listing reporters: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Judge-pics endpoints
@app.post("/judges/photo")
async def get_judge_photo(request: JudgePhotoRequest):
    """Get judge photo URL"""
    try:
        conn = get_db_connection()
        flp = FLPIntegration(conn)
        result = await flp.get_judge_photo(request.judge_name, request.court)
        conn.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error getting judge photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/judges/list")
async def list_judges_with_photos():
    """List all judges with photos in database"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT name, court, photo_url, judge_pics_id, updated_at
                FROM court_data.judges
                WHERE photo_url IS NOT NULL
                ORDER BY name
            """)
            judges = cursor.fetchall()
        conn.close()
        
        return {
            "total": len(judges),
            "judges": judges
        }
    
    except Exception as e:
        logger.error(f"Error listing judges: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# X-Ray endpoints
@app.post("/xray/check-redactions")
async def check_redactions(file_path: str):
    """Check PDF for bad redactions"""
    try:
        conn = get_db_connection()
        flp = FLPIntegration(conn)
        result = flp.check_bad_redactions(Path(file_path))
        conn.close()
        
        return result
    
    except Exception as e:
        logger.error(f"Error checking redactions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Comprehensive processing
@app.post("/process/comprehensive")
async def process_comprehensive(
    request: ComprehensiveProcessRequest,
    background_tasks: BackgroundTasks
):
    """Process document using all FLP tools"""
    try:
        conn = get_db_connection()
        flp = FLPIntegration(conn)
        
        metadata = {
            'case_name': request.case_name,
            'docket_number': request.docket_number,
            'court_string': request.court_string,
            'date_filed': request.date_filed,
            'judges': request.judges
        }
        
        # Run processing in background
        background_tasks.add_task(
            flp.process_document_comprehensive,
            Path(request.file_path),
            metadata
        )
        
        conn.close()
        
        return {
            "status": "processing started",
            "file_path": request.file_path,
            "case_name": request.case_name,
            "tools": [
                "Courts-DB",
                "X-Ray",
                "Eyecite",
                "Reporters-DB",
                "Judge-pics"
            ]
        }
        
    except Exception as e:
        logger.error(f"Error starting comprehensive processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Statistics endpoints
@app.get("/stats/overview")
async def get_statistics():
    """Get overview statistics of processed documents"""
    try:
        conn = get_db_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # Get various statistics
            stats = {}
            
            # Total documents processed
            cursor.execute("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN has_bad_redactions THEN 1 END) as with_bad_redactions
                FROM court_data.processed_documents_flp
            """)
            doc_stats = cursor.fetchone()
            stats['documents'] = doc_stats
            
            # Courts represented
            cursor.execute("""
                SELECT COUNT(DISTINCT court_id) as unique_courts
                FROM court_data.processed_documents_flp
                WHERE court_id IS NOT NULL
            """)
            stats['courts'] = cursor.fetchone()
            
            # Judges with photos
            cursor.execute("""
                SELECT COUNT(*) as total_judges,
                       COUNT(CASE WHEN photo_url IS NOT NULL THEN 1 END) as with_photos
                FROM court_data.judges
            """)
            stats['judges'] = cursor.fetchone()
            
            # Citation statistics
            cursor.execute("""
                SELECT COUNT(*) as total_citations
                FROM court_data.processed_documents_flp,
                     jsonb_array_elements(normalized_citations) as citation
                WHERE normalized_citations IS NOT NULL
            """)
            stats['citations'] = cursor.fetchone()
            
        conn.close()
        
        return {
            "statistics": stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Run the API
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)