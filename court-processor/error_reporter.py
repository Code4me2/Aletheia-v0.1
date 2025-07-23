"""
Error reporting system for the court processor pipeline

Provides structured error collection, aggregation, and reporting
throughout the pipeline execution.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict
from pipeline_exceptions import PipelineError


class ErrorCollector:
    """Collects and aggregates errors during pipeline execution"""
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or datetime.now().isoformat()
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.validation_failures: List[Dict[str, Any]] = []
        self.stage_errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.document_errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.start_time = datetime.now()
        
    def add_error(self, error: Exception, stage: str, document_id: Optional[str] = None, context: Optional[Dict] = None):
        """Add an error to the collection"""
        error_record = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'document_id': document_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {}
        }
        
        # Add pipeline error details if available
        if isinstance(error, PipelineError):
            error_record['error_details'] = error.to_dict()
        
        self.errors.append(error_record)
        self.stage_errors[stage].append(error_record)
        
        if document_id:
            self.document_errors[document_id].append(error_record)
    
    def add_warning(self, message: str, stage: str, document_id: Optional[str] = None, context: Optional[Dict] = None):
        """Add a warning to the collection"""
        warning_record = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'document_id': document_id,
            'message': message,
            'context': context or {}
        }
        
        self.warnings.append(warning_record)
    
    def add_validation_failure(self, validation_result: Dict, stage: str, document_id: Optional[str] = None):
        """Add a validation failure"""
        failure_record = {
            'timestamp': datetime.now().isoformat(),
            'stage': stage,
            'document_id': document_id,
            'validation_errors': validation_result.get('errors', []),
            'validation_warnings': validation_result.get('warnings', [])
        }
        
        self.validation_failures.append(failure_record)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get error summary statistics"""
        processing_time = (datetime.now() - self.start_time).total_seconds()
        
        # Group errors by type
        error_types = defaultdict(int)
        for error in self.errors:
            error_types[error['error_type']] += 1
        
        # Stage statistics
        stage_stats = {}
        for stage, errors in self.stage_errors.items():
            stage_stats[stage] = {
                'error_count': len(errors),
                'error_types': defaultdict(int)
            }
            for error in errors:
                stage_stats[stage]['error_types'][error['error_type']] += 1
        
        # Document statistics
        failed_documents = len(self.document_errors)
        document_error_counts = {
            doc_id: len(errors) for doc_id, errors in self.document_errors.items()
        }
        
        return {
            'run_id': self.run_id,
            'processing_time_seconds': processing_time,
            'total_errors': len(self.errors),
            'total_warnings': len(self.warnings),
            'total_validation_failures': len(self.validation_failures),
            'failed_documents': failed_documents,
            'error_types': dict(error_types),
            'stage_statistics': stage_stats,
            'most_problematic_documents': sorted(
                document_error_counts.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed error report"""
        return {
            'summary': self.get_summary(),
            'errors': self.errors,
            'warnings': self.warnings,
            'validation_failures': self.validation_failures,
            'stage_errors': dict(self.stage_errors),
            'document_errors': dict(self.document_errors)
        }
    
    def save_report(self, filepath: str):
        """Save error report to file"""
        report = self.get_detailed_report()
        with open(filepath, 'w') as f:
            json.dump(report, f, indent=2)
    
    def log_summary(self, logger: logging.Logger):
        """Log error summary"""
        summary = self.get_summary()
        
        logger.info("=" * 60)
        logger.info("ERROR REPORT SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Run ID: {summary['run_id']}")
        logger.info(f"Processing time: {summary['processing_time_seconds']:.2f} seconds")
        logger.info(f"Total errors: {summary['total_errors']}")
        logger.info(f"Total warnings: {summary['total_warnings']}")
        logger.info(f"Validation failures: {summary['total_validation_failures']}")
        logger.info(f"Failed documents: {summary['failed_documents']}")
        
        if summary['error_types']:
            logger.info("\nError Types:")
            for error_type, count in summary['error_types'].items():
                logger.info(f"  {error_type}: {count}")
        
        if summary['stage_statistics']:
            logger.info("\nErrors by Stage:")
            for stage, stats in summary['stage_statistics'].items():
                logger.info(f"  {stage}: {stats['error_count']} errors")
                if stats['error_types']:
                    for error_type, count in stats['error_types'].items():
                        logger.info(f"    - {error_type}: {count}")
        
        if summary['most_problematic_documents']:
            logger.info("\nMost Problematic Documents:")
            for doc_id, error_count in summary['most_problematic_documents'][:5]:
                logger.info(f"  Document {doc_id}: {error_count} errors")


class ErrorAggregator:
    """Aggregates errors across multiple pipeline runs"""
    
    def __init__(self):
        self.runs: List[Dict[str, Any]] = []
        
    def add_run(self, error_report: Dict[str, Any]):
        """Add a run's error report"""
        self.runs.append(error_report)
    
    def get_trends(self) -> Dict[str, Any]:
        """Analyze error trends across runs"""
        if not self.runs:
            return {}
        
        # Aggregate statistics
        total_errors_by_run = [run['summary']['total_errors'] for run in self.runs]
        avg_errors = sum(total_errors_by_run) / len(total_errors_by_run)
        
        # Error type trends
        error_type_counts = defaultdict(list)
        for run in self.runs:
            for error_type, count in run['summary']['error_types'].items():
                error_type_counts[error_type].append(count)
        
        # Stage trends
        stage_error_counts = defaultdict(list)
        for run in self.runs:
            for stage, stats in run['summary']['stage_statistics'].items():
                stage_error_counts[stage].append(stats['error_count'])
        
        return {
            'total_runs': len(self.runs),
            'average_errors_per_run': avg_errors,
            'error_trend': 'increasing' if total_errors_by_run[-1] > avg_errors else 'decreasing',
            'most_common_error_types': sorted(
                [(error_type, sum(counts)) for error_type, counts in error_type_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'most_problematic_stages': sorted(
                [(stage, sum(counts)) for stage, counts in stage_error_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }