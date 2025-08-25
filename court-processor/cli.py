#!/usr/bin/env python3
"""
Court Processor - Unified CLI for Judiciary Insights

A human-centered command-line interface for analyzing judicial behavior,
court patterns, and legal trends.
"""

import click
import asyncio
from datetime import datetime
from typing import Optional
import sys
import os
from decimal import Decimal

# Load environment variables from .env file if it exists
from pathlib import Path
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# from services.enhanced_ingestion_service import EnhancedIngestionService  # Replaced by UnifiedCollectionService
from services.database import get_db_connection
from processor import RobustElevenStagePipeline
import json
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.panel import Panel
    from rich import print as rprint
    console = Console()
    RICH_AVAILABLE = True
except ImportError:
    # Fallback for systems without rich
    RICH_AVAILABLE = False
    class Console:
        def print(self, *args, **kwargs):
            # Simple fallback that strips markup
            text = ' '.join(str(arg) for arg in args)
            text = text.replace('[bold blue]', '').replace('[/bold blue]', '')
            text = text.replace('[bold]', '').replace('[/bold]', '')
            text = text.replace('[green]', '').replace('[/green]', '')
            text = text.replace('[red]', '').replace('[/red]', '')
            text = text.replace('[yellow]', '').replace('[/yellow]', '')
            text = text.replace('[cyan]', '').replace('[/cyan]', '')
            text = text.replace('[dim]', '').replace('[/dim]', '')
            print(text)
    console = Console()
    rprint = print
    
    # Mock Progress class
    class Progress:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def add_task(self, description, total=None):
            print(f"Starting: {description}")
            return 0
        def update(self, task_id, advance=1):
            pass
    
    # Mock Table class
    class Table:
        def __init__(self, *args, **kwargs):
            self.rows = []
            self.title = kwargs.get('title', '')
        def add_column(self, *args, **kwargs):
            pass
        def add_row(self, *args):
            self.rows.append(args)
        def __str__(self):
            if self.title:
                print(f"\n{self.title}")
                print("-" * len(self.title))
            for row in self.rows:
                print("  ".join(str(col) for col in row))
            return ""
    
    # Mock Panel class  
    class Panel:
        def __init__(self, content, *args, **kwargs):
            self.content = content
            self.title = kwargs.get('title', '')
        def __str__(self):
            if self.title:
                print(f"\n{self.title}")
                print("-" * len(self.title))
            print(str(self.content))
            return ""

@click.group()
def cli():
    """Court Processor - Judiciary Insights Platform
    
    Analyze judicial behavior, court patterns, and legal trends.
    
    Examples:
        court-processor analyze judge "Rodney Gilstrap"
        court-processor data status
        court-processor collect court txed --years 2020-2025
    """
    pass

@cli.group()
def analyze():
    """Analyze judges, courts, and legal patterns"""
    pass

