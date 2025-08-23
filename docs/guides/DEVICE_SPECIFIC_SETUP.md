# Aletheia-v0.1 Device-Specific Setup Guide

## Device Information
- **User**: manzanita
- **Home Directory**: `/home/manzanita`
- **Project Root**: `/home/manzanita/coding/data-compose`
- **Platform**: Linux (WSL2 - Windows Subsystem for Linux)
- **OS**: Linux 6.6.87.2-microsoft-standard-WSL2

## Project Overview

This is the **Aletheia-v0.1** unified platform that merges:
1. **data-compose**: Legal document processing and workflow automation
2. **temp_website** (now ai-portal): AI Portal for RJLF legal services

### Git Repository Structure

**Current Working Directory**: `/home/manzanita/coding/data-compose`

**Git Remotes**:
- `aletheia`: https://github.com/Code4me2/Aletheia-v0.1.git (PRIMARY - current upstream)
- `origin`: https://github.com/Code4me2/data-compose.git (original data-compose)
- `temp_website`: https://github.com/Code4me2/landing_page_RJLF.git (ai-portal source)

**Current Branch**: `main` (tracking `aletheia/main`)

## Directory Structure

```
/home/manzanita/coding/data-compose/
├── docker-compose.yml              # Main orchestration file (includes ai-portal services)
├── .env                           # Environment variables (NEVER commit this)
├── .env.example                   # Template for environment setup
├── CLAUDE.md                      # Project documentation for AI agents
├── README.md                      # Public project documentation
├── DEVICE_SPECIFIC_SETUP.md       # This file
├── nginx/                         # Main nginx configuration
│   └── conf.d/
│       └── default.conf
├── website/                       # Main web interface (SPA)
│   ├── index.html
│   ├── css/
│   │   └── app.css
│   └── js/
│       ├── app.js
│       └── config.js
├── services/
│   ├── lawyer-chat/              # Lawyer chat application (Next.js)
│   │   ├── Dockerfile
│   │   ├── src/
│   │   └── package.json
│   └── ai-portal/                # AI Portal (merged from temp_website)
│       ├── Dockerfile
│       ├── nginx.conf
│       ├── app/                  # Next.js app directory
│       └── package.json
├── n8n/                          # Workflow automation
│   ├── custom-nodes/             # Custom n8n nodes
│   │   ├── n8n-nodes-deepseek/
│   │   └── n8n-nodes-haystack/
│   └── docker-compose.haystack.yml
├── court-processor/              # PDF processing service
└── workflow_json/                # n8n workflow exports
```

## Service URLs and Ports

| Service | Internal Port | External Port | URL |
|---------|--------------|---------------|-----|
| web (nginx) | 80 | 8080 | http://localhost:8080 |
| n8n | 5678 | 5678 | http://localhost:5678 or http://localhost:8080/n8n/ |
| lawyer-chat | 3000 | 3001 | http://localhost:8080/chat |
| ai-portal | 3000 | - | Internal only |
| ai-portal-nginx | 80 | 8085 | http://localhost:8085 |
| db (PostgreSQL) | 5432 | - | Internal only |
| court-processor | - | - | Internal only |

## Essential Commands

### Starting the System
```bash
cd /home/manzanita/coding/data-compose
docker-compose up -d
```

### Stopping the System
```bash
docker-compose down
```

### Viewing Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ai-portal
docker-compose logs -f lawyer-chat
```

### Checking Service Status
```bash
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

## Environment Variables

The `.env` file contains sensitive configuration. Key variables:

```bash
# Database
DB_USER=your_db_user
DB_PASSWORD=your_secure_password_here  # This is the actual password, not a placeholder!
DB_NAME=your_db_name

# n8n
N8N_ENCRYPTION_KEY=your_secure_encryption_key_here  # Real key, not placeholder
N8N_API_KEY=...
N8N_API_SECRET=...

# NextAuth (for lawyer-chat)
NEXTAUTH_SECRET=...
NEXTAUTH_URL=http://localhost:8080/chat

# Email configuration (optional)
SMTP_HOST=...
SMTP_PORT=...
```

**IMPORTANT**: These "placeholder-looking" values are actually the working credentials for local development. They work as-is but should NEVER be used in production.

## Common Tasks for Contributing Agents

### 1. Making Changes to AI Portal
```bash
# Edit files in:
cd /home/manzanita/coding/data-compose/services/ai-portal/

# After changes, rebuild:
docker-compose build ai-portal
docker-compose up -d ai-portal ai-portal-nginx
```

