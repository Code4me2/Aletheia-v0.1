# Docker Cleanup Plan

## Current Status
- Haystack and Elasticsearch are now running as part of the Aletheia compose project ✅
- Active n8n volume: `aletheia_n8n_data` (MUST PRESERVE)
- Active PostgreSQL volume: `aletheia_postgres_data` (MUST PRESERVE)

## Safe to Remove

### 1. Old Stopped Containers
```bash
# Remove old aletheia-v01 containers
docker rm aletheia-v01-court-processor-1
docker rm aletheia-v01-db-1
docker rm aletheia-v01-web-1
```

### 2. Old Images
```bash
# Remove aletheia-v01 images (old project version)
docker rmi aletheia-v01-ai-portal:latest
docker rmi aletheia-v01-court-processor:latest
docker rmi aletheia-v01-haystack-service:latest
docker rmi aletheia-v01-lawyer-chat:latest

# Note: Keep data_compose-haystack-service:latest for now as it's currently in use
```

### 3. Old Volumes (CAREFUL - verify these are not in use)
```bash
# Old project volumes (aletheia-v01 prefix)
docker volume rm aletheia-v01_elasticsearch_data
docker volume rm aletheia-v01_haystack_models
docker volume rm aletheia-v01_n8n_data
docker volume rm aletheia-v01_postgres_data

# Other old volumes
docker volume rm data_compose_n8n_data
docker volume rm n8n_elasticsearch_data
docker volume rm n8n_haystack_models
docker volume rm n8n_n8n_data
```

## Volumes to KEEP
- `aletheia_n8n_data` - Active n8n data ⚠️
- `aletheia_postgres_data` - Active database ⚠️
- `aletheia_elasticsearch_data` - Active Elasticsearch
- `aletheia_haystack_models` - Active Haystack models

## Recommended Cleanup Order

1. **First**: Remove stopped containers (safe)
2. **Second**: Remove old images (safe)
3. **Third**: Remove old volumes (verify each one carefully)

## One-liner for safe cleanup:
```bash
# Remove old containers
docker rm aletheia-v01-court-processor-1 aletheia-v01-db-1 aletheia-v01-web-1

# Remove old images
docker rmi aletheia-v01-ai-portal:latest aletheia-v01-court-processor:latest \
  aletheia-v01-haystack-service:latest aletheia-v01-lawyer-chat:latest

# List volumes before removing (safety check)
docker volume ls | grep -E "(aletheia-v01|data_compose|^n8n_)"
```

## Future: After Container Renaming
Once the container names are updated in docker-compose files:
- The `data_compose-haystack-service:latest` image can be rebuilt as `aletheia-haystack:latest`
- This will complete the migration from data-compose naming