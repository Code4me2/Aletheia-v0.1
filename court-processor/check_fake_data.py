#!/usr/bin/env python3
"""Check for fake vs real data in the database"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json

conn = psycopg2.connect(
    host='db',
    database='aletheia',
    user='aletheia',
    password='aletheia123'
)

cursor = conn.cursor(cursor_factory=RealDictCursor)

# First, let's see the breakdown
cursor.execute("""
SELECT 
    metadata->>'source' as source,
    metadata->>'is_real_data' as is_real_flag,
    COUNT(*) as count
FROM court_documents
GROUP BY metadata->>'source', metadata->>'is_real_data'
ORDER BY source, is_real_flag
""")

print("=== Data Breakdown by Source and Real Flag ===")
for row in cursor.fetchall():
    source = row['source'] or 'None'
    real_flag = row['is_real_flag'] or 'None'
    print(f"Source: {source:<30} Real: {real_flag:<10} Count: {row['count']}")

# Check some documents without real data flag
print("\n=== Sample Documents WITHOUT is_real_data=true ===")
cursor.execute("""
SELECT 
    id,
    case_number,
    metadata->>'source' as source,
    metadata->>'is_real_data' as is_real,
    LEFT(content, 150) as content_preview
FROM court_documents 
WHERE metadata->>'is_real_data' IS NULL 
   OR metadata->>'is_real_data' = 'false'
   OR metadata->>'is_real_data' != 'true'
ORDER BY id
LIMIT 5
""")

for doc in cursor.fetchall():
    print(f"\nID: {doc['id']}")
    print(f"Case: {doc['case_number']}")
    print(f"Source: {doc['source']}")
    print(f"is_real_data: {doc['is_real']}")
    print(f"Content: {doc['content_preview'][:100]}...")

# Check some documents WITH real data flag
print("\n\n=== Sample Documents WITH is_real_data=true ===")
cursor.execute("""
SELECT 
    id,
    case_number,
    metadata->>'source' as source,
    metadata->>'case_name' as case_name,
    LEFT(content, 150) as content_preview
FROM court_documents 
WHERE metadata->>'is_real_data' = 'true'
ORDER BY id
LIMIT 5
""")

for doc in cursor.fetchall():
    print(f"\nID: {doc['id']}")
    print(f"Case: {doc['case_number']} - {doc['case_name']}")
    print(f"Source: {doc['source']}")
    print(f"Content: {doc['content_preview'][:100]}...")

# Let's check the metadata of one fake vs one real
print("\n\n=== Metadata Comparison ===")

# Get one without real flag
cursor.execute("""
SELECT metadata 
FROM court_documents 
WHERE metadata->>'is_real_data' IS NULL 
LIMIT 1
""")
fake_meta = cursor.fetchone()
if fake_meta:
    print("\nDocument without is_real_data flag:")
    print(json.dumps(fake_meta['metadata'], indent=2)[:500] + "...")

# Get one with real flag
cursor.execute("""
SELECT metadata 
FROM court_documents 
WHERE metadata->>'is_real_data' = 'true'
LIMIT 1
""")
real_meta = cursor.fetchone()
if real_meta:
    print("\nDocument with is_real_data=true:")
    print(json.dumps(real_meta['metadata'], indent=2)[:500] + "...")

cursor.close()
conn.close()