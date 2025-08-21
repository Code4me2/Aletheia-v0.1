# Developer Onboarding Guide

Welcome to Aletheia! This guide will help you get started quickly and avoid common pitfalls.

## Quick Start Checklist

- [ ] Clone the repository
- [ ] Copy `.env.example` to `.env` 
- [ ] Run `docker-compose up -d`
- [ ] Wait for health checks (all services should show "healthy")
- [ ] Run validation: `./scripts/validate-setup.sh`
- [ ] If services were rebuilt, reload nginx: `./scripts/dev-helper.sh reload-nginx`
- [ ] Access the application at http://localhost:8080

## Common Issues & Solutions

### 1. 404 Error on /chat After Rebuild
**Symptom**: Getting "404 Not Found nginx/1.29.0" at localhost:8080/chat

**Solution**: 
```bash
./scripts/dev-helper.sh reload-nginx
# Or manually: docker exec aletheia_development-web-1 nginx -s reload
```
**Why**: Nginx caches upstream connections and needs a reload after services restart.

### 2. Port Conflicts
**Symptom**: "bind: address already in use" errors

**Solution**: Check which ports are in use:
```bash
# Check all required ports
for port in 8080 5678 8085 8104 9200 8000; do
  lsof -i :$port 2>/dev/null | grep LISTEN
done
```

**Required Ports**:
- 8080: Main web interface (nginx)
- 5678: n8n workflow automation
- 8085: AI Portal
- 8104: Court processor API (internal only)
- 9200: Elasticsearch (optional)
- 8000: Haystack service (optional)

### 3. Service Dependencies Not Met
**Symptom**: Services failing to start or connect

**Service Dependencies**:
```
nginx → lawyer-chat, n8n, ai-portal
lawyer-chat → court-processor, n8n (webhook)
court-processor → db (PostgreSQL)
n8n → db, redis
```

### 4. Environment Variables Not Taking Effect
**Symptom**: Features not working despite setting environment variables

**Important**: Some variables are needed at BUILD time for Next.js apps:
```bash
# For lawyer-chat document selection feature
docker-compose up -d --build lawyer-chat
```

Build-time variables:
- `NEXT_PUBLIC_ENABLE_DOCUMENT_SELECTION`
- `NEXT_PUBLIC_COURT_API_URL`

Runtime variables:
- Database credentials
- API keys
- Service URLs

## Project Structure

```
Aletheia-v0.1/
├── .env                    # Main environment configuration
├── docker-compose.yml      # Service definitions
├── nginx/nginx.conf        # Routing configuration
├── services/
│   ├── lawyer-chat/        # Legal chat application
│   └── ai-portal/          # AI services portal
├── court-processor/        # Document processing
├── n8n/                    # Workflow automation
└── website/                # Main web interface
```

## Key Commands

### Using the Helper Scripts
```bash
# Validate your setup
./scripts/validate-setup.sh

# Common operations
./scripts/dev-helper.sh status         # Show all service status
./scripts/dev-helper.sh reload-nginx   # Fix 404 errors after rebuild
./scripts/dev-helper.sh endpoints      # Test all service endpoints
./scripts/dev-helper.sh ports          # Check port usage
./scripts/dev-helper.sh logs [service] # View logs
./scripts/dev-helper.sh restart [service] # Restart a service
./scripts/dev-helper.sh backup-db      # Backup database
```

### Manual Commands (if needed)
```bash
# View logs
docker-compose logs -f [service-name]

# Restart service
docker-compose restart [service-name]

# Rebuild and restart
docker-compose up -d --build [service-name]

# Check health
docker ps --format "table {{.Names}}\t{{.Status}}"
```

## Development Workflow

### 1. Making Changes to Services

For Next.js services (lawyer-chat, ai-portal):
```bash
# Development mode (hot reload)
cd services/lawyer-chat
npm run dev

# Production build
docker-compose up -d --build lawyer-chat
docker exec aletheia_development-web-1 nginx -s reload  # Don't forget!
```

### 2. Database Access
```bash
# Connect to PostgreSQL
docker exec -it aletheia_development-db-1 psql -U aletheia_user -d aletheia_db

# Backup database
docker exec aletheia_development-db-1 pg_dump -U aletheia_user aletheia_db > backup.sql
```

### 3. Working with n8n Workflows
- Access at: http://localhost:8080/n8n/
- Workflows auto-import from `workflow_json/` on startup
- Custom nodes in `n8n/custom-nodes/`
- Webhook ID: `c188c31c-1c45-4118-9ece-5b6057ab5177`

## Environment Files Overview

The project uses multiple .env files - here's what each does:

| File | Purpose | Git Status |
|------|---------|------------|
| `.env` | Main configuration | Ignored |
| `.env.example` | Template with defaults | Tracked |
| `.env.development` | Development overrides | Ignored |
| `court-processor/.env` | Court processor config | Ignored |
| `services/lawyer-chat/.env.local` | Lawyer chat config | Ignored |

**Best Practice**: Only modify the root `.env` file. Service-specific .env files are generally not needed.

## Getting Help

1. Check this guide first
2. Review service logs: `docker-compose logs [service-name]`
3. Check service health: `docker ps`
4. Search existing issues in the repository
5. For nginx issues, always try reload first

## Security Notes

- Never commit `.env` files with real credentials
- Default passwords in `.env.example` MUST be changed for production
- Use strong, unique passwords for all services
- Enable authentication for n8n in production (`N8N_BASIC_AUTH_ACTIVE=true`)

## Next Steps

1. Import n8n workflows from `workflow_json/`
2. Test the chat interface at http://localhost:8080/chat
3. Explore the AI Portal at http://localhost:8085
4. Review service-specific READMEs for detailed configuration

---

*Last updated: August 2025*
*For updates, check the repository's documentation*