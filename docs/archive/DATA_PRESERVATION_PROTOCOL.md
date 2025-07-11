# Data Preservation Protocol for Aletheia v0.1

## Overview

This protocol ensures that critical data is never lost during container operations, migrations, or updates.

## Data Storage Architecture

### 1. **Persistent Data (Survives Container Removal)**

#### Docker Volumes
- **PostgreSQL Database** (`postgres_data` volume)
  - Court documents
  - Hierarchical summaries  
  - Lawyer-chat conversations
  - All application data
  
- **n8n Data** (`n8n_data` volume)
  - Workflows
  - Credentials
  - Execution history
  - Node configurations

- **Elasticsearch Data** (`elasticsearch_data` volume)
  - Search indices
  - Document embeddings

- **Haystack Models** (`haystack_models` volume)
  - AI model files

#### Local Directories (Bind Mounts)
- `./court-data/pdfs/` - Court PDF documents
- `./court-data/logs/` - Processing logs
- `./n8n/local-files/` - Files processed by n8n
- `./n8n/custom-nodes/` - Custom node code
- `./workflow_json/` - Exported workflow backups

### 2. **Ephemeral Data (Lost on Container Removal)**
- Container logs (unless redirected)
- Temporary files in container filesystems
- Unsaved workflow changes in n8n UI
- Active container state

## Critical Rules for Data Safety

### ✅ ALWAYS DO:

1. **Before ANY container removal:**
   ```bash
   # Check what data is in volumes
   docker volume ls | grep aletheia
   
   # Verify volume contents
   docker run --rm -v aletheia_postgres_data:/data alpine du -sh /data
   ```

2. **Export n8n workflows regularly:**
   ```bash
   # Manual export through n8n UI
   # Navigate to Workflows → Settings → Download
   # Save to ./workflow_json/
   ```

3. **Use the safe migration script:**
   ```bash
   ./scripts/safe-container-migration.sh
   ```

4. **Backup before major changes:**
   ```bash
   # Database backup
   docker exec aletheia-db-1 pg_dumpall -U your_db_user > backup_$(date +%Y%m%d).sql
   
   # n8n backup
   docker exec aletheia-n8n-1 tar czf - -C /home/node/.n8n . > n8n_backup_$(date +%Y%m%d).tar.gz
   ```

### ❌ NEVER DO:

1. **Never remove volumes without backup:**
   ```bash
   # DANGEROUS - This deletes all data!
   docker volume rm aletheia_postgres_data  # DON'T DO THIS
   ```

2. **Never use `docker system prune -a --volumes`** without careful consideration

3. **Never remove containers without checking volume mounts**

4. **Never trust container state for persistent data**

## Standard Operating Procedures

### 1. **Container Updates/Rebuilds**
```bash
# Safe procedure
docker-compose stop [service]
docker-compose up -d --build [service]
# Data in volumes is preserved
```

### 2. **Network Changes**
```bash
# Use the safe migration script
./scripts/safe-container-migration.sh
# Or manually:
docker-compose stop
# Make network changes
docker-compose up -d
```

### 3. **Full System Reset (Preserving Data)**
```bash
# Stop all containers
docker-compose down

# Start fresh (volumes persist)
docker-compose up -d
```

### 4. **Complete Clean Start (DANGER)**
```bash
# Only if you really want to delete everything
docker-compose down -v  # -v flag removes volumes!
```

## Backup Schedule Recommendations

### Daily
- Export active n8n workflows to `./workflow_json/`
- Verify court data directories

### Weekly  
- Full database backup
- n8n configuration backup
- Document count verification

### Before Major Changes
- Complete system backup using migration script
- Export all workflows
- Document current state

## Recovery Procedures

### Restore Database
```bash
# From backup file
docker exec -i aletheia-db-1 psql -U your_db_user < backup_20240101.sql
```

### Restore n8n
```bash
# Stop n8n
docker-compose stop n8n

# Restore backup
docker run --rm -v aletheia_n8n_data:/data -v $(pwd):/backup alpine \
  tar xzf /backup/n8n_backup_20240101.tar.gz -C /data

# Start n8n
docker-compose up -d n8n
```

### Restore Court Data
Court data is stored locally, so just ensure the directories exist:
```bash
ls -la ./court-data/pdfs/
ls -la ./court-data/logs/
```

## Volume Management Commands

### List all project volumes
```bash
docker volume ls | grep -E "(aletheia|data-compose|data_compose)"
```

### Inspect volume contents
```bash
# PostgreSQL data
docker run --rm -v aletheia_postgres_data:/data alpine ls -la /data

# n8n data  
docker run --rm -v aletheia_n8n_data:/data alpine ls -la /data
```

### Check volume sizes
```bash
docker system df -v | grep aletheia
```

### Copy volume data (for migration)
```bash
# Create new volume
docker volume create aletheia_postgres_data_backup

# Copy data
docker run --rm \
  -v aletheia_postgres_data:/source \
  -v aletheia_postgres_data_backup:/dest \
  alpine cp -av /source/. /dest/
```

## Emergency Contacts

If data loss occurs:
1. Check `./backups/` directory for automatic backups
2. Check Docker volumes (they may still exist)
3. Use `docker volume ls -a` to see all volumes
4. Contact team lead before any destructive operations

---

**Remember**: Containers are ephemeral, volumes are persistent. Always protect your volumes!