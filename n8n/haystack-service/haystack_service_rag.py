"""
Haystack RAG Service - Simplified for Pure RAG Functionality
===========================================================

This is a streamlined version focusing only on RAG (Retrieval-Augmented Generation)
capabilities, removing all recursive summarization and hierarchy features.

Supports both unified mode (with PostgreSQL/n8n) and standalone mode.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
import json
from contextlib import asynccontextmanager
from enum import Enum

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service Mode
class ServiceMode(str, Enum):
    UNIFIED = "unified"
    STANDALONE = "standalone"

# Configuration
SERVICE_MODE = ServiceMode(os.getenv("HAYSTACK_MODE", "unified"))
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "rag-documents")
EMBEDDING_MODEL = os.getenv("HAYSTACK_MODEL", "BAAI/bge-small-en-v1.5")
ENABLE_POSTGRESQL = os.getenv("ENABLE_POSTGRESQL", "true").lower() == "true"

# PostgreSQL config for unified mode
if SERVICE_MODE == ServiceMode.UNIFIED and ENABLE_POSTGRESQL:
    import asyncpg
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
    POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "n8n")

# Global instances
es_client: Optional[Elasticsearch] = None
embedding_model: Optional[SentenceTransformer] = None
pg_pool: Optional[asyncpg.Pool] = None

# ===========================
# Pydantic Models (Simplified)
# ===========================

class DocumentInput(BaseModel):
    """Simplified document model for RAG"""
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    document_id: Optional[str] = None
    
class SearchRequest(BaseModel):
    """RAG-optimized search request"""
    query: str
    top_k: int = Field(default=10, ge=1, le=100)
    search_type: str = "hybrid"  # "hybrid", "vector", "bm25"
    filters: Optional[Dict[str, Any]] = None
    
class ImportRequest(BaseModel):
    """PostgreSQL import for unified mode"""
    workflow_id: str
    table_name: str = "documents"
    content_column: str = "content"
    metadata_columns: Optional[List[str]] = None

class IngestResponse(BaseModel):
    """Response for document ingestion"""
    documents_processed: int
    document_ids: List[str]
    mode: str

class SearchResponse(BaseModel):
    """Response for search operations"""
    results: List[Dict[str, Any]]
    total_results: int
    search_type: str
    query: str

# ===========================
# Lifespan Management
# ===========================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage service lifecycle"""
    global es_client, embedding_model, pg_pool
    
    # Startup
    logger.info(f"Starting Haystack RAG Service in {SERVICE_MODE} mode")
    
    try:
        # Initialize Elasticsearch
        es_client = Elasticsearch(ELASTICSEARCH_HOST)
        if not es_client.ping():
            raise Exception("Elasticsearch connection failed")
        
        # Ensure index exists with proper mapping
        if not es_client.indices.exists(index=ELASTICSEARCH_INDEX):
            es_client.indices.create(
                index=ELASTICSEARCH_INDEX,
                body={
                    "mappings": {
                        "properties": {
                            "content": {
                                "type": "text",
                                "analyzer": "standard"
                            },
                            "embedding": {
                                "type": "dense_vector",
                                "dims": 384,
                                "index": True,
                                "similarity": "cosine"
                            },
                            "metadata": {
                                "type": "object",
                                "dynamic": True
                            },
                            "document_id": {
                                "type": "keyword"
                            },
                            "ingestion_timestamp": {
                                "type": "date"
                            }
                        }
                    }
                }
            )
        
        # Initialize embedding model
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        
        # Initialize PostgreSQL for unified mode
        if SERVICE_MODE == ServiceMode.UNIFIED and ENABLE_POSTGRESQL:
            logger.info("Connecting to PostgreSQL for unified mode")
            pg_pool = await asyncpg.create_pool(
                host=POSTGRES_HOST,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                min_size=1,
                max_size=10
            )
        
        logger.info("Service initialization complete")
        
    except Exception as e:
        logger.error(f"Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Haystack RAG Service")
    if pg_pool:
        await pg_pool.close()

