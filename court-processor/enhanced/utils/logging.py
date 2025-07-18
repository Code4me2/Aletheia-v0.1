"""
Enhanced logging utilities for court document processor

Provides structured logging with performance monitoring, context tracking,
and enhanced error reporting.
"""
import logging
import logging.config
import time
import traceback
from contextlib import contextmanager
from typing import Any, Dict, Optional
from functools import wraps

from ..config import get_settings, Environment


class EnhancedFormatter(logging.Formatter):
    """Enhanced log formatter with additional context"""
    
    def format(self, record):
        # Add processing context if available
        if hasattr(record, 'document_id'):
            record.msg = f"[doc:{record.document_id}] {record.msg}"
        
        if hasattr(record, 'batch_id'):
            record.msg = f"[batch:{record.batch_id}] {record.msg}"
        
        if hasattr(record, 'processing_time'):
            record.msg = f"{record.msg} (took {record.processing_time:.2f}s)"
        
        return super().format(record)


class ContextLogger:
    """Logger with processing context"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.context: Dict[str, Any] = {}
    
    def set_context(self, **kwargs):
        """Set logging context"""
        self.context.update(kwargs)
    
    def clear_context(self):
        """Clear logging context"""
        self.context.clear()
    
    def _log_with_context(self, level, msg, *args, **kwargs):
        """Log message with context"""
        # Create a new record with context
        extra = kwargs.get('extra', {})
        extra.update(self.context)
        kwargs['extra'] = extra
        
        getattr(self.logger, level)(msg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        self._log_with_context('debug', msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._log_with_context('info', msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._log_with_context('warning', msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._log_with_context('error', msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self._log_with_context('critical', msg, *args, **kwargs)
    
    def exception(self, msg, *args, **kwargs):
        """Log exception with full traceback"""
        kwargs['exc_info'] = True
        self.error(msg, *args, **kwargs)


def setup_logging() -> None:
    """Setup enhanced logging configuration"""
    env = Environment()
    config = env.get_logging_config()
    
    # Add enhanced formatter
    config['formatters']['enhanced'] = {
        '()': EnhancedFormatter,
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }
    
    # Update handlers to use enhanced formatter
    for handler_config in config['handlers'].values():
        if handler_config.get('formatter') == 'standard':
            handler_config['formatter'] = 'enhanced'
    
    logging.config.dictConfig(config)


def get_logger(name: str) -> ContextLogger:
    """Get enhanced logger with context support"""
    logger = logging.getLogger(f"enhanced.{name}")
    return ContextLogger(logger)


@contextmanager
def log_processing_time(logger: ContextLogger, operation: str, **context):
    """Context manager to log processing time"""
    start_time = time.time()
    logger.set_context(**context)
    logger.info(f"Starting {operation}")
    
    try:
        yield
        processing_time = time.time() - start_time
        logger.info(f"Completed {operation}", extra={'processing_time': processing_time})
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Failed {operation}: {str(e)}", extra={'processing_time': processing_time})
        raise
    finally:
        logger.clear_context()


def log_performance(operation: str):
    """Decorator to log function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                processing_time = time.time() - start_time
                logger.info(f"{operation} completed", extra={'processing_time': processing_time})
                return result
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"{operation} failed: {str(e)}", extra={'processing_time': processing_time})
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                processing_time = time.time() - start_time
                logger.info(f"{operation} completed", extra={'processing_time': processing_time})
                return result
            except Exception as e:
                processing_time = time.time() - start_time
                logger.error(f"{operation} failed: {str(e)}", extra={'processing_time': processing_time})
                raise
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_error_with_context(logger: ContextLogger, error: Exception, context: Dict[str, Any]):
    """Log error with full context and traceback"""
    error_info = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc(),
        **context
    }
    
    logger.error(f"Error occurred: {str(error)}", extra=error_info)


class ProcessingLogger:
    """Specialized logger for document processing operations"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def start_document_processing(self, document_id: str, document_type: str = "unknown"):
        """Log start of document processing"""
        self.logger.set_context(document_id=document_id, document_type=document_type)
        self.logger.info(f"Starting document processing")
    
    def start_batch_processing(self, batch_id: str, batch_size: int):
        """Log start of batch processing"""
        self.logger.set_context(batch_id=batch_id, batch_size=batch_size)
        self.logger.info(f"Starting batch processing ({batch_size} documents)")
    
    def log_service_call(self, service: str, operation: str, success: bool, duration: float):
        """Log service call"""
        status = "successful" if success else "failed"
        self.logger.info(f"{service} {operation} {status}", extra={'processing_time': duration})
    
    def log_processing_step(self, step: str, details: Optional[Dict[str, Any]] = None):
        """Log processing step"""
        extra = details or {}
        self.logger.info(f"Processing step: {step}", extra=extra)
    
    def log_processing_error(self, step: str, error: Exception, context: Optional[Dict[str, Any]] = None):
        """Log processing error"""
        error_context = context or {}
        error_context['processing_step'] = step
        log_error_with_context(self.logger, error, error_context)
    
    def complete_processing(self, success: bool, duration: float, results: Optional[Dict[str, Any]] = None):
        """Log completion of processing"""
        status = "successful" if success else "failed"
        extra = {'processing_time': duration}
        if results:
            extra.update(results)
        
        self.logger.info(f"Processing completed ({status})", extra=extra)
        self.logger.clear_context()


# Initialize logging on module import
setup_logging()