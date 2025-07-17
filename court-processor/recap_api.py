"""
RECAP API for processing RECAP bulk data
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import logging

from services.recap_processor import RECAPProcessor
from services.courtlistener_service import CourtListenerService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="RECAP Document Processor API",
    description="API for processing RECAP court documents with focus on IP cases and transcripts",
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

# Initialize processor
processor = RECAPProcessor()


# Request/Response models
class RECAPDocketRequest(BaseModel):
    docket_id: int = Field(..., description="CourtListener docket ID")
    include_documents: bool = Field(True, description="Process associated documents")

class RECAPSearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    court_ids: Optional[List[str]] = Field(None, description="List of court IDs to search")
    max_results: int = Field(100, description="Maximum results to process", ge=1, le=500)

class IPCasesBatchRequest(BaseModel):
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    courts: Optional[List[str]] = Field(None, description="Court IDs (defaults to IP-heavy courts)")
    transcripts_only: bool = Field(False, description="Only process transcript documents")

class BulkDownloadRequest(BaseModel):
    nature_of_suit: List[str] = Field(
        default=['830', '840'], 
        description="Nature of suit codes (830=Patent, 840=Trademark)"
    )
    date_filed_after: str = Field(..., description="Filter cases filed after this date")
    courts: Optional[List[str]] = Field(None, description="Specific courts to include")
    max_dockets: int = Field(100, description="Maximum dockets to process", ge=1, le=1000)


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "RECAP Document Processor",
        "version": "1.0.0",
        "note": "Specialized for IP cases and transcript processing"
    }


@app.get("/recap/courts", response_model=Dict[str, List[str]])
async def get_recap_courts():
    """Get list of courts with good RECAP coverage for IP cases
    
    Note: Actual RECAP document access requires special API permissions.
    """
    return {
        "federal_circuit": CourtListenerService.IP_COURTS['federal_circuit'],
        "district_heavy_ip": CourtListenerService.IP_COURTS['district_heavy_ip'],
        "all_courts_url": "https://www.courtlistener.com/api/rest/v4/courts/",
        "note": "RECAP document access requires special permissions from CourtListener"
    }


@app.get("/recap/nature-of-suit", response_model=Dict[str, str])
async def get_nature_of_suit_codes():
    """Get IP-related nature of suit codes"""
    return CourtListenerService.IP_NATURE_OF_SUIT


@app.post("/recap/process-docket", response_model=Dict)
async def process_recap_docket(request: RECAPDocketRequest):
    """
    Process a specific RECAP docket and its documents
    
    This endpoint fetches a docket from CourtListener and processes
    all associated documents through the FLP→Unstructured pipeline.
    """
    try:
        # Get docket data with documents
        cl_service = processor.cl_service
        docket_data = await cl_service.get_docket_entries_with_documents(
            request.docket_id
        )
        
        if not docket_data:
            raise HTTPException(status_code=404, detail="Docket not found")
        
        # Process the docket
        result = await processor.process_recap_docket(docket_data)
        
        return {
            "success": True,
            "docket_id": request.docket_id,
            "case_name": docket_data.get('case_name'),
            "court": docket_data.get('court'),
            "documents_found": result.get('total_documents', 0),
            "documents_processed": result.get('documents_processed', 0),
            "is_ip_case": result.get('is_ip_case', False),
            "errors": result.get('errors', [])
        }
        
    except Exception as e:
        logger.error(f"Failed to process docket {request.docket_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recap/search-and-process", response_model=Dict)
async def search_and_process_recap(request: RECAPSearchRequest):
    """
    Search RECAP documents and process results
    
    Performs full-text search across RECAP documents and processes
    matching results through the pipeline.
    """
    try:
        result = await processor.search_and_process_recap(
            search_query=request.query,
            court_ids=request.court_ids,
            max_results=request.max_results
        )
        
        return {
            "success": True,
            "query": request.query,
            "documents_found": result['documents_found'],
            "documents_processed": result['documents_processed'],
            "errors": result.get('errors', [])
        }
        
    except Exception as e:
        logger.error(f"Search and process failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recap/ip-cases-batch", response_model=Dict)
async def process_ip_cases_batch(request: IPCasesBatchRequest):
    """
    Batch process IP-related cases from RECAP
    
    Fetches and processes patent, trademark, and copyright cases
    from specified courts and date range.
    """
    try:
        stats = await processor.process_ip_cases_batch(
            start_date=request.start_date,
            end_date=request.end_date,
            courts=request.courts,
            include_transcripts_only=request.transcripts_only
        )
        
        return {
            "success": not bool(stats.get('error')),
            "stats": stats,
            "recap_summary": stats.get('recap_stats', {})
        }
        
    except Exception as e:
        logger.error(f"IP batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recap/recent-transcripts")
async def get_recent_transcripts(
    days_back: int = Query(7, description="Days to look back"),
    courts: Optional[List[str]] = Query(None, description="Court IDs to filter")
):
    """
    Find recent transcript documents in RECAP
    
    Searches for transcript documents filed in the last N days.
    """
    try:
        start_date = (date.today() - timedelta(days=days_back)).isoformat()
        
        # Search for transcripts
        cl_service = processor.cl_service
        
        # Search with transcript-related terms
        transcript_results = await cl_service.search_recap(
            query='transcript OR hearing OR "oral argument" OR deposition',
            court_ids=courts,
            date_range=(start_date, date.today().isoformat()),
            max_results=200
        )
        
        # Filter to likely transcripts
        transcripts = []
        for result in transcript_results:
            if processor._is_transcript(result):
                transcripts.append({
                    'id': result.get('id'),
                    'case_name': result.get('caseName'),
                    'court': result.get('court'),
                    'date_filed': result.get('dateFiled'),
                    'description': result.get('snippet', '')[:200]
                })
        
        return {
            "success": True,
            "days_back": days_back,
            "transcript_count": len(transcripts),
            "transcripts": transcripts[:50]  # Limit response size
        }
        
    except Exception as e:
        logger.error(f"Failed to get recent transcripts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recap/bulk-download-metadata", response_model=Dict)
async def get_bulk_download_metadata(request: BulkDownloadRequest):
    """
    Get metadata for bulk download of RECAP documents
    
    Returns URLs and metadata for bulk data files matching criteria.
    This uses the CourtListener bulk data service.
    """
    try:
        # Note: Actual bulk data endpoint would need implementation
        # This is a placeholder showing the structure
        
        bulk_info = {
            "bulk_data_url": "https://www.courtlistener.com/api/bulk-data/",
            "update_frequency": "monthly",
            "last_update": "Last day of each month",
            "filtering_note": "Download full dumps and filter locally for best performance",
            "recommended_approach": [
                "1. Download dockets CSV for courts of interest",
                "2. Filter by nature_of_suit codes locally", 
                "3. Use docket IDs to fetch specific documents via API"
            ],
            "request_parameters": {
                "nature_of_suit": request.nature_of_suit,
                "date_filed_after": request.date_filed_after,
                "courts": request.courts or CourtListenerService.IP_COURTS['district_heavy_ip']
            }
        }
        
        return {
            "success": True,
            "bulk_download_info": bulk_info,
            "note": "Use cursor pagination for large API requests as shown in documentation"
        }
        
    except Exception as e:
        logger.error(f"Failed to get bulk metadata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recap/stats", response_model=Dict)
async def get_recap_stats():
    """Get current RECAP processing statistics"""
    return {
        "stats": processor.recap_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8091)