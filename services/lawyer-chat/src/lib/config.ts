/**
 * Centralized configuration for the lawyer-chat application
 * All environment variables and defaults are managed here
 */

export const config = {
  email: {
    host: process.env.SMTP_HOST || 'smtp.office365.com',
    port: parseInt(process.env.SMTP_PORT || '587'),
    user: process.env.SMTP_USER || '',
    pass: process.env.SMTP_PASS || '',
    from: process.env.SMTP_FROM || 'Aletheia Legal <noreply@reichmanjorgensen.com>',
    mode: process.env.EMAIL_MODE || 'console'
  },
  security: {
    allowedDomains: (process.env.ALLOWED_EMAIL_DOMAINS || '@reichmanjorgensen.com').split(',').map(d => d.trim()),
    sessionMaxAge: parseInt(process.env.SESSION_MAX_AGE || '28800'), // 8 hours in seconds
    maxLoginAttempts: parseInt(process.env.MAX_LOGIN_ATTEMPTS || '5'),
    lockoutDuration: parseInt(process.env.LOCKOUT_DURATION || '1800000'), // 30 minutes in milliseconds
    passwordMinLength: parseInt(process.env.PASSWORD_MIN_LENGTH || '8'),
    tokenExpiryHours: parseInt(process.env.TOKEN_EXPIRY_HOURS || '24'),
    resetTokenExpiryHours: parseInt(process.env.RESET_TOKEN_EXPIRY_HOURS || '1')
  },
  redis: {
    url: process.env.REDIS_URL || 'redis://localhost:6379/0'
  },
  auth: {
    secret: process.env.NEXTAUTH_SECRET,
    url: process.env.NEXTAUTH_URL || 'http://localhost:8080/chat',
    basePath: process.env.NEXTAUTH_BASE_PATH || '/chat'
  },
  database: {
    url: process.env.DATABASE_URL
  },
  environment: {
    nodeEnv: process.env.NODE_ENV || 'development',
    isDevelopment: process.env.NODE_ENV === 'development',
    isProduction: process.env.NODE_ENV === 'production',
    isTest: process.env.NODE_ENV === 'test'
  }
};

// Validate required configuration
export function validateConfig() {
  const errors: string[] = [];

  if (!config.auth.secret && config.environment.isProduction) {
    errors.push('NEXTAUTH_SECRET is required in production');
  }

  if (!config.database.url) {
    errors.push('DATABASE_URL is required');
  }

  if (config.environment.isProduction && !config.email.user) {
    errors.push('SMTP_USER is required in production');
  }

  if (errors.length > 0) {
    throw new Error(`Configuration validation failed:\n${errors.join('\n')}`);
  }
}

// Export helper to check if email domain is allowed
export function isAllowedEmailDomain(email: string): boolean {
  const domain = email.substring(email.lastIndexOf('@'));
  return config.security.allowedDomains.some(allowedDomain => 
    domain.toLowerCase() === allowedDomain.toLowerCase()
  );
}

// Export formatted email domain list for user messages
export function getAllowedDomainsForDisplay(): string {
  return config.security.allowedDomains.join(', ');
}