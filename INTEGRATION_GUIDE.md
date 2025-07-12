# Aletheia v0.1 Integration Guide

This guide provides clear integration points and instructions for merging Aletheia into a larger legal technology build.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Code4me2/Aletheia-v0.1.git
cd Aletheia-v0.1

# Start all services with one command
./scripts/start-aletheia.sh --with-haystack

# Access the main interface
open http://localhost:8080
```

## Architecture Overview

Aletheia is a containerized microservices platform with the following components:

### Core Services (Always Required)
- **PostgreSQL Database**: Central data storage
- **n8n Workflow Engine**: Process automation and webhook handling
- **NGINX Web Server**: Static content and reverse proxy
- **Redis Cache**: Session management and caching

### Application Services
- **Main Web Interface**: AI chat and system controls (port 8080)
- **Lawyer Chat**: Specialized legal chat interface (port 8080/chat)
- **AI Portal**: Legal firm portal (port 8085)
- **Court Processor**: Court document processing service

### Optional Services
- **Elasticsearch**: Document search engine (port 9200)
- **Haystack API**: Document RAG service (port 8000)

## Integration Points

### 1. Service Endpoints

All services expose REST APIs that can be integrated:

```yaml
Main Application:
  Web Interface: http://localhost:8080
  API Webhooks: http://localhost:8080/webhook/{webhook-id}
  
n8n Workflows:
  UI: http://localhost:8080/n8n/
  API: http://localhost:5678/rest/
  
Lawyer Chat:
  UI: http://localhost:8080/chat
  API: http://localhost:8080/chat/api/
  
AI Portal:
  UI: http://localhost:8085
  
Haystack (Optional):
  API: http://localhost:8000
  Docs: http://localhost:8000/docs
```

### 2. Database Integration

PostgreSQL database with multiple schemas:

```sql
- aletheia_db     # Main application data
- lawyerchat      # Lawyer chat application
- n8n             # Workflow engine data
- courtprocessor  # Court document data
```

Connection string format:
```
postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
```

### 3. Webhook Integration

The system uses n8n webhooks for all AI processing:

```javascript
// Default webhook for AI chat
const WEBHOOK_URL = 'http://localhost:8080/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177';

// Send chat request
fetch(WEBHOOK_URL, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    action: 'chat',
    message: 'Your message here'
  })
});
```

### 4. Authentication Integration

- **NextAuth**: Used by lawyer-chat service
- **Session Management**: Redis-based sessions
- **API Keys**: Environment variable based

### 5. Custom n8n Nodes

The project includes pre-built custom n8n nodes that are ready to use:

- **No build required**: All nodes come with compiled JavaScript in `dist/` directories
- **Automatic loading**: Nodes are mounted via Docker volumes and loaded by n8n on startup
- **Space optimization**: The `node_modules` directories (~675MB) can be safely removed without affecting functionality
- **Available nodes**:
  - `n8n-nodes-deepseek`: DeepSeek AI integration
  - `n8n-nodes-haystack`: Document search and RAG
  - `n8n-nodes-bitnet`: BitNet integration
  - `n8n-nodes-citationchecker`: Legal citation validation
  - `n8n-nodes-hierarchicalSummarization`: Document summarization
  - `n8n-nodes-yake`: Keyword extraction

## Deployment Options

### 1. Standalone Deployment

```bash
# Basic deployment
./scripts/start-aletheia.sh

# Full deployment with search
./scripts/start-aletheia.sh --with-haystack
```

### 2. Integration into Existing Docker Compose

Add Aletheia services to your existing `docker-compose.yml`:

```yaml
# In your docker-compose.yml
version: '3.8'

services:
  # Your existing services...
  
  # Include Aletheia services
  aletheia:
    extends:
      file: ./aletheia/docker-compose.yml
      service: web
  
  aletheia-n8n:
    extends:
      file: ./aletheia/docker-compose.yml
      service: n8n
  
  # Add other required services...
```

### 3. Kubernetes Deployment

Helm charts and Kubernetes manifests are planned for future releases.

## Environment Configuration

### Required Environment Variables

```bash
# Database
DB_USER=aletheia_user
DB_PASSWORD=<secure-password>
DB_NAME=aletheia_db

# n8n
N8N_ENCRYPTION_KEY=<32-char-hex-string>

# Authentication
NEXTAUTH_SECRET=<64-char-string>