# ===========================
# FastAPI App
# ===========================

app = FastAPI(
    title="Haystack RAG Service",
    description="Pure RAG service with unified/standalone modes",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===========================
# Core RAG Functions
# ===========================

async def generate_embedding(text: str) -> List[float]:
    """Generate embedding for text"""
    if not embedding_model:
        raise HTTPException(503, "Embedding model not initialized")
    return embedding_model.encode(text).tolist()

async def index_document(doc_id: str, content: str, metadata: Dict[str, Any], embedding: List[float]):
    """Index document in Elasticsearch"""
    es_doc = {
        "document_id": doc_id,
        "content": content,
        "embedding": embedding,
        "metadata": metadata,
        "ingestion_timestamp": datetime.utcnow().isoformat()
    }
    
    es_client.index(
        index=ELASTICSEARCH_INDEX,
        id=doc_id,
        body=es_doc,
        refresh=True
    )

# ===========================
# API Endpoints
# ===========================

@app.get("/health")
async def health_check():
    """Service health check with mode information"""
    try:
        es_health = es_client.cluster.health() if es_client else {"status": "red"}
        
        features = {
            "mode": SERVICE_MODE,
            "postgresql_import": SERVICE_MODE == ServiceMode.UNIFIED and pg_pool is not None,
            "direct_ingestion": True,
            "hybrid_search": True,
            "vector_search": True,
            "bm25_search": True
        }
        
        return {
            "status": "healthy" if es_health["status"] in ["yellow", "green"] else "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "elasticsearch": es_health["status"],
            "embedding_model": EMBEDDING_MODEL,
            "index": ELASTICSEARCH_INDEX,
            "features": features
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(503, "Service unavailable")

@app.post("/ingest", response_model=IngestResponse)
async def ingest_documents(documents: List[DocumentInput]):
    """Ingest documents with embeddings for RAG"""
    if not es_client or not embedding_model:
        raise HTTPException(503, "Service not initialized")
    
    try:
        document_ids = []
        
        for doc in documents:
            # Generate document ID
            doc_id = doc.document_id or str(uuid.uuid4())
            
            # Generate embedding
            embedding = await generate_embedding(doc.content)
            
            # Index document
            await index_document(doc_id, doc.content, doc.metadata, embedding)
            document_ids.append(doc_id)
        
        return IngestResponse(
            documents_processed=len(documents),
            document_ids=document_ids,
            mode=SERVICE_MODE
        )
        
    except Exception as e:
        logger.error(f"Ingestion failed: {str(e)}")
        raise HTTPException(500, f"Ingestion failed: {str(e)}")

@app.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """RAG-optimized search endpoint"""
    if not es_client:
        raise HTTPException(503, "Elasticsearch not initialized")
    
    try:
        # Build query based on search type
        if request.search_type == "bm25":
            query = {
                "match": {
                    "content": request.query
                }
            }
        elif request.search_type == "vector":
            if not embedding_model:
                raise HTTPException(503, "Embedding model not initialized")
            
            query_embedding = await generate_embedding(request.query)
            query = {
                "script_score": {
                    "query": {"match_all": {}},
                    "script": {
                        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                        "params": {"query_vector": query_embedding}
                    }
                }
            }
        else:  # hybrid
            if not embedding_model:
                raise HTTPException(503, "Embedding model not initialized")
                
            query_embedding = await generate_embedding(request.query)
            query = {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "content": {
                                    "query": request.query,
                                    "boost": 0.5
                                }
                            }
                        },
                        {
                            "script_score": {
                                "query": {"match_all": {}},
                                "script": {
                                    "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
                                    "params": {"query_vector": query_embedding}
                                },
                                "boost": 0.5
                            }
                        }
                    ]
                }
            }
        
        # Add filters if provided
        if request.filters:
            filter_conditions = []
            for field, value in request.filters.items():
                filter_conditions.append({"term": {field: value}})
            
            query = {
                "bool": {
                    "must": [query],
                    "filter": filter_conditions
                }
            }
        
        # Execute search
        search_body = {
            "query": query,
            "size": request.top_k,
            "_source": True
        }
        
        search_result = es_client.search(index=ELASTICSEARCH_INDEX, body=search_body)
        
        # Process results
        results = []
        for hit in search_result['hits']['hits']:
            results.append({
                "content": hit['_source']['content'],
                "score": hit['_score'],
                "metadata": hit['_source'].get('metadata', {}),
                "document_id": hit['_source'].get('document_id', hit['_id'])
            })
        
        return SearchResponse(
            results=results,
            total_results=len(results),
            search_type=request.search_type,
            query=request.query
        )
        
    except Exception as e:
        logger.error(f"Search failed: {str(e)}")
        raise HTTPException(500, f"Search failed: {str(e)}")

