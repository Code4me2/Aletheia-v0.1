# Environment Variables Reference

This document provides a comprehensive reference for all environment variables used across the Aletheia-v0.1 platform. Variables are organized by service and functionality.

## Quick Start

1. **Copy the example configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Update required variables** (see [Required Variables](#required-variables))

3. **Start the services**:
   ```bash
   docker-compose up -d
   ```

## Required Variables

These variables **must** be configured for the system to function:

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `DB_USER` | PostgreSQL username | `aletheia_user` |
| `DB_PASSWORD` | PostgreSQL password | `secure_password_123` |
| `DB_NAME` | PostgreSQL database name | `aletheia_db` |
| `N8N_ENCRYPTION_KEY` | n8n credentials encryption | `secure_encryption_key_456` |
| `NEXTAUTH_SECRET` | JWT token signing | `nextauth_secret_789` |

## Core Database Configuration

### PostgreSQL Database
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `DB_USER` | `postgres` | Yes | PostgreSQL database username |
| `DB_PASSWORD` | `postgres` | Yes | PostgreSQL database password |
| `DB_NAME` | `postgres` | Yes | PostgreSQL database name |
| `DATABASE_URL` | `postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}` | Auto-generated | Complete PostgreSQL connection string |

**Example Configuration**:
```bash
DB_USER=aletheia_user
DB_PASSWORD=my_secure_password_123
DB_NAME=aletheia_production
```

**Security Notes**:
- Use strong passwords with mixed characters
- Avoid common database names in production
- Consider using environment-specific prefixes

## n8n Workflow Engine

### Core Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `N8N_ENCRYPTION_KEY` | - | Yes | Encryption key for n8n credentials storage |
| `N8N_CORS_ORIGIN` | `http://localhost:8080` | No | Allowed CORS origins for n8n API |

### API Authentication
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `N8N_API_KEY` | - | Production | API key for n8n authentication |
| `N8N_API_SECRET` | - | Production | API secret for n8n request signing |
| `N8N_WEBHOOK_URL` | `http://n8n:5678/webhook/...` | Yes | n8n webhook endpoint URL |

**Example Configuration**:
```bash
N8N_ENCRYPTION_KEY=your_secure_256bit_encryption_key_here
N8N_CORS_ORIGIN=https://yourdomain.com,http://localhost:8080
N8N_API_KEY=n8n_api_key_123456
N8N_API_SECRET=n8n_api_secret_789012
```

**Security Notes**:
- Generate encryption keys using `openssl rand -hex 32`
- Store API credentials securely in production
- Use HTTPS URLs in production environments

## Authentication (NextAuth)

### Core Settings
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NEXTAUTH_SECRET` | - | Yes | Secret for JWT token signing |
| `NEXTAUTH_URL` | `http://localhost:8080/chat` | Yes | Base URL for NextAuth callbacks |
| `NEXT_PUBLIC_NEXTAUTH_URL` | `http://localhost:8080/chat` | Yes | Public-facing NextAuth URL |

**Example Configuration**:
```bash
NEXTAUTH_SECRET=nextauth_super_secret_key_987654321
NEXTAUTH_URL=https://yourdomain.com/chat
NEXT_PUBLIC_NEXTAUTH_URL=https://yourdomain.com/chat
```

**Security Notes**:
- Use different secrets for different environments
- Generate secrets using `openssl rand -base64 32`
- Ensure URLs match your actual deployment

## Email Configuration

### SMTP Settings
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `SMTP_HOST` | `smtp.office365.com` | No | SMTP server hostname |
| `SMTP_PORT` | `587` | No | SMTP server port |
| `SMTP_USER` | - | No | SMTP authentication username |
| `SMTP_PASS` | - | No | SMTP authentication password |
| `SMTP_FROM` | - | No | Default sender email address |

**Example Configuration**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-app@gmail.com
SMTP_PASS=your_app_password
SMTP_FROM="Aletheia Legal AI <noreply@yourdomain.com>"
```

**Provider-Specific Examples**:

**Gmail**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your_app_password  # Use App Password, not account password
```

**Office 365**:
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@yourcompany.com
SMTP_PASS=your_password
```

## BitNet AI Integration

### Installation Paths
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `BITNET_INSTALLATION_PATH` | `/opt/bitnet` | BitNet | Path to BitNet installation |
| `BITNET_MODEL_PATH` | `models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf` | BitNet | Path to BitNet model file |

### Server Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `BITNET_SERVER_HOST` | `0.0.0.0` | No | BitNet server bind address |
| `BITNET_SERVER_PORT` | `8080` | No | BitNet server port |
| `BITNET_EXTERNAL_SERVER_URL` | `http://localhost:8080` | No | External BitNet server URL |

### Performance Tuning
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `BITNET_CONTEXT_SIZE` | `4096` | No | Context window size |
| `BITNET_CPU_THREADS` | `4` | No | Number of CPU threads |
| `BITNET_GPU_LAYERS` | `0` | No | GPU acceleration layers |
| `BITNET_BATCH_SIZE` | `512` | No | Processing batch size |
| `BITNET_CONTINUOUS_BATCHING` | `true` | No | Enable continuous batching |
| `BITNET_CACHE_REUSE` | `256` | No | Cache reuse settings |
| `BITNET_MAX_PARALLEL` | `1` | No | Maximum parallel processing |

**Example Configuration**:
```bash
# Basic BitNet setup
BITNET_INSTALLATION_PATH=/opt/bitnet-inference/BitNet
BITNET_MODEL_PATH=models/BitNet-b1.58-2B-4T/ggml-model-i2_s.gguf

# Performance optimization
BITNET_CONTEXT_SIZE=8192
BITNET_CPU_THREADS=8
BITNET_GPU_LAYERS=32
BITNET_BATCH_SIZE=1024
```

## Haystack Document Processing

### Elasticsearch Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `ELASTICSEARCH_HOST` | `http://elasticsearch:9200` | Haystack | Elasticsearch connection URL |
| `ELASTICSEARCH_INDEX` | `judicial-documents` | No | Elasticsearch index name |
| `ES_JAVA_OPTS` | `-Xms2g -Xmx2g` | No | Java heap size for Elasticsearch |

### Model Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `HAYSTACK_MODEL` | `BAAI/bge-small-en-v1.5` | No | Embedding model for vector search |
| `SENTENCE_TRANSFORMERS_HOME` | `/app/models` | No | Model cache directory |

### Service Configuration
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `HAYSTACK_MODE` | `unified` | No | Haystack operation mode |
| `ENABLE_POSTGRESQL` | `true` | No | Enable PostgreSQL integration |
| `POSTGRES_HOST` | `db` | PostgreSQL | PostgreSQL hostname |
| `POSTGRES_USER` | `${DB_USER}` | PostgreSQL | PostgreSQL username |
| `POSTGRES_PASSWORD` | `${DB_PASSWORD}` | PostgreSQL | PostgreSQL password |
| `POSTGRES_DB` | `${DB_NAME}` | PostgreSQL | PostgreSQL database |

**Example Configuration**:
```bash
# Elasticsearch
ELASTICSEARCH_HOST=http://elasticsearch:9200
ELASTICSEARCH_INDEX=legal-documents-prod
ES_JAVA_OPTS=-Xms4g -Xmx4g

# Haystack
HAYSTACK_MODEL=sentence-transformers/all-MiniLM-L6-v2
HAYSTACK_MODE=unified
ENABLE_POSTGRESQL=true
```

## Court Processor

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `LOG_LEVEL` | `INFO` | No | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `OCR_ENABLED` | `true` | No | Enable OCR for PDF processing |
| `REQUEST_DELAY` | `2` | No | Delay between court requests (seconds) |
| `PYTHONPATH` | `/app` | Yes | Python module search path |
| `PYTHONUNBUFFERED` | `1` | No | Force unbuffered Python output |

**Example Configuration**:
```bash
LOG_LEVEL=WARNING
OCR_ENABLED=true
REQUEST_DELAY=3
```

## Development Environment

### Node.js Services
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `NODE_ENV` | `development` | Yes | Node.js environment mode |
| `PORT` | `3000` | No | Default server port |
| `HOSTNAME` | `0.0.0.0` | No | Server bind address |
| `NEXT_TELEMETRY_DISABLED` | `1` | No | Disable Next.js telemetry |

### AI Portal
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GITHUB_PAGES` | `false` | No | Enable GitHub Pages deployment |

**Example Development Configuration**:
```bash
NODE_ENV=development
PORT=3000
NEXT_TELEMETRY_DISABLED=1
```

## Production Environment

### Security & Performance
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PRODUCTION_DOMAIN` | - | Production | Production domain for CORS |
| `SECURE_HEADERS_ENABLED` | `true` | No | Enable security headers |
| `FORCE_HTTPS` | `true` | No | Force HTTPS redirects |

### Monitoring
| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | `admin` | No | Grafana admin password |

**Example Production Configuration**:
```bash
NODE_ENV=production
PRODUCTION_DOMAIN=aletheia.yourfirm.com
SECURE_HEADERS_ENABLED=true
FORCE_HTTPS=true
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

## Environment-Specific Templates

### Development (.env.development)
```bash
# Database
DB_USER=aletheia_dev
DB_PASSWORD=dev_password_123
DB_NAME=aletheia_development

# n8n
N8N_ENCRYPTION_KEY=dev_encryption_key_256bit
N8N_CORS_ORIGIN=http://localhost:8080

# Auth
NEXTAUTH_SECRET=dev_nextauth_secret
NEXTAUTH_URL=http://localhost:8080/chat
NEXT_PUBLIC_NEXTAUTH_URL=http://localhost:8080/chat

# Environment
NODE_ENV=development
LOG_LEVEL=DEBUG
```

### Production (.env.production)
```bash
# Database
DB_USER=aletheia_prod
DB_PASSWORD=super_secure_production_password
DB_NAME=aletheia_production

# n8n
N8N_ENCRYPTION_KEY=production_encryption_key_very_secure
N8N_CORS_ORIGIN=https://aletheia.yourfirm.com
N8N_API_KEY=production_api_key
N8N_API_SECRET=production_api_secret

# Auth
NEXTAUTH_SECRET=production_nextauth_secret_very_secure
NEXTAUTH_URL=https://aletheia.yourfirm.com/chat
NEXT_PUBLIC_NEXTAUTH_URL=https://aletheia.yourfirm.com/chat

# Email
SMTP_HOST=smtp.yourfirm.com
SMTP_PORT=587
SMTP_USER=noreply@yourfirm.com
SMTP_PASS=secure_smtp_password
SMTP_FROM="Aletheia Legal AI <noreply@yourfirm.com>"

# Security
PRODUCTION_DOMAIN=aletheia.yourfirm.com
SECURE_HEADERS_ENABLED=true
FORCE_HTTPS=true

# Environment
NODE_ENV=production
LOG_LEVEL=ERROR
```

## Security Best Practices

### Secret Generation
```bash
# Generate secure passwords
openssl rand -base64 32

# Generate hex keys
openssl rand -hex 32

# Generate UUID (for webhook IDs)
uuidgen
```

### Environment File Security
- **Never commit** `.env` files to version control
- Use different secrets for each environment
- Rotate secrets regularly in production
- Use secrets management services in production
- Set appropriate file permissions: `chmod 600 .env`

### Production Considerations
- Use external secret management (AWS Secrets Manager, HashiCorp Vault)
- Enable SSL/TLS for all external connections
- Use strong, unique passwords for each service
- Implement proper backup strategies for databases
- Monitor logs for security events

## Troubleshooting

### Common Issues

1. **Database Connection Failures**:
   ```bash
   # Check database connectivity
   docker-compose exec db psql -U $DB_USER -d $DB_NAME -c "SELECT 1;"
   ```

2. **n8n Encryption Key Issues**:
   - Ensure the key is exactly 32 characters (256 bits)
   - Don't change the key after workflows are created

3. **NextAuth Configuration**:
   - Ensure URLs match your actual deployment
   - Check for trailing slashes in URLs

4. **Email Configuration**:
   ```bash
   # Test SMTP connection
   docker-compose exec lawyer-chat npm run test:email
   ```

### Environment Validation

Create a validation script to check your environment:

```bash
#!/bin/bash
# validate-env.sh

required_vars=(
    "DB_USER"
    "DB_PASSWORD"
    "DB_NAME"
    "N8N_ENCRYPTION_KEY"
    "NEXTAUTH_SECRET"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "ERROR: $var is not set"
        exit 1
    fi
done

echo "✅ All required environment variables are set"
```

## Reference Links

- [n8n Environment Variables](https://docs.n8n.io/hosting/configuration/)
- [NextAuth.js Configuration](https://next-auth.js.org/configuration/options)
- [Docker Compose Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Node.js Environment Variables](https://nodejs.org/api/process.html#process_process_env)