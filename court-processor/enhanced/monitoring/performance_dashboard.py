"""
Performance Dashboard for Enhanced Haystack Bulk Processing

Provides real-time monitoring, metrics collection, and performance analysis
for large-scale document ingestion operations.
"""

import asyncio
import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import logging

import psutil
from ..utils.logging import get_logger


@dataclass
class PerformanceMetric:
    """Single performance metric data point"""
    timestamp: datetime
    metric_name: str
    value: float
    unit: str
    category: str
    tags: Dict[str, str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "category": self.category,
            "tags": self.tags or {}
        }


@dataclass
class SystemSnapshot:
    """System resource snapshot"""
    timestamp: datetime
    cpu_percent: float
    memory_rss_mb: float
    memory_vms_mb: float
    memory_percent: float
    disk_usage_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    open_file_descriptors: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MetricsCollector:
    """
    Collects and aggregates performance metrics
    """
    
    def __init__(self, max_history: int = 1000):
        self.max_history = max_history
        self.metrics_history: deque = deque(maxlen=max_history)
        self.system_snapshots: deque = deque(maxlen=max_history)
        self.logger = get_logger("metrics_collector")
        
        # Performance counters
        self.counters = defaultdict(int)
        self.timers = defaultdict(list)
        self.gauges = defaultdict(float)
        
        # Process monitoring
        self.process = psutil.Process()
        self.start_time = datetime.now(timezone.utc)
        
        self.logger.info("Metrics collector initialized")
    
    def record_metric(self, 
                     name: str, 
                     value: float, 
                     unit: str = "count",
                     category: str = "general",
                     tags: Optional[Dict[str, str]] = None):
        """Record a single metric"""
        metric = PerformanceMetric(
            timestamp=datetime.now(timezone.utc),
            metric_name=name,
            value=value,
            unit=unit,
            category=category,
            tags=tags
        )
        
        self.metrics_history.append(metric)
    
    def increment_counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        self.counters[name] += value
        self.record_metric(name, self.counters[name], "count", "counter", tags)
    
    def record_timing(self, name: str, duration: float, tags: Optional[Dict[str, str]] = None):
        """Record a timing metric"""
        self.timers[name].append(duration)
        
        # Keep only recent timings
        if len(self.timers[name]) > 100:
            self.timers[name] = self.timers[name][-100:]
        
        self.record_metric(name, duration, "seconds", "timing", tags)
    
    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """Set a gauge metric"""
        self.gauges[name] = value
        self.record_metric(name, value, "value", "gauge", tags)
    
    def capture_system_snapshot(self):
        """Capture current system state"""
        try:
            # Get process memory info
            memory_info = self.process.memory_info()
            
            # Get system-wide metrics
            cpu_percent = self.process.cpu_percent()
            memory_percent = self.process.memory_percent()
            
            # Get system disk usage
            disk_usage = psutil.disk_usage('/')
            
            # Get network statistics
            net_io = psutil.net_io_counters()
            
            # Get file descriptor count
            try:
                open_fds = len(self.process.open_files())
            except:
                open_fds = 0
            
            snapshot = SystemSnapshot(
                timestamp=datetime.now(timezone.utc),
                cpu_percent=cpu_percent,
                memory_rss_mb=memory_info.rss / 1024 / 1024,
                memory_vms_mb=memory_info.vms / 1024 / 1024,
                memory_percent=memory_percent,
                disk_usage_percent=disk_usage.percent,
                network_bytes_sent=net_io.bytes_sent,
                network_bytes_recv=net_io.bytes_recv,
                open_file_descriptors=open_fds
            )
            
            self.system_snapshots.append(snapshot)
            
            # Record as metrics
            self.set_gauge("system.cpu_percent", cpu_percent)
            self.set_gauge("system.memory_rss_mb", snapshot.memory_rss_mb)
            self.set_gauge("system.memory_percent", memory_percent)
            self.set_gauge("system.disk_usage_percent", disk_usage.percent)
            self.set_gauge("system.open_file_descriptors", open_fds)
            
        except Exception as e:
            self.logger.warning(f"Failed to capture system snapshot: {e}")
    
    def get_counter_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a counter"""
        return {
            "current_value": self.counters.get(name, 0),
            "total_increments": len([m for m in self.metrics_history if m.metric_name == name])
        }
    
    def get_timing_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics for a timing metric"""
        timings = self.timers.get(name, [])
        
        if not timings:
            return {"count": 0}
        
        sorted_timings = sorted(timings)
        count = len(timings)
        
        return {
            "count": count,
            "min": min(timings),
            "max": max(timings),
            "mean": sum(timings) / count,
            "median": sorted_timings[count // 2],
            "p95": sorted_timings[int(count * 0.95)] if count > 1 else sorted_timings[0],
            "p99": sorted_timings[int(count * 0.99)] if count > 1 else sorted_timings[0]
        }
    
    def get_gauge_value(self, name: str) -> float:
        """Get current gauge value"""
        return self.gauges.get(name, 0.0)
    
    def get_recent_metrics(self, minutes: int = 5) -> List[PerformanceMetric]:
        """Get metrics from the last N minutes"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return [m for m in self.metrics_history if m.timestamp >= cutoff]
    
    def get_system_trends(self, minutes: int = 30) -> Dict[str, List[float]]:
        """Get system resource trends"""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        recent_snapshots = [s for s in self.system_snapshots if s.timestamp >= cutoff]
        
        if not recent_snapshots:
            return {}
        
        return {
            "cpu_percent": [s.cpu_percent for s in recent_snapshots],
            "memory_rss_mb": [s.memory_rss_mb for s in recent_snapshots],
            "memory_percent": [s.memory_percent for s in recent_snapshots],
            "timestamps": [s.timestamp.isoformat() for s in recent_snapshots]
        }
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export all metrics for external systems"""
        return {
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
            "timing_stats": {name: self.get_timing_stats(name) for name in self.timers.keys()},
            "recent_metrics": [m.to_dict() for m in self.get_recent_metrics()],
            "system_trends": self.get_system_trends(),
            "uptime_seconds": (datetime.now(timezone.utc) - self.start_time).total_seconds(),
            "export_timestamp": datetime.now(timezone.utc).isoformat()
        }


class PerformanceDashboard:
    """
    Real-time performance dashboard for bulk ingestion monitoring
    """
    
    def __init__(self, 
                 metrics_collector: MetricsCollector,
                 update_interval: int = 5):
        self.metrics = metrics_collector
        self.update_interval = update_interval
        self.logger = get_logger("performance_dashboard")
        
        # Dashboard state
        self.is_running = False
        self.alerts = []
        self.thresholds = {
            "cpu_percent": 90.0,
            "memory_percent": 85.0,
            "disk_usage_percent": 90.0,
            "error_rate": 5.0,  # 5% error rate
            "throughput_min": 1.0  # minimum 1 doc/sec
        }
        
        self.logger.info("Performance dashboard initialized")
    
    async def start_monitoring(self):
        """Start real-time monitoring"""
        self.is_running = True
        self.logger.info("Starting performance monitoring...")
        
        while self.is_running:
            try:
                # Capture system metrics
                self.metrics.capture_system_snapshot()
                
                # Check for alerts
                await self._check_alerts()
                
                # Log periodic status
                await self._log_status()
                
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.update_interval)
    
    def stop_monitoring(self):
        """Stop monitoring"""
        self.is_running = False
        self.logger.info("Performance monitoring stopped")
    
    async def _check_alerts(self):
        """Check for performance alerts"""
        current_time = datetime.now(timezone.utc)
        
        # Check CPU usage
        cpu_percent = self.metrics.get_gauge_value("system.cpu_percent")
        if cpu_percent > self.thresholds["cpu_percent"]:
            self._add_alert("high_cpu", f"CPU usage {cpu_percent:.1f}% exceeds threshold {self.thresholds['cpu_percent']}%")
        
        # Check memory usage
        memory_percent = self.metrics.get_gauge_value("system.memory_percent")
        if memory_percent > self.thresholds["memory_percent"]:
            self._add_alert("high_memory", f"Memory usage {memory_percent:.1f}% exceeds threshold {self.thresholds['memory_percent']}%")
        
        # Check disk usage
        disk_percent = self.metrics.get_gauge_value("system.disk_usage_percent")
        if disk_percent > self.thresholds["disk_usage_percent"]:
            self._add_alert("high_disk", f"Disk usage {disk_percent:.1f}% exceeds threshold {self.thresholds['disk_usage_percent']}%")
        
        # Check error rates
        recent_metrics = self.metrics.get_recent_metrics(minutes=5)
        error_metrics = [m for m in recent_metrics if "error" in m.metric_name.lower()]
        success_metrics = [m for m in recent_metrics if "success" in m.metric_name.lower()]
        
        if error_metrics and success_metrics:
            error_count = len(error_metrics)
            total_count = len(error_metrics) + len(success_metrics)
            error_rate = (error_count / total_count) * 100
            
            if error_rate > self.thresholds["error_rate"]:
                self._add_alert("high_error_rate", f"Error rate {error_rate:.1f}% exceeds threshold {self.thresholds['error_rate']}%")
    
    def _add_alert(self, alert_type: str, message: str):
        """Add a performance alert"""
        alert = {
            "type": alert_type,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "warning"
        }
        
        # Avoid duplicate recent alerts
        recent_alerts = [a for a in self.alerts if 
                        datetime.fromisoformat(a["timestamp"]) > datetime.now(timezone.utc) - timedelta(minutes=5)]
        
        if not any(a["type"] == alert_type for a in recent_alerts):
            self.alerts.append(alert)
            self.logger.warning(f"Performance alert: {message}")
            
            # Keep only recent alerts
            cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            self.alerts = [a for a in self.alerts if datetime.fromisoformat(a["timestamp"]) >= cutoff]
    
    async def _log_status(self):
        """Log periodic status summary"""
        uptime = datetime.now(timezone.utc) - self.metrics.start_time
        
        # Get key metrics
        cpu = self.metrics.get_gauge_value("system.cpu_percent")
        memory_mb = self.metrics.get_gauge_value("system.memory_rss_mb")
        memory_pct = self.metrics.get_gauge_value("system.memory_percent")
        
        # Get processing stats
        doc_count = self.metrics.counters.get("documents_processed", 0)
        error_count = self.metrics.counters.get("processing_errors", 0)
        
        self.logger.info(
            f"Status - Uptime: {uptime}, CPU: {cpu:.1f}%, "
            f"Memory: {memory_mb:.1f}MB ({memory_pct:.1f}%), "
            f"Docs: {doc_count}, Errors: {error_count}"
        )
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": (datetime.now(timezone.utc) - self.metrics.start_time).total_seconds(),
            "system_metrics": {
                "cpu_percent": self.metrics.get_gauge_value("system.cpu_percent"),
                "memory_rss_mb": self.metrics.get_gauge_value("system.memory_rss_mb"),
                "memory_percent": self.metrics.get_gauge_value("system.memory_percent"),
                "disk_usage_percent": self.metrics.get_gauge_value("system.disk_usage_percent"),
                "open_file_descriptors": self.metrics.get_gauge_value("system.open_file_descriptors")
            },
            "processing_metrics": {
                "documents_processed": self.metrics.counters.get("documents_processed", 0),
                "documents_successful": self.metrics.counters.get("documents_successful", 0),
                "processing_errors": self.metrics.counters.get("processing_errors", 0),
                "elasticsearch_operations": self.metrics.counters.get("elasticsearch_operations", 0),
                "database_operations": self.metrics.counters.get("database_operations", 0)
            },
            "performance_stats": {
                "document_processing_time": self.metrics.get_timing_stats("document_processing_time"),
                "elasticsearch_index_time": self.metrics.get_timing_stats("elasticsearch_index_time"),
                "database_query_time": self.metrics.get_timing_stats("database_query_time"),
                "embedding_generation_time": self.metrics.get_timing_stats("embedding_generation_time")
            },
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "trends": self.metrics.get_system_trends(minutes=30),
            "thresholds": self.thresholds
        }
    
    def generate_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report"""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Get metrics from the specified period
        period_metrics = [m for m in self.metrics.metrics_history if m.timestamp >= cutoff]
        
        if not period_metrics:
            return {"error": "No metrics available for the specified period"}
        
        # Aggregate by category
        categories = defaultdict(list)
        for metric in period_metrics:
            categories[metric.category].append(metric)
        
        # Calculate summary statistics
        summary = {}
        for category, metrics in categories.items():
            values = [m.value for m in metrics]
            if values:
                summary[category] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "mean": sum(values) / len(values),
                    "total": sum(values) if category == "counter" else None
                }
        
        # Get error rate
        error_metrics = [m for m in period_metrics if "error" in m.metric_name.lower()]
        total_operations = len([m for m in period_metrics if m.category == "counter"])
        error_rate = (len(error_metrics) / total_operations * 100) if total_operations > 0 else 0
        
        # Get throughput
        doc_count = self.metrics.counters.get("documents_processed", 0)
        uptime_hours = (datetime.now(timezone.utc) - self.metrics.start_time).total_seconds() / 3600
        throughput = doc_count / uptime_hours if uptime_hours > 0 else 0
        
        return {
            "report_period_hours": hours,
            "report_generated": datetime.now(timezone.utc).isoformat(),
            "summary_statistics": summary,
            "key_metrics": {
                "total_documents_processed": doc_count,
                "error_rate_percent": error_rate,
                "average_throughput_per_hour": throughput,
                "uptime_hours": uptime_hours
            },
            "alerts_summary": {
                "total_alerts": len(self.alerts),
                "alert_types": list(set(a["type"] for a in self.alerts))
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance recommendations"""
        recommendations = []
        
        # Check CPU usage
        avg_cpu = self.metrics.get_gauge_value("system.cpu_percent")
        if avg_cpu > 80:
            recommendations.append("Consider reducing batch size or adding more workers due to high CPU usage")
        
        # Check memory usage
        avg_memory = self.metrics.get_gauge_value("system.memory_percent")
        if avg_memory > 80:
            recommendations.append("Consider implementing memory cleanup or reducing batch sizes due to high memory usage")
        
        # Check processing times
        processing_stats = self.metrics.get_timing_stats("document_processing_time")
        if processing_stats.get("mean", 0) > 10:  # 10 seconds per document
            recommendations.append("Document processing time is high - consider optimizing metadata extraction or embedding generation")
        
        # Check error rate
        error_count = self.metrics.counters.get("processing_errors", 0)
        total_count = self.metrics.counters.get("documents_processed", 1)
        error_rate = (error_count / total_count) * 100
        
        if error_rate > 2:
            recommendations.append("Error rate is elevated - review error logs and consider implementing retry mechanisms")
        
        # Check throughput
        doc_count = self.metrics.counters.get("documents_processed", 0)
        uptime_hours = (datetime.now(timezone.utc) - self.metrics.start_time).total_seconds() / 3600
        throughput = doc_count / uptime_hours if uptime_hours > 0 else 0
        
        if throughput < 100:  # Less than 100 docs/hour
            recommendations.append("Throughput is low - consider increasing batch sizes, adding workers, or optimizing database queries")
        
        if not recommendations:
            recommendations.append("System performance is within acceptable ranges")
        
        return recommendations


