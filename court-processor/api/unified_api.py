"""
Unified API for CL→FLP→Unstructured→PostgreSQL Pipeline
Now with separated Opinion Search and RECAP Docket retrieval
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import (
    UnifiedDocumentProcessor,
    DeduplicationManager
)
from services.document_ingestion_service import DocumentIngestionService
from services.unified_collection_service import UnifiedCollectionService
from services.recap_docket_service import RECAPDocketService
from services.recap.webhook_handler import RECAPWebhookHandler

# Import database search endpoints
try:
    from api.database_search_endpoint import router as database_router
    database_router_available = True
except ImportError:
    # Try alternative import path
    try:
        from database_search_endpoint import router as database_router
        database_router_available = True
    except ImportError:
        database_router_available = False
        logger.warning("Database search endpoint not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Unified Court Document Processor API",
    description="API for searching and processing court documents with separated Opinion and RECAP paths",
    version="2.0.0"
)

# Include database search router if available
if database_router_available:
    app.include_router(database_router)
    logger.info("Database search endpoints loaded")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors and services
processor = UnifiedDocumentProcessor()
recap_service = None
webhook_handler = None


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


# New models for Opinion Search and RECAP functionality
class OpinionSearchRequest(BaseModel):
    """Request model for broad opinion searches"""
    query: Optional[str] = Field(None, description="Search query for full-text search")
    court_ids: List[str] = Field(..., description="List of court IDs to search")
    date_filed_after: Optional[str] = Field(None, description="Filter opinions filed after this date (YYYY-MM-DD)")
    date_filed_before: Optional[str] = Field(None, description="Filter opinions filed before this date (YYYY-MM-DD)")
    document_types: List[str] = Field(default=['opinion'], description="Document types to search")
    max_results: int = Field(100, description="Maximum results to return", ge=1, le=1000)
    nature_of_suit: Optional[List[str]] = Field(None, description="Nature of suit codes (for IP cases)")


class OpinionSearchResponse(BaseModel):
    """Response model for opinion searches"""
    success: bool
    total_results: int
    documents_processed: int
    search_criteria: Dict[str, Any]
    processing_time: str
    results: List[Dict[str, Any]]
    error: Optional[str] = None


class RECAPDocketRequest(BaseModel):
    """Request model for specific RECAP docket retrieval"""
    docket_number: str = Field(..., description="Exact docket number (e.g., '2:2024cv00181')")
    court: str = Field(..., description="Court ID (e.g., 'txed')")
    include_documents: bool = Field(True, description="Whether to download associated PDFs")
    max_documents: Optional[int] = Field(None, description="Maximum PDFs to download")
    date_start: Optional[str] = Field(None, description="Start date for docket entries (YYYY-MM-DD)")
    date_end: Optional[str] = Field(None, description="End date for docket entries (YYYY-MM-DD)")
    force_purchase: bool = Field(False, description="Purchase from PACER even if in RECAP")


class RECAPDocketResponse(BaseModel):
    """Response model for RECAP docket retrieval"""
    success: bool
    docket_number: str
    court: str
    case_name: Optional[str] = None
    docket_id: Optional[int] = None
    in_recap: bool
    purchased_from_pacer: bool
    purchase_cost: Optional[float] = None
    documents_downloaded: int
    webhook_registered: bool = False
    request_id: Optional[int] = None
    status_url: Optional[str] = None
    error: Optional[str] = None


class ProcessingStatusResponse(BaseModel):
    """Response for checking RECAP processing status"""
    request_id: int
    status: str
    completed: bool
    docket_id: Optional[int] = None
    documents_processed: int
    error: Optional[str] = None


# API Endpoints
@app.get("/", response_model=Dict[str, Any])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Unified Court Document Processor",
        "version": "2.0.0",
        "capabilities": {
            "processing": "operational",
            "opinion_search": "operational",
            "recap_docket": "operational",
            "deduplication": "operational"
        }
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


# Opinion Search Endpoints
@app.post("/search/opinions", response_model=OpinionSearchResponse)
async def search_opinions(request: OpinionSearchRequest):
    """
    Search for court opinions using broad criteria
    
    This endpoint searches published court opinions from the CourtListener
    Search API, which returns full text content including 020lead documents.
    """
    start_time = datetime.now()
    
    try:
        # Use UnifiedCollectionService which actually gets content
        service = UnifiedCollectionService()
        
        # Map API request to collection parameters
        # Handle multiple court IDs by processing first one (API limitation)
        court_id = request.court_ids[0] if request.court_ids else None
        
        # Build custom query from request parameters
        custom_query = request.query
        if request.nature_of_suit:
            # Add nature of suit to query
            custom_query = f"{custom_query} nature_of_suit:({' OR '.join(request.nature_of_suit)})" if custom_query else f"nature_of_suit:({' OR '.join(request.nature_of_suit)})"
        
        # Collect documents using the working service
        results = await service.collect_documents(
            court_id=court_id,
            judge_name=None,  # Use custom_query for judge searches
            date_after=request.date_filed_after,
            date_before=request.date_filed_before,
            max_documents=request.max_results,
            custom_query=custom_query,
            run_pipeline=False,  # Don't run pipeline for API responses
            extract_pdfs=True,   # Do extract PDFs if needed
            store_to_db=True     # Store for future use
        )
        
        # Extract documents with content
        processed_docs = results.get('documents', [])
        
        # Ensure documents have proper structure for API response
        api_documents = []
        for doc in processed_docs:
            api_doc = {
                'case_number': doc.get('case_number', ''),
                'case_name': doc.get('case_name', ''),
                'document_type': doc.get('document_type', 'opinion'),
                'content': doc.get('content', ''),
                'metadata': doc.get('metadata', {})
            }
            # Add content length for debugging
            api_doc['metadata']['content_length'] = len(api_doc['content'])
            api_documents.append(api_doc)
        
        processing_time = str(datetime.now() - start_time)
        
        return OpinionSearchResponse(
            success=results.get('success', False),
            total_results=results.get('statistics', {}).get('total_fetched', 0),
            documents_processed=len(api_documents),
            search_criteria={
                'query': request.query,
                'courts': request.court_ids,
                'date_range': {
                    'after': request.date_filed_after,
                    'before': request.date_filed_before
                }
            },
            processing_time=processing_time,
            results=api_documents
        )
            
    except Exception as e:
        logger.error(f"Opinion search failed: {e}")
        return OpinionSearchResponse(
            success=False,
            total_results=0,
            documents_processed=0,
            search_criteria=request.dict(),
            processing_time=str(datetime.now() - start_time),
            results=[],
            error=str(e)
        )


# RECAP Docket Endpoints
@app.post("/recap/docket", response_model=RECAPDocketResponse)
async def fetch_recap_docket(request: RECAPDocketRequest, background_tasks: BackgroundTasks):
    """
    Fetch a specific docket from RECAP/PACER
    
    This endpoint retrieves a specific docket by number. It will:
    1. Check if the docket is already in RECAP (free)
    2. If not found and force_purchase=True, purchase from PACER
    3. Register webhook for async processing
    4. Return status and tracking information
    """
    global recap_service
    
    try:
        # Initialize RECAP service if needed
        if not recap_service:
            recap_service = RECAPDocketService(
                cl_token=os.getenv('COURTLISTENER_API_KEY'),
                pacer_username=os.getenv('PACER_USERNAME'),
                pacer_password=os.getenv('PACER_PASSWORD')
            )
        
        # Check RECAP availability first
        is_available = await recap_service.check_recap_availability(
            request.docket_number,
            request.court
        )
        
        if is_available and not request.force_purchase:
            # Fetch from RECAP (free)
            result = await recap_service.fetch_from_recap(
                request.docket_number,
                request.court,
                include_documents=request.include_documents,
                max_documents=request.max_documents
            )
            
            return RECAPDocketResponse(
                success=result.get('success', False),
                docket_number=request.docket_number,
                court=request.court,
                case_name=result.get('case_name'),
                docket_id=result.get('docket_id'),
                in_recap=True,
                purchased_from_pacer=False,
                documents_downloaded=len(result.get('documents', [])),
                error=result.get('error')
            )
        else:
            # Purchase from PACER
            if not os.getenv('PACER_USERNAME'):
                return RECAPDocketResponse(
                    success=False,
                    docket_number=request.docket_number,
                    court=request.court,
                    in_recap=False,
                    purchased_from_pacer=False,
                    documents_downloaded=0,
                    error="PACER credentials not configured"
                )
            
            # Submit PACER purchase request
            purchase_result = await recap_service.purchase_from_pacer(
                request.docket_number,
                request.court,
                include_documents=request.include_documents,
                max_documents=request.max_documents,
                date_start=request.date_start,
                date_end=request.date_end
            )
            
            # Generate status URL
            request_id = purchase_result.get('request_id')
            status_url = f"/recap/status/{request_id}" if request_id else None
            
            return RECAPDocketResponse(
                success=purchase_result.get('submitted', False),
                docket_number=request.docket_number,
                court=request.court,
                in_recap=False,
                purchased_from_pacer=True,
                purchase_cost=purchase_result.get('estimated_cost'),
                documents_downloaded=0,  # Will be updated via webhook
                webhook_registered=purchase_result.get('webhook_registered', False),
                request_id=request_id,
                status_url=status_url,
                error=purchase_result.get('error')
            )
            
    except Exception as e:
        logger.error(f"RECAP docket fetch failed: {e}")
        return RECAPDocketResponse(
            success=False,
            docket_number=request.docket_number,
            court=request.court,
            in_recap=False,
            purchased_from_pacer=False,
            documents_downloaded=0,
            error=str(e)
        )


@app.post("/recap/webhook")
async def handle_recap_webhook(request: Request):
    """
    Handle RECAP webhook notifications
    
    This endpoint receives webhooks from CourtListener when RECAP
    fetch requests complete.
    """
    global webhook_handler
    
    try:
        # Initialize webhook handler if needed
        if not webhook_handler:
            webhook_handler = RECAPWebhookHandler(
                cl_token=os.getenv('COURTLISTENER_API_KEY'),
                download_dir="recap_downloads"
            )
        
        # Parse webhook data
        webhook_data = await request.json()
        
        # Process webhook
        result = await webhook_handler.handle_webhook(webhook_data)
        
        return {
            "status": "processed",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Webhook processing failed: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@app.get("/recap/status/{request_id}", response_model=ProcessingStatusResponse)
async def get_recap_status(request_id: int):
    """
    Check status of a RECAP fetch request
    
    Use this endpoint to poll for completion of PACER purchases.
    """
    global recap_service
    
    try:
        if not recap_service:
            recap_service = RECAPDocketService(
                cl_token=os.getenv('COURTLISTENER_API_KEY'),
                pacer_username=os.getenv('PACER_USERNAME'),
                pacer_password=os.getenv('PACER_PASSWORD')
            )
        
        status = await recap_service.check_request_status(request_id)
        
        return ProcessingStatusResponse(
            request_id=request_id,
            status=status.get('status', 'unknown'),
            completed=status.get('completed', False),
            docket_id=status.get('docket_id'),
            documents_processed=status.get('documents_processed', 0),
            error=status.get('error')
        )
        
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return ProcessingStatusResponse(
            request_id=request_id,
            status='error',
            completed=False,
            documents_processed=0,
            error=str(e)
        )


# Database Search Endpoints - Direct access to existing full-text documents
@app.post("/database/search")
async def search_database(
    document_type: Optional[str] = "020lead",
    judge_name: Optional[str] = None,
    court_id: Optional[str] = None,
    min_content_length: int = 5000,
    limit: int = 10
):
    """
    Search existing database for FULL, UNTRUNCATED court opinions
    
    Returns complete opinion text (10-40KB) with all metadata.
    This does NOT make external API calls - only queries stored documents.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import re
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host='db',
            database='aletheia',
            user='aletheia',
            password='aletheia123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build query
        conditions = ["1=1"]
        params = []
        
        if document_type and document_type != 'all':
            conditions.append("document_type = %s")
            params.append(document_type)
        else:
            conditions.append("document_type IN ('020lead', 'opinion', 'opinion_doctor')")
        
        if judge_name:
            conditions.append("metadata->>'judge_name' ILIKE %s")
            params.append(f'%{judge_name}%')
        
        if court_id:
            conditions.append("metadata->>'court_id' = %s")
            params.append(court_id)
        
        if min_content_length > 0:
            conditions.append("LENGTH(content) >= %s")
            params.append(min_content_length)
        
        where_clause = " AND ".join(conditions)
        
        # Get FULL content
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
            ORDER BY created_at DESC
            LIMIT %s
        """
        params.append(limit)
        
        cur.execute(query, params)
        documents = cur.fetchall()
        
        # Process documents
        results = []
        for doc in documents:
            # Extract plain text from HTML/XML
            content = doc['content'] or ''
            plain_text = re.sub(r'<[^>]+>', ' ', content)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            
            results.append({
                'id': doc['id'],
                'case_number': doc['case_number'],
                'document_type': doc['document_type'],
                'content': {
                    'raw': content,  # FULL HTML/XML
                    'plain_text': plain_text,  # FULL plain text
                    'length': len(content),
                    'plain_text_length': len(plain_text)
                },
                'metadata': doc['metadata'] if isinstance(doc['metadata'], dict) else {},
                'created_at': str(doc['created_at']),
                'updated_at': str(doc['updated_at'])
            })
        
        cur.close()
        conn.close()
        
        return {
            'success': True,
            'total_results': len(results),
            'documents': results,
            'query_info': {
                'document_type': document_type,
                'judge_name': judge_name,
                'court_id': court_id,
                'min_content_length': min_content_length
            }
        }
        
    except Exception as e:
        logger.error(f"Database search failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'documents': []
        }

# Documentation endpoint
@app.get("/docs/flows")
async def get_data_flows():
    """
    Documentation endpoint explaining the two data flows
    """
    return {
        "opinion_flow": {
            "description": "Broad search for published court opinions",
            "data_source": "CourtListener opinion database",
            "search_capability": "Full-text search with keywords",
            "cost": "Free",
            "endpoints": ["/search/opinions"],
            "example_request": {
                "query": "intellectual property patent infringement",
                "court_ids": ["cafc", "ded"],
                "date_filed_after": "2024-01-01"
            }
        },
        "recap_flow": {
            "description": "Specific docket retrieval from PACER",
            "data_source": "RECAP Archive / PACER",
            "search_capability": "Exact docket number only",
            "cost": "Free if in RECAP, otherwise $0.10/page (max $3/doc)",
            "endpoints": ["/recap/docket", "/recap/webhook", "/recap/status/{id}"],
            "example_request": {
                "docket_number": "2:2024cv00181",
                "court": "txed",
                "include_documents": True
            }
        },
        "processing_flow": {
            "description": "Document processing pipeline",
            "endpoints": ["/process/batch", "/process/single"],
            "features": ["FLP enhancement", "Deduplication", "Unstructured.io parsing"]
        }
    }


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