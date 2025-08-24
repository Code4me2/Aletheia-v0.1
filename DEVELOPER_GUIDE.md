# Aletheia Developer Guide

## 🎯 Single Command Interface

**Use the `./dev` CLI for ALL operations.** Other methods are deprecated.

```bash
./dev help              # Show all available commands
```

## Quick Start

```bash
# 1. First time setup
./dev setup

# 2. Start everything
./dev up

# 3. Check status
./dev status
```

## Common Commands

### Service Management
```bash
./dev up                # Start all services
./dev down              # Stop all services
./dev restart           # Restart all services
./dev status            # Check service status
./dev health            # Check health endpoints
./dev logs [service]    # View logs
```

### Development
```bash
./dev test              # Run tests
./dev lint              # Run linting
./dev build             # Build services
```

### Database
```bash
./dev db backup         # Backup database
./dev db restore        # Restore database
./dev db shell          # Database shell
```

## ⚠️ Deprecated Methods

The following are **DEPRECATED** - use `./dev` instead:

```bash
# DON'T USE:
make dev               # → Use: ./dev up
npm run dev            # → Use: ./dev up
docker-compose up      # → Use: ./dev up

# DON'T USE:
make test              # → Use: ./dev test
npm test               # → Use: ./dev test

# DON'T USE:
make logs              # → Use: ./dev logs
docker-compose logs    # → Use: ./dev logs
```

## Service URLs

After running `./dev up`:

| Service | URL | Description |
|---------|-----|-------------|
| Main App | http://localhost:8080 | Data Compose web interface |
| n8n | http://localhost:8100 | Workflow automation |
| AI Portal | http://localhost:8102 | AI services interface |
| Court Processor | http://localhost:8104 | Document processing API |
| Lawyer Chat | http://localhost:8080/chat | Legal chat interface |

## Port Reference

| Port | Service | Purpose |
|------|---------|---------|
| 8080 | Web/NGINX | Main application |
| 8082 | Dev API | Development endpoints |
| 8100 | n8n | Workflow automation |
| 8102 | AI Portal | AI services |
| 8104 | Court Processor | Document API |
| 8200 | PostgreSQL | Database |
| 8201 | Redis | Cache/sessions |

## Environment Setup

1. Copy the template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values

3. Never commit `.env` with real credentials

## Testing

All tests are in `tests/` directory:

```bash
./dev test              # Run all tests
./dev test unit         # Run unit tests only
./dev test integration  # Run integration tests
./dev test e2e          # Run end-to-end tests
```

## Troubleshooting

### Services not starting?
```bash
./dev health            # Check health status
./dev logs              # View all logs
./dev restart           # Try restarting
```

### Port conflicts?
```bash
./dev status            # Check what's running
./dev down              # Stop everything
./dev ports             # Show port usage
```

### Database issues?
```bash
./dev db shell          # Access database
./dev db backup         # Backup before changes
./dev db restore        # Restore if needed
```

## Getting Help

```bash
./dev help              # Show all commands
./dev help [command]    # Show command details
```

For issues, check docs/ directory or open a GitHub issue.