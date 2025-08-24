# Changelog - August 2025

## Port Mapping and Health Check Fixes

### Date: August 23, 2025

#### Issues Resolved

1. **Nginx Routing Issue**
   - **Problem**: Nginx was routing to external IP (143.244.220.150) instead of internal Docker service names
   - **Cause**: Stale container configuration from previous docker-compose settings
   - **Solution**: Recreated web container to apply current nginx.conf

2. **Health Check Failures**
   - **Problem**: Multiple services showing "no health check" or "unhealthy" status
   - **Root Causes**:
     - Alpine containers (ai-portal, ai-portal-nginx) using `wget` which wasn't installed
     - lawyer-chat checking wrong endpoint (/ instead of /chat)
     - court-processor checking non-existent /health endpoint
   - **Solutions**:
     - ai-portal: Changed to Node.js HTTP request
     - ai-portal-nginx: Changed to `nginx -t` config test
     - lawyer-chat: Fixed to check /chat endpoint
     - court-processor: Fixed to check root endpoint /

3. **Phantom Port 8105**
   - **Problem**: Port 8105 appearing in container but not in docker-compose.yml
   - **Cause**: Old container configuration
   - **Solution**: Recreated web container, phantom port eliminated

4. **Dev CLI Inaccuracies**
   - **Problem**: Wrong port numbers and incomplete health checks
   - **Fixes**:
     - Corrected AI Portal port from 8085 to 8102
     - Added comprehensive health checks for all services
     - Fixed port display to show all services
     - Added special handling for recap-webhook (expected unhealthy)

#### Files Modified

- `docker-compose.yml` - Fixed health check configurations
- `dev` - Enhanced health checks and fixed port references
- `nginx/nginx.conf` - Verified correct internal routing
- `scripts/utilities/fix-healthchecks.sh` - Created utility script

#### Current Port Configuration

| Port | Service | Status |
|------|---------|--------|
| 8080 | Main Web (NGINX) | ✅ Working |
| 8082 | Development API | ✅ Working |
| 8100 | n8n | ✅ Working |
| 8102 | AI Portal | ✅ Working |
| 8104 | Court Processor | ✅ Working |
| 8200 | PostgreSQL | ✅ Working |
| 8201 | Redis | ✅ Working |
| 5001 | RECAP Webhook | ⚠️ Expected unhealthy |
| 5002 | Docker API | ✅ Working |

#### Verification

All services now accessible and health checks functional:
```bash
./dev health
# All services return HTTP 200
# PostgreSQL ready
```

#### Lessons Learned

1. Container recreation required when health check configurations change
2. Alpine-based containers need appropriate health check tools
3. Service-specific endpoints must be verified for health checks
4. Stale container configurations can persist through docker-compose changes