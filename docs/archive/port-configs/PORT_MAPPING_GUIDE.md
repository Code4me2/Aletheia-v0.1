# Aletheia Port Mapping & Deployment Guide

## Overview

This guide documents the new flexible port mapping system for Aletheia, designed to support easy local development and server deployment across multiple environments.

## Quick Start

### Basic Deployment

```bash
# Development environment (default)
./scripts/deploy.sh up

# Staging environment
./scripts/deploy.sh -e staging up

# Production with full stack
./scripts/deploy.sh -e production -m -l -s up
```

### Check Port Mappings

```bash
# View ports for current environment
./scripts/deploy.sh ports

# View ports for specific environment
./scripts/deploy.sh -e production ports
```

## Port Architecture

### Port Range Allocation

The system uses structured port ranges to avoid conflicts:

| Range      | Purpose                    | Examples                          |
|------------|----------------------------|-----------------------------------|
| 8000-8099  | Core Services              | Web, API Gateway, Reverse Proxy   |
| 8100-8199  | Application Services       | n8n, Lawyer Chat, AI Portal       |
| 8200-8299  | Data Services              | PostgreSQL, Redis, Elasticsearch  |
| 8300-8399  | Monitoring & Analytics     | Prometheus, Grafana, Loki         |
| 8400-8499  | Development & Testing      | Reserved for future use           |
| 8500-8599  | AI/ML Services             | Haystack, BitNet, Ollama Proxy    |

### Environment-Specific Ports

#### Development (8000-8599 range)
```
Core Services:
  - Web: 8080
  - API Gateway: 8081
  - Reverse Proxy: 8082

Application Services:
  - n8n: 8100
  - Lawyer Chat: 8101
  - AI Portal: 8102

Data Services:
  - PostgreSQL: 8200
  - Redis: 8201
  - Elasticsearch: 8202

AI Services:
  - Haystack: 8500
  - BitNet: 8501
  - Ollama Proxy: 8502

Monitoring:
  - Prometheus: 8300
  - Grafana: 8301
  - Loki: 8302
  - Node Exporter: 8303
```

#### Staging (9000-9599 range)
```
Core Services:
  - Web: 9080
  - API Gateway: 9081
  - Reverse Proxy: 9082

[Similar pattern with 9xxx ports]
```

#### Production (Standard ports)
```
Core Services:
  - Web: 80/443 (SSL)
  - API Gateway: 8080

Internal Services (not exposed):
  - n8n: 5678
  - Lawyer Chat: 3000
  - AI Portal: 3001
  - PostgreSQL: 5432
  - Redis: 6379
  - Elasticsearch: 9200
```

## Key Components

### 1. Centralized Configuration

**File:** `config/ports.yml`
- Defines all port mappings for each environment
- Specifies internal service ports
- Lists reserved port ranges

### 2. Environment Generator

**Script:** `scripts/generate-env.py`
- Generates environment-specific .env files
- Detects port conflicts automatically
- Ensures consistent configuration

### 3. Deployment Script

**Script:** `scripts/deploy.sh`
- Unified deployment interface
- Environment switching
- Optional components (monitoring, load balancer, SSL)

### 4. Reverse Proxy (Nginx)

**Configuration:** `nginx/nginx.conf`
- Service discovery and routing
- Rate limiting
- Health checks
- SSL termination (production)

### 5. Load Balancer (HAProxy)

**Configuration:** `config/haproxy.cfg`
- Horizontal scaling support
- Health monitoring
- Statistics interface
- SSL offloading

## Deployment Scenarios

### Local Development

```bash
# Start basic services
./scripts/deploy.sh up

# With monitoring
./scripts/deploy.sh -m up

# View logs
./scripts/deploy.sh logs n8n
```

### Server Deployment

```bash
# Staging server
./scripts/deploy.sh -e staging -m up

# Production server with full stack
./scripts/deploy.sh -e production -m -l -s up
```

### Service Access URLs

Development:
- Main App: http://localhost:8080
- n8n: http://localhost:8080/n8n/
- Lawyer Chat: http://localhost:8080/chat/
- AI Portal: http://localhost:8080/portal/
- API Gateway: http://localhost:8081
- Monitoring: http://localhost:8301 (Grafana)

Production:
- Main App: https://your-domain.com
- n8n: https://your-domain.com/n8n/
- Lawyer Chat: https://your-domain.com/chat/
- AI Portal: https://your-domain.com/portal/

## Advanced Features

### Service Discovery

The system includes Consul for service discovery:
```bash
# Enable with monitoring stack
./scripts/deploy.sh -m up

# Access Consul UI
http://localhost:8500
```

### Monitoring Stack

Full observability with:
- **Prometheus**: Metrics collection (port varies by environment)
- **Grafana**: Visualization (port varies by environment)
- **Loki**: Log aggregation
- **Promtail**: Log shipping
- **Node Exporter**: System metrics

### Custom Port Configuration

1. Edit `config/ports.yml` for permanent changes
2. Or override via environment variables:
   ```bash
   export WEB_PORT=8090
   ./scripts/deploy.sh up
   ```

## Migration from Legacy System

If migrating from the old port system:

1. Stop all running containers:
   ```bash
   docker-compose down
   ```

2. Clean up old volumes (optional):
   ```bash
   ./scripts/deploy.sh clean
   ```

3. Start with new system:
   ```bash
   ./scripts/deploy.sh up
   ```

## Troubleshooting

### Port Conflicts

The system automatically detects conflicts:
```bash
python3 scripts/generate-env.py development
# Warning: Port conflicts detected...
```

### Service Health

Check service status:
```bash
./scripts/deploy.sh status
```

### Debug Access

Development environment provides debug endpoints:
- http://localhost:8082/debug/n8n/
- http://localhost:8082/debug/chat/
- http://localhost:8082/debug/portal/

## Best Practices

1. **Environment Isolation**: Use different environments for different stages
2. **Port Documentation**: Update `config/ports.yml` when adding services
3. **Health Checks**: All services include health endpoints
4. **Monitoring**: Enable monitoring for production deployments
5. **SSL/TLS**: Always use SSL in production

## Adding New Services

1. Update `config/ports.yml` with port assignments
2. Add service to appropriate docker-compose file
3. Configure reverse proxy routing in `nginx/nginx.conf`
4. Update HAProxy configuration if load balancing needed
5. Regenerate environment files:
   ```bash
   python3 scripts/generate-env.py <environment>
   ```

## Security Considerations

- Rate limiting enabled on all API endpoints
- SSL/TLS support for production
- Internal networks for service isolation
- Security headers configured in nginx
- Port ranges avoid system/privileged ports

## Future Enhancements

- Kubernetes deployment manifests
- Auto-scaling configuration
- Service mesh integration
- Dynamic service registration
- Multi-region deployment support