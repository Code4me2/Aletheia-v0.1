# Production Deployment Guide for Lawyer-Chat Application

This guide provides comprehensive step-by-step instructions for deploying the complete lawyer-chat application to production, including authentication, chat functionality, AI integration, and all supporting services.

## Prerequisites

- Domain name with DNS control
- SSL certificate (or ability to obtain one via Let's Encrypt)
- Production PostgreSQL database (v13+)
- Production Redis instance (v6+)
- Access to n8n instance with DeepSeek workflow
- SMTP service credentials (optional but recommended)
- Minimum 4GB RAM, 2 CPU cores, 20GB storage

## Phase 1: Pre-Deployment Configuration (CRITICAL)

### 1.1 Generate Required Secrets

```bash
# Generate NEXTAUTH_SECRET (32+ characters)
openssl rand -base64 32
# Example: vK3kB5xTPc8pHbHmQX/NFxZKQXOqMwLm5nHuxQ6MYQM=

# Generate database password
openssl rand -base64 24
# Example: 9xB2mQ7pL3vN8kR5tY6wE1aZ

# Generate Redis password
openssl rand -base64 16
# Example: kL9mN3pQ7xR2vB5t
```

**IMPORTANT:** 
- Save all secrets in a secure password manager
- Never commit secrets to git
- Use the same NEXTAUTH_SECRET across all instances

### 1.2 Set Up HTTPS/SSL Certificate

#### Option A: Using Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

#### Option B: Using Purchased Certificate
1. Purchase SSL certificate from provider
2. Download certificate files (crt, key, ca-bundle)
3. Configure in nginx (see configuration below)

### 1.3 Configure Nginx with HTTPS and Subpath Routing

Create nginx configuration at `/etc/nginx/sites-available/lawyer-chat`:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS server block
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:10m;
    ssl_stapling on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Root path (optional - for main site)
    location / {
        # Your main site configuration
        root /var/www/html;
        index index.html;
    }

    # Lawyer-Chat Application (subpath /chat)
    location /chat {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # Required for streaming responses
        proxy_buffering off;
        proxy_cache off;
        
        # Increase timeouts for AI responses
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        proxy_send_timeout 300s;
        
        # WebSocket support for real-time features
        proxy_set_header X-NginX-Proxy true;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/lawyer-chat /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 1.4 Create Complete Production Environment File

Create `.env.production` in the lawyer-chat directory:

```env
# === CRITICAL - Required for production ===
NEXTAUTH_SECRET=your-generated-secret-from-step-1.1
NEXTAUTH_URL=https://yourdomain.com/chat
NODE_ENV=production

# === Database Configuration ===
DATABASE_URL=postgresql://prod_user:your-db-password@prod-db-host:5432/lawyerchat?sslmode=require

# === Redis Configuration ===
REDIS_URL=redis://:your-redis-password@prod-redis-host:6379/0

# === n8n Integration ===
# Internal Docker URL if using Docker
N8N_WEBHOOK_URL=http://n8n:5678/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177
# External URL for client-side (optional)
N8N_EXTERNAL_URL=https://yourdomain.com/n8n/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177

# === Security Configuration ===
ALLOWED_EMAIL_DOMAINS=@reichmanjorgensen.com
SESSION_MAX_AGE=28800  # 8 hours in seconds
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=1800000  # 30 minutes in milliseconds
PASSWORD_MIN_LENGTH=8
TOKEN_EXPIRY_HOURS=24
RESET_TOKEN_EXPIRY_HOURS=1

# === Email Service (Required for full functionality) ===
EMAIL_MODE=production  # console | production
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=noreply@reichmanjorgensen.com
SMTP_PASS=your-smtp-password
SMTP_FROM="Aletheia Legal <noreply@reichmanjorgensen.com>"

# === Application Settings ===
# Chat settings
MAX_MESSAGE_LENGTH=10000
CHAT_HISTORY_LIMIT=50
STREAMING_ENABLED=true

# Performance settings
DATABASE_POOL_MIN=2
DATABASE_POOL_MAX=10
REDIS_MAX_RETRIES=3

# Feature flags
ENABLE_ANALYTICS=true
ENABLE_PDF_EXPORT=true
ENABLE_DARK_MODE=true
```

## Phase 2: Infrastructure Setup

### 2.1 PostgreSQL Database Setup

```bash
# Connect to PostgreSQL server
sudo -u postgres psql

# Create production database and user
CREATE USER prod_user WITH PASSWORD 'your-db-password';
CREATE DATABASE lawyerchat OWNER prod_user;
GRANT ALL PRIVILEGES ON DATABASE lawyerchat TO prod_user;

# Enable required extensions
\c lawyerchat
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

# Configure SSL (edit postgresql.conf)
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'

# Configure connection limits (edit postgresql.conf)
max_connections = 200
shared_buffers = 256MB
```

### 2.2 Redis Setup with Persistence

Install and configure Redis:
```bash
# Install Redis
sudo apt-get install redis-server

# Configure Redis (edit /etc/redis/redis.conf)
# Authentication
requirepass your-redis-password

# Persistence
appendonly yes
appendfsync everysec
save 900 1
save 300 10
save 60 10000

# Memory management
maxmemory 1gb
maxmemory-policy allkeys-lru

# Network security
bind 127.0.0.1 ::1
protected-mode yes

# Start Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### 2.3 n8n Webhook Configuration

Ensure n8n is running with the DeepSeek workflow:

1. Access n8n interface
2. Import the `Basic_workflow` from `workflow_json/web_UI_basic`
3. Configure DeepSeek node with your API credentials
4. Activate the workflow
5. Verify webhook URL matches: `c188c31c-1c45-4118-9ece-5b6057ab5177`

## Phase 3: Application Deployment

### 3.1 Clone and Prepare Application

```bash
# Create application directory
sudo mkdir -p /opt/aletheia
cd /opt/aletheia

# Clone repository
git clone https://github.com/Code4me2/Aletheia-v0.1.git .
cd services/lawyer-chat

# Copy production environment
cp .env.production .env

# Set proper permissions
sudo chown -R www-data:www-data /opt/aletheia/services/lawyer-chat
```

### 3.2 Build Application

```bash
# Install dependencies
npm ci --production=false  # Need dev deps for building

# Generate Prisma client
npx prisma generate

# Build Next.js application
npm run build

# Remove dev dependencies
npm prune --production
```

### 3.3 Database Migration

```bash
# Run production migrations
NODE_ENV=production npx prisma migrate deploy

# Verify database schema
NODE_ENV=production npx prisma db push

# Seed initial data (optional)
NODE_ENV=production npm run db:seed
```

### 3.4 Docker Deployment (Recommended)

Create `docker-compose.production.yml`:

```yaml
version: '3.8'

services:
  lawyer-chat:
    build:
      context: ./services/lawyer-chat
      dockerfile: Dockerfile
    env_file:
      - ./services/lawyer-chat/.env.production
    environment:
      - NODE_ENV=production
    ports:
      - "127.0.0.1:8080:3000"  # Only bind to localhost
    networks:
      - frontend
      - backend
    depends_on:
      - db
      - redis
    restart: always
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/chat/api/csrf"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=prod_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=lawyerchat
      - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
      - ./init-scripts:/docker-entrypoint-initdb.d
    networks:
      - backend
    restart: always
    command: 
      - "postgres"
      - "-c"
      - "ssl=on"
      - "-c"
      - "ssl_cert_file=/var/lib/postgresql/server.crt"
      - "-c"
      - "ssl_key_file=/var/lib/postgresql/server.key"

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data_prod:/data
    networks:
      - backend
    restart: always
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # Isolate backend services

volumes:
  postgres_data_prod:
    driver: local
  redis_data_prod:
    driver: local
```

Deploy with Docker:
```bash
# Build and start services
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d --build

# Check service health
docker-compose ps
docker-compose logs -f lawyer-chat

# Verify application
curl -k https://yourdomain.com/chat/api/health
```

## Phase 4: Post-Deployment Configuration

### 4.1 Create Admin User

```bash
# Option 1: Using script
docker exec lawyer-chat npm run create-admin

# Option 2: Direct database insert
docker exec db psql -U prod_user -d lawyerchat << EOF
INSERT INTO "User" (id, email, name, password, role, "emailVerified", "createdAt", "updatedAt")
VALUES (
  gen_random_uuid(),
  'admin@reichmanjorgensen.com',
  'Admin User',
  '\$2b\$12\$YOUR_BCRYPT_HASH_HERE',  -- Generate with: npm run hash-password
  'admin',
  NOW(),
  NOW(),
  NOW()
);
EOF
```

### 4.2 Configure SMTP and Test Email

```bash
# Test email configuration
docker exec lawyer-chat npm run test-email

# Send test verification email
curl -X POST https://yourdomain.com/chat/api/auth/test-email \
  -H "Content-Type: application/json" \
  -d '{"email": "test@reichmanjorgensen.com"}'
```

### 4.3 Application Monitoring Setup

#### Install PM2 (if not using Docker)
```bash
npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'lawyer-chat',
    script: 'npm',
    args: 'start',
    cwd: '/opt/aletheia/services/lawyer-chat',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    },
    error_file: '/var/log/lawyer-chat/error.log',
    out_file: '/var/log/lawyer-chat/out.log',
    time: true,
    instances: 2,
    exec_mode: 'cluster',
    max_memory_restart: '1G'
  }]
};
EOF

