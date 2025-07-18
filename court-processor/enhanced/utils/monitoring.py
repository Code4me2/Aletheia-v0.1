"""
Monitoring and metrics utilities for enhanced court document processor

Provides performance monitoring, metrics collection, and health checks.
"""
import time
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil
import threading


@dataclass
class ProcessingMetrics:
    """Container for processing metrics"""
    # Document processing
    documents_processed: int = 0
    documents_failed: int = 0
    total_processing_time: float = 0.0
    
    # Service calls
    service_calls: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    service_failures: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    service_response_times: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))
    
    # Quality metrics
    citations_extracted: int = 0
    duplicates_found: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    # System metrics
    peak_memory_usage: float = 0.0
    cpu_usage_samples: List[float] = field(default_factory=list)
    
    # Timestamps
    start_time: datetime = field(default_factory=datetime.now)
    last_update: datetime = field(default_factory=datetime.now)
    
    def update_processing(self, success: bool, duration: float):
        """Update document processing metrics"""
        if success:
            self.documents_processed += 1
        else:
            self.documents_failed += 1
        
        self.total_processing_time += duration
        self.last_update = datetime.now()
    
    def update_service_call(self, service: str, success: bool, response_time: float):
        """Update service call metrics"""
        self.service_calls[service] += 1
        if not success:
            self.service_failures[service] += 1
        
        self.service_response_times[service].append(response_time)
        # Keep only last 100 response times per service
        if len(self.service_response_times[service]) > 100:
            self.service_response_times[service] = self.service_response_times[service][-100:]
        
        self.last_update = datetime.now()
    
    def update_quality_metrics(self, citations: int = 0, duplicates: int = 0):
        """Update quality metrics"""
        self.citations_extracted += citations
        self.duplicates_found += duplicates
        self.last_update = datetime.now()
    
    def record_error(self, error_type: str):
        """Record error by type"""
        self.errors_by_type[error_type] += 1
        self.last_update = datetime.now()
    
    def update_system_metrics(self):
        """Update system resource metrics"""
        # Memory usage
        memory_mb = psutil.virtual_memory().used / 1024 / 1024
        self.peak_memory_usage = max(self.peak_memory_usage, memory_mb)
        
        # CPU usage
        cpu_percent = psutil.cpu_percent()
        self.cpu_usage_samples.append(cpu_percent)
        # Keep only last 60 samples (for 1 minute at 1 second intervals)
        if len(self.cpu_usage_samples) > 60:
            self.cpu_usage_samples = self.cpu_usage_samples[-60:]
        
        self.last_update = datetime.now()
    
    @property
    def success_rate(self) -> float:
        """Calculate processing success rate"""
        total = self.documents_processed + self.documents_failed
        return self.documents_processed / total if total > 0 else 0.0
    
    @property
    def average_processing_time(self) -> float:
        """Calculate average processing time per document"""
        total_docs = self.documents_processed + self.documents_failed
        return self.total_processing_time / total_docs if total_docs > 0 else 0.0
    
    @property
    def processing_rate(self) -> float:
        """Calculate documents processed per hour"""
        duration = (self.last_update - self.start_time).total_seconds()
        if duration > 0:
            return (self.documents_processed * 3600) / duration
        return 0.0
    
    def get_service_success_rates(self) -> Dict[str, float]:
        """Get success rates by service"""
        rates = {}
        for service in self.service_calls:
            total_calls = self.service_calls[service]
            failures = self.service_failures[service]
            rates[service] = (total_calls - failures) / total_calls if total_calls > 0 else 0.0
        return rates
    
    def get_service_avg_response_times(self) -> Dict[str, float]:
        """Get average response times by service"""
        avg_times = {}
        for service, times in self.service_response_times.items():
            if times:
                avg_times[service] = sum(times) / len(times)
            else:
                avg_times[service] = 0.0
        return avg_times
    
    @property
    def average_cpu_usage(self) -> float:
        """Calculate average CPU usage"""
        return sum(self.cpu_usage_samples) / len(self.cpu_usage_samples) if self.cpu_usage_samples else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'processing': {
                'documents_processed': self.documents_processed,
                'documents_failed': self.documents_failed,
                'success_rate': self.success_rate,
                'processing_rate_per_hour': self.processing_rate,
                'average_processing_time': self.average_processing_time,
                'total_processing_time': self.total_processing_time,
            },
            'services': {
                'calls': dict(self.service_calls),
                'failures': dict(self.service_failures),
                'success_rates': self.get_service_success_rates(),
                'avg_response_times': self.get_service_avg_response_times(),
            },
            'quality': {
                'citations_extracted': self.citations_extracted,
                'duplicates_found': self.duplicates_found,
                'errors_by_type': dict(self.errors_by_type),
            },
            'system': {
                'peak_memory_usage_mb': self.peak_memory_usage,
                'average_cpu_usage': self.average_cpu_usage,
                'current_memory_usage_mb': psutil.virtual_memory().used / 1024 / 1024,
                'current_cpu_usage': psutil.cpu_percent(),
            },
            'timing': {
                'start_time': self.start_time.isoformat(),
                'last_update': self.last_update.isoformat(),
                'uptime_seconds': (self.last_update - self.start_time).total_seconds(),
            }
        }


