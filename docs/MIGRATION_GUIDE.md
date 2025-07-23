# Migration Guide: New Port Mapping System

## Overview

This guide helps you migrate from the legacy port configuration to the new flexible port mapping system introduced in the networking branch.

## What's Changed

### Old System
- Fixed ports in `.env` file
- Manual port management
- Single environment configuration
- Port conflicts when running multiple environments

### New System
- Dynamic port allocation by environment
- Automatic conflict detection
- Multiple environment support
- Centralized deployment script
- Built-in monitoring and scaling options

## Migration Steps

### 1. Stop Current Services

```bash
# In your current worktree
docker-compose down
docker system prune -f  # Optional: clean up unused resources
```

### 2. Backup Current Configuration

```bash
# Save your current .env if you have custom settings
cp .env .env.backup
```

### 3. Switch to Networking Branch

```bash
cd /Users/vel/Desktop/coding/Aletheia-worktrees/networking
```

### 4. Generate New Configuration

```bash
# For development
./scripts/deploy.sh -e development ports

# For staging
./scripts/deploy.sh -e staging ports

# For production
./scripts/deploy.sh -e production ports
```

### 5. Start Services with New System

```bash
# Basic deployment
./scripts/deploy.sh up

# With monitoring
./scripts/deploy.sh -m up

# Full production stack
./scripts/deploy.sh -e production -m -l -s up
```

## Port Mapping Changes

### Development Environment

| Service      | Old Port | New Port | Access URL                    |
|--------------|----------|----------|-------------------------------|
| Web          | 8080     | 8080     | http://localhost:8080         |
| n8n          | 5678     | 8100     | http://localhost:8080/n8n/    |
| Lawyer Chat  | 3001     | 8101     | http://localhost:8080/chat/   |
| AI Portal    | 8085     | 8102     | http://localhost:8080/portal/ |
| PostgreSQL   | 5432     | 8200     | postgresql://localhost:8200   |
| Redis        | 6379     | 8201     | redis://localhost:8201        |
| Elasticsearch| 9200     | 8202     | http://localhost:8202         |

### Important Notes

1. **Service URLs**: Most services are now accessed through the reverse proxy at port 8080
2. **Direct Access**: Direct service ports have changed but are generally not needed
3. **API Gateway**: New API gateway available at port 8081 for development

## Configuration Migration

### Environment Variables

If you have custom environment variables in your old `.env`, add them to the generated environment file:

```bash
# After generating new config
cat .env.backup >> .env
# Then edit .env to remove duplicates and conflicts
```

### Custom Ports

To override default ports:

```bash
# Edit config/ports.yml for permanent changes
# Or set environment variables before deployment
export WEB_PORT=8090
./scripts/deploy.sh up
```

## Troubleshooting

### Port Conflicts

```bash
# Check for conflicts
python3 scripts/generate-env.py development

# If conflicts found, stop conflicting services or choose different environment
./scripts/deploy.sh -e staging up
```

### Service Discovery

Services now use internal Docker networks and service names:
- Old: `http://localhost:5678`
- New: `http://n8n:5678` (internal) or `http://localhost:8080/n8n/` (external)

### Database Connections

Update connection strings:
- Old: `postgresql://user:pass@localhost:5432/db`
- New: `postgresql://user:pass@localhost:8200/db` (development)

## Rollback

If you need to rollback:

```bash
# Stop new services
./scripts/deploy.sh down

# Return to old worktree
cd ../main  # or your previous worktree

# Restore old configuration
cp .env.backup .env

# Start old services
docker-compose up -d
```

## Benefits of Migration

1. **Environment Flexibility**: Easy switching between dev/staging/prod
2. **Port Organization**: Logical port ranges prevent conflicts
3. **Monitoring**: Built-in observability stack
4. **Scaling**: Load balancer ready for horizontal scaling
5. **Automation**: Single script manages all deployments

## Getting Help

- Check deployment options: `./scripts/deploy.sh -h`
- View current ports: `./scripts/deploy.sh ports`
- Check service status: `./scripts/deploy.sh status`
- View logs: `./scripts/deploy.sh logs [service]`

## Next Steps

After successful migration:

1. Test all services are accessible
2. Update any external integrations with new ports
3. Configure monitoring dashboards (if using -m flag)
4. Set up SSL certificates for production
5. Update CI/CD pipelines to use new deployment script