@analyze.command()
@click.argument('judge_name')
@click.option('--court', help='Filter by court ID (e.g., txed)')
@click.option('--years', help='Year range (e.g., 2020-2025)')
@click.option('--focus', help='Case type focus (e.g., patent)')
@click.option('--export', type=click.Choice(['json', 'csv', 'summary']), help='Export format')
@click.option('--show-content', type=click.Choice(['full', 'preview', 'none']), default='preview', help='How much opinion content to display')
@click.option('--limit', default=10, help='Number of opinions to show')
def judge(judge_name, court, years, focus, export, show_content, limit):
    """Analyze a specific judge's patterns and decisions
    
    Example:
        court-processor analyze judge "Rodney Gilstrap" --court txed --years 2020-2025
    """
    console.print(f"\n[bold blue]🔍 Analyzing Judge {judge_name}[/bold blue]\n")
    
    # Parse years if provided
    date_after = None
    date_before = None
    if years:
        try:
            start_year, end_year = years.split('-')
            date_after = f"{start_year}-01-01"
            date_before = f"{end_year}-12-31"
        except:
            console.print("[red]Invalid year format. Use YYYY-YYYY (e.g., 2020-2025)[/red]")
            return
    
    # Check data availability first
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build query
    query = """
        SELECT COUNT(*), 
               COUNT(CASE WHEN metadata->>'judge_name' IS NOT NULL THEN 1 END) as with_judge,
               COUNT(CASE WHEN metadata->>'docket_number' IS NOT NULL THEN 1 END) as with_docket,
               MIN(metadata->>'date_filed') as earliest,
               MAX(metadata->>'date_filed') as latest
        FROM public.court_documents
        WHERE 1=1
    """
    params = []
    
    if judge_name:
        query += " AND (metadata->>'judge_name' ILIKE %s OR metadata->>'judge_source' ILIKE %s)"
        params.extend([f'%{judge_name}%', f'%{judge_name}%'])
    
    if court:
        query += " AND metadata->>'court_id' = %s"
        params.append(court)
        
    if date_after:
        query += " AND metadata->>'date_filed' >= %s"
        params.append(date_after)
        
    if date_before:
        query += " AND metadata->>'date_filed' <= %s"
        params.append(date_before)
    
    cur.execute(query, params)
    total, with_judge, with_docket, earliest, latest = cur.fetchone()
    
    if total == 0:
        console.print(f"[yellow]No documents found for Judge {judge_name}[/yellow]")
        console.print("\n[dim]Try collecting data first:[/dim]")
        console.print(f"  court-processor collect judge \"{judge_name}\"")
        cur.close()
        conn.close()
        return
    
    # Calculate data quality
    judge_attribution = (with_judge / total * 100) if total > 0 else 0
    docket_coverage = (with_docket / total * 100) if total > 0 else 0
    
    # Display data quality panel
    quality_table = Table(show_header=False, box=None)
    quality_table.add_row("Documents found:", f"{total:,}")
    quality_table.add_row("Judge attribution:", f"{judge_attribution:.1f}%" + (" ✅" if judge_attribution > 95 else " ⚠️"))
    quality_table.add_row("Docket coverage:", f"{docket_coverage:.1f}%")
    quality_table.add_row("Date range:", f"{earliest[:10]} to {latest[:10]}" if earliest else "No dates")
    
    console.print(Panel(quality_table, title="Data Quality", border_style="blue"))
    
    if judge_attribution < 95:
        console.print("\n[yellow]⚠️  Judge attribution below 95% threshold[/yellow]")
        console.print("For complete analysis, improve data quality:")
        console.print(f"  court-processor data fix --judge-attribution --filter-judge \"{judge_name}\"")
    
    # Perform analysis
    console.print("\n[bold]📊 Analysis Results[/bold]")
    
    # Case types
    cur.execute("""
        SELECT metadata->>'opinion_type' as type, COUNT(*) as count
        FROM public.court_documents
        WHERE metadata->>'judge_name' ILIKE %s
        GROUP BY metadata->>'opinion_type'
        ORDER BY count DESC
        LIMIT 5
    """, [f'%{judge_name}%'])
    
    case_types = cur.fetchall()
    if case_types:
        console.print("\n[cyan]Opinion Types:[/cyan]")
        for opinion_type, count in case_types:
            console.print(f"  • {opinion_type or 'Unknown'}: {count}")
    
    # Time patterns
    cur.execute("""
        SELECT 
            EXTRACT(YEAR FROM (metadata->>'date_filed')::date) as year,
            COUNT(*) as cases
        FROM public.court_documents
        WHERE metadata->>'judge_name' ILIKE %s
          AND metadata->>'date_filed' IS NOT NULL
        GROUP BY year
        ORDER BY year DESC
        LIMIT 5
    """, [f'%{judge_name}%'])
    
    time_data = cur.fetchall()
    if time_data:
        console.print("\n[cyan]Cases by Year:[/cyan]")
        for year, count in time_data:
            console.print(f"  • {int(year)}: {count} cases")
    
    # Get opinions with full text (ordered by most recent first)
    console.print("\n[bold]📄 Opinion Documents[/bold]")
    
    cur.execute("""
        SELECT 
            id,
            case_number,
            metadata->>'case_name' as case_name,
            metadata->>'docket_number' as docket_number,
            metadata->>'date_filed' as date_filed,
            metadata->>'opinion_type' as opinion_type,
            metadata->>'court_id' as court_id,
            metadata->>'cl_opinion_id' as opinion_id,
            LENGTH(content) as content_length,
            content,
            document_type
        FROM public.court_documents
        WHERE metadata->>'judge_name' ILIKE %s
          AND document_type IN ('opinion', '020lead')
        ORDER BY 
            CASE 
                WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                THEN (metadata->>'date_filed')::date 
                ELSE '1900-01-01'::date 
            END DESC
        LIMIT %s
    """, [f'%{judge_name}%', limit])
    
    opinions = cur.fetchall()
    opinions_with_content = 0
    opinions_metadata_only = 0
    
    if opinions:
        console.print(f"\n[dim]Showing {len(opinions)} most recent opinions:[/dim]\n")
        
        for idx, (doc_id, case_num, case_name, docket_num, date_filed, op_type, court_id, opinion_id, content_len, content, doc_type) in enumerate(opinions, 1):
            # Header for each opinion
            console.print(f"[bold cyan]{'─' * 80}[/bold cyan]")
            console.print(f"[bold]Opinion {idx}[/bold] | ID: {doc_id} | Type: {doc_type}")
            
            # Metadata section
            if case_name:
                console.print(f"[cyan]Case:[/cyan] {case_name}")
            if case_num:
                console.print(f"[cyan]Case Number:[/cyan] {case_num}")
            if docket_num:
                console.print(f"[cyan]Docket:[/cyan] {docket_num}")
            if date_filed:
                console.print(f"[cyan]Date Filed:[/cyan] {date_filed[:10]}")
            if court_id:
                console.print(f"[cyan]Court:[/cyan] {court_id}")
            if op_type:
                console.print(f"[cyan]Opinion Type:[/cyan] {op_type}")
            
            # Content section
            if show_content != 'none':
                console.print(f"\n[cyan]Content ({content_len:,} characters):[/cyan]")
                
                if content and content_len > 100:
                    opinions_with_content += 1
                    
                    if show_content == 'full':
                        # Show full content
                        clean_content = ' '.join(content.strip().split())
                        console.print(f"\n{clean_content}")
                    else:  # preview mode
                        # Show first 1000 chars and last 500 chars for long documents
                        if content_len > 2000:
                            preview = content[:1000].strip()
                            # Clean up the preview
                            preview = ' '.join(preview.split())
                            console.print(f"\n{preview}")
                            console.print(f"\n[dim]... [{content_len - 1500:,} characters omitted] ...[/dim]")
                            
                            # Show ending
                            ending = content[-500:].strip()
                            ending = ' '.join(ending.split())
                            console.print(f"\n{ending}")
                        else:
                            # Show full content for shorter documents
                            clean_content = ' '.join(content.strip().split())
                            console.print(f"\n{clean_content}")
                else:
                    opinions_metadata_only += 1
                    if content:
                        console.print(f"[dim]{content}[/dim]")
                    else:
                        console.print("[yellow]No content available (metadata only)[/yellow]")
            else:
                # Just count content availability
                if content and content_len > 100:
                    opinions_with_content += 1
                else:
                    opinions_metadata_only += 1
            
            console.print("")  # Blank line between opinions
    
    # Get dockets (condensed view)
    console.print("\n[bold]⚖️ Docket Information[/bold]")
    
    cur.execute("""
        SELECT 
            COUNT(*) as total_dockets,
            COUNT(DISTINCT metadata->>'docket_number') as unique_dockets,
            COUNT(CASE WHEN metadata->>'nature_of_suit' IS NOT NULL THEN 1 END) as with_nos,
            COUNT(CASE WHEN metadata->>'date_terminated' IS NOT NULL THEN 1 END) as terminated
        FROM public.court_documents
        WHERE metadata->>'judge_name' ILIKE %s
          AND document_type = 'docket'
    """, [f'%{judge_name}%'])
    
    docket_stats = cur.fetchone()
    if docket_stats and docket_stats[0] > 0:
        total_dockets, unique_dockets, with_nos, terminated = docket_stats
        console.print(f"\n[cyan]Docket Statistics:[/cyan]")
        console.print(f"  • Total docket entries: {total_dockets}")
        console.print(f"  • Unique dockets: {unique_dockets}")
        console.print(f"  • With nature of suit: {with_nos}")
        console.print(f"  • Terminated cases: {terminated}")
        
        # Show sample dockets
        cur.execute("""
            SELECT 
                metadata->>'docket_number' as docket_num,
                metadata->>'case_name' as case_name,
                metadata->>'nature_of_suit' as nos,
                metadata->>'date_filed' as filed,
                metadata->>'date_terminated' as terminated
            FROM public.court_documents
            WHERE metadata->>'judge_name' ILIKE %s
              AND document_type = 'docket'
              AND metadata->>'docket_number' IS NOT NULL
            ORDER BY 
                CASE 
                    WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                    THEN (metadata->>'date_filed')::date 
                    ELSE '1900-01-01'::date 
                END DESC
            LIMIT 5
        """, [f'%{judge_name}%'])
        
        sample_dockets = cur.fetchall()
        if sample_dockets:
            console.print("\n[cyan]Recent Dockets:[/cyan]")
            for docket_num, case_name, nos, filed, terminated in sample_dockets:
                console.print(f"  • {docket_num}: {case_name or 'Unknown Case'}")
                if nos:
                    console.print(f"    Nature: {nos}")
                if filed:
                    console.print(f"    Filed: {filed[:10]}" + (f", Terminated: {terminated[:10]}" if terminated else ""))
    
    # Summary statistics
    console.print(f"\n[bold]📊 Document Summary[/bold]")
    console.print(f"  • Opinions with full text: {opinions_with_content}")
    console.print(f"  • Opinions metadata only: {opinions_metadata_only}")
    console.print(f"  • Total opinions shown: {len(opinions)}")
    
    # Merged Insights - Show valuable data from combining docket and opinion info
    console.print(f"\n[bold]🔗 Merged Data Insights[/bold]")
    
    # Get case duration insights
    cur.execute("""
        WITH case_durations AS (
            SELECT 
                metadata->>'docket_number' as docket,
                metadata->>'case_name' as case_name,
                MIN(CASE WHEN metadata->>'date_filed' != '' THEN (metadata->>'date_filed')::date END) as filed_date,
                MAX(CASE WHEN metadata->>'date_terminated' != '' THEN (metadata->>'date_terminated')::date END) as terminated_date,
                MAX(CASE WHEN document_type IN ('opinion', '020lead') AND metadata->>'date_filed' != '' 
                    THEN (metadata->>'date_filed')::date END) as opinion_date
            FROM public.court_documents
            WHERE metadata->>'judge_name' ILIKE %s
              AND metadata->>'docket_number' IS NOT NULL
            GROUP BY metadata->>'docket_number', metadata->>'case_name'
            HAVING MIN(CASE WHEN metadata->>'date_filed' != '' THEN (metadata->>'date_filed')::date END) IS NOT NULL
        )
        SELECT 
            COUNT(*) as total_cases,
            AVG(terminated_date - filed_date) as avg_case_duration,
            AVG(opinion_date - filed_date) as avg_time_to_opinion,
            MIN(terminated_date - filed_date) as shortest_case,
            MAX(terminated_date - filed_date) as longest_case
        FROM case_durations
        WHERE terminated_date IS NOT NULL
    """, [f'%{judge_name}%'])
    
    duration_stats = cur.fetchone()
    if duration_stats and duration_stats[0] > 0:
        total_cases, avg_duration, avg_to_opinion, shortest, longest = duration_stats
        console.print(f"\n[cyan]Case Duration Analysis:[/cyan]")
        if avg_duration:
            console.print(f"  • Average case duration: {int(avg_duration)} days")
        if avg_to_opinion:
            console.print(f"  • Average time to opinion: {int(avg_to_opinion)} days")
        if shortest and longest:
            console.print(f"  • Range: {int(shortest)} to {int(longest)} days")
    
    # Nature of suit patterns
    cur.execute("""
        SELECT 
            metadata->>'nature_of_suit' as nos,
            COUNT(DISTINCT metadata->>'docket_number') as case_count,
            COUNT(CASE WHEN document_type IN ('opinion', '020lead') THEN 1 END) as opinion_count
        FROM public.court_documents
        WHERE metadata->>'judge_name' ILIKE %s
          AND metadata->>'nature_of_suit' IS NOT NULL
        GROUP BY metadata->>'nature_of_suit'
        ORDER BY case_count DESC
        LIMIT 5
    """, [f'%{judge_name}%'])
    
    nos_patterns = cur.fetchall()
    if nos_patterns:
        console.print(f"\n[cyan]Case Type Patterns:[/cyan]")
        for nos, case_count, opinion_count in nos_patterns:
            ratio = opinion_count / case_count if case_count > 0 else 0
            console.print(f"  • {nos}: {case_count} cases, {opinion_count} opinions ({ratio:.1%} opinion rate)")
    
    # Export if requested
    if export:
        export_data = {
            'judge': judge_name,
            'total_documents': total,
            'judge_attribution': judge_attribution,
            'date_range': f"{earliest} to {latest}" if earliest else None,
            'case_types': dict(case_types) if case_types else {},
            'yearly_distribution': {int(year): count for year, count in time_data} if time_data else {},
            'opinions': []
        }
        
        # Add opinion data for export
        for doc_id, case_num, case_name, docket_num, date_filed, op_type, court_id, opinion_id, content_len, content, doc_type in opinions:
            export_data['opinions'].append({
                'id': doc_id,
                'case_number': case_num,
                'case_name': case_name,
                'docket_number': docket_num,
                'date_filed': date_filed,
                'opinion_type': op_type,
                'court_id': court_id,
                'content_length': content_len,
                'content': content if content_len < 10000 else content[:10000] + '... [truncated]'
            })
        
        if export == 'json':
            filename = f"judge_{judge_name.replace(' ', '_').lower()}_analysis.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            console.print(f"\n[green]✅ Exported to {filename}[/green]")
        elif export == 'summary':
            console.print(f"\n[dim]Summary:[/dim] Judge {judge_name} has {total} documents with {judge_attribution:.1f}% attribution")
    
    cur.close()
    conn.close()

