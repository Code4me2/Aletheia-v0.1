# Container Naming Updates

## Proposed Simple Names

### Main docker-compose.yml:
- `web` → container_name: `website`
- `db` → container_name: `postgres`
- `n8n` → container_name: `n8n`
- `court-processor` → container_name: `court-processor`
- `lawyer-chat` → keep as `lawyer-chat` (already set)
- `ai-portal` → container_name: `ai-portal` (change from `ai-portal-app`)
- `ai-portal-nginx` → container_name: `ai-portal-nginx` (already set)

### n8n/docker-compose.haystack.yml:
- `elasticsearch` → container_name: `elasticsearch` (change from `elasticsearch-judicial`)
- `haystack-service` → container_name: `haystack` (change from `haystack-judicial`)

## Required Changes

### 1. Update docker-compose.yml:
```yaml
services:
  web:
    container_name: website
    # ... rest of config

  db:
    container_name: postgres
    # ... rest of config

  n8n:
    container_name: n8n
    # ... rest of config

  court-processor:
    container_name: court-processor
    # ... rest of config

  ai-portal:
    container_name: ai-portal  # Changed from ai-portal-app
    # ... rest of config
```

### 2. Update n8n/docker-compose.haystack.yml:
```yaml
services:
  elasticsearch:
    container_name: elasticsearch  # Changed from elasticsearch-judicial
    # ... rest of config

  haystack-service:
    container_name: haystack  # Changed from haystack-judicial
    # ... rest of config
```

### 3. Update references in other services:
- In haystack-service environment: `ELASTICSEARCH_HOST=http://elasticsearch:9200` (already correct)
- In court-processor environment: `postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}` (update from @db)
- In lawyer-chat environment: `postgresql://${DB_USER}:${DB_PASSWORD}@postgres:5432/lawyerchat` (update from @db)

## Notes:
- Container service names in compose files don't need to change
- Only the explicit `container_name` field is being added/updated
- This will make all containers appear with clean, simple names in Docker Desktop