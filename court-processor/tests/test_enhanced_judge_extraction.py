#!/usr/bin/env python3
"""
Test enhanced judge extraction on real Delaware documents
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from enhanced_judge_extraction import EnhancedJudgeExtractor

def test_on_real_documents():
    """Test enhanced extraction on actual court documents"""
    
    # Check if running in Docker
    is_docker = os.path.exists('/.dockerenv') or os.getenv('DOCKER_CONTAINER', False)
    
    conn = psycopg2.connect(
        host='db' if is_docker else 'localhost',
        database='aletheia',
        user='aletheia',
        password='aletheia123',
        port=5432
    )
    
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Get documents that likely have judge signatures
        cur.execute('''
            SELECT 
                id,
                document_type,
                LENGTH(content) as content_length,
                content,
                metadata->>'case_name' as case_name,
                metadata->>'cl_id' as cl_id
            FROM public.court_documents
            WHERE LENGTH(content) > 10000  -- Substantial documents
            AND (document_type = 'opinion' OR document_type IS NULL)
            ORDER BY id DESC
            LIMIT 20
        ''')
        
        docs = cur.fetchall()
        
        print(f"Testing enhanced judge extraction on {len(docs)} documents")
        print("="*80)
        
        success_count = 0
        results_by_confidence = {'high': 0, 'medium': 0, 'low': 0}
        
        for doc in docs:
            print(f"\nDocument {doc['id']} (CL_ID: {doc['cl_id'] or 'N/A'}, Type: {doc['document_type'] or 'unknown'})")
            print(f"Case: {(doc['case_name'] or 'Unknown')[:60]}...")
            print(f"Length: {doc['content_length']:,} chars")
            
            # Extract judge using enhanced method
            result = EnhancedJudgeExtractor.extract_judge_from_content(
                doc['content'], 
                doc['document_type'] or 'unknown'
            )
            
            if result['found']:
                success_count += 1
                confidence = result['confidence']
                
                if confidence >= 80:
                    results_by_confidence['high'] += 1
                elif confidence >= 60:
                    results_by_confidence['medium'] += 1
                else:
                    results_by_confidence['low'] += 1
                
                print(f"✓ FOUND: {result['judge_name']} (confidence: {confidence:.1f}%)")
                print(f"  Pattern: {result['pattern']}")
                if result.get('fuzzy_matched'):
                    print(f"  Fuzzy matched from: '{result['extracted_text']}' (score: {result['fuzzy_score']:.2f})")
            else:
                print(f"✗ NOT FOUND: {result['reason']}")
                if result.get('candidates'):
                    print("  Candidates that failed validation:")
                    for name, pattern, conf in result['candidates']:
                        print(f"    - '{name}' from {pattern} (conf: {conf})")
        
        print("\n" + "="*80)
        print("SUMMARY")
        print("-"*40)
        print(f"Total documents tested: {len(docs)}")
        print(f"Successfully extracted: {success_count} ({success_count/len(docs)*100:.1f}%)")
        print(f"  High confidence (80%+): {results_by_confidence['high']}")
        print(f"  Medium confidence (60-79%): {results_by_confidence['medium']}")
        print(f"  Low confidence (<60%): {results_by_confidence['low']}")
        
        # Compare with current pipeline
        print("\n\nCOMPARING WITH ORIGINAL PATTERNS")
        print("-"*40)
        
        # Test a few documents with the worst OCR issues
        cur.execute('''
            SELECT 
                id,
                content
            FROM public.court_documents
            WHERE id IN (2159, 2157, 2161)  -- Known problematic documents
        ''')
        
        problem_docs = cur.fetchall()
        
        for doc in problem_docs:
            content_end = doc['content'][-500:] if doc['content'] else ''
            
            print(f"\nDoc {doc['id']} - Testing OCR problem handling:")
            
            # Show what's in the document
            import re
            judge_area = re.search(r'.{0,50}(?:JUDGE|Judge).{0,100}', content_end)
            if judge_area:
                print(f"Raw text: ...{judge_area.group()}...")
            
            # Test extraction
            result = EnhancedJudgeExtractor.extract_judge_from_content(doc['content'], 'opinion')
            if result['found']:
                print(f"✓ Enhanced extraction found: {result['judge_name']}")
            else:
                print(f"✗ Enhanced extraction failed: {result['reason']}")
    
    conn.close()

if __name__ == "__main__":
    test_on_real_documents()