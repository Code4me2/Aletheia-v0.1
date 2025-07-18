# Authentication Setup Guide

## Overview

The lawyer-chat authentication system is fully implemented with all security features. This guide explains how to set up and test the authentication system.

## Current Features

### ✅ Implemented Security Features

1. **User Registration & Login**
   - Email domain validation (only @reichmanjorgensen.com allowed)
   - Password complexity requirements (8+ chars, uppercase, lowercase, numbers, special chars)
   - Email verification required before login
   - User enumeration protection (identical responses for existing/new emails)

2. **Account Security**
   - Account lockout after 5 failed login attempts
   - 30-minute lockout duration
   - Failed attempt tracking with IP logging
   - Comprehensive audit logging
   - Field-level encryption for sensitive data (tokens, IP addresses)

3. **Password Management**
   - Secure password hashing with bcrypt (cost factor 12)
   - Password reset flow with email tokens
   - Reset tokens expire after 1 hour
   - Validated password regex pattern with proper anchoring

4. **Rate Limiting**
   - In-memory rate limiting in Edge Runtime middleware
   - Redis-based rate limiting available for server-side API routes
   - Different limits per endpoint:
     - Auth: 5 attempts/minute
     - Chat: 20 messages/minute
     - API: 100 requests/minute
   - Note: Middleware uses in-memory due to Edge Runtime limitations

5. **CSRF Protection**
   - Active on all state-changing requests
   - Secure token generation and validation
   - HMAC-based token signatures
   - Timing-safe comparison

6. **Additional Security**
   - Email failure resilience with retry mechanism
   - Input validation and sanitization (DOMPurify)
   - Comprehensive security headers
   - API authentication for webhook requests
   - Role-based access control (user/admin)

📖 **See [SECURITY_FEATURES.md](./SECURITY_FEATURES.md) for complete security implementation details**

## Setup Instructions

### 1. Environment Configuration

Copy the example environment file and configure:

```bash
cp services/lawyer-chat/.env.example services/lawyer-chat/.env
```

**Required Configuration:**

```env
# Authentication (REQUIRED)
NEXTAUTH_SECRET=generate-a-secure-32-character-string-here
NEXTAUTH_URL=http://localhost:8080/chat

# Database (Already configured in docker-compose)
DATABASE_URL=postgresql://aletheia_user:aletheia_pass_2024@db:5432/lawyerchat

# Email Service (Optional - for email delivery)
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USER=your-email@example.com  # Replace with real email
SMTP_PASS=your-password           # Replace with real password
SMTP_FROM="Aletheia Legal <noreply@reichmanjorgensen.com>"

# Security Configuration (Defaults are fine)
ALLOWED_EMAIL_DOMAINS=@reichmanjorgensen.com
SESSION_MAX_AGE=28800
MAX_LOGIN_ATTEMPTS=5
LOCKOUT_DURATION=1800000
```

### 2. Generate NEXTAUTH_SECRET

Generate a secure secret for production:

```bash
openssl rand -base64 32
```

### 3. Start Services

```bash
# Start all services including Redis
docker-compose up -d

# Check services are running
docker-compose ps
```

### 4. Initialize Database

The database is automatically initialized when the container starts. To verify:

```bash
# Check database logs
docker-compose logs db

# Check if tables are created
docker exec -it db psql -U aletheia_user -d lawyerchat -c "\dt"
```

## Testing Authentication (Without Email Delivery)

Since email delivery requires SMTP credentials, here's how to test in development:

### 1. User Registration

1. Visit: http://localhost:8080/chat/auth/register
2. Enter details:
   - Name: Test User
   - Email: test@reichmanjorgensen.com
   - Password: Test@123!

3. Submit form - you'll see a success message

4. **Get Verification URL from logs:**
   ```bash
   docker-compose logs lawyer-chat | grep "VERIFICATION EMAIL"
   ```
   
   You'll see output like:
   ```
   =================================
   VERIFICATION EMAIL (DEV MODE)
   To: test@reichmanjorgensen.com
   Verification URL: http://localhost:8080/chat/api/auth/verify?email=test%40reichmanjorgensen.com&token=abc123...
   =================================
   ```

5. Copy and visit the verification URL in your browser

### 2. User Login

After email verification:
1. Visit: http://localhost:8080/chat/auth/signin
2. Login with your credentials
3. You'll be redirected to the chat interface

### 3. Password Reset

1. Visit: http://localhost:8080/chat/auth/forgot-password
2. Enter your email
3. **Get Reset URL from logs:**
   ```bash
   docker-compose logs lawyer-chat | grep "PASSWORD RESET EMAIL"
   ```
4. Copy and visit the reset URL
5. Enter new password

### 4. Test Account Lockout

1. Try logging in with wrong password 5 times
2. Account will be locked for 30 minutes
3. Check audit logs:
   ```bash
   docker exec -it db psql -U aletheia_user -d lawyerchat -c "SELECT * FROM \"AuditLog\" ORDER BY \"createdAt\" DESC LIMIT 10;"
   ```

### 5. Test Rate Limiting

```bash
# Test rate limiting (should block after 5 attempts)
for i in {1..10}; do
  curl -X POST http://localhost:8080/chat/api/auth/signin \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
  echo
done
```

## Admin User Creation

To create an admin user for testing:

