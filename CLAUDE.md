# Aletheia-v0.1 Project

**IMPORTANT**: For device-specific setup and paths, see [DEVICE_SPECIFIC_SETUP.md](./DEVICE_SPECIFIC_SETUP.md)

## Project Overview

Aletheia-v0.1 is a unified AI-powered platform that combines:
1. **Data Compose**: Web application integrating with n8n for workflow automation
2. **AI Portal**: Next.js application providing AI services for RJLF
3. **Lawyer Chat**: Full-featured chat application with legal AI capabilities
   - **NEW (Aug 2025)**: Document Context feature for court opinion selection
   - Modularized components for better maintainability
4. **Court Processor**: Automated court document processing system
   - Uses `simplified_api.py` for document access (port 8104)

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

## Recent Changes (August 2025)

### Lawyer Chat Document Context Feature (WORKING - August 2025)

#### How It Works:
1. **Document Selection**: Click "Document Context" button (top-right corner)
2. **Browse Cases**: Expand Gilstrap or Albright dropdowns to see available court opinions
3. **Select Documents**: Click on cases to select them (full text is fetched)
4. **Send Query**: Your message + selected document text is sent to n8n as a single message

#### Implementation Details:
- **DocumentCabinet** (`src/components/DocumentCabinet.tsx`): Sliding panel UI
  - Fetches documents from court-processor API on port 8104
  - Supports multiple document selection
  - Shows case numbers and preview text
- **Integration**: Document text is appended to user message before sending to n8n
  - Format: `[User Message]\n\n---LEGAL DOCUMENT CONTEXT---\n[Document Text]\n---END CONTEXT---`
  - This allows n8n workflows that expect a single message parameter to work

#### Build Requirements:
- Environment variables needed at BUILD TIME:
  - `NEXT_PUBLIC_ENABLE_DOCUMENT_SELECTION=true`
  - `NEXT_PUBLIC_COURT_API_URL=http://localhost:8104`
  - `COURT_API_BASE_URL=http://court-processor:8104`
- Port 8104 must be exposed in docker-compose.yml for browser access

### Court Processor Integration

#### API Access:
- **Internal (Docker)**: `http://court-processor:8104`
- **External (Host)**: `http://localhost:8104` (port exposed in docker-compose.yml)
- **API Type**: `simplified_api.py` (primary API for lawyer-chat integration)
- **Status**: ✅ Auto-starts with container

#### Recent Fixes Applied:
1. **Fixed DB Port Configuration**: 
   - Updated `simplified_api.py` to use correct default port (5432 instead of 8200)
   - Added smart detection for Docker environment (uses 'db' host in Docker, 'localhost' locally)
2. **Added Environment Variables to docker-compose.yml**:
   - DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD now properly configured
3. **Updated entrypoint.sh**:
   - Now automatically starts simplified_api on container startup
   - Logs available at `/data/logs/simplified-api.log`

#### API is now working correctly:
- Automatically starts when court-processor container starts
- Connects to PostgreSQL at `db:5432` 
- Returns actual court opinion documents with full text
- No manual intervention required

## Troubleshooting

1. **n8n not starting**: Check for crash state in volume, may need to recreate
2. **Port conflicts**: Ensure ports 8080, 5678, 8104, 8085 are free
3. **Database issues**: Verify PostgreSQL credentials in `.env`
4. **Custom nodes not appearing**: Restart n8n after adding nodes
5. **DocumentCabinet issues**: 
   - Ensure port 8104 is exposed in docker-compose.yml
   - Check if n8n workflow is active (webhook must be enabled)
   - Verify court-processor is running: `docker logs aletheia_development-court-processor-1`
6. **Message fails when documents selected**:
   - This is fixed - document text is now appended to message for n8n compatibility
   - Verify container is running: `docker ps | grep court-processor`

For detailed component documentation, see individual README files in each service directory.