@app.get("/get_document_with_context/{document_id}")
async def get_document_with_context(document_id: str):
    """Get document with metadata for RAG context"""
    if not es_client:
        raise HTTPException(503, "Elasticsearch not initialized")
    
    try:
        result = es_client.get(index=ELASTICSEARCH_INDEX, id=document_id)
        
        return {
            "document_id": document_id,
            "content": result['_source']['content'],
            "metadata": result['_source'].get('metadata', {}),
            "ingestion_timestamp": result['_source'].get('ingestion_timestamp'),
            "mode": SERVICE_MODE
        }
        
    except Exception as e:
        if "NotFoundError" in str(type(e)):
            raise HTTPException(404, "Document not found")
        logger.error(f"Document retrieval failed: {str(e)}")
        raise HTTPException(500, f"Failed to retrieve document: {str(e)}")

# Conditional endpoint for unified mode
if SERVICE_MODE == ServiceMode.UNIFIED:
    @app.post("/import_from_node")
    async def import_from_postgresql(request: ImportRequest):
        """Import documents from PostgreSQL (unified mode only)"""
        if not pg_pool:
            raise HTTPException(503, "PostgreSQL not configured")
        
        try:
            async with pg_pool.acquire() as conn:
                # Build query to fetch documents
                columns = [request.content_column]
                if request.metadata_columns:
                    columns.extend(request.metadata_columns)
                
                query = f"""
                    SELECT {', '.join(columns)}
                    FROM {request.table_name}
                    WHERE workflow_id = $1
                """
                
                rows = await conn.fetch(query, request.workflow_id)
                
                # Convert to documents
                documents = []
                for row in rows:
                    metadata = {}
                    if request.metadata_columns:
                        for col in request.metadata_columns:
                            if col in row:
                                metadata[col] = row[col]
                    
                    documents.append(DocumentInput(
                        content=row[request.content_column],
                        metadata=metadata
                    ))
                
                # Ingest documents
                return await ingest_documents(documents)
                
        except Exception as e:
            logger.error(f"PostgreSQL import failed: {str(e)}")
            raise HTTPException(500, f"Import failed: {str(e)}")
else:
    @app.post("/import_from_node", status_code=404)
    async def import_not_available():
        """PostgreSQL import not available in standalone mode"""
        raise HTTPException(
            404, 
            "PostgreSQL import is not available in standalone mode. "
            "Use /ingest endpoint for direct document ingestion."
        )

# ===========================
# Removed Endpoints (Return 404)
# ===========================

removed_endpoints = [
    ("/hierarchy", "POST"),
    ("/get_by_stage", "GET"),
    ("/update_status", "POST"),
    ("/batch_hierarchy", "POST"),
    ("/get_final_summary/{workflow_id}", "GET"),
    ("/get_complete_tree/{workflow_id}", "GET")
]

for endpoint, method in removed_endpoints:
    @app.api_route(endpoint, methods=[method], status_code=404)
    async def removed_endpoint():
        raise HTTPException(
            404,
            "This endpoint has been removed in the RAG-only version. "
            "Please use the simplified RAG endpoints instead."
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)