class ProcessingMonitor:
    """Centralized monitoring for document processing operations"""
    
    def __init__(self):
        self.metrics = ProcessingMetrics()
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
    
    def start_monitoring(self, interval: float = 10.0):
        """Start background monitoring"""
        if self._monitoring_active:
            return
        
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop, 
            args=(interval,),
            daemon=True
        )
        self._monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring"""
        self._monitoring_active = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)
    
    def _monitoring_loop(self, interval: float):
        """Background monitoring loop"""
        while self._monitoring_active:
            with self._lock:
                self.metrics.update_system_metrics()
            time.sleep(interval)
    
    def record_document_processing(self, success: bool, duration: float, 
                                 citations: int = 0, is_duplicate: bool = False):
        """Record document processing event"""
        with self._lock:
            self.metrics.update_processing(success, duration)
            if success:
                self.metrics.update_quality_metrics(citations=citations)
            if is_duplicate:
                self.metrics.update_quality_metrics(duplicates=1)
    
    def record_service_call(self, service: str, success: bool, response_time: float):
        """Record service call event"""
        with self._lock:
            self.metrics.update_service_call(service, success, response_time)
    
    def record_error(self, error: Exception):
        """Record error event"""
        with self._lock:
            error_type = type(error).__name__
            self.metrics.record_error(error_type)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        with self._lock:
            return self.metrics.to_dict()
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status"""
        with self._lock:
            metrics_dict = self.metrics.to_dict()
            
            # Determine health status
            is_healthy = True
            warnings = []
            
            # Check success rate
            if metrics_dict['processing']['success_rate'] < 0.8:
                is_healthy = False
                warnings.append("Low processing success rate")
            
            # Check service failures
            for service, rate in metrics_dict['services']['success_rates'].items():
                if rate < 0.9:
                    warnings.append(f"High failure rate for {service}")
            
            # Check memory usage
            current_memory = metrics_dict['system']['current_memory_usage_mb']
            if current_memory > 8192:  # 8GB
                warnings.append("High memory usage")
            
            # Check CPU usage
            avg_cpu = metrics_dict['system']['average_cpu_usage']
            if avg_cpu > 80:
                warnings.append("High CPU usage")
            
            return {
                'status': 'healthy' if is_healthy else 'unhealthy',
                'warnings': warnings,
                'metrics_summary': {
                    'documents_processed': metrics_dict['processing']['documents_processed'],
                    'success_rate': metrics_dict['processing']['success_rate'],
                    'processing_rate': metrics_dict['processing']['processing_rate_per_hour'],
                    'memory_usage_mb': current_memory,
                    'cpu_usage': metrics_dict['system']['current_cpu_usage'],
                },
                'uptime_seconds': metrics_dict['timing']['uptime_seconds'],
                'last_update': metrics_dict['timing']['last_update'],
            }
    
    def reset_metrics(self):
        """Reset all metrics"""
        with self._lock:
            self.metrics = ProcessingMetrics()


# Global monitor instance
_monitor: Optional[ProcessingMonitor] = None


def get_monitor() -> ProcessingMonitor:
    """Get global monitoring instance"""
    global _monitor
    if _monitor is None:
        _monitor = ProcessingMonitor()
        _monitor.start_monitoring()
    return _monitor


async def monitor_async_operation(operation_name: str, coro):
    """Monitor an async operation"""
    monitor = get_monitor()
    start_time = time.time()
    
    try:
        result = await coro
        duration = time.time() - start_time
        monitor.record_service_call(operation_name, True, duration)
        return result
    except Exception as e:
        duration = time.time() - start_time
        monitor.record_service_call(operation_name, False, duration)
        monitor.record_error(e)
        raise


def monitor_operation(operation_name: str):
    """Decorator to monitor function operations"""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            return await monitor_async_operation(operation_name, func(*args, **kwargs))
        
        def sync_wrapper(*args, **kwargs):
            monitor = get_monitor()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                monitor.record_service_call(operation_name, True, duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                monitor.record_service_call(operation_name, False, duration)
                monitor.record_error(e)
                raise
        
        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator