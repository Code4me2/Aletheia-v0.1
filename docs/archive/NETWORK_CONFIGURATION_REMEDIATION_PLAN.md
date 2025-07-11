# Aletheia v0.1 Network Configuration Remediation Plan

## Executive Summary

This document outlines a comprehensive plan to address critical networking, configuration, and credential management issues discovered in the Aletheia v0.1 project. The analysis revealed multiple network naming inconsistencies, credential management problems, and architectural issues that are causing service communication failures and pose security risks.

## Current State Analysis

### 1. Network Naming Chaos
The project currently has **four different network naming patterns** in use:
- `data-compose_frontend/backend` (hyphenated, hardcoded in main docker-compose.yml)
- `data_compose_frontend/backend` (underscored, expected by some services)
- `aletheia_frontend/backend` (would be created with COMPOSE_PROJECT_NAME=aletheia)
- `staging_frontend/backend`, `production_frontend/backend` (environment-specific)

**Impact**: Services cannot communicate reliably, requiring manual network connections.

### 2. Credential Management Issues

#### PostgreSQL Database Access
- **Current State**: 
  - Database name: `your_db_name`
  - Username: `your_db_user`
  - Password: `your_secure_password_here`
  - These "placeholder-looking" values are the actual working credentials

#### Service-Specific Database Requirements
- `lawyer-chat` expects database: `lawyerchat`
- `court-processor` uses main database
- `haystack-service` uses main database
- **No automatic database creation** for service-specific databases

#### n8n Credential Storage
- n8n stores its own credentials internally
- Custom nodes (HierarchicalSummarization) require PostgreSQL credentials configured in n8n UI
- No automated credential provisioning

### 3. Service Communication Matrix

| Service | Needs Access To | Current Network | Required Network |
|---------|----------------|-----------------|------------------|
| n8n | db, all services | frontend, backend | backend (for db), frontend (for UI) |
| web (nginx) | n8n, lawyer-chat | frontend, backend | frontend |
| db | - | backend | backend |
| court-processor | db | backend | backend |
| lawyer-chat | db, n8n | frontend, backend | both |
| elasticsearch | - | backend | backend |
| haystack-service | db, elasticsearch | backend | backend |
| ai-portal | - | frontend | frontend |
| ai-portal-nginx | ai-portal | frontend | frontend |

### 4. Security Vulnerabilities

1. **Hardcoded Credentials**: Environment variables with actual passwords
2. **Root Process Execution**: court-processor runs as root
3. **Unrestricted Network Access**: No network segmentation
4. **Missing Resource Limits**: Only production has memory/CPU limits
5. **Inconsistent Health Checks**: Mix of curl, wget, netstat

### 5. Port Conflicts

- Port 3001: Used by both `lawyer-chat` and `grafana` (production)
- No centralized port allocation strategy

## Remediation Plan

### Phase 1: Immediate Fixes (Critical Path)

#### 1.1 Standardize Network Names
```yaml
# Add to .env
COMPOSE_PROJECT_NAME=aletheia

# Update docker-compose.yml
networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
```

#### 1.2 Fix Service Network References
Update all docker-compose files that reference external networks:
- `n8n/docker-compose.haystack.yml`
- `n8n/custom-nodes/n8n-nodes-bitnet/docker-compose.yml`
- `website/docker-compose.yml`

Change from:
```yaml
networks:
  backend:
    external: true
    name: data_compose_backend
```

To:
```yaml
networks:
  backend:
    external: true
    name: aletheia_backend
```

#### 1.3 Database Initialization Script
Create proper `scripts/init-databases.sh`:
```bash
#!/bin/bash
set -e

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create service-specific databases
    CREATE DATABASE lawyerchat;
    GRANT ALL PRIVILEGES ON DATABASE lawyerchat TO $POSTGRES_USER;
    
    -- Create tables for hierarchical summarization
    CREATE TABLE IF NOT EXISTS hierarchical_summaries (
        id SERIAL PRIMARY KEY,
        workflow_id VARCHAR(255) NOT NULL,
        level INTEGER NOT NULL,
        content TEXT NOT NULL,
        metadata JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    
    -- Add indexes
    CREATE INDEX idx_workflow_id ON hierarchical_summaries(workflow_id);
    CREATE INDEX idx_level ON hierarchical_summaries(level);
EOSQL
```

### Phase 2: Configuration Management

#### 2.1 Environment File Structure
Create environment-specific files:
```
.env                    # Local development (gitignored)
.env.example            # Template with placeholders
.env.production         # Production values (gitignored)
.env.staging            # Staging values (gitignored)
```

#### 2.2 Credential Template (.env.example)
```bash
# Project Configuration
COMPOSE_PROJECT_NAME=aletheia

# Database Configuration
DB_USER=aletheia_user
DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
DB_NAME=aletheia_db

# n8n Configuration
N8N_ENCRYPTION_KEY=GENERATE_RANDOM_32_CHAR_STRING
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=CHANGE_ME_STRONG_PASSWORD

# Service Ports (to avoid conflicts)
WEB_PORT=8080
N8N_PORT=5678
LAWYER_CHAT_PORT=3001
AI_PORTAL_PORT=8085
ELASTICSEARCH_PORT=9200
HAYSTACK_PORT=8000
```