```bash
# Access the database
docker exec -it db psql -U aletheia_user -d lawyerchat

# Create admin user (already verified)
INSERT INTO "User" (id, email, name, password, role, "emailVerified", "createdAt", "updatedAt")
VALUES (
  gen_random_uuid(),
  'admin@reichmanjorgensen.com',
  'Admin User',
  '$2b$12$YOUR_BCRYPT_HASH_HERE', -- Generate with: npm run hash-password
  'admin',
  NOW(),
  NOW(),
  NOW()
);
```

## Production Deployment Checklist

**Critical (Must Have Before Deploy):**
- [ ] Set strong `NEXTAUTH_SECRET` (32+ characters)
- [ ] Configure production `NEXTAUTH_URL` (https://yourdomain.com/chat)
- [ ] Set up HTTPS with SSL certificate

**Security (Already Implemented):**
- [x] Session cookie security (✅ configured in auth.ts)
  - `__Secure-` prefix in production
  - `httpOnly` and `secure` flags
  - `sameSite` CSRF protection

**Infrastructure:**
- [ ] Use production database with SSL
- [ ] Enable Redis persistence in production
- [ ] Configure firewall rules

**Optional (Can Add Later):**
- [ ] Set up SMTP credentials for email delivery
- [ ] Set up monitoring and alerts
- [ ] Review and adjust rate limits based on usage
- [ ] Enable audit log retention policy
- [ ] Set up backup strategy

**See PRODUCTION_DEPLOYMENT_GUIDE.md for detailed step-by-step instructions.**

## Troubleshooting

### Common Issues

1. **"Invalid CSRF token"**
   - Clear browser cookies
   - Ensure NEXTAUTH_URL matches your domain

2. **"Too many requests"**
   - Rate limit hit - wait 1 minute
   - Middleware uses in-memory rate limiting (Edge Runtime compatible)
   - Redis is available for server-side API routes if needed

3. **Can't verify email**
   - Check logs for verification URL
   - Ensure you're copying the complete URL
   - Token expires after 24 hours

4. **Account locked**
   - Wait 30 minutes or manually unlock:
   ```sql
   UPDATE "User" SET "failedLoginAttempts" = 0, "lockedUntil" = NULL 
   WHERE email = 'user@reichmanjorgensen.com';
   ```

5. **TypeScript Build Errors**
   - **"Parameter implicitly has an 'any' type"**: The project uses strict TypeScript with `no-explicit-any` rule. Use Prisma's generated types:
     ```typescript
     import type { Prisma } from '@/generated/prisma';
     
     // For query results with includes
     type ChatWithMessages = Prisma.ChatGetPayload<{
       include: { messages: true }
     }>;
     
     // For transactions
     async (tx: Prisma.TransactionClient) => { ... }
     ```
   - **Prisma import errors**: Ensure imports use the custom output path: `@/generated/prisma` (not `@prisma/client`)

### Viewing Logs

```bash
# All lawyer-chat logs
docker-compose logs -f lawyer-chat

# Just authentication events
docker-compose logs lawyer-chat | grep -E "(AUTH|LOGIN|REGISTER|VERIFY)"

# Database queries
docker-compose logs -f db
```

## Security Best Practices

1. **Never commit real credentials** - Use environment variables
2. **Use strong passwords** - Minimum 8 characters with complexity
3. **Monitor audit logs** - Check for suspicious activity
4. **Keep dependencies updated** - Regular security updates
5. **Use HTTPS in production** - Protect session cookies
6. **Configure firewall** - Limit Redis/database access

## Email Configuration (When Ready)

When you're ready to enable real email delivery:

1. **For Office 365:**
   ```env
   SMTP_HOST=smtp.office365.com
   SMTP_PORT=587
   SMTP_USER=your-email@reichmanjorgensen.com
   SMTP_PASS=your-password
   SMTP_FROM="Aletheia Legal <your-email@reichmanjorgensen.com>"
   NODE_ENV=production
   ```

2. **For Gmail (Less Secure Apps):**
   ```env
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASS=your-app-password
   ```

3. **For SendGrid (Recommended):**
   ```env
   SMTP_HOST=smtp.sendgrid.net
   SMTP_PORT=587
   SMTP_USER=apikey
   SMTP_PASS=your-sendgrid-api-key
   ```

After configuring, restart the service:
```bash
docker-compose restart lawyer-chat
```

## Technical Notes

### Rate Limiting Architecture

The system uses a dual approach for rate limiting:

1. **Middleware (Edge Runtime)**: Uses in-memory rate limiting
   - Fast and efficient for single-instance deployments
   - Automatically cleans up expired entries
   - Works in Vercel Edge Runtime and similar environments

2. **Server-Side APIs**: Can use Redis-based rate limiting
   - Available via `src/lib/rateLimiter.ts`
   - Supports distributed deployments
   - Persists across restarts
   - Falls back to in-memory if Redis unavailable

This architecture ensures compatibility with modern edge deployments while maintaining the option for distributed rate limiting when needed.

## Summary

The authentication system is fully functional with:
- ✅ Secure user registration and login
- ✅ Email verification (console logging in dev)
- ✅ Password reset functionality
- ✅ Account lockout protection
- ✅ Rate limiting (dual implementation)
- ✅ CSRF protection
- ✅ Session cookie security (production-ready)
- ✅ Comprehensive audit logging

**Production Deployment Requirements:**
1. **Critical**: HTTPS, NEXTAUTH_SECRET, Production URL
2. **Already Done**: Cookie security configuration
3. **Optional**: SMTP credentials (system works without it)

See **PRODUCTION_DEPLOYMENT_GUIDE.md** for complete deployment instructions.