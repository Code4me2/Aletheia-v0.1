"""
Data Compose Dashboard Integration for Haystack Performance Monitoring

Provides API endpoints and data formatting for integrating Haystack performance
monitoring into the existing Data Compose developer dashboard UI.
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from ..services.haystack_integration import HaystackIntegrationManager
from ..monitoring.performance_dashboard import PerformanceMonitor
from ..utils.logging import get_logger


class DashboardIntegrationAPI:
    """
    API for integrating Haystack performance monitoring with Data Compose dashboard
    """
    
    def __init__(self):
        self.logger = get_logger("dashboard_integration")
        self.performance_monitor: Optional[PerformanceMonitor] = None
        self.haystack_manager: Optional[HaystackIntegrationManager] = None
        self.app = FastAPI(title="Haystack Dashboard Integration API")
        
        # Configure CORS for Data Compose frontend
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        self._setup_routes()
        self.logger.info("Dashboard Integration API initialized")
    
    def _setup_routes(self):
        """Setup API routes for dashboard integration"""
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint for dashboard service status"""
            try:
                if not self.performance_monitor:
                    return JSONResponse({
                        "status": "initializing",
                        "service": "haystack_performance",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                # Get comprehensive health status
                health = await self.haystack_manager.get_integration_health()
                
                # Format for Data Compose dashboard service status pattern
                return JSONResponse({
                    "status": "healthy" if health["integration_manager"]["status"] == "healthy" else "degraded",
                    "service": "haystack_performance",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "details": {
                        "active_jobs": health["integration_manager"]["active_jobs"],
                        "total_jobs": health["integration_manager"]["total_jobs"],
                        "services": health["bulk_service"]["services"]
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                return JSONResponse({
                    "status": "error",
                    "service": "haystack_performance",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "error": str(e)
                })
        
        @self.app.get("/performance/overview")
        async def get_performance_overview():
            """Get performance overview for dashboard card"""
            try:
                if not self.performance_monitor:
                    raise HTTPException(status_code=503, detail="Performance monitor not initialized")
                
                dashboard_data = self.performance_monitor.get_dashboard_data()
                
                # Format for dashboard consumption
                overview = {
                    "timestamp": dashboard_data["timestamp"],
                    "uptime_hours": dashboard_data["uptime_seconds"] / 3600,
                    "system": {
                        "cpu_percent": round(dashboard_data["system_metrics"]["cpu_percent"], 1),
                        "memory_mb": round(dashboard_data["system_metrics"]["memory_rss_mb"], 1),
                        "memory_percent": round(dashboard_data["system_metrics"]["memory_percent"], 1)
                    },
                    "processing": {
                        "total_documents": dashboard_data["processing_metrics"]["documents_processed"],
                        "successful_documents": dashboard_data["processing_metrics"]["documents_successful"],
                        "error_count": dashboard_data["processing_metrics"]["processing_errors"],
                        "error_rate": self._calculate_error_rate(dashboard_data["processing_metrics"])
                    },
                    "performance": {
                        "avg_processing_time": self._get_avg_processing_time(dashboard_data["performance_stats"]),
                        "throughput_last_hour": self._calculate_throughput(dashboard_data),
                        "elasticsearch_operations": dashboard_data["processing_metrics"]["elasticsearch_operations"]
                    },
                    "alerts": {
                        "count": len(dashboard_data["alerts"]),
                        "recent": dashboard_data["alerts"][-3:] if dashboard_data["alerts"] else []
                    },
                    "status_indicator": self._get_status_indicator(dashboard_data)
                }
                
                return JSONResponse(overview)
                
            except Exception as e:
                self.logger.error(f"Failed to get performance overview: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/performance/metrics")
        async def get_detailed_metrics():
            """Get detailed metrics for expanded dashboard view"""
            try:
                if not self.performance_monitor:
                    raise HTTPException(status_code=503, detail="Performance monitor not initialized")
                
                dashboard_data = self.performance_monitor.get_dashboard_data()
                metrics = await self.haystack_manager.get_performance_metrics()
                
                detailed = {
                    "system_trends": dashboard_data["trends"],
                    "connection_pools": metrics["bulk_service"]["connections"],
                    "timing_stats": dashboard_data["performance_stats"],
                    "job_statistics": metrics["job_management"],
                    "recent_alerts": dashboard_data["alerts"][-10:],
                    "recommendations": self._get_recommendations(dashboard_data)
                }
                
                return JSONResponse(detailed)
                
            except Exception as e:
                self.logger.error(f"Failed to get detailed metrics: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/jobs")
        async def get_jobs_status():
            """Get current job status for dashboard"""
            try:
                if not self.haystack_manager:
                    raise HTTPException(status_code=503, detail="Haystack manager not initialized")
                
                all_jobs = self.haystack_manager.get_all_jobs()
                active_jobs = self.haystack_manager.get_active_jobs()
                
                return JSONResponse({
                    "active_jobs": len(active_jobs),
                    "total_jobs": len(all_jobs),
                    "recent_jobs": all_jobs[-5:] if all_jobs else [],
                    "active_details": active_jobs,
                    "summary": {
                        "running": len([j for j in all_jobs if j["status"] == "running"]),
                        "completed": len([j for j in all_jobs if j["status"] == "completed"]),
                        "failed": len([j for j in all_jobs if j["status"] == "failed"])
                    }
                })
                
            except Exception as e:
                self.logger.error(f"Failed to get jobs status: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/jobs/start")
        async def start_ingestion_job(job_config: Dict[str, Any]):
            """Start a new ingestion job from dashboard"""
            try:
                if not self.haystack_manager:
                    raise HTTPException(status_code=503, detail="Haystack manager not initialized")
                
                job_type = job_config.get("type", "ingest_new")
                
                if job_type == "ingest_new":
                    job_id = await self.haystack_manager.ingest_new_documents_only()
                elif job_type == "ingest_judge":
                    judge_name = job_config.get("judge_name")
                    if not judge_name:
                        raise HTTPException(status_code=400, detail="judge_name required for judge ingestion")
                    job_id = await self.haystack_manager.ingest_judge_documents(
                        judge_name=judge_name,
                        court_id=job_config.get("court_id"),
                        max_documents=job_config.get("max_documents", 1000)
                    )
                elif job_type == "ingest_recent":
                    days = job_config.get("days", 30)
                    job_id = await self.haystack_manager.ingest_recent_documents(days=days)
                else:
                    raise HTTPException(status_code=400, detail=f"Unknown job type: {job_type}")
                
                return JSONResponse({
                    "job_id": job_id,
                    "status": "started",
                    "type": job_type,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
            except Exception as e:
                self.logger.error(f"Failed to start job: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/jobs/{job_id}")
        async def get_job_details(job_id: str):
            """Get detailed status for a specific job"""
            try:
                if not self.haystack_manager:
                    raise HTTPException(status_code=503, detail="Haystack manager not initialized")
                
                job_status = self.haystack_manager.get_job_status(job_id)
                if not job_status:
                    raise HTTPException(status_code=404, detail="Job not found")
                
                return JSONResponse(job_status)
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(f"Failed to get job details: {e}")
                raise HTTPException(status_code=500, detail=str(e))
    
    def _calculate_error_rate(self, processing_metrics: Dict[str, Any]) -> float:
        """Calculate error rate percentage"""
        total = processing_metrics["documents_processed"]
        errors = processing_metrics["processing_errors"]
        return round((errors / total * 100) if total > 0 else 0.0, 1)
    
    def _get_avg_processing_time(self, performance_stats: Dict[str, Any]) -> float:
        """Get average processing time in seconds"""
        doc_processing = performance_stats.get("document_processing_time", {})
        return round(doc_processing.get("mean", 0.0), 2)
    
    def _calculate_throughput(self, dashboard_data: Dict[str, Any]) -> float:
        """Calculate throughput for last hour"""
        uptime_hours = dashboard_data["uptime_seconds"] / 3600
        total_docs = dashboard_data["processing_metrics"]["documents_processed"]
        
        if uptime_hours < 1:
            return round(total_docs / max(uptime_hours, 0.1), 1)
        else:
            # Estimate based on recent processing
            return round(total_docs / uptime_hours, 1)
    
    def _get_status_indicator(self, dashboard_data: Dict[str, Any]) -> str:
        """Get overall status indicator for dashboard"""
        alerts = dashboard_data["alerts"]
        recent_alerts = [a for a in alerts if 
                        datetime.fromisoformat(a["timestamp"]) > 
                        datetime.now(timezone.utc) - timedelta(minutes=10)]
        
        error_rate = self._calculate_error_rate(dashboard_data["processing_metrics"])
        cpu_percent = dashboard_data["system_metrics"]["cpu_percent"]
        memory_percent = dashboard_data["system_metrics"]["memory_percent"]
        
        if recent_alerts or error_rate > 10 or cpu_percent > 90 or memory_percent > 90:
            return "warning"
        elif error_rate > 5 or cpu_percent > 80 or memory_percent > 80:
            return "degraded"
        else:
            return "healthy"
    
    def _get_recommendations(self, dashboard_data: Dict[str, Any]) -> List[str]:
        """Get performance recommendations"""
        recommendations = []
        
        cpu_percent = dashboard_data["system_metrics"]["cpu_percent"]
        memory_percent = dashboard_data["system_metrics"]["memory_percent"]
        error_rate = self._calculate_error_rate(dashboard_data["processing_metrics"])
        
        if cpu_percent > 80:
            recommendations.append("Consider reducing batch size due to high CPU usage")
        
        if memory_percent > 80:
            recommendations.append("Memory usage is high - consider restarting services")
        
        if error_rate > 5:
            recommendations.append("Error rate is elevated - check service logs")
        
        if not recommendations:
            recommendations.append("System performance is optimal")
        
        return recommendations
    
    async def initialize(self):
        """Initialize the dashboard integration"""
        try:
            self.performance_monitor = PerformanceMonitor()
            await self.performance_monitor.start()
            
            self.haystack_manager = HaystackIntegrationManager()
            await self.haystack_manager.initialize()
            
            self.logger.info("Dashboard integration initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize dashboard integration: {e}")
            raise
    
    async def cleanup(self):
        """Clean up resources"""
        if self.performance_monitor:
            await self.performance_monitor.stop()
        
        if self.haystack_manager:
            await self.haystack_manager.cleanup()


# Standalone server for testing
async def run_dashboard_integration_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the dashboard integration API server"""
    import uvicorn
    
    integration = DashboardIntegrationAPI()
    
    try:
        await integration.initialize()
        
        config = uvicorn.Config(
            app=integration.app,
            host=host,
            port=port,
            log_level="info"
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        print("Shutting down dashboard integration server...")
    finally:
        await integration.cleanup()


if __name__ == "__main__":
    asyncio.run(run_dashboard_integration_server())