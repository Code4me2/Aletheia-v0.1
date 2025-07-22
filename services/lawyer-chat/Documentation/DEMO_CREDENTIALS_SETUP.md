# Demo Credentials Setup Guide

## Quick Start - Simplest Method

For local development and testing, use this SQL command to create demo users directly:

```bash
# Create demo users with pre-verified email status
docker exec aletheia-db-1 psql -U your_db_user -d lawyerchat << 'EOF'
-- Create demo user (password: "password")
INSERT INTO "User" (id, email, name, password, role, "emailVerified", "createdAt", "updatedAt", "failedLoginAttempts")
VALUES 
  ('demo-user-001', 'demo@reichmanjorgensen.com', 'Demo User', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'user', NOW(), NOW(), NOW(), 0);

-- Create admin user (password: "password")
INSERT INTO "User" (id, email, name, password, role, "emailVerified", "createdAt", "updatedAt", "failedLoginAttempts")
VALUES 
  ('admin-user-001', 'admin@reichmanjorgensen.com', 'Admin User', '$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi', 'admin', NOW(), NOW(), NOW(), 0);
EOF
```

**Demo Credentials:**
- **Demo User:** `demo@reichmanjorgensen.com` / `password`
- **Admin User:** `admin@reichmanjorgensen.com` / `password`

Access the application at: http://localhost:8080/chat

## Understanding the Email Verification Issue

### The Problem

The lawyer-chat application has a critical issue in production mode:

1. **Container runs in production mode** (`NODE_ENV=production`)
2. **Registration requires email verification**
3. **SMTP credentials are not configured** (default to dummy values)
4. **Failed email = User deletion**: If email sending fails, the registration code deletes the user from the database

This creates an impossible situation where you cannot register users without working email configuration.

### Code Evidence

From `src/app/api/auth/register/route.ts`:

```typescript
// Send verification email
try {
  await sendVerificationEmail(email, verificationToken);
} catch {
  // If email fails, delete the user and return error
  await prisma.user.delete({ where: { id: user.id } });
  return new Response(
    JSON.stringify({ 
      error: 'Failed to send verification email. Please try again.' 
    }), 
    { status: 500, headers: { 'Content-Type': 'application/json' } }
  );
}
```

## Alternative Methods for Creating Users

### Method 1: Database Seed Script (Requires tsx)

**Note:** This method fails in production containers because `tsx` is not included.

```bash
# This will fail in production container:
docker exec lawyer-chat npm run db:seed
# Error: tsx not found
```

### Method 2: Create-Admin Script (Requires tsx)

**Note:** This method also fails in production containers.

```bash
# This will fail in production container:
docker exec lawyer-chat npm run create-admin
# Error: tsx not found
```

### Method 3: Development Mode with Console Logging

If you can run the container in development mode, emails will be logged to console instead:

```bash
# Set NODE_ENV=development in docker-compose.yml
# Then registration will log:
# =================================
# VERIFICATION EMAIL (DEV MODE)
# To: test@reichmanjorgensen.com
# Verification URL: http://localhost:8080/chat/api/auth/verify?email=...
# =================================
```

### Method 4: Direct Database Insert (Recommended)

The most reliable method is direct database insertion with pre-verified status, as shown in the Quick Start section above.

## Technical Details

### Password Hashing

The demo users use bcrypt with cost factor 10:
- Hash: `$2a$10$92IXUNpkjO0rOQ5byMi.Ye4oKoEa3Ro9llC/.og/at2.uheWG/igi`
- Password: `password`
- This is a widely-used test hash that's safe for demo purposes

### Required Fields

When creating users directly, these fields are mandatory:
- `id`: Unique identifier (can be any unique string)
- `email`: Must end with `@reichmanjorgensen.com`
- `password`: Bcrypt hash of the password
- `role`: Either 'user' or 'admin' (lowercase)
- `emailVerified`: Must be set to bypass verification
- `failedLoginAttempts`: Should be 0

### Security Notes

⚠️ **WARNING**: These demo credentials are for local development only!
- Never use simple passwords in production
- Always configure proper SMTP for production deployments
- The direct database method bypasses security checks

## Troubleshooting

### Login Still Fails

If login fails with these credentials:

1. **Check the role field**:
   ```sql
   SELECT email, role FROM "User";
   -- Role should be lowercase: 'user' or 'admin'
   ```

2. **Check email verification**:
   ```sql
   SELECT email, "emailVerified" FROM "User";
   -- emailVerified should NOT be NULL
   ```

3. **Check failed login attempts**:
   ```sql
   SELECT email, "failedLoginAttempts", "lockedUntil" FROM "User";
   -- Reset if needed:
   UPDATE "User" SET "failedLoginAttempts" = 0, "lockedUntil" = NULL WHERE email = 'demo@reichmanjorgensen.com';
   ```

### Container Issues

If the lawyer-chat container isn't accessible:

1. **Check nginx routing**:
   - Should be accessible at: http://localhost:8080/chat
   - NOT at: http://localhost:3001/chat

2. **Verify container is running**:
   ```bash
   docker ps | grep lawyer-chat
   ```

3. **Check nginx configuration**:
   ```bash
   docker exec aletheia-web-1 cat /etc/nginx/conf.d/default.conf | grep -A 5 "location /chat"
   ```

## Production Deployment

For production deployments:

1. **Configure real SMTP credentials** in `.env`
2. **Use strong passwords** and proper user registration flow
3. **Never bypass email verification** in production
4. See `PRODUCTION_DEPLOYMENT_GUIDE.md` for full details

## Summary

The simplest and most reliable method for creating demo credentials in lawyer-chat is the direct database insertion shown in the Quick Start section. This bypasses the email verification issue that blocks normal registration in containers without proper SMTP configuration.