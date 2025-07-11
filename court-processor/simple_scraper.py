#!/usr/bin/env python3
"""
Simple court scraper to get some test documents
Bypasses date format issues by using direct downloads
"""

import os
import sys
import requests
from pathlib import Path
import psycopg2
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample public court opinions (these are real public documents)
SAMPLE_OPINIONS = [
    {
        "court": "tax",
        "case_name": "Estate of Giustina v. Commissioner",
        "docket": "T.C. Memo. 2024-1",
        "url": "https://www.ustaxcourt.gov/sites/ustaxcourt.gov/files/opinions/Giustina.TC%20Memo.%202024-1.Jones.pdf",
        "judge": "Jones",
        "date": "2024-01-08"
    },
    {
        "court": "tax", 
        "case_name": "Coca-Cola Co. & Subs. v. Commissioner",
        "docket": "155 T.C. No. 10",
        "url": "https://www.ustaxcourt.gov/sites/ustaxcourt.gov/files/opinions/Coca-Cola.155%20T.C.%20No.%2010.Lauber.pdf",
        "judge": "Lauber",
        "date": "2020-11-18"
    }
]

def download_pdf(url, filepath):
    """Download PDF from URL"""
    try:
        logger.info(f"Downloading: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        logger.info(f"Saved to: {filepath}")
        return True
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return False

def extract_text_simple(pdf_path):
    """Simple text extraction - just return placeholder for now"""
    # For testing, we'll just create sample text
    # In production, this would use PyPDF2 or similar
    return f"""
    This is a sample court opinion text extracted from {pdf_path.name}.
    
    In a real implementation, this would contain the full text of the court opinion.
    For testing purposes, we're using placeholder text that includes relevant keywords
    like tax, commissioner, petitioner, respondent, and legal precedent.
    
    The court finds that the petitioner's arguments regarding tax liability are...
    """

def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not set")
        sys.exit(1)
    
    conn = psycopg2.connect(db_url)
    pdf_dir = Path('/data/pdfs/tax')
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    # Insert judges if not exist
    with conn.cursor() as cur:
        for opinion in SAMPLE_OPINIONS:
            cur.execute("""
                INSERT INTO court_data.judges (name, court) 
                VALUES (%s, %s) 
                ON CONFLICT (name) DO NOTHING
                RETURNING id
            """, (opinion['judge'], opinion['court']))
            
            result = cur.fetchone()
            if result:
                judge_id = result[0]
            else:
                cur.execute("SELECT id FROM court_data.judges WHERE name = %s", (opinion['judge'],))
                judge_id = cur.fetchone()[0]
            
            opinion['judge_id'] = judge_id
        conn.commit()
    
    # Process each opinion
    for opinion in SAMPLE_OPINIONS:
        pdf_filename = f"{opinion['docket'].replace(' ', '_')}.pdf"
        pdf_path = pdf_dir / pdf_filename
        
        # Download PDF (skip if exists)
        if not pdf_path.exists():
            if not download_pdf(opinion['url'], pdf_path):
                continue
        
        # Extract text
        text_content = extract_text_simple(pdf_path)
        
        # Insert into database
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO court_data.opinions (
                    court_code, case_name, docket_number, judge_id,
                    pdf_url, pdf_path, text_content, case_date, metadata
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
                ) ON CONFLICT (docket_number) DO UPDATE
                SET text_content = EXCLUDED.text_content,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                opinion['court'],
                opinion['case_name'],
                opinion['docket'],
                opinion['judge_id'],
                opinion['url'],
                str(pdf_path),
                text_content,
                opinion['date'],
                '{"source": "simple_scraper"}'
            ))
            
            opinion_id = cur.fetchone()[0]
            logger.info(f"Inserted opinion {opinion_id}: {opinion['case_name']}")
        
        conn.commit()
    
    conn.close()
    logger.info("Simple scraper completed")

if __name__ == "__main__":
    main()