#!/usr/bin/env python3
"""
Check the structure and constraints of opinions_unified table
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://aletheia:aletheia123@db:5432/aletheia'

def check_opinions_unified():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=== OPINIONS_UNIFIED TABLE ANALYSIS ===\n")
    
    # 1. Check columns
    print("1. Table Structure:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'court_data' AND table_name = 'opinions_unified'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
        print(f"   - {col['column_name']}: {col['data_type']} {nullable}{default}")
    
    # 2. Check constraints
    print("\n2. Constraints:")
    cursor.execute("""
        SELECT conname, contype, pg_get_constraintdef(oid) as definition
        FROM pg_constraint
        WHERE conrelid = 'court_data.opinions_unified'::regclass
    """)
    constraints = cursor.fetchall()
    for const in constraints:
        const_type = {'p': 'PRIMARY KEY', 'u': 'UNIQUE', 'f': 'FOREIGN KEY', 'c': 'CHECK'}.get(const['contype'], const['contype'])
        print(f"   - {const['conname']} ({const_type}): {const['definition']}")
    
    # 3. Check existing cl_ids
    print("\n3. Sample of existing cl_ids:")
    cursor.execute("""
        SELECT cl_id, case_name, created_at
        FROM court_data.opinions_unified
        ORDER BY created_at DESC
        LIMIT 5
    """)
    rows = cursor.fetchall()
    for row in rows:
        print(f"   - cl_id: {row['cl_id']}, case: {row['case_name'][:50]}..., created: {row['created_at']}")
    
    # 4. Check if any cl_ids match our test data
    print("\n4. Checking for conflicts with test data:")
    cursor.execute("""
        SELECT cd.id, ou.cl_id, cd.case_number, ou.case_name
        FROM public.court_documents cd
        LEFT JOIN court_data.opinions_unified ou ON cd.id = ou.cl_id
        WHERE ou.cl_id IS NOT NULL
        LIMIT 5
    """)
    conflicts = cursor.fetchall()
    if conflicts:
        print("   Found conflicts:")
        for conf in conflicts:
            print(f"   - Document ID {conf['id']} already exists as cl_id {conf['cl_id']}")
    else:
        print("   No conflicts found")
    
    # 5. Proposed solutions
    print("\n5. Proposed Solutions:")
    print("   a) Use INSERT ... ON CONFLICT DO UPDATE")
    print("   b) Generate unique IDs instead of using source document IDs")
    print("   c) Add a source field and use composite unique constraint")
    print("   d) Check before inserting and skip duplicates")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    check_opinions_unified()