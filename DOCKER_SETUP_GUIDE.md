# Aletheia-v0 Docker Setup Guide

## Overview

Aletheia-v0 is a comprehensive AI-powered legal platform that combines document processing, workflow automation, and AI services. This guide provides detailed instructions for setting up the entire Docker-based infrastructure.

## System Requirements

### Minimum Requirements
- **RAM**: 4GB minimum (8GB recommended)
- **Storage**: 10GB free space
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Operating System**: Linux, macOS, or Windows with WSL2

### Required Ports
Ensure the following ports are available:
- `8080` - Main web interface (NGINX)
- `5678` - n8n workflow automation
- `3001` - Lawyer chat application
- `8085` - AI Portal
- `9200` - Elasticsearch (optional)
- `8000` - Haystack API (optional)
- `6379` - Redis cache

## Pre-Setup Checklist

- [ ] Docker and Docker Compose installed
- [ ] Required ports are free
- [ ] Git repository cloned locally
- [ ] Terminal access to project directory

## Step-by-Step Setup Instructions

### Step 1: Clone the Repository

```bash
git clone https://github.com/Code4me2/Aletheia-v0.1.git
cd Aletheia-v0.1
```

### Step 2: Environment Configuration

#### Option A: Automated Setup (Recommended)

```bash
# Make the script executable
chmod +x scripts/generate-credentials.sh

# Run the credential generator
./scripts/generate-credentials.sh
```

This script will:
- Create a `.env` file from `.env.example`
- Generate secure passwords and encryption keys
- Create n8n credential templates
- Backup existing `.env` if present

#### Option B: Manual Setup

```bash
# Copy the example environment file
cp .env.example .env

# Edit the file with your preferred editor
nano .env  # or vim, code, etc.
```

Key variables to configure:
```bash
# Database credentials
DB_USER=aletheia_user
DB_PASSWORD=your_secure_password_here  # Change this!
DB_NAME=aletheia_db

# n8n encryption key (32+ characters)
N8N_ENCRYPTION_KEY=your_32_char_hex_string_here  # Change this!

# NextAuth secret for lawyer-chat
NEXTAUTH_SECRET=your_64_char_string_here  # Change this!

# Optional: Email configuration
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@example.com
SMTP_PASS=your-email-password
```

### Step 3: Start Core Services

```bash
# Start all services in detached mode
docker-compose up -d

# View logs to monitor startup
docker-compose logs -f
```

Expected output:
```
✓ Network aletheia_frontend created
✓ Network aletheia_backend created
✓ Volume "aletheia_postgres_data" created
✓ Volume "aletheia_n8n_data" created
✓ Container aletheia-db-1 Started
✓ Container aletheia-redis-1 Started
✓ Container aletheia-n8n-1 Started
✓ Container aletheia-web-1 Started
✓ Container aletheia-court-processor-1 Started
✓ Container aletheia-lawyer-chat-1 Started
✓ Container aletheia-ai-portal-1 Started
✓ Container aletheia-ai-portal-nginx-1 Started
```

### Step 4: Verify Services

Check service status:
```bash
docker-compose ps
```

All services should show "Up" status with health checks passing.

### Step 5: Database Initialization

The PostgreSQL database automatically initializes with:
- Main database: `aletheia_db`
- Lawyer chat database: `lawyerchat`
- Required tables for hierarchical summarization
- Court document processing tables

Verify database setup:
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U ${DB_USER} -d ${DB_NAME} -c "\dt"
```

### Step 6: n8n Workflow Setup

1. Access n8n interface:
   - URL: `http://localhost:8080/n8n/`
   - First-time setup will prompt for email/password

2. Import basic workflow:
   - Click menu (☰) → Import from file
   - Select `workflow_json/web_UI_basic`
   - Activate the workflow

3. Verify custom nodes:
   - In node palette, search for:
     - "DeepSeek" - AI integration
     - "Hierarchical Summarization" - Document processing
     - "Haystack Search" - Document search (if enabled)

### Step 7: Optional - Enable Haystack/Elasticsearch

For advanced document search capabilities:

```bash
# Start additional services
docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d

# Or use the convenience script
cd n8n && ./start_haystack_services.sh
```

### Step 8: Access Points

Once all services are running:

