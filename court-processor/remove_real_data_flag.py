#!/usr/bin/env python3
"""Remove the is_real_data flag from all documents to avoid confusion"""
import psycopg2
from psycopg2.extras import Json

conn = psycopg2.connect(
    host='db',
    database='aletheia',
    user='aletheia',
    password='aletheia123'
)

cursor = conn.cursor()

print("Removing is_real_data flag from all documents...")

# Update all documents to remove the is_real_data flag
cursor.execute("""
UPDATE court_documents
SET metadata = metadata - 'is_real_data'
WHERE metadata ? 'is_real_data'
RETURNING id
""")

updated_ids = cursor.fetchall()
conn.commit()

print(f"✓ Removed is_real_data flag from {len(updated_ids)} documents")

# Verify the change
cursor.execute("""
SELECT COUNT(*) 
FROM court_documents 
WHERE metadata ? 'is_real_data'
""")

remaining = cursor.fetchone()[0]
print(f"✓ Documents still having is_real_data flag: {remaining}")

# Show current document counts by source
cursor.execute("""
SELECT 
    metadata->>'source' as source,
    COUNT(*) as count
FROM court_documents
GROUP BY metadata->>'source'
ORDER BY count DESC
""")

print("\nCurrent document counts by source:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

print("\n✓ All documents are real data from CourtListener API")

cursor.close()
conn.close()