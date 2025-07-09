#!/bin/bash
set -e

echo "=== Aletheia v0.1 Credential Generator ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env already exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file already exists!${NC}"
    read -p "Do you want to backup the existing .env file? [Y/n]: " backup_choice
    
    if [[ "$backup_choice" != "n" ]] && [[ "$backup_choice" != "N" ]]; then
        timestamp=$(date +%Y%m%d_%H%M%S)
        cp .env ".env.backup_${timestamp}"
        echo -e "${GREEN}✓ Backed up to .env.backup_${timestamp}${NC}"
    fi
    
    read -p "Do you want to generate new credentials? This will overwrite existing ones. [y/N]: " overwrite_choice
    if [[ "$overwrite_choice" != "y" ]] && [[ "$overwrite_choice" != "Y" ]]; then
        echo "Aborted. No changes made."
        exit 0
    fi
fi

# Function to generate secure random strings
generate_password() {
    local length=${1:-32}
    # Use /dev/urandom for cryptographically secure randomness
    # Remove problematic characters that might cause issues in shell/docker
    LC_ALL=C tr -dc 'A-Za-z0-9!@#%^&*()_+=' < /dev/urandom | head -c "$length"
}

generate_hex() {
    local length=${1:-32}
    openssl rand -hex "$length"
}

generate_base64() {
    local length=${1:-32}
    openssl rand -base64 "$length" | tr -d '\n/'
}

# Copy template
cp .env.example .env
echo -e "${GREEN}✓ Created .env from template${NC}"

# Generate credentials
echo ""
echo "Generating secure credentials..."

# Database password
DB_PASSWORD=$(generate_password 32)
echo -e "${GREEN}✓ Generated database password (32 chars)${NC}"

# n8n encryption key (must be hex)
N8N_ENCRYPTION_KEY=$(generate_hex 32)
echo -e "${GREEN}✓ Generated n8n encryption key (64 hex chars)${NC}"

# n8n basic auth password
N8N_BASIC_AUTH_PASSWORD=$(generate_password 24)
echo -e "${GREEN}✓ Generated n8n basic auth password${NC}"

# n8n API credentials
N8N_API_KEY=$(generate_base64 24)
N8N_API_SECRET=$(generate_base64 32)
echo -e "${GREEN}✓ Generated n8n API credentials${NC}"

# NextAuth secret
NEXTAUTH_SECRET=$(generate_base64 64)
echo -e "${GREEN}✓ Generated NextAuth secret${NC}"

# Replace placeholders in .env
echo ""
echo "Updating .env file..."

# Use different delimiter for sed to avoid conflicts with special characters
sed -i.tmp "s|DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD_32_CHARS|DB_PASSWORD=${DB_PASSWORD}|g" .env
sed -i.tmp "s|N8N_ENCRYPTION_KEY=GENERATE_RANDOM_32_CHAR_HEX_STRING|N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}|g" .env
sed -i.tmp "s|N8N_BASIC_AUTH_PASSWORD=CHANGE_ME_STRONG_PASSWORD|N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}|g" .env
sed -i.tmp "s|N8N_API_KEY=GENERATE_RANDOM_API_KEY|N8N_API_KEY=${N8N_API_KEY}|g" .env
sed -i.tmp "s|N8N_API_SECRET=GENERATE_RANDOM_API_SECRET|N8N_API_SECRET=${N8N_API_SECRET}|g" .env
sed -i.tmp "s|NEXTAUTH_SECRET=GENERATE_RANDOM_64_CHAR_STRING|NEXTAUTH_SECRET=${NEXTAUTH_SECRET}|g" .env

# Clean up temp file
rm -f .env.tmp

echo -e "${GREEN}✓ Updated .env with generated credentials${NC}"

# Create n8n credential export file for PostgreSQL
echo ""
echo "Creating n8n credential configuration..."

mkdir -p n8n/credentials

# Create a JSON file with PostgreSQL credentials for n8n
cat > n8n/credentials/postgres-credentials.json <<EOF
{
  "name": "PostgreSQL - Aletheia",
  "type": "postgres",
  "data": {
    "host": "db",
    "port": 5432,
    "database": "aletheia_db",
    "user": "aletheia_user",
    "password": "${DB_PASSWORD}",
    "ssl": "disable"
  }
}
EOF

echo -e "${GREEN}✓ Created n8n PostgreSQL credential template${NC}"

# Create workflow template with credentials placeholder
cat > workflow_json/hierarchical-summarization-template.json <<EOF
{
  "name": "Hierarchical Summarization Template",
  "nodes": [
    {
      "parameters": {
        "operation": "processDocuments",
        "sourceType": "directory",
        "directoryPath": "/files/documents",
        "databaseConfig": "manual",
        "dbHost": "db",
        "dbPort": 5432,
        "dbName": "aletheia_db",
        "dbUser": "aletheia_user",
        "dbPassword": "${DB_PASSWORD}",
        "batchConfig": {
          "batchStrategy": "token",
          "tokenBatchSize": 2048
        }
      },
      "name": "Hierarchical Summarization",
      "type": "n8n-nodes-hierarchicalSummarization.hierarchicalSummarization",
      "position": [250, 300],
      "credentials": {
        "postgres": {
          "name": "PostgreSQL - Aletheia"
        }
      }
    }
  ],
  "connections": {},
  "settings": {
    "executionOrder": "v1"
  }
}
EOF

echo -e "${GREEN}✓ Created workflow template with database configuration${NC}"

# Create script to help with n8n credential import
cat > n8n/credentials/README.md <<'EOF'
# n8n Credential Setup

Since n8n doesn't have a direct API for credential import, you have two options:

## Option 1: Manual Configuration (Recommended)
The Hierarchical Summarization node supports manual database configuration:
1. In the node settings, set "Database Configuration" to "Manual"
2. The database credentials will be automatically filled from environment variables

## Option 2: Manual Credential Creation
1. Access n8n at http://localhost:5678
2. Go to Credentials → New → PostgreSQL
3. Use these values:
   - Name: PostgreSQL - Aletheia
   - Host: db
   - Database: aletheia_db
   - User: aletheia_user
   - Password: (check your .env file)
   - SSL: Disable

## Option 3: Use Workflow Template
Import the workflow template at `workflow_json/hierarchical-summarization-template.json`
which includes the database configuration.

## Future Automation
When n8n adds API support for credential management, we can automate this process.
EOF

echo -e "${GREEN}✓ Created credential setup documentation${NC}"

# Final summary
echo ""
echo "=== Setup Complete ==="
echo ""
echo -e "${GREEN}Generated credentials have been saved to .env${NC}"
echo ""
echo "Next steps:"
echo "1. Review the generated .env file"
echo "2. Start services: docker-compose up -d"
echo "3. For n8n PostgreSQL access:"
echo "   - Automatic: Use 'Manual' database config in Hierarchical Summarization node"
echo "   - Manual: Create credentials in n8n UI (see n8n/credentials/README.md)"
echo ""
echo -e "${YELLOW}Security Notes:${NC}"
echo "- Keep your .env file secure and never commit it to git"
echo "- The generated passwords are cryptographically secure"
echo "- Consider using a password manager for production deployments"
echo "- Rotate credentials regularly"
echo ""

# Check if services are running
if docker-compose ps 2>/dev/null | grep -q "Up"; then
    echo -e "${YELLOW}Warning: Services are currently running.${NC}"
    echo "You'll need to restart them for new credentials to take effect:"
    echo "  docker-compose down && docker-compose up -d"
fi