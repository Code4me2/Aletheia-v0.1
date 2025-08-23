# Security Improvements from Aletheia v0.1 - Implementation Guide

## Executive Summary

This document provides a comprehensive analysis of security features and improvements identified in Aletheia v0.1 that need to be implemented in Aletheia v0. The analysis covers authentication, database security, API protection, frontend security, and infrastructure hardening.

## Critical Security Issues to Address

### 1. **Main Web Interface Authentication (CRITICAL)**

**Current State**: The main web interface at port 8080 has NO authentication mechanism.

**v0.1 Improvement**: Comprehensive authentication system in lawyer-chat service.

**Implementation Plan**:
```nginx
# Add to nginx/conf.d/default.conf
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';" always;
    
    root /usr/share/nginx/html;
    index index.html;
}
```

### 2. **Webhook Authentication (CRITICAL)**

**Current State**: n8n webhooks are publicly accessible without authentication.

**Implementation**:
1. Enable n8n webhook authentication:
```yaml
# In docker-compose.yml
N8N_WEBHOOK_JWT_AUTH_ACTIVE=true
N8N_WEBHOOK_JWT_AUTH_HEADER=Authorization
N8N_WEBHOOK_JWT_AUTH_HEADER_VALUE_PREFIX="Bearer "
```

2. Update webhook configurations in workflows to require authentication.

### 3. **Database Connection Security (HIGH)**

**Current State**: No SSL/TLS encryption for database connections.

**Implementation**:
```yaml
# Update docker-compose.yml
environment:
  - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}?sslmode=require
  - POSTGRES_SSL_MODE=require
```

### 4. **CORS Configuration (HIGH)**

**Current State**: Haystack service allows all origins with credentials.

**Fix in** `n8n/haystack-service/haystack_service.py`:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],  # Specific origins
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-CSRF-Token"],
)
```

## Security Features to Implement

### 1. **CSRF Protection for Main Interface**

Create `/website/js/csrf.js`:
```javascript
class CSRFProtection {
    constructor() {
        this.token = null;
        this.tokenExpiry = null;
    }

    async getToken() {
        if (!this.token || Date.now() > this.tokenExpiry) {
            const response = await fetch('/api/csrf', {
                credentials: 'include'
            });
            const data = await response.json();
            this.token = data.token;
            this.tokenExpiry = Date.now() + (23 * 60 * 60 * 1000); // 23 hours
        }
        return this.token;
    }

    async fetch(url, options = {}) {
        const token = await this.getToken();
        return fetch(url, {
            ...options,
            headers: {
                ...options.headers,
                'X-CSRF-Token': token
            },
            credentials: 'include'
        });
    }
}

window.csrf = new CSRFProtection();
```

### 2. **Rate Limiting Implementation**

Add to NGINX configuration:
```nginx
# In nginx/conf.d/default.conf
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=webhook:10m rate=5r/s;
    
    server {
        location /webhook/ {
            limit_req zone=webhook burst=5 nodelay;
            # ... existing config
        }
        
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            # ... existing config
        }
    }
}
```

### 3. **Input Validation Enhancement**

Create `/website/js/validation.js`:
```javascript
class InputValidator {
    static sanitizeHtml(input) {
        return DOMPurify.sanitize(input, {
            ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
            ALLOWED_ATTR: ['href', 'target', 'rel']
        });
    }

    static validateMessage(message) {
        if (!message || typeof message !== 'string') {
            throw new Error('Invalid message');
        }
        if (message.length > 10000) {
            throw new Error('Message too long');
        }
        return this.sanitizeHtml(message);
    }

    static escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
```

### 4. **Security Headers Configuration**

Complete NGINX security headers:
```nginx
# Add to nginx/conf.d/default.conf
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;
```

### 5. **Error Handling Improvements**

Create `/website/js/error-handler.js`:
```javascript
class SecureErrorHandler {
    static handle(error, context = '') {
        // Log internally
        console.error(`Error in ${context}:`, error);
        
        // Return sanitized message
        if (error.status === 429) {
            return 'Too many requests. Please try again later.';
        } else if (error.status >= 500) {
            return 'A server error occurred. Please try again later.';
        } else if (error.status === 404) {
            return 'The requested resource was not found.';
        } else {
            return 'An error occurred. Please try again.';
        }
    }
}
```

### 6. **Audit Logging Implementation**

Create database table for audit logs:
```sql
-- Add to scripts/init-databases.sh
CREATE TABLE IF NOT EXISTS security_audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(50) NOT NULL,
    user_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    action VARCHAR(100) NOT NULL,
    resource TEXT,
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_audit_timestamp ON security_audit_log(timestamp);
CREATE INDEX idx_audit_event_type ON security_audit_log(event_type);
CREATE INDEX idx_audit_user_id ON security_audit_log(user_id);
```

### 7. **Docker Security Hardening**

Update `docker-compose.yml`:
```yaml
services:
  web:
    image: nginx:1.24-alpine  # Pin version
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /var/run
      - /var/cache/nginx
    
  db:
    image: postgres:15.5-alpine  # Pin version
    security_opt:
      - no-new-privileges:true
    environment:
      - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256 --auth-local=scram-sha-256
```

## Implementation Priority

### Phase 1 - Critical (Immediate)
1. ✅ Add basic authentication to main web interface
2. ✅ Fix CORS configuration in Haystack service
3. ✅ Enable webhook authentication in n8n
4. ✅ Add security headers to NGINX

### Phase 2 - High Priority (Within 1 week)
1. ✅ Implement CSRF protection for main interface
2. ✅ Add rate limiting to all endpoints
3. ✅ Enable SSL/TLS for database connections
4. ✅ Fix error message information disclosure

### Phase 3 - Medium Priority (Within 2 weeks)
1. ✅ Implement comprehensive input validation
2. ✅ Add audit logging system
3. ✅ Harden Docker containers
4. ✅ Implement proper secrets management

### Phase 4 - Enhancement (Within 1 month)
1. ✅ Migrate to JWT-based authentication
2. ✅ Implement role-based access control
3. ✅ Add security monitoring and alerting
4. ✅ Implement automated security testing

## Testing Checklist

- [ ] Verify authentication blocks unauthorized access
- [ ] Test CSRF protection on all state-changing operations
- [ ] Confirm rate limiting prevents abuse
- [ ] Validate error messages don't leak information
- [ ] Test input validation prevents XSS/injection
- [ ] Verify security headers are present
- [ ] Confirm audit logs capture security events
- [ ] Test database connections use SSL/TLS

## Monitoring and Maintenance

1. **Security Event Monitoring**:
   - Monitor failed authentication attempts
   - Track rate limit violations
   - Alert on unusual error patterns
   - Review audit logs regularly

2. **Regular Updates**:
   - Update Docker base images monthly
   - Review and update dependencies
   - Perform security scans quarterly
   - Conduct penetration testing annually

## Conclusion

Implementing these security improvements from v0.1 will significantly enhance the security posture of Aletheia v0. The most critical issues are the lack of authentication on the main interface and the publicly accessible webhooks. These should be addressed immediately before any production deployment.

The lawyer-chat service in the current codebase demonstrates excellent security practices that should be extended to the entire application. By following this implementation guide, Aletheia v0 can achieve enterprise-grade security suitable for handling sensitive legal data.