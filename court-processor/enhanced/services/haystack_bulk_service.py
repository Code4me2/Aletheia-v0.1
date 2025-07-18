"""
Enhanced Haystack Bulk Ingestion Service

Optimized for high-volume court document processing with extensive metadata tagging.
Provides async bulk operations, connection pooling, and performance monitoring.
"""

import asyncio
import json
import time
import hashlib
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager
import logging

import asyncpg
import aioredis
from elasticsearch import AsyncElasticsearch
from elasticsearch.helpers import async_bulk, BulkIndexError
from sentence_transformers import SentenceTransformer
import psutil

from ..config.settings import get_settings
from ..utils.logging import get_logger


@dataclass
class BulkIngestionStats:
    """Statistics for bulk ingestion operations"""
    total_documents: int = 0
    successful_documents: int = 0
    failed_documents: int = 0
    duplicate_documents: int = 0
    processing_time: float = 0.0
    embedding_time: float = 0.0
    elasticsearch_time: float = 0.0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        return (self.successful_documents / self.total_documents * 100) if self.total_documents > 0 else 0.0
    
    @property
    def throughput(self) -> float:
        return (self.successful_documents / self.processing_time) if self.processing_time > 0 else 0.0


@dataclass
class DocumentBatch:
    """Container for a batch of documents to be processed"""
    documents: List[Dict[str, Any]]
    batch_id: str
    metadata: Dict[str, Any]
    
    def __len__(self) -> int:
        return len(self.documents)


