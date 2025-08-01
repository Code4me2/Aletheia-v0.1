# Aletheia-v0.1 Project

**IMPORTANT**: For device-specific setup and paths, see [DEVICE_SPECIFIC_SETUP.md](./DEVICE_SPECIFIC_SETUP.md)

## Project Overview

Aletheia-v0.1 is a unified AI-powered platform that combines:
1. **Data Compose**: Web application integrating with n8n for workflow automation
2. **AI Portal**: Next.js application providing AI services for RJLF
3. **Lawyer Chat**: Full-featured chat application with legal AI capabilities
4. **Court Processor**: Automated court document processing system

## Architecture

### Docker Services

```yaml
# Core Services
web:                # NGINX web server (port 8080)
db:                 # PostgreSQL database
n8n:                # Workflow automation (port 5678)
redis:              # Cache and session storage

# Application Services
lawyer-chat:        # Legal chat application (accessible at /chat via nginx)
ai-portal:          # AI services portal (internal)
ai-portal-nginx:    # AI portal proxy (port 8085)
court-processor:    # Court document processor

# Optional Services (via docker-compose.haystack.yml)
elasticsearch:      # Document search (port 9200)
haystack-service:   # RAG API service (port 8000)
```

### Directory Structure

```
Aletheia-v0.1/
├── docker-compose.yml         # Main Docker configuration
├── .env                       # Environment variables
├── nginx/                     # NGINX configuration
├── website/                   # Frontend SPA
│   ├── index.html            # Single entry point
│   ├── css/                  # Stylesheets
│   ├── js/                   # JavaScript modules
│   └── src/                  # TypeScript modules
├── services/                  # Microservices
│   ├── ai-portal/            # Next.js AI portal
│   └── lawyer-chat/          # Next.js chat app
├── n8n/                      # n8n configuration
│   ├── custom-nodes/         # Custom n8n nodes
│   │   ├── n8n-nodes-bitnet/
│   │   ├── n8n-nodes-citationchecker/
│   │   ├── n8n-nodes-deepseek/
│   │   ├── n8n-nodes-haystack/
│   │   ├── n8n-nodes-hierarchicalSummarization/
│   │   └── n8n-nodes-yake/
│   └── haystack-service/     # Haystack RAG service
├── court-processor/          # Court data processing
├── scripts/                  # Deployment scripts
└── docs/                     # Documentation
```

## Configuration

### Environment Variables

Create `.env` file from template:
```bash
cp .env.example .env
```

Key variables:
```
# Database
DB_USER=your_db_user
DB_PASSWORD=your_secure_password_here
DB_NAME=your_db_name

# n8n
N8N_ENCRYPTION_KEY=your_secure_encryption_key_here
N8N_PORT=5678

# Services
# LAWYER_CHAT_PORT is no longer needed - lawyer-chat is served at /chat via nginx
AI_PORTAL_PORT=8085
HAYSTACK_PORT=8000
ELASTICSEARCH_PORT=9200

# Authentication
NEXTAUTH_SECRET=your_nextauth_secret
```

### Service URLs

- **Main Application**: http://localhost:8080
- **n8n Interface**: http://localhost:8080/n8n/
- **AI Portal**: http://localhost:8085
- **Lawyer Chat**: http://localhost:8080/chat (served via nginx proxy)
- **Haystack API**: http://localhost:8000/docs

## Quick Start

1. **Start all services**:
   ```bash
   docker-compose up -d
   ```

2. **With Haystack/Elasticsearch**:
   ```bash
   docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d
   ```

3. **Import n8n workflow**:
   - Access n8n at http://localhost:8080/n8n/
   - Import workflow from `workflow_json/web_UI_basic`
   - Activate the workflow

## Key Features

### Web Frontend (SPA)
- **AI Chat**: DeepSeek R1 integration with citation support
- **Hierarchical Summarization**: Document processing with visualization
- **Developer Dashboard**: System monitoring and administration
- **Dark Mode**: Persistent theme support
- **Keyboard Shortcuts**: Press `?` for help

### Citation System
- Inline citation formats: `<cite id="X">text</cite>` and `[X]`
- Claude-style citation panel with bidirectional navigation
- Automatic citation extraction from AI responses

### n8n Custom Nodes
All nodes are pre-built and ready to use:
- **DeepSeek**: AI text generation via Ollama
- **Haystack**: Document search (3 operations)
- **CitationChecker**: Legal citation verification
- **HierarchicalSummarization**: Document hierarchy processing
- **BitNet**: BitNet AI integration
- **YAKE**: Keyword extraction

**Note**: Node `node_modules` directories are not required for runtime and can be removed to save ~675MB.

### Haystack Integration
- **7 API endpoints** for document management and search
- **Direct Elasticsearch integration** (not full Haystack library)
- **Hybrid search**: BM25 + Vector search capabilities
- Works alongside HierarchicalSummarization, not as replacement

## Development

### Frontend Development
```bash
cd website
# TypeScript compilation available in src/
```

### Custom Node Development
```bash
cd n8n/custom-nodes/n8n-nodes-[name]
npm install      # Only if modifying TypeScript
npm run build    # Recompile to dist/
```

### Service Development
- **AI Portal**: `cd services/ai-portal && npm run dev`
- **Lawyer Chat**: `cd services/lawyer-chat && npm run dev`

## Important Notes

1. **Webhook Configuration**: 
   - ID: `c188c31c-1c45-4118-9ece-5b6057ab5177`
   - Used by frontend chat and lawyer-chat

2. **CSRF Protection**: 
   - Lawyer-chat implements CSRF tokens
   - Required for all state-changing requests

3. **Health Checks**: 
   - All services include Docker health checks
   - Monitor via Developer Dashboard

4. **Git Configuration**:
   - `.env` is gitignored for security
   - Use `.env.example` as template

## Common Operations

### View Logs
```bash
docker-compose logs -f [service-name]
```

### Restart Service
```bash
docker-compose restart [service-name]
```

### Update and Rebuild
```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Troubleshooting

1. **n8n not starting**: Check for crash state in volume, may need to recreate
2. **Port conflicts**: Ensure ports 8080, 5678, 3001, 8085, 9200, 8000 are free
3. **Database issues**: Verify PostgreSQL credentials in `.env`
4. **Custom nodes not appearing**: Restart n8n after adding nodes

For detailed component documentation, see individual README files in each service directory.