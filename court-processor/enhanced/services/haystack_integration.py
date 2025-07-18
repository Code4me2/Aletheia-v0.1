"""
Enhanced Haystack Integration Module

Provides integration points between the Enhanced Unified Document Processor
and the Haystack Bulk Service for optimized court document processing.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timezone
from dataclasses import dataclass

from .haystack_bulk_service import EnhancedHaystackBulkService, BulkIngestionStats
from ..config.settings import get_settings
from ..utils.logging import get_logger


@dataclass
class ProcessingJob:
    """Represents a processing job for document ingestion"""
    job_id: str
    job_type: str
    parameters: Dict[str, Any]
    created_at: datetime
    status: str = "pending"
    progress: float = 0.0
    stats: Optional[BulkIngestionStats] = None
    error: Optional[str] = None


class HaystackIntegrationManager:
    """
    Integration manager for connecting Enhanced Document Processor with Haystack
    
    Provides high-level methods for different ingestion scenarios
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.logger = get_logger("haystack_integration")
        
        # Initialize bulk service with optimized settings
        self.bulk_service = EnhancedHaystackBulkService(
            elasticsearch_url=self.settings.elasticsearch.url,
            redis_url=self.settings.redis.url,
            batch_size=150,  # Optimized batch size
            max_workers=6
        )
        
        # Job tracking
        self.active_jobs: Dict[str, ProcessingJob] = {}
        
        self.logger.info("Haystack Integration Manager initialized")
    
    async def initialize(self):
        """Initialize the integration manager"""
        await self.bulk_service.initialize()
        self.logger.info("Haystack Integration Manager ready")
    
    async def cleanup(self):
        """Clean up resources"""
        await self.bulk_service.cleanup()
    
    # High-level integration methods
    
    async def ingest_all_court_documents(self, 
                                       court_filter: Optional[str] = None,
                                       date_filter: Optional[str] = None,
                                       judge_filter: Optional[str] = None) -> str:
        """
        Ingest all court documents from PostgreSQL to Haystack
        
        Returns job_id for tracking progress
        """
        job_id = f"ingest_all_{int(time.time())}"
        
        # Build query based on filters
        query_parts = ["SELECT * FROM enhanced_court_documents WHERE 1=1"]
        params = []
        
        if court_filter:
            query_parts.append("AND court_id = $" + str(len(params) + 1))
            params.append(court_filter)
        
        if date_filter:
            query_parts.append("AND date_filed >= $" + str(len(params) + 1))
            params.append(date_filter)
        
        if judge_filter:
            query_parts.append("AND (judges ILIKE $" + str(len(params) + 1) + 
                             " OR assigned_to_str ILIKE $" + str(len(params) + 1) + ")")
            params.extend([f"%{judge_filter}%", f"%{judge_filter}%"])
        
        query_parts.append("ORDER BY date_filed DESC")
        query = " ".join(query_parts)
        
        job = ProcessingJob(
            job_id=job_id,
            job_type="bulk_ingest",
            parameters={
                "query": query,
                "params": params,
                "court_filter": court_filter,
                "date_filter": date_filter,
                "judge_filter": judge_filter
            },
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._execute_bulk_ingestion_job(job))
        
        return job_id
    
    async def ingest_new_documents_only(self) -> str:
        """
        Ingest only documents that haven't been processed to Haystack yet
        
        Returns job_id for tracking progress
        """
        job_id = f"ingest_new_{int(time.time())}"
        
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
            metadata_json,
            processing_timestamp,
            flp_enhanced,
            cl_document_id
        FROM enhanced_court_documents 
        WHERE haystack_ingested = FALSE 
           OR haystack_ingested IS NULL
        ORDER BY processing_timestamp DESC
        """
        
        job = ProcessingJob(
            job_id=job_id,
            job_type="ingest_new",
            parameters={"query": query, "params": []},
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._execute_bulk_ingestion_job(job))
        
        return job_id
    
    async def ingest_judge_documents(self, 
                                   judge_name: str,
                                   court_id: Optional[str] = None,
                                   max_documents: int = 1000) -> str:
        """
        Ingest all documents for a specific judge
        
        Returns job_id for tracking progress
        """
        job_id = f"ingest_judge_{judge_name.lower().replace(' ', '_')}_{int(time.time())}"
        
        query_parts = [
            "SELECT * FROM enhanced_court_documents",
            "WHERE (judges ILIKE $1 OR assigned_to_str ILIKE $1)"
        ]
        params = [f"%{judge_name}%"]
        
        if court_id:
            query_parts.append("AND court_id = $2")
            params.append(court_id)
        
        query_parts.extend([
            "ORDER BY date_filed DESC",
            f"LIMIT {max_documents}"
        ])
        
        query = " ".join(query_parts)
        
        job = ProcessingJob(
            job_id=job_id,
            job_type="ingest_judge",
            parameters={
                "query": query,
                "params": params,
                "judge_name": judge_name,
                "court_id": court_id,
                "max_documents": max_documents
            },
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._execute_bulk_ingestion_job(job))
        
        return job_id
    
    async def ingest_recent_documents(self, days: int = 30) -> str:
        """
        Ingest documents from the last N days
        
        Returns job_id for tracking progress
        """
        job_id = f"ingest_recent_{days}d_{int(time.time())}"
        
        query = """
        SELECT * FROM enhanced_court_documents 
        WHERE date_filed >= CURRENT_DATE - INTERVAL '%s days'
        ORDER BY date_filed DESC
        """ % days
        
        job = ProcessingJob(
            job_id=job_id,
            job_type="ingest_recent",
            parameters={
                "query": query,
                "params": [],
                "days": days
            },
            created_at=datetime.now(timezone.utc)
        )
        
        self.active_jobs[job_id] = job
        
        # Start processing in background
        asyncio.create_task(self._execute_bulk_ingestion_job(job))
        
        return job_id
    
    async def _execute_bulk_ingestion_job(self, job: ProcessingJob):
        """Execute a bulk ingestion job"""
        try:
            job.status = "running"
            self.logger.info(f"Starting ingestion job {job.job_id} ({job.job_type})")
            
            # Execute the bulk ingestion
            stats = await self.bulk_service.bulk_ingest_from_postgres(
                query=job.parameters["query"],
                query_params=job.parameters.get("params"),
                process_metadata=True
            )
            
            # Update job with results
            job.status = "completed"
            job.progress = 100.0
            job.stats = stats
            
            self.logger.info(
                f"Ingestion job {job.job_id} completed: "
                f"{stats.successful_documents}/{stats.total_documents} successful "
                f"({stats.success_rate:.1f}% success rate)"
            )
            
            # Update database to mark documents as ingested
            if stats.successful_documents > 0:
                await self._mark_documents_as_ingested(job)
            
        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            self.logger.error(f"Ingestion job {job.job_id} failed: {e}")
    
    async def _mark_documents_as_ingested(self, job: ProcessingJob):
        """Mark successfully ingested documents in PostgreSQL"""
        try:
            if not self.bulk_service.pg_pool:
                return
            
            # Update the haystack_ingested flag
            update_query = """
            UPDATE enhanced_court_documents 
            SET haystack_ingested = TRUE,
                haystack_ingestion_timestamp = CURRENT_TIMESTAMP
            WHERE id IN (
                SELECT id FROM enhanced_court_documents 
                WHERE haystack_ingested IS NULL OR haystack_ingested = FALSE
                LIMIT $1
            )
            """
            
            async with self.bulk_service.pg_pool.acquire() as conn:
                result = await conn.execute(
                    update_query, 
                    job.stats.successful_documents if job.stats else 0
                )
                
                self.logger.info(f"Marked {result} documents as ingested in PostgreSQL")
                
        except Exception as e:
            self.logger.error(f"Failed to update ingestion status in PostgreSQL: {e}")
    
    # Job management methods
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a processing job"""
        job = self.active_jobs.get(job_id)
        if not job:
            return None
        
        status = {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at.isoformat(),
            "parameters": job.parameters
        }
        
        if job.stats:
            status["stats"] = {
                "total_documents": job.stats.total_documents,
                "successful_documents": job.stats.successful_documents,
                "failed_documents": job.stats.failed_documents,
                "duplicate_documents": job.stats.duplicate_documents,
                "success_rate": job.stats.success_rate,
                "throughput": job.stats.throughput,
                "processing_time": job.stats.processing_time
            }
        
        if job.error:
            status["error"] = job.error
        
        return status
    
    def get_all_jobs(self) -> List[Dict[str, Any]]:
        """Get status of all jobs"""
        return [self.get_job_status(job_id) for job_id in self.active_jobs.keys()]
    
    def get_active_jobs(self) -> List[Dict[str, Any]]:
        """Get status of currently running jobs"""
        return [
            self.get_job_status(job_id) 
            for job_id, job in self.active_jobs.items() 
            if job.status == "running"
        ]
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job"""
        job = self.active_jobs.get(job_id)
        if not job or job.status != "running":
            return False
        
        # Note: This is a simplified cancellation
        # In production, you'd want more sophisticated task cancellation
        job.status = "cancelled"
        self.logger.info(f"Job {job_id} marked as cancelled")
        return True
    
    def cleanup_completed_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        cutoff_time = datetime.now(timezone.utc).timestamp() - (max_age_hours * 3600)
        
        jobs_to_remove = []
        for job_id, job in self.active_jobs.items():
            if (job.status in ["completed", "failed", "cancelled"] and 
                job.created_at.timestamp() < cutoff_time):
                jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
        
        if jobs_to_remove:
            self.logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    # Health and monitoring methods
    
    async def get_integration_health(self) -> Dict[str, Any]:
        """Get health status of the integration"""
        bulk_health = await self.bulk_service.health_check()
        
        integration_health = {
            "integration_manager": {
                "status": "healthy",
                "active_jobs": len([j for j in self.active_jobs.values() if j.status == "running"]),
                "total_jobs": len(self.active_jobs)
            },
            "bulk_service": bulk_health
        }
        
        # Overall status
        if bulk_health.get("status") != "healthy":
            integration_health["integration_manager"]["status"] = "degraded"
        
        return integration_health
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        bulk_metrics = await self.bulk_service.get_performance_metrics()
        
        # Add integration-specific metrics
        job_stats = {
            "total_jobs": len(self.active_jobs),
            "running_jobs": len([j for j in self.active_jobs.values() if j.status == "running"]),
            "completed_jobs": len([j for j in self.active_jobs.values() if j.status == "completed"]),
            "failed_jobs": len([j for j in self.active_jobs.values() if j.status == "failed"])
        }
        
        return {
            "bulk_service": bulk_metrics,
            "job_management": job_stats
        }


# Utility functions for common operations

async def quick_ingest_new_documents() -> str:
    """Quick utility to ingest new documents"""
    manager = HaystackIntegrationManager()
    try:
        await manager.initialize()
        job_id = await manager.ingest_new_documents_only()
        return job_id
    finally:
        await manager.cleanup()


async def quick_ingest_judge_documents(judge_name: str, court_id: Optional[str] = None) -> str:
    """Quick utility to ingest documents for a specific judge"""
    manager = HaystackIntegrationManager()
    try:
        await manager.initialize()
        job_id = await manager.ingest_judge_documents(judge_name, court_id)
        return job_id
    finally:
        await manager.cleanup()


# Integration with Enhanced Unified Document Processor

class EnhancedProcessorHaystackBridge:
    """
    Bridge between Enhanced Unified Document Processor and Haystack
    
    Provides seamless integration for real-time document processing
    """
    
    def __init__(self, processor):
        self.processor = processor
        self.haystack_manager = HaystackIntegrationManager()
        self.logger = get_logger("processor_haystack_bridge")
    
    async def initialize(self):
        """Initialize the bridge"""
        await self.haystack_manager.initialize()
        self.logger.info("Processor-Haystack bridge initialized")
    
    async def process_and_ingest_batch(self, 
                                     court_id: Optional[str] = None,
                                     judge_name: Optional[str] = None,
                                     max_documents: int = 100) -> Dict[str, Any]:
        """
        Process documents through Enhanced Processor and ingest to Haystack
        
        This combines the document processing pipeline with bulk ingestion
        """
        try:
            # Step 1: Process documents through Enhanced Processor
            processor_stats = await self.processor.process_courtlistener_batch(
                court_id=court_id,
                judge_name=judge_name,
                max_documents=max_documents
            )
            
            # Step 2: Ingest processed documents to Haystack
            if processor_stats.get('new_documents', 0) > 0:
                if judge_name:
                    job_id = await self.haystack_manager.ingest_judge_documents(
                        judge_name=judge_name,
                        court_id=court_id,
                        max_documents=processor_stats['new_documents']
                    )
                else:
                    job_id = await self.haystack_manager.ingest_new_documents_only()
                
                return {
                    "processing_stats": processor_stats,
                    "haystack_job_id": job_id,
                    "status": "success"
                }
            else:
                return {
                    "processing_stats": processor_stats,
                    "haystack_job_id": None,
                    "status": "no_new_documents"
                }
                
        except Exception as e:
            self.logger.error(f"Combined processing and ingestion failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up bridge resources"""
        await self.haystack_manager.cleanup()