class EnhancedHaystackBulkService:
    """
    Enhanced bulk ingestion service for Haystack/Elasticsearch
    
    Optimized for court documents with extensive metadata tagging
    """
    
    def __init__(self, 
                 elasticsearch_url: str = "http://elasticsearch:9200",
                 postgres_url: Optional[str] = None,
                 redis_url: str = "redis://redis:6379",
                 embedding_model: str = "BAAI/bge-small-en-v1.5",
                 index_name: str = "legal-documents-enhanced",
                 batch_size: int = 100,
                 max_workers: int = 4):
        
        self.settings = get_settings()
        self.logger = get_logger("haystack_bulk_service")
        
        # Configuration
        self.elasticsearch_url = elasticsearch_url
        self.postgres_url = postgres_url or self._get_postgres_url()
        self.redis_url = redis_url
        self.index_name = index_name
        self.batch_size = batch_size
        self.max_workers = max_workers
        
        # Connection pools (initialized in startup)
        self.es_client: Optional[AsyncElasticsearch] = None
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[aioredis.Redis] = None
        
        # Embedding model (loaded lazily)
        self.embedding_model_name = embedding_model
        self.embedding_model: Optional[SentenceTransformer] = None
        
        # Processing state
        self.is_initialized = False
        self.processing_stats = BulkIngestionStats()
        
        # Performance monitoring
        self._monitor_process = psutil.Process()
        
        self.logger.info(f"Enhanced Haystack Bulk Service initialized with batch_size={batch_size}")
    
    def _get_postgres_url(self) -> str:
        """Construct PostgreSQL URL from settings"""
        return (f"postgresql://{self.settings.database.user}:"
                f"{self.settings.database.password}@"
                f"{self.settings.database.host}:"
                f"{self.settings.database.port}/"
                f"{self.settings.database.name}")
    
    async def initialize(self):
        """Initialize all connection pools and resources"""
        if self.is_initialized:
            return
        
        try:
            self.logger.info("Initializing Enhanced Haystack Bulk Service...")
            
            # Initialize Elasticsearch with optimized settings
            self.es_client = AsyncElasticsearch(
                [self.elasticsearch_url],
                max_connections=20,
                max_connections_per_host=10,
                connection_timeout=30,
                max_retries=3,
                retry_on_timeout=True,
                retry_on_status=[429, 500, 502, 503, 504],
                http_compress=True
            )
            
            # Test Elasticsearch connection
            if await self.es_client.ping():
                self.logger.info("Elasticsearch connection established")
                await self._ensure_index_exists()
            else:
                raise ConnectionError("Failed to connect to Elasticsearch")
            
            # Initialize PostgreSQL connection pool
            if self.postgres_url:
                self.pg_pool = await asyncpg.create_pool(
                    self.postgres_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60,
                    server_settings={
                        'application_name': 'haystack_bulk_service',
                        'jit': 'off'  # Disable JIT for better pool performance
                    }
                )
                self.logger.info("PostgreSQL connection pool established")
            
            # Initialize Redis client
            self.redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20
            )
            await self.redis_client.ping()
            self.logger.info("Redis connection established")
            
            # Load embedding model in background
            asyncio.create_task(self._load_embedding_model())
            
            self.is_initialized = True
            self.logger.info("Enhanced Haystack Bulk Service initialization completed")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize bulk service: {e}")
            await self.cleanup()
            raise
    
    async def _load_embedding_model(self):
        """Load embedding model in background thread"""
        try:
            self.logger.info(f"Loading embedding model: {self.embedding_model_name}")
            loop = asyncio.get_event_loop()
            
            # Load model in thread pool to avoid blocking
            self.embedding_model = await loop.run_in_executor(
                None,
                lambda: SentenceTransformer(self.embedding_model_name)
            )
            
            self.logger.info("Embedding model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load embedding model: {e}")
            # Continue without embeddings rather than fail
    
    async def _ensure_index_exists(self):
        """Ensure Elasticsearch index exists with optimized settings"""
        if await self.es_client.indices.exists(index=self.index_name):
            self.logger.info(f"Index {self.index_name} already exists")
            return
        
        # Optimized index settings for bulk operations
        index_config = {
            "settings": {
                "number_of_shards": 3,  # Increased for better parallelism
                "number_of_replicas": 1,  # Add fault tolerance
                "refresh_interval": "30s",  # Reduce refresh frequency for bulk ops
                "index": {
                    "max_result_window": 50000,
                    "mapping": {
                        "total_fields": {"limit": 2000},  # Support extensive metadata
                        "depth": {"limit": 40}  # Support nested structures
                    },
                    "blocks": {"read_only_allow_delete": False}
                },
                "analysis": {
                    "analyzer": {
                        "legal_text": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "stop", "stemmer"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "legal_text",
                        "fields": {
                            "raw": {"type": "keyword", "ignore_above": 8192}
                        }
                    },
                    "summary": {
                        "type": "text",
                        "analyzer": "legal_text"
                    },
                    "embedding": {
                        "type": "dense_vector",
                        "dims": 384,
                        "index": True,
                        "similarity": "cosine"
                    },
                    "case_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "court_id": {"type": "keyword"},
                    "date_filed": {"type": "date"},
                    "judges": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                    "citations": {
                        "type": "nested",
                        "properties": {
                            "citation_string": {"type": "keyword"},
                            "type": {"type": "keyword"}
                        }
                    },
                    
                    # Extensive metadata support for tag population
                    "metadata": {
                        "type": "object",
                        "dynamic": True,  # Allow dynamic metadata fields
                        "properties": {
                            "tags": {
                                "type": "nested",
                                "properties": {
                                    "category": {"type": "keyword"},
                                    "value": {"type": "keyword"},
                                    "confidence": {"type": "float"},
                                    "source": {"type": "keyword"}
                                }
                            },
                            "legal_concepts": {"type": "keyword"},
                            "jurisdiction": {"type": "keyword"},
                            "practice_area": {"type": "keyword"},
                            "case_type": {"type": "keyword"},
                            "procedural_posture": {"type": "keyword"}
                        }
                    },
                    
                    "processing": {
                        "properties": {
                            "ingestion_timestamp": {"type": "date"},
                            "processing_version": {"type": "keyword"},
                            "source_system": {"type": "keyword"},
                            "content_hash": {"type": "keyword"}
                        }
                    }
                }
            }
        }
        
        await self.es_client.indices.create(index=self.index_name, body=index_config)
        self.logger.info(f"Created optimized index: {self.index_name}")
    
    async def bulk_ingest_from_postgres(self,
                                      query: str,
                                      query_params: Optional[List] = None,
                                      process_metadata: bool = True) -> BulkIngestionStats:
        """
        Bulk ingest documents from PostgreSQL query results
        
        Args:
            query: SQL query to fetch documents
            query_params: Parameters for the query
            process_metadata: Whether to process and enhance metadata tags
        """
        if not self.is_initialized:
            await self.initialize()
        
        stats = BulkIngestionStats()
        stats.start_time = datetime.now(timezone.utc)
        
        try:
            self.logger.info(f"Starting bulk ingestion from PostgreSQL")
            
            # Stream documents from PostgreSQL
            async for batch in self._stream_postgres_batches(query, query_params):
                batch_stats = await self._process_document_batch(batch, process_metadata)
                
                # Aggregate stats
                stats.total_documents += batch_stats.total_documents
                stats.successful_documents += batch_stats.successful_documents
                stats.failed_documents += batch_stats.failed_documents
                stats.duplicate_documents += batch_stats.duplicate_documents
                stats.embedding_time += batch_stats.embedding_time
                stats.elasticsearch_time += batch_stats.elasticsearch_time
                
                # Log progress
                self.logger.info(
                    f"Processed batch: {batch_stats.successful_documents}/{batch_stats.total_documents} "
                    f"successful, rate: {batch_stats.throughput:.2f} docs/sec"
                )
            
            stats.end_time = datetime.now(timezone.utc)
            stats.processing_time = (stats.end_time - stats.start_time).total_seconds()
            
            # Final refresh for immediate availability
            await self.es_client.indices.refresh(index=self.index_name)
            
            self.logger.info(
                f"Bulk ingestion completed: {stats.successful_documents}/{stats.total_documents} "
                f"documents, {stats.success_rate:.1f}% success rate, "
                f"{stats.throughput:.2f} docs/sec"
            )
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Bulk ingestion failed: {e}")
            stats.end_time = datetime.now(timezone.utc)
            if stats.start_time:
                stats.processing_time = (stats.end_time - stats.start_time).total_seconds()
            raise
    
    async def _stream_postgres_batches(self, 
                                     query: str, 
                                     query_params: Optional[List] = None) -> AsyncGenerator[DocumentBatch, None]:
        """Stream documents from PostgreSQL in batches"""
        if not self.pg_pool:
            raise RuntimeError("PostgreSQL pool not initialized")
        
        offset = 0
        batch_num = 0
        
        while True:
            # Add pagination to query
            paginated_query = f"{query} LIMIT {self.batch_size} OFFSET {offset}"
            
            async with self.pg_pool.acquire() as conn:
                rows = await conn.fetch(paginated_query, *(query_params or []))
                
                if not rows:
                    break
                
                # Convert rows to dictionaries
                documents = [dict(row) for row in rows]
                
                batch = DocumentBatch(
                    documents=documents,
                    batch_id=f"pg_batch_{batch_num:06d}",
                    metadata={
                        "source": "postgresql",
                        "offset": offset,
                        "query_hash": hashlib.md5(query.encode()).hexdigest()[:8]
                    }
                )
                
                yield batch
                
                offset += self.batch_size
                batch_num += 1
    
    async def _process_document_batch(self, 
                                    batch: DocumentBatch,
                                    process_metadata: bool = True) -> BulkIngestionStats:
        """Process a single batch of documents"""
        batch_stats = BulkIngestionStats()
        batch_stats.start_time = datetime.now(timezone.utc)
        batch_stats.total_documents = len(batch)
        
        try:
            # Step 1: Check for duplicates using Redis cache
            deduplicated_docs = await self._deduplicate_batch(batch.documents)
            batch_stats.duplicate_documents = len(batch.documents) - len(deduplicated_docs)
            
            if not deduplicated_docs:
                self.logger.info(f"Batch {batch.batch_id}: All documents are duplicates")
                batch_stats.end_time = datetime.now(timezone.utc)
                return batch_stats
            
            # Step 2: Process metadata if requested
            if process_metadata:
                processed_docs = await self._process_metadata_batch(deduplicated_docs)
            else:
                processed_docs = deduplicated_docs
            
            # Step 3: Generate embeddings
            embedding_start = time.time()
            docs_with_embeddings = await self._generate_embeddings_batch(processed_docs)
            batch_stats.embedding_time = time.time() - embedding_start
            
            # Step 4: Prepare Elasticsearch documents
            es_docs = []
            for doc in docs_with_embeddings:
                es_doc = self._prepare_elasticsearch_document(doc)
                es_docs.append({
                    "_index": self.index_name,
                    "_id": es_doc["document_id"],
                    "_source": es_doc
                })
            
            # Step 5: Bulk index to Elasticsearch
            es_start = time.time()
            success_count, failed_docs = await self._bulk_index_elasticsearch(es_docs)
            batch_stats.elasticsearch_time = time.time() - es_start
            
            batch_stats.successful_documents = success_count
            batch_stats.failed_documents = len(failed_docs)
            
            # Step 6: Cache successful document IDs to prevent duplicates
            if success_count > 0:
                await self._cache_processed_documents(
                    [doc for doc in docs_with_embeddings if doc.get("document_id")][:success_count]
                )
            
            batch_stats.end_time = datetime.now(timezone.utc)
            batch_stats.processing_time = (batch_stats.end_time - batch_stats.start_time).total_seconds()
            
            return batch_stats
            
        except Exception as e:
            self.logger.error(f"Failed to process batch {batch.batch_id}: {e}")
            batch_stats.end_time = datetime.now(timezone.utc)
            batch_stats.failed_documents = batch_stats.total_documents - batch_stats.successful_documents
            return batch_stats
    
    async def _deduplicate_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate documents using Redis cache"""
        if not self.redis_client:
            return documents
        
        unique_docs = []
        doc_hashes = []
        
        for doc in documents:
            # Generate content hash
            content = doc.get('content') or doc.get('plain_text', '')
            doc_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
            doc_hashes.append(doc_hash)
        
        # Check Redis for existing hashes
        pipeline = self.redis_client.pipeline()
        for doc_hash in doc_hashes:
            pipeline.exists(f"doc:{doc_hash}")
        exists_results = await pipeline.execute()
        
        # Filter out duplicates
        for i, (doc, exists) in enumerate(zip(documents, exists_results)):
            if not exists:
                doc['_content_hash'] = doc_hashes[i]
                unique_docs.append(doc)
        
        self.logger.info(f"Deduplicated: {len(unique_docs)}/{len(documents)} documents are unique")
        return unique_docs
    
    async def _process_metadata_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and enhance metadata for documents"""
        processed_docs = []
        
        for doc in documents:
            try:
                # Extract and structure metadata
                enhanced_metadata = self._extract_enhanced_metadata(doc)
                
                # Create processed document
                processed_doc = doc.copy()
                processed_doc['metadata'] = enhanced_metadata
                processed_doc['processing'] = {
                    'ingestion_timestamp': datetime.now(timezone.utc).isoformat(),
                    'processing_version': '2.0',
                    'source_system': 'enhanced_court_processor',
                    'content_hash': doc.get('_content_hash')
                }
                
                processed_docs.append(processed_doc)
                
            except Exception as e:
                self.logger.warning(f"Failed to process metadata for document: {e}")
                processed_docs.append(doc)  # Include original document
        
        return processed_docs
    
    def _extract_enhanced_metadata(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and structure metadata with extensive tag support"""
        metadata = {
            'tags': [],
            'legal_concepts': [],
            'jurisdiction': None,
            'practice_area': None,
            'case_type': None,
            'procedural_posture': None
        }
        
        # Extract court information
        if doc.get('court_id'):
            metadata['jurisdiction'] = doc['court_id']
        
        # Extract judge information as tags
        judges = doc.get('judges') or doc.get('assigned_to_str', '')
        if judges:
            metadata['tags'].append({
                'category': 'judge',
                'value': judges,
                'confidence': 1.0,
                'source': 'courtlistener'
            })
        
        # Extract case type from nature of suit
        nature_of_suit = doc.get('nature_of_suit', '')
        if nature_of_suit:
            metadata['case_type'] = nature_of_suit
            metadata['tags'].append({
                'category': 'nature_of_suit',
                'value': nature_of_suit,
                'confidence': 0.9,
                'source': 'courtlistener'
            })
        
        # Extract procedural posture
        procedural_history = doc.get('procedural_history', '')
        if procedural_history:
            metadata['procedural_posture'] = procedural_history[:100]  # Truncate
            metadata['tags'].append({
                'category': 'procedural_history',
                'value': procedural_history,
                'confidence': 0.8,
                'source': 'courtlistener'
            })
        
        # Extract citations as legal concepts
        citations = doc.get('citations', [])
        for citation in citations:
            if isinstance(citation, dict):
                citation_str = citation.get('citation_string', '')
            else:
                citation_str = str(citation)
            
            if citation_str:
                metadata['legal_concepts'].append(citation_str)
                metadata['tags'].append({
                    'category': 'citation',
                    'value': citation_str,
                    'confidence': 1.0,
                    'source': 'extracted'
                })
        
        # Add all original fields as tags for searchability
        for field, value in doc.items():
            if field.startswith('_') or value is None:
                continue
            
            if isinstance(value, (str, int, float)) and value != '':
                metadata['tags'].append({
                    'category': f'field_{field}',
                    'value': str(value),
                    'confidence': 0.7,
                    'source': 'raw_data'
                })
        
        return metadata
    
    async def _generate_embeddings_batch(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for document batch"""
        if not self.embedding_model:
            self.logger.warning("Embedding model not available, skipping embeddings")
            return documents
        
        try:
            # Prepare texts for embedding
            texts = []
            for doc in documents:
                # Combine multiple text fields for richer embeddings
                text_parts = []
                
                # Primary content
                content = doc.get('content') or doc.get('plain_text', '')
                if content:
                    text_parts.append(content[:2000])  # Limit length
                
                # Case name for context
                case_name = doc.get('case_name', '')
                if case_name:
                    text_parts.append(case_name)
                
                # Summary if available
                summary = doc.get('summary', '')
                if summary:
                    text_parts.append(summary)
                
                combined_text = ' '.join(text_parts)
                texts.append(combined_text if combined_text.strip() else 'No content available')
            
            # Generate embeddings in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.embedding_model.encode,
                texts
            )
            
            # Add embeddings to documents
            docs_with_embeddings = []
            for doc, embedding in zip(documents, embeddings):
                doc_copy = doc.copy()
                doc_copy['embedding'] = embedding.tolist()
                docs_with_embeddings.append(doc_copy)
            
            return docs_with_embeddings
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {e}")
            return documents  # Return without embeddings
    
    def _prepare_elasticsearch_document(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare document for Elasticsearch indexing"""
        # Generate document ID if not present
        doc_id = doc.get('id') or doc.get('document_id') or doc.get('_content_hash')
        if not doc_id:
            # Generate ID from content
            content = doc.get('content') or doc.get('plain_text', '')
            doc_id = hashlib.md5(content.encode('utf-8')).hexdigest()
        
        # Prepare Elasticsearch document
        es_doc = {
            'document_id': str(doc_id),
            'content': doc.get('content') or doc.get('plain_text', ''),
            'summary': doc.get('summary', ''),
            'case_name': doc.get('case_name', ''),
            'court_id': doc.get('court_id'),
            'date_filed': doc.get('date_filed'),
            'judges': doc.get('judges') or doc.get('assigned_to_str', ''),
            'citations': doc.get('citations', []),
            'metadata': doc.get('metadata', {}),
            'processing': doc.get('processing', {})
        }
        
        # Add embedding if available
        if 'embedding' in doc:
            es_doc['embedding'] = doc['embedding']
        
        # Remove None values to save space
        es_doc = {k: v for k, v in es_doc.items() if v is not None}
        
        return es_doc
    
    async def _bulk_index_elasticsearch(self, documents: List[Dict[str, Any]]) -> Tuple[int, List[Dict]]:
        """Bulk index documents to Elasticsearch"""
        if not documents:
            return 0, []
        
        try:
            # Use async bulk helper with optimized settings
            success_count, failed_docs = await async_bulk(
                self.es_client,
                documents,
                max_chunk_bytes=10 * 1024 * 1024,  # 10MB chunks
                chunk_size=self.batch_size,
                max_retries=3,
                initial_backoff=2,
                max_backoff=600,
                yield_ok=False,  # Only yield failed docs
                raise_on_error=False,
                refresh=False  # Don't refresh immediately
            )
            
            return success_count, list(failed_docs)
            
        except BulkIndexError as e:
            self.logger.error(f"Bulk indexing partially failed: {len(e.errors)} errors")
            # Extract successful count from errors
            success_count = len(documents) - len(e.errors)
            return success_count, e.errors
        
        except Exception as e:
            self.logger.error(f"Bulk indexing failed completely: {e}")
            return 0, [{"error": str(e), "documents": len(documents)}]
    
    async def _cache_processed_documents(self, documents: List[Dict[str, Any]]):
        """Cache processed document hashes to prevent duplicates"""
        if not self.redis_client:
            return
        
        pipeline = self.redis_client.pipeline()
        
        for doc in documents:
            content_hash = doc.get('_content_hash')
            if content_hash:
                # Cache for 30 days
                pipeline.setex(f"doc:{content_hash}", 2592000, "processed")
        
        await pipeline.execute()
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        if not self.is_initialized:
            return {"status": "not_initialized"}
        
        # System metrics
        memory_info = self._monitor_process.memory_info()
        cpu_percent = self._monitor_process.cpu_percent()
        
        # Connection pool metrics
        es_info = {"connected": await self.es_client.ping() if self.es_client else False}
        
        pg_info = {}
        if self.pg_pool:
            pg_info = {
                "size": self.pg_pool.get_size(),
                "min_size": self.pg_pool.get_min_size(),
                "max_size": self.pg_pool.get_max_size(),
                "idle_connections": self.pg_pool.get_idle_size()
            }
        
        redis_info = {}
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
                redis_info["connected"] = True
            except:
                redis_info["connected"] = False
        
        return {
            "system": {
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "cpu_percent": cpu_percent
            },
            "connections": {
                "elasticsearch": es_info,
                "postgresql": pg_info,
                "redis": redis_info
            },
            "processing": {
                "embedding_model_loaded": self.embedding_model is not None,
                "batch_size": self.batch_size,
                "max_workers": self.max_workers
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check"""
        health = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {}
        }
        
        try:
            # Check Elasticsearch
            if self.es_client:
                es_health = await self.es_client.cluster.health()
                health["services"]["elasticsearch"] = {
                    "status": es_health.get("status", "unknown"),
                    "connected": True
                }
            else:
                health["services"]["elasticsearch"] = {"connected": False}
            
            # Check PostgreSQL
            if self.pg_pool:
                async with self.pg_pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                health["services"]["postgresql"] = {"connected": True}
            else:
                health["services"]["postgresql"] = {"connected": False}
            
            # Check Redis
            if self.redis_client:
                await self.redis_client.ping()
                health["services"]["redis"] = {"connected": True}
            else:
                health["services"]["redis"] = {"connected": False}
            
            # Overall status
            failed_services = [
                service for service, info in health["services"].items()
                if not info.get("connected", False)
            ]
            
            if failed_services:
                health["status"] = "degraded"
                health["failed_services"] = failed_services
            
        except Exception as e:
            health["status"] = "unhealthy"
            health["error"] = str(e)
        
        return health
    
    async def cleanup(self):
        """Clean up all resources"""
        self.logger.info("Cleaning up Enhanced Haystack Bulk Service...")
        
        if self.es_client:
            await self.es_client.close()
        
        if self.pg_pool:
            await self.pg_pool.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.is_initialized = False
        self.logger.info("Cleanup completed")
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.cleanup()


