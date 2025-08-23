# Port Configuration Guide

## Service Ports (Defined in .env)

| Service | Port | Access URL |
|---------|------|------------|
| Web/Nginx | 8080 | http://localhost:8080 |
| n8n | 8100 | http://localhost:8100 or http://localhost:8080/n8n |
| PostgreSQL | 8200 | localhost:8200 |
| AI Portal | 8085 | http://localhost:8085 |
| Court Processor API | 8104 | http://localhost:8104 |
| Redis | 8201 | localhost:8201 |

## Important Notes

1. **No docker-compose.override.yml** - All ports controlled by .env
2. **Standard ports NOT used** - We use 8100 for n8n (not 5678), 8200 for PostgreSQL (not 5432)
3. **Access via nginx proxy** - Most services accessible through http://localhost:8080

## Testing Fresh Deployment

```bash
# Stop everything
docker-compose down

# Start fresh
docker-compose up -d

# Wait ~30 seconds for services to start

# Test endpoints
curl http://localhost:8080          # Main web
curl http://localhost:8100/healthz  # n8n direct
curl http://localhost:8080/n8n/     # n8n via proxy
curl http://localhost:8080/chat     # Lawyer chat
```

## Changing Ports

Edit `.env` file:
```env
WEB_PORT=8080      # Change to any port you want
N8N_PORT=8100      # Change to any port you want
POSTGRES_PORT=8200 # Change to any port you want
```

Then recreate services:
```bash
docker-compose down
docker-compose up -d
```