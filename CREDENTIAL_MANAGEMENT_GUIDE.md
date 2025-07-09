# Credential Management Guide for Aletheia v0.1

## Overview

This guide documents the comprehensive credential management system for Aletheia v0.1, with special focus on n8n integration and automated credential provisioning.

## Credential Types and Usage

### 1. System-Level Credentials (via .env)

These credentials are managed through environment variables and used by Docker services:

| Credential | Used By | Purpose |
|------------|---------|---------|
| `DB_USER/PASSWORD` | All services | PostgreSQL database access |
| `N8N_ENCRYPTION_KEY` | n8n | Encrypts stored credentials in n8n |
| `N8N_API_KEY/SECRET` | Frontend apps | Webhook authentication |
| `NEXTAUTH_SECRET` | lawyer-chat | Session encryption |
| `SMTP_*` | lawyer-chat | Email notifications |

### 2. n8n Internal Credentials

Stored encrypted within n8n's SQLite database:

| Credential Type | Used By Nodes | Current Status |
|-----------------|---------------|----------------|
| PostgreSQL | HierarchicalSummarization | Manual config supported |
| OpenAI API | AI nodes | User-configured |
| Anthropic API | AI nodes | User-configured |
| Custom APIs | Various | User-configured |

### 3. Service-Specific Credentials

| Service | Credential Location | Management |
|---------|-------------------|------------|
| Elasticsearch | No auth (internal) | Docker network security |
| Haystack | Uses system DB creds | Inherited from .env |
| BitNet | No auth required | Open endpoint |
| Court Processor | Uses system DB creds | Inherited from .env |

## Automated Credential Generation

### Quick Start

```bash
# Generate all credentials automatically
./scripts/generate-credentials.sh

# This creates:
# - Secure random passwords in .env
# - n8n credential templates
# - Workflow templates with credentials
```

### What Gets Generated

1. **Database Password**: 32-character alphanumeric + symbols
2. **n8n Encryption Key**: 64-character hex string
3. **API Keys**: Base64-encoded random strings
4. **NextAuth Secret**: 64-character base64 string

### Security Features

- Cryptographically secure random generation
- No predictable patterns
- Special character filtering for shell compatibility
- Automatic backup of existing credentials

## n8n Credential Integration

### Current Limitations

n8n does not yet provide an API for programmatic credential creation. We work around this with three approaches:

### Approach 1: Manual Configuration (Recommended)

The HierarchicalSummarization node supports manual database configuration:

```javascript
// In node configuration
{
  "databaseConfig": "manual",
  "dbHost": "db",
  "dbPort": 5432,
  "dbName": "aletheia_db",
  "dbUser": "aletheia_user",
  "dbPassword": "{{ $env.DB_PASSWORD }}"  // Can reference env vars
}
```

### Approach 2: Workflow Templates

Import pre-configured workflows:

```bash
# Workflow includes database configuration
workflow_json/hierarchical-summarization-template.json
```

### Approach 3: Manual UI Creation

1. Access n8n: http://localhost:5678
2. Navigate: Credentials → New → PostgreSQL
3. Enter values from your .env file

## Credential Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    .env     │────▶│   Docker    │────▶│  Services   │
│  (source)   │     │  Compose    │     │ (runtime)   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                                         │
       │                                         ▼
       │            ┌─────────────┐     ┌─────────────┐
       └───────────▶│     n8n     │────▶│    Nodes    │
                    │ (manual cfg)│     │ (execution) │
                    └─────────────┘     └─────────────┘
```

## Best Practices

### 1. Initial Setup

```bash
# Fresh installation
cp .env.example .env
./scripts/generate-credentials.sh
docker-compose up -d
```

### 2. Credential Rotation

```bash
# Backup current state
docker-compose exec db pg_dumpall -U $DB_USER > backup.sql
./scripts/generate-credentials.sh
docker-compose down && docker-compose up -d
```

### 3. Environment Separation

```
.env                # Development
.env.staging        # Staging environment
.env.production     # Production (never in git!)
```

### 4. n8n Workflow Portability

For sharing workflows without exposing credentials:

1. Use manual configuration in nodes
2. Reference environment variables where possible
3. Export workflows without credential data
4. Document required credentials in README

## Security Considerations

### DO ✅

1. **Use generated credentials**: Always use the script for production
2. **Rotate regularly**: Monthly for production, quarterly for dev
3. **Backup before rotation**: Always backup data and credentials
4. **Use manual config**: For n8n nodes when possible
5. **Document requirements**: List needed credentials in workflows

### DON'T ❌

1. **Never commit .env**: Only .env.example should be in git
2. **Don't share n8n exports**: They may contain credentials
3. **Avoid hardcoding**: Never put credentials in code
4. **Don't use weak passwords**: Always use the generator
5. **Never log credentials**: Check logs before sharing

## Troubleshooting

### Issue: n8n Can't Connect to Database

```bash
# Verify credentials match
grep DB_ .env
docker exec aletheia-n8n-1 ping db

# Test connection
docker exec aletheia-db-1 psql -U your_db_user -d your_db_name -c "SELECT 1"
```

### Issue: Lost n8n Encryption Key

**Prevention**: Always backup your .env file!

**Recovery**: 
1. Export workflows before changing encryption key
2. Reset n8n data volume (loses credential store)
3. Re-import workflows
4. Recreate credentials

### Issue: Credential Mismatch After Rotation

```bash
# Check which services are using old credentials
docker-compose ps
docker-compose logs [service-name]

# Force recreation
docker-compose up -d --force-recreate
```

## Future Enhancements

### Planned Improvements

1. **n8n API Integration**: When n8n adds credential API
2. **Vault Integration**: For enterprise deployments
3. **Automatic Rotation**: Scheduled credential updates
4. **Multi-Environment Sync**: Credential propagation tools

### Webhook Credential Management

Future enhancement for dynamic webhook credentials:

```javascript
// Proposed n8n credential provisioning
{
  "webhookCredentials": {
    "bearerToken": "{{ $env.N8N_API_KEY }}",
    "customHeader": "X-API-Secret",
    "customValue": "{{ $env.N8N_API_SECRET }}"
  }
}
```

## Quick Reference

### Generate New Project

```bash
git clone https://github.com/Code4me2/Aletheia-v0.1.git
cd Aletheia-v0.1
cp .env.example .env
./scripts/generate-credentials.sh
docker-compose up -d
```

### Add New Service

1. Add credentials to `.env.example`
2. Update `generate-credentials.sh`
3. Document in this guide
4. Update workflow templates

### Share with Team

1. Share `.env.example` (safe)
2. Team runs `generate-credentials.sh`
3. Each gets unique credentials
4. Same configuration structure

---

**Remember**: Credentials are the keys to your kingdom. Protect them accordingly!