class PerformanceMonitor:
    """
    Main performance monitoring coordinator
    """
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.dashboard = PerformanceDashboard(self.metrics_collector)
        self.monitoring_task: Optional[asyncio.Task] = None
        self.logger = get_logger("performance_monitor")
    
    async def start(self):
        """Start performance monitoring"""
        self.monitoring_task = asyncio.create_task(self.dashboard.start_monitoring())
        self.logger.info("Performance monitoring started")
    
    async def stop(self):
        """Stop performance monitoring"""
        self.dashboard.stop_monitoring()
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info("Performance monitoring stopped")
    
    def get_metrics_collector(self) -> MetricsCollector:
        """Get the metrics collector for recording metrics"""
        return self.metrics_collector
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get current dashboard data"""
        return self.dashboard.get_dashboard_data()
    
    def generate_report(self, hours: int = 24) -> Dict[str, Any]:
        """Generate performance report"""
        return self.dashboard.generate_report(hours)
    
    def export_metrics(self) -> Dict[str, Any]:
        """Export metrics for external monitoring systems"""
        return self.metrics_collector.export_metrics()


# Example usage and integration
async def example_monitoring():
    """Example of how to use the performance monitoring system"""
    
    monitor = PerformanceMonitor()
    await monitor.start()
    
    try:
        # Simulate some work with metrics
        metrics = monitor.get_metrics_collector()
        
        for i in range(100):
            # Simulate document processing
            start_time = time.time()
            
            # Simulate work
            await asyncio.sleep(0.1)
            
            # Record metrics
            processing_time = time.time() - start_time
            metrics.record_timing("document_processing_time", processing_time)
            metrics.increment_counter("documents_processed")
            
            if i % 10 == 0:
                metrics.increment_counter("documents_successful")
            else:
                metrics.increment_counter("processing_errors")
            
            # Get dashboard data every 10 iterations
            if i % 10 == 0:
                dashboard_data = monitor.get_dashboard_data()
                print(f"Processed {dashboard_data['processing_metrics']['documents_processed']} documents")
        
        # Generate final report
        report = monitor.generate_report(hours=1)
        print("\nPerformance Report:")
        print(f"Total documents: {report['key_metrics']['total_documents_processed']}")
        print(f"Error rate: {report['key_metrics']['error_rate_percent']:.2f}%")
        print(f"Throughput: {report['key_metrics']['average_throughput_per_hour']:.1f} docs/hour")
    
    finally:
        await monitor.stop()


if __name__ == "__main__":
    asyncio.run(example_monitoring())