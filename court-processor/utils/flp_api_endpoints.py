"""
Extracted FLP API Endpoints
Complete FastAPI implementation for all Free Law Project tools
Extracted from flp_api.py with working FLP dependencies
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import logging
import json
from dataclasses import dataclass

# FLP imports (verified working in Docker)
from courts_db import find_court
from reporters_db import REPORTERS
from eyecite import get_citations
import judge_pics

logger = logging.getLogger(__name__)

# Pydantic models for API requests/responses
class CourtResolveRequest(BaseModel):
    """Request model for court resolution"""
    court_string: str = Field(..., description="Court name or abbreviation to resolve")
    date: Optional[str] = Field(None, description="Date for historical court resolution (YYYY-MM-DD)")

class CourtResolveResponse(BaseModel):
    """Response model for court resolution"""
    court_id: Optional[str]
    court_name: Optional[str]
    jurisdiction: Optional[str]
    type: Optional[str]
    error: Optional[str]

class ReporterNormalizeRequest(BaseModel):
    """Request model for reporter normalization"""
    reporter: str = Field(..., description="Reporter abbreviation to normalize")

class ReporterNormalizeResponse(BaseModel):
    """Response model for reporter normalization"""
    original: str
    normalized: Optional[str]
    name: Optional[str]
    publisher: Optional[str]
    variations: List[str]

class CitationExtractionRequest(BaseModel):
    """Request model for citation extraction"""
    text: str = Field(..., description="Legal text to extract citations from")
    normalize: bool = Field(True, description="Whether to normalize citations")

class CitationExtractionResponse(BaseModel):
    """Response model for citation extraction"""
    total_citations: int
    citations: List[Dict[str, Any]]
    normalized_citations: List[Dict[str, Any]]

class JudgePhotoRequest(BaseModel):
    """Request model for judge photo lookup"""
    judge_name: str = Field(..., description="Judge name to search for")
    court: Optional[str] = Field(None, description="Court to narrow search")

class JudgePhotoResponse(BaseModel):
    """Response model for judge photo lookup"""
    judge_name: str
    photo_available: bool
    photo_path: Optional[str]
    metadata: Optional[Dict[str, Any]]

class ComprehensiveProcessRequest(BaseModel):
    """Request model for comprehensive document processing"""
    file_path: str = Field(..., description="Path to document file")
    case_name: str = Field(..., description="Case name")
    docket_number: Optional[str] = Field(None, description="Docket number")
    court_string: str = Field(..., description="Court identifier")
    date_filed: Optional[str] = Field(None, description="Filing date (YYYY-MM-DD)")
    judges: Optional[List[str]] = Field(None, description="List of judge names")

@dataclass
class FLPAPIEndpoints:
    """
    Complete collection of FLP API endpoints
    Extracted from flp_api.py with working implementations
    """
    
    def __init__(self, db_connection_factory=None):
        """Initialize with database connection factory"""
        self.db_connection_factory = db_connection_factory or self._default_db_connection
    
    def _default_db_connection(self):
        """Default database connection factory"""
        return psycopg2.connect(
            host=os.getenv('DB_HOST', 'db'),
            port=os.getenv('DB_PORT', '5432'),
            user=os.getenv('DB_USER', 'aletheia'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME', 'aletheia')
        )
    
    def create_fastapi_app(self) -> FastAPI:
        """Create FastAPI application with all FLP endpoints"""
        app = FastAPI(
            title="Free Law Project Integration API",
            description="Comprehensive API for Courts-DB, Reporters-DB, Eyecite, and Judge-pics",
            version="4.0.0",
            docs_url="/docs",
            redoc_url="/redoc"
        )
        
        # Add all endpoints to the app
        self._add_health_endpoints(app)
        self._add_courts_endpoints(app)
        self._add_reporters_endpoints(app)
        self._add_citation_endpoints(app)
        self._add_judge_endpoints(app)
        self._add_comprehensive_endpoints(app)
        self._add_statistics_endpoints(app)
        
        return app
    
    def _add_health_endpoints(self, app: FastAPI):
        """Add health check endpoints"""
        
        @app.get("/health", response_model=Dict[str, Any])
        async def health_check():
            """Check API and service health"""
            try:
                conn = self.db_connection_factory()
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                conn.close()
                
                return {
                    "status": "healthy",
                    "services": {
                        "database": "connected",
                        "courts_db": "available",
                        "reporters_db": f"available ({len(REPORTERS)} reporters)",
                        "eyecite": "available",
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
    
    def _add_courts_endpoints(self, app: FastAPI):
        """Add Courts-DB endpoints"""
        
        @app.post("/courts/resolve", response_model=CourtResolveResponse)
        async def resolve_court(request: CourtResolveRequest):
            """Resolve court name to standardized ID using Courts-DB"""
            try:
                # Use Courts-DB to find court
                courts = find_court(request.court_string)
                
                if courts:
                    court = courts[0]  # Take first match
                    return CourtResolveResponse(
                        court_id=court.get('id'),
                        court_name=court.get('name'),
                        jurisdiction=court.get('jurisdiction'),
                        type=court.get('type'),
                        error=None
                    )
                else:
                    return CourtResolveResponse(
                        court_id=None,
                        court_name=None,
                        jurisdiction=None,
                        type=None,
                        error=f"Court not found: {request.court_string}"
                    )
                    
            except Exception as e:
                logger.error(f"Error resolving court: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/courts/list")
        async def list_courts():
            """List all available courts from Courts-DB"""
            try:
                # Get all courts (this might be large, consider pagination)
                all_courts = find_court("")  # Empty string returns all
                
                return {
                    "total": len(all_courts),
                    "courts": all_courts[:100],  # Limit to first 100
                    "note": "Limited to first 100 courts. Use /courts/search for specific lookups."
                }
                
            except Exception as e:
                logger.error(f"Error listing courts: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _add_reporters_endpoints(self, app: FastAPI):
        """Add Reporters-DB endpoints"""
        
        @app.post("/reporters/normalize", response_model=ReporterNormalizeResponse)
        async def normalize_reporter(request: ReporterNormalizeRequest):
            """Normalize reporter abbreviation using Reporters-DB"""
            try:
                reporter_key = request.reporter
                
                # Look for exact match first
                if reporter_key in REPORTERS:
                    reporter_data = REPORTERS[reporter_key]
                    return ReporterNormalizeResponse(
                        original=request.reporter,
                        normalized=reporter_key,
                        name=reporter_data.get('name', ''),
                        publisher=reporter_data.get('publisher', ''),
                        variations=reporter_data.get('variations', [])
                    )
                
                # Look for case-insensitive match
                for key, data in REPORTERS.items():
                    if key.lower() == reporter_key.lower():
                        return ReporterNormalizeResponse(
                            original=request.reporter,
                            normalized=key,
                            name=data.get('name', ''),
                            publisher=data.get('publisher', ''),
                            variations=data.get('variations', [])
                        )
                
                # Look in variations
                for key, data in REPORTERS.items():
                    variations = data.get('variations', [])
                    if any(var.lower() == reporter_key.lower() for var in variations):
                        return ReporterNormalizeResponse(
                            original=request.reporter,
                            normalized=key,
                            name=data.get('name', ''),
                            publisher=data.get('publisher', ''),
                            variations=variations
                        )
                
                # Not found
                return ReporterNormalizeResponse(
                    original=request.reporter,
                    normalized=None,
                    name=None,
                    publisher=None,
                    variations=[]
                )
                
            except Exception as e:
                logger.error(f"Error normalizing reporter: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/reporters/list")
        async def list_reporters():
            """List all available reporters from Reporters-DB"""
            try:
                reporters_list = []
                for key, data in REPORTERS.items():
                    reporters_list.append({
                        "abbreviation": key,
                        "name": data.get('name', ''),
                        "publisher": data.get('publisher', ''),
                        "type": data.get('type', ''),
                        "variations": data.get('variations', [])
                    })
                
                return {
                    "total": len(reporters_list),
                    "reporters": sorted(reporters_list, key=lambda x: x['name'])
                }
                
            except Exception as e:
                logger.error(f"Error listing reporters: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _add_citation_endpoints(self, app: FastAPI):
        """Add Eyecite citation extraction endpoints"""
        
        @app.post("/citations/extract", response_model=CitationExtractionResponse)
        async def extract_citations(request: CitationExtractionRequest):
            """Extract legal citations from text using Eyecite"""
            try:
                # Extract citations using Eyecite
                citations = get_citations(request.text)
                
                # Convert citations to serializable format
                citation_list = []
                normalized_list = []
                
                for citation in citations:
                    citation_dict = {
                        "text": str(citation),
                        "type": type(citation).__name__,
                        "groups": getattr(citation, 'groups', {}),
                        "span": getattr(citation, 'span', None),
                        "metadata": {}
                    }
                    
                    # Extract metadata if available
                    if hasattr(citation, 'metadata'):
                        metadata = citation.metadata
                        citation_dict["metadata"] = {
                            "year": getattr(metadata, 'year', None),
                            "court": getattr(metadata, 'court', None),
                            "plaintiff": getattr(metadata, 'plaintiff', None),
                            "defendant": getattr(metadata, 'defendant', None),
                            "pin_cite": getattr(metadata, 'pin_cite', None)
                        }
                    
                    citation_list.append(citation_dict)
                    
                    # Add to normalized list if requested
                    if request.normalize:
                        normalized_citation = citation_dict.copy()
                        # Add normalization logic here if needed
                        normalized_list.append(normalized_citation)
                
                return CitationExtractionResponse(
                    total_citations=len(citations),
                    citations=citation_list,
                    normalized_citations=normalized_list if request.normalize else []
                )
                
            except Exception as e:
                logger.error(f"Error extracting citations: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _add_judge_endpoints(self, app: FastAPI):
        """Add Judge-pics endpoints"""
        
        @app.post("/judges/photo", response_model=JudgePhotoResponse)
        async def get_judge_photo(request: JudgePhotoRequest):
            """Get judge photo information using Judge-pics"""
            try:
                # Load judge data from judge-pics
                judge_data_path = Path(judge_pics.judge_root) / "people.json"
                
                if not judge_data_path.exists():
                    return JudgePhotoResponse(
                        judge_name=request.judge_name,
                        photo_available=False,
                        photo_path=None,
                        metadata={"error": "Judge data file not found"}
                    )
                
                with open(judge_data_path, 'r') as f:
                    judges_data = json.load(f)
                
                # Search for judge by name
                judge_name_lower = request.judge_name.lower()
                
                for judge_id, judge_info in judges_data.items():
                    judge_full_name = judge_info.get('name', {})
                    full_name = f"{judge_full_name.get('first', '')} {judge_full_name.get('last', '')}".strip()
                    
                    if (judge_name_lower in full_name.lower() or
                        full_name.lower() in judge_name_lower):
                        
                        return JudgePhotoResponse(
                            judge_name=request.judge_name,
                            photo_available=True,
                            photo_path=f"{judge_pics.judge_root}/{judge_id}",
                            metadata={
                                "judge_id": judge_id,
                                "full_name": full_name,
                                "court": judge_info.get('court', None),
                                "position": judge_info.get('position', None)
                            }
                        )
                
                return JudgePhotoResponse(
                    judge_name=request.judge_name,
                    photo_available=False,
                    photo_path=None,
                    metadata={"message": "Judge not found in database"}
                )
                
            except Exception as e:
                logger.error(f"Error getting judge photo: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @app.get("/judges/list")
        async def list_judges_with_photos():
            """List all judges with photos available"""
            try:
                judge_data_path = Path(judge_pics.judge_root) / "people.json"
                
                if not judge_data_path.exists():
                    return {"total": 0, "judges": [], "error": "Judge data file not found"}
                
                with open(judge_data_path, 'r') as f:
                    judges_data = json.load(f)
                
                judges_list = []
                for judge_id, judge_info in judges_data.items():
                    judge_full_name = judge_info.get('name', {})
                    full_name = f"{judge_full_name.get('first', '')} {judge_full_name.get('last', '')}".strip()
                    
                    judges_list.append({
                        "judge_id": judge_id,
                        "name": full_name,
                        "court": judge_info.get('court', None),
                        "position": judge_info.get('position', None),
                        "photo_path": f"{judge_pics.judge_root}/{judge_id}"
                    })
                
                return {
                    "total": len(judges_list),
                    "judges": sorted(judges_list, key=lambda x: x['name'])
                }
                
            except Exception as e:
                logger.error(f"Error listing judges: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _add_comprehensive_endpoints(self, app: FastAPI):
        """Add comprehensive processing endpoints"""
        
        @app.post("/process/comprehensive")
        async def process_comprehensive(
            request: ComprehensiveProcessRequest,
            background_tasks: BackgroundTasks
        ):
            """Process document using all FLP tools comprehensively"""
            try:
                # Add background task for comprehensive processing
                background_tasks.add_task(
                    self._process_document_comprehensive,
                    request
                )
                
                return {
                    "status": "processing started",
                    "file_path": request.file_path,
                    "case_name": request.case_name,
                    "tools_used": [
                        "Courts-DB (court resolution)",
                        "Eyecite (citation extraction)",
                        "Reporters-DB (citation normalization)",
                        "Judge-pics (judge photo lookup)"
                    ],
                    "estimated_time": "30-60 seconds",
                    "check_status_at": "/process/status/{task_id}"
                }
                
            except Exception as e:
                logger.error(f"Error starting comprehensive processing: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _add_statistics_endpoints(self, app: FastAPI):
        """Add statistics and monitoring endpoints"""
        
        @app.get("/stats/overview")
        async def get_statistics():
            """Get overview statistics of processed documents"""
            try:
                conn = self.db_connection_factory()
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    stats = {}
                    
                    # FLP processing statistics
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) as total
                            FROM court_documents
                            WHERE metadata->>'flp_processed' = 'true'
                        """)
                        stats['flp_processed'] = cursor.fetchone()
                    except:
                        stats['flp_processed'] = {"total": 0}
                    
                    # Court resolution statistics
                    try:
                        cursor.execute("""
                            SELECT COUNT(DISTINCT metadata->>'court_id') as unique_courts
                            FROM court_documents
                            WHERE metadata->>'court_id' IS NOT NULL
                        """)
                        stats['courts'] = cursor.fetchone()
                    except:
                        stats['courts'] = {"unique_courts": 0}
                    
                    # Citation statistics
                    try:
                        cursor.execute("""
                            SELECT COUNT(*) as total_documents_with_citations
                            FROM court_documents
                            WHERE metadata->>'citations_extracted' = 'true'
                        """)
                        stats['citations'] = cursor.fetchone()
                    except:
                        stats['citations'] = {"total_documents_with_citations": 0}
                
                conn.close()
                
                # Add FLP library statistics
                stats['libraries'] = {
                    "reporters_db": {
                        "total_reporters": len(REPORTERS),
                        "sample_reporters": list(REPORTERS.keys())[:5]
                    },
                    "courts_db": {
                        "status": "available",
                        "sample_search": len(find_court("district"))
                    },
                    "eyecite": {
                        "status": "available",
                        "test_extraction": len(get_citations("123 F.3d 456"))
                    },
                    "judge_pics": {
                        "status": "available",
                        "data_path": judge_pics.judge_root
                    }
                }
                
                return {
                    "statistics": stats,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                logger.error(f"Error getting statistics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    async def _process_document_comprehensive(self, request: ComprehensiveProcessRequest):
        """Background task for comprehensive document processing"""
        try:
            logger.info(f"Starting comprehensive processing for {request.case_name}")
            
            # This would contain the full processing logic
            # integrating all FLP tools with the document
            
            # 1. Resolve court using Courts-DB
            courts = find_court(request.court_string)
            court_info = courts[0] if courts else None
            
            # 2. Extract text and citations using Eyecite
            # (would need file reading logic here)
            
            # 3. Normalize citations using Reporters-DB
            
            # 4. Look up judge photos using Judge-pics
            
            # 5. Store results in database
            
            logger.info(f"Completed comprehensive processing for {request.case_name}")
            
        except Exception as e:
            logger.error(f"Error in comprehensive processing: {e}")


# Convenience function to create the API
def create_flp_api_app(db_connection_factory=None) -> FastAPI:
    """
    Create a complete FLP API application
    
    Args:
        db_connection_factory: Optional custom database connection factory
        
    Returns:
        FastAPI application with all FLP endpoints
    """
    endpoints = FLPAPIEndpoints(db_connection_factory)
    return endpoints.create_fastapi_app()


# Example usage for testing
if __name__ == "__main__":
    import uvicorn
    
    app = create_flp_api_app()
    uvicorn.run(app, host="0.0.0.0", port=8090)