# Example usage and integration points
async def main_example():
    """Example usage of the Enhanced Haystack Bulk Service"""
    
    # Initialize service
    bulk_service = EnhancedHaystackBulkService(
        batch_size=200,  # Larger batches for better performance
        max_workers=6
    )
    
    try:
        await bulk_service.initialize()
        
        # Example: Bulk ingest all court documents from PostgreSQL
        query = """
        SELECT 
            id,
            case_name,
            court_id,
            date_filed,
            plain_text as content,
            summary,
            judges,
            assigned_to_str,
            citations,
            nature_of_suit,
            procedural_history,
            metadata_tags
        FROM court_documents 
        WHERE ingested_to_haystack = FALSE
        ORDER BY date_filed DESC
        """
        
        stats = await bulk_service.bulk_ingest_from_postgres(
            query=query,
            process_metadata=True
        )
        
        print(f"Ingestion completed:")
        print(f"  - Total documents: {stats.total_documents}")
        print(f"  - Successful: {stats.successful_documents}")
        print(f"  - Failed: {stats.failed_documents}")
        print(f"  - Duplicates: {stats.duplicate_documents}")
        print(f"  - Success rate: {stats.success_rate:.1f}%")
        print(f"  - Throughput: {stats.throughput:.2f} docs/sec")
        
    finally:
        await bulk_service.cleanup()


if __name__ == "__main__":
    asyncio.run(main_example())