### 2. Making Changes to Lawyer Chat
```bash
# Edit files in:
cd /home/manzanita/coding/data-compose/services/lawyer-chat/

# After changes, rebuild:
docker-compose build lawyer-chat
docker-compose up -d lawyer-chat
```

### 3. Updating Main Web Interface
```bash
# Edit files in:
cd /home/manzanita/coding/data-compose/website/

# Changes are served immediately by nginx (no rebuild needed)
```

### 4. Working with n8n Workflows
- Access n8n at: http://localhost:8080/n8n/
- Import workflows from: `/home/manzanita/coding/data-compose/workflow_json/`
- Custom nodes source: `/home/manzanita/coding/data-compose/n8n/custom-nodes/`

### 5. Git Operations
```bash
# Current setup pushes to Aletheia-v0.1
git push  # Goes to aletheia/main

# To push to original data-compose:
git push origin main

# To pull updates from ai-portal source:
git subtree pull --prefix=services/ai-portal temp_website main --squash
```

## Important Path Mappings

### Docker Volume Mounts
- `./website` → `/usr/share/nginx/html` (main web)
- `./services/ai-portal/nginx.conf` → `/etc/nginx/nginx.conf:ro` (ai-portal nginx)
- `./n8n/custom-nodes` → `/home/node/.n8n/custom` (n8n custom nodes)
- `./court-data/pdfs` → `/data/pdfs` (court processor)

### Network Names
- `data-compose_frontend` - For web-facing services
- `data-compose_backend` - For internal services

## Troubleshooting

### Port Already in Use
```bash
# Check what's using a port (e.g., 8085)
docker ps | grep 8085

# Stop old containers
docker stop <container-name>
docker rm <container-name>
```

### Service Won't Start
```bash
# Check logs
docker-compose logs <service-name>

# Rebuild if needed
docker-compose build --no-cache <service-name>
```

### Database Issues
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U your_db_user -d your_db_name

# List databases
docker-compose exec db psql -U your_db_user -c "\l"
```

### n8n Crash State
```bash
# If n8n keeps crashing, clear its data
docker-compose down
docker volume rm data-compose_n8n_data
docker-compose up -d
```

## Development Workflow

1. **Always check git status first**:
   ```bash
   git status
   git remote -v
   ```

2. **Test changes locally** before committing

3. **Use meaningful commit messages** with the format:
   ```
   Short description
   
   - Detailed change 1
   - Detailed change 2
   
   🤖 Generated with [Claude Code](https://claude.ai/code)
   
   Co-Authored-By: Claude <noreply@anthropic.com>
   ```

4. **Never modify `.env` file** unless adding new variables

5. **Always preserve existing functionality** when making changes

## Related Projects on This Device

### Other Projects in `/home/manzanita/coding/`:
- Original temp_website location: `/home/manzanita/coding/temp_website/` (can be removed if not needed)
- Other projects may exist in the coding directory

### WSL2 Specific Notes
- Host machine files accessible at: `/mnt/c/` (C: drive)
- Docker Desktop integration means containers can use `host.docker.internal`
- File permissions may differ from native Linux

## Quick Health Check Script

Create this as `/home/manzanita/coding/data-compose/health_check.sh`:

```bash
#!/bin/bash
echo "Checking Aletheia-v0.1 Services..."
echo "================================"

# Check each service
services=("http://localhost:8080:Main Web" "http://localhost:8085:AI Portal" "http://localhost:8080/chat:Lawyer Chat" "http://localhost:8080/n8n/healthz:n8n")

for service in "${services[@]}"; do
    IFS=':' read -r url port name <<< "$service"
    response=$(curl -s -o /dev/null -w "%{http_code}" "$url:$port")
    if [ "$response" = "200" ]; then
        echo "✓ $name ($url:$port) - OK"
    else
        echo "✗ $name ($url:$port) - Failed (HTTP $response)"
    fi
done

echo "================================"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(ai-portal|lawyer-chat|n8n|web|db|court)"
```

Make it executable: `chmod +x health_check.sh`

## For Future Agents

When you start working on this project:

1. **Read CLAUDE.md first** - It contains the full project history and architecture
2. **Check current git remote** - Ensure you're pushing to the right repository
3. **Verify services are running** - Use the health check script
4. **Respect existing patterns** - Follow the established coding style
5. **Test before committing** - Ensure nothing breaks
6. **Document significant changes** - Update this file if you change paths or add services

Remember: This is a unified platform serving a law firm's AI needs. Stability and security are paramount.