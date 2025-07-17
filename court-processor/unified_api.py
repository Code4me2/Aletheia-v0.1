"""
Unified API for CL→FLP→Unstructured→PostgreSQL Pipeline
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime
import logging

from services.unified_document_processor import (
    UnifiedDocumentProcessor,
    DeduplicationManager
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Unified Court Document Processor API",
    description="API for processing court documents through CL→FLP→Unstructured→PostgreSQL pipeline",
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
processor = UnifiedDocumentProcessor()


# Request/Response models
class BatchProcessRequest(BaseModel):
    court_id: Optional[str] = Field(None, description="Court ID to filter by")
    date_filed_after: Optional[str] = Field(None, description="Filter opinions filed after this date (YYYY-MM-DD)")
    max_documents: int = Field(100, description="Maximum documents to process", ge=1, le=1000)
    
class BatchProcessResponse(BaseModel):
    total_fetched: int
    new_documents: int
    duplicates: int
    errors: int
    processing_time: str
    error: Optional[str] = None

class SingleDocumentRequest(BaseModel):
    cl_document: Dict = Field(..., description="CourtListener document to process")

class SingleDocumentResponse(BaseModel):
    success: bool
    saved_id: Optional[int] = None
    document_hash: Optional[str] = None
    error: Optional[str] = None
    processing_details: Optional[Dict] = None

class DeduplicationCheckRequest(BaseModel):
    documents: List[Dict] = Field(..., description="List of documents to check for duplicates")

class DeduplicationCheckResponse(BaseModel):
    total_documents: int
    duplicates: List[str]
    new_documents: List[str]

class PipelineStatusResponse(BaseModel):
    status: str
    total_documents_processed: int
    active_processing: bool
    last_processing_time: Optional[str]
    deduplication_stats: Dict


# API Endpoints
@app.get("/", response_model=Dict[str, str])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Unified Court Document Processor",
        "version": "1.0.0"
    }


@app.post("/process/batch", response_model=BatchProcessResponse)
async def process_batch(
    request: BatchProcessRequest,
    background_tasks: BackgroundTasks
):
    """
    Process a batch of documents from CourtListener
    
    This endpoint fetches documents from CourtListener and processes them
    through the FLP enhancement and Unstructured.io pipeline before
    storing in PostgreSQL with deduplication.
    """
    try:
        result = await processor.process_courtlistener_batch(
            court_id=request.court_id,
            date_filed_after=request.date_filed_after,
            max_documents=request.max_documents
        )
        
        return BatchProcessResponse(**result)
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process/single", response_model=SingleDocumentResponse)
async def process_single_document(request: SingleDocumentRequest):
    """
    Process a single CourtListener document
    
    Useful for reprocessing or handling specific documents.
    """
    try:
        # Check for duplicate first
        dedup_manager = processor.dedup_manager
        if dedup_manager.is_duplicate(request.cl_document):
            doc_hash = dedup_manager.generate_hash(request.cl_document)
            return SingleDocumentResponse(
                success=False,
                document_hash=doc_hash,
                error="Document is a duplicate"
            )
        
        # Process document
        result = await processor.process_single_document(request.cl_document)
        
        if result.get('saved_id'):
            return SingleDocumentResponse(
                success=True,
                saved_id=result['saved_id'],
                document_hash=dedup_manager.generate_hash(request.cl_document),
                processing_details={
                    'citations_found': len(result.get('citations', [])),
                    'has_judge_info': bool(result.get('judge_info')),
                    'has_structured_elements': bool(result.get('structured_elements')),
                    'processing_timestamps': {
                        'flp': result.get('flp_processing_timestamp'),
                        'unstructured': result.get('structured_elements', {}).get('processing_timestamp')
                    }
                }
            )
        else:
            return SingleDocumentResponse(
                success=False,
                error=result.get('error', 'Unknown error occurred')
            )
            
    except Exception as e:
        logger.error(f"Single document processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/deduplication/check", response_model=DeduplicationCheckResponse)
async def check_duplicates(request: DeduplicationCheckRequest):
    """
    Check which documents in a list would be duplicates
    
    Useful for pre-filtering before processing.
    """
    try:
        dedup_manager = processor.dedup_manager
        duplicates = []
        new_documents = []
        
        for doc in request.documents:
            doc_hash = dedup_manager.generate_hash(doc)
            if dedup_manager.is_duplicate(doc):
                duplicates.append(doc_hash)
            else:
                new_documents.append(doc_hash)
        
        return DeduplicationCheckResponse(
            total_documents=len(request.documents),
            duplicates=duplicates,
            new_documents=new_documents
        )
        
    except Exception as e:
        logger.error(f"Deduplication check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/pipeline/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Get current status of the processing pipeline
    """
    try:
        dedup_manager = processor.dedup_manager
        
        # Get document count from database
        from services.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM court_data.opinions_unified")
        total_docs = cursor.fetchone()[0]
        conn.close()
        
        return PipelineStatusResponse(
            status="operational",
            total_documents_processed=total_docs,
            active_processing=False,  # Would need to implement tracking
            last_processing_time=None,  # Would need to implement tracking
            deduplication_stats={
                "total_hashes_cached": len(dedup_manager.processed_hashes),
                "memory_usage_estimate": f"{len(dedup_manager.processed_hashes) * 64 / 1024:.2f} KB"
            }
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return PipelineStatusResponse(
            status="error",
            total_documents_processed=0,
            active_processing=False,
            last_processing_time=None,
            deduplication_stats={"error": str(e)}
        )


@app.post("/pipeline/refresh-dedup-cache")
async def refresh_deduplication_cache():
    """
    Refresh the deduplication cache from database
    
    Useful if the cache gets out of sync.
    """
    try:
        processor.dedup_manager._load_existing_hashes()
        hash_count = len(processor.dedup_manager.processed_hashes)
        
        return {
            "success": True,
            "message": f"Deduplication cache refreshed with {hash_count} hashes"
        }
        
    except Exception as e:
        logger.error(f"Cache refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Background task for continuous processing (optional)
async def continuous_processing_task(
    court_id: Optional[str] = None,
    batch_size: int = 100,
    delay_seconds: int = 300
):
    """
    Background task for continuous document processing
    
    This would run periodically to fetch and process new documents.
    """
    import asyncio
    
    while True:
        try:
            # Process a batch
            result = await processor.process_courtlistener_batch(
                court_id=court_id,
                date_filed_after=None,  # Could track last processed date
                max_documents=batch_size
            )
            
            logger.info(f"Continuous processing completed: {result}")
            
            # Wait before next batch
            await asyncio.sleep(delay_seconds)
            
        except Exception as e:
            logger.error(f"Continuous processing error: {e}")
            await asyncio.sleep(delay_seconds)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)