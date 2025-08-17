# Stable Port Configuration - Aletheia v0.1

## Overview
This document describes the stable port configuration for the Aletheia platform, following Option A (Fixed Ports with Conflict Resolution) approach.

## Current Working Configuration

### Core Services
- **Main Web (nginx)**: Port 8080
  - Serves static website at `/`
  - Routes to all other services via proxy
- **Reverse Proxy Debug**: Port 8082 (development only)

### Application Services
- **n8n Workflow**: 
  - Direct: Port 8100 → 5678 (internal)
  - Via nginx: http://localhost:8080/n8n/
- **Lawyer Chat**: 
  - Internal: Port 3000
  - Via nginx: http://localhost:8080/chat
- **AI Portal**: 
  - Direct nginx: Port 8102
  - Via main nginx: http://localhost:8080/portal/

### Data Services
- **PostgreSQL**: Port 8200 → 5432 (internal)
- **Redis**: Port 8201 → 6379 (internal)

### Support Services
- **Recap Webhook**: Port 5001
- **Docker API**: Port 5002

## Access URLs

### Production URLs (via main nginx on port 8080)
```
http://localhost:8080/          # Main website
http://localhost:8080/n8n/      # n8n interface
http://localhost:8080/chat      # Lawyer chat application
http://localhost:8080/portal/   # AI portal (requires trailing slash)
http://localhost:8080/webhook/  # n8n webhooks
```

### Direct Service URLs
```
http://localhost:8100/          # n8n direct access
http://localhost:8102/          # AI portal direct access
```

## Key Configuration Files

### 1. `.env`
```env
# Core configuration
WEB_PORT=8080
WEB_HOST=0.0.0.0  # Changed from 127.0.0.1 to fix binding issues

# Application ports
N8N_PORT=8100
LAWYER_CHAT_PORT=8101
AI_PORTAL_PORT=8102

# Data services
POSTGRES_PORT=8200
REDIS_PORT=8201
```

### 2. `docker-compose.yml`
- Web service configured with ports `${WEB_HOST}:${WEB_PORT}:80`
- All services use environment variables for port configuration
- No hardcoded fallback values

### 3. `nginx/nginx.conf`
- Main routing configuration
- Upstream definitions for all services
- Proper WebSocket support for n8n
- Rate limiting zones for API and auth endpoints

## Known Issues & Solutions

### Issue 1: Port 8080 Binding
**Problem**: Docker couldn't bind to `127.0.0.1:8080`
**Solution**: Changed `WEB_HOST` from `127.0.0.1` to `0.0.0.0` in `.env`

### Issue 2: AI Portal Links
**Status**: Hardcoded URLs in Next.js build
**Impact**: Links use `http://localhost:8080` regardless of environment variables
**Workaround**: Accept as limitation of build-time configuration

### Issue 3: Portal Routing
**Note**: AI portal requires trailing slash when accessed via nginx
- Works: `http://localhost:8080/portal/`
- Fails: `http://localhost:8080/portal`

## Service Health Status

| Service | Status | Health Check |
|---------|--------|--------------|
| Web (nginx) | ✅ Running | Port 8080 accessible |
| n8n | ✅ Running | `/n8n/` responds |
| Lawyer Chat | ✅ Running | `/chat` responds |
| AI Portal | ✅ Running | Port 8102 accessible |
| PostgreSQL | ✅ Running | Port 8200 accessible |
| Redis | ✅ Running | Port 8201 accessible |

## Management Commands

### Start all services
```bash
docker compose up -d
```

### Check service status
```bash
docker compose ps
```

### View logs
```bash
docker compose logs -f [service-name]
```

### Restart a service
```bash
docker compose restart [service-name]
```

## Future Improvements

1. **Build-time Configuration**: Consider implementing build scripts that inject correct URLs during Next.js builds
2. **Service Discovery**: Implement proper service discovery for dynamic environments
3. **Health Monitoring**: Add comprehensive health check dashboard
4. **SSL/TLS**: Implement HTTPS for production deployment

## Summary

The current configuration provides a stable, working environment with:
- Fixed ports that avoid conflicts
- Centralized routing through nginx on port 8080
- All services accessible and functional
- Authentication flow working correctly
- No breaking changes to Next.js applications

This configuration is suitable for both development and can be adapted for production deployment.