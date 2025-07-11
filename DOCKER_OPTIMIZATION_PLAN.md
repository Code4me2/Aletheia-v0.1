# Docker Organization Optimization Plan

## Current State Analysis

### Container Organization
- **9 containers** running across 2 networks (backend/frontend)
- **Inconsistent naming**: Mix of auto-generated and custom names
- **Duplicate volumes**: 11 volumes from different compose runs

### Issues Identified

1. **Naming Inconsistency**
   - `aletheia-web-1` vs `haystack-judicial` vs `ai-portal-nginx`
   - Auto-generated suffixes (-1) mixed with custom names

2. **Volume Duplication**
   - Multiple volume sets: `aletheia_*`, `aletheia-v01_*`, `data_compose_*`, `n8n_*`
   - Potentially wasting disk space and causing confusion

3. **Network Segmentation**
   - Proper separation (frontend/backend) but some services on both

## Recommended Improvements

### 1. Standardize Container Names
Add explicit `container_name` to all services in docker-compose files:

```yaml
services:
  web:
    container_name: aletheia-nginx-web
  db:
    container_name: aletheia-postgres
  n8n:
    container_name: aletheia-n8n
  court-processor:
    container_name: aletheia-court-processor
```

### 2. Clean Up Duplicate Volumes
```bash
# List unused volumes
docker volume ls -f dangling=true

# Remove specific old volumes (after backing up if needed)
docker volume rm aletheia-v01_elasticsearch_data aletheia-v01_haystack_models
docker volume rm data_compose_elasticsearch_data
```

### 3. Update Haystack Services
In `n8n/docker-compose.haystack.yml`:
```yaml
services:
  elasticsearch:
    container_name: aletheia-elasticsearch  # Remove 'judicial' suffix
  haystack-service:
    container_name: aletheia-haystack
```

### 4. Volume Naming Strategy
Ensure all volumes use consistent prefix:
```yaml
volumes:
  aletheia_postgres_data:
  aletheia_n8n_data:
  aletheia_elasticsearch_data:
  aletheia_haystack_models:
```

### 5. Add Docker Management Scripts

Create `scripts/docker-manage.sh`:
```bash
#!/bin/bash
case "$1" in
  "status")
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep aletheia
    ;;
  "clean-volumes")
    docker volume prune -f
    ;;
  "restart-all")
    docker-compose down
    docker-compose up -d
    ;;
esac
```

## Implementation Priority

1. **High Priority**: Clean up duplicate volumes (saves disk space)
2. **Medium Priority**: Standardize container names (improves management)
3. **Low Priority**: Create management scripts (convenience)

## Benefits

- **Easier Management**: Clear which containers belong to Aletheia
- **Reduced Confusion**: No duplicate volumes or ambiguous names
- **Better Organization**: Consistent naming makes scripting easier
- **Resource Efficiency**: Remove duplicate data volumes

## Migration Steps

1. **Backup Important Data**
   ```bash
   docker exec aletheia-db-1 pg_dumpall -U your_db_user > backup.sql
   ```

2. **Stop Services**
   ```bash
   docker-compose down
   ```

3. **Update docker-compose files** with new container names

4. **Clean old volumes** (after verifying backups)

5. **Restart with new configuration**
   ```bash
   docker-compose up -d
   ```