# Aletheia

AI-powered legal document processing platform with n8n workflow automation.

## Prerequisites

Before you begin, ensure you have:

1. **Docker Desktop** installed and running:
   - [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
   - After installation, make sure Docker is running (icon in system tray/menu bar)
   - Verify with: `docker --version` and `docker-compose --version`

2. **System Requirements**:
   - 8GB RAM minimum (16GB recommended)
   - 10GB free disk space
   - macOS, Linux, or Windows with WSL2

3. **Required Ports Available**:
   - 8080 (Main web interface)
   - 8100 (n8n workflow automation)
   - 8102 (AI Portal)
   - 8104 (Court Processor)
   - 8200 (PostgreSQL)
   - 8201 (Redis)

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Code4me2/Aletheia-v0.1.git
cd Aletheia-v0.1

# 2. Setup (first time only)
./dev setup

# 3. Start services
./dev up

# 4. Access services
# Main app:          http://localhost:8080
# n8n:               http://localhost:8100
# Lawyer Chat:       http://localhost:8080/chat
# AI Portal:         http://localhost:8102
# Court Processor:   http://localhost:8104
# Development API:   http://localhost:8082/status
```

## Project Overview

Aletheia is a unified AI-powered platform that combines:
1. **Data Compose**: Web application integrating with n8n for workflow automation
2. **AI Portal**: Next.js application providing AI services for RJLF
3. **Lawyer Chat**: Full-featured chat application with legal AI capabilities
   - Document Context feature for court opinion selection
   - Modularized components for better maintainability
4. **Court Processor**: Automated court document processing system
   - Uses `simplified_api.py` for document access (port 8104)

## Commands

**Use the `./dev` CLI for ALL operations.** Run `./dev help` for all available commands.

### Common Commands

#### Service Management
```bash
./dev up                # Start all services
./dev down              # Stop all services
./dev restart           # Restart all services
./dev status            # Check service status
./dev health            # Check health endpoints
./dev logs [service]    # View logs
```

#### Development
```bash
./dev test              # Run tests
./dev lint              # Run linting
./dev build             # Build services
```

#### Database
```bash
./dev db backup         # Backup database
./dev db restore        # Restore database
./dev db shell          # Database shell
./dev db schema         # View database schema
```

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
ai-portal-nginx:    # AI portal proxy (port 8102)
court-processor:    # Court document processor

# Support Services
docker-api:         # Docker control API (port 5002)
recap-webhook:      # RECAP document webhook handler (port 5001)

# Optional Services (via docker-compose.haystack.yml)
elasticsearch:      # Document search (port 9200)
haystack-service:   # RAG API service (port 8000)
```

### Directory Structure

```
Aletheia/
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
├── tests/                    # Test suites
└── docs/                     # Documentation
```

### Optional Docker Services

- **Haystack**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d`
- **Doctor**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d`
- **BitNet**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.bitnet.yml up -d`
- **Production**: `docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d`

## Configuration

### Environment Setup

**Option 1: Automatic Setup (Recommended)**
```bash
./dev setup                    # Interactive setup
./dev setup --non-interactive  # Automated setup (for CI/CD)
```

**Option 2: Manual Setup**
1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Replace ALL `CHANGE_ME` values in `.env`:
   ```bash
   # Generate secure passwords:
   openssl rand -hex 32  # For DB_PASSWORD and N8N_ENCRYPTION_KEY
   openssl rand -base64 48  # For NEXTAUTH_SECRET
   ```

3. **Important Notes:**
   - Never commit `.env` with real credentials
   - N8N_API_KEY and N8N_API_SECRET are optional (only needed for n8n API access)
   - AI service keys (OpenAI, Anthropic) are optional

### Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Main Web | 8080 | NGINX serving Data Compose |
| Development API | 8082 | Debug endpoints for services |
| n8n | 8100 | Workflow automation interface |
| AI Portal | 8102 | AI services for RJLF |
| Court Processor | 8104 | Court document API |
| PostgreSQL | 8200 | Database |
| Redis | 8201 | Cache/sessions |
| RECAP Webhook | 5001 | Document webhook handler |
| Docker API | 5002 | Docker control interface |
| Elasticsearch | 9200 | Document search (optional) |
| Haystack | 8000 | RAG API service (optional) |

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
- **CitationGen**: Citation generation
- **HierarchicalSummarization**: Document hierarchy processing
- **BitNet**: BitNet AI integration
- **YAKE**: Keyword extraction
- **Unstructured**: Document processing

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

## Testing

All tests are in `tests/` directory:

```bash
./dev test              # Run all tests
./dev test unit         # Run unit tests only
./dev test integration  # Run integration tests
./dev test e2e          # Run end-to-end tests
```

## Troubleshooting

### Common Issues

1. **Services not starting?**
   ```bash
   ./dev health            # Check health status
   ./dev logs              # View all logs
   ./dev restart           # Try restarting
   ```

2. **Port conflicts?**
   ```bash
   ./dev status            # Check what's running
   ./dev down              # Stop everything
   ./dev env check         # Verify port configuration
   ```

3. **Database issues?**
   ```bash
   ./dev db shell          # Access database
   ./dev db backup         # Backup before changes
   ./dev db restore        # Restore if needed
   ```

4. **n8n not starting**: Check for crash state in volume, may need to recreate
5. **Custom nodes not appearing**: Restart n8n after adding nodes
6. **DocumentCabinet issues**: 
   - Ensure port 8104 is exposed in docker-compose.yml
   - Check if n8n workflow is active (webhook must be enabled)
   - Verify court-processor is running: `docker logs aletheia_development-court-processor-1`

### Health Check Issues

If containers show "unhealthy":

1. **Quick Fix**: Run `./scripts/utilities/fix-healthchecks.sh`
2. **Manual Fix**: Recreate affected containers:
   ```bash
   docker-compose up -d --force-recreate --no-deps [service-name]
   ```

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

## Documentation

- **AI Instructions**: [CLAUDE.md](CLAUDE.md) - Instructions for AI assistants
- **Service Dependencies**: [docs/SERVICE_DEPENDENCIES.md](docs/SERVICE_DEPENDENCIES.md)
- **Port Configuration**: [docs/PORT_CONFIGURATION.md](docs/PORT_CONFIGURATION.md)
- **Database Schema**: [docs/DATABASE.md](docs/DATABASE.md)
- **Additional Docs**: See `docs/` folder for architecture and guides