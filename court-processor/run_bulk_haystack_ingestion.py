#!/usr/bin/env python3
"""
Bulk Haystack Ingestion Runner

Command-line tool for running large-scale document ingestion to Haystack/Elasticsearch.
Provides monitoring, performance optimization, and job management capabilities.
"""

import asyncio
import argparse
import sys
import time
import signal
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

# Add the enhanced directory to the path
sys.path.insert(0, str(Path(__file__).parent / "enhanced"))

from enhanced.services.haystack_bulk_service import EnhancedHaystackBulkService
from enhanced.services.haystack_integration import HaystackIntegrationManager
from enhanced.utils.logging import get_logger


class BulkIngestionRunner:
    """
    Command-line runner for bulk Haystack ingestion operations
    """
    
    def __init__(self):
        self.logger = get_logger("bulk_ingestion_runner")
        self.manager: Optional[HaystackIntegrationManager] = None
        self.running = True
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.running = False
    
    async def initialize(self):
        """Initialize the ingestion manager"""
        self.manager = HaystackIntegrationManager()
        await self.manager.initialize()
        self.logger.info("Bulk ingestion runner initialized")
    
    async def cleanup(self):
        """Clean up resources"""
        if self.manager:
            await self.manager.cleanup()
    
    async def run_ingest_all(self, 
                           court_filter: Optional[str] = None,
                           date_filter: Optional[str] = None,
                           judge_filter: Optional[str] = None,
                           monitor: bool = True) -> str:
        """Run ingestion of all court documents"""
        self.logger.info("Starting ingestion of all court documents")
        
        if court_filter:
            self.logger.info(f"Court filter: {court_filter}")
        if date_filter:
            self.logger.info(f"Date filter: {date_filter}")
        if judge_filter:
            self.logger.info(f"Judge filter: {judge_filter}")
        
        job_id = await self.manager.ingest_all_court_documents(
            court_filter=court_filter,
            date_filter=date_filter,
            judge_filter=judge_filter
        )
        
        self.logger.info(f"Ingestion job started: {job_id}")
        
        if monitor:
            await self._monitor_job(job_id)
        
        return job_id
    
    async def run_ingest_new(self, monitor: bool = True) -> str:
        """Run ingestion of new documents only"""
        self.logger.info("Starting ingestion of new documents only")
        
        job_id = await self.manager.ingest_new_documents_only()
        self.logger.info(f"New documents ingestion job started: {job_id}")
        
        if monitor:
            await self._monitor_job(job_id)
        
        return job_id
    
    async def run_ingest_judge(self, 
                             judge_name: str,
                             court_id: Optional[str] = None,
                             max_documents: int = 1000,
                             monitor: bool = True) -> str:
        """Run ingestion for specific judge"""
        self.logger.info(f"Starting ingestion for judge: {judge_name}")
        
        if court_id:
            self.logger.info(f"Court filter: {court_id}")
        
        job_id = await self.manager.ingest_judge_documents(
            judge_name=judge_name,
            court_id=court_id,
            max_documents=max_documents
        )
        
        self.logger.info(f"Judge ingestion job started: {job_id}")
        
        if monitor:
            await self._monitor_job(job_id)
        
        return job_id
    
    async def run_ingest_recent(self, days: int = 30, monitor: bool = True) -> str:
        """Run ingestion for recent documents"""
        self.logger.info(f"Starting ingestion for documents from last {days} days")
        
        job_id = await self.manager.ingest_recent_documents(days=days)
        self.logger.info(f"Recent documents ingestion job started: {job_id}")
        
        if monitor:
            await self._monitor_job(job_id)
        
        return job_id
    
    async def _monitor_job(self, job_id: str):
        """Monitor a job until completion"""
        self.logger.info(f"Monitoring job: {job_id}")
        
        last_status = None
        start_time = time.time()
        
        while self.running:
            try:
                status = self.manager.get_job_status(job_id)
                
                if not status:
                    self.logger.error(f"Job {job_id} not found")
                    break
                
                current_status = status['status']
                
                # Log status changes
                if current_status != last_status:
                    self.logger.info(f"Job {job_id} status: {current_status}")
                    last_status = current_status
                
                # Show progress for running jobs
                if current_status == "running":
                    elapsed = time.time() - start_time
                    self.logger.info(f"Job {job_id} running for {elapsed:.1f}s...")
                
                # Job completed
                elif current_status in ["completed", "failed", "cancelled"]:
                    elapsed = time.time() - start_time
                    
                    if current_status == "completed" and 'stats' in status:
                        stats = status['stats']
                        self.logger.info(
                            f"Job {job_id} completed successfully in {elapsed:.1f}s:\n"
                            f"  - Total documents: {stats['total_documents']}\n"
                            f"  - Successful: {stats['successful_documents']}\n"
                            f"  - Failed: {stats['failed_documents']}\n"
                            f"  - Duplicates: {stats['duplicate_documents']}\n"
                            f"  - Success rate: {stats['success_rate']:.1f}%\n"
                            f"  - Throughput: {stats['throughput']:.2f} docs/sec"
                        )
                    elif current_status == "failed":
                        error = status.get('error', 'Unknown error')
                        self.logger.error(f"Job {job_id} failed after {elapsed:.1f}s: {error}")
                    else:
                        self.logger.info(f"Job {job_id} {current_status} after {elapsed:.1f}s")
                    
                    break
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except KeyboardInterrupt:
                self.logger.info("Monitoring interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error monitoring job {job_id}: {e}")
                await asyncio.sleep(5)
    
    async def show_job_status(self, job_id: Optional[str] = None):
        """Show status of jobs"""
        if job_id:
            status = self.manager.get_job_status(job_id)
            if status:
                self._print_job_status(status)
            else:
                print(f"Job {job_id} not found")
        else:
            jobs = self.manager.get_all_jobs()
            if jobs:
                print(f"Found {len(jobs)} jobs:")
                for job_status in jobs:
                    self._print_job_status(job_status)
            else:
                print("No jobs found")
    
    def _print_job_status(self, status: Dict[str, Any]):
        """Print formatted job status"""
        print(f"\nJob ID: {status['job_id']}")
        print(f"Type: {status['job_type']}")
        print(f"Status: {status['status']}")
        print(f"Created: {status['created_at']}")
        
        if 'stats' in status:
            stats = status['stats']
            print(f"Progress:")
            print(f"  - Total: {stats['total_documents']}")
            print(f"  - Successful: {stats['successful_documents']}")
            print(f"  - Failed: {stats['failed_documents']}")
            print(f"  - Success rate: {stats['success_rate']:.1f}%")
            print(f"  - Throughput: {stats['throughput']:.2f} docs/sec")
        
        if 'error' in status:
            print(f"Error: {status['error']}")
    
    async def show_health(self):
        """Show system health status"""
        health = await self.manager.get_integration_health()
        
        print("System Health Status:")
        print(f"Integration Manager: {health['integration_manager']['status']}")
        print(f"Active Jobs: {health['integration_manager']['active_jobs']}")
        print(f"Total Jobs: {health['integration_manager']['total_jobs']}")
        
        bulk_health = health['bulk_service']
        print(f"\nBulk Service: {bulk_health['status']}")
        
        if 'services' in bulk_health:
            services = bulk_health['services']
            print("Service Connections:")
            for service, info in services.items():
                status = "✓" if info.get('connected', False) else "✗"
                print(f"  - {service}: {status}")
    
    async def show_metrics(self):
        """Show performance metrics"""
        metrics = await self.manager.get_performance_metrics()
        
        print("Performance Metrics:")
        
        if 'bulk_service' in metrics:
            bulk_metrics = metrics['bulk_service']
            
            if 'system' in bulk_metrics:
                system = bulk_metrics['system']
                print(f"System Resources:")
                print(f"  - Memory RSS: {system['memory_rss_mb']:.1f} MB")
                print(f"  - CPU: {system['cpu_percent']:.1f}%")
            
            if 'connections' in bulk_metrics:
                connections = bulk_metrics['connections']
                print(f"Connection Pools:")
                for service, info in connections.items():
                    if isinstance(info, dict) and 'size' in info:
                        print(f"  - {service}: {info['idle_connections']}/{info['size']} idle")
        
        if 'job_management' in metrics:
            job_stats = metrics['job_management']
            print(f"Job Statistics:")
            print(f"  - Total: {job_stats['total_jobs']}")
            print(f"  - Running: {job_stats['running_jobs']}")
            print(f"  - Completed: {job_stats['completed_jobs']}")
            print(f"  - Failed: {job_stats['failed_jobs']}")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Bulk Haystack Ingestion Tool")
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Ingest all documents
    ingest_all_parser = subparsers.add_parser('ingest-all', help='Ingest all court documents')
    ingest_all_parser.add_argument('--court', help='Filter by court ID')
    ingest_all_parser.add_argument('--date-after', help='Filter by date filed after (YYYY-MM-DD)')
    ingest_all_parser.add_argument('--judge', help='Filter by judge name')
    ingest_all_parser.add_argument('--no-monitor', action='store_true', help="Don't monitor job progress")
    
    # Ingest new documents
    ingest_new_parser = subparsers.add_parser('ingest-new', help='Ingest new documents only')
    ingest_new_parser.add_argument('--no-monitor', action='store_true', help="Don't monitor job progress")
    
    # Ingest judge documents
    ingest_judge_parser = subparsers.add_parser('ingest-judge', help='Ingest documents for specific judge')
    ingest_judge_parser.add_argument('judge_name', help='Judge name to search for')
    ingest_judge_parser.add_argument('--court', help='Filter by court ID')
    ingest_judge_parser.add_argument('--max-docs', type=int, default=1000, help='Maximum documents to ingest')
    ingest_judge_parser.add_argument('--no-monitor', action='store_true', help="Don't monitor job progress")
    
    # Ingest recent documents
    ingest_recent_parser = subparsers.add_parser('ingest-recent', help='Ingest recent documents')
    ingest_recent_parser.add_argument('--days', type=int, default=30, help='Number of days back to search')
    ingest_recent_parser.add_argument('--no-monitor', action='store_true', help="Don't monitor job progress")
    
    # Job management
    status_parser = subparsers.add_parser('status', help='Show job status')
    status_parser.add_argument('job_id', nargs='?', help='Specific job ID (optional)')
    
    # Health and monitoring
    subparsers.add_parser('health', help='Show system health')
    subparsers.add_parser('metrics', help='Show performance metrics')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    runner = BulkIngestionRunner()
    
    try:
        await runner.initialize()
        
        if args.command == 'ingest-all':
            await runner.run_ingest_all(
                court_filter=args.court,
                date_filter=args.date_after,
                judge_filter=args.judge,
                monitor=not args.no_monitor
            )
        
        elif args.command == 'ingest-new':
            await runner.run_ingest_new(monitor=not args.no_monitor)
        
        elif args.command == 'ingest-judge':
            await runner.run_ingest_judge(
                judge_name=args.judge_name,
                court_id=args.court,
                max_documents=args.max_docs,
                monitor=not args.no_monitor
            )
        
        elif args.command == 'ingest-recent':
            await runner.run_ingest_recent(
                days=args.days,
                monitor=not args.no_monitor
            )
        
        elif args.command == 'status':
            await runner.show_job_status(args.job_id)
        
        elif args.command == 'health':
            await runner.show_health()
        
        elif args.command == 'metrics':
            await runner.show_metrics()
    
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    finally:
        await runner.cleanup()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())