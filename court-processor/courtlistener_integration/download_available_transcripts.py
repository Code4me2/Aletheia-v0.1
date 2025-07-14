#!/usr/bin/env python3
"""
Download transcript data using available CourtListener endpoints
Works around RECAP permission limitations by using search and opinions
"""

import os
import json
import subprocess
import time
from datetime import datetime, timedelta

# Get API token from environment
API_TOKEN = os.environ.get('COURTLISTENER_API_TOKEN')
if not API_TOKEN:
    print("Error: COURTLISTENER_API_TOKEN not set")
    exit(1)

BASE_URL = "https://www.courtlistener.com/api/rest/v4"
OUTPUT_DIR = "../../data/courtlistener/transcripts"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Courts to search
COURTS = ['txed', 'cand', 'nysd']

def api_call(endpoint, params=None):
    """Make API call using curl and return JSON"""
    headers = [
        '-H', f'Authorization: Token {API_TOKEN}',
        '-H', 'User-Agent: Aletheia-v0.1/1.0'
    ]
    
    url = f"{BASE_URL}/{endpoint}"
    if params:
        param_str = '&'.join([f"{k}={v}" for k, v in params.items()])
        url += '?' + param_str
    
    cmd = ['curl', '-s'] + headers + [url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            print(f"Error parsing JSON from {endpoint}")
            return None
    else:
        print(f"Error calling {endpoint}: {result.stderr}")
        return None

def search_transcripts(court_id, days_back=90):
    """Search for transcript mentions in court documents"""
    print(f"\nSearching {court_id} for transcript references...")
    
    # Search queries to find transcripts
    transcript_queries = [
        "transcript",
        "deposition transcript",
        "hearing transcript", 
        "trial transcript",
        "oral argument transcript"
    ]
    
    all_results = []
    stats = {
        'total_found': 0,
        'with_text': 0,
        'opinions': 0,
        'transcript_types': {}
    }
    
    for query in transcript_queries:
        print(f"  Searching for: {query}")
        
        # Search in all available document types
        params = {
            'q': query,
            'court': court_id,
            'filed_after': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
            'page_size': 20,
            'order_by': 'dateFiled desc'
        }
        
        result = api_call('search/', params)
        
        if result and 'results' in result:
            count = result.get('count', 0)
            print(f"    Found {count} results")
            stats['total_found'] += count
            
            # Process results
            for item in result['results']:
                # Determine document type
                doc_type = item.get('type', 'unknown')
                
                # Create structured record
                record = {
                    'court_id': court_id,
                    'query': query,
                    'case_name': item.get('caseName', ''),
                    'date_filed': item.get('dateFiled', ''),
                    'type': doc_type,
                    'snippet': item.get('snippet', ''),
                    'absolute_url': item.get('absolute_url', ''),
                    'id': item.get('id', ''),
                    'docket_id': item.get('docketId'),
                    'has_text': bool(item.get('text'))
                }
                
                # Detect transcript type from snippet
                snippet_lower = record['snippet'].lower()
                if 'deposition' in snippet_lower:
                    record['transcript_type'] = 'deposition'
                elif 'hearing' in snippet_lower:
                    record['transcript_type'] = 'hearing'
                elif 'trial' in snippet_lower:
                    record['transcript_type'] = 'trial'
                elif 'oral argument' in snippet_lower:
                    record['transcript_type'] = 'oral_argument'
                else:
                    record['transcript_type'] = 'other'
                
                # Update stats
                if record['has_text']:
                    stats['with_text'] += 1
                if doc_type == 'o':  # Opinion
                    stats['opinions'] += 1
                
                t_type = record['transcript_type']
                stats['transcript_types'][t_type] = stats['transcript_types'].get(t_type, 0) + 1
                
                all_results.append(record)
        
        time.sleep(0.5)  # Rate limiting
    
    # Save results
    output_file = f"{OUTPUT_DIR}/{court_id}_transcript_search.json"
    with open(output_file, 'w') as f:
        json.dump({
            'court_id': court_id,
            'search_date': datetime.now().isoformat(),
            'days_searched': days_back,
            'stats': stats,
            'results': all_results
        }, f, indent=2)
    
    print(f"\n  Summary for {court_id}:")
    print(f"    Total transcript references: {stats['total_found']}")
    print(f"    Documents with text: {stats['with_text']}")
    print(f"    Opinions: {stats['opinions']}")
    print(f"    Transcript types found:")
    for t_type, count in stats['transcript_types'].items():
        print(f"      - {t_type}: {count}")
    
    return all_results

def download_opinion_texts(court_id, limit=50):
    """Download full text of opinions that mention transcripts"""
    print(f"\nDownloading opinion texts for {court_id}...")
    
    # Get recent opinions that might contain transcript text
    params = {
        'cluster__docket__court': court_id,
        'date_created__gte': (datetime.now() - timedelta(days=90)).isoformat(),
        'page_size': limit,
        'order_by': '-date_created'
    }
    
    result = api_call('opinions/', params)
    
    if result and 'results' in result:
        opinions_with_transcripts = []
        
        for opinion in result['results']:
            # Check if opinion text mentions transcript
            text = opinion.get('plain_text', '') or opinion.get('html', '')
            if text and 'transcript' in text.lower():
                # Extract transcript mentions
                transcript_data = {
                    'opinion_id': opinion['id'],
                    'date_created': opinion.get('date_created'),
                    'author': opinion.get('author_str'),
                    'type': opinion.get('type'),
                    'text_length': len(text),
                    'has_plain_text': bool(opinion.get('plain_text')),
                    'transcript_mentions': text.lower().count('transcript'),
                    'absolute_url': opinion.get('absolute_url')
                }
                
                # Save the full text
                text_file = f"{OUTPUT_DIR}/{court_id}_opinion_{opinion['id']}_text.txt"
                with open(text_file, 'w') as f:
                    f.write(f"Opinion ID: {opinion['id']}\n")
                    f.write(f"Date: {opinion.get('date_created')}\n")
                    f.write(f"Author: {opinion.get('author_str')}\n")
                    f.write(f"URL: {opinion.get('absolute_url')}\n")
                    f.write("=" * 80 + "\n\n")
                    f.write(text)
                
                opinions_with_transcripts.append(transcript_data)
                print(f"    Saved opinion {opinion['id']} ({transcript_data['transcript_mentions']} transcript mentions)")
        
        # Save metadata
        metadata_file = f"{OUTPUT_DIR}/{court_id}_opinions_with_transcripts.json"
        with open(metadata_file, 'w') as f:
            json.dump(opinions_with_transcripts, f, indent=2)
        
        print(f"  Found {len(opinions_with_transcripts)} opinions mentioning transcripts")
        
        return opinions_with_transcripts

def main():
    """Main download process"""
    print("=" * 60)
    print("CourtListener Transcript Data Download")
    print("Using available endpoints (search and opinions)")
    print("=" * 60)
    
    all_stats = {
        'start_time': datetime.now().isoformat(),
        'courts_processed': 0,
        'total_transcript_refs': 0,
        'total_opinions_saved': 0
    }
    
    for court in COURTS:
        print(f"\n{'=' * 40}")
        print(f"Processing {court}")
        print('=' * 40)
        
        # Search for transcript references
        search_results = search_transcripts(court, days_back=90)
        all_stats['total_transcript_refs'] += len(search_results)
        
        # Download opinion texts
        opinions = download_opinion_texts(court, limit=30)
        all_stats['total_opinions_saved'] += len(opinions)
        
        all_stats['courts_processed'] += 1
        
        # Rate limiting between courts
        time.sleep(2)
    
    # Save overall summary
    all_stats['end_time'] = datetime.now().isoformat()
    summary_file = f"{OUTPUT_DIR}/download_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(all_stats, f, indent=2)
    
    print("\n" + "=" * 60)
    print("Download Complete!")
    print("=" * 60)
    print(f"Courts processed: {all_stats['courts_processed']}")
    print(f"Transcript references found: {all_stats['total_transcript_refs']}")
    print(f"Opinion texts saved: {all_stats['total_opinions_saved']}")
    print(f"\nData saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("\nTo explore the data:")
    print(f"  ls -la {OUTPUT_DIR}")
    print(f"  cat {OUTPUT_DIR}/txed_transcript_search.json | python3 -m json.tool | less")

if __name__ == "__main__":
    main()