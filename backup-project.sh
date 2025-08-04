#!/bin/bash

# Aletheia-v0 Complete Backup Script
# This script creates a complete backup of the Aletheia project including Docker volumes

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Create timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="backup_aletheia_v0_${TIMESTAMP}"

echo -e "${GREEN}=== Aletheia-v0 Complete Backup ===${NC}"
echo "Creating backup in: $BACKUP_DIR"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# 1. Backup all project files
echo -e "\n${YELLOW}1. Backing up project files...${NC}"
rsync -av --progress \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude 'backup_aletheia_v0_*' \
    --exclude '*.log' \
    --exclude '.next' \
    --exclude 'dist' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    ./ "$BACKUP_DIR/project_files/"

# 2. Save current Docker state
echo -e "\n${YELLOW}2. Saving Docker configuration...${NC}"
mkdir -p "$BACKUP_DIR/docker_state"

# Save running containers info
docker compose ps > "$BACKUP_DIR/docker_state/containers_status.txt"

# Save Docker compose configuration
cp docker-compose.yml "$BACKUP_DIR/docker_state/"
cp -r n8n/docker-compose.haystack.yml "$BACKUP_DIR/docker_state/" 2>/dev/null || true

# 3. Export Docker volumes
echo -e "\n${YELLOW}3. Exporting Docker volumes...${NC}"
mkdir -p "$BACKUP_DIR/docker_volumes"

# Function to export a volume
export_volume() {
    local volume_name=$1
    local backup_name=$2
    
    if docker volume inspect "$volume_name" >/dev/null 2>&1; then
        echo "Exporting $volume_name..."
        docker run --rm -v "$volume_name":/data -v "$(pwd)/$BACKUP_DIR/docker_volumes":/backup alpine \
            tar czf "/backup/${backup_name}.tar.gz" -C /data .
        echo -e "${GREEN}✓ Exported $volume_name${NC}"
    else
        echo -e "${RED}✗ Volume $volume_name not found${NC}"
    fi
}

# Export each volume
export_volume "aletheia_postgres_data" "postgres_data"
export_volume "aletheia_n8n_data" "n8n_data"
export_volume "aletheia_redis_data" "redis_data"

# 4. Export database dumps
echo -e "\n${YELLOW}4. Creating database dumps...${NC}"
mkdir -p "$BACKUP_DIR/database_dumps"

# Dump main database
docker compose exec -T db pg_dump -U aletheia_user aletheia_db > "$BACKUP_DIR/database_dumps/aletheia_db.sql" 2>/dev/null || echo "Warning: Could not dump aletheia_db"

# Dump lawyerchat database
docker compose exec -T db pg_dump -U aletheia_user lawyerchat > "$BACKUP_DIR/database_dumps/lawyerchat.sql" 2>/dev/null || echo "Warning: Could not dump lawyerchat"

# 5. Save environment configuration (without sensitive data)
echo -e "\n${YELLOW}5. Saving environment configuration...${NC}"
if [ -f .env ]; then
    # Create sanitized version of .env
    grep -E '^[A-Z_]+=' .env | sed 's/=.*/=***HIDDEN***/' > "$BACKUP_DIR/env_structure.txt"
    cp .env "$BACKUP_DIR/.env.backup"
    echo -e "${GREEN}✓ Environment configuration saved${NC}"
fi

# 6. Save git information
echo -e "\n${YELLOW}6. Saving git information...${NC}"
mkdir -p "$BACKUP_DIR/git_info"
git log --oneline -20 > "$BACKUP_DIR/git_info/recent_commits.txt" 2>/dev/null || true
git status > "$BACKUP_DIR/git_info/git_status.txt" 2>/dev/null || true
git remote -v > "$BACKUP_DIR/git_info/git_remotes.txt" 2>/dev/null || true

# 7. Create backup summary
echo -e "\n${YELLOW}7. Creating backup summary...${NC}"
cat > "$BACKUP_DIR/BACKUP_INFO.txt" << EOF
Aletheia-v0 Backup Information
==============================
Backup Date: $(date)
Backup Directory: $BACKUP_DIR

Contents:
---------
1. project_files/     - All project source files
2. docker_state/      - Docker configuration and status
3. docker_volumes/    - Exported Docker volumes (compressed)
4. database_dumps/    - PostgreSQL database dumps
5. .env.backup        - Environment configuration (contains secrets!)
6. git_info/          - Git repository information

