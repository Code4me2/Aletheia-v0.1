# Aletheia

AI-powered legal document processing platform with n8n workflow automation.

## Quick Start

```bash
# 1. Setup (first time only)
./dev setup

# 2. Start services
./dev up

# 3. Access services
# Main app:          http://localhost:8080
# n8n:               http://localhost:8100 (velvetmoon222999@gmail.com / Welcome123!)
# Lawyer Chat:       http://localhost:8080/chat
# AI Portal:         http://localhost:8102
# Court Processor:   http://localhost:8104
# Development API:   http://localhost:8082/status
```

## Commands
Run `./dev help` for all available commands.

## Project Status

### ✅ Completed Simplifications
- **Scripts**: 19 scripts → 4 essential + `/dev` CLI
- **Docker**: 13 docker-compose files → 3 active + 4 optional
- **Documentation**: 31 MD files in root → 5 essential
- **Environment**: 94 lines → 47 essential variables
- **Tests**: 4 directories → 1 organized `tests/` directory

### 🔴 Remaining Opportunities
- **Node Modules**: 1.6GB removable (779MB in custom nodes, 822MB in lawyer-chat)
  - Custom nodes use `dist/` folders, node_modules not needed at runtime
  - Run: `rm -rf n8n/custom-nodes/*/node_modules services/lawyer-chat/node_modules`

### 📁 Backup Locations
- `backups/`: Recent .env and database backups (22MB SQL from Aug 23)
- `data/db-backups/`: Court documents database (11MB SQL + restore script)
- `workflow_json/backup/`: n8n workflow backups

### 🐳 Optional Docker Services
- **Haystack**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d`
- **Doctor**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d`
- **BitNet**: `docker-compose -f docker-compose.yml -f n8n/docker-compose.bitnet.yml up -d`
- **Production**: `docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d`

## Port Configuration

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

## Documentation
- **Main Guide**: [CLAUDE.md](CLAUDE.md) - Complete project details
- **Service Architecture**: [docs/SERVICE_DEPENDENCIES.md](docs/SERVICE_DEPENDENCIES.md)
- **Detailed Docs**: See `docs/` folder for architecture, guides, and development docs