### Phase 3: Network Segmentation

#### 3.1 Three-Network Architecture
```yaml
networks:
  frontend:      # Public-facing services
    driver: bridge
  backend:       # Database and internal services
    driver: bridge
    internal: true  # No external access
  middleware:    # Services that bridge frontend/backend
    driver: bridge
```

#### 3.2 Service Network Assignments
- **Frontend only**: web, ai-portal-nginx
- **Backend only**: db, elasticsearch
- **Middleware + Backend**: n8n, lawyer-chat, court-processor, haystack-service
- **Frontend + Middleware**: ai-portal

### Phase 4: Security Hardening

#### 4.1 Non-Root Containers
Update all Dockerfiles:
```dockerfile
# Add non-root user
RUN addgroup -g 1001 -S appuser && adduser -u 1001 -S appuser -G appuser
USER appuser
```

#### 4.2 Read-Only Filesystems
```yaml
services:
  web:
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache/nginx
      - /var/run
```

#### 4.3 Resource Limits (All Environments)
```yaml
services:
  service_name:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Phase 5: Operational Improvements

#### 5.1 Health Check Standardization
Create health check script for each service type:
```bash
# scripts/health-checks/postgres.sh
#!/bin/bash
pg_isready -U $DB_USER -d $DB_NAME

# scripts/health-checks/web.sh
#!/bin/bash
curl -f http://localhost/health || exit 1
```

#### 5.2 Automated Credential Generation
```bash
#!/bin/bash
# scripts/generate-credentials.sh

# Generate secure passwords
DB_PASSWORD=$(openssl rand -base64 32)
N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
NEXTAUTH_SECRET=$(openssl rand -base64 32)

# Create .env from template
cp .env.example .env
sed -i "s/CHANGE_ME_STRONG_PASSWORD/$DB_PASSWORD/g" .env
sed -i "s/GENERATE_RANDOM_32_CHAR_STRING/$N8N_ENCRYPTION_KEY/g" .env
```

### Phase 6: Migration Strategy

#### 6.1 Migration Steps
1. **Backup Current State**
   ```bash
   docker-compose exec db pg_dumpall -U your_db_user > backup.sql
   docker cp aletheia-v01-n8n-1:/home/node/.n8n n8n_backup
   ```

2. **Stop All Services**
   ```bash
   docker-compose down
   ```

3. **Clean Up Networks**
   ```bash
   docker network prune -f
   ```

4. **Apply New Configuration**
   ```bash
   # Update .env with COMPOSE_PROJECT_NAME
   # Update docker-compose.yml files
   # Apply security updates
   ```

5. **Start Services with New Configuration**
   ```bash
   docker-compose up -d
   ```

6. **Verify Connectivity**
   ```bash
   # Test script to verify all services can communicate
   ./scripts/verify-connectivity.sh
   ```

### Phase 7: Documentation and Monitoring

#### 7.1 Network Architecture Diagram
Create visual documentation showing:
- Service placement on networks
- Communication flows
- Port mappings
- Credential flow

#### 7.2 Monitoring Setup
```yaml
# Add to docker-compose.production.yml
services:
  prometheus:
    image: prom/prometheus
    configs:
      - source: prometheus_config
        target: /etc/prometheus/prometheus.yml
    networks:
      - middleware
```

## Implementation Timeline

| Phase | Duration | Dependencies | Risk Level |
|-------|----------|--------------|------------|
| Phase 1 | 1 day | None | High (fixes critical issues) |
| Phase 2 | 2 days | Phase 1 | Medium |
| Phase 3 | 3 days | Phase 2 | Medium |
| Phase 4 | 1 week | Phase 3 | Low |
| Phase 5 | 3 days | Phase 2 | Low |
| Phase 6 | 1 day | All phases | High (migration) |
| Phase 7 | Ongoing | Phase 6 | Low |

## Risk Mitigation

1. **Data Loss**: Full backup before migration
2. **Service Downtime**: Implement in staging first
3. **Configuration Drift**: Use git for all configuration
4. **Credential Exposure**: Rotate all credentials post-migration

## Success Criteria

1. All services can communicate without manual network connections
2. No hardcoded credentials in configuration files
3. Consistent network naming across all environments
4. All services pass health checks
5. Security scan shows no critical vulnerabilities

## Post-Implementation Tasks

1. Update CI/CD pipelines with new configuration
2. Train team on new credential management
3. Schedule regular security audits
4. Document troubleshooting procedures
5. Create runbooks for common operations

---

This plan addresses all identified issues while maintaining service functionality and improving security posture. Implementation should proceed in phases to minimize risk and allow for rollback if needed.