# Optional: Email
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=<email>
SMTP_PASS=<password>
```

### Port Configuration

All ports are configurable via environment variables:

```bash
WEB_PORT=8080          # Main web interface
N8N_PORT=5678          # n8n engine
LAWYER_CHAT_PORT=3001  # Lawyer chat internal
AI_PORTAL_PORT=8085    # AI portal
ELASTICSEARCH_PORT=9200 # Elasticsearch
HAYSTACK_PORT=8000     # Haystack API
```

## API Integration Examples

### 1. Chat API Integration

```python
import requests

# Send message to AI chat
response = requests.post(
    'http://localhost:8080/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177',
    json={
        'action': 'chat',
        'message': 'Explain contract law basics',
        'timestamp': '2024-01-01T12:00:00Z'
    }
)

ai_response = response.json()
```

### 2. Document Search Integration

```python
# Search documents via Haystack
response = requests.post(
    'http://localhost:8000/search',
    json={
        'query': 'patent infringement cases',
        'top_k': 5,
        'use_hybrid': True
    }
)

search_results = response.json()
```

### 3. Workflow Automation

```javascript
// Trigger n8n workflow via API
const workflowResponse = await fetch('http://localhost:5678/rest/workflows/execute', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-N8N-API-KEY': process.env.N8N_API_KEY
  },
  body: JSON.stringify({
    workflowId: 'your-workflow-id',
    data: { /* your data */ }
  })
});
```

## Health Monitoring

### Automated Health Checks

```bash
# Run comprehensive health check
./scripts/health-check-comprehensive.sh
```

### Programmatic Health Checks

```python
# Check all services
services = {
    'database': 'http://localhost:5432',
    'n8n': 'http://localhost:5678/healthz',
    'web': 'http://localhost:8080',
    'elasticsearch': 'http://localhost:9200/_cluster/health'
}

for service, url in services.items():
    try:
        response = requests.get(url, timeout=5)
        print(f"{service}: {'UP' if response.ok else 'DOWN'}")
    except:
        print(f"{service}: DOWN")
```

## Scaling Considerations

### Horizontal Scaling

The architecture supports horizontal scaling:

1. **Stateless Services**: Web, API services can be replicated
2. **Load Balancing**: NGINX can distribute traffic
3. **Database**: PostgreSQL supports read replicas
4. **Cache**: Redis can be clustered

### Docker Swarm Support

```bash
# Deploy with Docker Swarm
docker stack deploy -c docker-compose.swarm.yml aletheia
```

## Security Considerations

### Network Isolation

Services are isolated in two networks:
- `frontend`: Public-facing services
- `backend`: Internal services and databases

### Secrets Management

1. Use environment variables for sensitive data
2. Never commit `.env` files
3. Rotate credentials regularly
4. Use Docker secrets in production

### Access Control

- n8n supports basic authentication
- NextAuth for lawyer-chat
- API key authentication for webhooks

## Troubleshooting

### Common Issues

1. **Services not starting**: Check logs with `docker-compose logs -f [service]`
2. **Workflow not active**: Verify in n8n UI
3. **Database connection**: Ensure `.env` is properly configured

### Debug Commands

```bash
# View all logs
docker-compose logs -f

# Check specific service
docker-compose logs -f n8n

# Restart service
docker-compose restart [service]

# Full reset
./scripts/stop-aletheia.sh --clean
./scripts/start-aletheia.sh
```

## Migration Path

### From Development to Production

1. Update environment variables for production
2. Enable HTTPS in NGINX configuration
3. Set up proper backup strategies
4. Configure monitoring and alerting
5. Implement rate limiting and security headers

### Database Migrations

```bash
# Export data
docker-compose exec db pg_dump -U aletheia_user aletheia_db > backup.sql

# Import data
docker-compose exec -T db psql -U aletheia_user aletheia_db < backup.sql
```

## Support and Documentation

- **Repository**: https://github.com/Code4me2/Aletheia-v0.1
- **Issues**: https://github.com/Code4me2/Aletheia-v0.1/issues
- **Documentation**: See `/docs` directory
- **API Docs**: http://localhost:8000/docs (when Haystack is running)

## Next Steps

1. Review the provided scripts in `/scripts` directory
2. Configure environment variables in `.env`
3. Run `./scripts/start-aletheia.sh` to start
4. Access http://localhost:8080 to verify installation
5. Integrate desired endpoints into your application