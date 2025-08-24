# Port Configuration Guide

## Current Port Mappings

All services use the 8000+ range for external access to avoid conflicts with common development tools.

### Production Ports (External → Internal)

| Service | External Port | Internal Port | Description |
|---------|--------------|---------------|-------------|
| **Web/NGINX** | 8080 | 80 | Main application interface |
| **Dev API** | 8082 | 8082 | Development API endpoints |
| **n8n** | 8100 | 5678 | Workflow automation |
| **AI Portal** | 8102 | 80 | AI services (via nginx proxy) |
| **Court Processor** | 8104 | 8104 | Document processing API |
| **PostgreSQL** | 8200 | 5432 | Primary database |
| **Redis** | 8201 | 6379 | Cache and sessions |
| **RECAP Webhook** | 5001 | 5000 | Document webhook handler |
| **Docker API** | 5002 | 5000 | Docker control interface |

### Internal-Only Services

These services are not exposed externally:

| Service | Internal Port | Access Via |
|---------|--------------|------------|
| **lawyer-chat** | 3000 | NGINX proxy at /chat |
| **ai-portal** | 3000 | ai-portal-nginx proxy |

## Port Allocation Strategy

### Ranges
- **8000-8099**: Core web services
- **8100-8199**: Application services
- **8200-8299**: Data services
- **8300-8399**: Monitoring (reserved)
- **8400-8499**: AI services (reserved)
- **5000-5099**: Utility services

### Rules
1. External ports in 8000+ range (except utilities which use 5000+)
2. Internal ports use standard defaults where possible
3. Next.js apps run on internal port 3000
4. Databases use standard ports internally

## Environment Variables

Configure ports in `.env`:

```env
# Core Services
WEB_PORT=8080
REVERSE_PROXY_PORT=8082

# Application Services
N8N_PORT=8100
AI_PORTAL_PORT=8102
COURT_PROCESSOR_PORT=8104

# Data Services
POSTGRES_PORT=8200
REDIS_PORT=8201

# Utility Services
RECAP_WEBHOOK_PORT=5001
DOCKER_API_PORT=5002
```

## Adding New Services

When adding a new service:

1. **Determine category** (core/app/data/monitoring/ai/utility)
2. **Assign external port** from appropriate range
3. **Use standard internal port** where possible
4. **Update this document**
5. **Add to docker-compose.yml**
6. **Update README.md port section**

## Troubleshooting Port Conflicts

### Check what's using a port:
```bash
# macOS/Linux
lsof -i :8080

# Check all our ports
./dev ports
```

### Common conflicts:
- 8080: Often used by other web servers
- 5432: Default PostgreSQL (we use 8200 externally)
- 6379: Default Redis (we use 8201 externally)
- 3000: Common Next.js dev port (we proxy via NGINX)

### Resolution:
1. Stop conflicting service, or
2. Change port in `.env` file
3. Restart with `./dev restart`

## Security Considerations

- **Never expose internal ports directly** in production
- **Use NGINX proxy** for web services
- **Bind to localhost** in development when possible
- **Use Docker networks** for inter-service communication
- **Implement rate limiting** on exposed ports

## Future Standardization

Consider migrating to:
- Kubernetes with Service/Ingress model
- Service mesh for internal communication
- Dynamic port allocation with service discovery