@cli.group()
def data():
    """Manage data quality and collection"""
    pass

@data.command()
def status():
    """Check data quality and coverage status"""
    console.print("\n[bold blue]📊 Data Quality Status[/bold blue]\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Overall statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN metadata->>'judge_name' IS NOT NULL THEN 1 END) as with_judge,
            COUNT(CASE WHEN metadata->>'docket_number' IS NOT NULL THEN 1 END) as with_docket,
            COUNT(CASE WHEN metadata->>'court_id' IS NOT NULL THEN 1 END) as with_court,
            COUNT(CASE WHEN content IS NOT NULL AND LENGTH(content) > 100 THEN 1 END) as with_content
        FROM public.court_documents
    """)
    
    total, with_judge, with_docket, with_court, with_content = cur.fetchone()
    
    if total == 0:
        console.print("[yellow]No documents in database[/yellow]")
        console.print("\nStart by collecting some data:")
        console.print("  court-processor collect court txed --limit 100")
        cur.close()
        conn.close()
        return
    
    # Calculate percentages
    judge_pct = (with_judge / total * 100) if total > 0 else 0
    docket_pct = (with_docket / total * 100) if total > 0 else 0
    court_pct = (with_court / total * 100) if total > 0 else 0
    content_pct = (with_content / total * 100) if total > 0 else 0
    
    # Create status table
    table = Table(title="Data Quality Metrics", show_header=True)
    table.add_column("Metric", style="cyan", width=20)
    table.add_column("Coverage", justify="right", width=15)
    table.add_column("Status", width=10)
    table.add_column("Target", width=10)
    
    # Helper function for status icon
    def get_status(pct, target):
        if pct >= target:
            return "✅"
        elif pct >= target * 0.5:
            return "⚠️"
        else:
            return "❌"
    
    table.add_row("Total Documents", f"{total:,}", "📄", "")
    table.add_row("Judge Attribution", f"{judge_pct:.1f}%", get_status(judge_pct, 95), ">95%")
    table.add_row("Docket Numbers", f"{docket_pct:.1f}%", get_status(docket_pct, 90), ">90%")
    table.add_row("Court IDs", f"{court_pct:.1f}%", get_status(court_pct, 100), "100%")
    table.add_row("Text Content", f"{content_pct:.1f}%", get_status(content_pct, 95), ">95%")
    
    console.print(table)
    
    # Check date coverage
    cur.execute("""
        SELECT 
            MIN(CASE WHEN metadata->>'date_filed' != '' THEN (metadata->>'date_filed')::date END) as earliest,
            MAX(CASE WHEN metadata->>'date_filed' != '' THEN (metadata->>'date_filed')::date END) as latest
        FROM public.court_documents
        WHERE metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
    """)
    
    earliest, latest = cur.fetchone()
    if earliest and latest:
        console.print(f"\n[cyan]Date Coverage:[/cyan] {earliest} to {latest}")
    
    # Court distribution
    cur.execute("""
        SELECT metadata->>'court_id' as court, COUNT(*) as count
        FROM public.court_documents
        WHERE metadata->>'court_id' IS NOT NULL
        GROUP BY metadata->>'court_id'
        ORDER BY count DESC
        LIMIT 5
    """)
    
    courts = cur.fetchall()
    if courts:
        console.print("\n[cyan]Top Courts:[/cyan]")
        for court_id, count in courts:
            console.print(f"  • {court_id}: {count:,} documents")
    
    # Provide recommendations
    if judge_pct < 95:
        console.print("\n[yellow]📋 Recommendations:[/yellow]")
        console.print(f"  1. Improve judge attribution ({judge_pct:.1f}% → >95%)")
        console.print("     court-processor data fix --judge-attribution")
        
    if docket_pct < 90:
        console.print(f"  2. Enhance docket coverage ({docket_pct:.1f}% → >90%)")
        console.print("     court-processor data fix --docket-linking")
    
    cur.close()
    conn.close()

@data.command()
@click.option('--judge-attribution', is_flag=True, help='Fix missing judge data')
@click.option('--docket-linking', is_flag=True, help='Fix missing docket numbers')
@click.option('--filter-court', help='Only fix documents from specific court')
@click.option('--filter-judge', help='Only fix documents for specific judge')
@click.option('--limit', default=100, help='Maximum documents to fix')
def fix(judge_attribution, docket_linking, filter_court, filter_judge, limit):
    """Fix data quality issues automatically
    
    Example:
        court-processor data fix --judge-attribution --filter-court txed
    """
    if not judge_attribution and not docket_linking:
        console.print("[yellow]Please specify what to fix:[/yellow]")
        console.print("  --judge-attribution    Fix missing judge data")
        console.print("  --docket-linking      Fix missing docket numbers")
        return
    
    async def run_fix():
        # Import the comprehensive judge extractor for attribution fixes
        from comprehensive_judge_extractor import ComprehensiveJudgeExtractor
        import json
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            if judge_attribution:
                task = progress.add_task("Fixing judge attribution...", total=limit)
                
                # Find documents missing judge data
                conn = get_db_connection()
                cur = conn.cursor()
                
                query = """
                    SELECT id, case_number, metadata, content
                    FROM public.court_documents
                    WHERE metadata->>'judge_name' IS NULL
                       OR metadata->>'judge_name' = ''
                       OR metadata->>'judge_name' = 'Unknown'
                """
                params = []
                
                if filter_court:
                    query += " AND metadata->>'court_id' = %s"
                    params.append(filter_court)
                    
                if filter_judge:
                    query += " AND metadata->>'docket_number' LIKE %s"
                    params.append(f'%-{filter_judge}%')
                    
                query += f" LIMIT {limit}"
                
                cur.execute(query, params)
                documents = cur.fetchall()
                
                console.print(f"Found {len(documents)} documents needing judge attribution fixes\n")
                
                # Initialize judge extractor
                judge_extractor = ComprehensiveJudgeExtractor()
                
                fixed_count = 0
                for doc_id, case_num, metadata, content in documents:
                    try:
                        # Extract judge from multiple sources
                        judge_info = judge_extractor.extract_judge(
                            search_result=metadata,
                            opinion_data=metadata,
                            docket_data=metadata,
                            content=content or ""
                        )
                        
                        if judge_info and judge_info['name'] and judge_info['name'] != 'Unknown':
                            # Update the metadata with judge information
                            updated_metadata = metadata.copy() if metadata else {}
                            updated_metadata['judge_name'] = judge_info['name']
                            updated_metadata['judge_confidence'] = judge_info['confidence']
                            updated_metadata['judge_source'] = judge_info['source']
                            
                            # Update database
                            update_query = """
                                UPDATE public.court_documents 
                                SET metadata = %s,
                                    updated_at = CURRENT_TIMESTAMP
                                WHERE id = %s
                            """
                            cur.execute(update_query, (json.dumps(updated_metadata), doc_id))
                            fixed_count += 1
                            
                            console.print(f"  ✓ Fixed: {case_num} → Judge: {judge_info['name']} (confidence: {judge_info['confidence']:.2f})")
                    except Exception as e:
                        console.print(f"  ✗ Error fixing {case_num}: {str(e)}")
                    
                    progress.update(task, advance=1)
                
                # Commit changes
                conn.commit()
                
                console.print(f"\n[green]✅ Fixed judge attribution for {fixed_count}/{len(documents)} documents[/green]")
                
                # Show statistics
                if fixed_count > 0:
                    cur.execute("""
                        SELECT 
                            COUNT(*) as total,
                            COUNT(CASE WHEN metadata->>'judge_name' IS NOT NULL 
                                      AND metadata->>'judge_name' != '' 
                                      AND metadata->>'judge_name' != 'Unknown' THEN 1 END) as with_judges
                        FROM public.court_documents
                        WHERE 1=1
                    """ + (" AND metadata->>'court_id' = %s" if filter_court else ""), 
                    [filter_court] if filter_court else [])
                    
                    total, with_judges = cur.fetchone()
                    attribution_rate = (with_judges / total * 100) if total > 0 else 0
                    console.print(f"\n[bold]Overall Judge Attribution Rate:[/bold] {attribution_rate:.1f}% ({with_judges}/{total})")
                
                cur.close()
                conn.close()
    
    asyncio.run(run_fix())

@cli.group()
def collect():
    """Collect court documents from various sources"""
    pass

@collect.command()
@click.argument('court_id')
@click.option('--years', help='Year range (e.g., 2020-2025)')
@click.option('--date-after', help='Start date (YYYY-MM-DD)')
@click.option('--date-before', help='End date (YYYY-MM-DD)')
@click.option('--judge', help='Filter by judge name')
@click.option('--limit', default=100, help='Maximum documents to collect')
@click.option('--enhance/--no-enhance', default=False, help='Run 11-stage pipeline enhancement')
@click.option('--extract-pdfs/--no-extract-pdfs', default=True, help='Extract content from PDFs')
@click.option('--store/--no-store', default=True, help='Store to database')
def court(court_id, years, date_after, date_before, judge, limit, enhance, extract_pdfs, store):
    """Collect documents from a specific court with enhanced options
    
    Examples:
        court-processor collect court txed --years 2020-2025 --limit 500
        court-processor collect court txed --judge "Rodney Gilstrap" --limit 50
        court-processor collect court ded --date-after 2024-01-01 --enhance
    """
    console.print(f"\n[bold blue]📥 Enhanced Collection from {court_id.upper()} court[/bold blue]\n")
    
    # Parse years if provided (takes precedence over date-after/before)
    if years:
        try:
            start_year, end_year = years.split('-')
            date_after = f"{start_year}-01-01"
            date_before = f"{end_year}-12-31"
        except:
            console.print("[red]Invalid year format. Use YYYY-YYYY[/red]")
            return
    
    # Display collection parameters
    console.print("[bold]Collection Parameters:[/bold]")
    console.print(f"  Court: {court_id.upper()}")
    if judge:
        console.print(f"  Judge: {judge}")
    if date_after:
        console.print(f"  Date after: {date_after}")
    if date_before:
        console.print(f"  Date before: {date_before}")
    console.print(f"  Max documents: {limit}")
    console.print(f"  11-stage enhancement: {'✅ Enabled' if enhance else '❌ Disabled'}")
    console.print(f"  PDF extraction: {'✅ Enabled' if extract_pdfs else '❌ Disabled'}")
    console.print(f"  Database storage: {'✅ Enabled' if store else '❌ Disabled'}")
    console.print()
    
    async def run_collection():
        # Import unified collection service
        from services.unified_collection_service import UnifiedCollectionService
        
        # Import Progress components locally if not available globally
        if not RICH_AVAILABLE:
            console.print("[yellow]Rich library not available. Using simple output.[/yellow]")
            # Simple version without progress bar
            async with UnifiedCollectionService() as service:
                results = await service.collect_documents(
                    court_id=court_id,
                    judge_name=judge,
                    date_after=date_after,
                    date_before=date_before,
                    max_documents=limit,
                    run_pipeline=enhance,
                    extract_pdfs=extract_pdfs,
                    store_to_db=store
                )
                # Display results (simplified)
                stats = results['statistics']
                console.print(f"\n✅ Collection Complete")
                console.print(f"  Documents collected: {stats['new_documents']}")
                console.print(f"  With content: {stats['with_content']}")
                console.print(f"  With judges: {stats['with_judges']}")
            return
        
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
        
        async with UnifiedCollectionService() as service:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(f"Collecting from {court_id}...", total=limit)
                
                try:
                    results = await service.collect_documents(
                        court_id=court_id,
                        judge_name=judge,
                        date_after=date_after,
                        date_before=date_before,
                        max_documents=limit,
                        run_pipeline=enhance,
                        extract_pdfs=extract_pdfs,
                        store_to_db=store
                    )
                    
                    progress.update(task, completed=limit)
                    
                    # Display comprehensive results
                    stats = results['statistics']
                    perf = results['performance']
                    
                    console.print(f"\n[green]✅ Collection Complete[/green]")
                    
                    # Document statistics
                    console.print(f"\n[bold]Document Statistics:[/bold]")
                    console.print(f"  Total fetched: {stats['total_fetched']}")
                    console.print(f"  New documents: {stats['new_documents']}")
                    console.print(f"  Duplicates: {stats['duplicates']}")
                    console.print(f"  With content: {stats['with_content']}")
                    console.print(f"  With judges: {stats['with_judges']}")
                    
                    # Calculate rates
                    if stats['new_documents'] > 0:
                        content_rate = (stats['with_content'] / stats['new_documents']) * 100
                        judge_rate = (stats['with_judges'] / stats['new_documents']) * 100
                        console.print(f"\n[bold]Attribution Rates:[/bold]")
                        console.print(f"  Content extraction: {content_rate:.1f}%")
                        console.print(f"  Judge attribution: {judge_rate:.1f}%")
                    
                    # Enhancement statistics
                    if enhance:
                        console.print(f"\n[bold]Enhancement Statistics:[/bold]")
                        console.print(f"  Pipeline enhanced: {stats['pipeline_enhanced']}")
                    
                    if extract_pdfs and stats['pdf_extracted'] > 0:
                        console.print(f"  PDF extractions: {stats['pdf_extracted']}")
                    
                    if store:
                        console.print(f"  Stored to database: {stats['stored_to_db']}")
                    
                    # Performance metrics
                    console.print(f"\n[bold]Performance Metrics:[/bold]")
                    console.print(f"  Fetch time: {perf['fetch_time']:.2f}s")
                    if enhance:
                        console.print(f"  Pipeline time: {perf['pipeline_time']:.2f}s")
                    if store:
                        console.print(f"  Storage time: {perf['storage_time']:.2f}s")
                    console.print(f"  Total time: {perf['total_time']:.2f}s")
                    
                    # Show sample documents
                    if results['documents']:
                        console.print(f"\n[bold]Sample Documents:[/bold]")
                        for i, doc in enumerate(results['documents'][:3], 1):
                            meta = doc.get('meta', {})
                            console.print(f"\n  {i}. {meta.get('case_name', 'Unknown Case')}")
                            console.print(f"     Court: {meta.get('court', 'Unknown')}")
                            console.print(f"     Judge: {meta.get('judge_name', 'Unknown')} (confidence: {meta.get('judge_confidence', 0):.2f})")
                            console.print(f"     Date filed: {meta.get('date_filed', 'Unknown')}")
                            console.print(f"     Content: {len(doc.get('content', ''))} chars")
                            console.print(f"     Type: {meta.get('document_type', 'Unknown')}")
                    
                    # Show errors if any
                    if results['errors']:
                        console.print(f"\n[yellow]⚠️ Errors encountered:[/yellow]")
                        for error in results['errors'][:5]:
                            console.print(f"  - {error}")
                    
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")
    
    asyncio.run(run_collection())

@collect.command()
@click.argument('judge_name')
@click.option('--court', help='Filter by court ID')
@click.option('--years', help='Year range (e.g., 2020-2025)')
@click.option('--limit', default=100, help='Maximum documents to collect')
def judge(judge_name, court, years, limit):
    """Collect documents by a specific judge
    
    Example:
        court-processor collect judge "Rodney Gilstrap" --court txed --years 2020-2025
    """
    console.print(f"\n[bold blue]📥 Collecting cases by Judge {judge_name}[/bold blue]\n")
    
    # Parse years
    date_after = None
    date_before = None
    if years:
        try:
            start_year, end_year = years.split('-')
            date_after = f"{start_year}-01-01"
            date_before = f"{end_year}-12-31"
        except:
            console.print("[red]Invalid year format. Use YYYY-YYYY[/red]")
            return
    
    async def run_collection():
        # Use unified collection service for consistency and better retrieval
        from services.unified_collection_service import UnifiedCollectionService
        
        console.print(f"[dim]Using enhanced retrieval with content extraction[/dim]\n")
        
        # Check if rich is available for progress bar
        if not RICH_AVAILABLE:
            console.print("Rich library not available. Using simple output.")
            async with UnifiedCollectionService() as service:
                results = await service.collect_documents(
                    court_id=court,
                    judge_name=judge_name,
                    date_after=date_after,
                    date_before=date_before,
                    max_documents=limit,
                    run_pipeline=False,
                    extract_pdfs=True,
                    store_to_db=True
                )
                
                if results['success']:
                    console.print(f"\n✅ Collection Complete")
                    console.print(f"  Documents collected: {len(results['documents'])}")
                    console.print(f"  With content: {results['statistics']['with_content']}")
                    console.print(f"  With judges: {results['statistics']['with_judges']}")
                else:
                    console.print(f"\n❌ Collection Failed")
                    for error in results.get('errors', []):
                        console.print(f"  Error: {error}")
        else:
            # Use Progress with proper imports at function level
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:
                
                task = progress.add_task(f"Collecting {judge_name} documents...", total=limit)
                
                try:
                    async with UnifiedCollectionService() as service:
                        results = await service.collect_documents(
                            court_id=court,
                            judge_name=judge_name,
                            date_after=date_after,
                            date_before=date_before,
                            max_documents=limit,
                            run_pipeline=False,
                            extract_pdfs=True,
                            store_to_db=True
                        )
                    
                    progress.update(task, completed=limit)
                    
                    if results['success']:
                        console.print(f"\n[green]✅ Collection Complete[/green]")
                        console.print(f"  Documents collected: {len(results['documents'])}")
                        console.print(f"  With content: {results['statistics']['with_content']}")
                        console.print(f"  With judges: {results['statistics']['with_judges']}")
                        console.print(f"  Average content: {sum(len(d.get('content', '')) for d in results['documents']) // max(1, len(results['documents'])):,} chars")
                    else:
                        console.print(f"\n[red]❌ Collection Failed[/red]")
                        for error in results.get('errors', []):
                            console.print(f"  [red]Error: {error}[/red]")
                    
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")
    
    asyncio.run(run_collection())

@data.command()
@click.option('--type', 'doc_type', type=click.Choice(['opinion', 'docket', 'order', 'all']), default='all', help='Document type filter')
@click.option('--court', help='Filter by court ID')
@click.option('--status', type=click.Choice(['with-content', 'without-content', 'all']), default='all', help='Content status filter')
@click.option('--limit', default=50, help='Number of documents to show')
@click.option('--offset', default=0, help='Pagination offset')
@click.option('--sort', type=click.Choice(['date', 'court', 'type', 'id']), default='date', help='Sort order')
@click.option('--export', type=click.Choice(['json', 'csv']), help='Export format')
def list(doc_type, court, status, limit, offset, sort, export):
    """List indexed documents with filters
    
    Examples:
        court-processor data list --type opinion --court txed
        court-processor data list --status with-content --limit 100
        court-processor data list --export csv > documents.csv
    """
    console.print("\n[bold blue]📋 Document Listing[/bold blue]\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build query
    query = """
        SELECT 
            id,
            case_number,
            document_type,
            metadata->>'case_name' as case_name,
            metadata->>'court_id' as court_id,
            metadata->>'judge_name' as judge_name,
            metadata->>'date_filed' as date_filed,
            metadata->>'docket_number' as docket_number,
            LENGTH(content) as content_length,
            created_at
        FROM public.court_documents
        WHERE 1=1
    """
    
    params = []
    
    # Apply filters
    if doc_type != 'all':
        query += " AND document_type = %s"
        params.append(doc_type)
    
    if court:
        query += " AND metadata->>'court_id' = %s"
        params.append(court)
    
    if status == 'with-content':
        query += " AND LENGTH(content) > 100"
    elif status == 'without-content':
        query += " AND (content IS NULL OR LENGTH(content) <= 100)"
    
    # Add sorting
    if sort == 'date':
        query += """ ORDER BY 
            CASE 
                WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                THEN (metadata->>'date_filed')::date 
                ELSE created_at::date 
            END DESC"""
    elif sort == 'court':
        query += " ORDER BY metadata->>'court_id', created_at DESC"
    elif sort == 'type':
        query += " ORDER BY document_type, created_at DESC"
    else:
        query += " ORDER BY id DESC"
    
    query += " LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    cur.execute(query, params)
    documents = cur.fetchall()
    
    # Get total count
    count_query = "SELECT COUNT(*) FROM public.court_documents WHERE 1=1"
    count_params = []
    if doc_type != 'all':
        count_query += " AND document_type = %s"
        count_params.append(doc_type)
    if court:
        count_query += " AND metadata->>'court_id' = %s"
        count_params.append(court)
    if status == 'with-content':
        count_query += " AND LENGTH(content) > 100"
    elif status == 'without-content':
        count_query += " AND (content IS NULL OR LENGTH(content) <= 100)"
    
    cur.execute(count_query, count_params)
    total = cur.fetchone()[0]
    
    if export == 'json':
        # JSON export
        import json
        data = []
        for doc in documents:
            data.append({
                'id': doc[0],
                'case_number': doc[1],
                'type': doc[2],
                'case_name': doc[3],
                'court': doc[4],
                'judge': doc[5],
                'date_filed': doc[6],
                'docket': doc[7],
                'content_length': doc[8],
                'created_at': str(doc[9])
            })
        print(json.dumps(data, indent=2))
    elif export == 'csv':
        # CSV export
        print("id,case_number,type,case_name,court,judge,date_filed,docket,content_length,created_at")
        for doc in documents:
            print(f"{doc[0]},{doc[1]},{doc[2]},{doc[3]},{doc[4]},{doc[5]},{doc[6]},{doc[7]},{doc[8]},{doc[9]}")
    else:
        # Display in table
        console.print(f"Showing {len(documents)} of {total} documents (offset: {offset})\n")
        
        if documents:
            table = Table(show_header=True)
            table.add_column("ID", style="cyan", width=8)
            table.add_column("Type", width=10)
            table.add_column("Court", width=8)
            table.add_column("Case Name", width=35)
            table.add_column("Judge", width=20)
            table.add_column("Date", width=12)
            table.add_column("Content", width=10)
            
            for doc in documents:
                content_status = "✅" if doc[8] and doc[8] > 100 else "❌"
                case_name = (doc[3] or doc[1] or "Unknown")[:35]
                judge_name = (doc[5] or "-")[:20]
                table.add_row(
                    str(doc[0]),
                    doc[2] or "-",
                    doc[4] or "-",
                    case_name,
                    judge_name,
                    doc[6][:10] if doc[6] else "-",
                    content_status
                )
            
            console.print(table)
            
            if total > limit:
                console.print(f"\n[dim]Page {offset//limit + 1} of {(total-1)//limit + 1}")
                if offset + limit < total:
                    console.print(f"Next page: court-processor data list --offset {offset + limit} --limit {limit}")
        else:
            console.print("[yellow]No documents found matching criteria[/yellow]")
    
    cur.close()
    conn.close()

@data.command()
@click.option('--type', 'doc_type', type=click.Choice(['opinion', 'opinion_doctor', '020lead', 'docket', 'all']), default='all', help='Document type filter')
@click.option('--judge', help='Filter by judge name')
@click.option('--court', help='Filter by court ID')
@click.option('--after', help='Date after (YYYY-MM-DD)')
@click.option('--before', help='Date before (YYYY-MM-DD)')
@click.option('--limit', default=100, help='Maximum documents to export')
@click.option('--format', 'output_format', type=click.Choice(['json', 'jsonl', 'csv']), default='json', help='Export format')
@click.option('--full-content/--preview', default=True, help='Include full content or just preview')
@click.option('--content-format', type=click.Choice(['raw', 'text', 'both']), default='raw', help='Content format (raw XML/HTML, plain text, or both)')
@click.option('--compact', is_flag=True, help='Compact JSON for API use (no indentation, minimal size)')
@click.option('--pretty', is_flag=True, help='Pretty print JSON for human readability (default for stdout)')
@click.option('--min-content-length', type=int, default=0, help='Minimum content length to include (filters out placeholders)')
@click.option('--output', 'output_file', help='Output file (default: stdout)')
def export(doc_type, judge, court, after, before, limit, output_format, full_content, content_format, compact, pretty, min_content_length, output_file):
    """Export documents with full content and metadata
    
    Examples:
        court-processor data export --judge "Rodney Gilstrap" --full-content
        court-processor data export --type opinion_doctor --format jsonl --output opinions.jsonl
        court-processor data export --type 020lead --court txed --limit 50
        court-processor data export --type 020lead --min-content-length 10000 --limit 5
    """
    import json
    import csv
    import sys
    import re
    from datetime import datetime
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build query with filters
    conditions = ["1=1"]
    params = []
    
    if doc_type != 'all':
        conditions.append("document_type = %s")
        params.append(doc_type)
    else:
        # Export only opinion types by default for 'all'
        conditions.append("document_type IN ('opinion', 'opinion_doctor', '020lead')")
    
    if judge:
        conditions.append("metadata->>'judge_name' ILIKE %s")
        params.append(f'%{judge}%')
    
    if court:
        conditions.append("metadata->>'court_id' = %s")
        params.append(court)
    
    if after:
        conditions.append("metadata->>'date_filed' >= %s")
        params.append(after)
    
    if before:
        conditions.append("metadata->>'date_filed' <= %s")
        params.append(before)
    
    if min_content_length > 0:
        conditions.append("LENGTH(content) >= %s")
        params.append(min_content_length)
    
    where_clause = " AND ".join(conditions)
    
    # Select all fields including full content
    query = f"""
        SELECT 
            id,
            case_number,
            document_type,
            content,
            metadata,
            created_at,
            updated_at
        FROM public.court_documents
        WHERE {where_clause}
        ORDER BY 
            CASE 
                WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                THEN (metadata->>'date_filed')::date 
                ELSE created_at::date 
            END DESC
        LIMIT %s
    """
    params.append(limit)
    
    cur.execute(query, params)
    documents = cur.fetchall()
    
    # Helper function to extract plain text from XML/HTML
    def extract_plain_text(content):
        """Extract plain text from XML/HTML content"""
        if not content:
            return ""
        
        from html.parser import HTMLParser
        
        class TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []
                self.in_footnote = False
            
            def handle_starttag(self, tag, attrs):
                if tag == 'footnote':
                    self.in_footnote = True
            
            def handle_endtag(self, tag):
                if tag == 'footnote':
                    self.in_footnote = False
                elif tag == 'p':
                    self.text.append('\n\n')
            
            def handle_data(self, data):
                if not self.in_footnote:
                    self.text.append(data.strip())
        
        try:
            parser = TextExtractor()
            parser.feed(content)
            plain_text = ' '.join(parser.text)
            plain_text = re.sub(r'\s+', ' ', plain_text).strip()
            return plain_text
        except:
            # Fallback to simple tag removal
            text = re.sub(r'<[^>]+>', '', content)
            return re.sub(r'\s+', ' ', text).strip()
    
    # Helper function to remove null values from dict
    def remove_nulls(obj):
        """Recursively remove null values from dict"""
        import builtins
        if isinstance(obj, dict):
            return {k: remove_nulls(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, builtins.list):
            return [remove_nulls(item) for item in obj if item is not None]
        return obj
    
    # Format documents for export
    formatted_docs = []
    for doc in documents:
        doc_id, case_num, doc_type, content, metadata, created, updated = doc
        
        # Parse metadata
        metadata = metadata or {}
        
        if compact:
            # Compact, API-friendly format
            formatted_doc = {
                'id': doc_id,
                'type': doc_type,
                'case_name': metadata.get('case_name'),
                'case_number': case_num,
                'docket_number': metadata.get('docket_number'),
                'court': metadata.get('court_id', metadata.get('court')),
                'judge': metadata.get('judge_name'),
                'date_filed': metadata.get('date_filed'),
                'citations': metadata.get('citations', []),
                'courtlistener_id': metadata.get('cl_opinion_id', metadata.get('cl_id')),
            }
            
            # Add content based on format preference
            if full_content:
                if content_format == 'text':
                    formatted_doc['content'] = extract_plain_text(content) if content else ""
                    formatted_doc['content_format'] = 'text'
                elif content_format == 'both':
                    formatted_doc['content'] = {
                        'raw': content,
                        'text': extract_plain_text(content) if content else "",
                        'format': 'xml' if content and content.startswith('<') else 'text'
                    }
                else:  # raw
                    formatted_doc['content'] = content
                    formatted_doc['content_format'] = 'xml' if content and content.startswith('<') else 'text'
            else:
                preview = content[:500] if content else None
                formatted_doc['content_preview'] = preview
            
            formatted_doc['content_length'] = len(content) if content else 0
            
            # Remove null values
            formatted_doc = remove_nulls(formatted_doc)
            
        else:
            # Structured, comprehensive format
            formatted_doc = {
                'id': doc_id,
                'document_type': doc_type,
                
                # Case information
                'case': {
                    'name': metadata.get('case_name'),
                    'number': case_num,
                    'docket_number': metadata.get('docket_number'),
                    'court_id': metadata.get('court_id', metadata.get('court')),
                    'nature_of_suit': metadata.get('nature_of_suit'),
                    'cause': metadata.get('cause'),
                },
                
                # Judge information
                'judge': {
                    'name': metadata.get('judge_name'),
                    'source': metadata.get('judge_source'),
                },
                
                # Dates
                'dates': {
                    'filed': metadata.get('date_filed'),
                    'terminated': metadata.get('date_terminated'),
                    'created': created.isoformat() if created else None,
                    'updated': updated.isoformat() if updated else None,
                },
                
                # External references
                'courtlistener': {
                    'opinion_id': metadata.get('cl_opinion_id', metadata.get('cl_id')),
                    'cluster_id': metadata.get('cl_cluster_id', metadata.get('cluster_id')),
                    'docket_id': metadata.get('cl_docket_id'),
                },
                
                # Legal metadata
                'legal': {
                    'opinion_type': metadata.get('opinion_type', metadata.get('type')),
                    'citations': metadata.get('citations', []),
                    'parties': metadata.get('parties', []),
                },
                
                # Processing metadata
                'processing': {
                    'source': metadata.get('source'),
                    'status': metadata.get('processing_status', 'complete'),
                }
            }
            
            # Add content based on format preference
            if full_content:
                if content_format == 'text':
                    formatted_doc['content'] = {
                        'text': extract_plain_text(content) if content else "",
                        'length': len(content) if content else 0,
                        'format': 'text'
                    }
                elif content_format == 'both':
                    formatted_doc['content'] = {
                        'raw': content,
                        'text': extract_plain_text(content) if content else "",
                        'length': len(content) if content else 0,
                        'format': 'xml' if content and content.startswith('<') else 'text'
                    }
                else:  # raw
                    formatted_doc['content'] = {
                        'raw': content,
                        'length': len(content) if content else 0,
                        'format': 'xml' if content and content.startswith('<') else 'text'
                    }
            else:
                formatted_doc['content'] = {
                    'preview': content[:500] if content else None,
                    'length': len(content) if content else 0
                }
        
        formatted_docs.append(formatted_doc)
    
    # Output in requested format
    output = None
    
    # Determine if we should pretty print (for stdout by default, unless compact is specified)
    should_pretty = pretty or (not output_file and not compact)
    
    if output_format == 'json':
        if should_pretty:
            output = json.dumps(formatted_docs, indent=2, default=str)
        else:
            output = json.dumps(formatted_docs, default=str, separators=(',', ':'))
    elif output_format == 'jsonl':
        output = '\n'.join(json.dumps(doc, default=str, separators=(',', ':')) for doc in formatted_docs)
    elif output_format == 'csv':
        # CSV format with flattened structure
        output_buffer = []
        if formatted_docs:
            fieldnames = ['id', 'case_number', 'document_type', 'case_name', 'judge_name',
                         'court_id', 'date_filed', 'docket_number', 'content_length']
            if full_content:
                fieldnames.append('content')
            else:
                fieldnames.append('content_preview')
            
            import io
            string_buffer = io.StringIO()
            writer = csv.DictWriter(string_buffer, fieldnames=fieldnames)
            writer.writeheader()
            
            for doc in formatted_docs:
                row = {
                    'id': doc['id'],
                    'case_number': doc['case_number'],
                    'document_type': doc['document_type'],
                    'case_name': doc['metadata']['case_name'],
                    'judge_name': doc['metadata']['judge_name'],
                    'court_id': doc['metadata']['court_id'],
                    'date_filed': doc['metadata']['date_filed'],
                    'docket_number': doc['metadata']['docket_number'],
                    'content_length': doc['content_length']
                }
                if full_content:
                    row['content'] = doc.get('content', '')
                else:
                    row['content_preview'] = doc.get('content_preview', '')
                
                writer.writerow(row)
            
            output = string_buffer.getvalue()
    
    # Write output
    if output_file:
        with open(output_file, 'w') as f:
            f.write(output)
        console.print(f"[green]✅ Exported {len(formatted_docs)} documents to {output_file}[/green]")
    else:
        # When outputting to stdout, add clear headers for readability
        if not compact:
            console.print("\n" + "="*80)
            console.print(f"📄 COURT DOCUMENT EXPORT - {len(formatted_docs)} document(s)")
            console.print("="*80)
            
            # Show export parameters
            params_info = []
            if doc_type != 'all':
                params_info.append(f"Type: {doc_type}")
            if judge:
                params_info.append(f"Judge: {judge}")
            if court:
                params_info.append(f"Court: {court}")
            if after or before:
                date_range = f"{after or 'start'} to {before or 'end'}"
                params_info.append(f"Date range: {date_range}")
            if params_info:
                console.print(f"Filters: {', '.join(params_info)}")
            
            console.print(f"Format: {output_format.upper()}")
            console.print(f"Content: {'Full' if full_content else 'Preview'} ({content_format})")
            console.print("-"*80 + "\n")
        
        # Output the actual data
        print(output)
        
        # Add footer for readability when not compact
        if not compact:
            console.print("\n" + "-"*80)
            console.print(f"[dim]Export complete: {len(formatted_docs)} document(s)[/dim]")
            console.print("="*80)
    
    cur.close()
    conn.close()

@cli.group()
def search():
    """Search indexed court documents"""
    pass

@search.command()
@click.argument('query', required=False)
@click.option('--judge', help='Filter by judge name')
@click.option('--court', help='Filter by court ID')
@click.option('--after', help='Date after (YYYY-MM-DD)')
@click.option('--before', help='Date before (YYYY-MM-DD)')
@click.option('--type', 'doc_type', type=click.Choice(['opinion', 'docket', 'order']), help='Document type')
@click.option('--case-name', help='Search in case names')
@click.option('--docket', help='Search by docket number')
@click.option('--limit', default=20, help='Number of results')
@click.option('--show-content', is_flag=True, help='Show content preview')
@click.option('--export', type=click.Choice(['json', 'csv']), help='Export format')
def opinions(query, judge, court, after, before, doc_type, case_name, docket, limit, show_content, export):
    """Search through indexed opinions and documents
    
    Examples:
        court-processor search opinions "patent infringement"
        court-processor search opinions --judge Gilstrap --court txed
        court-processor search opinions --case-name "Apple v Samsung"
        court-processor search opinions --after 2020-01-01 --show-content
    """
    console.print("\n[bold blue]🔍 Searching Documents[/bold blue]\n")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Build search query
    conditions = []
    params = []
    
    if query:
        conditions.append("(content ILIKE %s OR metadata->>'case_name' ILIKE %s)")
        params.extend([f'%{query}%', f'%{query}%'])
    
    if judge:
        conditions.append("metadata->>'judge_name' ILIKE %s")
        params.append(f'%{judge}%')
    
    if court:
        conditions.append("metadata->>'court_id' = %s")
        params.append(court)
    
    if after:
        conditions.append("metadata->>'date_filed' >= %s")
        params.append(after)
    
    if before:
        conditions.append("metadata->>'date_filed' <= %s")
        params.append(before)
    
    if doc_type:
        conditions.append("document_type = %s")
        params.append(doc_type)
    
    if case_name:
        conditions.append("metadata->>'case_name' ILIKE %s")
        params.append(f'%{case_name}%')
    
    if docket:
        conditions.append("metadata->>'docket_number' ILIKE %s")
        params.append(f'%{docket}%')
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    search_query = f"""
        SELECT 
            id,
            case_number,
            document_type,
            metadata->>'case_name' as case_name,
            metadata->>'court_id' as court_id,
            metadata->>'judge_name' as judge_name,
            metadata->>'date_filed' as date_filed,
            metadata->>'docket_number' as docket_number,
            LENGTH(content) as content_length,
            SUBSTRING(content, 1, 500) as content_preview
        FROM public.court_documents
        WHERE {where_clause}
        ORDER BY 
            CASE 
                WHEN metadata->>'date_filed' IS NOT NULL AND metadata->>'date_filed' != ''
                THEN (metadata->>'date_filed')::date 
                ELSE created_at::date 
            END DESC
        LIMIT %s
    """
    params.append(limit)
    
    cur.execute(search_query, params)
    results = cur.fetchall()
    
    # Count total matches
    count_query = f"SELECT COUNT(*) FROM public.court_documents WHERE {where_clause}"
    cur.execute(count_query, params[:-1])  # Exclude limit
    total_matches = cur.fetchone()[0]
    
    if export == 'json':
        import json
        data = []
        for r in results:
            data.append({
                'id': r[0],
                'case_number': r[1],
                'type': r[2],
                'case_name': r[3],
                'court': r[4],
                'judge': r[5],
                'date_filed': r[6],
                'docket': r[7],
                'content_length': r[8],
                'preview': r[9][:200] if show_content and r[9] else None
            })
        print(json.dumps(data, indent=2))
    elif export == 'csv':
        print("id,case_number,type,case_name,court,judge,date_filed,docket,content_length")
        for r in results:
            print(f"{r[0]},{r[1]},{r[2]},{r[3]},{r[4]},{r[5]},{r[6]},{r[7]},{r[8]}")
    else:
        console.print(f"Found {total_matches} matching documents (showing {len(results)})\n")
        
        if results:
            for idx, r in enumerate(results, 1):
                console.print(f"[bold cyan]{'─' * 80}[/bold cyan]")
                console.print(f"[bold]Result {idx}[/bold] | ID: {r[0]} | Type: {r[2] or 'unknown'}")
                if r[3]:
                    console.print(f"[cyan]Case:[/cyan] {r[3]}")
                if r[5]:
                    console.print(f"[cyan]Judge:[/cyan] {r[5]}")
                if r[4]:
                    console.print(f"[cyan]Court:[/cyan] {r[4]}")
                if r[6]:
                    console.print(f"[cyan]Date:[/cyan] {r[6][:10]}")
                if r[7]:
                    console.print(f"[cyan]Docket:[/cyan] {r[7]}")
                console.print(f"[cyan]Content:[/cyan] {r[8]:,} chars")
                
                if show_content and r[9]:
                    preview = ' '.join(r[9].split())[:300]
                    console.print(f"\n[dim]{preview}...[/dim]")
                console.print()
            
            if total_matches > limit:
                console.print(f"[dim]Showing first {limit} results. Use --limit to see more.[/dim]")
        else:
            console.print("[yellow]No documents found matching search criteria[/yellow]")
    
    cur.close()
    conn.close()

@cli.group()
def pipeline():
    """Run document processing pipeline"""
    pass

@pipeline.command()
@click.option('--limit', default=10, help='Number of documents to process')
@click.option('--force', is_flag=True, help='Force reprocess even if unchanged')
@click.option('--unprocessed', is_flag=True, help='Only process new documents')
@click.option('--extract-pdfs', is_flag=True, help='Extract content from PDFs')
@click.option('--no-strict', is_flag=True, help='Process with warnings instead of skipping')
def run(limit, force, unprocessed, extract_pdfs, no_strict):
    """Run the 11-stage enhancement pipeline
    
    Example:
        court-processor pipeline run --limit 100 --unprocessed
    """
    console.print(f"\n[bold blue]⚙️  Running Enhancement Pipeline[/bold blue]\n")
    console.print(f"Options: limit={limit}, force={force}, unprocessed={unprocessed}, PDFs={extract_pdfs}, strict={not no_strict}")
    
    async def run_pipeline_async():
        pipeline = RobustElevenStagePipeline()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Processing documents...", total=limit)
            
            try:
                results = await pipeline.process_batch(
                    limit=limit,
                    validate_strict=not no_strict,
                    force_reprocess=force,
                    only_unprocessed=unprocessed,
                    extract_pdfs=extract_pdfs
                )
                
                if results['success']:
                    stats = results['statistics']
                    console.print(f"\n[green]✅ Pipeline Complete[/green]")
                    console.print(f"  Documents processed: {stats['documents_processed']}")
                    console.print(f"  Courts resolved: {stats['courts_resolved']}")
                    console.print(f"  Citations extracted: {stats['citations_extracted']}")
                    console.print(f"  Judges identified: {stats['judges_enhanced'] + stats['judges_extracted_from_content']}")
                    
                    # Show quality metrics
                    metrics = results.get('quality_metrics', {})
                    if metrics:
                        console.print(f"\n[cyan]Quality Metrics:[/cyan]")
                        console.print(f"  Completeness: {metrics.get('average_completeness', 0):.1f}%")
                        console.print(f"  Quality score: {metrics.get('average_quality', 0):.1f}%")
                else:
                    console.print(f"[red]Pipeline failed: {results.get('error', 'Unknown error')}[/red]")
                    
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
    
    asyncio.run(run_pipeline_async())

@cli.command()
def version():
    """Show version and system information"""
    console.print("\n[bold]Court Processor[/bold]")
    console.print("Version: 2.0.0 (Unified CLI)")
    console.print("Pipeline: 11-Stage Production")
    console.print("Focus: Judiciary Insights")
    console.print("\nFor help: court-processor --help")

if __name__ == '__main__':
    cli()