| Service | URL | Purpose |
|---------|-----|---------|
| Main Web UI | http://localhost:8080 | Primary interface with AI Chat, Workflows |
| n8n Interface | http://localhost:8080/n8n/ | Workflow automation management |
| Lawyer Chat | http://localhost:8080/chat | Dedicated legal chat interface |
| AI Portal | http://localhost:8085 | AI services portal |
| Developer Dashboard | http://localhost:8080 (Developer tab) | System monitoring and testing |

### Step 9: Post-Setup Configuration

#### Configure AI Service (if using local Ollama)

1. Ensure Ollama is running on host machine
2. Verify DeepSeek model is installed:
   ```bash
   ollama list | grep deepseek
   ```

#### Import Additional Workflows

```bash
# List available workflows
ls workflow_json/

# Import via n8n UI as needed
```

#### Set External API Tokens

If using external services, add to `.env`:
- `COURTLISTENER_API_TOKEN` - For court document access
- Other service-specific tokens

## Troubleshooting

### Common Issues and Solutions

#### 1. Service Won't Start

Check logs:
```bash
docker-compose logs [service-name]
```

Common causes:
- Port already in use
- Missing environment variables
- Insufficient memory

#### 2. n8n Crash Loop

Clear n8n data and restart:
```bash
docker-compose down
docker volume rm aletheia_n8n_data
docker-compose up -d
```

#### 3. Database Connection Issues

Verify credentials:
```bash
docker-compose exec db psql -U ${DB_USER} -d ${DB_NAME}
```

#### 4. Cannot Access Web Interface

Check NGINX is running:
```bash
docker-compose logs web
curl http://localhost:8080
```

#### 5. Custom Nodes Not Appearing

Verify node mounting:
```bash
docker-compose exec n8n ls -la /home/node/.n8n/custom
```

## Health Check Script

Create `health_check.sh`:

```bash
#!/bin/bash
echo "Checking Aletheia Services..."
echo "=============================="

# Core services
services=(
    "http://localhost:8080|Main Web"
    "http://localhost:8080/n8n/healthz|n8n"
    "http://localhost:8080/chat|Lawyer Chat"
    "http://localhost:8085|AI Portal"
)

for service in "${services[@]}"; do
    IFS='|' read -r url name <<< "$service"
    if curl -s -f -o /dev/null "$url"; then
        echo "✓ $name - OK"
    else
        echo "✗ $name - Failed"
    fi
done

# Optional services
if curl -s -f -o /dev/null "http://localhost:9200"; then
    echo "✓ Elasticsearch - OK"
fi

if curl -s -f -o /dev/null "http://localhost:8000/health"; then
    echo "✓ Haystack API - OK"
fi

echo "=============================="
docker-compose ps --format "table {{.Name}}\t{{.Status}}"
```

## Maintenance Commands

### Stop All Services
```bash
docker-compose down
```

### Stop and Remove Volumes (CAUTION: Deletes data)
```bash
docker-compose down -v
```

### Update Services
```bash
docker-compose pull
docker-compose up -d
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f [service-name]

# Last 100 lines
docker-compose logs --tail=100 [service-name]
```

### Backup Database
```bash
docker-compose exec db pg_dump -U ${DB_USER} ${DB_NAME} > backup.sql
```

### Restore Database
```bash
docker-compose exec -T db psql -U ${DB_USER} ${DB_NAME} < backup.sql
```

## Security Considerations

1. **Environment File**
   - Never commit `.env` to version control
   - Use strong, unique passwords
   - Rotate credentials regularly

2. **Network Security**
   - Services communicate via internal Docker networks
   - Only necessary ports are exposed to host
   - Consider using reverse proxy for production

3. **Data Protection**
   - Database volumes persist data
   - Regular backups recommended
   - Encrypt sensitive data at rest

## Next Steps

1. **Test Core Functionality**
   - Send a test message in AI Chat
   - Create a simple n8n workflow
   - Access lawyer chat interface

2. **Configure Workflows**
   - Import and customize workflows
   - Set up webhook integrations
   - Configure AI model connections

3. **Explore Features**
   - Hierarchical Summarization
   - Document Processing
   - Developer Dashboard tools

## Support Resources

- Project Documentation: `CLAUDE.md`
- Device-Specific Setup: `DEVICE_SPECIFIC_SETUP.md`
- n8n Documentation: https://docs.n8n.io
- GitHub Issues: https://github.com/Code4me2/Aletheia-v0.1/issues

## Version Information

- Aletheia Version: v0.1
- Docker Compose Version: 3.8
- Last Updated: January 2025