#!/usr/bin/env python3
"""
Analyze database schema to understand current state and requirements
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = 'postgresql://aletheia:aletheia123@db:5432/aletheia'

def analyze_schema():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("=== DATABASE SCHEMA ANALYSIS ===\n")
    
    # 1. Check what schemas exist
    print("1. Existing Schemas:")
    cursor.execute("""
        SELECT schema_name 
        FROM information_schema.schemata 
        WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        ORDER BY schema_name
    """)
    schemas = cursor.fetchall()
    for schema in schemas:
        print(f"   - {schema['schema_name']}")
    
    # 2. Check if court_data schema exists
    print("\n2. Looking for 'court_data' schema:")
    cursor.execute("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.schemata 
            WHERE schema_name = 'court_data'
        )
    """)
    court_data_exists = cursor.fetchone()['exists']
    print(f"   court_data schema exists: {court_data_exists}")
    
    # 3. Check tables in public schema
    print("\n3. Tables in 'public' schema:")
    cursor.execute("""
        SELECT t.table_name, 
               pg_size_pretty(pg_total_relation_size('public.'||t.table_name)) as size,
               s.n_live_tup as row_count
        FROM information_schema.tables t
        LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname AND s.schemaname = 'public'
        WHERE t.table_schema = 'public'
        ORDER BY t.table_name
    """)
    tables = cursor.fetchall()
    for table in tables:
        print(f"   - {table['table_name']} (size: {table['size']}, rows: {table['row_count'] or 0})")
    
    # 3.5 Check tables in court_data schema
    print("\n3.5. Tables in 'court_data' schema:")
    cursor.execute("""
        SELECT t.table_name, 
               pg_size_pretty(pg_total_relation_size('court_data.'||t.table_name)) as size,
               s.n_live_tup as row_count
        FROM information_schema.tables t
        LEFT JOIN pg_stat_user_tables s ON t.table_name = s.relname AND s.schemaname = 'court_data'
        WHERE t.table_schema = 'court_data'
        ORDER BY t.table_name
    """)
    tables = cursor.fetchall()
    if tables:
        for table in tables:
            print(f"   - {table['table_name']} (size: {table['size']}, rows: {table['row_count'] or 0})")
    else:
        print("   No tables found in court_data schema")
    
    # 4. Check if opinions_unified exists anywhere
    print("\n4. Searching for 'opinions_unified' table:")
    cursor.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name = 'opinions_unified'
    """)
    opinions_tables = cursor.fetchall()
    if opinions_tables:
        for table in opinions_tables:
            print(f"   Found in schema: {table['table_schema']}")
    else:
        print("   Not found in any schema")
    
    # 5. Analyze court_documents structure
    print("\n5. Structure of 'court_documents' table:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'court_documents'
        ORDER BY ordinal_position
    """)
    columns = cursor.fetchall()
    for col in columns:
        nullable = "NULL" if col['is_nullable'] == 'YES' else "NOT NULL"
        default = f" DEFAULT {col['column_default']}" if col['column_default'] else ""
        print(f"   - {col['column_name']}: {col['data_type']} {nullable}{default}")
    
    # 6. Check constraints on court_documents
    print("\n6. Constraints on 'court_documents':")
    cursor.execute("""
        SELECT conname, contype, pg_get_constraintdef(oid) as definition
        FROM pg_constraint
        WHERE conrelid = 'public.court_documents'::regclass
    """)
    constraints = cursor.fetchall()
    for const in constraints:
        const_type = {'p': 'PRIMARY KEY', 'u': 'UNIQUE', 'f': 'FOREIGN KEY', 'c': 'CHECK'}.get(const['contype'], const['contype'])
        print(f"   - {const['conname']} ({const_type}): {const['definition']}")
    
    # 7. Check what the pipeline is trying to do
    print("\n7. Pipeline expectations vs Reality:")
    print("   Pipeline expects: court_data.opinions_unified")
    print("   Reality: table doesn't exist")
    print("   Pipeline uses: doc.get('id') as cl_id")
    print("   Issue: Trying to insert into non-existent table")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_schema()