Services Status at Backup:
--------------------------
$(docker compose ps)

To Restore:
-----------
1. Run the restore script: ./restore-project.sh $BACKUP_DIR
2. Or manually follow the instructions in RESTORE_INSTRUCTIONS.md

Important Notes:
----------------
- The .env.backup file contains sensitive credentials
- Docker volumes are compressed tar.gz files
- Database dumps are SQL files that can be restored with psql
EOF

# 8. Create restore script
echo -e "\n${YELLOW}8. Creating restore script...${NC}"
cat > "$BACKUP_DIR/restore-project.sh" << 'EOF'
#!/bin/bash

# Aletheia-v0 Restore Script
# Usage: ./restore-project.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}=== Aletheia-v0 Restore Script ===${NC}"
echo -e "${YELLOW}This will restore the project from this backup${NC}"
echo -e "${RED}WARNING: This will overwrite existing data!${NC}"
read -p "Continue? (y/N): " confirm

if [[ "$confirm" != "y" ]] && [[ "$confirm" != "Y" ]]; then
    echo "Restore cancelled."
    exit 0
fi

# Get the directory where this script is located
BACKUP_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR=$(dirname "$BACKUP_DIR")

echo -e "\n${YELLOW}1. Stopping existing services...${NC}"
cd "$PROJECT_DIR"
docker compose down || true

echo -e "\n${YELLOW}2. Restoring project files...${NC}"
rsync -av --delete \
    --exclude 'restore-project.sh' \
    --exclude 'BACKUP_INFO.txt' \
    "$BACKUP_DIR/project_files/" "$PROJECT_DIR/"

echo -e "\n${YELLOW}3. Restoring environment configuration...${NC}"
if [ -f "$BACKUP_DIR/.env.backup" ]; then
    cp "$BACKUP_DIR/.env.backup" "$PROJECT_DIR/.env"
    echo -e "${GREEN}✓ Environment configuration restored${NC}"
fi

echo -e "\n${YELLOW}4. Restoring Docker volumes...${NC}"

# Function to restore a volume
restore_volume() {
    local backup_file=$1
    local volume_name=$2
    
    if [ -f "$BACKUP_DIR/docker_volumes/${backup_file}.tar.gz" ]; then
        echo "Restoring $volume_name..."
        docker volume create "$volume_name" || true
        docker run --rm -v "$volume_name":/data -v "$BACKUP_DIR/docker_volumes":/backup alpine \
            sh -c "cd /data && tar xzf /backup/${backup_file}.tar.gz"
        echo -e "${GREEN}✓ Restored $volume_name${NC}"
    else
        echo -e "${RED}✗ Backup file ${backup_file}.tar.gz not found${NC}"
    fi
}

# Restore each volume
restore_volume "postgres_data" "aletheia_postgres_data"
restore_volume "n8n_data" "aletheia_n8n_data"
restore_volume "redis_data" "aletheia_redis_data"

echo -e "\n${YELLOW}5. Starting services...${NC}"
docker compose up -d

echo -e "\n${GREEN}=== Restore Complete ===${NC}"
echo "Services are starting. Check status with: docker compose ps"
echo "Logs available with: docker compose logs -f"
EOF

chmod +x "$BACKUP_DIR/restore-project.sh"

# 9. Compress the backup
echo -e "\n${YELLOW}9. Compressing backup...${NC}"
tar czf "${BACKUP_DIR}.tar.gz" "$BACKUP_DIR"

# Calculate sizes
BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)
COMPRESSED_SIZE=$(du -sh "${BACKUP_DIR}.tar.gz" | cut -f1)

echo -e "\n${GREEN}=== Backup Complete ===${NC}"
echo "Backup directory: $BACKUP_DIR ($BACKUP_SIZE)"
echo "Compressed archive: ${BACKUP_DIR}.tar.gz ($COMPRESSED_SIZE)"
echo ""
echo "To restore from this backup:"
echo "1. Extract: tar xzf ${BACKUP_DIR}.tar.gz"
echo "2. Run: ./${BACKUP_DIR}/restore-project.sh"
echo ""
echo -e "${YELLOW}Important: The backup contains sensitive data (.env file). Keep it secure!${NC}"