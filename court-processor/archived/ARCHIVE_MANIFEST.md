# Archive Manifest

This directory contains components that are not currently in active use but are preserved for potential future implementation or reference.

## Archived Database Schemas

### database_schemas/

1. **init_courtlistener_schema.sql**
   - Purpose: CourtListener integration tables (cl_dockets, cl_opinions, cl_clusters)
   - Status: Empty tables, never populated
   - Potential use: Full CourtListener API integration

2. **add_recap_schema.sql**
   - Purpose: RECAP document and transcript support
   - Status: Tables created but unused
   - Potential use: PACER document integration, transcript processing

3. **add_flp_supplemental_tables.sql**
   - Purpose: Free Law Project enhancement tables
   - Status: Partially implemented
   - Potential use: Citation normalization, court standardization

4. **create_unified_opinions_table.sql**
   - Purpose: Attempt to unify all opinion sources
   - Status: Has 210 documents (partial migration)
   - Potential use: Future schema consolidation target

## Archived Services

### services/

1. **recap/**
   - authenticated_client.py - PACER authentication
   - recap_fetch_client.py - Document fetching from RECAP
   - recap_pdf_handler.py - PDF processing
   - webhook_handler.py - Webhook integration
   - Status: Not integrated with current pipeline

2. **flp_integration.py**
   - Free Law Project API integration
   - Judge photos, court standardization
   - Status: Not actively used

3. **recap_docket_service.py**
   - Docket-level document management
   - Status: Replaced by simplified approach

## Archived Scripts

### scripts/

1. **utilities/**
   - Various standalone scripts for data processing
   - Many duplicate functionality now in CLI
   - Includes specialized scrapers and processors

2. **data_import/**
   - Legacy data import scripts
   - Test data insertion utilities
   - Status: Functionality moved to CLI

## Why These Were Archived

1. **Schema Proliferation**: Multiple competing schemas created confusion
2. **Incomplete Integration**: Services were partially implemented
3. **Functionality Duplication**: CLI consolidated many script functions
4. **Simplified Architecture**: Current system uses single table approach

## Restoration Guide

If you need to restore any component:

1. **Database Schemas**: Run the SQL file against the database
2. **Services**: Copy back to services/ and update imports in pipeline.py
3. **Scripts**: Can be run standalone with proper DATABASE_URL

## Current Active System

The active system uses:
- Database: `public.court_documents` table only
- API: simplified_api.py on port 8104
- CLI: court_processor command
- Pipeline: pipeline.py for processing

See parent README.md for current documentation.