# Example usage
async def example_integration():
    """Example of how to use the Haystack integration"""
    
    # Initialize integration manager
    manager = HaystackIntegrationManager()
    await manager.initialize()
    
    try:
        # Example 1: Ingest all new documents
        job_id_1 = await manager.ingest_new_documents_only()
        print(f"Started new documents ingestion: {job_id_1}")
        
        # Example 2: Ingest specific judge's documents
        job_id_2 = await manager.ingest_judge_documents("Gilstrap", "txed")
        print(f"Started Gilstrap documents ingestion: {job_id_2}")
        
        # Example 3: Ingest recent documents
        job_id_3 = await manager.ingest_recent_documents(days=7)
        print(f"Started recent documents ingestion: {job_id_3}")
        
        # Monitor jobs
        while True:
            active_jobs = manager.get_active_jobs()
            if not active_jobs:
                break
            
            for job_status in active_jobs:
                print(f"Job {job_status['job_id']}: {job_status['status']}")
                
            await asyncio.sleep(5)
        
        # Get final results
        all_jobs = manager.get_all_jobs()
        for job_status in all_jobs:
            print(f"Final status for {job_status['job_id']}: {job_status['status']}")
            if 'stats' in job_status:
                stats = job_status['stats']
                print(f"  - Processed: {stats['successful_documents']}/{stats['total_documents']}")
                print(f"  - Success rate: {stats['success_rate']:.1f}%")
    
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(example_integration())