#!/usr/bin/env python3
"""
Debug judge enhancement error
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import json

DATABASE_URL = 'postgresql://aletheia:aletheia123@db:5432/aletheia'

# Get a document that's causing issues
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor(cursor_factory=RealDictCursor)
cursor.execute('SELECT id, metadata FROM public.court_documents WHERE id = 2030')
row = cursor.fetchone()

if row:
    print(f"Document ID: {row['id']}")
    print(f"Metadata type: {type(row['metadata'])}")
    
    metadata = row['metadata']
    if isinstance(metadata, dict):
        print(f"Metadata keys: {list(metadata.keys())[:10]}...")
        
        # Check for judge-related fields
        judge_fields = ['judge', 'judge_name', 'assigned_to', 'author', 'author_id', 'author_str']
        for field in judge_fields:
            if field in metadata:
                value = metadata[field]
                print(f"{field}: {value} (type: {type(value)})")
        
        # Check author field more deeply
        if 'author' in metadata:
            author = metadata['author']
            print(f"\nAuthor field details:")
            print(f"  Type: {type(author)}")
            print(f"  Value: {author}")
            
            # If it's a URL or ID, that might be causing the integer issue
            if isinstance(author, str) and author.isdigit():
                print(f"  ⚠️  Author is a numeric string: {author}")
            elif isinstance(author, int):
                print(f"  ⚠️  Author is an integer: {author}")
                
        if 'author_id' in metadata:
            print(f"\nAuthor ID: {metadata['author_id']} (type: {type(metadata['author_id'])})")

cursor.close()
conn.close()