# Start with PM2
pm2 start ecosystem.config.js
pm2 save
pm2 startup
```

#### Configure Logging
```bash
# Create log directory
sudo mkdir -p /var/log/lawyer-chat
sudo chown -R www-data:www-data /var/log/lawyer-chat

# Configure log rotation
sudo tee /etc/logrotate.d/lawyer-chat << EOF
/var/log/lawyer-chat/*.log {
    daily
    rotate 14
    compress
    missingok
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        docker-compose restart lawyer-chat > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 4.4 Backup Configuration

Create automated backup script at `/opt/aletheia/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backup/aletheia"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
echo "Backing up database..."
docker exec db pg_dump -U prod_user -d lawyerchat | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup Redis
echo "Backing up Redis..."
docker exec redis redis-cli --raw BGSAVE
sleep 5
docker cp redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Backup environment and configurations
echo "Backing up configurations..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz \
  /opt/aletheia/services/lawyer-chat/.env.production \
  /opt/aletheia/services/lawyer-chat/prisma \
  /etc/nginx/sites-available/lawyer-chat

# Backup uploaded files (if any)
if [ -d "/opt/aletheia/services/lawyer-chat/uploads" ]; then
  tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/aletheia/services/lawyer-chat/uploads
fi

# Clean old backups
echo "Cleaning old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "*.rdb" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

Add to crontab:
```bash
# Run backup daily at 2 AM
0 2 * * * /opt/aletheia/backup.sh >> /var/log/lawyer-chat/backup.log 2>&1
```

## Phase 5: Security Hardening

### 5.1 Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow required ports
sudo ufw allow 22/tcp     # SSH
sudo ufw allow 80/tcp     # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp    # HTTPS

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status verbose
```

### 5.2 Fail2Ban Configuration

Install and configure Fail2Ban:

```bash
# Install Fail2Ban
sudo apt-get install fail2ban

# Create jail configuration
sudo tee /etc/fail2ban/jail.d/lawyer-chat.conf << EOF
[lawyer-chat-auth]
enabled = true
port = https,http
filter = lawyer-chat-auth
logpath = /var/log/lawyer-chat/error.log
maxretry = 5
bantime = 3600
findtime = 600

[lawyer-chat-api]
enabled = true
port = https,http
filter = lawyer-chat-api
logpath = /var/log/nginx/access.log
maxretry = 100
bantime = 600
findtime = 60
EOF

# Create filter for authentication failures
sudo tee /etc/fail2ban/filter.d/lawyer-chat-auth.conf << EOF
[Definition]
failregex = Failed login attempt.*from <HOST>
            Invalid credentials.*from <HOST>
            Account locked.*from <HOST>
ignoreregex =
EOF

# Create filter for API abuse
sudo tee /etc/fail2ban/filter.d/lawyer-chat-api.conf << EOF
[Definition]
failregex = <HOST>.*"(GET|POST|PUT|DELETE) /chat/api/.*" 429
ignoreregex =
EOF

# Restart Fail2Ban
sudo systemctl restart fail2ban
```

### 5.3 Security Audit and Monitoring

```bash
# Install security tools
sudo apt-get install -y lynis aide

# Run Lynis security audit
sudo lynis audit system

# Initialize AIDE (file integrity monitoring)
sudo aideinit
sudo cp /var/lib/aide/aide.db.new /var/lib/aide/aide.db

# Check for vulnerabilities in dependencies
cd /opt/aletheia/services/lawyer-chat
npm audit --production
npm audit fix --production

# Test SSL configuration
nmap --script ssl-cert,ssl-enum-ciphers -p 443 yourdomain.com

# Monitor authentication attempts
tail -f /var/log/lawyer-chat/error.log | grep -E "(login|auth|security)"
```

## Phase 6: Performance Optimization

### 6.1 Database Optimization

```sql
-- Connect to database
docker exec -it db psql -U prod_user -d lawyerchat

-- Create indexes for performance
CREATE INDEX idx_messages_chat_id ON "Message"("chatId");
CREATE INDEX idx_messages_created_at ON "Message"("createdAt");
CREATE INDEX idx_chats_user_id ON "Chat"("userId");
CREATE INDEX idx_chats_updated_at ON "Chat"("updatedAt");
CREATE INDEX idx_audit_logs_email ON "AuditLog"("email");
CREATE INDEX idx_audit_logs_created_at ON "AuditLog"("createdAt");

-- Analyze tables for query optimization
ANALYZE "User";
ANALYZE "Chat";
ANALYZE "Message";
ANALYZE "AuditLog";
```

### 6.2 Application Performance

Configure Next.js for production performance:

```bash
# Enable caching headers (add to nginx)
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}

# Enable gzip compression (nginx)
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
```

## Verification Checklist

### Core Functionality
- [ ] HTTPS working on production domain
- [ ] Users can register with @reichmanjorgensen.com email
- [ ] Email verification works (check inbox or logs)
- [ ] Users can login after verification
- [ ] Password reset functionality works
- [ ] Chat interface loads at /chat
- [ ] AI responses stream character by character
- [ ] Chat history persists and displays
- [ ] Dark mode toggle works
- [ ] PDF export generates correctly

### Security
- [ ] NEXTAUTH_SECRET is set (32+ characters)
- [ ] NODE_ENV=production
- [ ] Cookies show `__Secure-` prefix in browser
- [ ] Rate limiting blocks after limits
- [ ] Account locks after 5 failed attempts
- [ ] CSRF token required for API calls
- [ ] Audit logs record all auth events

### Infrastructure
- [ ] Database connection uses SSL
- [ ] Redis has persistence enabled
- [ ] n8n webhook responds to chat requests
- [ ] Nginx properly proxies to application
- [ ] Health check endpoint responds
- [ ] Backups run successfully
- [ ] Monitoring alerts configured
- [ ] Firewall rules active

## Troubleshooting Guide

### Application Issues

**Chat not loading:**
```bash
# Check n8n webhook
curl -X POST https://yourdomain.com/chat/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "sessionId": "test-123"}'

# Verify n8n connectivity
docker exec lawyer-chat curl http://n8n:5678/healthz

# Check webhook URL in environment
docker exec lawyer-chat env | grep N8N
```

**Authentication failures:**
```bash
# Verify NEXTAUTH configuration
docker exec lawyer-chat env | grep NEXTAUTH

# Check for cookie issues
# In browser DevTools > Application > Cookies
# Should see: __Secure-next-auth.session-token

# Review auth logs
docker logs lawyer-chat | grep -i auth
```

**Database connection issues:**
```bash
# Test database connection
docker exec lawyer-chat npx prisma db push

# Check connection pool
docker exec db psql -U prod_user -d lawyerchat -c "SELECT count(*) FROM pg_stat_activity;"

# Review connection string
docker exec lawyer-chat env | grep DATABASE_URL
```

### Performance Issues

**Slow response times:**
```bash
# Check resource usage
docker stats lawyer-chat

# Review slow queries
docker exec db psql -U prod_user -d lawyerchat -c "
SELECT query, calls, mean_exec_time, max_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;"

# Check Redis performance
docker exec redis redis-cli --raw INFO stats
```

### Emergency Procedures

**Rollback deployment:**
```bash
# Stop current version
docker-compose down

# Restore previous version
git checkout previous-tag
docker-compose up -d

# Restore database if needed
gunzip < /backup/aletheia/db_YYYYMMDD_HHMMSS.sql.gz | docker exec -i db psql -U prod_user -d lawyerchat
```

**Emergency maintenance mode:**
```bash
# Create maintenance page
echo "Under Maintenance" > /var/www/maintenance.html

# Update nginx to show maintenance
location /chat {
    return 503;
    error_page 503 @maintenance;
}

location @maintenance {
    root /var/www;
    rewrite ^.*$ /maintenance.html break;
}
```

## Summary

This deployment guide ensures a production-ready lawyer-chat application with:

✅ **Complete Functionality**: Authentication, AI chat, history, exports  
✅ **Enterprise Security**: HTTPS, CSRF, rate limiting, audit logging  
✅ **High Availability**: Redis caching, connection pooling, health checks  
✅ **Data Protection**: Automated backups, SSL connections, encryption  
✅ **Monitoring**: Logs, alerts, performance metrics  
✅ **Scalability**: Load balancer ready, horizontal scaling support  

The application is configured for legal industry compliance with comprehensive audit trails, secure authentication, and data protection measures.