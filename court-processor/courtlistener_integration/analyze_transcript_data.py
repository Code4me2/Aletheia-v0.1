#!/usr/bin/env python3
"""
Analyze downloaded transcript opinions from the database
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json

DATABASE_URL = os.environ.get('DATABASE_URL')

def analyze_transcript_data():
    """Analyze the downloaded transcript opinion data"""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=== Transcript Opinion Analysis ===\n")
    
    # Overall statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_opinions,
            COUNT(CASE WHEN transcript_mentions > 0 THEN 1 END) as with_transcripts,
            SUM(transcript_mentions) as total_mentions,
            COUNT(CASE WHEN is_ip_case THEN 1 END) as ip_cases,
            COUNT(CASE WHEN has_deposition THEN 1 END) as with_depositions,
            COUNT(CASE WHEN has_trial_transcript THEN 1 END) as with_trial_transcripts,
            COUNT(CASE WHEN has_hearing_transcript THEN 1 END) as with_hearing_transcripts
        FROM court_data.transcript_opinions
    """)
    
    stats = cur.fetchone()
    print("Overall Statistics:")
    print(f"  Total opinions downloaded: {stats['total_opinions']}")
    print(f"  Opinions mentioning transcripts: {stats['with_transcripts']}")
    print(f"  Total transcript mentions: {stats['total_mentions']}")
    print(f"  IP-related cases: {stats['ip_cases']}")
    print(f"  With deposition transcripts: {stats['with_depositions']}")
    print(f"  With trial transcripts: {stats['with_trial_transcripts']}")
    print(f"  With hearing transcripts: {stats['with_hearing_transcripts']}")
    
    # By court
    print("\n\nBy Court:")
    cur.execute("""
        SELECT 
            court,
            court_name,
            COUNT(*) as total,
            COUNT(CASE WHEN transcript_mentions > 0 THEN 1 END) as with_transcripts,
            AVG(transcript_mentions) as avg_mentions
        FROM court_data.transcript_opinions
        GROUP BY court, court_name
        ORDER BY total DESC
    """)
    
    for row in cur.fetchall():
        print(f"\n  {row['court_name']} ({row['court']}):")
        print(f"    Total: {row['total']}")
        print(f"    With transcripts: {row['with_transcripts']}")
        print(f"    Avg mentions: {row['avg_mentions']:.1f}")
    
    # Top cases by transcript mentions
    print("\n\nTop Cases by Transcript Mentions:")
    cur.execute("""
        SELECT 
            case_name,
            court,
            date_filed,
            transcript_mentions,
            has_deposition,
            has_trial_transcript,
            has_hearing_transcript
        FROM court_data.transcript_opinions
        WHERE transcript_mentions > 0
        ORDER BY transcript_mentions DESC
        LIMIT 10
    """)
    
    for i, row in enumerate(cur.fetchall(), 1):
        print(f"\n  {i}. {row['case_name']}")
        print(f"     Court: {row['court']}, Filed: {row['date_filed']}")
        print(f"     Mentions: {row['transcript_mentions']}")
        types = []
        if row['has_deposition']: types.append('Deposition')
        if row['has_trial_transcript']: types.append('Trial')
        if row['has_hearing_transcript']: types.append('Hearing')
        if types:
            print(f"     Types: {', '.join(types)}")
    
    # Sample transcript quotes
    print("\n\nSample Transcript Quotes:")
    cur.execute("""
        SELECT 
            case_name,
            court,
            transcript_quotes
        FROM court_data.transcript_opinions
        WHERE jsonb_array_length(transcript_quotes) > 0
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        print(f"\n  Case: {row['case_name']} ({row['court']})")
        quotes = row['transcript_quotes']
        if quotes and len(quotes) > 0:
            for quote in quotes[:2]:  # Show first 2 quotes
                print(f"    - {quote.get('text', '')[:150]}...")
                print(f"      Type: {quote.get('type', 'unknown')}")
    
    # Recent IP cases with transcripts
    print("\n\nRecent IP Cases with Transcript References:")
    cur.execute("""
        SELECT 
            case_name,
            court,
            date_filed,
            transcript_mentions
        FROM court_data.transcript_opinions
        WHERE is_ip_case = true 
        AND transcript_mentions > 0
        ORDER BY date_filed DESC
        LIMIT 10
    """)
    
    for row in cur.fetchall():
        print(f"  - {row['case_name']} ({row['court']}, {row['date_filed']})")
        print(f"    Transcript mentions: {row['transcript_mentions']}")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    if not DATABASE_URL:
        print("Error: DATABASE_URL not set")
        exit(1)
    
    analyze_transcript_data()